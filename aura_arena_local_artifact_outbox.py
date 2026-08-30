from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence, Tuple

from aura_arena_artifact_event_core import (
    UNKNOWN,
    ArtifactIdentity,
    ArtifactMutationEvent,
    FileObservation,
    MirrorLineage,
    QuiescenceProof,
    prove_quiescence,
)

LOCAL_OUTBOX_SCHEMA = "LocalArtifactOutboxRecordV1"
LOCAL_OUTBOX_DB_SCHEMA = 1


class LocalOutboxRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(name: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise LocalOutboxRefusal(f"INVALID_{name.upper()}")
    value = value.strip()
    if not value and not allow_empty:
        raise LocalOutboxRefusal(f"INVALID_{name.upper()}")
    return value


def _digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _proof_dict(proof: QuiescenceProof | None) -> dict | None:
    return None if proof is None else asdict(proof)


@dataclass(frozen=True)
class LocalWatchConfig:
    roots: Tuple[str, ...]
    source_surface: str
    project_id: str
    source_currentness_ref: str
    producer_worker_id: str = UNKNOWN
    claim_id: str = UNKNOWN
    work_order_id: str = UNKNOWN
    provider: str = "LOCAL_FS"
    min_stable_samples: int = 2
    min_stable_ns: int = 25_000_000

    def __post_init__(self) -> None:
        if not self.roots:
            raise LocalOutboxRefusal("LOCAL_ROOT_REQUIRED")
        roots = tuple(str(Path(root).expanduser().resolve(strict=False)) for root in self.roots)
        if len(set(roots)) != len(roots):
            raise LocalOutboxRefusal("DUPLICATE_LOCAL_ROOT")
        object.__setattr__(self, "roots", roots)
        for name in ("source_surface", "project_id", "provider"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        currentness = _text("source_currentness_ref", self.source_currentness_ref)
        if currentness == UNKNOWN:
            raise LocalOutboxRefusal("CURRENTNESS_REF_REQUIRED")
        object.__setattr__(self, "source_currentness_ref", currentness)
        for name in ("producer_worker_id", "claim_id", "work_order_id"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if self.min_stable_samples < 2:
            raise LocalOutboxRefusal("INVALID_STABLE_SAMPLE_REQUIREMENT")
        if self.min_stable_ns < 0:
            raise LocalOutboxRefusal("INVALID_STABLE_NS")


@dataclass(frozen=True)
class LocalArtifactOutboxRecord:
    mutation_key: str
    event: ArtifactMutationEvent
    identity: ArtifactIdentity | None
    quiescence: QuiescenceProof | None
    local_path: str
    resource_ref: str
    status: str = "PENDING"
    ack_ref: str = ""
    schema: str = LOCAL_OUTBOX_SCHEMA
    execution_authorized: bool = False
    provider_calls_authorized: bool = False
    background_execution_claimed: bool = False

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "mutation_key": self.mutation_key,
            "event": self.event.to_dict(),
            "identity": None if self.identity is None else asdict(self.identity),
            "quiescence": _proof_dict(self.quiescence),
            "local_path": self.local_path,
            "resource_ref": self.resource_ref,
            "status": self.status,
            "ack_ref": self.ack_ref,
            "execution_authorized": False,
            "provider_calls_authorized": False,
            "background_execution_claimed": False,
        }


@dataclass(frozen=True)
class LocalIngestResult:
    disposition: str
    record: LocalArtifactOutboxRecord | None = None


class LocalArtifactOutbox:
    """Crash-safe local mutation outbox. It observes/persists; it never routes authority or executes work."""

    def __init__(self, db_path: os.PathLike[str] | str, config: LocalWatchConfig) -> None:
        self.db_path = str(Path(db_path).expanduser().resolve(strict=False))
        self.config = config
        self._conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def close(self) -> None:
        self._conn.close()

    def _init_db(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS resource_generation (
                resource_ref TEXT PRIMARY KEY,
                generation INTEGER NOT NULL CHECK(generation >= 0)
            );
            CREATE TABLE IF NOT EXISTS outbox (
                mutation_key TEXT PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                resource_ref TEXT NOT NULL,
                generation INTEGER NOT NULL CHECK(generation >= 0),
                record_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('PENDING','ACKED')),
                ack_ref TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS outbox_status_event_idx ON outbox(status, event_id);
            """
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO metadata(key,value) VALUES('schema_version',?)",
            (str(LOCAL_OUTBOX_DB_SCHEMA),),
        )
        row = self._conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        if row is None or row["value"] != str(LOCAL_OUTBOX_DB_SCHEMA):
            raise LocalOutboxRefusal("OUTBOX_SCHEMA_MISMATCH")

    def _resource_for_path(self, path: os.PathLike[str] | str) -> tuple[Path, str]:
        candidate = Path(path).expanduser().resolve(strict=False)
        for index, root_text in enumerate(self.config.roots):
            root = Path(root_text)
            try:
                rel = candidate.relative_to(root)
            except ValueError:
                continue
            return candidate, f"local-root-{index}://{rel.as_posix()}"
        raise LocalOutboxRefusal("PATH_OUTSIDE_CONFIGURED_ROOT", str(candidate))

    @staticmethod
    def sample(path: os.PathLike[str] | str, observed_monotonic_ns: int) -> FileObservation:
        stat = Path(path).stat()
        return FileObservation(stat.st_size, stat.st_mtime_ns, observed_monotonic_ns)

    def _currentness_is_admitted(self, expected_currentness_ref: str, currentness: str) -> bool:
        expected = _text("expected_currentness_ref", expected_currentness_ref)
        qualitative = _text("currentness", currentness).upper()
        return expected == self.config.source_currentness_ref and qualitative == "CURRENT"

    def _mirror_preflight(
        self,
        inbound_mirror_lineage: MirrorLineage | None,
        *,
        expected_mirror_origin_id: str | None,
        expected_mirror_generation: int | None,
    ) -> str | None:
        """Validate exact inbound mirror identity before any outbox/generation effect."""
        if inbound_mirror_lineage is None:
            return None
        if self.config.source_surface in inbound_mirror_lineage.surfaces:
            return "SELF_LOOP_SUPPRESSED"
        if expected_mirror_origin_id is None or expected_mirror_generation is None:
            raise LocalOutboxRefusal("MIRROR_EXPECTATION_REQUIRED")
        expected_origin = _text("expected_mirror_origin_id", expected_mirror_origin_id)
        if inbound_mirror_lineage.origin_id != expected_origin:
            raise LocalOutboxRefusal("MIRROR_ORIGIN_BINDING_MISMATCH")
        if (
            not isinstance(expected_mirror_generation, int)
            or isinstance(expected_mirror_generation, bool)
            or expected_mirror_generation < 0
        ):
            raise LocalOutboxRefusal("INVALID_EXPECTED_MIRROR_GENERATION")
        if inbound_mirror_lineage.artifact_generation != expected_mirror_generation:
            raise LocalOutboxRefusal("MIRROR_GENERATION_BINDING_MISMATCH")
        return None

    def _read_bound_bytes(self, path: Path, proof: QuiescenceProof) -> bytes:
        before = path.stat()
        if (before.st_size, before.st_mtime_ns) != (proof.byte_size, proof.mtime_ns):
            raise LocalOutboxRefusal("QUIESCENCE_STAT_MISMATCH", str(path))
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_size, opened.st_mtime_ns) != (proof.byte_size, proof.mtime_ns):
                raise LocalOutboxRefusal("ARTIFACT_CHANGED_BEFORE_READ", str(path))
            body = handle.read()
            after_fd = os.fstat(handle.fileno())
        after_path = path.stat()
        expected = (proof.byte_size, proof.mtime_ns)
        if (after_fd.st_size, after_fd.st_mtime_ns) != expected or (after_path.st_size, after_path.st_mtime_ns) != expected:
            raise LocalOutboxRefusal("ARTIFACT_CHANGED_DURING_READ", str(path))
        if len(body) != proof.byte_size:
            raise LocalOutboxRefusal("ARTIFACT_READ_SIZE_MISMATCH", str(path))
        return body

    @staticmethod
    def _record_from_json(payload: str, status: str, ack_ref: str) -> LocalArtifactOutboxRecord:
        data = json.loads(payload)
        return LocalArtifactOutboxRecord(
            mutation_key=data["mutation_key"],
            event=ArtifactMutationEvent(**dict(data["event"])),
            identity=None if data.get("identity") is None else ArtifactIdentity(**data["identity"]),
            quiescence=None if data.get("quiescence") is None else QuiescenceProof(**data["quiescence"]),
            local_path=data["local_path"],
            resource_ref=data["resource_ref"],
            status=status,
            ack_ref=ack_ref,
        )

    def _enqueue(
        self,
        *,
        event_type: str,
        resource_ref: str,
        local_path: str,
        identity: ArtifactIdentity | None,
        quiescence: QuiescenceProof | None,
        observed_at: str,
        prior_artifact_id: str = "",
        prior_resource_ref: str = "",
        inbound_mirror_lineage: MirrorLineage | None = None,
    ) -> LocalIngestResult:
        mutation_payload = {
            "event_type": event_type.upper(),
            "resource_ref": resource_ref,
            "identity_sha256": "" if identity is None else identity.sha256,
            "identity_size": -1 if identity is None else identity.byte_size,
            "mtime_ns": -1 if quiescence is None else quiescence.mtime_ns,
            "prior_artifact_id": prior_artifact_id,
            "prior_resource_ref": prior_resource_ref,
            "project_id": self.config.project_id,
            "source_surface": self.config.source_surface,
            "mirror_origin_id": "" if inbound_mirror_lineage is None else inbound_mirror_lineage.origin_id,
            "mirror_generation": -1 if inbound_mirror_lineage is None else inbound_mirror_lineage.artifact_generation,
            "mirror_surfaces": () if inbound_mirror_lineage is None else inbound_mirror_lineage.surfaces,
        }
        mutation_key = f"lmut-{_digest(mutation_payload)[:40]}"
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                "SELECT record_json,status,ack_ref FROM outbox WHERE mutation_key=?", (mutation_key,)
            ).fetchone()
            if row is not None:
                self._conn.execute("COMMIT")
                return LocalIngestResult(
                    "IDEMPOTENT_REPLAY",
                    self._record_from_json(row["record_json"], row["status"], row["ack_ref"]),
                )

            advances_local_generation = inbound_mirror_lineage is None
            if advances_local_generation:
                row = self._conn.execute(
                    "SELECT generation FROM resource_generation WHERE resource_ref=?", (resource_ref,)
                ).fetchone()
                generation = 1 if row is None else int(row["generation"]) + 1
                origin_id = f"local-origin-{mutation_key[5:37]}"
                lineage = MirrorLineage.start(
                    origin_id, self.config.source_surface, artifact_generation=generation
                )
            else:
                if self.config.source_surface in inbound_mirror_lineage.surfaces:
                    self._conn.execute("ROLLBACK")
                    return LocalIngestResult("SELF_LOOP_SUPPRESSED", None)
                lineage = inbound_mirror_lineage.next_hop(self.config.source_surface)
                generation = lineage.artifact_generation
                origin_id = lineage.origin_id

            event = ArtifactMutationEvent(
                origin_id=origin_id,
                provider=self.config.provider,
                source_surface=self.config.source_surface,
                event_type=event_type,
                resource_ref=resource_ref,
                project_id=self.config.project_id,
                producer_worker_id=self.config.producer_worker_id,
                claim_id=self.config.claim_id,
                work_order_id=self.config.work_order_id,
                source_currentness_ref=self.config.source_currentness_ref,
                observed_at=_text("observed_at", observed_at),
                generation=generation,
                mirror_fence=lineage.fence,
                prior_artifact_id=prior_artifact_id,
                prior_resource_ref=prior_resource_ref,
            )
            record = LocalArtifactOutboxRecord(
                mutation_key, event, identity, quiescence, local_path, resource_ref
            )
            encoded = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
            self._conn.execute(
                "INSERT INTO outbox(mutation_key,event_id,resource_ref,generation,record_json,status,ack_ref) VALUES(?,?,?,?,?,'PENDING','')",
                (mutation_key, event.event_id, resource_ref, generation, encoded),
            )
            if advances_local_generation:
                self._conn.execute(
                    "INSERT INTO resource_generation(resource_ref,generation) VALUES(?,?) ON CONFLICT(resource_ref) DO UPDATE SET generation=excluded.generation",
                    (resource_ref, generation),
                )
            self._conn.execute("COMMIT")
            return LocalIngestResult("ENQUEUED", record)
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def ingest_file_notification(
        self,
        path: os.PathLike[str] | str,
        *,
        event_type: str,
        observations: Sequence[FileObservation],
        observed_at: str,
        expected_currentness_ref: str,
        currentness: str = "CURRENT",
        closed_evidence: bool = False,
        atomic_publish_evidence: bool = False,
        prior_artifact_id: str = "",
        prior_resource_ref: str = "",
        inbound_mirror_lineage: MirrorLineage | None = None,
        expected_mirror_origin_id: str | None = None,
        expected_mirror_generation: int | None = None,
    ) -> LocalIngestResult:
        if not self._currentness_is_admitted(expected_currentness_ref, currentness):
            return LocalIngestResult("REBASE", None)
        path_obj, resource_ref = self._resource_for_path(path)
        mirror_disposition = self._mirror_preflight(
            inbound_mirror_lineage,
            expected_mirror_origin_id=expected_mirror_origin_id,
            expected_mirror_generation=expected_mirror_generation,
        )
        if mirror_disposition is not None:
            return LocalIngestResult(mirror_disposition, None)
        proof = prove_quiescence(
            observations,
            min_stable_samples=self.config.min_stable_samples,
            min_stable_ns=self.config.min_stable_ns,
            closed_evidence=closed_evidence,
            atomic_publish_evidence=atomic_publish_evidence,
        )
        body = self._read_bound_bytes(path_obj, proof)
        identity = ArtifactIdentity.from_bytes(
            body,
            mime_type=mimetypes.guess_type(path_obj.name)[0] or "application/octet-stream",
            extension=path_obj.suffix,
            parent_refs=(resource_ref,),
        )
        return self._enqueue(
            event_type=event_type,
            resource_ref=resource_ref,
            local_path=str(path_obj),
            identity=identity,
            quiescence=proof,
            observed_at=observed_at,
            prior_artifact_id=prior_artifact_id,
            prior_resource_ref=prior_resource_ref,
            inbound_mirror_lineage=inbound_mirror_lineage,
        )

    def ingest_tombstone(
        self,
        path: os.PathLike[str] | str,
        *,
        observed_at: str,
        expected_currentness_ref: str,
        currentness: str = "CURRENT",
        prior_artifact_id: str = "",
        prior_resource_ref: str = "",
        inbound_mirror_lineage: MirrorLineage | None = None,
        expected_mirror_origin_id: str | None = None,
        expected_mirror_generation: int | None = None,
    ) -> LocalIngestResult:
        if not self._currentness_is_admitted(expected_currentness_ref, currentness):
            return LocalIngestResult("REBASE", None)
        path_obj, resource_ref = self._resource_for_path(path)
        mirror_disposition = self._mirror_preflight(
            inbound_mirror_lineage,
            expected_mirror_origin_id=expected_mirror_origin_id,
            expected_mirror_generation=expected_mirror_generation,
        )
        if mirror_disposition is not None:
            return LocalIngestResult(mirror_disposition, None)
        if not (prior_artifact_id.strip() or prior_resource_ref.strip()):
            raise LocalOutboxRefusal("PRIOR_LINEAGE_REQUIRED", resource_ref)
        return self._enqueue(
            event_type="TOMBSTONE",
            resource_ref=resource_ref,
            local_path=str(path_obj),
            identity=None,
            quiescence=None,
            observed_at=observed_at,
            prior_artifact_id=prior_artifact_id,
            prior_resource_ref=prior_resource_ref,
            inbound_mirror_lineage=inbound_mirror_lineage,
        )

    def ingest_rename(
        self,
        old_path: os.PathLike[str] | str,
        new_path: os.PathLike[str] | str,
        *,
        observations: Sequence[FileObservation],
        observed_at: str,
        expected_currentness_ref: str,
        currentness: str = "CURRENT",
        prior_artifact_id: str = "",
        closed_evidence: bool = False,
        atomic_publish_evidence: bool = False,
        inbound_mirror_lineage: MirrorLineage | None = None,
        expected_mirror_origin_id: str | None = None,
        expected_mirror_generation: int | None = None,
    ) -> LocalIngestResult:
        if not self._currentness_is_admitted(expected_currentness_ref, currentness):
            return LocalIngestResult("REBASE", None)
        mirror_disposition = self._mirror_preflight(
            inbound_mirror_lineage,
            expected_mirror_origin_id=expected_mirror_origin_id,
            expected_mirror_generation=expected_mirror_generation,
        )
        if mirror_disposition is not None:
            return LocalIngestResult(mirror_disposition, None)
        _, old_resource = self._resource_for_path(old_path)
        return self.ingest_file_notification(
            new_path,
            event_type="RENAME",
            observations=observations,
            observed_at=observed_at,
            expected_currentness_ref=expected_currentness_ref,
            currentness=currentness,
            closed_evidence=closed_evidence,
            atomic_publish_evidence=atomic_publish_evidence,
            prior_artifact_id=prior_artifact_id,
            prior_resource_ref=old_resource,
            inbound_mirror_lineage=inbound_mirror_lineage,
            expected_mirror_origin_id=expected_mirror_origin_id,
            expected_mirror_generation=expected_mirror_generation,
        )

    def pending(self) -> list[LocalArtifactOutboxRecord]:
        rows = self._conn.execute(
            "SELECT record_json,status,ack_ref FROM outbox WHERE status='PENDING' ORDER BY event_id"
        ).fetchall()
        return [
            self._record_from_json(row["record_json"], row["status"], row["ack_ref"])
            for row in rows
        ]

    def ack(self, event_id: str, *, persistence_receipt_ref: str) -> str:
        event_id = _text("event_id", event_id)
        receipt = _text("persistence_receipt_ref", persistence_receipt_ref)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                "SELECT status,ack_ref FROM outbox WHERE event_id=?", (event_id,)
            ).fetchone()
            if row is None:
                raise LocalOutboxRefusal("UNKNOWN_EVENT_ID", event_id)
            if row["status"] == "ACKED":
                if row["ack_ref"] != receipt:
                    raise LocalOutboxRefusal("ACK_RECEIPT_CONFLICT", event_id)
                self._conn.execute("COMMIT")
                return "IDEMPOTENT_ACK"
            self._conn.execute(
                "UPDATE outbox SET status='ACKED',ack_ref=? WHERE event_id=?", (receipt, event_id)
            )
            self._conn.execute("COMMIT")
            return "ACKED"
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def generation_for(self, path: os.PathLike[str] | str) -> int:
        _, resource_ref = self._resource_for_path(path)
        row = self._conn.execute(
            "SELECT generation FROM resource_generation WHERE resource_ref=?", (resource_ref,)
        ).fetchone()
        return 0 if row is None else int(row["generation"])

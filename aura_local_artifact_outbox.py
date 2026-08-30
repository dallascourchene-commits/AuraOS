from __future__ import annotations

import json
import mimetypes
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from aura_arena_artifact_event_core import (
    ArtifactEventRefusal,
    ArtifactIdentity,
    ArtifactMutationEvent,
    FileObservation,
    MirrorLineage,
    QuiescenceProof,
    classify_replay,
    prove_quiescence,
    validate_event_identity_binding,
)


LOCAL_OUTBOX_SCHEMA = "LocalAuraDrive2OutboxV1"
LOCAL_ENVELOPE_SCHEMA = "LocalArtifactEnvelopeV1"
LOCAL_SURFACE = "AURA_DRIVE_2_LOCAL"
LOCAL_PROVIDER = "LOCAL_FS"


class LocalArtifactRefusal(ValueError):
    """Typed fail-closed refusal for the local Aura Drive 2 adapter."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LocalArtifactRefusal(f"INVALID_{name.upper()}")
    return value.strip()


def _nonnegative_int(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise LocalArtifactRefusal(f"INVALID_{name.upper()}")
    return value


def _resolve_inside_root(root: Path | str, relative_path: str, *, require_exists: bool) -> tuple[Path, str]:
    root_path = Path(root).expanduser().resolve(strict=True)
    rel_text = _text("relative_path", relative_path).replace("\\", "/")
    rel = Path(rel_text)
    if rel.is_absolute() or ".." in rel.parts:
        raise LocalArtifactRefusal("PATH_OUTSIDE_AURA_DRIVE_2", rel_text)
    target = (root_path / rel).resolve(strict=require_exists)
    try:
        normalized = target.relative_to(root_path).as_posix()
    except ValueError as exc:
        raise LocalArtifactRefusal("PATH_OUTSIDE_AURA_DRIVE_2", rel_text) from exc
    if require_exists and not target.is_file():
        raise LocalArtifactRefusal("LOCAL_RESOURCE_NOT_REGULAR_FILE", normalized)
    lexical = root_path / rel
    if lexical.exists() and lexical.is_symlink():
        raise LocalArtifactRefusal("LOCAL_SYMLINK_NOT_ADMITTED", normalized)
    return target, normalized


def sample_file_observation(root: Path | str, relative_path: str, *, observed_monotonic_ns: int) -> FileObservation:
    """Take one caller-timed local file sample. This function never sleeps or starts a watcher."""
    _nonnegative_int("observed_monotonic_ns", observed_monotonic_ns)
    target, _ = _resolve_inside_root(root, relative_path, require_exists=True)
    stat = target.stat()
    return FileObservation(
        byte_size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        observed_monotonic_ns=observed_monotonic_ns,
    )


@dataclass(frozen=True)
class LocalMutationIntent:
    origin_id: str
    event_type: str
    relative_path: str
    project_id: str
    source_currentness_ref: str
    artifact_generation: int
    producer_worker_id: str = "UNKNOWN"
    claim_id: str = "UNKNOWN"
    work_order_id: str = "UNKNOWN"
    observed_at: str = "UNKNOWN"
    prior_artifact_id: str = ""
    prior_resource_ref: str = ""

    def __post_init__(self) -> None:
        for name in ("origin_id", "event_type", "relative_path", "project_id", "source_currentness_ref"):
            _text(name, getattr(self, name))
        _nonnegative_int("artifact_generation", self.artifact_generation)


@dataclass(frozen=True)
class LocalArtifactEnvelope:
    event: ArtifactMutationEvent
    identity: ArtifactIdentity | None
    quiescence: QuiescenceProof | None
    mirror_lineage: MirrorLineage
    disposition: str
    schema: str = LOCAL_ENVELOPE_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "disposition": self.disposition,
            "event": self.event.to_dict(),
            "identity": asdict(self.identity) if self.identity is not None else None,
            "quiescence": asdict(self.quiescence) if self.quiescence is not None else None,
            "mirror_lineage": asdict(self.mirror_lineage),
            "authority": {
                "semantic_owner_bound": False,
                "coordinate_owner_bound": False,
                "cloud_write_authorized": False,
                "artifact_persistence_indexed": False,
                "workgraph_wake_emitted": False,
                "execution_authorized": False,
                "runtime_execution_proven": False,
                "background_execution_claimed": False,
                "provider_calls": 0,
            },
        }


@dataclass(frozen=True)
class LocalStageResult:
    disposition: str
    event_id: str
    enqueued: bool
    envelope: LocalArtifactEnvelope


def _bind_lineage(intent: LocalMutationIntent, inbound_lineage: MirrorLineage | None) -> MirrorLineage:
    if inbound_lineage is None:
        return MirrorLineage.start(
            intent.origin_id,
            LOCAL_SURFACE,
            artifact_generation=intent.artifact_generation,
        )
    if inbound_lineage.origin_id != intent.origin_id:
        raise LocalArtifactRefusal("MIRROR_ORIGIN_BINDING_MISMATCH")
    if inbound_lineage.artifact_generation != intent.artifact_generation:
        raise LocalArtifactRefusal("MIRROR_GENERATION_BINDING_MISMATCH")
    try:
        return inbound_lineage.next_hop(LOCAL_SURFACE)
    except ArtifactEventRefusal as exc:
        raise LocalArtifactRefusal(exc.code, exc.detail) from exc


def build_local_envelope(
    root: Path | str,
    intent: LocalMutationIntent,
    *,
    expected_currentness_ref: str,
    currentness: str,
    observations: Sequence[FileObservation] = (),
    min_stable_ns: int = 0,
    closed_evidence: bool = False,
    atomic_publish_evidence: bool = False,
    inbound_lineage: MirrorLineage | None = None,
    seen_event_ids: Iterable[str] = (),
) -> LocalArtifactEnvelope:
    """Bind one local mutation to AS-02 without inferring semantic ownership or execution."""
    expected_ref = _text("expected_currentness_ref", expected_currentness_ref)
    _, normalized = _resolve_inside_root(
        root,
        intent.relative_path,
        require_exists=intent.event_type.upper() not in {"DELETE", "TOMBSTONE"},
    )
    resource_ref = f"aura-drive-2://{normalized}"
    lineage = _bind_lineage(intent, inbound_lineage)

    identity: ArtifactIdentity | None = None
    proof: QuiescenceProof | None = None
    if intent.event_type.upper() not in {"DELETE", "TOMBSTONE"}:
        try:
            proof = prove_quiescence(
                observations,
                min_stable_ns=min_stable_ns,
                closed_evidence=closed_evidence,
                atomic_publish_evidence=atomic_publish_evidence,
            )
        except ArtifactEventRefusal as exc:
            raise LocalArtifactRefusal(exc.code, exc.detail) from exc

        target, _ = _resolve_inside_root(root, intent.relative_path, require_exists=True)
        before = target.stat()
        if (before.st_size, before.st_mtime_ns) != (proof.byte_size, proof.mtime_ns):
            raise LocalArtifactRefusal("LOCAL_FILE_CHANGED_AFTER_QUIESCENCE")
        payload = target.read_bytes()
        after = target.stat()
        if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise LocalArtifactRefusal("LOCAL_FILE_CHANGED_DURING_READ")
        mime_type, _ = mimetypes.guess_type(target.name)
        identity = ArtifactIdentity.from_bytes(
            payload,
            mime_type=mime_type or "application/octet-stream",
            extension=target.suffix,
            parent_refs=tuple(ref for ref in (intent.prior_artifact_id,) if ref),
        )

    try:
        event = ArtifactMutationEvent(
            origin_id=intent.origin_id,
            provider=LOCAL_PROVIDER,
            source_surface=LOCAL_SURFACE,
            event_type=intent.event_type,
            resource_ref=resource_ref,
            project_id=intent.project_id,
            producer_worker_id=intent.producer_worker_id,
            claim_id=intent.claim_id,
            work_order_id=intent.work_order_id,
            source_currentness_ref=intent.source_currentness_ref,
            observed_at=intent.observed_at,
            generation=intent.artifact_generation,
            mirror_fence=lineage.fence,
            prior_artifact_id=intent.prior_artifact_id,
            prior_resource_ref=intent.prior_resource_ref,
        )
        validate_event_identity_binding(event, identity)
    except ArtifactEventRefusal as exc:
        raise LocalArtifactRefusal(exc.code, exc.detail) from exc

    if intent.source_currentness_ref != expected_ref:
        disposition = "REBASE"
    else:
        disposition = classify_replay(
            event,
            currentness=currentness,
            seen_event_ids=seen_event_ids,
        )
    return LocalArtifactEnvelope(event, identity, proof, lineage, disposition)


class LocalArtifactOutbox:
    """Crash-safe local coordination outbox; it performs no cloud write or background wake."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = str(database_path)
        self._db = sqlite3.connect(self.database_path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS local_artifact_outbox (
                event_id TEXT PRIMARY KEY,
                schema TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                artifact_sid TEXT,
                disposition TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','DELIVERED')),
                delivery_receipt_ref TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "LocalArtifactOutbox":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def seen_event_ids(self) -> tuple[str, ...]:
        rows = self._db.execute("SELECT event_id FROM local_artifact_outbox ORDER BY event_id").fetchall()
        return tuple(row[0] for row in rows)

    def stage(
        self,
        root: Path | str,
        intent: LocalMutationIntent,
        *,
        expected_currentness_ref: str,
        currentness: str,
        observations: Sequence[FileObservation] = (),
        min_stable_ns: int = 0,
        closed_evidence: bool = False,
        atomic_publish_evidence: bool = False,
        inbound_lineage: MirrorLineage | None = None,
    ) -> LocalStageResult:
        envelope = build_local_envelope(
            root,
            intent,
            expected_currentness_ref=expected_currentness_ref,
            currentness=currentness,
            observations=observations,
            min_stable_ns=min_stable_ns,
            closed_evidence=closed_evidence,
            atomic_publish_evidence=atomic_publish_evidence,
            inbound_lineage=inbound_lineage,
            seen_event_ids=self.seen_event_ids(),
        )
        event_id = envelope.event.event_id
        if envelope.disposition == "REBASE":
            return LocalStageResult("REBASE", event_id, False, envelope)
        if envelope.disposition == "IDEMPOTENT_REPLAY":
            return LocalStageResult("IDEMPOTENT_REPLAY", event_id, False, envelope)
        if envelope.disposition not in {"INGEST", "TOMBSTONE"}:
            raise LocalArtifactRefusal("UNSUPPORTED_OUTBOX_DISPOSITION", envelope.disposition)

        payload_json = json.dumps(
            envelope.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        artifact_sid = envelope.identity.artifact_sid if envelope.identity is not None else None
        try:
            with self._db:
                self._db.execute(
                    """
                    INSERT INTO local_artifact_outbox
                        (event_id, schema, payload_json, artifact_sid, disposition, state)
                    VALUES (?, ?, ?, ?, ?, 'PENDING')
                    """,
                    (event_id, LOCAL_OUTBOX_SCHEMA, payload_json, artifact_sid, envelope.disposition),
                )
        except sqlite3.IntegrityError:
            existing = self._db.execute(
                "SELECT payload_json FROM local_artifact_outbox WHERE event_id = ?", (event_id,)
            ).fetchone()
            if existing is None or existing[0] != payload_json:
                raise LocalArtifactRefusal("OUTBOX_EVENT_ID_COLLISION", event_id)
            return LocalStageResult("IDEMPOTENT_REPLAY", event_id, False, envelope)
        return LocalStageResult(envelope.disposition, event_id, True, envelope)

    def pending(self, *, limit: int = 100) -> list[dict[str, object]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise LocalArtifactRefusal("INVALID_PENDING_LIMIT")
        rows = self._db.execute(
            """
            SELECT payload_json FROM local_artifact_outbox
            WHERE state = 'PENDING' ORDER BY rowid LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def mark_delivered(self, event_id: str, delivery_receipt_ref: str) -> None:
        event = _text("event_id", event_id)
        receipt = _text("delivery_receipt_ref", delivery_receipt_ref)
        row = self._db.execute(
            "SELECT state, delivery_receipt_ref FROM local_artifact_outbox WHERE event_id = ?", (event,)
        ).fetchone()
        if row is None:
            raise LocalArtifactRefusal("OUTBOX_EVENT_NOT_FOUND", event)
        state, prior_receipt = row
        if state == "DELIVERED":
            if prior_receipt != receipt:
                raise LocalArtifactRefusal("DELIVERY_RECEIPT_BINDING_MISMATCH", event)
            return
        with self._db:
            self._db.execute(
                """
                UPDATE local_artifact_outbox
                SET state = 'DELIVERED', delivery_receipt_ref = ?
                WHERE event_id = ? AND state = 'PENDING'
                """,
                (receipt, event),
            )

    def count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM local_artifact_outbox").fetchone()[0])

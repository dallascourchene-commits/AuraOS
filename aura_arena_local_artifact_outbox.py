"""Crash-safe local Aura Drive 2 mutation intake/outbox for CS-ARENA-SYNC-001 AS-04.

This adapter is intentionally local-observation/persistence only. It does not watch in a
background thread, write Google Drive, assign semantic coordinates, mutate WorkGraph,
or grant effect authority. A host watcher/poller supplies stable source-event keys and
samples; this module deduplicates, sequences per-artifact generations, proves
quiescence using the AS-02 core, snapshots stable bytes, and publishes append-only
outbox records for downstream AS-05/AS-06 consumers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import mimetypes
from pathlib import Path
import secrets
import sqlite3
from typing import Any, Mapping, Sequence

from aura_arena_artifact_event_core import (
    ArtifactIdentity,
    ArtifactMutationEvent,
    ArtifactEventRefusal,
    FileObservation,
    MirrorLineage,
    UNKNOWN,
    prove_quiescence,
    validate_event_identity_binding,
)

SCHEMA = "LocalArtifactOutboxV1"
NOTICE_SCHEMA = "LocalArtifactMutationNoticeV1"
OUTBOX_SCHEMA = "LocalArtifactOutboxRecordV1"
LOCAL_PROVIDER = "LOCAL_FS"
CONTENT_EVENTS = frozenset({"CREATE", "MODIFY", "ACCEPT", "SUPERSEDE", "MIRROR_REPAIR", "RENAME"})
TOMBSTONE_EVENTS = frozenset({"DELETE", "TOMBSTONE"})
ALLOWED_NOTICE_EVENTS = CONTENT_EVENTS | TOMBSTONE_EVENTS


class LocalArtifactOutboxError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canon(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise LocalArtifactOutboxError("NONCANONICAL_VALUE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256((domain + "\0" + _canon(value)).encode("utf-8")).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LocalArtifactOutboxError(code)
    text = value.strip()
    if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in text):
        raise LocalArtifactOutboxError(code)
    return text


def _nonnegative_int(value: Any, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise LocalArtifactOutboxError(code)
    return value


@dataclass(frozen=True)
class LocalMutationNotice:
    source_event_key: str
    event_type: str
    relative_path: str
    observed_at: str
    source_currentness_ref: str
    project_id: str
    producer_worker_id: str = UNKNOWN
    claim_id: str = UNKNOWN
    work_order_id: str = UNKNOWN
    prior_relative_path: str = ""
    prior_artifact_id: str = ""
    mirror_lineage: Mapping[str, Any] | None = None

    def validate(self) -> None:
        for value, code in (
            (self.source_event_key, "SOURCE_EVENT_KEY_REQUIRED"),
            (self.relative_path, "RELATIVE_PATH_REQUIRED"),
            (self.observed_at, "OBSERVED_AT_REQUIRED"),
            (self.source_currentness_ref, "SOURCE_CURRENTNESS_REQUIRED"),
            (self.project_id, "PROJECT_ID_REQUIRED"),
            (self.producer_worker_id, "PRODUCER_WORKER_REQUIRED"),
            (self.claim_id, "CLAIM_ID_REQUIRED"),
            (self.work_order_id, "WORK_ORDER_ID_REQUIRED"),
        ):
            _text(value, code)
        event_type = _text(self.event_type, "EVENT_TYPE_REQUIRED").upper()
        if event_type not in ALLOWED_NOTICE_EVENTS:
            raise LocalArtifactOutboxError("EVENT_TYPE_UNSUPPORTED", event_type)
        if event_type in {"RENAME", "DELETE", "TOMBSTONE", "SUPERSEDE"} and not (
            str(self.prior_relative_path).strip() or str(self.prior_artifact_id).strip()
        ):
            raise LocalArtifactOutboxError("PRIOR_LINEAGE_REQUIRED", event_type)
        if self.mirror_lineage is not None:
            if not isinstance(self.mirror_lineage, Mapping):
                raise LocalArtifactOutboxError("MIRROR_LINEAGE_INVALID")
            _canon(dict(self.mirror_lineage))

    @property
    def event_type_upper(self) -> str:
        return self.event_type.strip().upper()

    @property
    def notice_id(self) -> str:
        self.validate()
        # Stable source-event key is the primary replay identity. Currentness/project
        # are included so a reused external key in another project cannot collide.
        payload = {
            "schema": NOTICE_SCHEMA,
            "source_event_key": self.source_event_key,
            "event_type": self.event_type_upper,
            "relative_path": self.relative_path,
            "prior_relative_path": self.prior_relative_path,
            "project_id": self.project_id,
            "source_currentness_ref": self.source_currentness_ref,
            "mirror_lineage": dict(self.mirror_lineage) if self.mirror_lineage else None,
        }
        return "lan-" + _digest("LOCAL_ARTIFACT_NOTICE_V1", payload)[:32]


class LocalArtifactOutbox:
    """SQLite/WAL durable local mutation inbox plus append-only artifact outbox."""

    def __init__(self, db_path: str | Path, *, root: str | Path, source_surface: str) -> None:
        self.db_path = Path(db_path)
        self.root = Path(root).expanduser().resolve(strict=False)
        self.source_surface = _text(source_surface, "SOURCE_SURFACE_REQUIRED")
        if self.root == self.root.parent:
            raise LocalArtifactOutboxError("ROOT_TOO_BROAD")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    relative_path TEXT PRIMARY KEY,
                    origin_id TEXT NOT NULL,
                    latest_generation INTEGER NOT NULL,
                    latest_artifact_sid TEXT,
                    state TEXT NOT NULL CHECK(state IN ('ACTIVE','PENDING','TOMBSTONED','RENAMED')),
                    last_notice_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notices (
                    notice_id TEXT PRIMARY KEY,
                    source_event_key TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    prior_relative_path TEXT NOT NULL,
                    prior_artifact_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    source_currentness_ref TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    producer_worker_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL,
                    work_order_id TEXT NOT NULL,
                    origin_id TEXT NOT NULL,
                    artifact_generation INTEGER NOT NULL,
                    mirror_lineage_json TEXT,
                    state TEXT NOT NULL CHECK(state IN ('PENDING','READY','OUTBOXED','SUPERSEDED','ERROR')),
                    error_code TEXT,
                    UNIQUE(project_id, source_event_key, event_type, relative_path, prior_relative_path)
                );
                CREATE TABLE IF NOT EXISTS observations (
                    notice_id TEXT NOT NULL REFERENCES notices(notice_id) ON DELETE CASCADE,
                    observed_monotonic_ns INTEGER NOT NULL,
                    byte_size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    PRIMARY KEY(notice_id, observed_monotonic_ns)
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    event_id TEXT PRIMARY KEY,
                    notice_id TEXT NOT NULL UNIQUE REFERENCES notices(notice_id),
                    record_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('PENDING','CLAIMED','DONE','ERROR')),
                    claim_token TEXT,
                    claim_owner TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def _normalize_relative(self, relative_path: str) -> tuple[str, Path]:
        text = _text(relative_path, "RELATIVE_PATH_REQUIRED").replace("\\", "/")
        candidate = (self.root / text).resolve(strict=False)
        try:
            rel = candidate.relative_to(self.root)
        except ValueError as exc:
            raise LocalArtifactOutboxError("PATH_ESCAPES_ROOT", text) from exc
        normalized = rel.as_posix()
        if normalized in {"", "."}:
            raise LocalArtifactOutboxError("ROOT_ARTIFACT_FORBIDDEN")
        return normalized, candidate

    def _parse_mirror(self, raw: Mapping[str, Any] | None) -> MirrorLineage | None:
        if raw is None:
            return None
        required = {"origin_id", "artifact_generation", "surfaces", "hop_index", "max_hops"}
        if set(raw) != required:
            raise LocalArtifactOutboxError("MIRROR_LINEAGE_SHAPE_INVALID")
        try:
            lineage = MirrorLineage(
                origin_id=str(raw["origin_id"]),
                artifact_generation=int(raw["artifact_generation"]),
                surfaces=tuple(str(v) for v in raw["surfaces"]),
                hop_index=int(raw["hop_index"]),
                max_hops=int(raw["max_hops"]),
            )
        except (ArtifactEventRefusal, TypeError, ValueError) as exc:
            raise LocalArtifactOutboxError("MIRROR_LINEAGE_INVALID") from exc
        if not lineage.surfaces or lineage.surfaces[-1] != self.source_surface:
            raise LocalArtifactOutboxError("MIRROR_LINEAGE_LOCAL_SURFACE_MISMATCH")
        return lineage

    def ingest_notice(self, notice: LocalMutationNotice) -> dict[str, Any]:
        notice.validate()
        relative, _ = self._normalize_relative(notice.relative_path)
        prior_relative = ""
        if notice.prior_relative_path.strip():
            prior_relative, _ = self._normalize_relative(notice.prior_relative_path)
        mirror = self._parse_mirror(notice.mirror_lineage)
        notice_id = notice.notice_id

        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM notices WHERE notice_id=?", (notice_id,)).fetchone()
            if existing is not None:
                return self._notice_dict(existing, replay=True)

            event_type = notice.event_type_upper
            source_row = conn.execute("SELECT * FROM resources WHERE relative_path=?", (relative,)).fetchone()
            prior_row = None
            if prior_relative:
                prior_row = conn.execute("SELECT * FROM resources WHERE relative_path=?", (prior_relative,)).fetchone()

            if mirror is not None:
                origin_id = mirror.origin_id
                artifact_generation = mirror.artifact_generation
            elif event_type == "CREATE":
                if source_row is not None and source_row["state"] != "TOMBSTONED":
                    # A CREATE against a live path is ambiguous; watcher should classify it as MODIFY.
                    raise LocalArtifactOutboxError("CREATE_PATH_ALREADY_OWNED", relative)
                origin_id = "origin-" + _digest(
                    "LOCAL_ARTIFACT_ORIGIN_V1",
                    {"project_id": notice.project_id, "source_event_key": notice.source_event_key, "path": relative},
                )[:32]
                artifact_generation = 0
            elif event_type == "RENAME":
                if prior_row is None or prior_row["state"] == "TOMBSTONED":
                    raise LocalArtifactOutboxError("RENAME_PRIOR_RESOURCE_UNKNOWN", prior_relative)
                if source_row is not None and source_row["origin_id"] != prior_row["origin_id"] and source_row["state"] != "TOMBSTONED":
                    raise LocalArtifactOutboxError("RENAME_TARGET_COLLISION", relative)
                origin_id = str(prior_row["origin_id"])
                artifact_generation = int(prior_row["latest_generation"]) + 1
            else:
                if source_row is None or source_row["state"] == "TOMBSTONED":
                    raise LocalArtifactOutboxError("RESOURCE_LINEAGE_UNKNOWN", relative)
                origin_id = str(source_row["origin_id"])
                artifact_generation = int(source_row["latest_generation"]) + 1

            conn.execute("BEGIN IMMEDIATE")
            # Re-read inside write transaction to prevent two same-path notices receiving the same generation.
            if mirror is None and event_type not in {"CREATE", "RENAME"}:
                locked = conn.execute("SELECT * FROM resources WHERE relative_path=?", (relative,)).fetchone()
                if locked is None or locked["state"] == "TOMBSTONED":
                    raise LocalArtifactOutboxError("RESOURCE_LINEAGE_UNKNOWN", relative)
                origin_id = str(locked["origin_id"])
                artifact_generation = int(locked["latest_generation"]) + 1
            elif mirror is None and event_type == "RENAME":
                locked_prior = conn.execute("SELECT * FROM resources WHERE relative_path=?", (prior_relative,)).fetchone()
                if locked_prior is None or locked_prior["state"] == "TOMBSTONED":
                    raise LocalArtifactOutboxError("RENAME_PRIOR_RESOURCE_UNKNOWN", prior_relative)
                origin_id = str(locked_prior["origin_id"])
                artifact_generation = int(locked_prior["latest_generation"]) + 1

            conn.execute(
                """INSERT INTO notices(
                    notice_id,source_event_key,event_type,relative_path,prior_relative_path,prior_artifact_id,
                    observed_at,source_currentness_ref,project_id,producer_worker_id,claim_id,work_order_id,
                    origin_id,artifact_generation,mirror_lineage_json,state
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    notice_id, notice.source_event_key, event_type, relative, prior_relative,
                    notice.prior_artifact_id.strip(), notice.observed_at, notice.source_currentness_ref,
                    notice.project_id, notice.producer_worker_id, notice.claim_id, notice.work_order_id,
                    origin_id, artifact_generation, _canon(dict(notice.mirror_lineage)) if notice.mirror_lineage else None,
                    "PENDING",
                ),
            )

            if event_type == "RENAME":
                conn.execute("UPDATE resources SET state='RENAMED', last_notice_id=? WHERE relative_path=?", (notice_id, prior_relative))
                conn.execute(
                    """INSERT INTO resources(relative_path,origin_id,latest_generation,latest_artifact_sid,state,last_notice_id)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(relative_path) DO UPDATE SET origin_id=excluded.origin_id,
                    latest_generation=excluded.latest_generation,state=excluded.state,last_notice_id=excluded.last_notice_id""",
                    (relative, origin_id, artifact_generation, notice.prior_artifact_id.strip() or None, "PENDING", notice_id),
                )
            elif event_type == "CREATE":
                conn.execute(
                    """INSERT INTO resources(relative_path,origin_id,latest_generation,latest_artifact_sid,state,last_notice_id)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(relative_path) DO UPDATE SET origin_id=excluded.origin_id,
                    latest_generation=excluded.latest_generation,latest_artifact_sid=NULL,state=excluded.state,last_notice_id=excluded.last_notice_id""",
                    (relative, origin_id, artifact_generation, None, "PENDING", notice_id),
                )
            else:
                new_state = "PENDING" if event_type in CONTENT_EVENTS else "TOMBSTONED"
                conn.execute(
                    "UPDATE resources SET latest_generation=?, state=?, last_notice_id=? WHERE relative_path=?",
                    (artifact_generation, new_state, notice_id, relative),
                )

            row = conn.execute("SELECT * FROM notices WHERE notice_id=?", (notice_id,)).fetchone()
            return self._notice_dict(row, replay=False)

    def _notice_dict(self, row: sqlite3.Row, *, replay: bool) -> dict[str, Any]:
        return {
            "schema": NOTICE_SCHEMA,
            "notice_id": row["notice_id"],
            "event_type": row["event_type"],
            "relative_path": row["relative_path"],
            "origin_id": row["origin_id"],
            "artifact_generation": row["artifact_generation"],
            "state": row["state"],
            "idempotent_replay": replay,
        }

    def sample_notice(self, notice_id: str, *, observed_monotonic_ns: int) -> dict[str, Any]:
        _nonnegative_int(observed_monotonic_ns, "OBSERVED_MONOTONIC_NS_INVALID")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM notices WHERE notice_id=?", (_text(notice_id, "NOTICE_ID_REQUIRED"),)).fetchone()
            if row is None:
                raise LocalArtifactOutboxError("NOTICE_UNKNOWN")
            if row["event_type"] in TOMBSTONE_EVENTS:
                raise LocalArtifactOutboxError("TOMBSTONE_HAS_NO_FILE_SAMPLE")
            _, path = self._normalize_relative(row["relative_path"])
            try:
                stat = path.stat()
            except FileNotFoundError as exc:
                raise LocalArtifactOutboxError("ARTIFACT_NOT_PRESENT") from exc
            conn.execute(
                "INSERT OR IGNORE INTO observations(notice_id,observed_monotonic_ns,byte_size,mtime_ns) VALUES(?,?,?,?)",
                (notice_id, observed_monotonic_ns, int(stat.st_size), int(stat.st_mtime_ns)),
            )
            return {
                "notice_id": notice_id,
                "byte_size": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
                "observed_monotonic_ns": observed_monotonic_ns,
            }

    def finalize_notice(
        self,
        notice_id: str,
        *,
        min_stable_ns: int,
        min_stable_samples: int = 2,
        closed_evidence: bool = False,
        atomic_publish_evidence: bool = False,
    ) -> dict[str, Any]:
        notice_id = _text(notice_id, "NOTICE_ID_REQUIRED")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM notices WHERE notice_id=?", (notice_id,)).fetchone()
            if row is None:
                raise LocalArtifactOutboxError("NOTICE_UNKNOWN")
            if row["state"] == "OUTBOXED":
                existing = conn.execute("SELECT record_json FROM outbox WHERE notice_id=?", (notice_id,)).fetchone()
                if existing is None:
                    raise LocalArtifactOutboxError("OUTBOX_STATE_CORRUPT")
                result = json.loads(existing["record_json"])
                result["idempotent_replay"] = True
                return result
            if row["state"] in {"SUPERSEDED", "ERROR"}:
                raise LocalArtifactOutboxError("NOTICE_NOT_FINALIZABLE", row["state"])

            event_type = str(row["event_type"])
            relative = str(row["relative_path"])
            current_resource = conn.execute("SELECT * FROM resources WHERE relative_path=?", (relative,)).fetchone()
            if event_type in CONTENT_EVENTS:
                if current_resource is None or int(current_resource["latest_generation"]) != int(row["artifact_generation"]):
                    conn.execute("UPDATE notices SET state='SUPERSEDED', error_code='LATER_MUTATION_EXISTS' WHERE notice_id=?", (notice_id,))
                    raise LocalArtifactOutboxError("NOTICE_SUPERSEDED_BY_LATER_MUTATION")
                obs_rows = conn.execute(
                    "SELECT * FROM observations WHERE notice_id=? ORDER BY observed_monotonic_ns", (notice_id,)
                ).fetchall()
                samples = [FileObservation(int(o["byte_size"]), int(o["mtime_ns"]), int(o["observed_monotonic_ns"])) for o in obs_rows]
                try:
                    proof = prove_quiescence(
                        samples,
                        min_stable_samples=min_stable_samples,
                        min_stable_ns=min_stable_ns,
                        closed_evidence=closed_evidence,
                        atomic_publish_evidence=atomic_publish_evidence,
                    )
                except ArtifactEventRefusal as exc:
                    raise LocalArtifactOutboxError(exc.code, exc.detail) from exc

                _, path = self._normalize_relative(relative)
                try:
                    before = path.stat()
                    body = path.read_bytes()
                    after = path.stat()
                except FileNotFoundError as exc:
                    raise LocalArtifactOutboxError("ARTIFACT_DISAPPEARED_DURING_SNAPSHOT") from exc
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise LocalArtifactOutboxError("ARTIFACT_CHANGED_DURING_SNAPSHOT")
                if (int(after.st_size), int(after.st_mtime_ns)) != (proof.byte_size, proof.mtime_ns):
                    raise LocalArtifactOutboxError("ARTIFACT_CHANGED_AFTER_QUIESCENCE")
                mime, _ = mimetypes.guess_type(path.name)
                identity = ArtifactIdentity.from_bytes(
                    body,
                    mime_type=mime or "application/octet-stream",
                    extension=path.suffix,
                    parent_refs=tuple(v for v in (row["prior_artifact_id"],) if v),
                )
            else:
                proof = None
                identity = None

            mirror_lineage = json.loads(row["mirror_lineage_json"]) if row["mirror_lineage_json"] else None
            mirror_fence = ""
            if mirror_lineage:
                mirror = self._parse_mirror(mirror_lineage)
                assert mirror is not None
                mirror_fence = mirror.fence

            try:
                event = ArtifactMutationEvent(
                    origin_id=str(row["origin_id"]),
                    provider=LOCAL_PROVIDER,
                    source_surface=self.source_surface,
                    event_type=event_type,
                    resource_ref=relative,
                    project_id=str(row["project_id"]),
                    producer_worker_id=str(row["producer_worker_id"]),
                    claim_id=str(row["claim_id"]),
                    work_order_id=str(row["work_order_id"]),
                    source_currentness_ref=str(row["source_currentness_ref"]),
                    observed_at=str(row["observed_at"]),
                    generation=int(row["artifact_generation"]),
                    mirror_fence=mirror_fence,
                    prior_artifact_id=str(row["prior_artifact_id"]),
                    prior_resource_ref=str(row["prior_relative_path"]),
                )
                validate_event_identity_binding(event, identity)
            except ArtifactEventRefusal as exc:
                raise LocalArtifactOutboxError(exc.code, exc.detail) from exc

            record = {
                "schema": OUTBOX_SCHEMA,
                "notice_id": notice_id,
                "event": event.to_dict(),
                "identity": None if identity is None else {
                    "schema": identity.schema,
                    "artifact_sid": identity.artifact_sid,
                    "sha256": identity.sha256,
                    "byte_size": identity.byte_size,
                    "mime_type": identity.mime_type,
                    "extension": identity.extension,
                    "parent_refs": list(identity.parent_refs),
                },
                "quiescence": None if proof is None else asdict(proof),
                "mirror_lineage": mirror_lineage,
                "source_root": str(self.root),
                "execution_authorized": False,
                "cloud_write_authorized": False,
                "coordinate_assignment_proven": False,
                "workgraph_completion_proven": False,
            }
            record_json = _canon(record)

            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO outbox(event_id,notice_id,record_json,state) VALUES(?,?,?,'PENDING')",
                    (event.event_id, notice_id, record_json),
                )
            except sqlite3.IntegrityError:
                existing = conn.execute("SELECT record_json FROM outbox WHERE notice_id=? OR event_id=?", (notice_id, event.event_id)).fetchone()
                if existing is None or existing["record_json"] != record_json:
                    raise LocalArtifactOutboxError("OUTBOX_COLLISION")
            conn.execute("UPDATE notices SET state='OUTBOXED', error_code=NULL WHERE notice_id=?", (notice_id,))
            if event_type in CONTENT_EVENTS:
                conn.execute(
                    "UPDATE resources SET state='ACTIVE', latest_artifact_sid=?, last_notice_id=? WHERE relative_path=? AND latest_generation=?",
                    (identity.artifact_sid if identity else None, notice_id, relative, int(row["artifact_generation"])),
                )
            result = dict(record)
            result["idempotent_replay"] = False
            return result

    def claim_outbox(self, *, worker_id: str) -> dict[str, Any] | None:
        worker = _text(worker_id, "WORKER_ID_REQUIRED")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM outbox WHERE state='PENDING' ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return None
            token = "claim-" + secrets.token_hex(16)
            updated = conn.execute(
                "UPDATE outbox SET state='CLAIMED', claim_token=?, claim_owner=?, attempt_count=attempt_count+1 WHERE event_id=? AND state='PENDING'",
                (token, worker, row["event_id"]),
            )
            if updated.rowcount != 1:
                raise LocalArtifactOutboxError("OUTBOX_CLAIM_RACE")
            return {
                "event_id": row["event_id"],
                "notice_id": row["notice_id"],
                "claim_token": token,
                "claim_owner": worker,
                "record": json.loads(row["record_json"]),
            }

    def complete_outbox(self, *, event_id: str, worker_id: str, claim_token: str) -> None:
        event_id = _text(event_id, "EVENT_ID_REQUIRED")
        worker = _text(worker_id, "WORKER_ID_REQUIRED")
        token = _text(claim_token, "CLAIM_TOKEN_REQUIRED")
        with self._connect() as conn:
            updated = conn.execute(
                """UPDATE outbox SET state='DONE' WHERE event_id=? AND state='CLAIMED'
                   AND claim_owner=? AND claim_token=?""",
                (event_id, worker, token),
            )
            if updated.rowcount != 1:
                raise LocalArtifactOutboxError("OUTBOX_CLAIM_FENCE_MISMATCH")

    def release_claim(self, *, event_id: str, worker_id: str, claim_token: str) -> None:
        with self._connect() as conn:
            updated = conn.execute(
                """UPDATE outbox SET state='PENDING', claim_owner=NULL, claim_token=NULL
                   WHERE event_id=? AND state='CLAIMED' AND claim_owner=? AND claim_token=?""",
                (_text(event_id, "EVENT_ID_REQUIRED"), _text(worker_id, "WORKER_ID_REQUIRED"), _text(claim_token, "CLAIM_TOKEN_REQUIRED")),
            )
            if updated.rowcount != 1:
                raise LocalArtifactOutboxError("OUTBOX_CLAIM_FENCE_MISMATCH")

    def snapshot(self) -> dict[str, Any]:
        with self._connect() as conn:
            counts = {
                state: int(conn.execute("SELECT COUNT(*) FROM outbox WHERE state=?", (state,)).fetchone()[0])
                for state in ("PENDING", "CLAIMED", "DONE", "ERROR")
            }
            pending_notices = int(conn.execute("SELECT COUNT(*) FROM notices WHERE state='PENDING'").fetchone()[0])
            return {
                "schema": SCHEMA,
                "root": str(self.root),
                "source_surface": self.source_surface,
                "pending_notices": pending_notices,
                "outbox_counts": counts,
                "background_watcher_running": False,
                "cloud_write_capability": False,
                "coordinate_assignment_capability": False,
                "workgraph_mutation_capability": False,
            }

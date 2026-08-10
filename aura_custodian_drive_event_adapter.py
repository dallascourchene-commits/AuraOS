"""Durable, read-only provider seam for the local Aura Custodian.

This module intentionally stops at observation intake.  It turns Google Drive /
Google Workspace event material into provider-neutral ``EventEnvelope`` records,
persists them in a crash-recoverable SQLite inbox, and maintains a durable Drive
changes cursor.  It does **not** mutate Drive, Aura owners, generated projections,
or repository state.

The semantic consumer is deliberately injected later so current Aura ownership
can be source-bound without coupling this provider layer to a second routing or
authority plane.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Protocol


AURA_CUSTODIAN_DRIVE_EVENT_ADAPTER_VERSION = "AURA_CUSTODIAN_DRIVE_EVENT_ADAPTER_V1"
DEFAULT_CURSOR_KEY = "google_drive_changes"


class CursorConflictError(RuntimeError):
    """Raised when two local consumers try to advance the same provider cursor."""


class DriveChangeFeedClient(Protocol):
    """Small provider boundary implemented by the Google Drive API wrapper."""

    def get_start_page_token(self) -> str:
        """Return a current Drive changes start-page token."""

    def list_changes(self, page_token: str) -> Mapping[str, Any]:
        """Return one Drive ``changes.list`` response for ``page_token``."""


@dataclass(frozen=True)
class EventEnvelope:
    """Provider-neutral observation delivered to Aura's local runtime."""

    provider: str
    source: str
    event_type: str
    resource_id: str = ""
    provider_event_id: str = ""
    observed_at: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)
    version: str = AURA_CUSTODIAN_DRIVE_EVENT_ADAPTER_VERSION

    def __post_init__(self) -> None:
        if not str(self.provider).strip():
            raise ValueError("provider is required")
        if not str(self.source).strip():
            raise ValueError("source is required")
        if not str(self.event_type).strip():
            raise ValueError("event_type is required")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")

    @property
    def event_key(self) -> str:
        """Stable idempotency key; provider ids win, otherwise content is hashed."""
        provider = str(self.provider).strip().lower()
        event_id = str(self.provider_event_id).strip()
        if event_id:
            return f"{provider}:{event_id}"
        canonical = json.dumps(
            {
                "provider": provider,
                "source": self.source,
                "event_type": self.event_type,
                "resource_id": self.resource_id,
                "observed_at": self.observed_at,
                "payload": dict(self.payload),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{provider}:sha256:{digest}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "event_key": self.event_key,
            "provider": self.provider,
            "source": self.source,
            "event_type": self.event_type,
            "resource_id": self.resource_id,
            "provider_event_id": self.provider_event_id,
            "observed_at": self.observed_at,
            "payload": dict(self.payload),
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_workspace_event(raw: Mapping[str, Any]) -> EventEnvelope:
    """Normalize a Workspace Events / Pub/Sub CloudEvent without hydrating Drive.

    Google may evolve resource-data shapes independently of Aura.  This function
    therefore keeps the original payload intact and only extracts the small set of
    routing-neutral fields Aura needs for durable intake.
    """
    if not isinstance(raw, Mapping):
        raise ValueError("workspace event must be a mapping")
    data = raw.get("data")
    data_map = data if isinstance(data, Mapping) else {}
    resource_id = str(
        raw.get("resource_id")
        or raw.get("subject")
        or data_map.get("resource")
        or data_map.get("resourceName")
        or data_map.get("resource_name")
        or ""
    )
    return EventEnvelope(
        provider="google",
        source="workspace_events",
        provider_event_id=str(raw.get("id") or raw.get("event_id") or ""),
        event_type=str(raw.get("type") or raw.get("event_type") or "google.drive.unknown"),
        resource_id=resource_id,
        observed_at=str(raw.get("time") or raw.get("observed_at") or _utc_now_iso()),
        payload=dict(raw),
    )


def normalize_drive_change(
    raw: Mapping[str, Any],
    *,
    page_token: str,
    ordinal: int,
) -> EventEnvelope:
    """Normalize one Drive ``changes.list`` row into a replay-stable envelope."""
    if not isinstance(raw, Mapping):
        raise ValueError("Drive change must be a mapping")
    resource_id = str(raw.get("fileId") or raw.get("driveId") or "")
    change_type = str(raw.get("changeType") or "file")
    removed = bool(raw.get("removed"))
    event_type = f"drive.change.{change_type}{'.removed' if removed else ''}"
    # Drive change rows do not provide a globally unique change id.  Page token +
    # ordinal is stable across replay of the same page, which is exactly the
    # failure boundary this inbox has to make idempotent.
    provider_event_id = f"change:{page_token}:{int(ordinal)}:{resource_id}"
    return EventEnvelope(
        provider="google",
        source="drive_changes",
        provider_event_id=provider_event_id,
        event_type=event_type,
        resource_id=resource_id,
        observed_at=str(raw.get("time") or _utc_now_iso()),
        payload=dict(raw),
    )


class SQLiteCustodianEventStore:
    """Crash-recoverable local inbox, cursor store, and resource registry.

    Each operation opens a short-lived SQLite connection.  WAL mode and
    ``BEGIN IMMEDIATE`` make cursor advancement + page ingestion an atomic local
    transaction while remaining friendly to a continuously running laptop daemon.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS provider_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS event_inbox (
                    event_key TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    source TEXT NOT NULL,
                    provider_event_id TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'done', 'error')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    first_seen_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    claimed_at REAL,
                    last_error TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_custodian_event_status
                    ON event_inbox(status, first_seen_at);
                CREATE INDEX IF NOT EXISTS idx_custodian_event_resource
                    ON event_inbox(resource_id, first_seen_at);

                CREATE TABLE IF NOT EXISTS resource_registry (
                    resource_id TEXT PRIMARY KEY,
                    semantic_id TEXT NOT NULL DEFAULT '',
                    route TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _insert_envelope(conn: sqlite3.Connection, envelope: EventEnvelope, *, now: float) -> bool:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO event_inbox (
                event_key, provider, source, provider_event_id, resource_id,
                event_type, observed_at, payload_json, status, attempts,
                first_seen_at, updated_at, claimed_at, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, NULL, '')
            """,
            (
                envelope.event_key,
                envelope.provider,
                envelope.source,
                envelope.provider_event_id,
                envelope.resource_id,
                envelope.event_type,
                envelope.observed_at,
                json.dumps(dict(envelope.payload), sort_keys=True, separators=(",", ":"), default=str),
                now,
                now,
            ),
        )
        return cursor.rowcount == 1

    def enqueue(self, envelopes: Iterable[EventEnvelope]) -> int:
        """Persist observations idempotently and return newly inserted count."""
        now = time.time()
        inserted = 0
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for envelope in envelopes:
                    inserted += int(self._insert_envelope(conn, envelope, now=now))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return inserted

    def get_cursor(self, key: str = DEFAULT_CURSOR_KEY) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM provider_state WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row is not None else None

    def set_cursor_if_absent(self, value: str, *, key: str = DEFAULT_CURSOR_KEY) -> bool:
        value = str(value).strip()
        if not value:
            raise ValueError("cursor value is required")
        now = time.time()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO provider_state(key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, now),
            )
            return cursor.rowcount == 1

    def ingest_change_page(
        self,
        envelopes: Sequence[EventEnvelope],
        *,
        expected_cursor: str,
        next_cursor: str,
        key: str = DEFAULT_CURSOR_KEY,
    ) -> int:
        """Atomically persist one change page and advance its durable cursor.

        If the process dies before commit, neither the rows nor cursor advance.
        Replaying the page is therefore safe.  If another local consumer advanced
        the cursor first, fail closed rather than silently skipping observations.
        """
        expected_cursor = str(expected_cursor).strip()
        next_cursor = str(next_cursor).strip()
        if not expected_cursor or not next_cursor:
            raise ValueError("expected_cursor and next_cursor are required")
        now = time.time()
        inserted = 0
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT value FROM provider_state WHERE key = ?", (key,)).fetchone()
                current = str(row["value"]) if row is not None else None
                if current != expected_cursor:
                    raise CursorConflictError(
                        f"cursor {key!r} advanced concurrently: expected {expected_cursor!r}, got {current!r}"
                    )
                for envelope in envelopes:
                    inserted += int(self._insert_envelope(conn, envelope, now=now))
                conn.execute(
                    "UPDATE provider_state SET value = ?, updated_at = ? WHERE key = ?",
                    (next_cursor, now, key),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return inserted

    def claim_pending(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Claim a bounded pending batch for a future semantic consumer."""
        limit = max(1, min(int(limit), 1000))
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                rows = conn.execute(
                    "SELECT event_key FROM event_inbox WHERE status = 'pending' "
                    "ORDER BY first_seen_at, event_key LIMIT ?",
                    (limit,),
                ).fetchall()
                keys = [str(row["event_key"]) for row in rows]
                for key in keys:
                    conn.execute(
                        "UPDATE event_inbox SET status='processing', attempts=attempts+1, "
                        "claimed_at=?, updated_at=? WHERE event_key=? AND status='pending'",
                        (now, now, key),
                    )
                if not keys:
                    conn.commit()
                    return []
                placeholders = ",".join("?" for _ in keys)
                claimed = conn.execute(
                    f"SELECT * FROM event_inbox WHERE event_key IN ({placeholders}) ORDER BY first_seen_at, event_key",
                    keys,
                ).fetchall()
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return [self._row_to_event_record(row) for row in claimed]

    @staticmethod
    def _row_to_event_record(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["payload"] = json.loads(str(result.pop("payload_json")))
        return result

    def mark_done(self, event_key: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE event_inbox SET status='done', updated_at=?, claimed_at=NULL, last_error='' "
                "WHERE event_key=? AND status='processing'",
                (time.time(), str(event_key)),
            )
            return cursor.rowcount == 1

    def mark_error(self, event_key: str, error: str, *, retry: bool = True) -> bool:
        status = "pending" if retry else "error"
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE event_inbox SET status=?, updated_at=?, claimed_at=NULL, last_error=? "
                "WHERE event_key=? AND status='processing'",
                (status, time.time(), str(error)[:1024], str(event_key)),
            )
            return cursor.rowcount == 1

    def requeue_stale_processing(self, *, stale_after_seconds: float = 300.0) -> int:
        """Recover events whose local consumer died after claiming them."""
        threshold = time.time() - max(0.0, float(stale_after_seconds))
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE event_inbox SET status='pending', claimed_at=NULL, updated_at=?, "
                "last_error='stale_processing_requeued' "
                "WHERE status='processing' AND claimed_at IS NOT NULL AND claimed_at <= ?",
                (time.time(), threshold),
            )
            return int(cursor.rowcount)

    def pending_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM event_inbox WHERE status IN ('pending', 'processing')"
            ).fetchone()
        return int(row["count"] if row else 0)

    def upsert_resource(
        self,
        resource_id: str,
        *,
        semantic_id: str = "",
        route: str = "",
        active: bool = True,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        resource_id = str(resource_id).strip()
        if not resource_id:
            raise ValueError("resource_id is required")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO resource_registry(resource_id, semantic_id, route, active, metadata_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(resource_id) DO UPDATE SET
                    semantic_id=excluded.semantic_id,
                    route=excluded.route,
                    active=excluded.active,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    resource_id,
                    str(semantic_id),
                    str(route),
                    int(bool(active)),
                    json.dumps(dict(metadata or {}), sort_keys=True, separators=(",", ":"), default=str),
                    time.time(),
                ),
            )

    def resource_record(self, resource_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM resource_registry WHERE resource_id = ?",
                (str(resource_id),),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["active"] = bool(result["active"])
        result["metadata"] = json.loads(str(result.pop("metadata_json")))
        return result


class CustodianDriveEventAdapter:
    """Read-only local intake boundary between Google providers and Aura.

    The adapter deliberately has no Drive write client and no semantic mutation
    callback.  A later, source-bound Aura owner may consume claimed records and
    emit ordinary governed proposals through the existing background-worker path.
    """

    def __init__(self, store: SQLiteCustodianEventStore) -> None:
        self.store = store

    def ingest_workspace_events(self, raw_events: Iterable[Mapping[str, Any]]) -> int:
        return self.store.enqueue(normalize_workspace_event(raw) for raw in raw_events)

    def initialize_change_cursor(self, client: DriveChangeFeedClient) -> str:
        existing = self.store.get_cursor()
        if existing:
            return existing
        token = str(client.get_start_page_token()).strip()
        if not token:
            raise ValueError("Drive returned an empty start-page token")
        self.store.set_cursor_if_absent(token)
        return self.store.get_cursor() or token

    def reconcile_changes(
        self,
        client: DriveChangeFeedClient,
        *,
        max_pages: int = 100,
    ) -> dict[str, Any]:
        """Drain bounded Drive change pages into the durable local inbox."""
        max_pages = max(1, min(int(max_pages), 10_000))
        cursor = self.initialize_change_cursor(client)
        pages = 0
        inserted = 0
        observed = 0
        while pages < max_pages:
            response = client.list_changes(cursor)
            if not isinstance(response, Mapping):
                raise ValueError("Drive list_changes response must be a mapping")
            raw_changes = response.get("changes") or []
            if not isinstance(raw_changes, Sequence) or isinstance(raw_changes, (str, bytes, bytearray)):
                raise ValueError("Drive changes must be a sequence")
            envelopes = [
                normalize_drive_change(raw, page_token=cursor, ordinal=index)
                for index, raw in enumerate(raw_changes)
            ]
            observed += len(envelopes)
            next_page = str(response.get("nextPageToken") or "").strip()
            new_start = str(response.get("newStartPageToken") or "").strip()
            next_cursor = next_page or new_start
            if not next_cursor:
                raise ValueError("Drive response did not include nextPageToken or newStartPageToken")
            inserted += self.store.ingest_change_page(
                envelopes,
                expected_cursor=cursor,
                next_cursor=next_cursor,
            )
            pages += 1
            cursor = next_cursor
            if not next_page:
                break
        return {
            "version": AURA_CUSTODIAN_DRIVE_EVENT_ADAPTER_VERSION,
            "mode": "read_only_reconciliation",
            "pages": pages,
            "observed": observed,
            "inserted": inserted,
            "cursor": cursor,
            "pending": self.store.pending_count(),
            "page_limit_reached": pages >= max_pages and bool(next_page),
        }

    def health(self) -> dict[str, Any]:
        return {
            "version": AURA_CUSTODIAN_DRIVE_EVENT_ADAPTER_VERSION,
            "mode": "read_only",
            "cursor": self.store.get_cursor(),
            "pending": self.store.pending_count(),
            "drive_write_capability": False,
            "semantic_mutation_capability": False,
        }

"""
Aura Civic Session Store — persistent SQLite WAL-backed civic session store.

Replaces the in-memory _sessions dict. Works across separate CLI and server processes.

Tables: sessions, contributions, organ_receipts, audit_events, consent_responses,
what_if_runs, pilot_packets, decision_packets, community_memory.
"""
from __future__ import annotations
import sqlite3, json, time, hashlib, uuid
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

DEFAULT_DB_PATH = ".aura/runtime/civic_sessions.sqlite3"
SCHEMA_VERSION = 1


class CivicSessionStore:
    """Persistent civic session store using SQLite WAL."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self):
        cur = self._conn.execute("PRAGMA user_version")
        version = cur.fetchone()[0]
        if version < 1:
            self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY, value TEXT
            );
            INSERT OR REPLACE INTO schema_meta VALUES ('version', '1');

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                objective TEXT,
                objective_hash TEXT,
                state TEXT DEFAULT 'CREATED',
                story TEXT DEFAULT 'hairstylist',
                profile_set TEXT,
                created_at REAL,
                updated_at REAL,
                fixture_mode INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS session_data (
                session_id TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (session_id, key),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                contribution_type TEXT,
                data TEXT,
                created_at REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS organ_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                organ_type TEXT,
                organ_id TEXT,
                manifest_digest TEXT,
                ok INTEGER,
                executed_at REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT,
                data TEXT,
                created_at REAL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(state);
            CREATE INDEX IF NOT EXISTS idx_contributions_session ON contributions(session_id);
            CREATE INDEX IF NOT EXISTS idx_receipts_session ON organ_receipts(session_id);
            """)
            self._conn.execute("PRAGMA user_version = 1")

    def create_session(self, session: dict[str, Any]) -> dict[str, Any]:
        sid = session["session_id"]
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, objective, objective_hash, state, story, profile_set, created_at, updated_at, fixture_mode) VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, session.get("objective", ""), session.get("objective_hash", ""),
             session.get("state", "CREATED"), session.get("story", "hairstylist"),
             json.dumps(session.get("profile_set", {})),
             session.get("created_at", time.time()), time.time(),
             1 if session.get("fixture_mode", True) else 0)
        )
        # Store key session fields in session_data
        for key in ("contributions", "match_results", "workstreams", "scenarios",
                     "legal_instruments", "council_items", "consent_arc", "consent_responses",
                     "systemic_context", "democratic_friction", "what_if", "pilot",
                     "decision_packet", "organ_receipts", "needs", "offers",
                     "what_if_changes", "selected_scenario_id", "mandatory_constraints",
                     "map_manifest", "music_comparison"):
            if key in session:
                self._conn.execute(
                    "INSERT OR REPLACE INTO session_data (session_id, key, value) VALUES (?,?,?)",
                    (sid, key, json.dumps(session[key]))
                )
        self._log_audit(sid, "session_created", {"objective": session.get("objective", "")})
        return {"ok": True, "session_id": sid}

    def get_session(self, session_id: str) -> dict[str, Any]:
        row = self._conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"session not found: {session_id}"}
        session = {
            "session_id": row["session_id"],
            "objective": row["objective"],
            "objective_hash": row["objective_hash"],
            "state": row["state"],
            "story": row["story"],
            "profile_set": json.loads(row["profile_set"] or "{}"),
            "created_at": row["created_at"],
            "fixture_mode": bool(row["fixture_mode"]),
        }
        # Load session_data fields
        data_rows = self._conn.execute("SELECT key, value FROM session_data WHERE session_id = ?", (session_id,)).fetchall()
        for dr in data_rows:
            session[dr["key"]] = json.loads(dr["value"])
        # Load organ receipts
        receipt_rows = self._conn.execute("SELECT * FROM organ_receipts WHERE session_id = ?", (session_id,)).fetchall()
        session["organ_receipts"] = [
            {"organ_type": r["organ_type"], "organ_id": r["organ_id"],
             "manifest_digest": r["manifest_digest"], "ok": bool(r["ok"]),
             "executed_at": r["executed_at"]}
            for r in receipt_rows
        ]
        return {"ok": True, "session": session}

    def update_session(self, session_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        # Update top-level fields
        if "state" in updates:
            self._conn.execute("UPDATE sessions SET state = ?, updated_at = ? WHERE session_id = ?",
                              (updates["state"], time.time(), session_id))
        if "story" in updates:
            self._conn.execute("UPDATE sessions SET story = ? WHERE session_id = ?",
                              (updates["story"], session_id))
        if "profile_set" in updates:
            self._conn.execute("UPDATE sessions SET profile_set = ? WHERE session_id = ?",
                              (json.dumps(updates["profile_set"]), session_id))
        # Store other fields in session_data
        for key, value in updates.items():
            if key in ("state", "story", "profile_set", "_last_delta"):
                continue
            self._conn.execute(
                "INSERT OR REPLACE INTO session_data (session_id, key, value) VALUES (?,?,?)",
                (session_id, key, json.dumps(value))
            )
        # Record organ receipts
        if "organ_receipts" in updates:
            for receipt in updates["organ_receipts"]:
                self._conn.execute(
                    "INSERT INTO organ_receipts (session_id, organ_type, organ_id, manifest_digest, ok, executed_at) VALUES (?,?,?,?,?,?)",
                    (session_id, receipt.get("organ_type", ""), receipt.get("organ_id", ""),
                     receipt.get("manifest_digest", ""), 1 if receipt.get("ok") else 0,
                     receipt.get("executed_at", time.time()))
                )
        return {"ok": True}

    def _log_audit(self, session_id: str, event_type: str, data: dict[str, Any]):
        self._conn.execute(
            "INSERT INTO audit_events (session_id, event_type, data, created_at) VALUES (?,?,?,?)",
            (session_id, event_type, json.dumps(data), time.time())
        )

    def list_sessions(self) -> dict[str, Any]:
        rows = self._conn.execute("SELECT session_id, objective, state, story, created_at FROM sessions ORDER BY created_at DESC").fetchall()
        return {"ok": True, "sessions": [dict(r) for r in rows]}

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    @classmethod
    def for_tests(cls, tmp_path: str) -> "CivicSessionStore":
        """Create a test-isolated store."""
        db = Path(tmp_path) / "test_civic_sessions.sqlite3"
        return cls(str(db))

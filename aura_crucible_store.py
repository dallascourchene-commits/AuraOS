"""Persistent pause/resume, run, and proposal store for the Arena Crucible."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any

from aura_crucible_types import CRYSTALLIZATION_PROPOSED, CrystallizationProposal, PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, canonical_digest

CRUCIBLE_STORE_VERSION = "AURA_CRUCIBLE_STORE_V1"
_SCHEMA_VERSION = 1
_SCHEMA = """
CREATE TABLE IF NOT EXISTS crucible_control (
    control_id INTEGER PRIMARY KEY CHECK(control_id = 1),
    paused INTEGER NOT NULL,
    pause_reason TEXT NOT NULL,
    updated_at REAL NOT NULL
);
INSERT OR IGNORE INTO crucible_control(control_id, paused, pause_reason, updated_at) VALUES (1, 0, '', 0);
CREATE TABLE IF NOT EXISTS crucible_runs (
    run_id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    completed_at REAL NOT NULL,
    status TEXT NOT NULL,
    arena_id TEXT NOT NULL,
    source_record_count INTEGER NOT NULL,
    candidate_count INTEGER NOT NULL,
    proposal_count INTEGER NOT NULL,
    policy_json TEXT NOT NULL,
    report_json TEXT NOT NULL,
    run_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS crystallization_proposals (
    proposal_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status = 'CRYSTALLIZATION_PROPOSED'),
    arena_id TEXT NOT NULL,
    grammar_version TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    manifest_digest TEXT NOT NULL,
    transition_id TEXT NOT NULL,
    proposal_json TEXT NOT NULL,
    proposal_digest TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_crucible_proposal_run ON crystallization_proposals(run_id);
CREATE INDEX IF NOT EXISTS idx_crucible_proposal_target ON crystallization_proposals(arena_id, grammar_version, transition_id);
CREATE TABLE IF NOT EXISTS crucible_migrations (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);
"""


class CrucibleStore:
    """SQLite WAL store that contains proposals but no promotion operation."""

    def __init__(self, repo_root: str | Path = ".", *, db_path: str | Path | None = None) -> None:
        root = Path(repo_root).resolve()
        self.db_path = Path(db_path).resolve() if db_path is not None else root / "Aura_Memory" / "arena_crucible.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(_SCHEMA)
        self._conn.execute("INSERT OR IGNORE INTO crucible_migrations(version, applied_at) VALUES (?, ?)", (_SCHEMA_VERSION, time.time()))
        self._conn.commit()

    def pause(self, reason: str = "operator_pause") -> dict[str, Any]:
        now = time.time()
        self._conn.execute("UPDATE crucible_control SET paused = 1, pause_reason = ?, updated_at = ? WHERE control_id = 1", (str(reason or "operator_pause"), now))
        self._conn.commit()
        return self.control_status()

    def resume(self) -> dict[str, Any]:
        now = time.time()
        self._conn.execute("UPDATE crucible_control SET paused = 0, pause_reason = '', updated_at = ? WHERE control_id = 1", (now,))
        self._conn.commit()
        return self.control_status()

    def control_status(self) -> dict[str, Any]:
        row = self._conn.execute("SELECT paused, pause_reason, updated_at FROM crucible_control WHERE control_id = 1").fetchone()
        return {
            "ok": True,
            "paused": bool(row["paused"]),
            "pause_reason": str(row["pause_reason"] or ""),
            "updated_at": float(row["updated_at"] or 0.0),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_grammar_promotion": False,
        }

    def record_run(self, report: dict[str, Any]) -> dict[str, Any]:
        raw = dict(report or {})
        run_id = str(raw.get("run_id") or "")
        if not run_id:
            return _denial("run_id_required")
        digest = canonical_digest(raw)
        existing = self._conn.execute("SELECT run_digest FROM crucible_runs WHERE run_id = ?", (run_id,)).fetchone()
        if existing:
            if existing["run_digest"] == digest:
                return {"ok": True, "run_id": run_id, "run_digest": digest, "idempotent_replay": True}
            return _denial("run_id_digest_conflict", run_id=run_id)
        try:
            self._conn.execute(
                """INSERT INTO crucible_runs(run_id, started_at, completed_at, status, arena_id,
                   source_record_count, candidate_count, proposal_count, policy_json, report_json, run_digest)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    float(raw.get("started_at") or 0.0),
                    float(raw.get("completed_at") or 0.0),
                    str(raw.get("status") or ""),
                    str(raw.get("arena_id") or ""),
                    int(raw.get("source_record_count") or 0),
                    int(raw.get("candidate_count") or 0),
                    int(raw.get("proposal_count") or 0),
                    _json(raw.get("policy") or {}),
                    _json(raw),
                    digest,
                ),
            )
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            return _denial(f"database_write_failed:{type(exc).__name__}", run_id=run_id)
        return {"ok": True, "run_id": run_id, "run_digest": digest, "idempotent_replay": False}

    def record_proposal(self, proposal: CrystallizationProposal | dict[str, Any]) -> dict[str, Any]:
        raw = proposal.to_dict() if isinstance(proposal, CrystallizationProposal) else dict(proposal or {})
        if str(raw.get("status") or "") != CRYSTALLIZATION_PROPOSED:
            return _denial("invalid_proposal_status")
        proposal_id = str(raw.get("proposal_id") or "")
        required = ("run_id", "candidate_id", "arena_id", "grammar_version", "manifest_path", "manifest_digest", "transition_id")
        missing = [key for key in required if not str(raw.get(key) or "")]
        if not proposal_id or missing:
            return _denial("missing_proposal_fields", missing=missing + ([] if proposal_id else ["proposal_id"]))
        body = {key: value for key, value in raw.items() if key != "proposal_digest"}
        digest = canonical_digest(body)
        existing = self._conn.execute("SELECT proposal_digest FROM crystallization_proposals WHERE proposal_id = ?", (proposal_id,)).fetchone()
        if existing:
            if existing["proposal_digest"] == digest:
                return {"ok": True, "proposal_id": proposal_id, "proposal_digest": digest, "idempotent_replay": True}
            return _denial("proposal_id_digest_conflict", proposal_id=proposal_id)
        try:
            self._conn.execute(
                """INSERT INTO crystallization_proposals(proposal_id, run_id, candidate_id, status,
                   arena_id, grammar_version, manifest_path, manifest_digest, transition_id,
                   proposal_json, proposal_digest, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    proposal_id,
                    str(raw["run_id"]),
                    str(raw["candidate_id"]),
                    CRYSTALLIZATION_PROPOSED,
                    str(raw["arena_id"]),
                    str(raw["grammar_version"]),
                    str(raw["manifest_path"]),
                    str(raw["manifest_digest"]),
                    str(raw["transition_id"]),
                    _json(body),
                    digest,
                    float(raw.get("created_at") or time.time()),
                ),
            )
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            return _denial(f"database_write_failed:{type(exc).__name__}", proposal_id=proposal_id)
        return {"ok": True, "proposal_id": proposal_id, "proposal_digest": digest, "idempotent_replay": False}

    def get_proposal_by_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        """Return the existing proposal for an identical deterministic candidate."""

        row = self._conn.execute(
            "SELECT proposal_json, proposal_digest FROM crystallization_proposals WHERE candidate_id = ? ORDER BY created_at ASC LIMIT 1",
            (str(candidate_id),),
        ).fetchone()
        if not row:
            return None
        data = json.loads(row["proposal_json"])
        data["proposal_digest"] = row["proposal_digest"]
        return data

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT proposal_json, proposal_digest FROM crystallization_proposals WHERE proposal_id = ?", (str(proposal_id),)).fetchone()
        if not row:
            return None
        data = json.loads(row["proposal_json"])
        data["proposal_digest"] = row["proposal_digest"]
        return data

    def list_proposals(self, *, arena_id: str = "", limit: int = 50) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = ""
        if arena_id:
            where = "WHERE arena_id = ?"
            params.append(arena_id)
        params.append(max(1, min(int(limit), 1000)))
        rows = self._conn.execute(
            f"SELECT proposal_json, proposal_digest FROM crystallization_proposals {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        output = []
        for row in rows:
            data = json.loads(row["proposal_json"])
            data["proposal_digest"] = row["proposal_digest"]
            output.append(data)
        return output

    def status(self) -> dict[str, Any]:
        control = self.control_status()
        run_count = int(self._conn.execute("SELECT COUNT(*) FROM crucible_runs").fetchone()[0])
        proposal_count = int(self._conn.execute("SELECT COUNT(*) FROM crystallization_proposals").fetchone()[0])
        journal_mode = str(self._conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        return {
            **control,
            "version": CRUCIBLE_STORE_VERSION,
            "schema_version": _SCHEMA_VERSION,
            "db_path": str(self.db_path),
            "journal_mode": journal_mode,
            "run_count": run_count,
            "proposal_count": proposal_count,
            "terminal_proposal_status": CRYSTALLIZATION_PROPOSED,
        }

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "CrucibleStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _denial(reason: str, *, missing: list[str] | None = None, proposal_id: str = "", run_id: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "missing": list(missing or []),
        "proposal_id": proposal_id,
        "run_id": run_id,
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

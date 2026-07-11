"""Persistent SQLite WAL ledger for structured Aura Arena experiences."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any

from aura_arena_experience import ARENA_EXPERIENCE_VERSION, ArenaExperience, canonical_experience_digest, sanitize_experience_payload

ARENA_EXPERIENCE_LEDGER_VERSION = "AURA_ARENA_EXPERIENCE_LEDGER_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS arena_experiences (
    experience_id TEXT PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    task_id TEXT,
    workflow_id TEXT,
    arena_id TEXT NOT NULL,
    arena_version TEXT NOT NULL,
    grammar_version TEXT NOT NULL,
    runtime_version TEXT NOT NULL,
    compiler_version TEXT NOT NULL,
    started_at REAL NOT NULL,
    completed_at REAL NOT NULL,
    state_before TEXT NOT NULL,
    state_after TEXT NOT NULL,
    selected_transition TEXT,
    final_outcome TEXT NOT NULL,
    repository_commit_sha TEXT,
    working_tree_digest TEXT,
    objective_hash TEXT,
    source_hash_digest TEXT,
    provider TEXT,
    model TEXT,
    measurement_class TEXT,
    cost_run_id TEXT,
    trace_atom_ids_json TEXT NOT NULL,
    raw_evidence_refs_json TEXT NOT NULL,
    redactions_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    experience_digest TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experience_arena_state ON arena_experiences(arena_id, state_before, selected_transition);
CREATE INDEX IF NOT EXISTS idx_experience_task ON arena_experiences(task_id);
CREATE INDEX IF NOT EXISTS idx_experience_correlation ON arena_experiences(correlation_id);
CREATE INDEX IF NOT EXISTS idx_experience_commit ON arena_experiences(repository_commit_sha);
CREATE INDEX IF NOT EXISTS idx_experience_outcome ON arena_experiences(final_outcome);
CREATE TABLE IF NOT EXISTS arena_experience_migrations (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);
"""


class ArenaExperienceLedger:
    def __init__(self, repo_root: str | Path = ".", *, db_path: str | Path | None = None) -> None:
        root = Path(repo_root).resolve()
        self.db_path = Path(db_path).resolve() if db_path is not None else root / "Aura_Memory" / "arena_experience.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        row = self._conn.execute("SELECT MAX(version) AS version FROM arena_experience_migrations").fetchone()
        current = int(row["version"] or 0) if row else 0
        if current < _SCHEMA_VERSION:
            self._conn.execute(
                "INSERT OR REPLACE INTO arena_experience_migrations(version, applied_at) VALUES (?, ?)",
                (_SCHEMA_VERSION, time.time()),
            )

    def record(self, experience: ArenaExperience | dict[str, Any]) -> dict[str, Any]:
        raw = experience.to_dict() if isinstance(experience, ArenaExperience) else dict(experience)
        sanitized_payload, defensive_redactions = sanitize_experience_payload(raw.get("payload") or {})
        raw["payload"] = sanitized_payload
        existing_redactions = [str(item) for item in raw.get("redactions", []) or []]
        raw["redactions"] = sorted(set((*existing_redactions, *defensive_redactions)))
        raw.setdefault("version", ARENA_EXPERIENCE_VERSION)
        required = (
            "experience_id", "correlation_id", "arena_id", "arena_version",
            "grammar_version", "runtime_version", "compiler_version",
            "state_before", "state_after", "final_outcome",
        )
        missing = [key for key in required if not str(raw.get(key) or "").strip()]
        if missing:
            return _denial("missing_required_fields", missing=missing)
        try:
            started_at = float(raw.get("started_at"))
            completed_at = float(raw.get("completed_at"))
        except (TypeError, ValueError):
            return _denial("invalid_timestamps")
        if completed_at < started_at:
            return _denial("completed_before_started")

        digest = canonical_experience_digest(raw)
        experience_id = str(raw["experience_id"])
        existing = self._conn.execute(
            "SELECT experience_digest FROM arena_experiences WHERE experience_id = ?",
            (experience_id,),
        ).fetchone()
        if existing:
            if existing["experience_digest"] == digest:
                return {
                    "ok": True,
                    "experience_id": experience_id,
                    "experience_digest": digest,
                    "idempotent_replay": True,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                }
            return _denial("experience_id_digest_conflict", experience_id=experience_id)

        try:
            self._conn.execute(
                """INSERT INTO arena_experiences (
                    experience_id, correlation_id, task_id, workflow_id, arena_id,
                    arena_version, grammar_version, runtime_version, compiler_version,
                    started_at, completed_at, state_before, state_after,
                    selected_transition, final_outcome, repository_commit_sha,
                    working_tree_digest, objective_hash, source_hash_digest,
                    provider, model, measurement_class, cost_run_id,
                    trace_atom_ids_json, raw_evidence_refs_json, redactions_json,
                    payload_json, experience_digest, schema_version, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    experience_id,
                    str(raw.get("correlation_id") or ""),
                    str(raw.get("task_id") or ""),
                    str(raw.get("workflow_id") or ""),
                    str(raw.get("arena_id") or ""),
                    str(raw.get("arena_version") or ""),
                    str(raw.get("grammar_version") or ""),
                    str(raw.get("runtime_version") or ""),
                    str(raw.get("compiler_version") or ""),
                    started_at,
                    completed_at,
                    str(raw.get("state_before") or ""),
                    str(raw.get("state_after") or ""),
                    str(raw.get("selected_transition") or ""),
                    str(raw.get("final_outcome") or ""),
                    str(raw.get("repository_commit_sha") or ""),
                    str(raw.get("working_tree_digest") or ""),
                    str(raw.get("objective_hash") or ""),
                    str(raw.get("source_hash_digest") or ""),
                    str(raw.get("provider") or ""),
                    str(raw.get("model") or ""),
                    str(raw.get("measurement_class") or "UNAVAILABLE"),
                    str(raw.get("cost_run_id") or ""),
                    _json(raw.get("trace_atom_ids") or []),
                    _json(raw.get("raw_evidence_refs") or []),
                    _json(raw.get("redactions") or []),
                    _json(raw.get("payload") or {}),
                    digest,
                    str(raw.get("version") or ARENA_EXPERIENCE_VERSION),
                    time.time(),
                ),
            )
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            return _denial(f"database_write_failed:{type(exc).__name__}")
        return {
            "ok": True,
            "experience_id": experience_id,
            "experience_digest": digest,
            "idempotent_replay": False,
            "redactions": list(raw.get("redactions") or []),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def get(self, experience_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM arena_experiences WHERE experience_id = ?",
            (str(experience_id),),
        ).fetchone()
        return _decode_row(row) if row else None

    def history(self, *, arena_id: str = "", task_id: str = "", limit: int = 50) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if arena_id:
            clauses.append("arena_id = ?")
            params.append(arena_id)
        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(int(limit), 1000)))
        rows = self._conn.execute(
            f"SELECT * FROM arena_experiences {where} ORDER BY completed_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_decode_row(row) for row in rows]

    def export_jsonl(self, path: str | Path, *, arena_id: str = "", limit: int = 10000) -> dict[str, Any]:
        rows = self.history(arena_id=arena_id, limit=limit)
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            for row in reversed(rows):
                handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True, default=str) + "\n")
        return {
            "ok": True,
            "path": str(output),
            "record_count": len(rows),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def status(self) -> dict[str, Any]:
        journal_mode = self._conn.execute("PRAGMA journal_mode;").fetchone()[0]
        count = self._conn.execute("SELECT COUNT(*) FROM arena_experiences").fetchone()[0]
        return {
            "ok": True,
            "version": ARENA_EXPERIENCE_LEDGER_VERSION,
            "schema_version": _SCHEMA_VERSION,
            "db_path": str(self.db_path),
            "journal_mode": str(journal_mode).lower(),
            "record_count": int(count),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()

    def __enter__(self) -> "ArenaExperienceLedger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for key in ("trace_atom_ids_json", "raw_evidence_refs_json", "redactions_json", "payload_json"):
        value = data.pop(key, "")
        output_key = key.removesuffix("_json")
        try:
            data[output_key] = json.loads(value) if value else ([] if output_key != "payload" else {})
        except json.JSONDecodeError:
            data[output_key] = [] if output_key != "payload" else {}
    data["version"] = data.pop("schema_version", ARENA_EXPERIENCE_VERSION)
    data["patch_authority"] = PATCH_AUTHORITY
    data["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
    data["learned_weight_patch_authority"] = False
    data["crystallization_patch_authority"] = False
    return data


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _denial(reason: str, *, missing: list[str] | None = None, experience_id: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "missing": list(missing or []),
        "experience_id": experience_id,
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

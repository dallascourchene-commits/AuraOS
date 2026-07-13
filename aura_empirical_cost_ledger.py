"""Aura Empirical Cost Ledger — linked SQLite telemetry with migrations.

Every run preserves model/call/route/task/experience linkage, normalized usage,
versioned pricing evidence, stage latency, verification, repair, and fallback
burden. Missing measurements remain SQL NULL.

Dependencies: stdlib only (sqlite3, json, re, secrets, time, pathlib).
"""
from __future__ import annotations

import json
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
LEDGER_VERSION = "AURA_EMPIRICAL_COST_LEDGER_V2"
_SCHEMA_VERSION = 2

_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|secret|password|authorization|credential|access[_-]?token|refresh[_-]?token|private[_-]?key)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"sk-[a-zA-Z0-9_-]+|gh[opusr]_[a-zA-Z0-9]+|Bearer\s+[a-zA-Z0-9._~+/-]+=*",
    re.IGNORECASE,
)

_COLUMNS = (
    "run_id",
    "comparison_id",
    "parent_run_id",
    "task_id",
    "arena_id",
    "plan_phase_hash",
    "repository_commit_sha",
    "working_tree_digest",
    "objective_hash",
    "mode",
    "provider",
    "model",
    "measurement_class",
    "started_at",
    "completed_at",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_creation_tokens",
    "reasoning_tokens",
    "estimated_input_tokens",
    "estimated_output_tokens",
    "provider_cost_usd",
    "calculated_cost_usd",
    "latency_ms",
    "time_to_first_token_ms",
    "model_call_count",
    "tool_call_count",
    "files_exposed",
    "symbols_exposed",
    "source_lines_exposed",
    "source_chars_exposed",
    "context_bytes_before",
    "context_bytes_after",
    "patch_id",
    "patch_lines_added",
    "patch_lines_removed",
    "tests_run",
    "tests_passed",
    "tests_failed",
    "verification_status",
    "scope_violation_count",
    "repair_attempt_count",
    "human_intervention_count",
    "human_review_status",
    "quality_score",
    "confidence_class",
    "telemetry_warnings",
    "price_snapshot",
    "created_at",
    # V2 linkage and timing fields.
    "correlation_id",
    "route_decision_id",
    "task_context_id",
    "profile_id",
    "call_id",
    "observation_id",
    "experience_id",
    "time_to_verified_outcome_ms",
    "queue_ms",
    "connect_ms",
    "generation_ms",
    "tool_execution_ms",
    "verifier_ms",
    "retry_ms",
    "fallback_ms",
    "human_wait_ms",
    "cost_status",
    "price_snapshot_digest",
    "field_measurement_classes",
)

_JSON_COLUMNS = frozenset({
    "telemetry_warnings",
    "price_snapshot",
    "field_measurement_classes",
})

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS cost_runs (
    run_id TEXT PRIMARY KEY,
    comparison_id TEXT NOT NULL,
    parent_run_id TEXT,
    task_id TEXT,
    arena_id TEXT,
    plan_phase_hash TEXT,
    repository_commit_sha TEXT,
    working_tree_digest TEXT,
    objective_hash TEXT,
    mode TEXT,
    provider TEXT,
    model TEXT,
    measurement_class TEXT,
    started_at REAL,
    completed_at REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cached_input_tokens INTEGER,
    cache_creation_tokens INTEGER,
    reasoning_tokens INTEGER,
    estimated_input_tokens INTEGER,
    estimated_output_tokens INTEGER,
    provider_cost_usd REAL,
    calculated_cost_usd REAL,
    latency_ms REAL,
    time_to_first_token_ms REAL,
    model_call_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    files_exposed INTEGER,
    symbols_exposed INTEGER,
    source_lines_exposed INTEGER,
    source_chars_exposed INTEGER,
    context_bytes_before INTEGER,
    context_bytes_after INTEGER,
    patch_id TEXT,
    patch_lines_added INTEGER,
    patch_lines_removed INTEGER,
    tests_run INTEGER,
    tests_passed INTEGER,
    tests_failed INTEGER,
    verification_status TEXT,
    scope_violation_count INTEGER DEFAULT 0,
    repair_attempt_count INTEGER DEFAULT 0,
    human_intervention_count INTEGER DEFAULT 0,
    human_review_status TEXT,
    quality_score REAL,
    confidence_class TEXT,
    telemetry_warnings TEXT,
    price_snapshot TEXT,
    created_at REAL DEFAULT 0,
    correlation_id TEXT,
    route_decision_id TEXT,
    task_context_id TEXT,
    profile_id TEXT,
    call_id TEXT,
    observation_id TEXT,
    experience_id TEXT,
    time_to_verified_outcome_ms REAL,
    queue_ms REAL,
    connect_ms REAL,
    generation_ms REAL,
    tool_execution_ms REAL,
    verifier_ms REAL,
    retry_ms REAL,
    fallback_ms REAL,
    human_wait_ms REAL,
    cost_status TEXT,
    price_snapshot_digest TEXT,
    field_measurement_classes TEXT
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);
"""

_V2_COLUMNS = {
    "correlation_id": "TEXT",
    "route_decision_id": "TEXT",
    "task_context_id": "TEXT",
    "profile_id": "TEXT",
    "call_id": "TEXT",
    "observation_id": "TEXT",
    "experience_id": "TEXT",
    "time_to_verified_outcome_ms": "REAL",
    "queue_ms": "REAL",
    "connect_ms": "REAL",
    "generation_ms": "REAL",
    "tool_execution_ms": "REAL",
    "verifier_ms": "REAL",
    "retry_ms": "REAL",
    "fallback_ms": "REAL",
    "human_wait_ms": "REAL",
    "cost_status": "TEXT",
    "price_snapshot_digest": "TEXT",
    "field_measurement_classes": "TEXT",
}


def _db_path(repo_root: str | Path = ".") -> Path:
    root = Path(repo_root).resolve()
    memory = root / "Aura_Memory"
    memory.mkdir(parents=True, exist_ok=True)
    return memory / "empirical_cost_ledger.db"


def _sanitize(value: Any, *, key: str = "") -> Any:
    if _SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): _sanitize(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    return value


def _serialize(column: str, value: Any) -> Any:
    if column not in _JSON_COLUMNS:
        return value
    if value is None:
        return None
    return json.dumps(_sanitize(value), sort_keys=True, separators=(",", ":"))


def _deserialize_row(row: sqlite3.Row | tuple[Any, ...], columns: list[str]) -> dict[str, Any]:
    result = dict(zip(columns, row))
    for column in _JSON_COLUMNS:
        value = result.get(column)
        if isinstance(value, str):
            try:
                result[column] = json.loads(value)
            except json.JSONDecodeError:
                pass
    result["patch_authority"] = PATCH_AUTHORITY
    result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
    result["ledger_version"] = LEDGER_VERSION
    return result


class EmpiricalCostLedger:
    """Local WAL ledger for empirical cost, linkage, and stage timing evidence."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.db_path = _db_path(repo_root)
        self._conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_CREATE_TABLES)
        self._migrate()
        self._conn.commit()

    def _columns(self) -> set[str]:
        assert self._conn is not None
        return {str(row[1]) for row in self._conn.execute("PRAGMA table_info(cost_runs)")}

    def _migrate(self) -> None:
        assert self._conn is not None
        columns = self._columns()
        for name, declaration in _V2_COLUMNS.items():
            if name not in columns:
                self._conn.execute(f"ALTER TABLE cost_runs ADD COLUMN {name} {declaration}")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_comparison ON cost_runs(comparison_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_provider ON cost_runs(provider)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON cost_runs(model)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_call_id ON cost_runs(call_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_observation_id ON cost_runs(observation_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_route_decision_id ON cost_runs(route_decision_id)")
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES(?, ?)",
            (_SCHEMA_VERSION, time.time()),
        )

    def schema_status(self) -> dict[str, Any]:
        assert self._conn is not None
        version = self._conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        return {
            "ok": True,
            "ledger_version": LEDGER_VERSION,
            "schema_version": int(version),
            "journal_mode": str(self._conn.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
            "columns": sorted(self._columns()),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def record_run(self, run: dict[str, Any]) -> dict[str, Any]:
        """Record or idempotently replace one linked empirical run."""
        assert self._conn is not None
        clean = _sanitize(dict(run))
        run_id = str(clean.get("run_id") or secrets.token_hex(12))
        clean["run_id"] = run_id
        clean["comparison_id"] = str(clean.get("comparison_id") or "")
        clean.setdefault("model_call_count", 0)
        clean.setdefault("tool_call_count", 0)
        clean.setdefault("scope_violation_count", 0)
        clean.setdefault("repair_attempt_count", 0)
        clean.setdefault("human_intervention_count", 0)
        clean.setdefault("created_at", time.time())
        values = [_serialize(column, clean.get(column)) for column in _COLUMNS]
        placeholders = ",".join("?" for _ in _COLUMNS)
        columns_sql = ",".join(_COLUMNS)
        with self._conn:
            self._conn.execute(
                f"INSERT OR REPLACE INTO cost_runs({columns_sql}) VALUES({placeholders})",
                values,
            )
        return {
            "ok": True,
            "run_id": run_id,
            "call_id": clean.get("call_id"),
            "observation_id": clean.get("observation_id"),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        assert self._conn is not None
        cursor = self._conn.execute("SELECT * FROM cost_runs WHERE run_id=?", (run_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return _deserialize_row(row, [item[0] for item in cursor.description])

    def get_comparison(self, comparison_id: str) -> list[dict[str, Any]]:
        assert self._conn is not None
        cursor = self._conn.execute(
            "SELECT * FROM cost_runs WHERE comparison_id=? ORDER BY started_at, created_at",
            (comparison_id,),
        )
        columns = [item[0] for item in cursor.description]
        return [_deserialize_row(row, columns) for row in cursor.fetchall()]

    def get_by_call_id(self, call_id: str) -> list[dict[str, Any]]:
        assert self._conn is not None
        cursor = self._conn.execute(
            "SELECT * FROM cost_runs WHERE call_id=? ORDER BY created_at",
            (call_id,),
        )
        columns = [item[0] for item in cursor.description]
        return [_deserialize_row(row, columns) for row in cursor.fetchall()]

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        assert self._conn is not None
        cursor = self._conn.execute(
            "SELECT run_id, comparison_id, correlation_id, call_id, observation_id, "
            "route_decision_id, profile_id, provider, model, measurement_class, "
            "input_tokens, output_tokens, provider_cost_usd, calculated_cost_usd, "
            "cost_status, latency_ms, time_to_verified_outcome_ms, verification_status, created_at "
            "FROM cost_runs ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        )
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "EmpiricalCostLedger":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

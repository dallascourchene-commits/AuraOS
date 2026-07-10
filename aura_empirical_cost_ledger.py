"""
Aura Empirical Cost Ledger — SQLite persistent ledger with WAL mode and migrations.

Every run persists: run_id, comparison_id, provider, model, measurement_class,
tokens, cost, latency, source exposure, verification status, quality, confidence.

Dependencies: stdlib only (sqlite3, json, hashlib, time, pathlib).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
LEDGER_VERSION = "AURA_EMPIRICAL_COST_LEDGER_V1"

_SCHEMA_VERSION = 1

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
    created_at REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at REAL
);

CREATE INDEX IF NOT EXISTS idx_comparison ON cost_runs(comparison_id);
CREATE INDEX IF NOT EXISTS idx_provider ON cost_runs(provider);
CREATE INDEX IF NOT EXISTS idx_model ON cost_runs(model);
"""


def _db_path(repo_root: str | Path = ".") -> Path:
    root = Path(repo_root).resolve()
    mem_dir = root / "Aura_Memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    return mem_dir / "empirical_cost_ledger.db"


class EmpiricalCostLedger:
    """SQLite persistent ledger for empirical cost measurements."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.db_path = _db_path(repo_root)
        self._conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.executescript(_CREATE_TABLES)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Run schema migrations."""
        cursor = self._conn.execute("SELECT MAX(version) FROM schema_migrations")
        row = cursor.fetchone()
        current = row[0] if row and row[0] else 0
        if current < _SCHEMA_VERSION:
            self._conn.execute(
                "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (_SCHEMA_VERSION, time.time())
            )
            self._conn.commit()

    def record_run(self, run: dict[str, Any]) -> dict[str, Any]:
        """Record a cost run in the ledger."""
        run_id = run.get("run_id") or hashlib.blake2b(
            f"{run.get('comparison_id','')}{time.time()}".encode(), digest_size=12
        ).hexdigest()

        # Serialize complex fields
        warnings = run.get("telemetry_warnings", [])
        if isinstance(warnings, list):
            warnings = json.dumps(warnings)
        price_snap = run.get("price_snapshot")
        if isinstance(price_snap, dict):
            price_snap = json.dumps(price_snap)

        self._conn.execute(
            """INSERT OR REPLACE INTO cost_runs (
                run_id, comparison_id, parent_run_id, task_id, arena_id,
                plan_phase_hash, repository_commit_sha, working_tree_digest,
                objective_hash, mode, provider, model, measurement_class,
                started_at, completed_at, input_tokens, output_tokens,
                cached_input_tokens, cache_creation_tokens, reasoning_tokens,
                estimated_input_tokens, estimated_output_tokens,
                provider_cost_usd, calculated_cost_usd, latency_ms,
                time_to_first_token_ms, model_call_count, tool_call_count,
                files_exposed, symbols_exposed, source_lines_exposed,
                source_chars_exposed, context_bytes_before, context_bytes_after,
                patch_id, patch_lines_added, patch_lines_removed,
                tests_run, tests_passed, tests_failed, verification_status,
                scope_violation_count, repair_attempt_count,
                human_intervention_count, human_review_status,
                quality_score, confidence_class, telemetry_warnings,
                price_snapshot, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, run.get("comparison_id", ""), run.get("parent_run_id"),
                run.get("task_id"), run.get("arena_id"), run.get("plan_phase_hash"),
                run.get("repository_commit_sha"), run.get("working_tree_digest"),
                run.get("objective_hash"), run.get("mode"), run.get("provider"),
                run.get("model"), run.get("measurement_class"),
                run.get("started_at", time.time()), run.get("completed_at"),
                run.get("input_tokens"), run.get("output_tokens"),
                run.get("cached_input_tokens"), run.get("cache_creation_tokens"),
                run.get("reasoning_tokens"),
                run.get("estimated_input_tokens"), run.get("estimated_output_tokens"),
                run.get("provider_cost_usd"), run.get("calculated_cost_usd"),
                run.get("latency_ms"), run.get("time_to_first_token_ms"),
                run.get("model_call_count", 0), run.get("tool_call_count", 0),
                run.get("files_exposed"), run.get("symbols_exposed"),
                run.get("source_lines_exposed"), run.get("source_chars_exposed"),
                run.get("context_bytes_before"), run.get("context_bytes_after"),
                run.get("patch_id"), run.get("patch_lines_added"),
                run.get("patch_lines_removed"),
                run.get("tests_run"), run.get("tests_passed"), run.get("tests_failed"),
                run.get("verification_status"),
                run.get("scope_violation_count", 0), run.get("repair_attempt_count", 0),
                run.get("human_intervention_count", 0), run.get("human_review_status"),
                run.get("quality_score"), run.get("confidence_class"),
                warnings, price_snap, time.time(),
            )
        )
        self._conn.commit()
        return {"ok": True, "run_id": run_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve a run by ID."""
        cursor = self._conn.execute("SELECT * FROM cost_runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        result = dict(zip(cols, row))
        # Deserialize JSON fields
        for key in ("telemetry_warnings", "price_snapshot"):
            if result.get(key) and isinstance(result[key], str):
                try:
                    result[key] = json.loads(result[key])
                except Exception:
                    pass
        result["patch_authority"] = PATCH_AUTHORITY
        result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return result

    def get_comparison(self, comparison_id: str) -> list[dict[str, Any]]:
        """Get all runs in a comparison."""
        cursor = self._conn.execute(
            "SELECT * FROM cost_runs WHERE comparison_id = ? ORDER BY started_at",
            (comparison_id,)
        )
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        results = []
        for row in rows:
            r = dict(zip(cols, row))
            for key in ("telemetry_warnings", "price_snapshot"):
                if r.get(key) and isinstance(r[key], str):
                    try:
                        r[key] = json.loads(r[key])
                    except Exception:
                        pass
            r["patch_authority"] = PATCH_AUTHORITY
            r["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
            results.append(r)
        return results

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent runs."""
        cursor = self._conn.execute(
            "SELECT run_id, comparison_id, provider, model, measurement_class, "
            "input_tokens, output_tokens, calculated_cost_usd, verification_status, "
            "created_at FROM cost_runs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

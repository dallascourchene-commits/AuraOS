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
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
LEDGER_VERSION = "AURA_EMPIRICAL_COST_LEDGER_V1"

# Keys that should never be stored in the ledger
SECRET_KEYS = ["api_key", "secret", "token", "password"]

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
        # Filter out secret keys before storing
        filtered_run = {k: v for k, v in run.items() if k not in SECRET_KEYS}
        run_id = filtered_run.get("run_id") or secrets.token_hex(12)

        # Serialize complex fields and filter secrets from warning strings
        warnings = filtered_run.get("telemetry_warnings", [])
        if isinstance(warnings, list):
            # Filter out warnings containing secret patterns
            filtered_warnings = []
            for w in warnings:
                if isinstance(w, str):
                    # Remove warnings containing sk-* patterns and other secret-like strings
                    if not re.search(r'sk-[a-zA-Z0-9\-]+|api[_-]?key|secret|password', w, re.IGNORECASE):
                        filtered_warnings.append(w)
                else:
                    filtered_warnings.append(w)
            warnings = json.dumps(filtered_warnings)
        price_snap = filtered_run.get("price_snapshot")
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
                run_id, filtered_run.get("comparison_id", ""), filtered_run.get("parent_run_id"),
                filtered_run.get("task_id"), filtered_run.get("arena_id"), filtered_run.get("plan_phase_hash"),
                filtered_run.get("repository_commit_sha"), filtered_run.get("working_tree_digest"),
                filtered_run.get("objective_hash"), filtered_run.get("mode"), filtered_run.get("provider"),
                filtered_run.get("model"), filtered_run.get("measurement_class"),
                filtered_run.get("started_at", time.time()), filtered_run.get("completed_at"),
                filtered_run.get("input_tokens"), filtered_run.get("output_tokens"),
                filtered_run.get("cached_input_tokens"), filtered_run.get("cache_creation_tokens"),
                filtered_run.get("reasoning_tokens"),
                filtered_run.get("estimated_input_tokens"), filtered_run.get("estimated_output_tokens"),
                filtered_run.get("provider_cost_usd"), filtered_run.get("calculated_cost_usd"),
                filtered_run.get("latency_ms"), filtered_run.get("time_to_first_token_ms"),
                filtered_run.get("model_call_count", 0), filtered_run.get("tool_call_count", 0),
                filtered_run.get("files_exposed"), filtered_run.get("symbols_exposed"),
                filtered_run.get("source_lines_exposed"), filtered_run.get("source_chars_exposed"),
                filtered_run.get("context_bytes_before"), filtered_run.get("context_bytes_after"),
                filtered_run.get("patch_id"), filtered_run.get("patch_lines_added"),
                filtered_run.get("patch_lines_removed"),
                filtered_run.get("tests_run"), filtered_run.get("tests_passed"), filtered_run.get("tests_failed"),
                filtered_run.get("verification_status"),
                filtered_run.get("scope_violation_count", 0), filtered_run.get("repair_attempt_count", 0),
                filtered_run.get("human_intervention_count", 0), filtered_run.get("human_review_status"),
                filtered_run.get("quality_score"), filtered_run.get("confidence_class"),
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

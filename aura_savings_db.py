"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Honest Accounting)
DEPENDENCIES: sqlite3, os, time, json
FUNCTIONS: SavingsDB, log_call, query_savings, summary
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Savings Database — persistent, queryable record of every LLM call.
======================================================================

Every single external LLM call flows through `log_call()` which writes a
row to an append-only SQLite database. This is the source of truth for
the savings dashboard and all cost metrics.

The database lives at Aura_Memory/aura_savings.db and is created
automatically on first use.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Aura_Memory")
DB_PATH = os.path.join(MEMORY_DIR, "aura_savings.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS llm_calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,  -- ISO 8601 UTC
    ts_epoch    REAL    NOT NULL,  -- unix epoch float for time-series queries
    provider    TEXT    NOT NULL,
    model       TEXT    NOT NULL,
    call_type   TEXT    NOT NULL,  -- 'generate' | 'interpret'
    task        TEXT,              -- task key (mesh_offload, converse, etc.)
    aspect      TEXT,              -- conversation | refactor | self_optimize | ...
    prompt_tokens   INTEGER NOT NULL,
    output_tokens   INTEGER NOT NULL,
    cost_usd        REAL    NOT NULL,
    latency_sec     REAL    NOT NULL,
    baseline_prompt_tokens  INTEGER,  -- raw/non-aura token estimate
    baseline_output_tokens  INTEGER,  -- raw output estimate
    baseline_cost_usd       REAL,     -- what a naive call would cost
    tokens_saved    INTEGER NOT NULL DEFAULT 0,  -- baseline_prompt - prompt_tokens
    cost_saved_usd  REAL    NOT NULL DEFAULT 0.0,
    error           TEXT,              -- non-null if call failed
    metadata        TEXT               -- JSON blob for extra context
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_ts      ON llm_calls(ts_epoch);
CREATE INDEX IF NOT EXISTS idx_llm_calls_provider ON llm_calls(provider);
CREATE INDEX IF NOT EXISTS idx_llm_calls_type     ON llm_calls(call_type);
CREATE INDEX IF NOT EXISTS idx_llm_calls_task     ON llm_calls(task);
"""


def _ensure_dir() -> None:
    os.makedirs(MEMORY_DIR, exist_ok=True)


class SavingsDB:
    """Thread-safe(ish) append-only database for LLM call savings."""

    def __init__(self, db_path: str = DB_PATH):
        _ensure_dir()
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def log_call(self, *,
                 provider: str,
                 model: str,
                 call_type: str = "generate",
                 task: str | None = None,
                 aspect: str | None = None,
                 prompt_tokens: int,
                 output_tokens: int,
                 cost_usd: float,
                 latency_sec: float,
                 baseline_prompt_tokens: int | None = None,
                 baseline_output_tokens: int | None = None,
                 baseline_cost_usd: float | None = None,
                 error: str | None = None,
                 metadata: dict | None = None) -> int:
        """Log a single LLM call. Returns the row id."""
        now = time.time()
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

        # Compute savings
        tokens_saved = 0
        cost_saved = 0.0
        if baseline_prompt_tokens is not None:
            tokens_saved += (baseline_prompt_tokens - prompt_tokens)
        if baseline_output_tokens is not None:
            tokens_saved += (baseline_output_tokens - output_tokens)
        if baseline_cost_usd is not None:
            cost_saved = round(baseline_cost_usd - cost_usd, 6)

        meta_json = json.dumps(metadata or {}, default=str)

        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO llm_calls
                   (ts, ts_epoch, provider, model, call_type, task, aspect,
                    prompt_tokens, output_tokens, cost_usd, latency_sec,
                    baseline_prompt_tokens, baseline_output_tokens, baseline_cost_usd,
                    tokens_saved, cost_saved_usd, error, metadata)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ts, now, provider, model, call_type, task, aspect,
                 prompt_tokens, output_tokens, round(cost_usd, 6), round(latency_sec, 3),
                 baseline_prompt_tokens, baseline_output_tokens, baseline_cost_usd,
                 tokens_saved, cost_saved, error, meta_json),
            )
            conn.commit()
            return cur.lastrowid

    # ── query helpers ──────────────────────────────────────────────────── #

    def count(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0]

    def summary(self, *, days: int = 30) -> dict[str, Any]:
        """Aggregate savings summary for the dashboard."""
        cutoff = time.time() - days * 86400
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row

            # Overall stats
            overall = conn.execute(
                """SELECT
                    COUNT(*)                              AS total_calls,
                    COALESCE(SUM(prompt_tokens), 0)       AS total_prompt_tokens,
                    COALESCE(SUM(output_tokens), 0)       AS total_output_tokens,
                    COALESCE(SUM(cost_usd), 0)            AS total_cost_usd,
                    COALESCE(SUM(tokens_saved), 0)        AS total_tokens_saved,
                    COALESCE(SUM(cost_saved_usd), 0)      AS total_cost_saved_usd,
                    COALESCE(AVG(latency_sec), 0)         AS avg_latency_sec,
                    COALESCE(SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END), 0)
                                                          AS error_count
                FROM llm_calls
                WHERE ts_epoch >= ?""", (cutoff,)
            ).fetchone()

            # Per provider
            per_provider_rows = conn.execute(
                """SELECT
                    provider,
                    COUNT(*)                              AS calls,
                    COALESCE(SUM(prompt_tokens), 0)       AS prompt_tokens,
                    COALESCE(SUM(output_tokens), 0)       AS output_tokens,
                    COALESCE(SUM(cost_usd), 0)            AS cost_usd,
                    COALESCE(SUM(tokens_saved), 0)        AS tokens_saved,
                    COALESCE(SUM(cost_saved_usd), 0)      AS cost_saved_usd,
                    COALESCE(AVG(latency_sec), 0)         AS avg_latency_sec
                FROM llm_calls
                WHERE ts_epoch >= ?
                GROUP BY provider
                ORDER BY calls DESC""", (cutoff,)
            ).fetchall()

            # Per day (time series for charts)
            per_day_rows = conn.execute(
                """SELECT
                    date(ts)        AS day,
                    COUNT(*)        AS calls,
                    COALESCE(SUM(cost_usd), 0)       AS cost_usd,
                    COALESCE(SUM(cost_saved_usd), 0)  AS cost_saved_usd,
                    COALESCE(SUM(tokens_saved), 0)    AS tokens_saved
                FROM llm_calls
                WHERE ts_epoch >= ?
                GROUP BY day
                ORDER BY day ASC""", (cutoff,)
            ).fetchall()

            # Per aspect
            per_aspect_rows = conn.execute(
                """SELECT
                    COALESCE(aspect, 'unknown')   AS aspect,
                    COUNT(*)                      AS calls,
                    COALESCE(SUM(cost_usd), 0)    AS cost_usd,
                    COALESCE(SUM(cost_saved_usd), 0) AS cost_saved_usd
                FROM llm_calls
                WHERE ts_epoch >= ?
                GROUP BY aspect
                ORDER BY calls DESC""", (cutoff,)
            ).fetchall()

        return {
            "days": days,
            "overall": dict(overall),
            "per_provider": [dict(r) for r in per_provider_rows],
            "per_day": [dict(r) for r in per_day_rows],
            "per_aspect": [dict(r) for r in per_aspect_rows],
        }

    def recent_calls(self, limit: int = 50) -> list[dict[str, Any]]:
        """Most recent calls for the live feed."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT ts, provider, model, call_type, task, aspect,
                          prompt_tokens, output_tokens, cost_usd, latency_sec,
                          tokens_saved, cost_saved_usd, error
                   FROM llm_calls
                   ORDER BY id DESC
                   LIMIT ?""", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def lifetime_totals(self) -> dict[str, Any]:
        """All-time totals since the beginning."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """SELECT
                    COUNT(*)                              AS total_calls,
                    COALESCE(SUM(prompt_tokens), 0)       AS total_prompt_tokens,
                    COALESCE(SUM(output_tokens), 0)       AS total_output_tokens,
                    COALESCE(SUM(cost_usd), 0)            AS total_cost_usd,
                    COALESCE(SUM(tokens_saved), 0)        AS total_tokens_saved,
                    COALESCE(SUM(cost_saved_usd), 0)      AS total_cost_saved_usd,
                    COALESCE(MIN(ts), '')                 AS first_call,
                    COALESCE(MAX(ts), '')                 AS last_call
                FROM llm_calls"""
            ).fetchone()
        return dict(row)


# Singleton convenience
_db: SavingsDB | None = None


def get_db(db_path: str = DB_PATH) -> SavingsDB:
    global _db
    if _db is None:
        _db = SavingsDB(db_path)
    return _db


def log_call(**kwargs) -> int:
    return get_db().log_call(**kwargs)
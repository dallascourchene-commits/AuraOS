from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from aura_empirical_cost_ledger import EmpiricalCostLedger


V1_SCHEMA = """
CREATE TABLE cost_runs (
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
CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at REAL);
INSERT INTO schema_migrations(version, applied_at) VALUES(1, 0);
"""


def test_fresh_ledger_exposes_v2_linkage_schema(tmp_path: Path) -> None:
    with EmpiricalCostLedger(tmp_path) as ledger:
        status = ledger.schema_status()
        assert status["schema_version"] == 2
        assert status["journal_mode"] == "wal"
        for column in (
            "correlation_id",
            "route_decision_id",
            "task_context_id",
            "profile_id",
            "call_id",
            "observation_id",
            "experience_id",
            "time_to_verified_outcome_ms",
            "queue_ms",
            "generation_ms",
            "verifier_ms",
            "retry_ms",
            "fallback_ms",
            "human_wait_ms",
            "cost_status",
            "price_snapshot_digest",
            "field_measurement_classes",
        ):
            assert column in status["columns"]


def test_v1_database_migrates_without_losing_existing_run(tmp_path: Path) -> None:
    memory = tmp_path / "Aura_Memory"
    memory.mkdir()
    path = memory / "empirical_cost_ledger.db"
    conn = sqlite3.connect(path)
    conn.executescript(V1_SCHEMA)
    conn.execute(
        "INSERT INTO cost_runs(run_id, comparison_id, provider, model, input_tokens, created_at) "
        "VALUES(?,?,?,?,?,?)",
        ("legacy-run", "legacy-comparison", "provider", "model", 10, 1.0),
    )
    conn.commit()
    conn.close()

    with EmpiricalCostLedger(tmp_path) as ledger:
        assert ledger.schema_status()["schema_version"] == 2
        legacy = ledger.get_run("legacy-run")
        assert legacy is not None
        assert legacy["input_tokens"] == 10
        assert legacy["call_id"] is None
        assert legacy["time_to_verified_outcome_ms"] is None


def test_linked_run_round_trip_preserves_nulls_and_json_provenance(tmp_path: Path) -> None:
    with EmpiricalCostLedger(tmp_path) as ledger:
        recorded = ledger.record_run(
            {
                "run_id": "run-1",
                "comparison_id": "comparison-1",
                "correlation_id": "correlation-1",
                "route_decision_id": "route-1",
                "task_context_id": "task-1",
                "profile_id": "profile-1",
                "call_id": "call-1",
                "observation_id": "observation-1",
                "experience_id": "experience-1",
                "provider": "fireworks",
                "model": "glm",
                "input_tokens": None,
                "output_tokens": 12,
                "calculated_cost_usd": None,
                "cost_status": "COST_UNKNOWN",
                "latency_ms": 100,
                "time_to_verified_outcome_ms": None,
                "queue_ms": 5,
                "generation_ms": 80,
                "verifier_ms": 15,
                "field_measurement_classes": {
                    "input_tokens": "UNAVAILABLE",
                    "output_tokens": "MEASURED",
                },
                "telemetry_warnings": ["input usage unavailable"],
            }
        )
        assert recorded["call_id"] == "call-1"
        row = ledger.get_run("run-1")
        assert row is not None
        assert row["input_tokens"] is None
        assert row["calculated_cost_usd"] is None
        assert row["time_to_verified_outcome_ms"] is None
        assert row["field_measurement_classes"]["input_tokens"] == "UNAVAILABLE"
        assert row["telemetry_warnings"] == ["input usage unavailable"]
        assert ledger.get_by_call_id("call-1")[0]["observation_id"] == "observation-1"


def test_nested_secrets_are_redacted_before_storage(tmp_path: Path) -> None:
    with EmpiricalCostLedger(tmp_path) as ledger:
        ledger.record_run(
            {
                "run_id": "secret-run",
                "comparison_id": "comparison",
                "telemetry_warnings": [
                    {"api_key": "sk-should-not-survive"},
                    "Authorization: Bearer abcdefghijklmnop",
                ],
                "field_measurement_classes": {
                    "input_tokens": "MEASURED",
                    "private_key": "secret-value",
                },
                "price_snapshot": {
                    "provider": "x",
                    "access_token": "hidden-token",
                },
            }
        )
        row = ledger.get_run("secret-run")
        encoded = json.dumps(row, sort_keys=True)
        assert "should-not-survive" not in encoded
        assert "abcdefghijklmnop" not in encoded
        assert "hidden-token" not in encoded
        assert encoded.count("[REDACTED]") >= 3


def test_replay_with_same_run_id_replaces_deterministically(tmp_path: Path) -> None:
    with EmpiricalCostLedger(tmp_path) as ledger:
        ledger.record_run(
            {
                "run_id": "same-run",
                "comparison_id": "comparison",
                "call_id": "call-1",
                "latency_ms": 10,
            }
        )
        ledger.record_run(
            {
                "run_id": "same-run",
                "comparison_id": "comparison",
                "call_id": "call-1",
                "latency_ms": 20,
            }
        )
        rows = ledger.get_by_call_id("call-1")
        assert len(rows) == 1
        assert rows[0]["latency_ms"] == 20

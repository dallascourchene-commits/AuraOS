from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_arena_architect_connector import AuraArenaArchitectConnector
from aura_arena_connector_server import ArenaConnectorServerState, dispatch_connector_request


def _candidate(candidate_id: str, coverage: list[str]) -> dict:
    return {
        "candidate_id": candidate_id,
        "plan": {
            "architecture_decision": candidate_id,
            "target_file": "a.py",
            "target_symbol": "f",
            "coverage_tags": coverage,
            "architecture_reuse": True,
            "act_tasks": [
                {
                    "task_id": "A1",
                    "objective": "bounded",
                    "target_file": "a.py",
                    "target_symbol": "f",
                    "acceptance": "tests pass",
                    "expected_output": "UNIFIED_DIFF",
                    "size": "S",
                }
            ],
            "acceptance_criteria": ["tests pass"],
            "rollback_conditions": ["revert"],
            "risk_map": ["scope"],
            "constraints": ["proposal only"],
            "secret": "must-not-be-persisted",
        },
    }


def test_connector_record_is_redacted_and_digest_bound(tmp_path: Path) -> None:
    record = tmp_path / "selection.jsonl"
    connector = AuraArenaArchitectConnector(tmp_path, bridge=object(), record_path=record)
    result = connector.compare_plans(
        objective="select a bounded plan",
        candidates=[_candidate("A", ["routing"])],
        required_capabilities=["routing"],
    )
    row = json.loads(record.read_text(encoding="utf-8").splitlines()[0])
    encoded = json.dumps(row, sort_keys=True)
    assert row["payload"]["selected_candidate_id"] == "A"
    assert row["payload"]["selection_digest"] == result["selection_digest"]
    assert row["redaction"] == "FULL_PLANS_AUTHORIZATIONS_AND_PRIVATE_EVIDENCE_OMITTED"
    assert "must-not-be-persisted" not in encoded
    assert "selected_plan" not in row["payload"]


def test_connector_rejects_duplicate_ids_and_excess_candidates(tmp_path: Path) -> None:
    connector = AuraArenaArchitectConnector(tmp_path, bridge=object())
    with pytest.raises(ValueError, match="unique"):
        connector.compare_plans(
            objective="x",
            candidates=[_candidate("A", []), _candidate("A", [])],
        )
    with pytest.raises(ValueError, match="at most 8"):
        connector.compare_plans(
            objective="x",
            candidates=[_candidate(str(index), []) for index in range(9)],
        )


def test_http_connector_enforces_candidate_and_token_bounds(tmp_path: Path) -> None:
    state = ArenaConnectorServerState(tmp_path, connector=AuraArenaArchitectConnector(tmp_path, bridge=object()))
    status, result = dispatch_connector_request(
        state,
        "POST",
        "/v1/architect/compare",
        {"objective": "x", "candidates": [_candidate(str(index), []) for index in range(9)]},
    )
    assert status == 400
    assert "at most 8" in result["error"]
    status, result = dispatch_connector_request(
        state,
        "POST",
        "/v1/models/route",
        {"objective": "x", "purpose_digest": "p", "token_budget": 12001},
    )
    assert status == 400
    assert "token_budget" in result["error"]


def test_compose_is_pull_only_and_loopback_bound() -> None:
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.arena-connector.yml").read_text(encoding="utf-8")
    assert "build:" not in compose
    assert "pull_policy: always" in compose
    assert '127.0.0.1:8091:8091' in compose

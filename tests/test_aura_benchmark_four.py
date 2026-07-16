from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import given, strategies as st

from aura_arena_architect_connector import AuraArenaArchitectConnector
from aura_arena_connector_server import ArenaConnectorServerState, dispatch_connector_request
from aura_cognitive_labor_router import route_failure
from aura_native_model_gateway import AuraNativeModelGateway
from aura_refactor_state_ledger import build_state_ledger, bounded_state_ledger_text


@given(
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.floats(allow_nan=True, allow_infinity=True),
        st.text(),
        st.lists(st.integers(), max_size=3),
        st.dictionaries(st.text(max_size=5), st.integers(), max_size=3),
    )
)
def test_route_failure_never_raises_on_untrusted_counts(value: Any) -> None:
    decision = route_failure(
        failure_packet={"message": "focused assertion", "repair_attempt": value},
        local_repair_attempts=None,
    )
    assert decision.route in {"SURGEON_LOCAL_REPAIR", "ESCALATE_TO_COUNCIL_REPLAN"}


@pytest.mark.parametrize("value", ["bad", -1, float("nan"), float("inf"), True, [], {}])
def test_malformed_repair_attempt_fails_closed(value: Any) -> None:
    decision = route_failure(
        failure_packet={"message": "focused assertion", "repair_attempt": value},
        local_repair_attempts=None,
    )
    assert decision.route == "ESCALATE_TO_COUNCIL_REPLAN"
    assert decision.local_repair_allowed is False
    assert any("invalid_failure_evidence" in reason for reason in decision.reasons)


@pytest.mark.parametrize("value", [False, 0, 0.0, "0", "false", "off", "no", None])
def test_false_graph_flag_encodings_remain_local(value: Any) -> None:
    result = route_failure(
        failure_packet={
            "message": "focused unit test assertion failed",
            "dependency_graph_breach": value,
            "repair_attempt": 0,
        },
        local_repair_attempts=None,
    )
    assert result.route == "SURGEON_LOCAL_REPAIR"


@pytest.mark.parametrize("value", [True, 1, 1.0, "1", "true", "yes", "on", "breach"])
def test_true_graph_flag_encodings_escalate(value: Any) -> None:
    result = route_failure(
        failure_packet={"dependency_graph_breach": value, "repair_attempt": 0},
        local_repair_attempts=None,
    )
    assert result.route == "ESCALATE_TO_COUNCIL_REPLAN"


def _session(history: list[dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(
        session_id="SESSION-1",
        plan_phase_hash="PLAN-1",
        objective="Harden the real refactor",
        active_task_index=1,
        act_capsules=[
            {"task_id": "A1", "depends_on": []},
            {"task_id": "A2", "depends_on": ["A1"]},
        ],
        pending_turn=SimpleNamespace(role="worker"),
        turns=history,
        stage_results=[{"ok": True, "stage": "A1"}],
        verification_results=[{"ok": True, "tests": 4}],
        status="WAITING_FOR_MODEL",
    )


def test_history_root_changes_when_earlier_event_changes() -> None:
    first = build_state_ledger(
        _session([{"event": "first", "value": 1}, {"event": "last", "value": 2}])
    )
    second = build_state_ledger(
        _session([{"event": "different", "value": 999}, {"event": "last", "value": 2}])
    )
    assert first.history_event_count == second.history_event_count
    assert first.last_event_digest == second.last_event_digest
    assert first.history_root_digest != second.history_root_digest


def test_compact_ledger_preserves_history_identity_without_replaying_history() -> None:
    ledger = build_state_ledger(_session([{"event": "stage", "secret": "do-not-replay"}]))
    text = bounded_state_ledger_text(ledger, max_tokens=120)
    payload = json.loads(text)
    assert payload["history_event_count"] == 3
    assert len(payload["history_root_digest"]) == 24
    assert "do-not-replay" not in text
    assert "history" not in payload


def test_nonfinite_history_values_have_deterministic_identity() -> None:
    one = build_state_ledger(_session([{"metric": float("nan")}]))
    two = build_state_ledger(_session([{"metric": float("nan")}]))
    assert one.history_root_digest == two.history_root_digest


def _plans() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "benchmarks" / "real_refactor_trial" / "plans.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_council_v3_selects_integrated_real_refactor_plan(tmp_path: Path) -> None:
    payload = _plans()
    connector = AuraArenaArchitectConnector(tmp_path, bridge=object(), record_path=tmp_path / "record.jsonl")
    result = connector.compare_plans(
        objective=payload["objective"],
        candidates=payload["candidates"],
        required_capabilities=payload["required_capabilities"],
    )
    assert result["selected_candidate_id"] == payload["expected_selected_candidate_id"]
    assert result["selected_assessment"]["coverage_fraction"] == 1.0
    assert "tests" in result["selected_assessment"]["selected_critic_lanes"]
    assert result["cognitive_labor_route"]["route"] == "COUNCIL_PLAN_THEN_SURGEON_EXECUTION"
    assert (tmp_path / "record.jsonl").is_file()


class _FakeRouter:
    def __init__(self, **_kwargs: Any) -> None:
        self.closed = False

    def plan(self, objective: str, **_kwargs: Any) -> dict[str, Any]:
        return {
            "status": "PROPOSED",
            "selected_option": {
                "policy_mode": "CASCADE",
                "profile_ids": ["fast", "deep"],
                "expected_success": 0.91,
                "expected_cost_usd": 0.02,
                "expected_time_to_verified_ms": 800,
            },
            "shadow_evaluation": {
                "candidate_assessments": [
                    {"admitted": True, "candidate": {"profile_id": "fast"}},
                    {"admitted": True, "candidate": {"profile_id": "deep"}},
                ]
            },
            "objective": objective,
        }

    def execute(self, objective: str, **kwargs: Any) -> dict[str, Any]:
        result = self.plan(objective)
        result.update({"status": "SHADOW_ONLY", "executed": False, "execution_mode": kwargs.get("execution_mode")})
        return result

    def close(self) -> None:
        self.closed = True


def test_native_gateway_uses_adaptive_model_cognome_route(tmp_path: Path) -> None:
    gateway = AuraNativeModelGateway(tmp_path, router_factory=_FakeRouter)
    result = gateway.plan_best("Choose a model", purpose_digest="PURPOSE-1")
    trace = result["native_gateway"]["selection_trace"]
    assert trace["policy_mode"] == "CASCADE"
    assert trace["selected_profile_ids"] == ["fast", "deep"]
    assert trace["routing_basis"] == "MODEL_COGNOME_VERIFIED_OUTCOME_EVIDENCE"
    assert result["native_gateway"]["adaptive_selection"] is True


class _FakeConnector:
    def compare_plans(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "selected_candidate_id": "PLAN-C"}

    def prepare_refactor(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "proposal_only": True}

    def route_native_model(self, **_kwargs: Any) -> dict[str, Any]:
        return {"status": "PROPOSED", "selected_option": {"policy_mode": "DIRECT"}}

    def execute_native_model(self, **_kwargs: Any) -> dict[str, Any]:
        return {"status": "DENIED", "executed": False}


def test_http_connector_aliases_coding_and_human_agent_arenas(tmp_path: Path) -> None:
    state = ArenaConnectorServerState(tmp_path, connector=_FakeConnector())
    for route in (
        "/v1/architect/compare",
        "/v1/coding-arena/architect/compare",
        "/v1/human-agent/architect/compare",
    ):
        status, result = dispatch_connector_request(
            state, "POST", route, {"objective": "x", "candidates": [{"plan": {}}]}
        )
        assert status == 200
        assert result["selected_candidate_id"] == "PLAN-C"
    status, capability = dispatch_connector_request(state, "GET", "/v1/capabilities")
    assert status == 200
    assert "CASCADE" in capability["policy_modes"]


def test_unified_mcp_installs_architect_sessions_and_native_model_tools() -> None:
    import aura_agent_arena_mcp_architect as mcp

    names = {item["name"] for item in mcp.base_mcp.TOOL_DEFINITIONS}
    assert {
        "aura_llm_session_open",
        "aura_architect_compare_plans",
        "aura_architect_prepare",
        "aura_native_model_route",
        "aura_native_model_execute",
    }.issubset(names)


def test_container_contract_requires_no_runtime_github_clone() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dockerfile = (repo_root / "Dockerfile.arena-connector").read_text(encoding="utf-8")
    compose = (repo_root / "docker-compose.arena-connector.yml").read_text(encoding="utf-8")
    assert "COPY . /opt/aura" in dockerfile
    assert "git clone" not in dockerfile.lower()
    assert "aura_arena_connector_server.py" in dockerfile
    assert "8091" in compose

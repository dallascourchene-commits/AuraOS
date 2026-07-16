from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aura_cognitive_labor_router import route_failure
from aura_controlled_refactor_session import ControlledRefactorSessionManager
from aura_external_llm_session import ExternalLLMSession
from aura_refactor_state_ledger import (
    build_state_ledger,
    build_state_sidecar,
    measure_state_preservation,
    reconstruct_state_from_ledger,
)


def _session(history, *, accepted=None, rejected=None):
    return SimpleNamespace(
        session_id="SESSION-HARDENING",
        plan_phase_hash="PLAN-HARDENING",
        objective="Preserve exact refactor state",
        active_task_index=1,
        act_capsules=[
            {"task_id": "A1", "depends_on": []},
            {"task_id": "A2", "depends_on": ["A1"]},
        ],
        pending_turn=SimpleNamespace(role="worker"),
        turns=list(history),
        stage_results=[{"ok": True, "stage": "A1"}],
        verification_results=[{"ok": True, "tests": 4}],
        accepted_decisions=list(accepted or []),
        rejected_alternatives=list(rejected or []),
        assumptions=["public API remains stable"],
        unresolved_questions=["migration timing"],
        status="WAITING_FOR_MODEL",
    )


@pytest.mark.parametrize("packet", ["not-a-mapping", [1, 2], object()])
def test_non_mapping_failure_packets_fail_closed_without_exception(packet) -> None:
    decision = route_failure(failure_packet=packet)
    assert decision.route == "ESCALATE_TO_COUNCIL_REPLAN"
    assert decision.escalation_required is True
    assert "invalid_failure_evidence" in decision.reasons[0]


def test_explicit_false_override_takes_precedence_over_packet_true() -> None:
    decision = route_failure(
        failure_packet={
            "message": "focused unit test assertion failed",
            "dependency_graph_breach": True,
            "repair_attempt": 0,
        },
        dependency_graph_breach=False,
    )
    assert decision.route == "SURGEON_LOCAL_REPAIR"


@pytest.mark.parametrize("value", ["unknown", 2, -1, float("nan"), float("inf"), [], {}])
def test_unknown_graph_flag_encoding_fails_closed(value) -> None:
    decision = route_failure(
        failure_packet={"dependency_graph_breach": value, "repair_attempt": 0}
    )
    assert decision.route == "ESCALATE_TO_COUNCIL_REPLAN"
    assert "dependency_graph_breach" in decision.reasons[0]


def test_same_last_event_and_count_do_not_imply_same_history_identity() -> None:
    first = build_state_ledger(
        _session([{"event": "first", "value": 1}, {"event": "last", "value": 2}])
    )
    second = build_state_ledger(
        _session([{"event": "changed", "value": 999}, {"event": "last", "value": 2}])
    )
    assert first.history_event_count == second.history_event_count
    assert first.last_event_digest == second.last_event_digest
    assert first.history_root_digest != second.history_root_digest


def test_reordering_insertion_and_deletion_change_history_root() -> None:
    base = [{"event": "one"}, {"event": "two"}, {"event": "three"}]
    roots = {
        build_state_ledger(_session(base)).history_root_digest,
        build_state_ledger(_session(list(reversed(base)))).history_root_digest,
        build_state_ledger(_session(base + [{"event": "four"}])).history_root_digest,
        build_state_ledger(_session(base[:-1])).history_root_digest,
    }
    assert len(roots) == 4


def test_sidecar_reconstructs_execution_and_semantic_state() -> None:
    session = _session(
        [{"event": "stage"}, {"event": "verify"}],
        accepted=["keep compatibility adapter"],
        rejected=["replace public interface"],
    )
    ledger = build_state_ledger(
        session,
        repair_attempts_by_task={"A2": 1},
        council_replan_count=1,
    )
    sidecar = build_state_sidecar(
        session,
        repair_attempts_by_task={"A2": 1},
        council_replan_count=1,
    )
    projection = reconstruct_state_from_ledger(ledger, sidecar)
    assert projection["completed_task_ids"] == ["A1"]
    assert projection["current_task_id"] == "A2"
    assert projection["accepted_decisions"] == ["keep compatibility adapter"]
    assert projection["rejected_alternatives"] == ["replace public interface"]
    measurement = measure_state_preservation(session, ledger)
    assert measurement["state_preservation_score"] == 1.0
    assert measurement["checks"]["sidecar_reconstructability"] is True


def test_sidecar_tampering_is_rejected() -> None:
    session = _session([{"event": "stage"}])
    ledger = build_state_ledger(session)
    sidecar = build_state_sidecar(session)
    tampered = deepcopy(sidecar)
    tampered["events"][0]["payload"] = {"event": "substituted"}
    with pytest.raises(ValueError, match="sidecar"):
        reconstruct_state_from_ledger(ledger, tampered)


def test_different_semantic_decisions_change_projected_state_identity() -> None:
    first = build_state_ledger(_session([], accepted=["adapter A"]))
    second = build_state_ledger(_session([], accepted=["adapter B"]))
    assert first.history_root_digest == second.history_root_digest
    assert first.execution_state_digest != second.execution_state_digest
    assert first.accepted_decisions_digest != second.accepted_decisions_digest


class _NoTurnBridge:
    def aura_get_micro_context(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": False, "error": "no_context"}


def _controlled_manager(tmp_path: Path) -> ControlledRefactorSessionManager:
    return ControlledRefactorSessionManager(
        tmp_path,
        bridge=_NoTurnBridge(),
        control={
            "council_mode": "SELECTIVE_V3",
            "council_call_budget": 2,
            "surgeon_max_turns": 2,
            "record_outputs": False,
        },
    )


def _install_replan_session(
    manager: ControlledRefactorSessionManager,
    *,
    turns: list[dict[str, Any]],
    max_turns: int,
) -> ExternalLLMSession:
    session = ExternalLLMSession(
        session_id="SESSION-REPLAN",
        objective="Repair the affected graph",
        plan_phase_hash="PLAN-1",
        provider="test",
        model="fixture",
        act_capsules=[
            {
                "task_id": "A1",
                "objective": "repair",
                "target_file": "a.py",
                "target_symbol": "f",
                "related_files": [],
                "size": "S",
                "role": "cheap_builder",
            }
        ],
        max_context_tokens=512,
        max_output_tokens=512,
        max_turns=max_turns,
        status="WAITING_FOR_COUNCIL_REPLAN",
        turns=list(turns),
    )
    manager._sessions[session.session_id] = session
    manager._repair_attempts[session.session_id] = {}
    manager._council_replans[session.session_id] = 0
    manager._state_metrics[session.session_id] = []
    return session


def test_council_replan_cannot_issue_turn_after_session_budget(tmp_path: Path) -> None:
    manager = _controlled_manager(tmp_path)
    session = _install_replan_session(manager, turns=[{"turn": 1}], max_turns=1)

    result = manager.apply_council_replan(
        session_id=session.session_id,
        remaining_act_capsules=list(session.act_capsules),
        rationale="graph repair",
    )

    assert result["ok"] is False
    assert result["status"] == "BLOCKED_MAX_TURNS"
    assert result["error"] == "max_turns_exceeded_before_council_replan"
    assert result["turn"] is None
    assert result["session"]["pending_turn"] is None


def test_council_replan_never_leaves_waiting_state_without_turn(tmp_path: Path) -> None:
    manager = _controlled_manager(tmp_path)
    session = _install_replan_session(manager, turns=[], max_turns=2)

    result = manager.apply_council_replan(
        session_id=session.session_id,
        remaining_act_capsules=list(session.act_capsules),
        rationale="graph repair",
    )

    assert result["ok"] is False
    assert result["status"] == "BLOCKED_REPLAN_TURN_UNAVAILABLE"
    assert result["error"] == "unable_to_build_replanned_turn"
    assert result["turn"] is None
    assert result["session"]["pending_turn"] is None
    assert result["experience"]

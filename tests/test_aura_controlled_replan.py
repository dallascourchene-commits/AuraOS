from __future__ import annotations

from pathlib import Path
from typing import Any

from aura_controlled_refactor_session import ControlledRefactorSessionManager
from aura_external_llm_session import ExternalLLMSession


class _NoTurnBridge:
    def aura_get_micro_context(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": False, "error": "no_context"}


def _manager(tmp_path: Path) -> ControlledRefactorSessionManager:
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


def _install_session(
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
    manager = _manager(tmp_path)
    session = _install_session(manager, turns=[{"turn": 1}], max_turns=1)

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
    manager = _manager(tmp_path)
    session = _install_session(manager, turns=[], max_turns=2)

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

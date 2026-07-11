"""Live Human Agent routing and server-surface integration tests."""
from __future__ import annotations

from pathlib import Path
import shutil
from types import SimpleNamespace

from aura_human_agent_workflow import HumanAgentWorkflow
from aura_human_agent_arena_server import dispatch_api_request

REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_routes(tmp_path: Path) -> None:
    target = tmp_path / ".aura" / "arena_routes"
    target.mkdir(parents=True)
    for name in ("human_agent.v1.json", "meta.v1.json", "coding.v1.json"):
        shutil.copy(REPO_ROOT / ".aura" / "arena_routes" / name, target / name)


def test_help_is_meta_self_loop_not_a_new_objective(tmp_path: Path):
    _copy_routes(tmp_path)
    workflow = HumanAgentWorkflow(tmp_path)
    result = workflow.ingest_command("help")
    workflow.close()
    assert result["ok"] is True
    assert result["status"] == "META_COMPLETED"
    assert result["action_id"] == "META.HELP"
    assert result["workflow"]["current_phase"] == "FRAME"
    assert result["workflow"]["objective"] == ""


def test_free_form_request_is_admitted_as_frame_objective(tmp_path: Path):
    _copy_routes(tmp_path)
    workflow = HumanAgentWorkflow(tmp_path)
    result = workflow.ingest_command("Refactor the Human Agent Arena")
    state = workflow.get_state()
    workflow.close()
    assert result["ok"] is True
    assert result["action_id"] == "set_objective"
    assert result["route_decision"]["selected"]["transition_id"] == "HUMAN.SET_OBJECTIVE"
    assert state["current_phase"] == "GROUND"
    assert state["objective"] == "Refactor the Human Agent Arena"
    assert state["recommended"]
    assert state["state_packet"]["grammar_version"] == "human-agent-wfst-v1"


def test_direct_server_action_uses_guarded_route(tmp_path: Path):
    _copy_routes(tmp_path)
    workflow = HumanAgentWorkflow(tmp_path)
    coding = SimpleNamespace(
        get_state=lambda: {"ok": True},
        project_state=lambda: {"ok": True},
        route_action=lambda action_id, payload=None: {"ok": True, "action_id": action_id},
        route_command=lambda command, payload=None: {"ok": True, "command": command},
    )
    state = SimpleNamespace(workflow=workflow, coding_workbench=coding)
    status, result = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/action",
        {"action_id": "set_objective", "payload": {"objective": "Guard this"}},
    )
    workflow.close()
    assert status == 200
    assert result["route_decision"]["selected"]["transition_id"] == "HUMAN.SET_OBJECTIVE"
    assert result["experience_recording"]["persistent"] is True


def test_server_exposes_contextual_human_and_coding_routes(tmp_path: Path):
    _copy_routes(tmp_path)
    workflow = HumanAgentWorkflow(tmp_path)
    coding_projection = {"ok": True, "state": "WORKSPACE_OPENED", "recommended": []}
    coding = SimpleNamespace(
        get_state=lambda: {"ok": True, "state": "WORKSPACE_OPENED"},
        project_state=lambda: coding_projection,
        route_action=lambda action_id, payload=None: {"ok": True, "action_id": action_id},
        route_command=lambda command, payload=None: {"ok": True, "command": command},
    )
    state = SimpleNamespace(workflow=workflow, coding_workbench=coding)
    human_status, human = dispatch_api_request(state, "GET", "/api/human-agent/routes")
    coding_status, coding_result = dispatch_api_request(state, "GET", "/api/coding-workbench/routes")
    workflow.close()
    assert human_status == 200
    assert "recommended" in human and "blocked" in human and "meta" in human
    assert coding_status == 200
    assert coding_result is coding_projection


def test_execute_guarded_fails_closed_for_unknown_action_id(tmp_path: Path):
    _copy_routes(tmp_path)
    workflow = HumanAgentWorkflow(tmp_path)
    result = workflow.execute_guarded("unknown_nonexistent_action_12345", {})
    workflow.close()
    assert result["ok"] is False
    assert result["status"] == "DENIED"
    assert result["fail_closed"] is True
    assert result["reason"] == "unknown_action_id"
    assert "unknown_nonexistent_action_12345" in result["message"]

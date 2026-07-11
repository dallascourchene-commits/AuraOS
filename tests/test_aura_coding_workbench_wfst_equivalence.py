"""Equivalence and authority tests for Coding Workbench WFST integration."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_coding_workbench_sequence import GATE_DEFINITIONS, WorkbenchState
from aura_coding_workbench_wfst_adapter import CodingWorkbenchWFSTSession

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / ".aura" / "arena_routes" / "coding.v1.json"


def _transitions_by_state():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = {}
    for transition in data["transitions"]:
        rows.setdefault(transition["from_state"], []).append(transition)
    return data, rows


def test_coding_manifest_compiles_and_declares_all_18_states():
    result = load_and_compile_arena_grammar(MANIFEST)
    assert result.ok, [item.to_dict() for item in result.diagnostics]
    assert result.grammar is not None
    assert set(result.grammar.states) == {state.value for state in WorkbenchState}


def test_every_legacy_allowed_action_has_one_state_local_transition():
    _, rows = _transitions_by_state()
    for state, gate in GATE_DEFINITIONS.items():
        action_ids = [
            str((transition.get("provenance") or {}).get("action_id") or "")
            for transition in rows.get(state.value, [])
        ]
        assert sorted(action_ids) == sorted(gate.allowed_actions), state.value


def test_compiled_next_states_preserve_legacy_transition_contract():
    _, rows = _transitions_by_state()
    for state, gate in GATE_DEFINITIONS.items():
        allowed_targets = {state.value, *gate.next_actions}
        for transition in rows.get(state.value, []):
            assert transition["next_state"] in allowed_targets, transition["transition_id"]


def test_legacy_blocked_actions_are_not_admitted_from_same_state():
    _, rows = _transitions_by_state()
    for state, gate in GATE_DEFINITIONS.items():
        admitted = {
            str((transition.get("provenance") or {}).get("action_id") or "")
            for transition in rows.get(state.value, [])
        }
        assert not admitted.intersection(gate.blocked_actions), state.value


def test_human_approval_states_have_hard_approval_guards():
    _, rows = _transitions_by_state()
    for state, gate in GATE_DEFINITIONS.items():
        if not gate.human_approval_required:
            continue
        for transition in rows.get(state.value, []):
            guards = {item["id"] for item in transition.get("hard_guards", [])}
            if (transition.get("provenance") or {}).get("action_id") in {
                "send_to_agent", "approve_for_pr", "open_pr",
                "generate_pr_command", "human_override",
            }:
                assert "GUARD.HUMAN_APPROVAL" in guards


def test_no_transition_can_commit_push_merge_or_open_pr_directly():
    data, _ = _transitions_by_state()
    forbidden = {"commit", "push", "merge"}
    for transition in data["transitions"]:
        action_id = str((transition.get("provenance") or {}).get("action_id") or "").lower()
        output = str(transition.get("output_symbol") or "").lower()
        assert action_id not in forbidden
        assert not any(token in output for token in ("git_commit", "git_push", "merge_pr"))


def test_session_scopes_free_form_objective_and_only_generates_pr_command(tmp_path: Path):
    routes = tmp_path / ".aura" / "arena_routes"
    routes.mkdir(parents=True)
    shutil.copy(MANIFEST, routes / "coding.v1.json")
    shutil.copy(REPO_ROOT / ".aura" / "arena_routes" / "meta.v1.json", routes / "meta.v1.json")

    session = CodingWorkbenchWFSTSession(tmp_path, restore=False)
    scoped = session.route_command("Refactor the guarded routing integration")
    assert scoped["ok"] is True
    assert scoped["action_id"] == "scope_task"
    assert session.state is WorkbenchState.TASK_SCOPED

    session.state = WorkbenchState.PR_READY
    session.evidence.update({
        "human_approval": {"approved": True},
        "verification_ok": True,
    })
    packet = session.route_action(
        "generate_pr_command",
        payload={"approved": True, "branch": "feature/test", "title": "Review me"},
    )
    session.close()
    assert packet["ok"] is True
    assert packet["pr_opened"] is False
    assert packet["produced_evidence"]["pr_packet"]["executed"] is False
    assert packet["produced_evidence"]["pr_packet"]["draft"] is True


def test_workspace_meta_and_alias_are_routed_before_objective_fallback(tmp_path: Path):
    routes = tmp_path / ".aura" / "arena_routes"
    routes.mkdir(parents=True)
    shutil.copy(MANIFEST, routes / "coding.v1.json")
    shutil.copy(REPO_ROOT / ".aura" / "arena_routes" / "meta.v1.json", routes / "meta.v1.json")
    session = CodingWorkbenchWFSTSession(tmp_path, restore=False)
    help_result = session.route_command("help")
    assert help_result["status"] == "META_COMPLETED"
    assert session.state is WorkbenchState.WORKSPACE_OPENED
    assert session.objective == ""
    topology = session.route_command("topology health")
    session.close()
    assert topology["action_id"] == "check_topology"
    assert session.objective == ""


def test_prepare_handoff_accepts_existing_task_id(monkeypatch, tmp_path: Path):
    routes = tmp_path / ".aura" / "arena_routes"
    routes.mkdir(parents=True)
    shutil.copy(MANIFEST, routes / "coding.v1.json")
    shutil.copy(REPO_ROOT / ".aura" / "arena_routes" / "meta.v1.json", routes / "meta.v1.json")
    import aura_coding_workbench_actions as actions
    monkeypatch.setattr(actions, "prepare_agent_handoff", lambda capsule_id, agent, repo_root: {
        "ok": True, "handoff_packet": {"capsule_id": capsule_id, "agent": agent}
    })
    session = CodingWorkbenchWFSTSession(tmp_path, restore=False)
    session.state = WorkbenchState.ACT_CAPSULES_CREATED
    session.evidence["act_capsules"] = [{"task_id": "A1", "objective": "test"}]
    result = session.route_action("prepare_agent_handoff")
    session.close()
    assert result["ok"] is True
    assert result["produced_evidence"]["agent_handoff_packet"]["capsule_id"] == "A1"

"""Executable integration tests for persistence arena surfaces."""
from __future__ import annotations

from pathlib import Path
from types import MethodType

from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request
from aura_agent_arena_persistence_bridge import PersistentAuraAgentArenaBridge
from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_coding_workbench_wfst_adapter import CodingWorkbenchWFSTSession
from aura_human_agent_arena_server import HumanAgentArenaServerState, dispatch_api_request
from aura_restoration_commander import RestorationCommander


HEAD = "a" * 40


def test_coding_workbench_exposes_checkpoint_methods_without_full_initialization(tmp_path: Path):
    session = object.__new__(CodingWorkbenchWFSTSession)
    session.session_id = "CWFST-INTEGRATION"
    session.persistence = ArenaPersistenceCoordinator(str(tmp_path))
    events = []
    session._event = MethodType(lambda self, kind, message: events.append((kind, message)), session)
    session.get_state_without_routing = MethodType(
        lambda self: {
            "ok": True,
            "session_id": self.session_id,
            "state": "PLAN_READY",
            "objective": "Persist exact coding state",
            "evidence": {"topology": "healthy"},
            "gate": {"allowed_actions": ["stage_patch"]},
            "patch_authority": "exact_source_spans_and_hashes_only",
            "vsa_patch_authority": False,
        },
        session,
    )

    result = session.checkpoint_state(repo_head=HEAD)

    assert result["ok"] is True
    assert result["checkpoint"]["arena_id"] == "coding_workbench"
    assert events[0][0] == "checkpoint"
    assert session.list_checkpoints()["count"] == 1


def test_human_agent_server_exposes_checkpoint_and_read_only_projection(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    try:
        status, stored = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/persistence/checkpoint",
            {"repo_head": HEAD},
        )
        assert status == 200
        checkpoint_id = stored["checkpoint"]["checkpoint_id"]

        status, projection = dispatch_api_request(
            state,
            "GET",
            f"/api/human-agent/persistence/checkpoints/{checkpoint_id}",
        )
        assert status == 200
        assert projection["payload_included"] is False
        assert projection["read_only"] is True

        status, handoff = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/persistence/handoff",
            {
                "checkpoint_id": checkpoint_id,
                "target_arena_id": "agent_bridge_arena",
                "current_repo_head": HEAD,
            },
        )
        assert status == 200
        assert handoff["digital_baton_only"] is True
        assert handoff["target_arena_mutated"] is False
    finally:
        state.close()


def test_agent_bridge_mcp_registers_and_executes_persistence_listing(tmp_path: Path):
    names = {item["name"] for item in TOOL_DEFINITIONS}
    assert {
        "aura_checkpoint_session",
        "aura_list_checkpoints",
        "aura_restore_checkpoint",
        "aura_fork_checkpoint",
        "aura_handoff_checkpoint",
    }.issubset(names)

    bridge = PersistentAuraAgentArenaBridge(repo_root=str(tmp_path))
    response = handle_request(
        bridge,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "aura_list_checkpoints",
                "arguments": {"limit": 10},
            },
        },
    )
    assert response is not None
    assert response["result"]["isError"] is False
    assert '"count": 0' in response["result"]["content"][0]["text"]


def test_restoration_commander_never_applies_or_invokes_model(tmp_path: Path):
    coordinator = ArenaPersistenceCoordinator(str(tmp_path))
    stored = coordinator.checkpoint_mapping(
        arena_id="coding_arena",
        session_id="SESSION-1",
        repo_head=HEAD,
        state={"state": "PLAN"},
        invariant_values={"phase": "one"},
        created_at=1.0,
    )
    checkpoint_id = stored["checkpoint"]["checkpoint_id"]
    commander = RestorationCommander(str(tmp_path))

    result = commander.resume(
        checkpoint_id=checkpoint_id,
        current_repo_head=HEAD,
        current_invariant_values={"phase": "one"},
    )
    control = result["restoration_commander"]

    assert control["direct_resume_ready"] is True
    assert control["state_applied"] is False
    assert control["premium_model_invoked"] is False
    assert control["human_review_required"] is True

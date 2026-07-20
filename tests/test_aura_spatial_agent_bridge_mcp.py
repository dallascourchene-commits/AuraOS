from __future__ import annotations

from pathlib import Path

from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request
from aura_agent_arena_persistence_bridge import PersistentAuraAgentArenaBridge
from tests.test_aura_spatial_s5_arena import _construction_packet, _repo


def test_persistent_agent_bridge_exposes_typed_spatial_construction_lifecycle(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    fixture, packet = _construction_packet()
    bridge = PersistentAuraAgentArenaBridge(repo_root=str(root))
    prepared = bridge.aura_spatial_prepare_construction(
        objective="review Construction alternatives spatially",
        state=fixture.state,
        construction_runtime_packet=packet,
    )
    run_id = prepared["run_id"]
    assert bridge.aura_spatial_status(run_id)["phase"] == "PRESENT"
    response = handle_request(
        bridge,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "aura_spatial_status", "arguments": {"run_id": run_id}},
        },
    )
    assert response is not None
    assert response["result"]["isError"] is False
    receipts = bridge.aura_spatial_close()
    assert receipts[0]["renderer_cleanup_observed"] is False
    assert receipts[0]["renderer_resources_released"] is False


def test_mcp_lists_only_post_prepare_spatial_tools() -> None:
    names = {item["name"] for item in TOOL_DEFINITIONS}
    assert {
        "aura_spatial_status",
        "aura_spatial_interact",
        "aura_spatial_prove",
        "aura_spatial_decide",
        "aura_spatial_observatory",
        "aura_spatial_restore_assessment",
        "aura_spatial_dissolve",
    }.issubset(names)
    assert "aura_spatial_prepare_construction" not in names

from __future__ import annotations

import json
from typing import Any

from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request


class FakeBridge:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def aura_atomic_function_inventory(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("inventory", kwargs))
        return {"ok": True, "total_count": 321, "production_mutation": False}

    def aura_emergent_evidence(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("emergent", request))
        return {
            "ok": True,
            "packet_id": "EMERGENT-MCP",
            "grounding_ok": True,
            "production_mutation": False,
        }

    def aura_prepare_arena(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("prepare", kwargs))
        return {"ok": True, "plan_phase_hash": "phase-mcp"}


def _tool_call(bridge: FakeBridge, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = handle_request(
        bridge,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert response is not None
    return json.loads(response["result"]["content"][0]["text"])


def test_emergent_tools_are_advertised() -> None:
    definitions = {item["name"]: item for item in TOOL_DEFINITIONS}
    assert "aura_atomic_function_inventory" in definitions
    assert "aura_emergent_evidence" in definitions
    prepare = definitions["aura_prepare_arena"]["inputSchema"]["properties"]
    assert "use_emergent_evidence" in prepare
    assert "emergent_radius" in prepare
    assert "emergent_max_atomic_nodes" in prepare


def test_atomic_inventory_mcp_dispatches_complete_request() -> None:
    bridge = FakeBridge()
    result = _tool_call(
        bridge,
        "aura_atomic_function_inventory",
        {
            "query": "find compute atoms",
            "target_files": ["core.py"],
            "target_symbols": ["compute"],
            "limit": 25,
            "include_source": True,
        },
    )
    assert result["ok"] is True
    name, arguments = bridge.calls[0]
    assert name == "inventory"
    assert arguments["target_symbols"] == ["compute"]
    assert arguments["limit"] == 25


def test_emergent_evidence_mcp_dispatches_bounded_request() -> None:
    bridge = FakeBridge()
    result = _tool_call(
        bridge,
        "aura_emergent_evidence",
        {
            "objective": "Find emergent behavior around compute",
            "target_files": ["core.py"],
            "target_symbols": ["compute"],
            "target_arena": "agent_bridge",
            "radius": 2,
            "max_atomic_nodes": 80,
            "max_source_lines": 100,
            "include_source": False,
            "include_research_plan": True,
        },
    )
    assert result["packet_id"] == "EMERGENT-MCP"
    name, request = bridge.calls[0]
    assert name == "emergent"
    assert request["target_symbols"] == ["compute"]
    assert request["radius"] == 2
    assert request["max_atomic_nodes"] == 80


def test_prepare_mcp_forwards_opt_in_emergent_controls() -> None:
    bridge = FakeBridge()
    result = _tool_call(
        bridge,
        "aura_prepare_arena",
        {
            "objective": "Prepare using exact emergent closure",
            "target_file": "core.py",
            "target_symbol": "compute",
            "use_emergent_evidence": True,
            "emergent_radius": 2,
            "emergent_max_atomic_nodes": 90,
            "emergent_include_source": False,
        },
    )
    assert result["ok"] is True
    name, arguments = bridge.calls[0]
    assert name == "prepare"
    assert arguments["use_emergent_evidence"] is True
    assert arguments["emergent_radius"] == 2
    assert arguments["emergent_max_atomic_nodes"] == 90
    assert arguments["emergent_include_source"] is False

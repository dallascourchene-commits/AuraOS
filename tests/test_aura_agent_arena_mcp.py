"""
Tests for the Aura Agent Arena Bridge MCP server.

Verifies tool list, JSON-RPC protocol handling, and that the server
correctly dispatches tool calls to the bridge.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_mcp import (
    MCP_SERVER_VERSION,
    PROTOCOL_VERSION,
    SERVER_NAME,
    TOOL_DEFINITIONS,
    handle_request,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def bridge() -> AuraAgentArenaBridge:
    return AuraAgentArenaBridge(repo_root=REPO_ROOT)


def _has_codemap() -> bool:
    return (REPO_ROOT / ".aura" / "CODEMAP.json").exists()


# ---------------------------------------------------------------------------
# Test: MCP tool list contains all expected tools
# ---------------------------------------------------------------------------

def test_mcp_tool_definitions_complete():
    tool_names = [t["name"] for t in TOOL_DEFINITIONS]
    expected = [
        "aura_repo_digest",
        "aura_prepare_arena",
        "aura_get_micro_context",
        "aura_search_code",
        "aura_read_slice",
        "aura_stage_patch",
        "aura_verify_arena",
        "aura_repair_packet",
        "aura_hotswap_status",
        "aura_export_icm",
        "aura_fireworks_patch_worker",
    ]
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"


def test_mcp_tool_definitions_have_schema():
    for tool in TOOL_DEFINITIONS:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


# ---------------------------------------------------------------------------
# Test: initialize request returns server info
# ---------------------------------------------------------------------------

def test_initialize_returns_server_info(bridge: AuraAgentArenaBridge):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
    }
    response = handle_request(bridge, request)
    assert response is not None
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    result = response["result"]
    assert result["protocolVersion"] == PROTOCOL_VERSION
    assert result["serverInfo"]["name"] == SERVER_NAME
    assert "capabilities" in result


# ---------------------------------------------------------------------------
# Test: tools/list returns tool definitions
# ---------------------------------------------------------------------------

def test_tools_list_returns_definitions(bridge: AuraAgentArenaBridge):
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    }
    response = handle_request(bridge, request)
    assert response is not None
    assert response["id"] == 2
    tools = response["result"]["tools"]
    assert len(tools) == len(TOOL_DEFINITIONS)


# ---------------------------------------------------------------------------
# Test: tools/call dispatches to bridge
# ---------------------------------------------------------------------------

def test_tools_call_repo_digest(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "aura_repo_digest",
            "arguments": {},
        },
    }
    response = handle_request(bridge, request)
    assert response is not None
    assert response["id"] == 3
    content = response["result"]["content"]
    assert len(content) > 0
    assert content[0]["type"] == "text"
    # Parse the text content as JSON.
    result = json.loads(content[0]["text"])
    assert result["ok"] is True
    assert result["version"] == "AURA_AGENT_ARENA_BRIDGE_V1"


# ---------------------------------------------------------------------------
# Test: tools/call with unknown tool returns error
# ---------------------------------------------------------------------------

def test_tools_call_unknown_tool(bridge: AuraAgentArenaBridge):
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "nonexistent_tool",
            "arguments": {},
        },
    }
    response = handle_request(bridge, request)
    assert response is not None
    assert "error" in response
    assert response["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Test: unknown method returns error
# ---------------------------------------------------------------------------

def test_unknown_method(bridge: AuraAgentArenaBridge):
    request = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "unknown/method",
    }
    response = handle_request(bridge, request)
    assert response is not None
    assert "error" in response
    assert response["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Test: initialized notification returns None
# ---------------------------------------------------------------------------

def test_initialized_notification(bridge: AuraAgentArenaBridge):
    request = {
        "jsonrpc": "2.0",
        "method": "initialized",
    }
    response = handle_request(bridge, request)
    assert response is None  # Notifications get no response


# ---------------------------------------------------------------------------
# Test: tools/call read_slice returns content
# ---------------------------------------------------------------------------

def test_tools_call_read_slice(bridge: AuraAgentArenaBridge):
    request = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "aura_read_slice",
            "arguments": {
                "file": "aura_fst_routing.py",
                "symbol": "RoutingFrame",
            },
        },
    }
    response = handle_request(bridge, request)
    assert response is not None
    content = response["result"]["content"]
    result = json.loads(content[0]["text"])
    assert result["ok"] is True
    assert result["file"] == "aura_fst_routing.py"


# ---------------------------------------------------------------------------
# Test: tools/call search_code returns results
# ---------------------------------------------------------------------------

def test_tools_call_search_code(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    request = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "aura_search_code",
            "arguments": {
                "query": "RoutingFrame",
                "search_kind": "symbol",
            },
        },
    }
    response = handle_request(bridge, request)
    assert response is not None
    content = response["result"]["content"]
    result = json.loads(content[0]["text"])
    assert result["ok"] is True
    assert "results" in result


# ---------------------------------------------------------------------------
# Test: isError flag is set for error packets
# ---------------------------------------------------------------------------

def test_is_error_flag_set(bridge: AuraAgentArenaBridge):
    request = {
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "aura_read_slice",
            "arguments": {
                "file": "aura_node.py",  # blocked hub file
            },
        },
    }
    response = handle_request(bridge, request)
    assert response is not None
    assert response["result"]["isError"] is True
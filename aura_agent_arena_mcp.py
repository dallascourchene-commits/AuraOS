"""
Aura Agent Arena Bridge — MCP Server (stdio JSON-RPC compatible).

Exposes all Aura Agent Arena Bridge tools via a minimal stdio JSON-RPC server
that can later be swapped for the official MCP Python SDK.

Protocol:
  - Reads JSON-RPC 2.0 requests from stdin (one per line).
  - Writes JSON-RPC 2.0 responses to stdout (one per line).
  - Supports: initialize, tools/list, tools/call.
  - No tool may mutate production files directly.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from aura_agent_arena_bridge import AuraAgentArenaBridge, BRIDGE_VERSION
from aura_agent_arena_errors import is_error_packet
from aura_agent_arena_fireworks import fireworks_patch_worker

_LOG = logging.getLogger(__name__)

MCP_SERVER_VERSION = "AURA_AGENT_ARENA_MCP_V1"
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "aura-agent-arena-bridge"
SERVER_INFO = {
    "name": SERVER_NAME,
    "version": BRIDGE_VERSION,
}

# Tool name → handler mapping.
# Each handler receives (bridge, arguments) and returns a dict.
_TOOL_HANDLERS: dict[str, Any] = {}


def _register_tool(name: str):
    """Decorator to register a tool handler."""
    def decorator(func):
        _TOOL_HANDLERS[name] = func
        return func
    return decorator


# ---------------------------------------------------------------------------
# Tool definitions (for tools/list)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "aura_repo_digest",
        "description": "Return a tiny, token-sparing repo orientation packet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_hubs": {"type": "boolean", "default": True},
                "max_lines": {"type": "integer", "default": 120},
            },
        },
    },
    {
        "name": "aura_prepare_arena",
        "description": "Run Aura's own prepare pipeline for a coding task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "target_file": {"type": "string"},
                "target_symbol": {"type": "string"},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                "risk_map": {"type": "array", "items": {"type": "string"}},
                "constraints": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["objective"],
        },
    },
    {
        "name": "aura_get_micro_context",
        "description": "Return the exact compressed context for one Act Capsule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
                "task_id": {"type": "string"},
                "depth": {"type": "integer", "default": 1},
                "format": {"type": "string", "default": "both"},
                "max_tokens_est": {"type": "integer", "default": 2000},
            },
            "required": ["plan_phase_hash", "task_id"],
        },
    },
    {
        "name": "aura_search_code",
        "description": "Search through Aura's CODEMAP without dumping files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "search_kind": {"type": "string", "default": "symbol"},
                "max_results": {"type": "integer", "default": 10},
                "include_neighbors": {"type": "boolean", "default": True},
            },
            "required": ["query"],
        },
    },
    {
        "name": "aura_read_slice",
        "description": "Read only authorized slices from source files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string"},
                "symbol": {"type": "string"},
                "line_start": {"type": "integer"},
                "line_end": {"type": "integer"},
                "max_lines": {"type": "integer", "default": 120},
            },
            "required": ["file"],
        },
    },
    {
        "name": "aura_stage_patch",
        "description": "Stage a patch through Aura's Refactor Arena boundary logic.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
                "task_id": {"type": "string"},
                "owner": {"type": "string", "default": "external_agent"},
                "diff": {"type": "string"},
                "affected_files": {"type": "array", "items": {"type": "string"}},
                "affected_symbols": {"type": "array", "items": {"type": "string"}},
                "tests": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["plan_phase_hash", "task_id", "diff", "affected_files"],
        },
    },
    {
        "name": "aura_verify_arena",
        "description": "Run verifiers/tests and return compressed machine-readable result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
                "test_scope": {"type": "string", "default": "focused"},
                "runner": {"type": "string", "default": "pytest"},
                "max_log_lines": {"type": "integer", "default": 80},
            },
            "required": ["plan_phase_hash"],
        },
    },
    {
        "name": "aura_repair_packet",
        "description": "Return the minimum context needed to repair a failed patch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
                "task_id": {"type": "string"},
                "failure_id": {"type": "string"},
                "max_tokens_est": {"type": "integer", "default": 1500},
            },
            "required": ["plan_phase_hash", "task_id"],
        },
    },
    {
        "name": "aura_hotswap_status",
        "description": "Return whether the staged transaction is ready for promotion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
            },
            "required": ["plan_phase_hash"],
        },
    },
    {
        "name": "aura_export_icm",
        "description": "Export the current arena transaction into ICM audit workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
                "workspace_root": {"type": "string"},
            },
            "required": ["plan_phase_hash"],
        },
    },
    {
        "name": "aura_fireworks_patch_worker",
        "description": "Call a Fireworks model for a compressed micro-patch (candidate diff only).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "compressed_context": {"type": "string"},
                "instruction": {"type": "string"},
                "model_tier": {"type": "string", "default": "fast"},
                "max_output_tokens": {"type": "integer", "default": 2048},
            },
            "required": ["task_id", "compressed_context", "instruction"],
        },
    },
    {
        "name": "aura_find_affordances",
        "description": "Find internal Aura tools that should be considered before inventing generic solutions. Returns top 3-7 advisory affordance cards.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "target_files": {"type": "array", "items": {"type": "string"}},
                "target_symbols": {"type": "array", "items": {"type": "string"}},
                "include_affordances": {"type": "boolean", "default": True},
                "top_k": {"type": "integer", "default": 7},
            },
            "required": ["objective"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@_register_tool("aura_repo_digest")
def _handle_repo_digest(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_repo_digest(
        include_hubs=bool(args.get("include_hubs", True)),
        max_lines=int(args.get("max_lines", 120)),
    )


@_register_tool("aura_prepare_arena")
def _handle_prepare_arena(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_prepare_arena(
        objective=str(args.get("objective", "")),
        target_file=args.get("target_file"),
        target_symbol=args.get("target_symbol"),
        acceptance_criteria=args.get("acceptance_criteria"),
        risk_map=args.get("risk_map"),
        constraints=args.get("constraints"),
    )


@_register_tool("aura_get_micro_context")
def _handle_get_micro_context(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_get_micro_context(
        plan_phase_hash=str(args.get("plan_phase_hash", "")),
        task_id=str(args.get("task_id", "")),
        depth=int(args.get("depth", 1)),
        format=str(args.get("format", "both")),
        max_tokens_est=int(args.get("max_tokens_est", 2000)),
    )


@_register_tool("aura_search_code")
def _handle_search_code(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_search_code(
        query=str(args.get("query", "")),
        search_kind=str(args.get("search_kind", "symbol")),
        max_results=int(args.get("max_results", 10)),
        include_neighbors=bool(args.get("include_neighbors", True)),
    )


@_register_tool("aura_read_slice")
def _handle_read_slice(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_read_slice(
        file=str(args.get("file", "")),
        symbol=args.get("symbol"),
        line_start=args.get("line_start"),
        line_end=args.get("line_end"),
        max_lines=int(args.get("max_lines", 120)),
    )


@_register_tool("aura_stage_patch")
def _handle_stage_patch(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_stage_patch(
        plan_phase_hash=str(args.get("plan_phase_hash", "")),
        task_id=str(args.get("task_id", "")),
        owner=str(args.get("owner", "external_agent")),
        diff=str(args.get("diff", "")),
        affected_files=list(args.get("affected_files", []) or []),
        affected_symbols=args.get("affected_symbols"),
        tests=args.get("tests"),
    )


@_register_tool("aura_verify_arena")
def _handle_verify_arena(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_verify_arena(
        plan_phase_hash=str(args.get("plan_phase_hash", "")),
        test_scope=str(args.get("test_scope", "focused")),
        runner=str(args.get("runner", "pytest")),
        max_log_lines=int(args.get("max_log_lines", 80)),
    )


@_register_tool("aura_repair_packet")
def _handle_repair_packet(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_repair_packet(
        plan_phase_hash=str(args.get("plan_phase_hash", "")),
        task_id=str(args.get("task_id", "")),
        failure_id=args.get("failure_id"),
        max_tokens_est=int(args.get("max_tokens_est", 1500)),
    )


@_register_tool("aura_hotswap_status")
def _handle_hotswap_status(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_hotswap_status(
        plan_phase_hash=str(args.get("plan_phase_hash", "")),
    )


@_register_tool("aura_export_icm")
def _handle_export_icm(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_export_icm(
        plan_phase_hash=str(args.get("plan_phase_hash", "")),
        workspace_root=args.get("workspace_root"),
    )


@_register_tool("aura_fireworks_patch_worker")
def _handle_fireworks_patch(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return fireworks_patch_worker(
        task_id=str(args.get("task_id", "")),
        compressed_context=str(args.get("compressed_context", "")),
        instruction=str(args.get("instruction", "")),
        model_tier=str(args.get("model_tier", "fast")),
        max_output_tokens=int(args.get("max_output_tokens", 2048)),
    )


@_register_tool("aura_find_affordances")
def _handle_find_affordances(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_find_affordances(
        objective=str(args.get("objective", "")),
        target_files=args.get("target_files"),
        target_symbols=args.get("target_symbols"),
        include_affordances=bool(args.get("include_affordances", True)),
        top_k=int(args.get("top_k", 7)),
    )


# ---------------------------------------------------------------------------
# JSON-RPC server
# ---------------------------------------------------------------------------

def _make_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _make_error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(bridge: AuraAgentArenaBridge, request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle a single JSON-RPC request and return a response dict (or None for notifications)."""
    request_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {}) or {}

    if method == "initialize":
        return _make_response(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })

    if method == "initialized":
        # Notification — no response needed.
        return None

    if method == "tools/list":
        return _make_response(request_id, {"tools": TOOL_DEFINITIONS})

    if method == "tools/call":
        tool_name = str(params.get("name", ""))
        arguments = params.get("arguments", {}) or {}

        handler = _TOOL_HANDLERS.get(tool_name)
        if handler is None:
            return _make_error_response(request_id, -32601, f"Unknown tool: {tool_name}")

        try:
            result = handler(bridge, arguments)
            # Error packets are still valid results (ok=False).
            return _make_response(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, default=str, ensure_ascii=False),
                    }
                ],
                "isError": is_error_packet(result),
            })
        except Exception as exc:  # noqa: BLE001
            return _make_error_response(request_id, -32603, f"Tool execution error: {exc}")

    return _make_error_response(request_id, -32601, f"Unknown method: {method}")


def serve_stdio(bridge: AuraAgentArenaBridge | None = None) -> None:
    """Run the stdio JSON-RPC server loop."""
    if bridge is None:
        bridge = AuraAgentArenaBridge()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            # Skip malformed lines.
            continue

        response = handle_request(bridge, request)
        if response is not None:
            sys.stdout.write(json.dumps(response, default=str) + "\n")
            sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="Aura Agent Arena Bridge MCP Server")
    parser.add_argument("--list-tools", action="store_true", help="List all available tools and exit")
    args = parser.parse_args(argv)

    if args.list_tools:
        print(json.dumps(TOOL_DEFINITIONS, indent=2))
        return 0

    serve_stdio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
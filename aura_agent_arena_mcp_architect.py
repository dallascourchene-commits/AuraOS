"""Unified MCP entrypoint for Aura architecture, slice sessions, and model routing."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import aura_agent_arena_mcp_external_llm as session_mcp
from aura_arena_architect_connector import AuraArenaArchitectConnector

base_mcp = session_mcp.base_mcp
MCP_EXTENSION_VERSION = "AURA_AGENT_ARENA_ARCHITECT_MCP_V1"

ARCHITECT_TOOL_DEFINITIONS = [
    {
        "name": "aura_architect_compare_plans",
        "description": "Compare multiple bounded refactor plans with Council V3 selective critic routing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "candidates": {"type": "array", "items": {"type": "object"}},
                "required_capabilities": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["objective", "candidates"],
        },
    },
    {
        "name": "aura_architect_prepare",
        "description": "Select a Council V3 plan and prepare it through the Coding Arena bridge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "candidates": {"type": "array", "items": {"type": "object"}},
                "required_capabilities": {"type": "array", "items": {"type": "string"}},
                "target_file": {"type": "string"},
                "target_symbol": {"type": "string"},
            },
            "required": ["objective", "candidates"],
        },
    },
    {
        "name": "aura_native_model_route",
        "description": (
            "Ask Aura's Model Cognome to select the best admitted DIRECT, CASCADE, "
            "PANEL, or ZERO_MODEL route from verified outcome evidence."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "purpose_digest": {"type": "string"},
                "target_files": {"type": "array", "items": {"type": "string"}},
                "target_symbols": {"type": "array", "items": {"type": "string"}},
                "task_fields": {"type": "object"},
                "token_budget": {"type": "integer", "default": 2400},
                "forced_model": {"type": "string"},
            },
            "required": ["objective", "purpose_digest"],
        },
    },
    {
        "name": "aura_native_model_execute",
        "description": (
            "Execute the Model Cognome route. Defaults to SHADOW; PAIRED_LIVE "
            "requires an explicit content-addressed authorization."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "purpose_digest": {"type": "string"},
                "execution_mode": {"type": "string", "default": "SHADOW"},
                "authorization": {"type": "object"},
                "target_files": {"type": "array", "items": {"type": "string"}},
                "target_symbols": {"type": "array", "items": {"type": "string"}},
                "task_fields": {"type": "object"},
                "token_budget": {"type": "integer", "default": 2400},
                "forced_model": {"type": "string"},
            },
            "required": ["objective", "purpose_digest"],
        },
    },
]

_CONNECTORS: dict[int, AuraArenaArchitectConnector] = {}


def _connector_for(bridge: Any) -> AuraArenaArchitectConnector:
    key = id(bridge)
    connector = _CONNECTORS.get(key)
    if connector is None:
        connector = AuraArenaArchitectConnector(
            repo_root=Path(getattr(bridge, "repo_root", ".")),
            bridge=bridge,
        )
        _CONNECTORS[key] = connector
    return connector


def _compare(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).compare_plans(
        objective=str(args.get("objective", "")),
        candidates=list(args.get("candidates") or []),
        required_capabilities=list(args.get("required_capabilities") or []),
    )


def _prepare(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).prepare_refactor(
        objective=str(args.get("objective", "")),
        candidates=list(args.get("candidates") or []),
        required_capabilities=list(args.get("required_capabilities") or []),
        target_file=args.get("target_file"),
        target_symbol=args.get("target_symbol"),
    )


def _route_model(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).route_native_model(
        objective=str(args.get("objective", "")),
        purpose_digest=str(args.get("purpose_digest", "")),
        target_files=args.get("target_files"),
        target_symbols=args.get("target_symbols"),
        task_fields=args.get("task_fields"),
        token_budget=int(args.get("token_budget", 2400)),
        forced_model=args.get("forced_model"),
    )


def _execute_model(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).execute_native_model(
        objective=str(args.get("objective", "")),
        purpose_digest=str(args.get("purpose_digest", "")),
        execution_mode=str(args.get("execution_mode", "SHADOW")),
        authorization=args.get("authorization"),
        target_files=args.get("target_files"),
        target_symbols=args.get("target_symbols"),
        task_fields=args.get("task_fields"),
        token_budget=int(args.get("token_budget", 2400)),
        forced_model=args.get("forced_model"),
    )


def install_architect_tools() -> None:
    known = {item.get("name") for item in base_mcp.TOOL_DEFINITIONS}
    for definition in ARCHITECT_TOOL_DEFINITIONS:
        if definition["name"] not in known:
            base_mcp.TOOL_DEFINITIONS.append(definition)
    base_mcp._TOOL_HANDLERS.update(  # noqa: SLF001 - deliberate MCP extension seam
        {
            "aura_architect_compare_plans": _compare,
            "aura_architect_prepare": _prepare,
            "aura_native_model_route": _route_model,
            "aura_native_model_execute": _execute_model,
        }
    )


install_architect_tools()


def main(argv: list[str] | None = None) -> int:
    return base_mcp.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

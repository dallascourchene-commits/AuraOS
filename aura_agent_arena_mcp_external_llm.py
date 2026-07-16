"""Add external-LLM slice sessions to the canonical Agent Arena MCP server.

Run this entrypoint instead of the base server when an MCP client should receive
the existing Agent Arena tools plus the higher-level open/next/submit/status/
export session loop. The handlers reuse the same AuraAgentArenaBridge instance,
so phase hashes, staged patches, verification state, and Arena boundaries remain
continuous across model turns.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import aura_agent_arena_mcp as base_mcp
from aura_external_llm_session import AuraExternalLLMSessionManager

MCP_EXTENSION_VERSION = "AURA_AGENT_ARENA_EXTERNAL_LLM_MCP_V1"

SESSION_TOOL_DEFINITIONS = [
    {
        "name": "aura_llm_session_open",
        "description": (
            "Open a guarded Aura coding session and return one leased model turn "
            "with bounded source/test slices instead of the repository."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "target_file": {"type": "string"},
                "target_symbol": {"type": "string"},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                "risk_map": {"type": "array", "items": {"type": "string"}},
                "constraints": {"type": "array", "items": {"type": "string"}},
                "provider": {"type": "string", "default": "external"},
                "model": {"type": "string", "default": ""},
                "max_context_tokens": {"type": "integer", "default": 2200},
                "max_output_tokens": {"type": "integer", "default": 2400},
                "max_turns": {"type": "integer", "default": 12},
            },
            "required": ["objective"],
        },
    },
    {
        "name": "aura_llm_session_next",
        "description": "Return the current pending slice-leased turn.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "aura_llm_session_submit",
        "description": (
            "Submit the pending model response. Aura stages and verifies it, "
            "then returns completion or the next bounded repair turn."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "turn_id": {"type": "string"},
                "response": {"type": "string"},
                "provider_usage": {"type": "object"},
            },
            "required": ["session_id", "turn_id", "response"],
        },
    },
    {
        "name": "aura_llm_session_status",
        "description": "Return safe public session state and turn history.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "aura_llm_session_export",
        "description": "Export session evidence to a reviewable JSON file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "required": ["session_id", "output_path"],
        },
    },
]

_MANAGERS: dict[int, AuraExternalLLMSessionManager] = {}


def _manager_for(bridge: Any) -> AuraExternalLLMSessionManager:
    key = id(bridge)
    manager = _MANAGERS.get(key)
    if manager is None:
        manager = AuraExternalLLMSessionManager(
            repo_root=Path(getattr(bridge, "repo_root", ".")),
            bridge=bridge,
        )
        _MANAGERS[key] = manager
    return manager


def _open(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _manager_for(bridge).open_session(
        objective=str(args.get("objective", "")),
        target_file=args.get("target_file"),
        target_symbol=args.get("target_symbol"),
        acceptance_criteria=args.get("acceptance_criteria"),
        risk_map=args.get("risk_map"),
        constraints=args.get("constraints"),
        provider=str(args.get("provider", "external")),
        model=str(args.get("model", "")),
        max_context_tokens=int(args.get("max_context_tokens", 2200)),
        max_output_tokens=int(args.get("max_output_tokens", 2400)),
        max_turns=int(args.get("max_turns", 12)),
    )


def _next(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _manager_for(bridge).next_turn(str(args.get("session_id", "")))


def _submit(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _manager_for(bridge).submit_response(
        session_id=str(args.get("session_id", "")),
        turn_id=str(args.get("turn_id", "")),
        response=str(args.get("response", "")),
        provider_usage=args.get("provider_usage"),
    )


def _status(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _manager_for(bridge).get_session(str(args.get("session_id", "")))


def _export(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _manager_for(bridge).export_session(
        str(args.get("session_id", "")),
        str(args.get("output_path", "")),
    )


def install_external_llm_tools() -> None:
    known = {item.get("name") for item in base_mcp.TOOL_DEFINITIONS}
    for definition in SESSION_TOOL_DEFINITIONS:
        if definition["name"] not in known:
            base_mcp.TOOL_DEFINITIONS.append(definition)
    base_mcp._TOOL_HANDLERS.update(  # noqa: SLF001 - deliberate MCP extension seam
        {
            "aura_llm_session_open": _open,
            "aura_llm_session_next": _next,
            "aura_llm_session_submit": _submit,
            "aura_llm_session_status": _status,
            "aura_llm_session_export": _export,
        }
    )


install_external_llm_tools()


def main(argv: list[str] | None = None) -> int:
    return base_mcp.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

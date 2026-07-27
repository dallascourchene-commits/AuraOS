"""Unified MCP entrypoint for Aura Architect, Surgeon, sessions, and model routing.

Third-party coding agents use the same canonical Architect service as native Aura,
but this MCP boundary always identifies them as external. They receive bounded
controls, frozen selected plans, slice-leased Surgeon turns, verifier-driven
repairs, and local output recording without production or promotion authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import aura_agent_arena_mcp_external_llm as session_mcp
from aura_arena_architect_connector import AuraArenaArchitectConnector

base_mcp = session_mcp.base_mcp
MCP_EXTENSION_VERSION = "AURA_AGENT_ARENA_ARCHITECT_MCP_V2"
_EXTERNAL_SURFACE = "mcp_external"

_CONTROL_SCHEMA = {
    "type": "object",
    "properties": {
        "council_mode": {
            "type": "string",
            "enum": ["OFF", "AUTO", "SELECTIVE_V3", "FULL_V2"],
        },
        "council_call_budget": {"type": "integer", "minimum": 0, "maximum": 32},
        "critic_lanes": {"type": "array", "items": {"type": "string"}},
        "surgeon_mode": {
            "type": "string",
            "enum": ["PLAN_ONLY", "PROPOSE", "STAGE_AND_VERIFY"],
        },
        "surgeon_max_turns": {"type": "integer", "minimum": 1, "maximum": 40},
        "surgeon_max_local_repairs": {"type": "integer", "minimum": 0, "maximum": 8},
        "surgeon_context_tokens": {"type": "integer", "minimum": 256, "maximum": 16000},
        "surgeon_output_tokens": {"type": "integer", "minimum": 128, "maximum": 16000},
        "council_replan_allowed": {"type": "boolean"},
        "record_outputs": {"type": "boolean"},
        "output_root": {"type": "string"},
    },
}

ARCHITECT_TOOL_DEFINITIONS = [
    {
        "name": "aura_architect_control_validate",
        "description": "Validate bounded Council and Surgeon controls for an external MCP client.",
        "inputSchema": {
            "type": "object",
            "properties": {"control": _CONTROL_SCHEMA},
        },
    },
    {
        "name": "aura_architect_compare_plans",
        "description": (
            "Compare frozen refactor plans through Aura's controlled Architect rubric, "
            "record every candidate locally, and return the selected plan."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "candidates": {"type": "array", "items": {"type": "object"}},
                "required_capabilities": {"type": "array", "items": {"type": "string"}},
                "control": _CONTROL_SCHEMA,
                "run_id": {"type": "string"},
                "bilateral_contract": {"type": "object"},
                "confirmation_session_id": {"type": "string"},
            },
            "required": ["objective", "candidates"],
        },
    },
    {
        "name": "aura_architect_prepare",
        "description": (
            "Select a plan, bind it to exact Act Capsules, and prepare the same governed "
            "Arena used by native Aura."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "candidates": {"type": "array", "items": {"type": "object"}},
                "required_capabilities": {"type": "array", "items": {"type": "string"}},
                "target_file": {"type": "string"},
                "target_symbol": {"type": "string"},
                "control": _CONTROL_SCHEMA,
                "run_id": {"type": "string"},
                "bilateral_contract": {"type": "object"},
                "confirmation_session_id": {"type": "string"},
            },
            "required": ["objective", "candidates"],
        },
    },
    {
        "name": "aura_architect_surgeon_open",
        "description": (
            "Freeze an Architect plan and open a slice-leased Surgeon session. Full generated "
            "outputs are stored in the local Refactor Output Vault."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "candidates": {"type": "array", "items": {"type": "object"}},
                "required_capabilities": {"type": "array", "items": {"type": "string"}},
                "provider": {"type": "string", "default": "external"},
                "model": {"type": "string", "default": ""},
                "control": _CONTROL_SCHEMA,
                "run_id": {"type": "string"},
                "bilateral_contract": {"type": "object"},
                "confirmation_session_id": {"type": "string"},
            },
            "required": ["objective", "candidates"],
        },
    },
    {
        "name": "aura_architect_surgeon_next",
        "description": "Return the current bounded Surgeon turn.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "aura_architect_surgeon_submit",
        "description": (
            "Submit generated code for staging, verification, local repair or Council replan, "
            "and local evidence recording."
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
        "name": "aura_architect_surgeon_status",
        "description": "Return controlled Surgeon state, Chronicle evidence, and State Ledger metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "aura_architect_council_replan",
        "description": "Apply a bounded Council replan only when the control profile permits it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "remaining_act_capsules": {"type": "array", "items": {"type": "object"}},
                "rationale": {"type": "string"},
                "prompt": {"type": "string"},
                "response": {"type": "string"},
                "provider_usage": {"type": "object"},
            },
            "required": ["session_id", "remaining_act_capsules", "rationale"],
        },
    },
    {
        "name": "aura_refactor_outputs_list",
        "description": "List local private refactor-output runs available to the Human Agent Arena.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}},
        },
    },
    {
        "name": "aura_refactor_output_load",
        "description": "Load one bounded artifact from the local Refactor Output Vault for review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"},
                "max_bytes": {"type": "integer", "minimum": 1, "maximum": 5000000},
            },
            "required": ["relative_path"],
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
            "requires explicit content-addressed authorization."
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


def _control(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).validate_control(args.get("control"), surface=_EXTERNAL_SURFACE)


def _compare(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).compare_plans(
        objective=str(args.get("objective", "")),
        candidates=list(args.get("candidates") or []),
        required_capabilities=list(args.get("required_capabilities") or []),
        control=args.get("control"),
        surface=_EXTERNAL_SURFACE,
        run_id=str(args.get("run_id", "")),
        bilateral_contract=args.get("bilateral_contract"),
        confirmation_session_id=str(args.get("confirmation_session_id", "")),
    )


def _prepare(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).prepare_refactor(
        objective=str(args.get("objective", "")),
        candidates=list(args.get("candidates") or []),
        required_capabilities=list(args.get("required_capabilities") or []),
        target_file=args.get("target_file"),
        target_symbol=args.get("target_symbol"),
        control=args.get("control"),
        surface=_EXTERNAL_SURFACE,
        run_id=str(args.get("run_id", "")),
        bilateral_contract=args.get("bilateral_contract"),
        confirmation_session_id=str(args.get("confirmation_session_id", "")),
    )


def _open_surgeon(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).open_surgeon_session(
        objective=str(args.get("objective", "")),
        candidates=list(args.get("candidates") or []),
        required_capabilities=list(args.get("required_capabilities") or []),
        provider=str(args.get("provider", "external")),
        model=str(args.get("model", "")),
        control=args.get("control"),
        surface=_EXTERNAL_SURFACE,
        run_id=str(args.get("run_id", "")),
        bilateral_contract=args.get("bilateral_contract"),
        confirmation_session_id=str(args.get("confirmation_session_id", "")),
    )


def _surgeon_next(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).surgeon_next(str(args.get("session_id", "")))


def _surgeon_submit(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).surgeon_submit(
        session_id=str(args.get("session_id", "")),
        turn_id=str(args.get("turn_id", "")),
        response=str(args.get("response", "")),
        provider_usage=args.get("provider_usage"),
    )


def _surgeon_status(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).surgeon_status(str(args.get("session_id", "")))


def _council_replan(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).surgeon_replan(
        session_id=str(args.get("session_id", "")),
        remaining_act_capsules=list(args.get("remaining_act_capsules") or []),
        rationale=str(args.get("rationale", "")),
        prompt=str(args.get("prompt", "")),
        response=str(args.get("response", "")),
        provider_usage=dict(args.get("provider_usage") or {}),
    )


def _list_outputs(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).list_refactor_outputs(limit=int(args.get("limit", 50)))


def _load_output(bridge: Any, args: dict[str, Any]) -> dict[str, Any]:
    return _connector_for(bridge).load_refactor_output(
        str(args.get("relative_path", "")),
        max_bytes=int(args.get("max_bytes", 2_000_000)),
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
            "aura_architect_control_validate": _control,
            "aura_architect_compare_plans": _compare,
            "aura_architect_prepare": _prepare,
            "aura_architect_surgeon_open": _open_surgeon,
            "aura_architect_surgeon_next": _surgeon_next,
            "aura_architect_surgeon_submit": _surgeon_submit,
            "aura_architect_surgeon_status": _surgeon_status,
            "aura_architect_council_replan": _council_replan,
            "aura_refactor_outputs_list": _list_outputs,
            "aura_refactor_output_load": _load_output,
            "aura_native_model_route": _route_model,
            "aura_native_model_execute": _execute_model,
        }
    )


install_architect_tools()


def main(argv: list[str] | None = None) -> int:
    return base_mcp.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

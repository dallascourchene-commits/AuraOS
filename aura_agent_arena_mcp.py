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

from collections.abc import Mapping
import json
import logging
import sys
from typing import Any

from aura_agent_arena_bridge import BRIDGE_VERSION
from aura_agent_arena_errors import is_error_packet
from aura_agent_arena_fireworks import fireworks_patch_worker
from aura_agent_arena_persistence_bridge import (
    PersistentAuraAgentArenaBridge as AuraAgentArenaBridge,
)

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


def _strict_bool_arg(
    args: dict[str, Any],
    key: str,
    *,
    default: bool,
) -> bool:
    value = args.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be a boolean")


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
                "use_emergent_evidence": {"type": "boolean", "default": False},
                "emergent_radius": {"type": "integer", "minimum": 0, "maximum": 3, "default": 1},
                "emergent_max_atomic_nodes": {"type": "integer", "minimum": 1, "maximum": 200, "default": 48},
                "emergent_include_source": {"type": "boolean", "default": False},
                "emergent_include_research_plan": {"type": "boolean", "default": True},
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
    {
        "name": "aura_checkpoint_session",
        "description": "Persist a prepared Agent Bridge session as a verifier-bound checkpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
                "repo_head": {"type": "string"},
                "parent_checkpoint_id": {"type": "string"},
                "branch_name": {"type": "string"},
            },
            "required": ["plan_phase_hash", "repo_head"],
        },
    },
    {
        "name": "aura_list_checkpoints",
        "description": "List Agent Bridge checkpoints without returning checkpoint payloads.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
        },
    },
    {
        "name": "aura_restore_checkpoint",
        "description": "Return a reviewable restore assessment; never apply state automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string"},
                "current_repo_head": {"type": "string"},
                "current_invariant_values": {"type": "object"},
                "remaining_context_tokens": {"type": "integer", "default": 0},
                "surgeon_context_limit": {"type": "integer", "default": 0},
            },
            "required": ["checkpoint_id", "current_repo_head"],
        },
    },
    {
        "name": "aura_fork_checkpoint",
        "description": "Create a named child checkpoint for a what-if branch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string"},
                "branch_name": {"type": "string"},
                "repo_head": {"type": "string"},
            },
            "required": ["checkpoint_id", "branch_name"],
        },
    },
    {
        "name": "aura_handoff_checkpoint",
        "description": "Create a payload-free digital baton for another Aura arena.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string"},
                "target_arena_id": {"type": "string"},
                "current_repo_head": {"type": "string"},
                "current_invariant_values": {"type": "object"},
            },
            "required": ["checkpoint_id", "target_arena_id", "current_repo_head"],
        },
    },
    {
        "name": "aura_spatial_status",
        "description": "Return one governed Spatial Arena run status without raw payloads.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "aura_spatial_interact",
        "description": "Compile a review-only interaction for an existing Spatial Arena run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "action": {"type": "string"},
                "target_entity_ids": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object"},
            },
            "required": ["run_id", "action", "target_entity_ids"],
        },
    },
    {
        "name": "aura_spatial_prove",
        "description": "Record bounded render evidence and an assessment-only checkpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "repo_head": {"type": "string"},
                "outcome": {"type": "string", "default": "PRESENTED"},
                "evidence_class": {"type": "string", "default": "DERIVED"},
                "metrics": {"type": "object"},
                "branch_name": {"type": "string"},
            },
            "required": ["run_id", "repo_head"],
        },
    },
    {
        "name": "aura_spatial_prove_browser_telemetry",
        "description": "Validate exact browser telemetry and record empirical Spatial proof.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "telemetry_packet": {"type": "object"},
                "repo_head": {"type": "string"},
                "branch_name": {"type": "string"},
            },
            "required": ["run_id", "telemetry_packet", "repo_head"],
        },
    },
    {
        "name": "aura_spatial_decide",
        "description": "Compile a human/domain decision packet without applying it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "decision": {"type": "string"},
                "decision_ref": {"type": "string"},
            },
            "required": ["run_id", "decision"],
        },
    },
    {
        "name": "aura_spatial_observatory",
        "description": "Return a read-only Spatial Arena evidence and cost projection.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "aura_spatial_restore_assessment",
        "description": "Assess a Spatial checkpoint without automatic resume.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "current_repo_head": {"type": "string"},
            },
            "required": ["run_id", "current_repo_head"],
        },
    },
    {
        "name": "aura_spatial_dissolve",
        "description": "Dissolve a Spatial run only with exact renderer cleanup evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "renderer_cleanup_receipt": {"type": "object"},
                "reason_code": {"type": "string"},
            },
            "required": ["run_id", "renderer_cleanup_receipt"],
        },
    },
    {
        "name": "aura_atomic_function_inventory",
        "description": "Enumerate exact atomic functions, methods, async functions, and nested functions with spans and hashes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "default": ""},
                "target_files": {"type": "array", "items": {"type": "string"}},
                "target_symbols": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                "include_source": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "aura_emergent_evidence",
        "description": "Resolve the Capability Connectome, exact atomic dependency closure, source slices, emergent audit, and research gaps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "target_files": {"type": "array", "items": {"type": "string"}},
                "target_symbols": {"type": "array", "items": {"type": "string"}},
                "target_arena": {
                    "type": "string",
                    "enum": ["coding_arena", "coding_waboose", "human_agent", "agent_bridge", "research"],
                    "default": "agent_bridge",
                },
                "radius": {"type": "integer", "minimum": 0, "maximum": 3, "default": 1},
                "max_atomic_nodes": {"type": "integer", "minimum": 1, "maximum": 200, "default": 48},
                "max_source_lines": {"type": "integer", "minimum": 8, "maximum": 300, "default": 120},
                "include_source": {"type": "boolean", "default": True},
                "include_future": {"type": "boolean", "default": True},
                "include_research_plan": {"type": "boolean", "default": True},
                "include_offline_research": {"type": "boolean", "default": True},
            },
            "required": ["objective"],
        },
    },
    {
        "name": "aura_waboose_learn_coderabbit",
        "description": "Learn from a successful CodeRabbit review after exact head/source grounding.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_payload": {"type": "object"},
            },
            "required": ["review_payload"],
        },
    },
    {
        "name": "aura_waboose_learning_summary",
        "description": "Show Coding Waboose external-review learning status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "aura_waboose_prepare",
        "description": "Compile a Coding Waboose evidence contract and diagnostic breadboard from a Git range, workspace, or explicit files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "mode": {"type": "string", "enum": ["range", "workspace", "files"], "default": "range"},
                "base_ref": {"type": "string", "default": "HEAD~1"},
                "head_ref": {"type": "string", "default": "HEAD"},
                "changed_files": {"type": "array", "items": {"type": "string"}},
                "diff_text": {"type": "string"},
                "profile": {"type": "string", "enum": ["precision", "balanced", "exhaustive"], "default": "precision"},
                "focus_directives": {"type": "array", "items": {"type": ["string", "object"]}},
                "invariants": {"type": "array", "items": {"type": "string"}},
                "risk_map": {"type": "array", "items": {"type": "string"}},
                "agent_name": {"type": "string", "default": "external_agent"},
                "graph_depth": {"type": "integer", "minimum": 0, "maximum": 4, "default": 2},
                "graph_node_budget": {"type": "integer", "minimum": 1, "maximum": 500, "default": 120},
                "run_tests": {"type": "boolean", "default": True},
                "run_optional_tools": {"type": "boolean", "default": True},
                "metadata": {"type": "object"},
            },
            "required": ["objective"],
        },
    },
    {
        "name": "aura_waboose_scan",
        "description": "Run Coding Waboose deterministic scans and energize the applicable diagnostic breadboard components.",
        "inputSchema": {
            "type": "object",
            "properties": {"review_id": {"type": "string"}},
            "required": ["review_id"],
        },
    },
    {
        "name": "aura_waboose_agent_packet",
        "description": "Return Coding Waboose focus, diagnostic breadboard, topology, evidence, and optional exact-source slices for a coding agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "include_source": {"type": "boolean", "default": False},
                "max_files": {"type": "integer", "minimum": 1, "maximum": 80, "default": 24},
                "max_lines_per_file": {"type": "integer", "minimum": 8, "maximum": 240, "default": 120},
            },
            "required": ["review_id"],
        },
    },
    {
        "name": "aura_waboose_submit_findings",
        "description": "Submit Coding Waboose findings for exact-source corroboration; agent confirmation claims are ignored.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "findings": {"type": "array", "items": {"type": "object"}},
                "agent_name": {"type": "string", "default": "external_agent"},
            },
            "required": ["review_id", "findings"],
        },
    },
    {
        "name": "aura_waboose_finalize",
        "description": "Deduplicate and rank Coding Waboose findings, then compile review-only Forge repair requests.",
        "inputSchema": {
            "type": "object",
            "properties": {"review_id": {"type": "string"}},
            "required": ["review_id"],
        },
    },
    {
        "name": "aura_waboose_status",
        "description": "Return Coding Waboose status, breadboard continuity, and finding counts.",
        "inputSchema": {
            "type": "object",
            "properties": {"review_id": {"type": "string"}},
            "required": ["review_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


@_register_tool("aura_repo_digest")
def _handle_repo_digest(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_repo_digest(
        include_hubs=_strict_bool_arg(args, "include_hubs", default=True),
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
        use_emergent_evidence=_strict_bool_arg(args, "use_emergent_evidence", default=False),
        emergent_radius=int(args.get("emergent_radius", 1)),
        emergent_max_atomic_nodes=int(args.get("emergent_max_atomic_nodes", 48)),
        emergent_include_source=_strict_bool_arg(args, "emergent_include_source", default=False),
        emergent_include_research_plan=_strict_bool_arg(args, "emergent_include_research_plan", default=True),
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
        include_neighbors=_strict_bool_arg(args, "include_neighbors", default=True),
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
        include_affordances=_strict_bool_arg(args, "include_affordances", default=True),
        top_k=int(args.get("top_k", 7)),
    )


@_register_tool("aura_checkpoint_session")
def _handle_checkpoint_session(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_checkpoint_session(
        plan_phase_hash=str(args.get("plan_phase_hash", "")),
        repo_head=str(args.get("repo_head", "")),
        parent_checkpoint_id=str(args.get("parent_checkpoint_id", "")),
        branch_name=str(args.get("branch_name", "")),
    )


@_register_tool("aura_list_checkpoints")
def _handle_list_checkpoints(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_list_checkpoints(
        session_id=str(args.get("session_id", "")) or None,
        limit=int(args.get("limit", 100)),
    )


@_register_tool("aura_restore_checkpoint")
def _handle_restore_checkpoint(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_restore_checkpoint(
        checkpoint_id=str(args.get("checkpoint_id", "")),
        current_repo_head=str(args.get("current_repo_head", "")),
        current_invariant_values=dict(args.get("current_invariant_values") or {}),
        remaining_context_tokens=int(args.get("remaining_context_tokens", 0)),
        surgeon_context_limit=int(args.get("surgeon_context_limit", 0)),
    )


@_register_tool("aura_fork_checkpoint")
def _handle_fork_checkpoint(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_fork_checkpoint(
        checkpoint_id=str(args.get("checkpoint_id", "")),
        branch_name=str(args.get("branch_name", "")),
        repo_head=str(args.get("repo_head", "")) or None,
    )


@_register_tool("aura_handoff_checkpoint")
def _handle_handoff_checkpoint(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_handoff_checkpoint(
        checkpoint_id=str(args.get("checkpoint_id", "")),
        target_arena_id=str(args.get("target_arena_id", "")),
        current_repo_head=str(args.get("current_repo_head", "")),
        current_invariant_values=dict(args.get("current_invariant_values") or {}),
    )


@_register_tool("aura_spatial_status")
def _handle_spatial_status(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_spatial_status(str(args.get("run_id", "")))


@_register_tool("aura_spatial_interact")
def _handle_spatial_interact(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_spatial_interact(
        str(args.get("run_id", "")),
        action=str(args.get("action", "")),
        target_entity_ids=tuple(args.get("target_entity_ids", []) or []),
        metadata=dict(args.get("metadata") or {}),
    )


@_register_tool("aura_spatial_prove")
def _handle_spatial_prove(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_spatial_prove(
        str(args.get("run_id", "")),
        repo_head=str(args.get("repo_head", "")),
        outcome=str(args.get("outcome", "PRESENTED")),
        evidence_class=str(args.get("evidence_class", "DERIVED")),
        metrics=dict(args.get("metrics") or {}),
        branch_name=str(args.get("branch_name", "")),
    )


@_register_tool("aura_spatial_prove_browser_telemetry")
def _handle_spatial_prove_browser_telemetry(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    telemetry = args.get("telemetry_packet")
    if not isinstance(telemetry, Mapping):
        raise ValueError("telemetry_packet must be an object")
    return bridge.aura_spatial_prove_browser_telemetry(
        str(args.get("run_id", "")),
        telemetry_packet=dict(telemetry),
        repo_head=str(args.get("repo_head", "")),
        branch_name=str(args.get("branch_name", "")),
    )


@_register_tool("aura_spatial_decide")
def _handle_spatial_decide(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_spatial_decide(
        str(args.get("run_id", "")),
        decision=str(args.get("decision", "")),
        decision_ref=str(args.get("decision_ref", "human:pending")),
    )


@_register_tool("aura_spatial_observatory")
def _handle_spatial_observatory(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_spatial_observatory(str(args.get("run_id", "")))


@_register_tool("aura_spatial_restore_assessment")
def _handle_spatial_restore_assessment(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    return bridge.aura_spatial_restore_assessment(
        str(args.get("run_id", "")),
        current_repo_head=str(args.get("current_repo_head", "")),
    )


@_register_tool("aura_spatial_dissolve")
def _handle_spatial_dissolve(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    receipt = args.get("renderer_cleanup_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("renderer_cleanup_receipt must be an object")
    return bridge.aura_spatial_dissolve(
        str(args.get("run_id", "")),
        renderer_cleanup_receipt=dict(receipt),
        reason_code=str(args.get("reason_code", "SPATIAL_ARENA_COMPLETE")),
    )


@_register_tool("aura_atomic_function_inventory")
def _handle_atomic_function_inventory(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    limit = args.get("limit")
    return bridge.aura_atomic_function_inventory(
        query=str(args.get("query", "")),
        target_files=list(args.get("target_files", []) or []),
        target_symbols=list(args.get("target_symbols", []) or []),
        limit=int(limit) if limit is not None else None,
        include_source=_strict_bool_arg(args, "include_source", default=False),
    )


@_register_tool("aura_emergent_evidence")
def _handle_emergent_evidence(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    request = {
        "objective": str(args.get("objective", "")),
        "target_files": list(args.get("target_files", []) or []),
        "target_symbols": list(args.get("target_symbols", []) or []),
        "target_arena": str(args.get("target_arena", "agent_bridge")),
        "radius": int(args.get("radius", 1)),
        "max_atomic_nodes": int(args.get("max_atomic_nodes", 48)),
        "max_source_lines": int(args.get("max_source_lines", 120)),
        "include_source": _strict_bool_arg(args, "include_source", default=True),
        "include_future": _strict_bool_arg(args, "include_future", default=True),
        "include_research_plan": _strict_bool_arg(args, "include_research_plan", default=True),
        "include_offline_research": _strict_bool_arg(args, "include_offline_research", default=True),
    }
    return bridge.aura_emergent_evidence(request)


@_register_tool("aura_waboose_learn_coderabbit")
def _handle_waboose_learn_coderabbit(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    review_payload = args.get("review_payload")
    if not isinstance(review_payload, Mapping):
        raise ValueError("review_payload must be an object")
    return bridge.aura_waboose_learn_coderabbit(dict(review_payload))


@_register_tool("aura_waboose_learning_summary")
def _handle_waboose_learning_summary(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    del args
    return bridge.aura_waboose_learning_summary()


@_register_tool("aura_waboose_prepare")
def _handle_waboose_prepare(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    request = {
        "objective": str(args.get("objective", "")),
        "mode": str(args.get("mode", "range")),
        "base_ref": str(args.get("base_ref", "HEAD~1")),
        "head_ref": str(args.get("head_ref", "HEAD")),
        "changed_files": list(args.get("changed_files", []) or []),
        "diff_text": str(args.get("diff_text", "")),
        "profile": str(args.get("profile", "precision")),
        "focus_directives": list(args.get("focus_directives", []) or []),
        "invariants": list(args.get("invariants", []) or []),
        "risk_map": list(args.get("risk_map", []) or []),
        "agent_name": str(args.get("agent_name", "external_agent")),
        "graph_depth": int(args.get("graph_depth", 2)),
        "graph_node_budget": int(args.get("graph_node_budget", 120)),
        "run_tests": _strict_bool_arg(args, "run_tests", default=True),
        "run_optional_tools": _strict_bool_arg(args, "run_optional_tools", default=True),
        "metadata": dict(args.get("metadata") or {}),
    }
    return bridge.aura_waboose_prepare(request)


@_register_tool("aura_waboose_scan")
def _handle_waboose_scan(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_waboose_scan(str(args.get("review_id", "")))


@_register_tool("aura_waboose_agent_packet")
def _handle_waboose_agent_packet(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_waboose_agent_packet(
        str(args.get("review_id", "")),
        include_source=_strict_bool_arg(args, "include_source", default=False),
        max_files=int(args.get("max_files", 24)),
        max_lines_per_file=int(args.get("max_lines_per_file", 120)),
    )


@_register_tool("aura_waboose_submit_findings")
def _handle_waboose_submit_findings(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    raw_findings = args.get("findings", []) or []
    findings = [dict(item) for item in raw_findings if isinstance(item, Mapping)]
    return bridge.aura_waboose_submit_findings(
        str(args.get("review_id", "")),
        findings,
        agent_name=str(args.get("agent_name", "external_agent")),
    )


@_register_tool("aura_waboose_finalize")
def _handle_waboose_finalize(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_waboose_finalize(str(args.get("review_id", "")))


@_register_tool("aura_waboose_status")
def _handle_waboose_status(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_waboose_status(str(args.get("review_id", "")))


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
        return _make_response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )

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
            return _make_response(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, default=str, ensure_ascii=False),
                        }
                    ],
                    "isError": is_error_packet(result) or (isinstance(result, Mapping) and result.get("ok") is False),
                },
            )
        except Exception as exc:
            return _make_error_response(request_id, -32603, f"Tool execution error: {exc}")

    return _make_error_response(request_id, -32601, f"Unknown method: {method}")


def serve_stdio(bridge: AuraAgentArenaBridge | None = None) -> None:
    """Run the stdio JSON-RPC server loop."""
    if bridge is None:
        bridge = AuraAgentArenaBridge()

    for raw_line in sys.stdin:
        line = raw_line.strip()
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

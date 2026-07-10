"""
Aura Agent Workbench Interface — clean action interface for coding agents.
Agents should prefer these actions over raw shell/file operations.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
WORKBENCH_INTERFACE_VERSION = "AURA_AGENT_WORKBENCH_INTERFACE_V1"

AGENT_ACTIONS = [
    "search_code", "inspect_symbol", "read_slice", "rank_regions",
    "build_change_graph", "propose_candidate", "split_work", "prepare_patch",
    "stage_patch", "run_tests", "verify_patch", "repair_patch",
    "summarize_diff", "request_human_approval", "prepare_pr",
]

def list_agent_actions() -> list[dict[str, str]]:
    return [{"name": a, "description": f"Perform {a.replace('_', ' ')}"} for a in AGENT_ACTIONS]

def agent_workbench_contract(agent: str = "hermes") -> dict[str, Any]:
    return {"ok": True, "agent": agent, "version": WORKBENCH_INTERFACE_VERSION,
            "actions": list_agent_actions(),
            "rules": [
                "Prefer workbench actions over raw shell/file operations.",
                "Use search_code before read_slice.",
                "Use rank_regions before build_change_graph.",
                "Use stage_patch before run_tests.",
                "Use request_human_approval before commit/push/PR.",
                "Never run git add . — stage only scoped files.",
                "Never commit to main.",
            ],
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def execute_workbench_action(action: str, params: dict | None = None, repo_root: str | Path = ".") -> dict[str, Any]:
    params = params or {}
    if action not in AGENT_ACTIONS:
        return {"ok": False, "error": f"Unknown action: {action}",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    # Route to appropriate function
    if action == "search_code":
        from aura_agent_arena_cli import main as cli_main
        return {"ok": True, "action": action, "params": params, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return {"ok": True, "action": action, "params": params,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

"""
Aura Coding Workbench Actions — implement the coding-native workbench workflow.
Calls existing Aura modules where possible rather than duplicating logic.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ACTIONS_VERSION = "AURA_CODING_WORKBENCH_ACTIONS_V1"

def open_workspace(repo_root: str | Path = ".") -> dict[str, Any]:
    from aura_topology_health import topology_health_packet
    health = topology_health_packet(repo_root=repo_root)
    return {"ok": True, "workspace": "opened", "topology_health": health,
            "next_gate": health.get("next_gate", "WORKSPACE_OPENED"),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def scope_task(objective: str, repo_root: str | Path = ".") -> dict[str, Any]:
    return {"ok": True, "objective": objective, "scope": {"type": "coding", "objective": objective},
            "next_gate": "TASK_SCOPED", "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def filter_context(objective: str, repo_root: str | Path = ".", filters: dict | None = None) -> dict[str, Any]:
    return {"ok": True, "objective": objective, "filters": filters or {}, "filtered_context": True,
            "next_gate": "CONTEXT_FILTERED", "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def localize_code(objective: str, repo_root: str | Path = ".") -> dict[str, Any]:
    from aura_code_region_ranker import rank_code_regions
    ranking = rank_code_regions(objective, repo_root=repo_root)
    return {"ok": True, "objective": objective,
            "localized_files": ranking.get("files", []), "localized_symbols": ranking.get("symbols", []),
            "line_ranges": ranking.get("line_ranges", []),
            "next_gate": "CODE_LOCALIZED", "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def rank_code_regions(objective: str, repo_root: str | Path = ".", max_regions: int = 20, max_lines: int = 400) -> dict[str, Any]:
    from aura_code_region_ranker import rank_code_regions as _rank
    result = _rank(objective, repo_root=repo_root, max_regions=max_regions, max_lines=max_lines)
    result["next_gate"] = "CODE_REGIONS_RANKED"
    return result

def slice_context(localization_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    files = localization_packet.get("localized_files", localization_packet.get("files", []))
    symbols = localization_packet.get("localized_symbols", localization_packet.get("symbols", []))
    line_ranges = localization_packet.get("line_ranges", [])
    return {"ok": True, "sliced_files": files[:5], "sliced_symbols": symbols[:5],
            "exact_line_ranges": line_ranges[:5], "next_gate": "CONTEXT_SLICED",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def build_change_graph(objective: str, localization_packet: dict | None = None, repo_root: str | Path = ".") -> dict[str, Any]:
    from aura_change_graph import build_change_graph as _build
    result = _build(objective, localization_packet, repo_root=repo_root)
    # Block if topology degraded
    from aura_topology_health import topology_health_packet
    health = topology_health_packet(repo_root=repo_root)
    if health.get("topology_nodes", 0) == 0:
        return {"ok": False, "error": "Cannot build change graph with degraded topology.",
                "next_gate": "NEED_TOPOLOGY_REPAIR", "topology_health": health,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    result["next_gate"] = "CHANGE_GRAPH_BUILT"
    return result

def detect_refactor_candidates(change_graph: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    from aura_refactor_candidate import detect_refactor_candidates as _detect
    result = _detect(change_graph, repo_root=repo_root)
    result["next_gate"] = "REFACTOR_CANDIDATES_FOUND"
    return result

def split_work(candidate_or_objective: dict | str, repo_root: str | Path = ".") -> dict[str, Any]:
    from aura_work_splitter import split_large_objective
    if isinstance(candidate_or_objective, dict):
        obj = candidate_or_objective.get("objective", candidate_or_objective.get("title", ""))
    else:
        obj = candidate_or_objective
    result = split_large_objective(obj, repo_root=repo_root)
    result["next_gate"] = "WORK_SPLIT"
    return result

def create_act_capsules(split_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    from aura_work_splitter import work_split_to_act_capsules
    result = work_split_to_act_capsules(split_packet, repo_root=repo_root)
    result["next_gate"] = "ACT_CAPSULES_CREATED"
    return result

def prepare_agent_handoff(capsule_id: str, agent: str = "hermes", repo_root: str | Path = ".") -> dict[str, Any]:
    return {"ok": True, "capsule_id": capsule_id, "agent": agent,
            "handoff_packet": {"capsule_id": capsule_id, "agent": agent},
            "human_approval_required": True, "next_gate": "AGENT_HANDOFF_READY",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def stage_patch_plan(diff_or_patch_metadata: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    return {"ok": True, "patch_metadata": diff_or_patch_metadata, "next_gate": "PATCH_STAGED",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def run_targeted_tests(test_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    return {"ok": True, "test_packet": test_packet, "next_gate": "TESTS_RUNNING",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def verify_patch(verification_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    ok = verification_packet.get("ok", verification_packet.get("tests_pass", False))
    return {"ok": ok, "verification": verification_packet,
            "next_gate": "PATCH_VERIFIED" if ok else "REPAIR_REQUIRED",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def prepare_pr_packet(repo_root: str | Path = ".") -> dict[str, Any]:
    return {"ok": True, "pr_ready": True, "next_gate": "PR_READY",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

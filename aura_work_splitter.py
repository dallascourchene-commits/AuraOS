"""
Aura Work Splitter — split large objectives into child act-capsules.
Uses existing aura_mitosis.py where possible. Degrades gracefully.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SPLITTER_VERSION = "AURA_WORK_SPLITTER_V1"

def split_large_objective(objective: str, max_children: int = 5, repo_root: str | Path = ".") -> dict[str, Any]:
    children = []
    try:
        from aura_music_mitosis_adapter import mitosis_split_objective
        result = mitosis_split_objective(objective, max_children=max_children, repo_root=repo_root)
        children = result.get("children", [])
    except Exception:
        sentences = [s.strip() for s in re.split(r"[.;]", objective) if len(s.strip()) > 10]
        for i, s in enumerate(sentences[:max_children]):
            children.append({"child_id": f"child_{i+1}", "objective": s, "parent_objective": objective})
    if not children:
        children.append({"child_id": "child_1", "objective": objective, "parent_objective": objective})
    for c in children:
        c.setdefault("patch_authority", PATCH_AUTHORITY)
        c.setdefault("vsa_patch_authority", VSA_PATCH_AUTHORITY)
    return {"ok": True, "parent_objective": objective, "child_tasks": children,
            "sequencing": "parallel" if len(children) > 1 else "single",
            "dependencies_between_child_tasks": [],
            "suggested_branches": [f"feature/task-{c['child_id']}" for c in children],
            "suggested_tests": [], "token_budget_per_child": 2000,
            "agent_recommendation_per_child": [{"child_id": c["child_id"], "agent": "hermes"} for c in children],
            "phase_capsule_per_child": [], "workflow_gate_start": "WORKSPACE_OPENED",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def split_refactor_candidate(candidate: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    return split_large_objective(candidate.get("objective", candidate.get("title", "")), repo_root=repo_root)

def split_by_file(files: list[str], repo_root: str | Path = ".") -> dict[str, Any]:
    children = [{"child_id": f"child_{i+1}", "objective": f"Handle {fp}", "target_files": [fp],
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
                for i, fp in enumerate(files[:5])]
    return {"ok": True, "child_tasks": children, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def split_by_symbol(symbols: list[str], repo_root: str | Path = ".") -> dict[str, Any]:
    children = [{"child_id": f"child_{i+1}", "objective": f"Refactor {sym}", "target_symbols": [sym],
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
                for i, sym in enumerate(symbols[:5])]
    return {"ok": True, "child_tasks": children, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def split_by_test_scope(tests: list[str], repo_root: str | Path = ".") -> dict[str, Any]:
    children = [{"child_id": f"child_{i+1}", "objective": f"Fix {t}", "suggested_tests": [t],
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
                for i, t in enumerate(tests[:5])]
    return {"ok": True, "child_tasks": children, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def split_by_risk(risks: list[dict], repo_root: str | Path = ".") -> dict[str, Any]:
    children = [{"child_id": f"child_{i+1}", "objective": f"Address {r.get('type','risk')}", "risk_level": r.get("level","medium"),
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
                for i, r in enumerate(risks[:5])]
    return {"ok": True, "child_tasks": children, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def split_by_agent(agents: list[str], objective: str, repo_root: str | Path = ".") -> dict[str, Any]:
    children = [{"child_id": f"child_{i+1}", "objective": objective, "suggested_agent": a,
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
                for i, a in enumerate(agents[:5])]
    return {"ok": True, "child_tasks": children, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def work_split_to_act_capsules(split_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    capsules = [{"task_id": f"A{i+1}", "objective": c.get("objective",""), "target_files": c.get("target_files",[]),
                 "target_symbols": c.get("target_symbols",[]),
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
                for i, c in enumerate(split_packet.get("child_tasks",[]))]
    return {"ok": True, "act_capsules": capsules, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def work_split_to_phase_capsules(split_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    capsules = [{"child_id": c.get("child_id",""), "phase": "discovery", "objective": c.get("objective",""),
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
                for c in split_packet.get("child_tasks",[])]
    return {"ok": True, "phase_capsules": capsules, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

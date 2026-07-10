"""
Aura MUSIC + Mitosis Cockpit Adapter — advisory ranking and objective decomposition.

Dependencies: stdlib only. All Aura imports are lazy (numpy-free).
"""
from __future__ import annotations
import re
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ADAPTER_VERSION = "AURA_MUSIC_MITOSIS_ADAPTER_V1"


def music_rank_cockpit_candidates(objective: str, candidates: list, repo_root: str = ".") -> dict:
    """Rank candidates using MUSIC scoring (advisory only)."""
    ranked = []
    try:
        from aura_music_coding_arena import music_rank_candidates
        ranked = music_rank_candidates(objective, candidates)
    except Exception:
        # Fallback: keyword-match scoring
        obj_lower = objective.lower()
        for c in candidates:
            score = sum(1.0 for kw in obj_lower.split() if kw in str(c).lower())
            ranked.append({"candidate": c, "score": score, "reason": "keyword_match_fallback"})
        ranked.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"ok": True, "objective": objective, "ranked_candidates": ranked[:10],
             "advisory_only": True, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY,
             "note": "MUSIC output is advisory only. Never patch from MUSIC alone."}


def music_invert_code_route(objective: str, target_file: str, repo_root: str = ".") -> dict:
    """Inverse-search coding topology (advisory only)."""
    inverted = []
    try:
        from aura_music_inversion import invert_code_route
        inverted = invert_code_route(objective, target_file)
    except Exception:
        inverted = [{"file": target_file, "route": "fallback", "reason": "music_inversion_unavailable"}]
    return {"ok": True, "objective": objective, "inverted_routes": inverted,
             "advisory_only": True, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def mitosis_split_objective(objective: str, max_children: int = 5, repo_root: str = ".") -> dict:
    """Split a large objective into child act-capsules."""
    children = []
    try:
        from aura_mitosis import AuraMitosisEngine
        engine = AuraMitosisEngine()
        result = engine.split(objective, max_children=max_children)
        children = result.get("children", []) if isinstance(result, dict) else []
    except Exception:
        # Fallback: split by sentence/clause boundaries
        sentences = re.split(r'[.;]', objective)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        for i, s in enumerate(sentences[:max_children]):
            children.append({
                "child_id": f"child_{i+1}",
                "objective": s,
                "parent_objective": objective,
                "target_files": [],
                "target_symbols": [],
                "required_evidence": [],
                "suggested_tests": [],
                "token_budget": {},
                "workflow_gate_start": "INGESTED",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            })
        if not children:
            children.append({
                "child_id": "child_1",
                "objective": objective,
                "parent_objective": objective,
                "target_files": [],
                "target_symbols": [],
                "required_evidence": [],
                "suggested_tests": [],
                "token_budget": {},
                "workflow_gate_start": "INGESTED",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            })
    # Ensure each child has invariants
    for c in children:
        if isinstance(c, dict):
            c.setdefault("patch_authority", PATCH_AUTHORITY)
            c.setdefault("vsa_patch_authority", VSA_PATCH_AUTHORITY)
    return {"ok": True, "objective": objective, "children": children,
             "child_count": len(children), "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def mitosis_to_phase_capsules(children: list, repo_root: str = ".") -> dict:
    """Convert mitosis children to phase capsules."""
    capsules = []
    for child in children:
        capsules.append({
            "child_id": child.get("child_id", ""),
            "phase": "discovery",
            "objective": child.get("objective", ""),
            "next_action": "ground_through_codemap",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        })
    return {"ok": True, "phase_capsules": capsules, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def mitosis_to_agent_act_capsules(children: list, repo_root: str = ".") -> dict:
    """Convert mitosis children to agent act capsules."""
    capsules = []
    for i, child in enumerate(children):
        capsules.append({
            "task_id": f"A{i+1}",
            "objective": child.get("objective", ""),
            "parent_objective": child.get("parent_objective", ""),
            "target_files": child.get("target_files", []),
            "target_symbols": child.get("target_symbols", []),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        })
    return {"ok": True, "act_capsules": capsules, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}

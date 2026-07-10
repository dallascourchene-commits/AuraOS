"""
Aura Coding MUSIC Lane — MUSIC advisory ranking for code regions and candidates.
MUSIC is ranking/advisory only. Cannot patch.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MUSIC_LANE_VERSION = "AURA_CODING_MUSIC_LANE_V1"

def music_rank_code_regions(objective: str, regions: list, repo_root: str | Path = ".") -> dict[str, Any]:
    try:
        from aura_music_mitosis_adapter import music_rank_cockpit_candidates
        return music_rank_cockpit_candidates(objective, regions, repo_root=repo_root)
    except Exception:
        return {"ok": True, "objective": objective, "ranked_candidates": [],
                "advisory_only": True, "note": "MUSIC unavailable. Advisory only.",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def music_rank_refactor_candidates(objective: str, candidates: list, repo_root: str | Path = ".") -> dict[str, Any]:
    result = music_rank_code_regions(objective, candidates, repo_root=repo_root)
    result["ranked_candidates"] = result.get("ranked_candidates", [])[:5]
    return result

def music_invert_change_graph(change_graph: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    obj = change_graph.get("objective", "")
    files = change_graph.get("files", [])
    inverted = []
    for fp in files[:3]:
        try:
            from aura_music_mitosis_adapter import music_invert_code_route
            r = music_invert_code_route(obj, fp, repo_root=repo_root)
            inverted.extend(r.get("inverted_routes", []))
        except Exception:
            inverted.append({"file": fp, "route": "fallback"})
    return {"ok": True, "inverted_routes": inverted, "advisory_only": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def music_to_ranking_evidence(music_result: dict) -> dict[str, Any]:
    return {"ok": True, "music_scores": music_result.get("ranked_candidates", []),
            "advisory_only": True, "note": "MUSIC scores are advisory. Cannot override exact lookup.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

"""
Aura Coding Research Lane — research evidence for coding plans.
Offline mode uses .aura/RESEARCH_MANIFEST.json. Advisory only.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
RESEARCH_LANE_VERSION = "AURA_CODING_RESEARCH_LANE_V1"

def search_research_manifest(objective: str, repo_root: str | Path = ".", offline: bool = True) -> dict[str, Any]:
    try:
        from aura_research_cockpit_adapter import research_manifest_search
        return research_manifest_search(objective, repo_root=repo_root, offline=offline)
    except Exception:
        return {"ok": True, "objective": objective, "papers": [], "offline": offline,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def recall_paper_memory(objective: str, repo_root: str | Path = ".") -> dict[str, Any]:
    try:
        from aura_research_cockpit_adapter import paper_memory_recall
        return paper_memory_recall(objective, repo_root=repo_root)
    except Exception:
        return {"ok": True, "objective": objective, "recalled_papers": [],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def plan_arxiv_forager_query(objective: str) -> dict[str, Any]:
    return {"ok": True, "objective": objective, "plan": {"query": objective, "offline": True},
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def build_research_evidence_packet(objective: str, repo_root: str | Path = ".", offline: bool = True) -> dict[str, Any]:
    search = search_research_manifest(objective, repo_root=repo_root, offline=offline)
    try:
        from aura_research_cockpit_adapter import research_to_cockpit_evidence_packet
        evidence = research_to_cockpit_evidence_packet(search, repo_root=repo_root)
    except Exception:
        evidence = {"ok": True, "evidence_packet": {"papers": search.get("papers",[]), "advisory_only": True},
                    "advisory_only": True, "note": "Research evidence is advisory. CODEMAP grounding required before patch.",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return evidence

def compress_research_for_agent(evidence_packet: dict) -> dict[str, Any]:
    try:
        from aura_research_cockpit_adapter import research_to_agent_context_capsule
        return research_to_agent_context_capsule(evidence_packet)
    except Exception:
        return {"ok": True, "context_capsule": {"summary": "compressed"}, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def attach_research_to_change_graph(change_graph: dict, evidence_packet: dict) -> dict[str, Any]:
    g = dict(change_graph)
    g["research_evidence"] = evidence_packet.get("evidence_packet", {})
    g["research_advisory"] = True
    return {"ok": True, "change_graph": g, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

"""
Aura Change Graph — represent proposed coding changes as a graph.
Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
CHANGE_GRAPH_VERSION = "AURA_CHANGE_GRAPH_V1"

def _graph_id(objective: str) -> str:
    return hashlib.blake2b(objective.encode(), digest_size=8).hexdigest()

def build_change_graph(objective: str, localization_packet: dict | None = None, repo_root: str | Path = ".") -> dict[str, Any]:
    loc = localization_packet or {}
    files = loc.get("files", [])[:10]
    symbols = loc.get("symbols", [])[:10]
    tests = loc.get("tests", [])[:5]
    token_before = loc.get("raw_context_tokens_est", 0)
    token_after = loc.get("estimated_tokens", 0)
    comp_ratio = round(token_after / max(token_before, 1) * 100, 1) if token_before > 0 else 0.0
    jspace = {}
    try:
        from aura_jspace_codec import build_jspace_packet
        jp = build_jspace_packet({"intent": "code_refactor"}, {"route": "BUILDER_PATCH"})
        jspace = {"packet": jp.packet[:200]}
    except Exception: pass
    st3gg = {}
    try:
        from aura_arena_st3gg_codec import should_st3gg_encode_arena_capsule
        d = should_st3gg_encode_arena_capsule({"objective": objective})
        st3gg = {"enabled": d.enabled, "reason": d.reason}
    except Exception: pass
    return {
        "ok": True, "version": CHANGE_GRAPH_VERSION,
        "graph_id": _graph_id(objective), "objective": objective,
        "files": files, "symbols": symbols, "tests": tests,
        "dependencies": [], "risks": [], "command_risks": [], "agent_actions": [],
        "proposed_edges": [], "missing_edges": [],
        "required_evidence": ["grounding_ok", "tests_pass"],
        "token_cost_before": token_before, "token_cost_after": token_after,
        "compression_ratio": comp_ratio, "jspace_state": jspace, "st3gg_decision": st3gg,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

def change_graph_from_regions(ranking_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    return build_change_graph(ranking_packet.get("objective",""), ranking_packet, repo_root)

def add_test_nodes(graph: dict, tests: list[str]) -> dict:
    g = dict(graph); g["tests"] = list(set(g.get("tests",[]) + tests)); return g

def add_risk_nodes(graph: dict, risks: list[dict]) -> dict:
    g = dict(graph); g["risks"] = g.get("risks",[]) + risks; return g

def add_dependency_edges(graph: dict, deps: list[dict]) -> dict:
    g = dict(graph); g["dependencies"] = g.get("dependencies",[]) + deps; return g

def add_agent_action_nodes(graph: dict, actions: list[dict]) -> dict:
    g = dict(graph); g["agent_actions"] = g.get("agent_actions",[]) + actions; return g

def add_command_risk_nodes(graph: dict, risks: list[dict]) -> dict:
    g = dict(graph); g["command_risks"] = g.get("command_risks",[]) + risks; return g

def change_graph_to_act_capsules(graph: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    capsules = []
    for i, fp in enumerate(graph.get("files", [])[:5]):
        capsules.append({"task_id": f"A{i+1}", "target_file": fp, "objective": graph.get("objective",""),
                         "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY})
    return {"ok": True, "act_capsules": capsules, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def change_graph_to_token_report(graph: dict) -> dict[str, Any]:
    return {"ok": True, "token_cost_before": graph.get("token_cost_before",0),
            "token_cost_after": graph.get("token_cost_after",0),
            "compression_ratio": graph.get("compression_ratio",0),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def change_graph_to_review_packet(graph: dict) -> dict[str, Any]:
    return {"ok": True, "review_packet": {
        "files": graph.get("files",[]), "symbols": graph.get("symbols",[]),
        "tests": graph.get("tests",[]), "risks": graph.get("risks",[]),
        "command_risks": graph.get("command_risks",[])},
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

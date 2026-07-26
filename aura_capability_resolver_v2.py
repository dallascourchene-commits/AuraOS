"""Graph-pinned Capability Genome Resolver facade.

This preserves the V1 resolver and makes the Capability Connectome path a
first-class result for Cognome routing. It remains advisory and grants no patch,
model-execution, or policy authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aura_capability_connectome import build_capability_connectome, find_capability_path
from aura_capability_connectome_v2 import enrich_connectome, enrich_path
from aura_capability_resolver import resolve_capabilities as resolve_capabilities_v1

RESOLVER_VERSION = "AURA_CAPABILITY_RESOLUTION_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def resolve_capabilities(
    objective: str,
    *,
    target_files: list[str] | None = None,
    target_symbols: list[str] | None = None,
    selected_node_ids: list[str] | None = None,
    repo_root: str | Path = ".",
    top_k: int = 12,
    token_budget: int = 2400,
    persist_module_manifest: bool = False,
) -> dict[str, Any]:
    """Resolve existing Aura capabilities and bind an exact Connectome path."""
    result = resolve_capabilities_v1(
        objective,
        target_files=target_files,
        target_symbols=target_symbols,
        selected_node_ids=selected_node_ids,
        repo_root=repo_root,
        top_k=top_k,
        token_budget=token_budget,
        persist_module_manifest=persist_module_manifest,
    )
    source_version = result.get("version", "")
    graph = enrich_connectome(build_capability_connectome(repo_root))
    path = enrich_path(find_capability_path(objective, repo_root=repo_root), graph)

    result.update(
        {
            "version": RESOLVER_VERSION,
            "source_version": source_version,
            "capability_connectome_path": path,
            "capability_graph_digest": path.get("graph_digest", ""),
            "capability_path_digest": path.get("path_digest", ""),
            "required_capability_ids": path.get("required_capability_ids", []),
            "capability_path": path.get("path", []),
            "capability_path_details": path.get("path_details", []),
            "capability_truth_boundaries": path.get("truth_boundaries", []),
            "capability_risks": path.get("risks", []),
            "capability_tests": path.get("tests", []),
            "capability_token_savings_roles": path.get("token_savings_roles", []),
            "deterministic_capability_ids": path.get("deterministic_capability_ids", []),
            "model_dependent_capability_ids": path.get("model_dependent_capability_ids", []),
            "unresolved_execution_capability_ids": path.get(
                "unresolved_execution_capability_ids", []
            ),
            "model_execution_requirements": path.get("model_execution_requirements", []),
        }
    )
    guidance = list(result.get("do_not_reinvent", []))
    guidance.extend(
        [
            "Do not invent a second capability graph; use aura_capability_connectome.py with aura_capability_connectome_v2.py.",
            "Do not attach model support to undeclared capability IDs; use aura_model_connectome_bridge.py.",
        ]
    )
    result["do_not_reinvent"] = list(dict.fromkeys(guidance))
    if not path.get("ok"):
        missing = list(result.get("missing_capabilities", []))
        missing.append(
            {
                "capability": "capability_connectome_path",
                "status": "unresolved",
                "reason": path.get("missing_capability_ids", []),
                "impact": "Consequential model routing must fail closed.",
            }
        )
        result["missing_capabilities"] = missing
    result["patch_authority"] = PATCH_AUTHORITY
    result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
    return result

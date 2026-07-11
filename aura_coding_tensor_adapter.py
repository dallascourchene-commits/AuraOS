"""
Aura Coding Tensor Adapter — converts a bounded code region into a tensor evidence graph.

Variables: TARGET_GROUNDED, TEST_COVERAGE_PRESENT, DEPENDENCY_IMPACT_BOUNDED,
PUBLIC_API_RISK, EXTERNAL_EFFECT_RISK, CHANGE_REGION_CONFINED, READY_FOR_AGENT_HANDOFF.

Advisory only — never becomes patch authority.
"""
from __future__ import annotations
from typing import Any
import numpy as np

from aura_tensor_evidence import (
    TensorVariable, TensorFactor, EvidenceReference, TensorBeliefEngine,
    SUPPORTED, CONTRADICTED, UNRESOLVED,
    PATCH_AUTHORITY, TENSOR_PATCH_AUTHORITY, BELIEF_PROPAGATION_PATCH_AUTHORITY,
)

CODING_VARIABLES = (
    "TARGET_GROUNDED", "TEST_COVERAGE_PRESENT", "DEPENDENCY_IMPACT_BOUNDED",
    "PUBLIC_API_RISK", "EXTERNAL_EFFECT_RISK", "CHANGE_REGION_CONFINED",
    "READY_FOR_AGENT_HANDOFF",
)


def analyze_coding_region(
    *,
    node_ids: list[str] | None = None,
    topology_graph: dict[str, Any] | None = None,
    source_grounded: bool = False,
    tests_present: bool = False,
    dependency_depth: int = 0,
    public_api_touched: bool = False,
    external_effects: list[str] | None = None,
    diagnostics: dict[str, Any] | None = None,
    change_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze a coding region and return tensor evidence + belief propagation results.

    Advisory only. Does not change patch authority.
    """
    external_effects = external_effects or []
    n = max(1, len(node_ids or []))

    # Build variables
    variables = [
        TensorVariable("TARGET_GROUNDED",
                       evidence_refs=[EvidenceReference(topology_node_id=nid) for nid in (node_ids or [])]),
        TensorVariable("TEST_COVERAGE_PRESENT"),
        TensorVariable("DEPENDENCY_IMPACT_BOUNDED"),
        TensorVariable("PUBLIC_API_RISK"),
        TensorVariable("EXTERNAL_EFFECT_RISK",
                       evidence_refs=[EvidenceReference(human_note=e) for e in external_effects]),
        TensorVariable("CHANGE_REGION_CONFINED"),
        TensorVariable("READY_FOR_AGENT_HANDOFF"),
    ]

    # Build unary factors from observed facts
    def unary(vals): return np.array(vals, dtype=np.float64)

    factors = [
        # TARGET_GROUNDED
        TensorFactor("f_grounded", ["TARGET_GROUNDED"],
                     unary([0.9, 0.05, 0.05]) if source_grounded else unary([0.2, 0.1, 0.7])),
        # TEST_COVERAGE_PRESENT
        TensorFactor("f_tests", ["TEST_COVERAGE_PRESENT"],
                     unary([0.85, 0.1, 0.05]) if tests_present else unary([0.1, 0.05, 0.85])),
        # DEPENDENCY_IMPACT_BOUNDED
        TensorFactor("f_deps", ["DEPENDENCY_IMPACT_BOUNDED"],
                     unary([0.8, 0.1, 0.1]) if dependency_depth <= 3 else unary([0.1, 0.2, 0.7])),
        # PUBLIC_API_RISK
        TensorFactor("f_api", ["PUBLIC_API_RISK"],
                     unary([0.1, 0.8, 0.1]) if public_api_touched else unary([0.8, 0.1, 0.1])),
        # EXTERNAL_EFFECT_RISK
        TensorFactor("f_ext", ["EXTERNAL_EFFECT_RISK"],
                     unary([0.1, 0.8, 0.1]) if len(external_effects) > 2 else unary([0.7, 0.2, 0.1])),
    ]

    # Pairwise factors
    # Grounded + Tests -> Ready
    factors.append(TensorFactor("f_grounded_tests", ["TARGET_GROUNDED", "TEST_COVERAGE_PRESENT"],
        np.array([[0.7,0.2,0.1],[0.1,0.8,0.1],[0.2,0.2,0.6]])))
    # Deps + API -> Ready
    factors.append(TensorFactor("f_deps_api", ["DEPENDENCY_IMPACT_BOUNDED", "PUBLIC_API_RISK"],
        np.array([[0.8,0.1,0.1],[0.1,0.8,0.1],[0.2,0.3,0.5]])))
    # External -> Confined (R4 fix: connect CHANGE_REGION_CONFINED to evidence chain)
    factors.append(TensorFactor("f_ext_confined", ["EXTERNAL_EFFECT_RISK", "CHANGE_REGION_CONFINED"],
        np.array([[0.8,0.1,0.1],[0.1,0.8,0.1],[0.2,0.3,0.5]])))
    # Deps -> Confined
    factors.append(TensorFactor("f_deps_confined", ["DEPENDENCY_IMPACT_BOUNDED", "CHANGE_REGION_CONFINED"],
        np.array([[0.7,0.2,0.1],[0.1,0.8,0.1],[0.3,0.3,0.4]])))
    # Confined + Grounded -> Ready (C1 fix: derive readiness from prerequisites)
    factors.append(TensorFactor("f_confined_grounded_ready", ["CHANGE_REGION_CONFINED", "TARGET_GROUNDED", "READY_FOR_AGENT_HANDOFF"],
        np.array([
            [[0.8,0.1,0.1],[0.6,0.2,0.2],[0.2,0.3,0.5]],  # confined=supported
            [[0.2,0.3,0.5],[0.1,0.8,0.1],[0.1,0.3,0.6]],  # confined=contradicted
            [[0.2,0.2,0.6],[0.2,0.2,0.6],[0.1,0.2,0.7]],  # confined=unresolved
        ])))
    # Tests -> Ready (C1 fix: readiness depends on tests too)
    factors.append(TensorFactor("f_tests_ready", ["TEST_COVERAGE_PRESENT", "READY_FOR_AGENT_HANDOFF"],
        np.array([[0.7,0.2,0.1],[0.1,0.8,0.1],[0.3,0.3,0.4]])))

    engine = TensorBeliefEngine()
    result = engine.analyze(variables, factors)

    # Build advisory summary
    beliefs = {r["var_id"]: r for r in result["results"]}
    supported = [r["var_id"] for r in result["results"] if r["state"] == SUPPORTED]
    contradicted = [r["var_id"] for r in result["results"] if r["state"] == CONTRADICTED]
    unresolved = [r["var_id"] for r in result["results"] if r["state"] == UNRESOLVED]

    ready = beliefs.get("READY_FOR_AGENT_HANDOFF", {})
    confined = beliefs.get("CHANGE_REGION_CONFINED", {})

    return {
        "ok": result["ok"],
        "tensor_evidence": {
            "status": result["status"],
            "iterations": result["iterations"],
            "max_residual": result["max_residual"],
            "graph_hash": result["graph_hash"],
            "supported": supported,
            "contradicted": contradicted,
            "unresolved": unresolved,
            "confinement": result["confinement"],
            "belief_results": result["results"],
            "n_variables": result["n_variables"],
            "n_factors": result["n_factors"],
            "execution_time_ms": result["execution_time_ms"],
        },
        "advisory_summary": {
            "ready_for_agent_handoff": ready.get("state") == SUPPORTED,
            "change_region_confined": confined.get("state") == SUPPORTED,
            "confinement_level": result["confinement"]["confinement_level"],
            "influence_radius": result["confinement"]["influence_radius"],
            "local_recompute_allowed": result["confinement"]["local_recompute_allowed"],
            "human_review_recommended": len(unresolved) > 0 or len(contradicted) > 0,
            "boundary_nodes": [vid for vid in contradicted],
        },
        "patch_authority": PATCH_AUTHORITY,
        "tensor_patch_authority": TENSOR_PATCH_AUTHORITY,
        "belief_propagation_patch_authority": BELIEF_PROPAGATION_PATCH_AUTHORITY,
    }

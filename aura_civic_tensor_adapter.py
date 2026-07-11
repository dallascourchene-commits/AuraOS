"""
Aura Civic Tensor Adapter — builds a bounded factor graph from a Civic session.

Variables: NEED_SUPPORTED, OFFER_AVAILABLE, MATCH_FEASIBLE, EVIDENCE_SUFFICIENT,
SCENARIO_VIABLE, BUDGET_INFORMATION_COMPLETE, LEGAL_INFORMATION_CURRENT,
REPRESENTATION_SUFFICIENT, CONSENT_UNRESOLVED, DISSENT_PRESENT,
PILOT_READY_FOR_DELIBERATION.

Advisory only — never becomes Civic decision authority. Preserves dissent,
representation gaps, unresolved evidence, and conflicting contributions.
"""
from __future__ import annotations
from typing import Any
import numpy as np

from aura_tensor_evidence import (
    TensorVariable, TensorFactor, EvidenceReference, TensorBeliefEngine,
    SUPPORTED, CONTRADICTED, UNRESOLVED,
    STATE_INDEX,
    PATCH_AUTHORITY, CIVIC_DECISION_AUTHORITY,
)

CIVIC_VARIABLES = (
    "NEED_SUPPORTED", "OFFER_AVAILABLE", "MATCH_FEASIBLE", "EVIDENCE_SUFFICIENT",
    "SCENARIO_VIABLE", "BUDGET_INFORMATION_COMPLETE", "LEGAL_INFORMATION_CURRENT",
    "REPRESENTATION_SUFFICIENT", "CONSENT_UNRESOLVED", "DISSENT_PRESENT",
    "PILOT_READY_FOR_DELIBERATION",
)


def analyze_civic_session(session: dict[str, Any]) -> dict[str, Any]:
    """Build a tensor evidence graph from a Civic session and run BP.

    Advisory only. Never declares community consensus. Preserves dissent.
    """
    needs = session.get("needs", [])
    offers = session.get("offers", [])
    match_results = session.get("match_results", [])
    workstreams = session.get("workstreams", [])
    scenarios = session.get("scenarios", [])
    legal_instruments = session.get("legal_instruments", [])
    consent_arc = session.get("consent_arc", {})
    representation_gaps = session.get("representation_gaps", []) or \
                          consent_arc.get("representation_gaps", [])
    pilot = session.get("pilot", {})
    what_if = session.get("what_if", {})
    decision_packet = session.get("decision_packet", {})

    has_needs = len(needs) > 0
    has_offers = len(offers) > 0
    has_matches = any(m.get("ok") for m in match_results) if match_results else False
    has_evidence = len(legal_instruments) > 0
    has_scenarios = len(scenarios) > 0
    # Guard consent_arc access (R1 fix: crashes if non-dict)
    if isinstance(consent_arc, dict):
        has_consent = bool(consent_arc.get("responses"))
        has_dissent = any(r.get("response_type") in ("OBJECT", "CRITICAL_OBJECTION")
                          for r in consent_arc.get("responses", []))
    else:
        has_consent = False
        has_dissent = False
    has_representation_gaps = len(representation_gaps) > 0
    has_pilot = bool(pilot)

    def unary(vals): return np.array(vals, dtype=np.float64)

    variables = [
        TensorVariable("NEED_SUPPORTED",
                       evidence_refs=[EvidenceReference(civic_contribution_id=n.get("id","")) for n in needs]),
        TensorVariable("OFFER_AVAILABLE",
                       evidence_refs=[EvidenceReference(civic_contribution_id=o.get("id","")) for o in offers]),
        TensorVariable("MATCH_FEASIBLE"),
        TensorVariable("EVIDENCE_SUFFICIENT",
                       evidence_refs=[EvidenceReference(civic_evidence_id=li.get("id","")) for li in legal_instruments]),
        TensorVariable("SCENARIO_VIABLE"),
        TensorVariable("BUDGET_INFORMATION_COMPLETE"),
        TensorVariable("LEGAL_INFORMATION_CURRENT"),
        TensorVariable("REPRESENTATION_SUFFICIENT"),
        TensorVariable("CONSENT_UNRESOLVED"),
        TensorVariable("DISSENT_PRESENT",
                       evidence_refs=[EvidenceReference(human_note="Dissent preserved")]),
        TensorVariable("PILOT_READY_FOR_DELIBERATION"),
    ]

    factors = [
        TensorFactor("f_need", ["NEED_SUPPORTED"],
                     unary([0.85, 0.05, 0.1]) if has_needs else unary([0.05, 0.1, 0.85])),
        TensorFactor("f_offer", ["OFFER_AVAILABLE"],
                     unary([0.8, 0.1, 0.1]) if has_offers else unary([0.1, 0.1, 0.8])),
        TensorFactor("f_match", ["MATCH_FEASIBLE"],
                     unary([0.75, 0.1, 0.15]) if has_matches else unary([0.1, 0.2, 0.7])),
        TensorFactor("f_evidence", ["EVIDENCE_SUFFICIENT"],
                     unary([0.7, 0.1, 0.2]) if has_evidence else unary([0.1, 0.1, 0.8])),
        TensorFactor("f_scenario", ["SCENARIO_VIABLE"],
                     unary([0.7, 0.15, 0.15]) if has_scenarios else unary([0.1, 0.1, 0.8])),
        TensorFactor("f_budget", ["BUDGET_INFORMATION_COMPLETE"],
                     unary([0.3, 0.1, 0.6])),  # usually incomplete in fixture mode
        TensorFactor("f_legal", ["LEGAL_INFORMATION_CURRENT"],
                     unary([0.6, 0.1, 0.3]) if has_evidence else unary([0.1, 0.1, 0.8])),
        TensorFactor("f_representation", ["REPRESENTATION_SUFFICIENT"],
                     unary([0.1, 0.2, 0.7]) if has_representation_gaps else unary([0.6, 0.2, 0.2])),
        TensorFactor("f_consent", ["CONSENT_UNRESOLVED"],
                     unary([0.2, 0.1, 0.7]) if has_consent else unary([0.8, 0.1, 0.1])),
        TensorFactor("f_dissent", ["DISSENT_PRESENT"],
                     unary([0.8, 0.1, 0.1]) if has_dissent else unary([0.1, 0.1, 0.8])),
        # Pairwise: need + offer -> match
        TensorFactor("f_need_offer", ["NEED_SUPPORTED", "OFFER_AVAILABLE"],
                     np.array([[0.8,0.1,0.1],[0.1,0.8,0.1],[0.2,0.2,0.6]])),
        # Pairwise: match + evidence -> scenario
        TensorFactor("f_match_evidence", ["MATCH_FEASIBLE", "EVIDENCE_SUFFICIENT"],
                     np.array([[0.8,0.1,0.1],[0.1,0.8,0.1],[0.2,0.3,0.5]])),
        # Pairwise: scenario + representation -> pilot (R5 fix: connect pilot to evidence chain)
        TensorFactor("f_scenario_repr", ["SCENARIO_VIABLE", "REPRESENTATION_SUFFICIENT"],
                     np.array([[0.7,0.2,0.1],[0.1,0.8,0.1],[0.3,0.3,0.4]])),
        # Pairwise: representation + consent -> pilot (connects pilot to consent island)
        TensorFactor("f_repr_consent_pilot", ["REPRESENTATION_SUFFICIENT", "CONSENT_UNRESOLVED"],
                     np.array([[0.6,0.3,0.1],[0.1,0.7,0.2],[0.3,0.3,0.4]])),
        # Pairwise: pilot connects to scenario+representation island
        TensorFactor("f_scenario_pilot", ["SCENARIO_VIABLE", "PILOT_READY_FOR_DELIBERATION"],
                     np.array([[0.7,0.2,0.1],[0.1,0.8,0.1],[0.3,0.3,0.4]])),
        # Pairwise: dissent + consent -> pilot (connects dissent island to pilot)
        TensorFactor("f_dissent_pilot", ["DISSENT_PRESENT", "PILOT_READY_FOR_DELIBERATION"],
                     np.array([[0.6,0.3,0.1],[0.1,0.7,0.2],[0.3,0.3,0.4]])),
        # Pilot readiness
        TensorFactor("f_pilot", ["PILOT_READY_FOR_DELIBERATION"],
                     unary([0.6, 0.1, 0.3]) if has_pilot else unary([0.2, 0.1, 0.7])),
    ]

    engine = TensorBeliefEngine()
    result = engine.analyze(variables, factors)

    beliefs = {r["var_id"]: r for r in result["results"]}
    supported = [r["var_id"] for r in result["results"] if r["state"] == SUPPORTED]
    contradicted = [r["var_id"] for r in result["results"] if r["state"] == CONTRADICTED]
    unresolved = [r["var_id"] for r in result["results"] if r["state"] == UNRESOLVED]

    # Preserve dissent and representation gaps explicitly
    dissent_present = beliefs.get("DISSENT_PRESENT", {}).get("state") == SUPPORTED
    consent_unresolved = beliefs.get("CONSENT_UNRESOLVED", {}).get("state") == SUPPORTED
    representation_insufficient = beliefs.get("REPRESENTATION_SUFFICIENT", {}).get("state") == CONTRADICTED

    return {
        "ok": result["ok"],
        "tensor_evidence_analysis": {
            "status": result["status"],
            "iterations": result["iterations"],
            "max_residual": result["max_residual"],
            "graph_hash": result["graph_hash"],
            "supported_variables": supported,
            "contradicted_variables": contradicted,
            "unresolved_variables": unresolved,
            "confinement": result["confinement"],
            "belief_results": result["results"],
            "dissent_preserved": dissent_present,
            "consent_unresolved": consent_unresolved,
            "representation_gaps_visible": representation_insufficient or has_representation_gaps,
            "non_binding": True,
            "no_consensus_declared": True,  # never declare consensus
            "evidence_references": [r for res in result["results"] for r in res.get("supporting_evidence",[])],
            "n_variables": result["n_variables"],
            "n_factors": result["n_factors"],
            "execution_time_ms": result["execution_time_ms"],
        },
        "scenario_support": {
            vid: beliefs.get(vid, {}).get("beliefs", [0, 0, 0])[STATE_INDEX[SUPPORTED]]
            for vid in ["SCENARIO_VIABLE", "PILOT_READY_FOR_DELIBERATION", "MATCH_FEASIBLE"]
        },
        "patch_authority": "exact_source_spans_and_hashes_only",
        "civic_decision_authority": CIVIC_DECISION_AUTHORITY,
    }

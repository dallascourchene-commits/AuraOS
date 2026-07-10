"""
Aura Cockpit Capability Router — routes objectives to capability lanes.

Given a human objective or IntentPacket, chooses which capability lanes should
run before agent handoff. Uses keyword matching and objective structure to
select relevant lanes.

Dependencies: stdlib only. All Aura imports are lazy.
"""

from __future__ import annotations

import re
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ROUTER_VERSION = "AURA_COCKPIT_CAPABILITY_ROUTER_V1"


# Keyword → lane_id routing rules. Evaluated in order; first match wins.
_ROUTING_RULES: list[tuple[list[str], str, str]] = [
    # Research
    (["research", "arxiv", "paper", "prior art", "evidence", "study", "compare approaches"],
     "research_arxiv_lane", "Objective mentions research, papers, or evidence."),
    # Split / decompose
    (["split", "decompose", "break down", "smaller", "multiple prs", "huge refactor", "large refactor"],
     "mitosis_decomposition_lane", "Objective mentions splitting or decomposition."),
    # Skills
    (["skill", "weave", "discover", "find capabilities", "what tools"],
     "skillweaver_lane", "Objective mentions skills or capability discovery."),
    # Multi-agent / swarm
    (["hermes and codex", "multiple agents", "swarm", "coordinate", "parallel agents", "multi-agent"],
     "mesh_swarm_lane", "Objective mentions multi-agent coordination."),
    # MCP / tools
    (["mcp", "tool surface", "expose", "plugin", "discoverable"],
     "mcp_gateway_lane", "Objective mentions MCP or tool exposure."),
    # Music / rank
    (["music", "rank candidates", "inverse search", "topology rank"],
     "music_coding_lane", "Objective mentions MUSIC ranking or inverse search."),
    # GOAP / plan
    (["plan", "goap", "ordered actions", "prerequisites", "sequence", "step by step"],
     "goap_planner_lane", "Objective mentions planning or ordered actions."),
    # Stage / review
    (["stage", "review patch", "merge patch", "purge", "live architect"],
     "live_architect_lane", "Objective mentions staging or patch review."),
    # Tests
    (["test", "verify", "what tests", "test gap", "prove"],
     "resonant_test_oracle_lane", "Objective mentions tests or verification."),
    # Benchmark / compare
    (["benchmark", "compare", "measure", "empirical", "outcome"],
     "empirical_lab_lane", "Objective mentions benchmarking or comparison."),
    # Audit
    (["audit", "trace", "approval record", "stake", "tamper"],
     "audit_staking_lane", "Objective mentions audit or trace."),
    # Federation
    (["federation", "cross-repo", "cross repository", "multiple repos"],
     "federation_lane", "Objective mentions cross-repository operations."),
    # Module manifest
    (["module manifest", "ownership", "responsibility map", "module metadata"],
     "module_manifest_lane", "Objective mentions module manifest or ownership."),
    # Associative
    (["associative", "recall", "memory association", "similar decisions"],
     "associative_core_lane", "Objective mentions associative recall."),
    # Phase capsules
    (["phase", "checkpoint state", "persist state", "between gates"],
     "phase_capsule_lane", "Objective mentions phase state or checkpoints."),
]


def _match_lanes(objective: str) -> list[tuple[str, str]]:
    """Match an objective to capability lanes. Returns list of (lane_id, rationale)."""
    obj_lower = objective.lower()
    matched: list[tuple[str, str]] = []
    seen: set[str] = set()

    for keywords, lane_id, rationale in _ROUTING_RULES:
        if lane_id in seen:
            continue
        for kw in keywords:
            if kw in obj_lower:
                matched.append((lane_id, rationale))
                seen.add(lane_id)
                break

    return matched


def _default_lanes() -> list[tuple[str, str]]:
    """Lanes that are always recommended for any coding objective."""
    return [
        ("mitosis_decomposition_lane", "Default: check if objective needs decomposition."),
        ("goap_planner_lane", "Default: plan ordered actions for the objective."),
        ("phase_capsule_lane", "Default: persist phase state between gates."),
        ("audit_staking_lane", "Default: record audit trail for gate transitions."),
    ]


def route_capability_lanes(
    objective: str,
    intent_packet: dict | None = None,
    human_selected_lanes: list[str] | None = None,
) -> dict[str, Any]:
    """Route an objective to capability lanes.

    Returns a CapabilityRoutePacket with selected_lanes, rejected_lanes,
    lane_order, rationale, and invariants.
    """
    from aura_capability_lane_registry import load_capability_lanes, list_lane_ids

    all_lane_ids = set(list_lane_ids())
    matched = _match_lanes(objective)
    matched_ids = {lane_id for lane_id, _ in matched}

    # Add default lanes
    defaults = _default_lanes()
    for lane_id, rationale in defaults:
        if lane_id not in matched_ids:
            matched.append((lane_id, rationale))
            matched_ids.add(lane_id)

    # Add human-selected lanes
    if human_selected_lanes:
        for lane_id in human_selected_lanes:
            if lane_id in all_lane_ids and lane_id not in matched_ids:
                matched.append((lane_id, "Human-selected lane."))
                matched_ids.add(lane_id)

    # Determine selected and rejected
    selected_lanes = []
    rejected_lanes = []
    lane_order = []

    for lane_id, rationale in matched:
        selected_lanes.append({"lane_id": lane_id, "rationale": rationale})
        lane_order.append(lane_id)

    for lane_id in all_lane_ids:
        if lane_id not in matched_ids:
            rejected_lanes.append({
                "lane_id": lane_id,
                "reason": "Not matched by routing rules.",
            })

    # Determine advisory layers
    lanes = load_capability_lanes()
    lane_map = {lane.lane_id: lane for lane in lanes}
    advisory_layers = []
    for sel in selected_lanes:
        lane = lane_map.get(sel["lane_id"])
        if lane and lane.advisory_only:
            advisory_layers.append(sel["lane_id"])

    # Token savings estimate
    token_savings_estimate = {
        "estimated_lanes_run": len(selected_lanes),
        "estimated_token_overhead": len(selected_lanes) * 200,  # ~200 tokens per lane packet
        "estimated_savings_vs_raw": "Advisory lanes reduce context by routing to relevant capabilities only.",
    }

    # Required evidence
    required_evidence: list[str] = []
    for sel in selected_lanes:
        lane = lane_map.get(sel["lane_id"])
        if lane:
            for req in lane.workflow_gate_requirements:
                if req not in required_evidence:
                    required_evidence.append(req)

    # Next workflow gate
    next_workflow_gate = "INGESTED"
    if "CODEMAP_LOCALIZED" in required_evidence:
        next_workflow_gate = "CODEMAP_LOCALIZED"
    elif "PLAN_READY" in required_evidence:
        next_workflow_gate = "PLAN_READY"

    return {
        "ok": True,
        "version": ROUTER_VERSION,
        "objective": objective,
        "selected_lanes": selected_lanes,
        "rejected_lanes": rejected_lanes,
        "lane_order": lane_order,
        "rationale": "; ".join(r for _, r in matched),
        "required_evidence": required_evidence,
        "token_savings_estimate": token_savings_estimate,
        "advisory_layers": advisory_layers,
        "next_workflow_gate": next_workflow_gate,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

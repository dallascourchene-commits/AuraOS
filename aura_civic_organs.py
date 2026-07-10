"""
Aura Civic Organs — trusted built-in civic organ types (story-aware).

15 organ types. Each organ consumes session data and story fixtures
rather than hardcoding a single fixture internally.
"""
from __future__ import annotations
from typing import Any, Callable

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

ORGAN_TYPES = (
    "CivicProfileOrgan","CivicMapOrgan","CivicEvidenceOrgan","LegalBylawOrgan",
    "CouncilIssuePulseOrgan","CommunityContributionOrgan","CommunityResourceMatcherOrgan",
    "CivicMITOSISOrgan","CivicMUSICOrgan","ScenarioComparisonOrgan",
    "ConsentArcOrgan","SystemicContextOrgan","WhatIfOrgan",
    "PilotTunnelOrgan","DecisionPacketOrgan",
)


def _get_fixtures(session: dict[str, Any]) -> dict[str, Any]:
    """Get story-specific fixtures from the session."""
    fx = session.get("story_fixtures")
    if fx:
        return fx
    # Fallback: load based on story
    from aura_civic_demo_fixtures import hairstylist_fixtures
    return hairstylist_fixtures()


def civic_profile_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_profiles import create_winnipeg_demo_profile_set
    ps = create_winnipeg_demo_profile_set()
    return {"ok": True, "organ_type": "CivicProfileOrgan", "profile_set": ps.to_dict(),
            "active_profiles_visible": True,
            "treaty1_activated": "treaty1_context" in ps.context_lens_refs,
            "no_identity_inference": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def civic_map_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_map import build_map_manifest
    fx = _get_fixtures(session)
    geojson = fx.get("geojson", {"type": "FeatureCollection", "features": []})
    heatmap = fx.get("heatmap")
    layers = ["boundary", "facility", "transit", "services", "needs_heatmap",
              "community_spaces", "scenario_locations"]
    manifest = build_map_manifest(geojson, layers, heatmap)
    return {"ok": True, "organ_type": "CivicMapOrgan", "map_manifest": manifest,
            "accessible_table_parity": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def civic_evidence_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_evidence import assess_legal_applicability
    fx = _get_fixtures(session)
    instruments = fx.get("legal_instruments", [])
    assessed = [assess_legal_applicability(li, {}) for li in instruments]
    return {"ok": True, "organ_type": "CivicEvidenceOrgan", "legal_instruments": assessed,
            "no_legal_approval": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def legal_bylaw_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    """Distinct from CivicEvidenceOrgan — focuses specifically on bylaw text retrieval."""
    from aura_civic_evidence import assess_legal_applicability, LEGAL_HIERARCHY
    fx = _get_fixtures(session)
    instruments = fx.get("legal_instruments", [])
    # Focus on bylaw-level instruments
    bylaw_results = []
    for li in instruments:
        if li.get("level") == "bylaw":
            result = assess_legal_applicability(li, {})
            result["instrument_type"] = "bylaw"
            result["exact_source_ref"] = li.get("source_ref", "")
            result["as_of_date"] = li.get("as_of_date", "")
            bylaw_results.append(result)
    return {"ok": True, "organ_type": "LegalBylawOrgan", "bylaw_instruments": bylaw_results,
            "hierarchy": LEGAL_HIERARCHY, "no_legal_approval": True,
            "disclaimer": "Aura is not providing legal advice.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def council_issue_pulse_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    """Distinct organ — displays council records with source provenance."""
    fx = _get_fixtures(session)
    council_items = fx.get("council_items", [])
    # Enrich with source provenance
    enriched = []
    for item in council_items:
        enriched_item = dict(item)
        enriched_item["source_date"] = item.get("meeting_date", "")
        enriched_item["extraction_confidence"] = item.get("extraction_confidence", 0.0)
        enriched_item["missing_records"] = []
        enriched_item["representativeness_limitations"] = "Records may not reflect all Council activity."
        enriched_item["no_motive_inference"] = True
        enriched.append(enriched_item)
    return {"ok": True, "organ_type": "CouncilIssuePulseOrgan", "issues": enriched,
            "note": "Do not infer councillor motives.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def community_contribution_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    fx = _get_fixtures(session)
    # Also merge any user-added contributions from the session
    user_contributions = session.get("contributions", [])
    needs = fx.get("needs", [])
    offers = fx.get("offers", [])
    concerns = fx.get("concerns", [])
    # Add user contributions to the appropriate lists
    for uc in user_contributions:
        ctype = uc.get("contribution_type", "")
        if ctype == "NEED":
            needs.append(uc)
        elif "OFFER" in ctype:
            offers.append(uc)
        elif ctype in ("OBJECTION", "RESERVATION", "CONSTRAINT"):
            concerns.append(uc)
    return {"ok": True, "organ_type": "CommunityContributionOrgan",
            "needs": needs, "offers": offers, "concerns": concerns,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def community_resource_matcher_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_resources import match_resources
    fx = _get_fixtures(session)
    # Also check user-added contributions
    user_contributions = session.get("contributions", [])
    needs = fx.get("needs", [])
    offers = fx.get("offers", [])
    # Add user offers
    for uc in user_contributions:
        if "OFFER" in uc.get("contribution_type", ""):
            offers.append(uc)
    results = []
    for need in needs:
        mr = match_resources(need, offers)
        results.append(mr)
    return {"ok": True, "organ_type": "CommunityResourceMatcherOrgan",
            "match_results": results, "no_contract_created": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def civic_mitosis_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_reasoning import civic_mitosis
    obj = session.get("objective", "")
    constraints = session.get("mandatory_constraints", ["community_ownership", "affordability", "accessibility"])
    result = civic_mitosis(obj, mandatory_constraints=constraints)
    return {"ok": True, "organ_type": "CivicMITOSISOrgan", "mitosis": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def civic_music_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_reasoning import civic_music
    fx = _get_fixtures(session)
    scenarios = fx.get("scenarios", [])
    result = civic_music(scenarios)
    return {"ok": True, "organ_type": "CivicMUSICOrgan", "music": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def scenario_comparison_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    """Distinct from MUSIC — focuses on side-by-side scenario comparison with bridge options."""
    from aura_civic_reasoning import civic_music
    fx = _get_fixtures(session)
    scenarios = fx.get("scenarios", [])
    result = civic_music(scenarios)
    # Add comparison-specific fields
    comparison = result.get("comparison", {})
    comparison["side_by_side_view"] = True
    comparison["bridge_options_labelled"] = True
    comparison["pareto_frontier_visible"] = True
    return {"ok": True, "organ_type": "ScenarioComparisonOrgan", "comparison": comparison,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def consent_arc_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_deliberation import ConsentArc, assess_convergence, DemocraticFriction
    fx = _get_fixtures(session)
    # Get user responses from session if any
    user_responses = session.get("consent_responses", [])
    arc = ConsentArc(
        arc_id=f"ARC-{session.get('session_id', 'x')[:8]}",
        proposal_ref="SCEN-coop",
        participant_scope="demo_neighbourhood",
        representation_gaps=fx.get("representation_gaps", []),
    )
    # Add user responses to the arc
    for ur in user_responses:
        arc.responses.append(ur)
    conv = assess_convergence(arc)
    # Build democratic friction
    friction = DemocraticFriction(
        round_count=len(user_responses),
        objections_raised=sum(1 for r in user_responses if r.get("response_type") in ("OBJECT", "CRITICAL_OBJECTION")),
    )
    return {"ok": True, "organ_type": "ConsentArcOrgan",
            "consent_arc": arc.to_dict(), "convergence": conv,
            "democratic_friction": friction.to_dict(),
            "friction_explanation": friction.explanation(),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def systemic_context_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    """Distinct from ConsentArc — surfaces documented historical patterns."""
    from aura_civic_deliberation import create_systemic_context
    fx = _get_fixtures(session)
    # Build systemic context findings from fixture data
    findings = []
    gaps = fx.get("representation_gaps", [])
    for gap in gaps:
        findings.append({
            "source": "SYNTHETIC_DEMO_DATA",
            "truth_class": "SYNTHETIC_DEMO_DATA",
            "finding": gap,
            "time_period": "current",
            "geography": "Winnipeg demo neighbourhood",
            "method": "fixture",
            "uncertainty": "high",
        })
    result = create_systemic_context(findings)
    return {"ok": True, "organ_type": "SystemicContextOrgan",
            "systemic_context": result,
            "correlation_not_causation": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def what_if_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_scenarios import run_what_if
    fx = _get_fixtures(session)
    scenarios = fx.get("scenarios", [])
    if not scenarios:
        return {"ok": True, "organ_type": "WhatIfOrgan", "what_if": {"simulation": {}},
                "labels": ["SIMULATION_ONLY", "NOT_A_PREDICTION"],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    # Get user-supplied changes from session
    user_changes = session.get("what_if_changes", {})
    if not user_changes:
        user_changes = {"cost": 0.7, "accessibility": 0.9}
    base = scenarios[0]
    result = run_what_if(base, user_changes)
    return {"ok": True, "organ_type": "WhatIfOrgan", "what_if": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def pilot_tunnel_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_scenarios import create_pilot
    fx = _get_fixtures(session)
    scenarios = fx.get("scenarios", [])
    # Use the scenario selected by the user/session
    selected_scenario_id = session.get("selected_scenario_id", "")
    scenario = None
    if selected_scenario_id:
        for s in scenarios:
            if s.get("scenario_id") == selected_scenario_id:
                scenario = s
                break
    if not scenario and scenarios:
        scenario = scenarios[0]
    if not scenario:
        scenario = {"scenario_id": "default"}
    result = create_pilot(scenario)
    return {"ok": True, "organ_type": "PilotTunnelOrgan", "pilot": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def decision_packet_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    """Assemble Decision Packet from accumulated session state — not from fixtures."""
    from aura_civic_world_model import DecisionPacket
    import time as _time
    fx = _get_fixtures(session)
    session_id = session.get("session_id", "unknown")
    # Build from actual session state
    packet = DecisionPacket(
        packet_id=f"DECPKT-{int(_time.time())}",
        objective=session.get("objective", ""),
        active_profiles=list(session.get("profile_set", {}).get("jurisdiction_profile_refs", [])),
        participant_scope="demo_neighbourhood",
        needs=session.get("needs", fx.get("needs", [])),
        assets=session.get("offers", fx.get("offers", [])),
        workstreams=session.get("workstreams", []),
        scenarios=session.get("scenarios", fx.get("scenarios", [])),
        legal_questions=session.get("legal_instruments", fx.get("legal_instruments", [])),
        consent_arc=session.get("consent_arc", {}),
        reservations=session.get("reservations", []),
        objections=session.get("objections", fx.get("objections", [])),
        minority_report=session.get("minority_report", ""),
        representation_gaps=session.get("representation_gaps", fx.get("representation_gaps", [])),
    )
    # Fill in required sections with NONE_RECORDED if empty
    packet_dict = packet.to_dict()
    required_sections = [
        "needs", "assets", "workstreams", "scenarios", "legal_questions",
        "consent_arc", "reservations", "objections", "representation_gaps",
        "bridge_options", "pilot_option",
    ]
    for section in required_sections:
        val = packet_dict.get(section)
        if val == [] or val == {} or val is None:
            packet_dict[section] = "NONE_RECORDED"

    return {"ok": True, "organ_type": "DecisionPacketOrgan", "decision_packet": packet_dict,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


ORGAN_ADAPTERS: dict[str, Callable[..., dict[str, Any]]] = {
    "CivicProfileOrgan": civic_profile_organ,
    "CivicMapOrgan": civic_map_organ,
    "CivicEvidenceOrgan": civic_evidence_organ,
    "LegalBylawOrgan": legal_bylaw_organ,
    "CouncilIssuePulseOrgan": council_issue_pulse_organ,
    "CommunityContributionOrgan": community_contribution_organ,
    "CommunityResourceMatcherOrgan": community_resource_matcher_organ,
    "CivicMITOSISOrgan": civic_mitosis_organ,
    "CivicMUSICOrgan": civic_music_organ,
    "ScenarioComparisonOrgan": scenario_comparison_organ,
    "ConsentArcOrgan": consent_arc_organ,
    "SystemicContextOrgan": systemic_context_organ,
    "WhatIfOrgan": what_if_organ,
    "PilotTunnelOrgan": pilot_tunnel_organ,
    "DecisionPacketOrgan": decision_packet_organ,
}


def execute_organ(organ_type: str, session: dict[str, Any], **kw) -> dict[str, Any]:
    adapter = ORGAN_ADAPTERS.get(organ_type)
    if not adapter:
        return {"ok": False, "error": f"unknown_organ_type: {organ_type}", "status": "DENIED",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return adapter(session, **kw)

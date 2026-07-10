"""Aura Civic Organs — trusted built-in civic organ types.

15 organ types. Trusted predefined adapters only. No arbitrary generated code.
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

def civic_profile_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_profiles import create_winnipeg_demo_profile_set, get_profile
    ps = create_winnipeg_demo_profile_set()
    return {"ok": True, "organ_type": "CivicProfileOrgan", "profile_set": ps.to_dict(),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def civic_map_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_demo_fixtures import hairstylist_fixtures
    from aura_civic_map import build_map_manifest
    fx = hairstylist_fixtures()
    manifest = build_map_manifest(fx["geojson"], ["boundary","facility","transit","services","needs_heatmap","community_spaces","scenario_locations"], fx["heatmap"])
    return {"ok": True, "organ_type": "CivicMapOrgan", "map_manifest": manifest,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def civic_evidence_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_demo_fixtures import hairstylist_fixtures
    from aura_civic_evidence import assess_legal_applicability
    fx = hairstylist_fixtures()
    assessed = [assess_legal_applicability(li, {}) for li in fx.get("legal_instruments", [])]
    return {"ok": True, "organ_type": "CivicEvidenceOrgan", "legal_instruments": assessed,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def council_issue_pulse_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_demo_fixtures import council_issue_fixtures
    fx = council_issue_fixtures()
    return {"ok": True, "organ_type": "CouncilIssuePulseOrgan", "issues": fx["issues"],
            "note": fx.get("note",""), "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def community_contribution_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_demo_fixtures import hairstylist_fixtures
    fx = hairstylist_fixtures()
    return {"ok": True, "organ_type": "CommunityContributionOrgan",
            "needs": fx["needs"], "offers": fx["offers"], "concerns": fx["concerns"],
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def community_resource_matcher_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_demo_fixtures import hairstylist_fixtures
    from aura_civic_resources import match_resources
    fx = hairstylist_fixtures()
    needs = fx["needs"]; offers = fx["offers"]
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
    constraints = session.get("mandatory_constraints", ["community_ownership","affordability","accessibility"])
    result = civic_mitosis(obj, mandatory_constraints=constraints)
    return {"ok": True, "organ_type": "CivicMITOSISOrgan", "mitosis": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def civic_music_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_demo_fixtures import hairstylist_fixtures
    from aura_civic_reasoning import civic_music
    fx = hairstylist_fixtures()
    result = civic_music(fx["scenarios"])
    return {"ok": True, "organ_type": "CivicMUSICOrgan", "music": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def consent_arc_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_deliberation import ConsentArc, assess_convergence
    from aura_civic_demo_fixtures import hairstylist_fixtures
    fx = hairstylist_fixtures()
    arc = ConsentArc(arc_id="ARC-001", proposal_ref="SCEN-coop",
                     participant_scope="demo_neighbourhood",
                     representation_gaps=fx.get("representation_gaps", []))
    conv = assess_convergence(arc)
    return {"ok": True, "organ_type": "ConsentArcOrgan", "consent_arc": arc.to_dict(),
            "convergence": conv, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def what_if_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_scenarios import run_what_if
    from aura_civic_demo_fixtures import hairstylist_fixtures
    fx = hairstylist_fixtures()
    base = fx["scenarios"][0]
    result = run_what_if(base, {"cost": 0.7, "accessibility": 0.9})
    return {"ok": True, "organ_type": "WhatIfOrgan", "what_if": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def pilot_tunnel_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_scenarios import create_pilot
    from aura_civic_demo_fixtures import hairstylist_fixtures
    fx = hairstylist_fixtures()
    result = create_pilot(fx["scenarios"][0])
    return {"ok": True, "organ_type": "PilotTunnelOrgan", "pilot": result,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def decision_packet_organ(session: dict[str, Any], **kw) -> dict[str, Any]:
    from aura_civic_world_model import DecisionPacket
    from aura_civic_demo_fixtures import hairstylist_fixtures
    import hashlib, time
    fx = hairstylist_fixtures()
    packet = DecisionPacket(
        packet_id=f"DECPKT-{int(time.time())}",
        objective=session.get("objective", fx["objective"]),
        active_profiles=["winnipeg_mb_ca","winnipeg_demo_community"],
        participant_scope="demo_neighbourhood",
        needs=fx["needs"],
        assets=fx["offers"],
        workstreams=[],
        scenarios=fx["scenarios"],
        legal_questions=fx.get("legal_instruments", []),
        consent_arc={},
        objections=fx.get("objections", []),
        representation_gaps=fx.get("representation_gaps", []),
    )
    return {"ok": True, "organ_type": "DecisionPacketOrgan", "decision_packet": packet.to_dict(),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

ORGAN_ADAPTERS: dict[str, Callable[..., dict[str, Any]]] = {
    "CivicProfileOrgan": civic_profile_organ,
    "CivicMapOrgan": civic_map_organ,
    "CivicEvidenceOrgan": civic_evidence_organ,
    "LegalBylawOrgan": civic_evidence_organ,
    "CouncilIssuePulseOrgan": council_issue_pulse_organ,
    "CommunityContributionOrgan": community_contribution_organ,
    "CommunityResourceMatcherOrgan": community_resource_matcher_organ,
    "CivicMITOSISOrgan": civic_mitosis_organ,
    "CivicMUSICOrgan": civic_music_organ,
    "ScenarioComparisonOrgan": civic_music_organ,
    "ConsentArcOrgan": consent_arc_organ,
    "SystemicContextOrgan": consent_arc_organ,
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

"""
Aura Civic Result Projector — atomically projects verified organ results into session state.

Projection occurs ONLY after verifier success.
A failed organ must not partially mutate the Civic session.
Records a WorldStateDelta for each projection.
"""
from __future__ import annotations
import hashlib, time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def project_civic_organ_result(session: dict[str, Any], organ_type: str, verified_result: dict[str, Any]) -> dict[str, Any]:
    """Project a verified organ result into session state.

    Returns the updates dict to be applied atomically.
    Does NOT mutate the session directly — the caller applies the updates.
    """
    if not verified_result.get("ok", False):
        return {"ok": False, "error": "result_not_ok",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    result = verified_result.get("result", verified_result)
    updates: dict[str, Any] = {}
    delta_entries: list[dict[str, Any]] = []

    # Map organ types to session fields
    if organ_type == "CivicProfileOrgan":
        if "profile_set" in result:
            updates["profile_set"] = result["profile_set"]
            updates["state"] = "PROFILED"
            delta_entries.append({"field": "profile_set", "change": "set"})

    elif organ_type == "CivicMapOrgan":
        if "map_manifest" in result:
            updates["map_manifest"] = result["map_manifest"]
            delta_entries.append({"field": "map_manifest", "change": "set"})

    elif organ_type == "CommunityContributionOrgan":
        if "needs" in result:
            updates["needs"] = result["needs"]
            delta_entries.append({"field": "needs", "change": "set"})
        if "offers" in result:
            updates["offers"] = result["offers"]
            delta_entries.append({"field": "offers", "change": "set"})

    elif organ_type == "CommunityResourceMatcherOrgan":
        if "match_results" in result:
            updates["match_results"] = result["match_results"]
            delta_entries.append({"field": "match_results", "change": "set"})

    elif organ_type == "CivicMITOSISOrgan":
        if "mitosis" in result:
            mitosis = result["mitosis"]
            updates["workstreams"] = mitosis.get("workstreams", [])
            delta_entries.append({"field": "workstreams", "change": "set"})

    elif organ_type in ("CivicMUSICOrgan", "ScenarioComparisonOrgan"):
        if organ_type == "CivicMUSICOrgan":
            # Unwrap nested payload envelope for CivicMUSICOrgan
            if "music" in result:
                music_data = result["music"]
                updates["scenarios"] = music_data.get("scenarios", [])
                updates["music_comparison"] = music_data
                delta_entries.append({"field": "scenarios", "change": "set"})
        else:
            # ScenarioComparisonOrgan uses flattened handling
            if "comparison" in result:
                music_data = result["comparison"]
                updates["scenarios"] = music_data.get("scenarios", [])
                updates["music_comparison"] = music_data
                delta_entries.append({"field": "scenarios", "change": "set"})

    elif organ_type in ("CivicEvidenceOrgan", "LegalBylawOrgan"):
        key = "legal_instruments" if organ_type == "CivicEvidenceOrgan" else "bylaw_instruments"
        if key in result:
            updates["legal_instruments"] = result[key]
            delta_entries.append({"field": "legal_instruments", "change": "set"})

    elif organ_type == "CouncilIssuePulseOrgan":
        if "issues" in result:
            updates["council_items"] = result["issues"]
            delta_entries.append({"field": "council_items", "change": "set"})

    elif organ_type == "ConsentArcOrgan":
        if "consent_arc" in result:
            updates["consent_arc"] = result["consent_arc"]
            updates["convergence"] = result.get("convergence", {})
            updates["democratic_friction"] = result.get("democratic_friction", {})
            delta_entries.append({"field": "consent_arc", "change": "set"})

    elif organ_type == "SystemicContextOrgan":
        if "systemic_context" in result:
            updates["systemic_context"] = result["systemic_context"]
            delta_entries.append({"field": "systemic_context", "change": "set"})

    elif organ_type == "WhatIfOrgan":
        if "what_if" in result:
            updates["what_if"] = result["what_if"]
            delta_entries.append({"field": "what_if", "change": "set"})

    elif organ_type == "PilotTunnelOrgan":
        if "pilot" in result:
            # Unwrap nested response envelope — store inner pilot packet
            pilot_envelope = result["pilot"]
            # If pilot_envelope has a nested "pilot" key, unwrap it; otherwise use as-is
            if isinstance(pilot_envelope, dict) and "pilot" in pilot_envelope:
                pilot_data = pilot_envelope["pilot"]
            else:
                pilot_data = pilot_envelope
            updates["pilot"] = pilot_data
            updates["state"] = "PILOT_PLANNING"
            delta_entries.append({"field": "pilot", "change": "set"})

    elif organ_type == "DecisionPacketOrgan":
        if "decision_packet" in result:
            updates["decision_packet"] = result["decision_packet"]
            updates["state"] = "DECISION_PACKET_READY"
            delta_entries.append({"field": "decision_packet", "change": "set"})

    # Record WorldStateDelta
    delta = {
        "delta_id": hashlib.blake2b(f"{organ_type}:{time.time()}".encode(), digest_size=8).hexdigest(),
        "organ_type": organ_type,
        "entries": delta_entries,
        "timestamp": time.time(),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    updates["_last_delta"] = delta

    return {"ok": True, "updates": updates, "delta": delta,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

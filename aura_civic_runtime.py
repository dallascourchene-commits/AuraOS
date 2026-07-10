"""
Aura Civic Runtime — orchestrates the full Civic Commons Arena pipeline.

human objective → IntentPacket → Capability Resolution → Civic profile set →
Civic session → ephemeral civic-organ manifests → minimum capability leases →
fixture/snapshot evidence → Civic World Model → community needs and offers →
MITOSIS → resource matching → MUSIC → legal/policy → map → Consent Arc →
What-If → Pilot Tunnel → Decision Packet → organ dissolution → governed memory.

Civic session lifecycle is distinct from ephemeral organ lifecycle.
Sessions use explicit human closure. Organs use short TTLs.
"""
from __future__ import annotations
import hashlib, json, time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

CIVIC_SESSION_STATES = (
    "CREATED","PROFILED","COLLECTING_INPUT","ANALYZING",
    "DELIBERATING","PILOT_PLANNING","DECISION_PACKET_READY",
    "PAUSED","CLOSED","ARCHIVED_GOVERNED",
)

# In-memory session store (would be SQLite for production)
_sessions: dict[str, dict[str, Any]] = {}


def create_civic_session(objective: str, *, fixture: bool = True) -> dict[str, Any]:
    """Create a new Civic Commons session from a plain-language objective."""
    from aura_civic_profiles import create_winnipeg_demo_profile_set
    session_id = f"CIVIC-{hashlib.blake2b(objective.encode(), digest_size=10).hexdigest()}"
    profile_set = create_winnipeg_demo_profile_set()
    session = {
        "session_id": session_id,
        "objective": objective,
        "objective_hash": hashlib.blake2b(objective.encode(), digest_size=12).hexdigest(),
        "state": "CREATED",
        "profile_set": profile_set.to_dict(),
        "created_at": time.time(),
        "contributions": [],
        "match_results": [],
        "workstreams": [],
        "scenarios": [],
        "legal_instruments": [],
        "council_items": [],
        "consent_arc": {},
        "what_if": {},
        "pilot": {},
        "decision_packet": {},
        "organ_receipts": [],
        "fixture_mode": fixture,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    _sessions[session_id] = session
    return {"ok": True, "session": session,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def get_session(session_id: str) -> dict[str, Any]:
    s = _sessions.get(session_id)
    if not s:
        return {"ok": False, "error": f"session not found: {session_id}"}
    return {"ok": True, "session": s,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def run_civic_organ(session_id: str, organ_type: str) -> dict[str, Any]:
    """Run a trusted civic organ within a session."""
    s = get_session(session_id)
    if not s["ok"]:
        return s
    session = s["session"]
    from aura_civic_organs import execute_organ
    result = execute_organ(organ_type, session)
    # Record receipt
    if result.get("ok"):
        session["organ_receipts"].append({
            "organ_type": organ_type,
            "executed_at": time.time(),
            "truth_class": result.get("organ_type", ""),
        })
    return result


def run_full_demo(*, story: str = "hairstylist") -> dict[str, Any]:
    """One-shot atomic demo command. Executes the full lifecycle."""
    from aura_civic_demo_fixtures import hairstylist_fixtures, youth_centre_fixtures

    if story == "hairstylist":
        fx = hairstylist_fixtures()
    elif story == "youth_centre":
        fx = youth_centre_fixtures()
    elif story == "council_pulse":
        from aura_civic_demo_fixtures import council_issue_fixtures
        fx = council_issue_fixtures()
    else:
        fx = hairstylist_fixtures()

    objective = fx.get("objective", "Civic demo")
    session_result = create_civic_session(objective, fixture=True)
    if not session_result["ok"]:
        return session_result
    session_id = session_result["session"]["session_id"]

    # Run all organs in sequence
    organ_sequence = [
        "CivicProfileOrgan", "CivicMapOrgan", "CommunityContributionOrgan",
        "CommunityResourceMatcherOrgan", "CivicMITOSISOrgan", "CivicMUSICOrgan",
        "CivicEvidenceOrgan", "ConsentArcOrgan", "WhatIfOrgan",
        "PilotTunnelOrgan", "DecisionPacketOrgan",
    ]
    results = {}
    for organ_type in organ_sequence:
        r = run_civic_organ(session_id, organ_type)
        results[organ_type] = {"ok": r.get("ok", False)}

    # Get final session
    final = get_session(session_id)
    session = final.get("session", {})

    return {
        "ok": True,
        "session_id": session_id,
        "story": story,
        "objective": objective,
        "organ_results": results,
        "decision_packet": session.get("decision_packet", {}),
        "organ_receipts": session.get("organ_receipts", []),
        "session_state": session.get("state", "CREATED"),
        "fixture_mode": True,
        "zero_raw_network_calls": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def add_contribution(session_id: str, contribution: dict[str, Any]) -> dict[str, Any]:
    s = get_session(session_id)
    if not s["ok"]:
        return s
    s["session"]["contributions"].append(contribution)
    return {"ok": True, "session_id": session_id,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def match_resources(session_id: str) -> dict[str, Any]:
    return run_civic_organ(session_id, "CommunityResourceMatcherOrgan")


def run_mitosis(session_id: str) -> dict[str, Any]:
    return run_civic_organ(session_id, "CivicMITOSISOrgan")


def run_scenarios(session_id: str) -> dict[str, Any]:
    return run_civic_organ(session_id, "CivicMUSICOrgan")


def get_consent(session_id: str) -> dict[str, Any]:
    return run_civic_organ(session_id, "ConsentArcOrgan")


def run_what_if(session_id: str, changes: dict[str, Any] | None = None) -> dict[str, Any]:
    return run_civic_organ(session_id, "WhatIfOrgan")


def create_pilot(session_id: str, scenario_id: str = "") -> dict[str, Any]:
    return run_civic_organ(session_id, "PilotTunnelOrgan")


def get_issue_pulse(session_id: str) -> dict[str, Any]:
    return run_civic_organ(session_id, "CouncilIssuePulseOrgan")


def export_packet(session_id: str) -> dict[str, Any]:
    s = get_session(session_id)
    if not s["ok"]:
        return s
    return run_civic_organ(session_id, "DecisionPacketOrgan")


def close_session(session_id: str) -> dict[str, Any]:
    s = get_session(session_id)
    if not s["ok"]:
        return s
    s["session"]["state"] = "CLOSED"
    return {"ok": True, "session_id": session_id, "state": "CLOSED",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def civic_status(session_id: str) -> dict[str, Any]:
    return get_session(session_id)

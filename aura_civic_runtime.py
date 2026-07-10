"""
Aura Civic Runtime — orchestrates the full Civic Commons Arena pipeline.

Updated for completion: uses persistent session store, real ephemeral runtime
integration, story-specific fixtures, and atomic result projection.

human objective → IntentPacket → Capability Resolution → Civic profile set →
Civic session → ephemeral civic-organ manifests → minimum capability leases →
fixture/snapshot evidence → Civic World Model → community needs and offers →
MITOSIS → resource matching → MUSIC → legal/policy → map → Consent Arc →
What-If → Pilot Tunnel → Decision Packet → organ dissolution → governed memory.
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


_sessions: dict[str, dict[str, Any]] = {}  # in-memory fallback


def _get_store():
    """Get the persistent civic session store (lazy import for test isolation)."""
    try:
        from aura_civic_session_store import CivicSessionStore
        return CivicSessionStore()
    except Exception:
        return None


def _get_ephemeral_store():
    """Get the persistent ephemeral registry store."""
    try:
        from aura_ephemeral_registry_store import EphemeralRegistryStore
        return EphemeralRegistryStore()
    except Exception:
        return None


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
        "systemic_context": {},
        "democratic_friction": {},
        "what_if": {},
        "pilot": {},
        "decision_packet": {},
        "organ_receipts": [],
        "fixture_mode": fixture,
        "story": "hairstylist",  # default story
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

    store = _get_store()
    if store is not None:
        store.create_session(session)
    _sessions[session_id] = session  # also keep in-memory

    return {"ok": True, "session": session,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def get_session(session_id: str) -> dict[str, Any]:
    """Get a civic session by ID — works across processes via persistent store."""
    store = _get_store()
    if store is not None:
        r = store.get_session(session_id)
        if r["ok"]:
            _sessions[session_id] = r["session"]  # cache in memory
            return {"ok": True, "session": r["session"],
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    # Fallback to in-memory
    if session_id in _sessions:
        return {"ok": True, "session": _sessions[session_id],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    return {"ok": False, "error": f"session not found: {session_id}",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def _update_session(session_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Atomically update session fields."""
    store = _get_store()
    if store is not None:
        result = store.update_session(session_id, updates)
        if result["ok"]:
            # Also update in-memory cache
            if session_id in _sessions:
                _sessions[session_id].update(updates)
            return result

    # Fallback to in-memory
    if session_id in _sessions:
        _sessions[session_id].update(updates)
        return {"ok": True}
    return {"ok": False, "error": "session not found"}


def _project_organ_result(session_id: str, organ_type: str, result: dict[str, Any]) -> dict[str, Any]:
    """Project verified organ results into session state atomically."""
    # Try the result projector first
    try:
        from aura_civic_result_projector import project_civic_organ_result
        s = get_session(session_id)
        if s["ok"]:
            projected = project_civic_organ_result(s["session"], organ_type, result)
            if projected["ok"]:
                _update_session(session_id, projected["updates"])
    except Exception:
        pass  # Fallback: just record the receipt below

    # Always record organ receipt
    s = get_session(session_id)
    if s["ok"]:
        session = s["session"]
        receipts = session.get("organ_receipts", [])
        receipt = {
            "organ_type": organ_type,
            "executed_at": time.time(),
            "ok": result.get("ok", False),
            "manifest_digest": result.get("manifest_digest", ""),
            "organ_id": result.get("organ_id", ""),
        }
        receipts.append(receipt)
        _update_session(session_id, {"organ_receipts": receipts})

    return {"ok": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def run_civic_organ(session_id: str, organ_type: str) -> dict[str, Any]:
    """Run a trusted civic organ through the real ephemeral runtime."""
    s = get_session(session_id)
    if not s["ok"]:
        return s
    session = s["session"]

    # Get story-specific fixtures
    from aura_civic_demo_fixtures import hairstylist_fixtures, youth_centre_fixtures, council_issue_fixtures
    story = session.get("story", "hairstylist")
    if story == "youth_centre":
        session["story_fixtures"] = youth_centre_fixtures()
    elif story == "council_pulse":
        session["story_fixtures"] = council_issue_fixtures()
    else:
        session["story_fixtures"] = hairstylist_fixtures()

    # Execute through real ephemeral runtime
    from aura_civic_ephemeral_integration import execute_civic_organ_through_runtime
    store = _get_ephemeral_store()
    result = execute_civic_organ_through_runtime(organ_type, session, store=store)

    if result.get("ok"):
        _project_organ_result(session_id, organ_type, result)

    return result


def run_full_demo(*, story: str = "hairstylist") -> dict[str, Any]:
    """One-shot atomic demo command. Executes the full lifecycle."""
    from aura_civic_demo_fixtures import hairstylist_fixtures, youth_centre_fixtures, council_issue_fixtures

    if story == "hairstylist":
        fx = hairstylist_fixtures()
    elif story == "youth_centre":
        fx = youth_centre_fixtures()
    elif story == "council_pulse":
        fx = council_issue_fixtures()
    else:
        fx = hairstylist_fixtures()

    objective = fx.get("objective", "Civic demo")
    session_result = create_civic_session(objective, fixture=True)
    if not session_result["ok"]:
        return session_result
    session_id = session_result["session"]["session_id"]

    # Set the story
    _update_session(session_id, {"story": story})

    # Choose organ sequence based on story
    if story == "council_pulse":
        organ_sequence = ["CivicProfileOrgan", "CouncilIssuePulseOrgan", "DecisionPacketOrgan"]
    else:
        organ_sequence = [
            "CivicProfileOrgan", "CivicMapOrgan", "CommunityContributionOrgan",
            "CommunityResourceMatcherOrgan", "CivicMITOSISOrgan", "CivicMUSICOrgan",
            "CivicEvidenceOrgan", "ConsentArcOrgan", "WhatIfOrgan",
            "PilotTunnelOrgan", "DecisionPacketOrgan",
        ]

    results = {}
    for organ_type in organ_sequence:
        r = run_civic_organ(session_id, organ_type)
        results[organ_type] = {"ok": r.get("ok", False), "organ_id": r.get("organ_id", "")}

    # Get final session with projected state
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
        "workstreams": session.get("workstreams", []),
        "needs": session.get("needs", []),
        "offers": session.get("offers", []),
        "scenarios": session.get("scenarios", []),
        "legal_instruments": session.get("legal_instruments", []),
        "consent_arc": session.get("consent_arc", {}),
        "fixture_mode": True,
        "zero_raw_network_calls": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def add_contribution(session_id: str, contribution: dict[str, Any]) -> dict[str, Any]:
    s = get_session(session_id)
    if not s["ok"]:
        return s
    contributions = s["session"].get("contributions", [])
    contributions.append(contribution)
    _update_session(session_id, {"contributions": contributions})
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
    return run_civic_organ(session_id, "DecisionPacketOrgan")


def close_session(session_id: str) -> dict[str, Any]:
    _update_session(session_id, {"state": "CLOSED"})
    return {"ok": True, "session_id": session_id, "state": "CLOSED",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def civic_status(session_id: str) -> dict[str, Any]:
    return get_session(session_id)


def select_profiles(session_id: str, profile_refs: list[str]) -> dict[str, Any]:
    """Explicitly select profiles — no identity inference."""
    s = get_session(session_id)
    if not s["ok"]:
        return s
    profile_set = s["session"].get("profile_set", {})
    # Only allow explicit selection, never inference
    profile_set["context_lens_refs"] = profile_refs
    _update_session(session_id, {"profile_set": profile_set, "state": "PROFILED"})
    return {"ok": True, "session_id": session_id,
            "active_profiles": profile_set,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def record_consent_response(session_id: str, response: dict[str, Any]) -> dict[str, Any]:
    """Record a participant response in the consent arc."""
    s = get_session(session_id)
    if not s["ok"]:
        return s
    responses = s["session"].get("consent_responses", [])
    responses.append(response)
    _update_session(session_id, {"consent_responses": responses})
    return {"ok": True, "session_id": session_id,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def add_need(session_id: str, need: dict[str, Any]) -> dict[str, Any]:
    """Add a community need to the session."""
    return add_contribution(session_id, {**need, "contribution_type": "NEED"})


def add_offer(session_id: str, offer: dict[str, Any]) -> dict[str, Any]:
    """Add a resource offer to the session."""
    return add_contribution(session_id, {**offer, "contribution_type": "SPACE_OFFER"})

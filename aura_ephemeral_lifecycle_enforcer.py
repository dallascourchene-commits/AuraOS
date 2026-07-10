"""
Aura Ephemeral Lifecycle Enforcer — route all state changes through transition table.

Ensures RUNNING is impossible unless:
  CAPABILITIES_RESOLVED → GRAMMAR_VALIDATED → POLICY_VALIDATED →
  MANIFEST_DIGESTED → SANDBOX_PREPARED → READY
"""
from __future__ import annotations

from typing import Any

from aura_ephemeral_lifecycle import (
    EphemeralState, TRANSITIONS, can_transition, transition as _transition,
)

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# Required pre-states for RUNNING
REQUIRED_BEFORE_RUNNING = [
    EphemeralState.CAPABILITIES_RESOLVED,
    EphemeralState.GRAMMAR_VALIDATED,
    EphemeralState.POLICY_VALIDATED,
    EphemeralState.MANIFEST_DIGESTED,
    EphemeralState.SANDBOX_PREPARED,
    EphemeralState.READY,
]


def check_can_run(current_state: str | EphemeralState) -> dict[str, Any]:
    """Check if an organ is in READY state and can transition to RUNNING."""
    state = EphemeralState(current_state) if isinstance(current_state, str) else current_state
    if state != EphemeralState.READY:
        return {"ok": False, "error": f"cannot_run_from_{state.value}: must be READY",
                "current_state": state.value,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return {"ok": True, "can_run": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def enforced_transition(
    store, organ_id: str, expected_from: str, to: str, *, evidence_ref: str = "",
) -> dict[str, Any]:
    """Route a state change through the lifecycle transition table with CAS."""
    from_str = expected_from
    to_str = to
    # Validate transition is legal
    from_state = EphemeralState(from_str)
    to_state = EphemeralState(to_str)
    if not can_transition(from_state, to_state):
        return {"ok": False, "error": f"illegal_transition: {from_str} -> {to_str}",
                "organ_id": organ_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    # Use compare-and-set from store
    result = store.transition_organ(organ_id, from_str, to_str, evidence_ref=evidence_ref)
    return result


def validate_transition_chain(states: list[str]) -> dict[str, Any]:
    """Validate that a list of states forms a legal transition chain."""
    for i in range(len(states) - 1):
        from_s = EphemeralState(states[i])
        to_s = EphemeralState(states[i + 1])
        if not can_transition(from_s, to_s):
            return {"ok": False, "error": f"illegal_transition: {states[i]} -> {states[i+1]}",
                    "index": i,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return {"ok": True, "chain_valid": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

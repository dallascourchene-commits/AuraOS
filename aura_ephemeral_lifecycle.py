"""
Aura Ephemeral Lifecycle — 16-state lifecycle machine for ephemeral organs.

States:
  DRAFTED, CAPABILITIES_RESOLVED, GRAMMAR_VALIDATED, POLICY_VALIDATED,
  MANIFEST_DIGESTED, SANDBOX_PREPARED, HUMAN_APPROVAL_REQUIRED, READY,
  RUNNING, VERIFYING, COMPLETED, DISSOLVING, DISSOLVED,
  BLOCKED, FAILED, CRYSTALLIZATION_PROPOSED

Rules:
  - Every transition is explicit.
  - No RUNNING without validated grammar, policy, lease, manifest digest, and sandbox.
  - TTL expiration transitions to DISSOLVING.
  - Failure transitions to DISSOLVING after evidence capture.
  - CRYSTALLIZATION_PROPOSED creates a review packet only.
  - No automatic promotion into a permanent plugin or organ.

Dependencies: stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class EphemeralState(str, Enum):
    DRAFTED = "DRAFTED"
    CAPABILITIES_RESOLVED = "CAPABILITIES_RESOLVED"
    GRAMMAR_VALIDATED = "GRAMMAR_VALIDATED"
    POLICY_VALIDATED = "POLICY_VALIDATED"
    MANIFEST_DIGESTED = "MANIFEST_DIGESTED"
    SANDBOX_PREPARED = "SANDBOX_PREPARED"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    READY = "READY"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    DISSOLVING = "DISSOLVING"
    DISSOLVED = "DISSOLVED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CRYSTALLIZATION_PROPOSED = "CRYSTALLIZATION_PROPOSED"


# Explicit transition table: state -> set of allowed next states
TRANSITIONS: dict[EphemeralState, set[EphemeralState]] = {
    EphemeralState.DRAFTED: {EphemeralState.CAPABILITIES_RESOLVED, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.CAPABILITIES_RESOLVED: {EphemeralState.GRAMMAR_VALIDATED, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.GRAMMAR_VALIDATED: {EphemeralState.POLICY_VALIDATED, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.POLICY_VALIDATED: {EphemeralState.MANIFEST_DIGESTED, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.MANIFEST_DIGESTED: {EphemeralState.SANDBOX_PREPARED, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.SANDBOX_PREPARED: {EphemeralState.HUMAN_APPROVAL_REQUIRED, EphemeralState.READY, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.HUMAN_APPROVAL_REQUIRED: {EphemeralState.READY, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.READY: {EphemeralState.RUNNING, EphemeralState.DISSOLVING, EphemeralState.BLOCKED, EphemeralState.FAILED},
    EphemeralState.RUNNING: {EphemeralState.VERIFYING, EphemeralState.DISSOLVING, EphemeralState.FAILED},
    EphemeralState.VERIFYING: {EphemeralState.COMPLETED, EphemeralState.FAILED, EphemeralState.DISSOLVING},
    EphemeralState.COMPLETED: {EphemeralState.DISSOLVING, EphemeralState.CRYSTALLIZATION_PROPOSED},
    EphemeralState.DISSOLVING: {EphemeralState.DISSOLVED, EphemeralState.FAILED},
    EphemeralState.DISSOLVED: set(),  # Terminal
    EphemeralState.BLOCKED: {EphemeralState.DISSOLVING, EphemeralState.DRAFTED},  # Can retry or dissolve
    EphemeralState.FAILED: {EphemeralState.DISSOLVING},
    EphemeralState.CRYSTALLIZATION_PROPOSED: {EphemeralState.DISSOLVING},  # Review only, then dissolve
}


@dataclass
class LifecycleStateInfo:
    state: EphemeralState
    allowed_actions: list[str]
    blocked_actions: list[str]
    required_evidence: list[str]
    human_approval_required: bool
    next_actions: list[str]


STATE_INFO: dict[EphemeralState, LifecycleStateInfo] = {
    EphemeralState.DRAFTED: LifecycleStateInfo(
        state=EphemeralState.DRAFTED,
        allowed_actions=["create_manifest", "set_objective", "set_ttl"],
        blocked_actions=["run", "execute", "verify", "dissolve"],
        required_evidence=["objective", "organ_id"],
        human_approval_required=False,
        next_actions=["resolve_capabilities"],
    ),
    EphemeralState.CAPABILITIES_RESOLVED: LifecycleStateInfo(
        state=EphemeralState.CAPABILITIES_RESOLVED,
        allowed_actions=["validate_grammar", "list_capabilities"],
        blocked_actions=["run", "execute", "dissolve"],
        required_evidence=["capability_resolution_packet"],
        human_approval_required=False,
        next_actions=["validate_grammar"],
    ),
    EphemeralState.GRAMMAR_VALIDATED: LifecycleStateInfo(
        state=EphemeralState.GRAMMAR_VALIDATED,
        allowed_actions=["validate_policy", "show_route"],
        blocked_actions=["run", "execute"],
        required_evidence=["lexc_route", "machine_route"],
        human_approval_required=False,
        next_actions=["validate_policy"],
    ),
    EphemeralState.POLICY_VALIDATED: LifecycleStateInfo(
        state=EphemeralState.POLICY_VALIDATED,
        allowed_actions=["digest_manifest"],
        blocked_actions=["run", "execute"],
        required_evidence=["policy_check_result"],
        human_approval_required=False,
        next_actions=["digest_manifest"],
    ),
    EphemeralState.MANIFEST_DIGESTED: LifecycleStateInfo(
        state=EphemeralState.MANIFEST_DIGESTED,
        allowed_actions=["prepare_sandbox"],
        blocked_actions=["run", "execute"],
        required_evidence=["manifest_digest"],
        human_approval_required=False,
        next_actions=["prepare_sandbox"],
    ),
    EphemeralState.SANDBOX_PREPARED: LifecycleStateInfo(
        state=EphemeralState.SANDBOX_PREPARED,
        allowed_actions=["request_human_approval", "proceed_if_not_required"],
        blocked_actions=["run"],
        required_evidence=["sandbox_receipt"],
        human_approval_required=True,
        next_actions=["request_human_approval"],
    ),
    EphemeralState.HUMAN_APPROVAL_REQUIRED: LifecycleStateInfo(
        state=EphemeralState.HUMAN_APPROVAL_REQUIRED,
        allowed_actions=["approve", "deny"],
        blocked_actions=["run", "execute"],
        required_evidence=["human_approval_record"],
        human_approval_required=True,
        next_actions=["approve_to_ready", "deny_to_dissolve"],
    ),
    EphemeralState.READY: LifecycleStateInfo(
        state=EphemeralState.READY,
        allowed_actions=["run", "dissolve"],
        blocked_actions=["modify_manifest"],
        required_evidence=["all_checks_passed"],
        human_approval_required=False,
        next_actions=["run"],
    ),
    EphemeralState.RUNNING: LifecycleStateInfo(
        state=EphemeralState.RUNNING,
        allowed_actions=["query", "read_slice", "resolve_capabilities", "render_schema", "emit_telemetry"],
        blocked_actions=["modify_manifest", "create_new_organ"],
        required_evidence=["execution_log"],
        human_approval_required=False,
        next_actions=["verify"],
    ),
    EphemeralState.VERIFYING: LifecycleStateInfo(
        state=EphemeralState.VERIFYING,
        allowed_actions=["run_verifier", "check_results"],
        blocked_actions=["run_new_actions"],
        required_evidence=["verifier_result"],
        human_approval_required=False,
        next_actions=["complete", "fail"],
    ),
    EphemeralState.COMPLETED: LifecycleStateInfo(
        state=EphemeralState.COMPLETED,
        allowed_actions=["dissolve", "propose_crystallization", "export_audit"],
        blocked_actions=["run", "execute_new"],
        required_evidence=["completion_record"],
        human_approval_required=True,
        next_actions=["dissolve"],
    ),
    EphemeralState.DISSOLVING: LifecycleStateInfo(
        state=EphemeralState.DISSOLVING,
        allowed_actions=["revoke_capabilities", "remove_temp_dir", "write_receipt"],
        blocked_actions=["run", "execute", "create_new"],
        required_evidence=["dissolution_evidence"],
        human_approval_required=False,
        next_actions=["confirm_dissolved"],
    ),
    EphemeralState.DISSOLVED: LifecycleStateInfo(
        state=EphemeralState.DISSOLVED,
        allowed_actions=["view_receipt", "export_audit"],
        blocked_actions=["run", "execute", "modify", "create"],
        required_evidence=["dissolution_receipt"],
        human_approval_required=False,
        next_actions=[],
    ),
    EphemeralState.BLOCKED: LifecycleStateInfo(
        state=EphemeralState.BLOCKED,
        allowed_actions=["retry", "dissolve", "view_blocking_reasons"],
        blocked_actions=["run", "execute"],
        required_evidence=["blocking_reasons"],
        human_approval_required=False,
        next_actions=["retry_from_drafted", "dissolve"],
    ),
    EphemeralState.FAILED: LifecycleStateInfo(
        state=EphemeralState.FAILED,
        allowed_actions=["capture_evidence", "dissolve"],
        blocked_actions=["run", "execute", "retry_without_changes"],
        required_evidence=["failure_record"],
        human_approval_required=False,
        next_actions=["dissolve"],
    ),
    EphemeralState.CRYSTALLIZATION_PROPOSED: LifecycleStateInfo(
        state=EphemeralState.CRYSTALLIZATION_PROPOSED,
        allowed_actions=["view_proposal", "dissolve"],
        blocked_actions=["promote_automatically", "install_plugin"],
        required_evidence=["crystallization_proposal"],
        human_approval_required=True,
        next_actions=["dissolve"],
    ),
}


def can_transition(from_state: EphemeralState, to_state: EphemeralState) -> bool:
    """Check if a transition is allowed."""
    return to_state in TRANSITIONS.get(from_state, set())


def transition(from_state: EphemeralState, to_state: EphemeralState) -> dict[str, Any]:
    """Attempt a lifecycle transition. Returns {ok, from, to, reason}."""
    if can_transition(from_state, to_state):
        return {"ok": True, "from": from_state.value, "to": to_state.value,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return {"ok": False, "from": from_state.value, "to": to_state.value,
            "reason": f"illegal_transition: {from_state.value} -> {to_state.value}",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def get_state_info(state: EphemeralState) -> dict[str, Any]:
    """Get state information including allowed/blocked actions."""
    info = STATE_INFO.get(state)
    if not info:
        return {"ok": False, "error": f"unknown_state: {state}"}
    return {
        "ok": True, "state": state.value,
        "allowed_actions": info.allowed_actions,
        "blocked_actions": info.blocked_actions,
        "required_evidence": info.required_evidence,
        "human_approval_required": info.human_approval_required,
        "next_actions": info.next_actions,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def lifecycle_state_machine() -> dict[str, Any]:
    """Return the full lifecycle state machine."""
    return {
        "ok": True,
        "states": [s.value for s in EphemeralState],
        "state_count": len(EphemeralState),
        "transitions": {s.value: [t.value for t in targets] for s, targets in TRANSITIONS.items()},
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def check_ttl_expired(expires_at: float, now: float | None = None) -> bool:
    """Check if the TTL has expired."""
    import time
    current = now if now is not None else time.time()
    return current >= expires_at

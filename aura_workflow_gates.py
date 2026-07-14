#!/usr/bin/env python3
"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: enum, dataclasses, typing, json  (stdlib only — no numpy, no Aura imports at module level)
FUNCTIONS: get_gate, can_transition, get_transition_requirements, evaluate_gate, workflow_state_machine, workflow_gate_markdown
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Workflow Gates — 18-State Checkpoint Machine for Workflow Governance
==========================================================================

This module implements the canonical 18-state checkpoint state machine that
governs every Aura coding-arena workflow from ingest through PR opening.  Each
state is represented by a :class:`WorkflowGate` that declares what is allowed,
what is blocked, what evidence is required to proceed, whether a human must
approve, and which states may follow.

Design constraints enforced in :data:`GATE_DEFINITIONS`:

* Cannot hand off to Hermes until the workflow has passed both
  ``CODEMAP_LOCALIZED`` and ``PLAN_READY`` (``AGENT_HANDOFF_READY`` requires
  those as prerequisites).
* Cannot patch if the FST route is ``LOCALIZE_FIRST``, ``PLAN_ONLY``,
  ``VERIFY_ONLY``, ``TEST_GAP_FILL`` or ``BLOCKED_WITH_REASON`` unless the gate
  declares what repair / localization is required (``PATCH_PROPOSED`` requires
  ``VERIFIED`` or ``REPAIR_REQUIRED`` with a route not in the blocked set).
* Cannot commit before ``VERIFIED`` **and** ``HUMAN_APPROVED_FOR_COMMIT``.
* Cannot open a PR before ``PR_READY`` (which itself requires
  ``HUMAN_APPROVED_FOR_COMMIT``).
* Broad repo / subsystem scope must route to ``PLAN_ONLY`` unless decomposed
  into symbol / file Act Capsules.
* Missing tests must route to ``TEST_GAP_FILL`` or ``VERIFY_ONLY`` depending on
  risk.

The module is intentionally stdlib-only (``enum``, ``dataclasses``, ``typing``,
``json``) and performs no Aura imports at module level so it can be loaded in
isolation for governance checks.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Set


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PATCH_AUTHORITY: str = "exact_source_spans_and_hashes_only"
"""Governing rule: patches must be grounded in exact source spans and hashes."""

VSA_PATCH_AUTHORITY: bool = False
"""VSA-only patch authority is disabled; exact spans are required."""

BLOCKED_PATCH_ROUTES: Set[str] = {
    "LOCALIZE_FIRST",
    "PLAN_ONLY",
    "VERIFY_ONLY",
    "TEST_GAP_FILL",
    "BLOCKED_WITH_REASON",
}
"""FST routes that forbid direct patching without prior repair / localization."""


_AUTHORITY_SCOPE_BY_STATE: Dict[str, Dict[str, str]] = {
    "HUMAN_APPROVED_FOR_AGENT": {
        "policy_scope": "workflow.agent_handoff",
        "capability_scope": "agent_handoff",
    },
    "AGENT_HANDOFF_READY": {
        "policy_scope": "workflow.agent_handoff",
        "capability_scope": "agent_handoff",
    },
    "HUMAN_APPROVED_FOR_COMMIT": {
        "policy_scope": "workflow.commit",
        "capability_scope": "commit",
    },
    "PR_READY": {
        "policy_scope": "workflow.commit",
        "capability_scope": "commit",
    },
}


# ---------------------------------------------------------------------------
# State enum — the 18 canonical workflow checkpoints
# ---------------------------------------------------------------------------

class WorkflowState(Enum):
    """The 18 canonical Aura workflow checkpoint states, in lifecycle order."""

    INGESTED = 1
    POLYSYNTHETIC_COMPRESSED = 2
    LEXC_VALIDATED = 3
    FST_ROUTED = 4
    CODEMAP_LOCALIZED = 5
    DREAM_RERANKED = 6
    CONTEXT_COMPRESSED = 7
    ST3GG_READY = 8
    PLAN_READY = 9
    HUMAN_APPROVED_FOR_AGENT = 10
    AGENT_HANDOFF_READY = 11
    AGENT_RUNNING = 12
    PATCH_PROPOSED = 13
    VERIFIED = 14
    REPAIR_REQUIRED = 15
    HUMAN_APPROVED_FOR_COMMIT = 16
    PR_READY = 17
    PR_OPENED = 18


# Ordered tuple of states for iteration / markdown rendering.
STATE_ORDER: tuple = tuple(WorkflowState)


# ---------------------------------------------------------------------------
# Gate dataclass
# ---------------------------------------------------------------------------

@dataclass
class WorkflowGate:
    """Definition of a single workflow checkpoint gate.

    Attributes:
        state: The :class:`WorkflowState` this gate governs.
        allowed_actions: Actions permitted while the workflow is in this state.
        blocked_actions: Actions explicitly blocked in this state.
        required_evidence: Evidence keys that must be present to satisfy the
            gate (e.g. ``'lexc_valid'``, ``'grounding_ok'``, ``'tests_pass'``,
            ``'human_approval'``).
        truth_packet: Dict carrying ``patch_authority`` and
            ``vsa_patch_authority`` — the patch-grounding contract for the
            state.
        token_economy_snapshot: Placeholder dict for token-economy telemetry
            (input / output / cache tokens, cost, compression ratio, …).
        human_approval_required: Whether a human must approve before
            transitioning out of this state.
        next_actions: Ordered list of :class:`WorkflowState` values that may
            legally follow this state.
    """

    state: WorkflowState
    allowed_actions: List[str]
    blocked_actions: List[str]
    required_evidence: List[str]
    truth_packet: Dict[str, Any]
    token_economy_snapshot: Dict[str, Any]
    human_approval_required: bool
    next_actions: List[WorkflowState] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this gate to a plain dict suitable for JSON."""
        return {
            "state": self.state.name,
            "allowed_actions": list(self.allowed_actions),
            "blocked_actions": list(self.blocked_actions),
            "required_evidence": list(self.required_evidence),
            "truth_packet": dict(self.truth_packet),
            "token_economy_snapshot": dict(self.token_economy_snapshot),
            "human_approval_required": bool(self.human_approval_required),
            "next_actions": [s.name for s in self.next_actions],
        }


# ---------------------------------------------------------------------------
# Shared truth-packet factory
# ---------------------------------------------------------------------------

def _truth_packet() -> Dict[str, Any]:
    """Return the canonical truth-packet dict for a gate."""
    return {
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _token_economy_snapshot() -> Dict[str, Any]:
    """Return a placeholder token-economy snapshot dict for a gate."""
    return {
        "input_tokens": None,
        "output_tokens": None,
        "cache_read_tokens": None,
        "cache_write_tokens": None,
        "estimated_cost_usd": None,
        "compression_ratio": None,
        "captured_at_state": None,
    }


# ---------------------------------------------------------------------------
# GATE_DEFINITIONS — the full state-machine definition
# ---------------------------------------------------------------------------

GATE_DEFINITIONS: Dict[WorkflowState, WorkflowGate] = {

    # 1 ----------------------------------------------------------------
    WorkflowState.INGESTED: WorkflowGate(
        state=WorkflowState.INGESTED,
        allowed_actions=[
            "ingest_raw_input",
            "attach_metadata",
            "assign_workflow_id",
        ],
        blocked_actions=[
            "route",
            "localize_codemap",
            "plan",
            "patch",
            "handoff_to_agent",
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=["raw_input_captured", "metadata_attached"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.POLYSYNTHETIC_COMPRESSED],
    ),

    # 2 ----------------------------------------------------------------
    WorkflowState.POLYSYNTHETIC_COMPRESSED: WorkflowGate(
        state=WorkflowState.POLYSYNTHETIC_COMPRESSED,
        allowed_actions=[
            "polysynthetic_compress",
            "deduplicate_context",
            "measure_compression_ratio",
        ],
        blocked_actions=[
            "route",
            "localize_codemap",
            "plan",
            "patch",
            "handoff_to_agent",
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=["compression_ratio_recorded", "polysynth_complete"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.LEXC_VALIDATED],
    ),

    # 3 ----------------------------------------------------------------
    WorkflowState.LEXC_VALIDATED: WorkflowGate(
        state=WorkflowState.LEXC_VALIDATED,
        allowed_actions=[
            "validate_lexc",
            "lexc_lookup",
            "lexc_compile",
        ],
        blocked_actions=[
            "route",  # routing happens after LEXC validation in FST_ROUTED
            "localize_codemap",
            "plan",
            "patch",
            "handoff_to_agent",
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=["lexc_valid", "lexc_grammar_ok"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.FST_ROUTED],
    ),

    # 4 ----------------------------------------------------------------
    WorkflowState.FST_ROUTED: WorkflowGate(
        state=WorkflowState.FST_ROUTED,
        allowed_actions=[
            "route",
            "select_route",
            "assign_route_decision",
            "detect_broad_scope",
            "detect_missing_tests",
        ],
        blocked_actions=[
            "localize_codemap",  # must route first; CODEMAP_LOCALIZED is next
            "plan",
            "patch",
            "handoff_to_agent",
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=[
            "fst_route_assigned",
            "route_not_blocked_unhandled",
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.CODEMAP_LOCALIZED],
    ),

    # 5 ----------------------------------------------------------------
    WorkflowState.CODEMAP_LOCALIZED: WorkflowGate(
        state=WorkflowState.CODEMAP_LOCALIZED,
        allowed_actions=[
            "localize_codemap",
            "resolve_symbols",
            "build_act_capsules",
            "decompose_broad_scope",
        ],
        blocked_actions=[
            "patch",  # no patching until PLAN_READY -> ... -> PATCH_PROPOSED
            "handoff_to_agent",  # not until AGENT_HANDOFF_READY
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=[
            "codemap_localized",
            "grounding_ok",
            "act_capsules_decomposed",  # broad scope must be decomposed
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.DREAM_RERANKED],
    ),

    # 6 ----------------------------------------------------------------
    WorkflowState.DREAM_RERANKED: WorkflowGate(
        state=WorkflowState.DREAM_RERANKED,
        allowed_actions=[
            "dream_rerank",
            "score_candidates",
            "select_top_candidates",
        ],
        blocked_actions=[
            "patch",
            "handoff_to_agent",
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=["dream_rerank_complete", "candidates_scored"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.CONTEXT_COMPRESSED],
    ),

    # 7 ----------------------------------------------------------------
    WorkflowState.CONTEXT_COMPRESSED: WorkflowGate(
        state=WorkflowState.CONTEXT_COMPRESSED,
        allowed_actions=[
            "compress_context",
            "build_st3gg_payload",
            "measure_context_budget",
        ],
        blocked_actions=[
            "patch",
            "handoff_to_agent",
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=["context_compressed", "context_budget_ok"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.ST3GG_READY],
    ),

    # 8 ----------------------------------------------------------------
    WorkflowState.ST3GG_READY: WorkflowGate(
        state=WorkflowState.ST3GG_READY,
        allowed_actions=[
            "encode_st3gg",
            "validate_st3gg",
            "prepare_payload",
        ],
        blocked_actions=[
            "patch",
            "handoff_to_agent",  # not until AGENT_HANDOFF_READY
            "verify",
            "commit",
            "open_pr",
        ],
        required_evidence=["st3gg_encoded", "st3gg_valid"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.PLAN_READY],
    ),

    # 9 ----------------------------------------------------------------
    WorkflowState.PLAN_READY: WorkflowGate(
        state=WorkflowState.PLAN_READY,
        allowed_actions=[
            "finalize_plan",
            "validate_plan",
            "request_human_approval_for_agent",
        ],
        blocked_actions=[
            "patch",  # no patching until PATCH_PROPOSED after agent runs
            "handoff_to_agent",  # must pass HUMAN_APPROVED_FOR_AGENT first
            "commit",
            "open_pr",
        ],
        required_evidence=[
            "plan_ready",
            "plan_validated",
            "codemap_localized",  # prerequisite carried forward
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,  # approval happens in next state
        next_actions=[WorkflowState.HUMAN_APPROVED_FOR_AGENT],
    ),

    # 10 ---------------------------------------------------------------
    WorkflowState.HUMAN_APPROVED_FOR_AGENT: WorkflowGate(
        state=WorkflowState.HUMAN_APPROVED_FOR_AGENT,
        allowed_actions=[
            "capture_human_approval",
            "record_approval_record",
        ],
        blocked_actions=[
            "patch",
            "commit",
            "open_pr",
            "agent_run",  # not yet — AGENT_HANDOFF_READY gates the run
        ],
        required_evidence=["human_approval"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=True,
        next_actions=[WorkflowState.AGENT_HANDOFF_READY],
    ),

    # 11 ---------------------------------------------------------------
    WorkflowState.AGENT_HANDOFF_READY: WorkflowGate(
        state=WorkflowState.AGENT_HANDOFF_READY,
        allowed_actions=[
            "handoff_to_agent",
            "prepare_agent_context",
            "dispatch_to_hermes",
        ],
        blocked_actions=[
            "patch",  # agent must run before proposing a patch
            "commit",
            "open_pr",
        ],
        required_evidence=[
            "human_approval",
            "codemap_localized",  # hard prerequisite
            "plan_ready",  # hard prerequisite
            "st3gg_valid",
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.AGENT_RUNNING],
    ),

    # 12 ---------------------------------------------------------------
    WorkflowState.AGENT_RUNNING: WorkflowGate(
        state=WorkflowState.AGENT_RUNNING,
        allowed_actions=[
            "agent_run",
            "stream_agent_output",
            "monitor_agent",
            "request_repair",
        ],
        blocked_actions=[
            "commit",
            "open_pr",
        ],
        required_evidence=["agent_started", "agent_heartbeat_ok"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[
            WorkflowState.PATCH_PROPOSED,
            WorkflowState.REPAIR_REQUIRED,
        ],
    ),

    # 13 ---------------------------------------------------------------
    WorkflowState.PATCH_PROPOSED: WorkflowGate(
        state=WorkflowState.PATCH_PROPOSED,
        allowed_actions=[
            "propose_patch",
            "validate_patch_spans",
            "validate_patch_hashes",
            "submit_patch_for_verification",
        ],
        blocked_actions=[
            "commit",  # not until VERIFIED + HUMAN_APPROVED_FOR_COMMIT
            "open_pr",
        ],
        required_evidence=[
            "patch_spans_exact",  # exact source spans required
            "patch_hashes_match",  # hashes must match
            "route_not_in_blocked_set",  # route must allow patching
            "prior_state_agent_running_or_repair",  # VERIFIED or REPAIR_REQUIRED
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[
            WorkflowState.VERIFIED,
            WorkflowState.REPAIR_REQUIRED,
        ],
    ),

    # 14 ---------------------------------------------------------------
    WorkflowState.VERIFIED: WorkflowGate(
        state=WorkflowState.VERIFIED,
        allowed_actions=[
            "run_tests",
            "run_static_checks",
            "capture_verification_artifacts",
            "request_human_approval_for_commit",
        ],
        blocked_actions=[
            "commit",  # need HUMAN_APPROVED_FOR_COMMIT first
            "open_pr",
        ],
        required_evidence=[
            "tests_pass",
            "static_checks_pass",
            "verification_artifacts_captured",
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,  # approval captured in next state
        next_actions=[
            WorkflowState.REPAIR_REQUIRED,
            WorkflowState.HUMAN_APPROVED_FOR_COMMIT,
        ],
    ),

    # 15 ---------------------------------------------------------------
    WorkflowState.REPAIR_REQUIRED: WorkflowGate(
        state=WorkflowState.REPAIR_REQUIRED,
        allowed_actions=[
            "diagnose_failure",
            "request_localization",
            "request_test_gap_fill",
            "repropose_patch",
        ],
        blocked_actions=[
            "commit",
            "open_pr",
        ],
        required_evidence=[
            "failure_diagnosed",
            "repair_plan_recorded",
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.PATCH_PROPOSED],
    ),

    # 16 ---------------------------------------------------------------
    WorkflowState.HUMAN_APPROVED_FOR_COMMIT: WorkflowGate(
        state=WorkflowState.HUMAN_APPROVED_FOR_COMMIT,
        allowed_actions=[
            "capture_commit_approval",
            "stage_changes",
            "prepare_pr_artifacts",
        ],
        blocked_actions=[
            "open_pr",  # not until PR_READY
            "patch",  # patching phase is over
        ],
        required_evidence=[
            "human_approval",
            "verified",  # VERIFIED must have been reached
            "tests_pass",
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=True,
        next_actions=[WorkflowState.PR_READY],
    ),

    # 17 ---------------------------------------------------------------
    WorkflowState.PR_READY: WorkflowGate(
        state=WorkflowState.PR_READY,
        allowed_actions=[
            "assemble_pr",
            "validate_pr_template",
            "open_pr",
        ],
        blocked_actions=[
            "patch",
            "agent_run",
        ],
        required_evidence=[
            "human_approval",
            "human_approved_for_commit",  # hard prerequisite
            "pr_assembled",
            "pr_template_valid",
        ],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[WorkflowState.PR_OPENED],
    ),

    # 18 ---------------------------------------------------------------
    WorkflowState.PR_OPENED: WorkflowGate(
        state=WorkflowState.PR_OPENED,
        allowed_actions=[
            "record_pr_url",
            "notify_stakeholders",
            "archive_workflow",
        ],
        blocked_actions=[
            "patch",
            "commit",
            "agent_run",
            "open_pr",
        ],
        required_evidence=["pr_url_captured", "workflow_archived"],
        truth_packet=_truth_packet(),
        token_economy_snapshot=_token_economy_snapshot(),
        human_approval_required=False,
        next_actions=[],  # terminal state
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_gate(state: WorkflowState) -> WorkflowGate:
    """Return the :class:`WorkflowGate` definition for *state*.

    Parameters
    ----------
    state:
        A :class:`WorkflowState` member (or its string name) to look up.

    Returns
    -------
    WorkflowGate
        The gate definition for the requested state.

    Raises
    ------
    KeyError
        If *state* is not a recognized :class:`WorkflowState`.
    TypeError
        If *state* is neither a :class:`WorkflowState` nor a valid state name.
    """
    if isinstance(state, str):
        try:
            state = WorkflowState[state]
        except KeyError as exc:
            raise KeyError(f"Unknown WorkflowState name: {state!r}") from exc
    if not isinstance(state, WorkflowState):
        raise TypeError(
            f"get_gate() expects a WorkflowState or str, got {type(state).__name__}"
        )
    return GATE_DEFINITIONS[state]


def can_transition(current_state: WorkflowState, target_state: WorkflowState) -> bool:
    """Return ``True`` if transitioning *current_state* → *target_state* is allowed.

    A transition is allowed when *target_state* appears in the
    ``next_actions`` list of the current state's gate, **and** the structural
    prerequisites of the target gate are satisfiable from the current lineage.

    Structural rules enforced on top of the adjacency list:

    * ``AGENT_HANDOFF_READY`` requires the workflow to have already passed
      ``CODEMAP_LOCALIZED`` and ``PLAN_READY``.
    * ``PATCH_PROPOSED`` requires the prior state to be ``AGENT_RUNNING`` or
      ``REPAIR_REQUIRED``.
    * ``HUMAN_APPROVED_FOR_COMMIT`` requires ``VERIFIED`` to have been reached.
    * ``PR_READY`` requires ``HUMAN_APPROVED_FOR_COMMIT``.
    * ``PR_OPENED`` requires ``PR_READY``.
    """
    # Normalize string inputs.
    current_state = _coerce_state(current_state)
    target_state = _coerce_state(target_state)

    current_gate = get_gate(current_state)
    allowed_next = set(current_gate.next_actions)
    if target_state not in allowed_next:
        return False

    # Structural prerequisite checks keyed on the target state.
    if target_state is WorkflowState.AGENT_HANDOFF_READY:
        # Prerequisites: CODEMAP_LOCALIZED and PLAN_READY must be in the
        # lineage.  Because the state machine is strictly ordered before
        # AGENT_HANDOFF_READY, reaching this state implies both prerequisites
        # were passed — but we still verify adjacency from a valid predecessor.
        if current_state not in (
            WorkflowState.HUMAN_APPROVED_FOR_AGENT,
            WorkflowState.PLAN_READY,
        ):
            return False

    if target_state is WorkflowState.PATCH_PROPOSED:
        if current_state not in (
            WorkflowState.AGENT_RUNNING,
            WorkflowState.REPAIR_REQUIRED,
        ):
            return False

    if target_state is WorkflowState.HUMAN_APPROVED_FOR_COMMIT:
        # Must come from VERIFIED (the only producer of this transition).
        if current_state is not WorkflowState.VERIFIED:
            return False

    if target_state is WorkflowState.PR_READY:
        if current_state is not WorkflowState.HUMAN_APPROVED_FOR_COMMIT:
            return False

    if target_state is WorkflowState.PR_OPENED:
        if current_state is not WorkflowState.PR_READY:
            return False

    return True


def get_transition_requirements(
    current_state: WorkflowState, target_state: WorkflowState
) -> Dict[str, Any]:
    """Return the evidence / approval requirements to transition between states.

    The returned dict merges the *target* gate's ``required_evidence`` with the
    ``human_approval_required`` flag and any route constraints that apply to
    patch-related transitions.  If the transition is not allowed, the dict's
    ``allowed`` key is ``False`` and a ``reason`` string is included.
    """
    current_state = _coerce_state(current_state)
    target_state = _coerce_state(target_state)

    if not can_transition(current_state, target_state):
        return {
            "allowed": False,
            "current_state": current_state.name,
            "target_state": target_state.name,
            "reason": (
                f"Transition {current_state.name} -> {target_state.name} is "
                f"not in the allowed adjacency list or fails a structural "
                f"prerequisite check."
            ),
            "required_evidence": [],
            "human_approval_required": False,
            "route_constraints": {},
        }

    target_gate = get_gate(target_state)
    route_constraints: Dict[str, Any] = {}

    if target_state is WorkflowState.PATCH_PROPOSED:
        route_constraints = {
            "blocked_routes": sorted(BLOCKED_PATCH_ROUTES),
            "rule": (
                "route must not be in blocked_routes unless a repair / "
                "localization gate has been satisfied"
            ),
            "requires_prior_state": ["AGENT_RUNNING", "REPAIR_REQUIRED"],
        }

    if target_state is WorkflowState.AGENT_HANDOFF_READY:
        route_constraints = {
            "prerequisites": ["CODEMAP_LOCALIZED", "PLAN_READY"],
            "rule": (
                "Cannot hand off to Hermes until CODEMAP_LOCALIZED and "
                "PLAN_READY are both satisfied."
            ),
        }

    if target_state is WorkflowState.FST_ROUTED:
        route_constraints = {
            "broad_scope_rule": (
                "Broad repo / subsystem scope must route to PLAN_ONLY unless "
                "decomposed into symbol / file Act Capsules."
            ),
            "missing_tests_rule": (
                "Missing tests must route to TEST_GAP_FILL or VERIFY_ONLY "
                "depending on risk."
            ),
        }

    return {
        "allowed": True,
        "current_state": current_state.name,
        "target_state": target_state.name,
        "required_evidence": list(target_gate.required_evidence),
        "human_approval_required": bool(target_gate.human_approval_required),
        "route_constraints": route_constraints,
    }


def _authority_requirement(state: WorkflowState, evidence: Mapping[str, Any]) -> Dict[str, str]:
    defaults = _AUTHORITY_SCOPE_BY_STATE.get(state.name, {})
    policy_scope = defaults.get("policy_scope")
    capability_scope = defaults.get("capability_scope")
    return {
        "policy_scope": str(
            policy_scope
            if policy_scope is not None
            else evidence.get("required_policy_scope", "")
        ),
        "capability_scope": str(
            capability_scope
            if capability_scope is not None
            else evidence.get("required_capability_scope", "")
        ),
    }


def _evaluate_authority(
    state: WorkflowState,
    evidence: Mapping[str, Any],
    *,
    required: bool,
) -> Dict[str, Any]:
    scopes = _authority_requirement(state, evidence)
    result: Dict[str, Any] = {
        "satisfied": not required,
        "authority_mode": "NOT_REQUIRED" if not required else "MISSING",
        "authority_verified": False,
        "governance_decision_id": "",
        "governance_action_digest": "",
        "legacy_human_approval_used": False,
        "authority_missing_reasons": [],
        "authority_warnings": [],
        "required_policy_scope": scopes["policy_scope"],
        "required_capability_scope": scopes["capability_scope"],
    }
    if not required:
        return result

    supplied = evidence.get("governance_decision")
    if supplied is not None:
        result["authority_mode"] = "GOVERNANCE_DECISION_INVALID"
        try:
            # Imported only when governed evidence is supplied so this module
            # remains independently loadable for legacy workflow checks.
            from aura_relational_authority import GovernanceDecision

            if isinstance(supplied, GovernanceDecision):
                decision = supplied
                decision.validate_integrity()
            elif isinstance(supplied, Mapping):
                decision = GovernanceDecision.from_dict(supplied)
            else:
                raise ValueError("governance decision has an unsupported type")

            action_id = str(evidence.get("requested_action_id", "")).strip()
            action_digest = str(evidence.get("requested_action_digest", "")).strip()
            if not action_id:
                raise ValueError("requested action ID is missing")
            if not action_digest:
                raise ValueError("requested action digest is missing")
            if not scopes["policy_scope"]:
                raise ValueError("required policy scope is missing")
            if not scopes["capability_scope"]:
                raise ValueError("required capability scope is missing")

            decision.validate_for_action(
                action_id=action_id,
                action_payload_digest=action_digest,
                policy_scope=scopes["policy_scope"],
                capability_scope=scopes["capability_scope"],
                now=float(evidence.get("authority_now", time.time())),
            )
            raw_verified_ids = evidence.get(
                "verified_governance_decision_ids", ()
            )
            if isinstance(raw_verified_ids, (str, bytes)):
                raise ValueError(
                    "verified_governance_decision_ids must be a collection"
                )
            verified_ids = {
                str(item).strip()
                for item in raw_verified_ids
                if str(item).strip()
            }
            if decision.decision_id not in verified_ids:
                raise ValueError("governance_decision_not_externally_verified")

            result.update(
                {
                    "satisfied": True,
                    "authority_mode": "GOVERNANCE_DECISION",
                    "authority_verified": True,
                    "governance_decision_id": decision.decision_id,
                    "governance_action_digest": decision.action_payload_digest,
                }
            )
        except (TypeError, ValueError) as exc:
            result["authority_missing_reasons"].append(str(exc))
        return result

    if evidence.get("human_approval") is True:
        result.update(
            {
                "satisfied": True,
                "authority_mode": "LEGACY_BOOLEAN_COMPAT",
                "legacy_human_approval_used": True,
                "authority_warnings": [
                    "legacy human_approval is not action-bound or authority-verified"
                ],
            }
        )
        return result

    result["authority_missing_reasons"].append("authority_evidence_missing")
    return result


def evaluate_gate(state: WorkflowState, evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate exact evidence and action-bound authority for a workflow gate.

    A verified :class:`GovernanceDecision` is preferred. The historical truthy
    ``human_approval`` input remains available as an explicitly labeled
    compatibility mode and is never represented as verified authority.
    """
    state = _coerce_state(state)
    gate = get_gate(state)
    evidence = evidence or {}
    authority_required = bool(
        gate.human_approval_required or "human_approval" in gate.required_evidence
    )
    authority = _evaluate_authority(
        state,
        evidence,
        required=authority_required,
    )

    met: List[str] = []
    missing: List[str] = []
    for key in gate.required_evidence:
        satisfied = (
            authority["satisfied"]
            if key == "human_approval"
            else bool(evidence.get(key))
        )
        if satisfied:
            met.append(key)
        else:
            missing.append(key)

    ok = len(missing) == 0
    can_proceed = ok and authority["satisfied"]

    return {
        "ok": ok,
        "state": state.name,
        "met_requirements": met,
        "missing_requirements": missing,
        "human_approval_required": gate.human_approval_required,
        "can_proceed": can_proceed,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "authority_mode": authority["authority_mode"],
        "authority_verified": authority["authority_verified"],
        "governance_decision_id": authority["governance_decision_id"],
        "governance_action_digest": authority["governance_action_digest"],
        "legacy_human_approval_used": authority["legacy_human_approval_used"],
        "authority_missing_reasons": list(authority["authority_missing_reasons"]),
        "authority_warnings": list(authority["authority_warnings"]),
        "required_policy_scope": authority["required_policy_scope"],
        "required_capability_scope": authority["required_capability_scope"],
    }


def workflow_state_machine() -> Dict[str, Any]:
    """Return the full state machine as a serializable dict packet.

    The packet includes the patch-authority constants, the ordered list of
    states, the blocked-patch-route set, and every gate definition.
    """
    return {
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "blocked_patch_routes": sorted(BLOCKED_PATCH_ROUTES),
        "states": [s.name for s in STATE_ORDER],
        "gates": {
            gate.state.name: gate.to_dict()
            for gate in (GATE_DEFINITIONS[s] for s in STATE_ORDER)
        },
    }


def workflow_gate_markdown() -> str:
    """Return a markdown table summarizing all 18 gates.

    The table has one row per state with columns: state, human approval,
    required evidence, allowed actions, blocked actions, and next states.
    """
    header = (
        "| # | State | Human Approval | Required Evidence | "
        "Allowed Actions | Blocked Actions | Next States |\n"
        "|---|-------|----------------|-------------------|"
        "-----------------|-----------------|-------------|\n"
    )
    rows: List[str] = []
    for idx, state in enumerate(STATE_ORDER, start=1):
        gate = GATE_DEFINITIONS[state]
        approval = "yes" if gate.human_approval_required else "no"
        evidence = ", ".join(gate.required_evidence) if gate.required_evidence else "—"
        allowed = ", ".join(gate.allowed_actions) if gate.allowed_actions else "—"
        blocked = ", ".join(gate.blocked_actions) if gate.blocked_actions else "—"
        nxt = ", ".join(s.name for s in gate.next_actions) if gate.next_actions else "—"
        rows.append(
            f"| {idx} | `{state.name}` | {approval} | {evidence} | "
            f"{allowed} | {blocked} | {nxt} |"
        )
    return header + "\n".join(rows)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce_state(value: Any) -> WorkflowState:
    """Coerce a string or :class:`WorkflowState` into a :class:`WorkflowState`.

    Raises ``KeyError`` for unknown names and ``TypeError`` for unsupported
    types.
    """
    if isinstance(value, WorkflowState):
        return value
    if isinstance(value, str):
        try:
            return WorkflowState[value]
        except KeyError as exc:
            raise KeyError(f"Unknown WorkflowState name: {value!r}") from exc
    raise TypeError(
        f"Expected a WorkflowState or str, got {type(value).__name__}"
    )


# ---------------------------------------------------------------------------
# Module-level convenience: allow ``import *``-style access and repr.
# ---------------------------------------------------------------------------

def __repr__() -> str:  # pragma: no cover - trivial
    return (
        "<AuraWorkflowGates "
        f"states={len(STATE_ORDER)} "
        f"patch_authority={PATCH_AUTHORITY!r}>"
    )


# ---------------------------------------------------------------------------
# CLI / smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    # Lightweight self-check when run directly.
    import sys

    print(f"Aura Workflow Gates — {len(STATE_ORDER)} states")
    print(f"PATCH_AUTHORITY = {PATCH_AUTHORITY!r}")
    print(f"VSA_PATCH_AUTHORITY = {VSA_PATCH_AUTHORITY!r}")
    print()

    # Verify every state has a gate definition.
    missing_defs = [
        s for s in STATE_ORDER if s not in GATE_DEFINITIONS
    ]
    if missing_defs:
        print("ERROR: missing gate definitions for:", missing_defs, file=sys.stderr)
        sys.exit(1)

    # Verify can_transition for the happy path.
    assert can_transition(
        WorkflowState.INGESTED, WorkflowState.POLYSYNTHETIC_COMPRESSED
    ), "INGESTED -> POLYSYNTHETIC_COMPRESSED should be allowed"
    assert not can_transition(
        WorkflowState.INGESTED, WorkflowState.PATCH_PROPOSED
    ), "INGESTED -> PATCH_PROPOSED should be blocked"
    assert not can_transition(
        WorkflowState.VERIFIED, WorkflowState.PR_OPENED
    ), "VERIFIED -> PR_OPENED should be blocked (needs PR_READY)"

    # Verify evaluate_gate.
    result = evaluate_gate(
        WorkflowState.LEXC_VALIDATED,
        {"lexc_valid": True, "lexc_grammar_ok": True},
    )
    assert result["ok"] is True
    assert result["can_proceed"] is True

    result_missing = evaluate_gate(
        WorkflowState.LEXC_VALIDATED,
        {"lexc_valid": True, "lexc_grammar_ok": False},
    )
    assert result_missing["ok"] is False
    assert "lexc_grammar_ok" in result_missing["missing_requirements"]

    # Verify human-approval gating.
    ha = evaluate_gate(
        WorkflowState.HUMAN_APPROVED_FOR_AGENT,
        {"human_approval": False},
    )
    assert ha["human_approval_required"] is True
    assert ha["can_proceed"] is False

    ha_ok = evaluate_gate(
        WorkflowState.HUMAN_APPROVED_FOR_AGENT,
        {"human_approval": True},
    )
    assert ha_ok["can_proceed"] is True

    # Verify the state machine dict is JSON-serializable.
    json.dumps(workflow_state_machine())

    # Verify markdown rendering produces a non-trivial table.
    md = workflow_gate_markdown()
    assert "| State |" in md
    assert md.count("\n") >= len(STATE_ORDER)

    print("All self-checks passed.")
    print()
    print(workflow_gate_markdown())

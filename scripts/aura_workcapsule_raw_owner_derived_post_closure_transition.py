#!/usr/bin/env python3
"""Derive the exact POST O10 closure at the PR533/PR518 ownership boundary.

PR533 derives the rejected-currentness PRE lifecycle from raw owner evidence and
owns the final exact HOLD -> distinct POST CLOSED transition, but intentionally
accepts one pinned POST O10 closure. PR518 independently derives the POST candidate
from distinct raw POST source-owner evidence and verifies an exact O10 receipt
against a supplied PRE re-entry receipt.

This D0 membrane removes the final caller-selected lifecycle intermediate without
changing either parent owner's causal history:

    raw PRE -> PR533 PRE lifecycle -> PRE O8/HOLD
    raw POST -> PR518 POST candidate
    previous binding + PRE O8 + POST candidate -> exact O10 closure
    exact O10 -> PR518 reproof -> PR533 final transition

It does not substitute a fresh POST re-entry receipt for the PRE re-entry receipt.
It mints no source currentness, semantic repair correctness, producer identity,
review/effect authority, or hidden/native transformer KV state.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_raw_owner_hold_to_closed_transition import (
    _derive_pre_lifecycle,
    admit_raw_owner_hold_to_closed_transition,
    verify_raw_owner_hold_to_closed_transition,
)
from scripts.aura_workcapsule_reentry_closure import CLOSED, HOLD, compile_reentry_closure
from scripts.aura_workcapsule_two_phase_source_bound_closure import (
    admit_two_phase_source_bound_exact_closure,
    derive_post_reentry_candidate,
    verify_two_phase_source_bound_exact_closure,
)

VERSION = "AURA_WORKCAPSULE_RAW_OWNER_DERIVED_POST_CLOSURE_TRANSITION_V1"
PRE_PREFIX = "PRE_RAW_OWNER_"
POST_PREFIX = "POST_RAW_OWNER_"
PR518_PREFIX = "PR518_TWO_PHASE_"
PR533_PREFIX = "PR533_TRANSITION_"
PRE_NOT_HOLD = "PRE_RAW_OWNER_LIFECYCLE_NOT_HOLD"
POST_NOT_CLOSED = "DERIVED_POST_O10_NOT_CLOSED"
POST_CLOSURE_IDENTITY_MISMATCH = "POST_O10_IDENTITY_MISMATCH"
POST_CANDIDATE_IDENTITY_MISMATCH = "POST_CANDIDATE_IDENTITY_MISMATCH"


def _derive_transition_inputs(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    pre = _derive_pre_lifecycle(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
    )
    if pre.get("closure_status") != HOLD:
        raise ValueError(PRE_NOT_HOLD)

    post_projection, post_candidate = derive_post_reentry_candidate(
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        post_graph_witness=post_graph_witness,
    )
    post_closure = compile_reentry_closure(
        previous_binding=previous_binding,
        reentry_receipt=pre["derived_reentry_receipt"],
        candidate_binding=post_candidate,
    )
    return pre, post_projection, post_candidate, post_closure


def verify_raw_owner_derived_post_closure_transition(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> list[str]:
    """Verify one fully raw-owner HOLD -> CLOSED transition without caller closure input."""
    try:
        pre, _projection, _candidate, post_closure = _derive_transition_inputs(
            pre_root=pre_root,
            pre_codemap=pre_codemap,
            pre_anchor_manifest=pre_anchor_manifest,
            pre_witness_manifest=pre_witness_manifest,
            previous_binding=previous_binding,
            pre_graph_witness=pre_graph_witness,
            post_root=post_root,
            post_codemap=post_codemap,
            post_anchor_manifest=post_anchor_manifest,
            post_witness_manifest=post_witness_manifest,
            post_graph_witness=post_graph_witness,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{POST_PREFIX}DERIVATION_FAILED:{exc}"]

    pr518_violations = verify_two_phase_source_bound_exact_closure(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=pre["derived_reentry_receipt"],
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=post_closure,
    )
    if pr518_violations:
        return [PR518_PREFIX + item for item in pr518_violations]
    if post_closure.get("closure_status") != CLOSED:
        return [POST_NOT_CLOSED]

    pr533_violations = verify_raw_owner_hold_to_closed_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_closure_receipt=post_closure,
    )
    return [PR533_PREFIX + item for item in pr533_violations]


def admit_raw_owner_derived_post_closure_transition(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    """Admit the corrected fully raw-owner temporal consequence or fail closed."""
    violations = verify_raw_owner_derived_post_closure_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
    )
    if violations:
        raise ValueError(
            "raw-owner derived POST closure transition failed: " + ",".join(violations)
        )

    pre, post_projection, post_candidate, post_closure = _derive_transition_inputs(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
    )
    pr518 = admit_two_phase_source_bound_exact_closure(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=pre["derived_reentry_receipt"],
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=post_closure,
    )
    pr533 = admit_raw_owner_hold_to_closed_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_closure_receipt=post_closure,
    )

    pr518_closure_identity = pr518["exact_closure_admission"]["o10_closure_receipt_identity"]
    if pr518_closure_identity != post_closure.get("receipt_identity"):
        raise ValueError(POST_CLOSURE_IDENTITY_MISMATCH)
    if pr533.get("post_closure_receipt_identity") != post_closure.get("receipt_identity"):
        raise ValueError(POST_CLOSURE_IDENTITY_MISMATCH)
    if pr518.get("post_derived_candidate_binding_identity") != post_candidate.get("binding_identity"):
        raise ValueError(POST_CANDIDATE_IDENTITY_MISMATCH)

    return {
        "version": VERSION,
        "raw_owner_pre_lifecycle_derived": True,
        "raw_owner_post_candidate_derived": True,
        "post_o10_closure_derived": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "caller_post_closure_receipt_accepted": False,
        "caller_reentry_receipt_accepted": False,
        "caller_candidate_binding_accepted": False,
        "caller_source_witnesses_accepted": False,
        "exact_hold_to_closed_transition": True,
        "pre_closure_status": pr533["pre_closure_status"],
        "post_closure_status": pr533["post_closure_status"],
        "pre_reentry_receipt_identity": pre["derived_reentry_receipt"]["receipt_identity"],
        "post_source_projection_receipt_identity": post_projection["receipt_identity"],
        "post_candidate_binding_identity": post_candidate["binding_identity"],
        "post_o10_closure_receipt_identity": post_closure["receipt_identity"],
        "pr518_post_o10_closure_receipt_identity": pr518_closure_identity,
        "pr533_post_o10_closure_receipt_identity": pr533["post_closure_receipt_identity"],
        "pre_and_post_evidence_are_distinct_phases": pr533[
            "pre_and_post_evidence_are_distinct_phases"
        ],
        "source_generation_domain_preserved": pr518["source_generation_domain_preserved"],
        "source_currentness_minted": False,
        "semantic_repair_correctness_minted": False,
        "producer_identity_authenticated": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
        "authority": {
            "review_authorized": False,
            "mutation_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }

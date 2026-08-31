#!/usr/bin/env python3
"""Remove the final caller-selected closure from the exact raw-owner HOLD -> CLOSED transition.

PR533 derives the complete rejected-currentness PRE lifecycle from raw owner evidence and then
proves a distinct POST CLOSED transition, but intentionally keeps one POST closure receipt pinned
at its public boundary. PR523 derives one canonical re-entry plan, candidate, and observation-bound
closure from raw owner evidence and accepts neither caller O8 nor caller candidate bindings.

This D0 successor derives the POST closure through PR523 from the same POST raw evidence passed to
PR533, requires that owner-derived consequence to be CLOSED, and passes only that exact derived
closure into PR533. No caller lifecycle intermediate remains. Exact temporal provenance remains
separate from producer authentication, semantic repair correctness, dependency-cone proof, review,
or operational authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_owner_bound_reentry_closure import (
    compile_owner_bound_reentry_closure,
    verify_owner_bound_reentry_closure,
)
from scripts.aura_workcapsule_raw_owner_hold_to_closed_transition import (
    admit_raw_owner_hold_to_closed_transition,
    verify_raw_owner_hold_to_closed_transition,
)

VERSION = "AURA_WORKCAPSULE_FULLY_RAW_OWNER_HOLD_TO_CLOSED_TRANSITION_V1"
POST_OWNER_PREFIX = "POST_RAW_OWNER_"
TRANSITION_PREFIX = "TRANSITION_"
POST_NOT_CLOSED = "POST_RAW_OWNER_CLOSURE_NOT_CLOSED"
POST_CLOSURE_IDENTITY_MISMATCH = "POST_DERIVED_CLOSURE_IDENTITY_MISMATCH"


def _derive_post_owner_closure(
    *,
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    owner = compile_owner_bound_reentry_closure(
        root=post_root,
        codemap=post_codemap,
        anchor_manifest=post_anchor_manifest,
        witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=post_graph_witness,
        candidate_graph_witness=post_graph_witness,
    )
    violations = verify_owner_bound_reentry_closure(
        root=post_root,
        codemap=post_codemap,
        anchor_manifest=post_anchor_manifest,
        witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=post_graph_witness,
        candidate_graph_witness=post_graph_witness,
        receipt=owner,
    )
    if violations:
        raise ValueError("owner-derived POST closure is not exact: " + ",".join(violations))
    closure = owner.get("observation_bound_closure")
    if not isinstance(closure, dict):
        raise ValueError("owner-derived POST closure payload missing")
    return owner, closure


def verify_fully_raw_owner_hold_to_closed_transition(
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
    """Verify an exact HOLD -> CLOSED transition with no caller lifecycle intermediate."""
    try:
        post_owner, post_closure = _derive_post_owner_closure(
            post_root=post_root,
            post_codemap=post_codemap,
            post_anchor_manifest=post_anchor_manifest,
            post_witness_manifest=post_witness_manifest,
            previous_binding=previous_binding,
            post_graph_witness=post_graph_witness,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{POST_OWNER_PREFIX}DERIVATION_FAILED:{exc}"]

    if post_owner.get("closure_status") != "CLOSED" or post_closure.get("closure_status") != "CLOSED":
        return [POST_NOT_CLOSED]

    transition_violations = verify_raw_owner_hold_to_closed_transition(
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
    return [TRANSITION_PREFIX + item for item in transition_violations]


def admit_fully_raw_owner_hold_to_closed_transition(
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
    """Admit the no-caller-intermediate temporal transition or fail closed."""
    violations = verify_fully_raw_owner_hold_to_closed_transition(
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
            "fully raw-owner HOLD-to-CLOSED transition failed: " + ",".join(violations)
        )

    post_owner, post_closure = _derive_post_owner_closure(
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        post_graph_witness=post_graph_witness,
    )
    transition = admit_raw_owner_hold_to_closed_transition(
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
    if transition.get("post_closure_receipt_identity") != post_closure.get("receipt_identity"):
        raise ValueError(POST_CLOSURE_IDENTITY_MISMATCH)

    return {
        "version": VERSION,
        "raw_owner_pre_lifecycle_derived": True,
        "raw_owner_post_closure_derived": True,
        "caller_reentry_receipt_accepted": False,
        "caller_pre_observation_receipt_accepted": False,
        "caller_post_closure_receipt_accepted": False,
        "caller_source_observation_receipt_accepted": False,
        "caller_source_witnesses_accepted": False,
        "caller_candidate_binding_accepted": False,
        "caller_lifecycle_intermediate_accepted": False,
        "exact_hold_to_closed_transition": True,
        "pre_closure_status": transition["pre_closure_status"],
        "post_closure_status": transition["post_closure_status"],
        "post_owner_bound_lifecycle_receipt_identity": post_owner["receipt_identity"],
        "post_owner_derived_reentry_receipt_identity": post_owner[
            "owner_derived_reentry_receipt_identity"
        ],
        "post_owner_derived_candidate_binding_identity": post_owner[
            "derived_candidate_binding_identity"
        ],
        "post_owner_derived_closure_receipt_identity": post_closure["receipt_identity"],
        "transition_post_closure_receipt_identity": transition[
            "post_closure_receipt_identity"
        ],
        "pre_and_post_evidence_are_distinct_phases": transition[
            "pre_and_post_evidence_are_distinct_phases"
        ],
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

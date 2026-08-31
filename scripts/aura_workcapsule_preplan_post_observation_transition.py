#!/usr/bin/env python3
"""Eliminate the final caller POST-closure slot while preserving PRE plan identity.

PR533 derives the rejected-currentness PRE lifecycle from raw owner evidence and proves an exact
distinct POST CLOSED transition, but deliberately accepts a pinned POST closure. PR516 accepts an
existing re-entry receipt and derives the candidate source basis and closure from fresh raw source
observations, with no caller candidate binding.

This D0 membrane derives the PRE lifecycle once from PR533's raw-owner substrate, passes that exact
PRE-derived re-entry receipt into PR516 over the POST raw world, extracts PR516's exact inner O10
closure, and passes only that closure to PR533. Therefore the transition preserves the PRE plan
while removing the caller's final lifecycle-intermediate choice.

Exact temporal/source provenance remains separate from source-currentness minting, producer
authentication, semantic repair correctness, dependency-cone proof, review, execution, or effect
authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_closure import (
    compile_observation_bound_reentry_closure,
    verify_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_raw_owner_end_to_end_stale_lifecycle import (
    compile_raw_owner_end_to_end_stale_lifecycle,
    verify_raw_owner_end_to_end_stale_lifecycle,
)
from scripts.aura_workcapsule_raw_owner_hold_to_closed_transition import (
    admit_raw_owner_hold_to_closed_transition,
    verify_raw_owner_hold_to_closed_transition,
)

VERSION = "AURA_WORKCAPSULE_PREPLAN_POST_OBSERVATION_TRANSITION_V1"
PRE_OWNER_PREFIX = "PRE_RAW_OWNER_"
POST_OWNER_PREFIX = "POST_OBSERVATION_OWNER_"
TRANSITION_PREFIX = "TRANSITION_"
PRE_NOT_HOLD = "PRE_OWNER_LIFECYCLE_NOT_HOLD"
POST_NOT_CLOSED = "POST_OBSERVATION_CLOSURE_NOT_CLOSED"
PLAN_IDENTITY_MISMATCH = "PRE_PLAN_TO_POST_CLOSURE_IDENTITY_MISMATCH"
POST_CLOSURE_IDENTITY_MISMATCH = "POST_CLOSURE_TO_TRANSITION_IDENTITY_MISMATCH"


def _derive_pre_owner(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    pre = compile_raw_owner_end_to_end_stale_lifecycle(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
    )
    violations = verify_raw_owner_end_to_end_stale_lifecycle(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
        lifecycle_receipt=pre,
    )
    if violations:
        raise ValueError("PRE raw-owner lifecycle is not exact: " + ",".join(violations))
    if pre.get("closure_status") != "HOLD":
        raise ValueError(PRE_NOT_HOLD)
    return pre


def _derive_post_observation_closure(
    *,
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_reentry_receipt: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    post = compile_observation_bound_reentry_closure(
        root=post_root,
        codemap=post_codemap,
        anchor_manifest=post_anchor_manifest,
        witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=pre_reentry_receipt,
        candidate_graph_witness=post_graph_witness,
    )
    violations = verify_observation_bound_reentry_closure(post)
    if violations:
        raise ValueError("POST observation closure is not coherent: " + ",".join(violations))
    closure = post.get("closure_receipt")
    if post.get("closure_status") != "CLOSED" or not isinstance(closure, dict) or closure.get(
        "closure_status"
    ) != "CLOSED":
        raise ValueError(POST_NOT_CLOSED)
    if post.get("reentry_receipt_identity") != pre_reentry_receipt.get("receipt_identity"):
        raise ValueError(PLAN_IDENTITY_MISMATCH)
    if closure.get("reentry_receipt_identity") != pre_reentry_receipt.get("receipt_identity"):
        raise ValueError(PLAN_IDENTITY_MISMATCH)
    return post, closure


def verify_preplan_post_observation_transition(
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
    """Verify raw PRE HOLD -> raw POST CLOSED with no caller lifecycle intermediate."""
    try:
        pre = _derive_pre_owner(
            pre_root=pre_root,
            pre_codemap=pre_codemap,
            pre_anchor_manifest=pre_anchor_manifest,
            pre_witness_manifest=pre_witness_manifest,
            previous_binding=previous_binding,
            pre_graph_witness=pre_graph_witness,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{PRE_OWNER_PREFIX}DERIVATION_FAILED:{exc}"]

    try:
        _, post_closure = _derive_post_observation_closure(
            post_root=post_root,
            post_codemap=post_codemap,
            post_anchor_manifest=post_anchor_manifest,
            post_witness_manifest=post_witness_manifest,
            previous_binding=previous_binding,
            pre_reentry_receipt=pre["derived_reentry_receipt"],
            post_graph_witness=post_graph_witness,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{POST_OWNER_PREFIX}DERIVATION_FAILED:{exc}"]

    violations = verify_raw_owner_hold_to_closed_transition(
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
    return [TRANSITION_PREFIX + item for item in violations]


def admit_preplan_post_observation_transition(
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
    violations = verify_preplan_post_observation_transition(
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
        raise ValueError("PRE-plan/POST-observation transition failed: " + ",".join(violations))

    pre = _derive_pre_owner(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
    )
    post, post_closure = _derive_post_observation_closure(
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        pre_reentry_receipt=pre["derived_reentry_receipt"],
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

    pre_plan_identity = pre["derived_reentry_receipt"]["receipt_identity"]
    if post.get("reentry_receipt_identity") != pre_plan_identity:
        raise ValueError(PLAN_IDENTITY_MISMATCH)
    if post_closure.get("reentry_receipt_identity") != pre_plan_identity:
        raise ValueError(PLAN_IDENTITY_MISMATCH)
    if transition.get("post_closure_receipt_identity") != post_closure.get("receipt_identity"):
        raise ValueError(POST_CLOSURE_IDENTITY_MISMATCH)

    return {
        "version": VERSION,
        "raw_owner_pre_lifecycle_derived": True,
        "pre_reentry_plan_derived_from_pre_raw_owner": True,
        "post_candidate_derived_from_post_raw_observations": True,
        "post_closure_derived_around_exact_pre_plan": True,
        "caller_reentry_receipt_accepted": False,
        "caller_pre_observation_receipt_accepted": False,
        "caller_post_closure_receipt_accepted": False,
        "caller_candidate_binding_accepted": False,
        "caller_source_observation_receipt_accepted": False,
        "caller_source_witnesses_accepted": False,
        "caller_lifecycle_intermediate_accepted": False,
        "exact_hold_to_closed_transition": True,
        "pre_closure_status": transition["pre_closure_status"],
        "post_closure_status": transition["post_closure_status"],
        "pre_derived_reentry_receipt_identity": pre_plan_identity,
        "post_observation_bound_receipt_identity": post["receipt_identity"],
        "post_source_observation_identity": post["source_observation_identity"],
        "post_derived_candidate_binding_identity": post[
            "derived_candidate_binding_identity"
        ],
        "post_derived_closure_receipt_identity": post_closure["receipt_identity"],
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

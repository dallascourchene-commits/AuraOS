#!/usr/bin/env python3
"""Prove an owner-reduced rejected-currentness HOLD -> repaired CLOSED transition.

PR524 owns the pre-repair rejected-currentness consequence: a PR516 observation-
bound closure receipt must first be proven by the general exact raw-input owner,
then consumed by the stale-safety owner, and it must remain HOLD. PR518 owns the
two-phase lifecycle: pre-reentry and post-repair raw evidence are distinct states,
the pre O8 receipt is source-owner-bound, the post candidate is derived from fresh
raw evidence, and closure is exact.

This child composes those two owners without replaying source observation, O8,
candidate, or closure constructors. It proves a narrower transition only:

    exact pre rejected-currentness HOLD -> exact distinct post CLOSED.

The same pre source-observation identity and O8 receipt identity must be witnessed
by both parents. No producer authentication, semantic truth, or effect authority
is created.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_closure import HOLD
from scripts.aura_workcapsule_reentry_closure import CLOSED
from scripts.aura_workcapsule_stale_exact_observation_owner_reduction import (
    admit_stale_exact_observation_owner_reduction,
    verify_stale_exact_observation_owner_reduction,
)
from scripts.aura_workcapsule_two_phase_source_bound_closure import (
    admit_two_phase_source_bound_exact_closure,
    verify_two_phase_source_bound_exact_closure,
)

VERSION = "AURA_WORKCAPSULE_TWO_PHASE_OWNER_REDUCED_TRANSITION_V1"
PRE_PREFIX = "PRE_HOLD_"
TWO_PHASE_PREFIX = "TWO_PHASE_"
PRE_PHASE_NOT_HOLD = "PRE_PHASE_NOT_HOLD"
POST_PHASE_NOT_CLOSED = "POST_PHASE_NOT_CLOSED"
PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH = "PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH"
PRE_REENTRY_RECEIPT_IDENTITY_MISMATCH = "PRE_REENTRY_RECEIPT_IDENTITY_MISMATCH"


def verify_two_phase_owner_reduced_transition(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    pre_observation_closure_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> list[str]:
    """Verify exact pre HOLD and distinct post CLOSED by consuming parent owners."""
    pre_violations = verify_stale_exact_observation_owner_reduction(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
        receipt=pre_observation_closure_receipt,
    )
    if pre_violations:
        return [PRE_PREFIX + item for item in pre_violations]

    two_phase_violations = verify_two_phase_source_bound_exact_closure(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=closure_receipt,
    )
    if two_phase_violations:
        return [TWO_PHASE_PREFIX + item for item in two_phase_violations]

    # Parent admissions expose the identities needed to prove both parents
    # witnessed the same pre-repair source observation and re-entry receipt.
    pre = admit_stale_exact_observation_owner_reduction(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
        receipt=pre_observation_closure_receipt,
    )
    lifecycle = admit_two_phase_source_bound_exact_closure(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=closure_receipt,
    )

    violations: list[str] = []
    if pre.get("closure_status") != HOLD:
        violations.append(PRE_PHASE_NOT_HOLD)
    if lifecycle.get("closure_status") != CLOSED:
        violations.append(POST_PHASE_NOT_CLOSED)

    pre_lifecycle = lifecycle.get("pre_source_owner_bound_exact_reentry", {})
    if pre.get("source_observation_identity") != pre_lifecycle.get("source_projection_receipt_identity"):
        violations.append(PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH)
    if pre.get("reentry_receipt_identity") != pre_lifecycle.get("o8_receipt_identity"):
        violations.append(PRE_REENTRY_RECEIPT_IDENTITY_MISMATCH)
    return violations


def admit_two_phase_owner_reduced_transition(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    pre_observation_closure_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit only an exact distinct-phase HOLD -> CLOSED transition."""
    violations = verify_two_phase_owner_reduced_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        pre_observation_closure_receipt=pre_observation_closure_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=closure_receipt,
    )
    if violations:
        raise ValueError("two-phase owner-reduced transition failed: " + ",".join(violations))

    pre = admit_stale_exact_observation_owner_reduction(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
        receipt=pre_observation_closure_receipt,
    )
    lifecycle = admit_two_phase_source_bound_exact_closure(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=closure_receipt,
    )
    return {
        "version": VERSION,
        "owner_reduced_pre_hold_proven": True,
        "two_phase_post_closed_proven": True,
        "pre_and_post_evidence_are_distinct_phases": True,
        "pre_closure_status": pre["closure_status"],
        "post_closure_status": lifecycle["closure_status"],
        "pre_source_observation_identity": pre["source_observation_identity"],
        "pre_reentry_receipt_identity": pre["reentry_receipt_identity"],
        "post_source_projection_receipt_identity": lifecycle["post_source_projection_receipt_identity"],
        "post_derived_candidate_binding_identity": lifecycle["post_derived_candidate_binding_identity"],
        "same_pre_source_observation_witnessed_by_both_parents": True,
        "raw_replay_reimplemented_by_child": False,
        "source_currentness_minted": False,
        "producer_identity_authenticated": False,
        "pre_graph_producer_authenticated": False,
        "post_graph_producer_authenticated": False,
        "semantic_truth_minted": False,
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

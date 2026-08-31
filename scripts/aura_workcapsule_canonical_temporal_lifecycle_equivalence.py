#!/usr/bin/env python3
"""Canonicalize one temporal lifecycle across two independently green owners.

PR530 owns the specialized rejected-currentness transition: exact pre HOLD ->
distinct post CLOSED, using owner-reduced parent boundaries. PR529 owns the general
two-phase exact observation replay: exact pre O8 + exact post outer PR516 receipt,
with the PR518 inner lifecycle replayed when an inner closure exists.

This D0 sentry consumes only those public owners. It does not replay source
observation, O8 planning, candidate construction, closure construction, or raw-owner
compilation. Its only consequence is cross-owner continuity: when both parents are
asked about the same raw worlds and pinned O8, they must expose one canonical
identity tuple for the temporal lifecycle.

Canonical equivalence is not semantic repair correctness, producer authentication,
source currentness, review authority, mutation/execution/commit/merge/promotion, or
any provider/public/human effect.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_two_phase_observation_bound_exact import (
    admit_two_phase_observation_bound_exact,
    verify_two_phase_observation_bound_exact,
)
from scripts.aura_workcapsule_two_phase_owner_reduced_transition import (
    admit_two_phase_owner_reduced_transition,
    verify_two_phase_owner_reduced_transition,
)

VERSION = "AURA_WORKCAPSULE_CANONICAL_TEMPORAL_LIFECYCLE_EQUIVALENCE_V1"
SPECIALIZED_PREFIX = "SPECIALIZED_"
GENERAL_PREFIX = "GENERAL_"
POST_OUTER_INNER_CLOSURE_REQUIRED = "POST_OUTER_INNER_CLOSURE_REQUIRED"
SPECIALIZED_NOT_CLOSED = "SPECIALIZED_TRANSITION_NOT_CLOSED"
GENERAL_NOT_CLOSED = "GENERAL_TWO_PHASE_REPLAY_NOT_CLOSED"
GENERAL_INNER_LIFECYCLE_NOT_REPLAYED = "GENERAL_INNER_LIFECYCLE_NOT_REPLAYED"
PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH = "PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH"
PRE_REENTRY_RECEIPT_IDENTITY_MISMATCH = "PRE_REENTRY_RECEIPT_IDENTITY_MISMATCH"
POST_SOURCE_PROJECTION_IDENTITY_MISMATCH = "POST_SOURCE_PROJECTION_IDENTITY_MISMATCH"
POST_DERIVED_CANDIDATE_IDENTITY_MISMATCH = "POST_DERIVED_CANDIDATE_IDENTITY_MISMATCH"
POST_INNER_CLOSURE_IDENTITY_MISMATCH = "POST_INNER_CLOSURE_IDENTITY_MISMATCH"
PHASE_DISTINCTNESS_MISMATCH = "PHASE_DISTINCTNESS_MISMATCH"


def verify_canonical_temporal_lifecycle_equivalence(
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
    post_observation_bound_receipt: dict[str, Any],
) -> list[str]:
    """Require PR530 and PR529 to describe the same exact temporal lifecycle."""
    inner_closure = post_observation_bound_receipt.get("closure_receipt")
    if not isinstance(inner_closure, dict):
        return [POST_OUTER_INNER_CLOSURE_REQUIRED]

    specialized_violations = verify_two_phase_owner_reduced_transition(
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
        closure_receipt=inner_closure,
    )
    if specialized_violations:
        return [SPECIALIZED_PREFIX + item for item in specialized_violations]

    general_violations = verify_two_phase_observation_bound_exact(
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
        observation_bound_receipt=post_observation_bound_receipt,
    )
    if general_violations:
        return [GENERAL_PREFIX + item for item in general_violations]

    specialized = admit_two_phase_owner_reduced_transition(
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
        closure_receipt=inner_closure,
    )
    general = admit_two_phase_observation_bound_exact(
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
        observation_bound_receipt=post_observation_bound_receipt,
    )

    violations: list[str] = []
    if specialized.get("post_closure_status") != "CLOSED":
        violations.append(SPECIALIZED_NOT_CLOSED)
    if general.get("closure_status") != "CLOSED":
        violations.append(GENERAL_NOT_CLOSED)
    if general.get("inner_two_phase_exact_lifecycle_replayed") is not True:
        violations.append(GENERAL_INNER_LIFECYCLE_NOT_REPLAYED)

    general_pre = general.get("pre_source_owner_bound_exact_reentry", {})
    general_inner = general.get("inner_two_phase_exact_lifecycle")
    if not isinstance(general_inner, dict):
        violations.append(GENERAL_INNER_LIFECYCLE_NOT_REPLAYED)
        return list(dict.fromkeys(violations))

    if specialized.get("pre_source_observation_identity") != general_pre.get(
        "source_projection_receipt_identity"
    ):
        violations.append(PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH)
    if specialized.get("pre_reentry_receipt_identity") != general_pre.get("o8_receipt_identity"):
        violations.append(PRE_REENTRY_RECEIPT_IDENTITY_MISMATCH)
    if specialized.get("post_source_projection_receipt_identity") != general_inner.get(
        "post_source_projection_receipt_identity"
    ):
        violations.append(POST_SOURCE_PROJECTION_IDENTITY_MISMATCH)
    if specialized.get("post_derived_candidate_binding_identity") != general_inner.get(
        "post_derived_candidate_binding_identity"
    ):
        violations.append(POST_DERIVED_CANDIDATE_IDENTITY_MISMATCH)

    exact_closure = general_inner.get("exact_closure_admission", {})
    if inner_closure.get("receipt_identity") != exact_closure.get("o10_closure_receipt_identity"):
        violations.append(POST_INNER_CLOSURE_IDENTITY_MISMATCH)

    if specialized.get("pre_and_post_evidence_are_distinct_phases") is not True or general.get(
        "pre_and_post_evidence_are_distinct_phases"
    ) is not True:
        violations.append(PHASE_DISTINCTNESS_MISMATCH)

    return list(dict.fromkeys(violations))


def admit_canonical_temporal_lifecycle_equivalence(
    **kwargs: Any,
) -> dict[str, Any]:
    """Admit only cross-owner canonical lifecycle equivalence or fail closed."""
    violations = verify_canonical_temporal_lifecycle_equivalence(**kwargs)
    if violations:
        raise ValueError("canonical temporal lifecycle equivalence failed: " + ",".join(violations))

    inner_closure = kwargs["post_observation_bound_receipt"]["closure_receipt"]
    specialized = admit_two_phase_owner_reduced_transition(
        pre_root=kwargs["pre_root"],
        pre_codemap=kwargs["pre_codemap"],
        pre_anchor_manifest=kwargs["pre_anchor_manifest"],
        pre_witness_manifest=kwargs["pre_witness_manifest"],
        previous_binding=kwargs["previous_binding"],
        pre_graph_witness=kwargs["pre_graph_witness"],
        reentry_receipt=kwargs["reentry_receipt"],
        pre_observation_closure_receipt=kwargs["pre_observation_closure_receipt"],
        post_root=kwargs["post_root"],
        post_codemap=kwargs["post_codemap"],
        post_anchor_manifest=kwargs["post_anchor_manifest"],
        post_witness_manifest=kwargs["post_witness_manifest"],
        post_graph_witness=kwargs["post_graph_witness"],
        closure_receipt=inner_closure,
    )
    general = admit_two_phase_observation_bound_exact(
        pre_root=kwargs["pre_root"],
        pre_codemap=kwargs["pre_codemap"],
        pre_anchor_manifest=kwargs["pre_anchor_manifest"],
        pre_witness_manifest=kwargs["pre_witness_manifest"],
        previous_binding=kwargs["previous_binding"],
        pre_graph_witness=kwargs["pre_graph_witness"],
        reentry_receipt=kwargs["reentry_receipt"],
        post_root=kwargs["post_root"],
        post_codemap=kwargs["post_codemap"],
        post_anchor_manifest=kwargs["post_anchor_manifest"],
        post_witness_manifest=kwargs["post_witness_manifest"],
        post_graph_witness=kwargs["post_graph_witness"],
        observation_bound_receipt=kwargs["post_observation_bound_receipt"],
    )
    general_inner = general["inner_two_phase_exact_lifecycle"]

    return {
        "version": VERSION,
        "canonical_temporal_lifecycle_equivalence_proven": True,
        "specialized_owner_reduced_transition_proven": True,
        "general_two_phase_observation_replay_proven": True,
        "pre_and_post_evidence_are_distinct_phases": True,
        "pre_closure_status": specialized["pre_closure_status"],
        "post_closure_status": specialized["post_closure_status"],
        "pre_source_observation_identity": specialized["pre_source_observation_identity"],
        "pre_reentry_receipt_identity": specialized["pre_reentry_receipt_identity"],
        "post_source_projection_receipt_identity": specialized[
            "post_source_projection_receipt_identity"
        ],
        "post_derived_candidate_binding_identity": specialized[
            "post_derived_candidate_binding_identity"
        ],
        "post_inner_closure_receipt_identity": general_inner["exact_closure_admission"][
            "o10_closure_receipt_identity"
        ],
        "cross_owner_identity_tuple_exact": True,
        "raw_replay_reimplemented_by_child": False,
        "semantic_repair_correctness_minted": False,
        "source_currentness_minted": False,
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

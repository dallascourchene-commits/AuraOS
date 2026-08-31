#!/usr/bin/env python3
"""Two-phase exact replay for observation-bound WorkCapsule closure receipts.

PR518 proves temporal separation: pre-reentry raw owner evidence determines the exact
O8 re-entry decision and distinct post-repair raw evidence determines the closure
candidate. PR519 proves a complete PR516 observation-bound receipt is exactly
reproducible from pinned raw inputs.

This D0 composition keeps those owners separate. The pre phase replays PR514 against
its raw snapshot. The post phase replays PR519 against a distinct raw snapshot. When
the exact PR516 consequence contains an inner O10 closure receipt, PR518 is also
replayed over that inner closure so the temporal lifecycle and complete outer receipt
are both current on the same supplied evidence pair.

No caller candidate binding or source-witness list is accepted. Exact replay does not
mint source currentness, producer authentication, semantic truth, authority, or a
source-to-graph dependency map.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_exact_verifier import (
    admit_exact_observation_bound_reentry_closure,
    verify_exact_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import (
    admit_source_bound_exact_reentry,
    verify_source_bound_exact_reentry,
)
from scripts.aura_workcapsule_two_phase_source_bound_closure import (
    admit_two_phase_source_bound_exact_closure,
    verify_two_phase_source_bound_exact_closure,
)

VERSION = "AURA_WORKCAPSULE_TWO_PHASE_OBSERVATION_BOUND_EXACT_V1"
SAME_PHASE_ROOT = "PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT"


def verify_two_phase_observation_bound_exact(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    observation_bound_receipt: dict[str, Any],
) -> list[str]:
    """Verify exact pre O8 and exact post PR516 replay across distinct evidence roots."""
    if pre_root.resolve() == post_root.resolve():
        return [SAME_PHASE_ROOT]

    violations: list[str] = []
    pre_violations = verify_source_bound_exact_reentry(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        receipt=reentry_receipt,
    )
    violations.extend(f"PRE_{item}" for item in pre_violations)
    if pre_violations:
        return list(dict.fromkeys(violations))

    post_violations = verify_exact_observation_bound_reentry_closure(
        root=post_root,
        codemap=post_codemap,
        anchor_manifest=post_anchor_manifest,
        witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=post_graph_witness,
        receipt=observation_bound_receipt,
    )
    violations.extend(f"POST_{item}" for item in post_violations)
    if post_violations:
        return list(dict.fromkeys(violations))

    inner_closure = observation_bound_receipt.get("closure_receipt")
    if isinstance(inner_closure, dict):
        lifecycle_violations = verify_two_phase_source_bound_exact_closure(
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
            closure_receipt=inner_closure,
        )
        violations.extend(f"PR518_{item}" for item in lifecycle_violations)

    return list(dict.fromkeys(violations))


def admit_two_phase_observation_bound_exact(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    observation_bound_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Return a narrow two-phase replay witness or fail closed."""
    violations = verify_two_phase_observation_bound_exact(
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
        observation_bound_receipt=observation_bound_receipt,
    )
    if violations:
        raise ValueError("two-phase observation-bound exact verification failed: " + ",".join(violations))

    pre_admission = admit_source_bound_exact_reentry(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        receipt=reentry_receipt,
    )
    post_admission = admit_exact_observation_bound_reentry_closure(
        root=post_root,
        codemap=post_codemap,
        anchor_manifest=post_anchor_manifest,
        witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=post_graph_witness,
        receipt=observation_bound_receipt,
    )

    inner_closure = observation_bound_receipt.get("closure_receipt")
    lifecycle_admission = None
    if isinstance(inner_closure, dict):
        lifecycle_admission = admit_two_phase_source_bound_exact_closure(
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
            closure_receipt=inner_closure,
        )

    return {
        "version": VERSION,
        "two_phase_observation_bound_exact_reproduction": True,
        "pre_and_post_evidence_are_distinct_phases": True,
        "pre_source_owner_bound_exact_reentry": pre_admission,
        "post_observation_bound_exact_reproduction": post_admission,
        "inner_two_phase_exact_lifecycle_replayed": lifecycle_admission is not None,
        "inner_two_phase_exact_lifecycle": lifecycle_admission,
        "closure_status": post_admission["closure_status"],
        "caller_candidate_binding_accepted": False,
        "caller_source_witnesses_accepted": False,
        "source_currentness_minted": False,
        "producer_identity_authenticated": False,
        "pre_graph_producer_authenticated": False,
        "post_graph_producer_authenticated": False,
        "semantic_truth_minted": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
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

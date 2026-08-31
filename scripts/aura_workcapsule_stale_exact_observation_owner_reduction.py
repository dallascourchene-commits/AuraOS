#!/usr/bin/env python3
"""Compose the canonical exact observation-closure owner with stale-safety.

PR519 owns general exact raw-input reproduction for PR516 observation-bound
closure receipts. PR517 owns rejected-currentness exact re-entry semantics.
This membrane composes those owners without reimplementing PR509/PR516 replay.

The embedded source observation is trusted only after PR519 proves the complete
receipt is the exact deterministic consequence of the supplied raw inputs.
It is then consumed by PR517 solely for STALE/UNKNOWN re-entry semantics.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_exact_verifier import (
    admit_exact_observation_bound_reentry_closure,
    verify_exact_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_observation_bound_closure import HOLD
from scripts.aura_workcapsule_stale_exact_reentry import (
    admit_stale_safe_exact_reentry,
    verify_stale_safe_exact_reentry,
)

VERSION = "AURA_WORKCAPSULE_STALE_EXACT_OBSERVATION_OWNER_REDUCTION_V1"
GENERAL_EXACT_PREFIX = "GENERAL_EXACT_"
STALE_SAFE_PREFIX = "STALE_SAFE_"
SOURCE_OBSERVATION_MISSING = "SOURCE_OBSERVATION_MISSING"
REJECTED_CURRENTNESS_MUST_HOLD = "REJECTED_CURRENTNESS_OBSERVATION_CLOSURE_MUST_HOLD"


def verify_stale_exact_observation_owner_reduction(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    receipt: dict[str, Any],
) -> list[str]:
    """Verify exact raw-input binding first, then the rejected-currentness leaf."""
    general = verify_exact_observation_bound_reentry_closure(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=candidate_graph_witness,
        receipt=receipt,
    )
    violations = [GENERAL_EXACT_PREFIX + item for item in general]
    if general:
        return list(dict.fromkeys(violations))

    source_observation = receipt.get("source_observation")
    if not isinstance(source_observation, dict):
        violations.append(SOURCE_OBSERVATION_MISSING)
        return violations

    stale = verify_stale_safe_exact_reentry(
        source_observation_receipt=source_observation,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    violations.extend(STALE_SAFE_PREFIX + item for item in stale)
    if receipt.get("closure_status") != HOLD:
        violations.append(REJECTED_CURRENTNESS_MUST_HOLD)
    return list(dict.fromkeys(violations))


def admit_stale_exact_observation_owner_reduction(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit only the exact raw-input-bound STALE/UNKNOWN HOLD consequence."""
    violations = verify_stale_exact_observation_owner_reduction(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        observed_graph_witness=observed_graph_witness,
        candidate_graph_witness=candidate_graph_witness,
        receipt=receipt,
    )
    if violations:
        raise ValueError(
            "stale exact observation owner reduction failed: " + ",".join(violations)
        )

    general = admit_exact_observation_bound_reentry_closure(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=candidate_graph_witness,
        receipt=receipt,
    )
    stale = admit_stale_safe_exact_reentry(
        source_observation_receipt=receipt["source_observation"],
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )

    return {
        "version": VERSION,
        "general_raw_input_owner_consumed": True,
        "stale_safety_owner_consumed": True,
        "raw_replay_reimplemented_by_child": False,
        "exact_observation_bound_input_reproduction": general[
            "exact_observation_bound_input_reproduction"
        ],
        "rejected_currentness_path": True,
        "closure_status": receipt["closure_status"],
        "observation_bound_receipt_identity": receipt["receipt_identity"],
        "source_observation_identity": receipt["source_observation_identity"],
        "reentry_receipt_identity": receipt["reentry_receipt_identity"],
        "minimum_reentry_scope": stale["minimum_reentry_scope"],
        "minimum_reentry_source_keys": stale["minimum_reentry_source_keys"],
        "rejected_dependency_keys": stale["rejected_dependency_keys"],
        "reentry_required": stale["reentry_required"],
        "source_currentness_minted": False,
        "stale_observed_bytes_bound_to_source_generation": False,
        "unknown_identity_guessed": False,
        "producer_identity_authenticated": False,
        "graph_witness_producer_authenticated": False,
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

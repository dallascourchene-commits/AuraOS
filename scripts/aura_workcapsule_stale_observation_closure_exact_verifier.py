#!/usr/bin/env python3
"""Raw-input exact verification for rejected-currentness observation-bound closure.

PR516 derives a closure candidate from raw source-currentness evidence and removes
caller-prepared candidate bindings. Its receipt verifier establishes internal
self-consistency. PR517 proves that an exact O8 decision driven by STALE/UNKNOWN
source evidence cannot mint source CURRENTness.

This D0 membrane composes those consequences. It reruns the source-observation
owner from the pinned raw inputs, re-proves PR517 stale-safe exact re-entry, then
recompiles PR516 from the same raw inputs and requires complete canonical equality
with the supplied observation-bound closure receipt.

The result proves deterministic raw-input reproduction only. It does not prove
producer identity, source CURRENTness, semantic truth, a source-to-graph node map,
review/mutation/execution authority, or any external effect.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_closure import (
    HOLD,
    compile_observation_bound_reentry_closure,
    verify_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_source_reentry_observation import compile_source_reentry_observations
from scripts.aura_workcapsule_stale_exact_reentry import verify_stale_safe_exact_reentry

VERSION = "AURA_WORKCAPSULE_STALE_OBSERVATION_CLOSURE_EXACT_VERIFIER_V1"
OBSERVATION_CLOSURE_INVALID_PREFIX = "OBSERVATION_CLOSURE_"
STALE_SAFE_REENTRY_INVALID_PREFIX = "STALE_SAFE_REENTRY_"
RAW_INPUT_CLOSURE_MISMATCH = "OBSERVATION_CLOSURE_NOT_EXACT_RAW_INPUT_REPRODUCTION"
REJECTED_CURRENTNESS_MUST_HOLD = "REJECTED_CURRENTNESS_OBSERVATION_CLOSURE_MUST_HOLD"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def verify_stale_observation_closure_exact_reproduction(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> list[str]:
    """Verify one rejected-currentness closure against the exact raw evidence inputs."""
    violations = [
        OBSERVATION_CLOSURE_INVALID_PREFIX + item
        for item in verify_observation_bound_reentry_closure(closure_receipt)
    ]

    expected_observation = compile_source_reentry_observations(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
    )

    violations.extend(
        STALE_SAFE_REENTRY_INVALID_PREFIX + item
        for item in verify_stale_safe_exact_reentry(
            source_observation_receipt=expected_observation,
            previous_binding=previous_binding,
            observed_graph_witness=observed_graph_witness,
            reentry_receipt=reentry_receipt,
        )
    )

    expected_closure = compile_observation_bound_reentry_closure(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=candidate_graph_witness,
    )

    if expected_closure.get("closure_status") != HOLD:
        violations.append(REJECTED_CURRENTNESS_MUST_HOLD)
    if _canonical_bytes(closure_receipt) != _canonical_bytes(expected_closure):
        violations.append(RAW_INPUT_CLOSURE_MISMATCH)

    return list(dict.fromkeys(violations))


def admit_stale_observation_closure_exact_reproduction(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Return a narrow raw-input reproduction witness or fail closed."""
    violations = verify_stale_observation_closure_exact_reproduction(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        observed_graph_witness=observed_graph_witness,
        candidate_graph_witness=candidate_graph_witness,
        closure_receipt=closure_receipt,
    )
    if violations:
        raise ValueError(
            "stale observation-bound closure exact reproduction failed: " + ",".join(violations)
        )

    source_observation = closure_receipt["source_observation"]
    return {
        "version": VERSION,
        "raw_input_bound_reproduction": True,
        "rejected_currentness_path": True,
        "closure_status": closure_receipt["closure_status"],
        "previous_binding_identity": closure_receipt["previous_binding_identity"],
        "reentry_receipt_identity": closure_receipt["reentry_receipt_identity"],
        "source_observation_identity": closure_receipt["source_observation_identity"],
        "observation_closure_receipt_identity": closure_receipt["receipt_identity"],
        "reentry_required": True,
        "source_currentness_minted": False,
        "stale_observed_bytes_bound_to_source_generation": False,
        "unknown_identity_guessed": False,
        "producer_identity_authenticated": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "semantic_truth_minted": False,
        "rejected_source_observation_count": sum(
            1
            for row in source_observation.get("source_observations", [])
            if row.get("currentness") == "STALE"
        )
        + sum(
            1
            for row in source_observation.get("unresolved_prior_sources", [])
            if row.get("currentness") in {"STALE", "UNKNOWN"}
        ),
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

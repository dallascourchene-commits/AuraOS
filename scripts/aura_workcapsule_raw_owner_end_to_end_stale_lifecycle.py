#!/usr/bin/env python3
"""End-to-end raw-owner-bound stale WorkCapsule lifecycle.

PR522 proves rejected-currentness re-entry against raw source-owner evidence, but its
public boundary still accepts a candidate O8 re-entry receipt. PR521 proves a stale
observation-bound closure is an exact reproduction of pinned raw inputs, but likewise
accepts that intermediate O8 receipt.

This D0 membrane removes the intermediate caller-controlled object. It derives the
canonical O8 receipt internally from raw owner evidence, proves PR522 stale-safe
admission on that exact receipt, compiles the observation-bound closure, and uses
PR521 as the final raw-input replay oracle.

No source CURRENTness, producer identity, semantic truth, review/mutation/execution
or external effect is minted by this composition.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_closure import (
    HOLD,
    compile_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_raw_owner_stale_safe_reentry import (
    admit_raw_owner_stale_safe_exact_reentry,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import (
    compile_expected_source_bound_reentry,
)
from scripts.aura_workcapsule_stale_observation_closure_exact_verifier import (
    admit_stale_observation_closure_exact_reproduction,
)

VERSION = "AURA_WORKCAPSULE_RAW_OWNER_END_TO_END_STALE_LIFECYCLE_V1"
LIFECYCLE_MISMATCH = "RAW_OWNER_STALE_LIFECYCLE_NOT_EXACT_REPRODUCTION"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def compile_raw_owner_end_to_end_stale_lifecycle(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    """Compile the canonical rejected-currentness lifecycle with no caller O8 slot."""
    source_observation, reentry_receipt = compile_expected_source_bound_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
    )

    stale_safe_admission = admit_raw_owner_stale_safe_exact_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )

    closure_receipt = compile_observation_bound_reentry_closure(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=candidate_graph_witness,
    )

    closure_reproduction = admit_stale_observation_closure_exact_reproduction(
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

    if closure_receipt.get("closure_status") != HOLD:
        raise ValueError("rejected-currentness end-to-end lifecycle must remain HOLD")

    return {
        "version": VERSION,
        "raw_owner_end_to_end_reproduction": True,
        "rejected_currentness_path": True,
        "source_observation_identity": source_observation["receipt_identity"],
        "derived_reentry_receipt_identity": reentry_receipt["receipt_identity"],
        "derived_reentry_receipt": reentry_receipt,
        "stale_safe_admission": stale_safe_admission,
        "closure_receipt": closure_receipt,
        "closure_reproduction": closure_reproduction,
        "closure_status": closure_receipt["closure_status"],
        "caller_reentry_receipt_accepted": False,
        "caller_source_observation_receipt_accepted": False,
        "caller_source_witnesses_accepted": False,
        "caller_candidate_binding_accepted": False,
        "source_currentness_minted": False,
        "stale_observed_bytes_bound_to_source_generation": False,
        "unknown_identity_guessed": False,
        "producer_identity_authenticated": False,
        "graph_witness_producer_authenticated": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "semantic_truth_minted": False,
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


def verify_raw_owner_end_to_end_stale_lifecycle(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    lifecycle_receipt: dict[str, Any],
) -> list[str]:
    """Recompile from raw inputs and require exact canonical lifecycle equality."""
    try:
        expected = compile_raw_owner_end_to_end_stale_lifecycle(
            root=root,
            codemap=codemap,
            anchor_manifest=anchor_manifest,
            witness_manifest=witness_manifest,
            previous_binding=previous_binding,
            observed_graph_witness=observed_graph_witness,
            candidate_graph_witness=candidate_graph_witness,
        )
    except ValueError as exc:
        return [f"RAW_OWNER_LIFECYCLE_RECOMPILE_FAILED:{exc}"]

    violations: list[str] = []
    if lifecycle_receipt.get("version") != VERSION:
        violations.append("UNSUPPORTED_VERSION")
    if lifecycle_receipt.get("caller_reentry_receipt_accepted") is not False:
        violations.append("CALLER_REENTRY_RECEIPT_ACCEPTED")
    if lifecycle_receipt.get("caller_source_observation_receipt_accepted") is not False:
        violations.append("CALLER_SOURCE_OBSERVATION_RECEIPT_ACCEPTED")
    if lifecycle_receipt.get("caller_source_witnesses_accepted") is not False:
        violations.append("CALLER_SOURCE_WITNESSES_ACCEPTED")
    if lifecycle_receipt.get("caller_candidate_binding_accepted") is not False:
        violations.append("CALLER_CANDIDATE_BINDING_ACCEPTED")
    if lifecycle_receipt.get("source_currentness_minted") is not False:
        violations.append("SOURCE_CURRENTNESS_MINTED")
    authority = lifecycle_receipt.get("authority")
    if not isinstance(authority, dict) or any(bool(value) for value in authority.values()):
        violations.append("AUTHORITY_MINTED")
    if _canonical_bytes(lifecycle_receipt) != _canonical_bytes(expected):
        violations.append(LIFECYCLE_MISMATCH)
    return list(dict.fromkeys(violations))


def admit_raw_owner_end_to_end_stale_lifecycle(**kwargs: Any) -> dict[str, Any]:
    """Return a narrow exact-reproduction witness or fail closed."""
    lifecycle_receipt = kwargs.pop("lifecycle_receipt")
    violations = verify_raw_owner_end_to_end_stale_lifecycle(
        lifecycle_receipt=lifecycle_receipt,
        **kwargs,
    )
    if violations:
        raise ValueError("raw-owner end-to-end stale lifecycle verification failed: " + ",".join(violations))
    return {
        "version": VERSION,
        "raw_owner_end_to_end_reproduction": True,
        "closure_status": lifecycle_receipt["closure_status"],
        "derived_reentry_receipt_identity": lifecycle_receipt["derived_reentry_receipt_identity"],
        "closure_receipt_identity": lifecycle_receipt["closure_receipt"]["receipt_identity"],
        "source_currentness_minted": False,
        "semantic_truth_minted": False,
        "authority": dict(lifecycle_receipt["authority"]),
    }

#!/usr/bin/env python3
"""Bind the live recursive target/raw-slice evidence to the exact PR556 causal POST world.

Objective anchors:
- PR562 owns the live current recursive target -> exact PR560 raw-source slice relation.
- repaired PR563 owns the deterministic Rust/Python raw-slice transport envelope and its
  source-coordinate consumer, while explicitly leaving the live PR560 -> PR556 causal join false.

PR556 is executable causal-owner substrate inherited through PR563, not a third objective anchor.
This membrane reruns PR556 from raw PRE/POST evidence, derives its exact POST source projection,
and requires that exact CURRENT source instance to equal the already-live PR562 raw slice.

The portable projection is verified by PR563 and must be an exact field projection of the same
PR562 raw-slice receipt. The semantic handle remains opaque structural evidence; raw bytes do not
mint semantic identity, repair correctness, producer authentication, review, or effect authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_k27_astge_portable_raw_slice_causal_handoff import (
    verify_portable_raw_slice_projection,
    verify_raw_slice_against_causal_post_source,
)
from scripts.aura_workcapsule_current_recursive_target_raw_slice_binding import (
    admit_current_recursive_target_raw_slice_binding,
    verify_current_recursive_target_raw_slice_binding,
)
from scripts.aura_workcapsule_raw_owner_derived_post_closure_transition import (
    admit_raw_owner_derived_post_closure_transition,
    verify_raw_owner_derived_post_closure_transition,
)
from scripts.aura_workcapsule_two_phase_source_bound_closure import derive_post_reentry_candidate

VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_RAW_SLICE_JOIN_V1"
STRUCTURAL_PREFIX = "LIVE_RAW_SLICE_"
TRANSPORT_PREFIX = "PORTABLE_TRANSPORT_"
CAUSAL_PREFIX = "CAUSAL_POST_"
HANDOFF_PREFIX = "CAUSAL_HANDOFF_"
RAW_PROJECTION_MISMATCH = "RAW_SLICE_PROJECTION_NOT_EXACT_RECEIPT_PROJECTION"
POST_PROJECTION_IDENTITY_MISMATCH = "POST_SOURCE_PROJECTION_IDENTITY_MISMATCH"
POST_CURRENT_WITNESS_CARDINALITY = "POST_CURRENT_SOURCE_WITNESS_CARDINALITY_NOT_ONE"
LIVE_SOURCE_INSTANCE_MISMATCH = "LIVE_RAW_SLICE_NOT_EXACT_CAUSAL_POST_SOURCE_INSTANCE"
LIVE_TARGET_SLICE_MISMATCH = "LIVE_TARGET_SLICE_NOT_EXACT_PORTABLE_PROJECTION"
CAUSAL_TRANSITION_NOT_EXACT = "CAUSAL_TRANSITION_NOT_EXACT_HOLD_TO_CLOSED"


def _projection_matches_raw_receipt(
    raw_slice_receipt: dict[str, Any], raw_slice_projection: dict[str, Any]
) -> bool:
    if not isinstance(raw_slice_projection, dict):
        return False
    payload = raw_slice_projection.get("payload")
    if not isinstance(payload, dict):
        return False
    pairs = {
        "raw_slice_version": "version",
        "projection_payload_sha256": "projection_payload_sha256",
        "file_id": "file_id",
        "relative_path": "relative_path",
        "source_generation": "source_generation",
        "full_source_sha256_hex": "full_source_sha256_hex",
        "full_source_byte_len": "full_source_byte_len",
        "target_byte_start": "target_byte_start",
        "target_byte_end": "target_byte_end",
        "target_slice_byte_len": "target_slice_byte_len",
        "target_slice_sha256_hex": "target_slice_sha256_hex",
        "selected_target_semantic_handle_digest_hex": (
            "selected_target_semantic_handle_digest_hex"
        ),
        "portable_target_bound_to_exact_current_raw_slice": (
            "portable_target_bound_to_exact_current_raw_slice"
        ),
        "source_currentness_revalidated_at_materialization": (
            "source_currentness_revalidated_at_materialization"
        ),
        "synthetic_record_is_materialization_coordinate_only": (
            "synthetic_record_is_materialization_coordinate_only"
        ),
        "storage_node_identity_minted": "storage_node_identity_minted",
        "semantic_handle_carried_from_portable_owner": (
            "semantic_handle_carried_from_portable_owner"
        ),
        "semantic_handle_derived_from_raw_slice": "semantic_handle_derived_from_raw_slice",
        "semantic_identity_proven_by_raw_slice": "semantic_identity_proven_by_raw_slice",
        "producer_authenticated": "producer_authenticated",
        "runtime_name_resolution_proven": "runtime_name_resolution_proven",
        "call_graph_proven": "call_graph_proven",
        "semantic_patch_correctness_proven": "semantic_patch_correctness_proven",
        "b_minus_approved": "b_minus_approved",
        "review_authorized": "review_authorized",
        "mutation_authorized": "mutation_authorized",
        "execution_authorized": "execution_authorized",
        "commit_authorized": "commit_authorized",
        "merge_authorized": "merge_authorized",
        "promotion_authorized": "promotion_authorized",
        "provider_effect_authorized": "provider_effect_authorized",
        "public_effect_authorized": "public_effect_authorized",
        "human_authority": "human_authority",
    }
    return all(
        key in raw_slice_receipt and payload.get(projected) == raw_slice_receipt[key]
        for projected, key in pairs.items()
    )


def _causal_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "pre_root": kwargs["pre_root"],
        "pre_codemap": kwargs["pre_codemap"],
        "pre_anchor_manifest": kwargs["pre_anchor_manifest"],
        "pre_witness_manifest": kwargs["pre_witness_manifest"],
        "previous_binding": kwargs["previous_binding"],
        "pre_graph_witness": kwargs["pre_graph_witness"],
        "post_root": kwargs["post_root"],
        "post_codemap": kwargs["post_codemap"],
        "post_anchor_manifest": kwargs["post_anchor_manifest"],
        "post_witness_manifest": kwargs["post_witness_manifest"],
        "post_graph_witness": kwargs["post_graph_witness"],
    }


def _derive_exact_post_projection(kwargs: dict[str, Any]) -> dict[str, Any]:
    projection, _candidate = derive_post_reentry_candidate(
        post_root=kwargs["post_root"],
        post_codemap=kwargs["post_codemap"],
        post_anchor_manifest=kwargs["post_anchor_manifest"],
        post_witness_manifest=kwargs["post_witness_manifest"],
        previous_binding=kwargs["previous_binding"],
        post_graph_witness=kwargs["post_graph_witness"],
    )
    return projection


def _one_current_post_witness(projection: dict[str, Any]) -> dict[str, Any] | None:
    rows = [
        row
        for row in projection.get("o7_source_witnesses", [])
        if isinstance(row, dict) and row.get("currentness") == "CURRENT"
    ]
    if len(rows) != 1:
        return None
    return rows[0]


def verify_live_causal_raw_slice_join(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
    raw_slice_projection: dict[str, Any],
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
    """Reprove both parents and admit only one exact live source-instance conjunction."""
    kwargs = locals()
    structural_violations = verify_current_recursive_target_raw_slice_binding(
        scoped_target_inputs=scoped_target_inputs,
        higher_owner_projection=higher_owner_projection,
        raw_slice_receipt=raw_slice_receipt,
    )
    violations = [STRUCTURAL_PREFIX + item for item in structural_violations]

    transport_violations = verify_portable_raw_slice_projection(raw_slice_projection)
    violations.extend(TRANSPORT_PREFIX + item for item in transport_violations)
    if not transport_violations and not _projection_matches_raw_receipt(
        raw_slice_receipt, raw_slice_projection
    ):
        violations.append(RAW_PROJECTION_MISMATCH)

    causal_violations = verify_raw_owner_derived_post_closure_transition(
        **_causal_kwargs(kwargs)
    )
    violations.extend(CAUSAL_PREFIX + item for item in causal_violations)
    if violations:
        return list(dict.fromkeys(violations))

    structural = admit_current_recursive_target_raw_slice_binding(
        scoped_target_inputs=scoped_target_inputs,
        higher_owner_projection=higher_owner_projection,
        raw_slice_receipt=raw_slice_receipt,
    )
    causal = admit_raw_owner_derived_post_closure_transition(**_causal_kwargs(kwargs))
    if causal.get("pre_closure_status") != "HOLD" or causal.get("post_closure_status") != "CLOSED":
        violations.append(CAUSAL_TRANSITION_NOT_EXACT)

    post_projection = _derive_exact_post_projection(kwargs)
    if post_projection.get("receipt_identity") != causal.get(
        "post_source_projection_receipt_identity"
    ):
        violations.append(POST_PROJECTION_IDENTITY_MISMATCH)
    witness = _one_current_post_witness(post_projection)
    if witness is None:
        violations.append(POST_CURRENT_WITNESS_CARDINALITY)
        return list(dict.fromkeys(violations))

    handoff_violations = verify_raw_slice_against_causal_post_source(
        raw_slice_projection=raw_slice_projection,
        post_source_witness=witness,
    )
    violations.extend(HANDOFF_PREFIX + item for item in handoff_violations)

    live_source = (
        structural["dependency_key"].get("file_id"),
        structural["dependency_key"].get("relative_path"),
        structural["source_generation"],
        structural["full_source_sha256_hex"],
        structural["full_source_byte_len"],
    )
    causal_source = (
        witness.get("file_id"),
        witness.get("relative_path"),
        witness.get("source_generation"),
        witness.get("source_sha256"),
        witness.get("source_byte_len"),
    )
    if live_source != causal_source:
        violations.append(LIVE_SOURCE_INSTANCE_MISMATCH)

    payload = raw_slice_projection["payload"]
    live_target = (
        structural["target_byte_start"],
        structural["target_byte_end"],
        structural["target_slice_byte_len"],
        structural["target_slice_sha256_hex"],
        structural["selected_target_semantic_handle_digest_hex"],
    )
    portable_target = (
        payload["target_byte_start"],
        payload["target_byte_end"],
        payload["target_slice_byte_len"],
        payload["target_slice_sha256_hex"],
        payload["selected_target_semantic_handle_digest_hex"],
    )
    if live_target != portable_target:
        violations.append(LIVE_TARGET_SLICE_MISMATCH)
    return list(dict.fromkeys(violations))


def admit_live_causal_raw_slice_join(**kwargs: Any) -> dict[str, Any]:
    violations = verify_live_causal_raw_slice_join(**kwargs)
    if violations:
        raise ValueError("live causal raw-slice join failed: " + ",".join(violations))

    structural = admit_current_recursive_target_raw_slice_binding(
        scoped_target_inputs=kwargs["scoped_target_inputs"],
        higher_owner_projection=kwargs["higher_owner_projection"],
        raw_slice_receipt=kwargs["raw_slice_receipt"],
    )
    causal = admit_raw_owner_derived_post_closure_transition(**_causal_kwargs(kwargs))
    post_projection = _derive_exact_post_projection(kwargs)
    witness = _one_current_post_witness(post_projection)
    assert witness is not None
    payload = kwargs["raw_slice_projection"]["payload"]
    return {
        "version": VERSION,
        "live_recursive_target_raw_slice_reproved": True,
        "portable_raw_slice_transport_reproved": True,
        "causal_post_owner_reproved_from_raw_evidence": True,
        "live_recursive_raw_slice_bound_to_exact_causal_post": True,
        "same_exact_post_source_instance_proven": True,
        "same_exact_raw_target_slice_proven": True,
        "post_source_projection_receipt_identity": post_projection["receipt_identity"],
        "causal_post_closure_receipt_identity": causal["post_o10_closure_receipt_identity"],
        "dependency_key": dict(structural["dependency_key"]),
        "source_generation": structural["source_generation"],
        "full_source_sha256_hex": structural["full_source_sha256_hex"],
        "full_source_byte_len": structural["full_source_byte_len"],
        "target_byte_start": structural["target_byte_start"],
        "target_byte_end": structural["target_byte_end"],
        "target_slice_byte_len": structural["target_slice_byte_len"],
        "target_slice_sha256_hex": structural["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": payload[
            "selected_target_semantic_handle_digest_hex"
        ],
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "raw_slice_projection_producer_authenticated": False,
        "source_observation_producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "b_minus_approved": False,
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

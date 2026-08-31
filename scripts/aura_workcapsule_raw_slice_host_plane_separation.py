#!/usr/bin/env python3
"""Keep exact PR560 raw-slice evidence below PR559 host/control-plane rank."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_workcapsule_temporal_host_observation_admission import (
    admit_temporal_host_observation_admission,
    verify_temporal_host_observation_admission,
)

VERSION = "AURA_WORKCAPSULE_RAW_SLICE_HOST_PLANE_SEPARATION_V1"
RAW_SLICE_VERSION = "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_V1"

RAW_SLICE_FIELDS = (
    "version", "projection_payload_sha256", "file_id", "relative_path",
    "source_generation", "full_source_sha256_hex", "full_source_byte_len",
    "target_byte_start", "target_byte_end", "target_slice_byte_len",
    "target_slice_sha256_hex", "selected_target_semantic_handle_digest_hex",
    "portable_target_bound_to_exact_current_raw_slice",
    "source_currentness_revalidated_at_materialization",
    "synthetic_record_is_materialization_coordinate_only",
    "storage_node_identity_minted", "semantic_handle_carried_from_portable_owner",
    "semantic_handle_derived_from_raw_slice", "semantic_identity_proven_by_raw_slice",
    "producer_authenticated", "runtime_name_resolution_proven", "call_graph_proven",
    "semantic_patch_correctness_proven", "b_minus_approved", "review_authorized",
    "mutation_authorized", "execution_authorized", "commit_authorized",
    "merge_authorized", "promotion_authorized", "provider_effect_authorized",
    "public_effect_authorized", "human_authority",
)
_TRUE_FLAGS = (
    "portable_target_bound_to_exact_current_raw_slice",
    "source_currentness_revalidated_at_materialization",
    "synthetic_record_is_materialization_coordinate_only",
    "semantic_handle_carried_from_portable_owner",
)
_FALSE_FLAGS = (
    "storage_node_identity_minted", "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice", "producer_authenticated",
    "runtime_name_resolution_proven", "call_graph_proven",
    "semantic_patch_correctness_proven", "b_minus_approved", "review_authorized",
    "mutation_authorized", "execution_authorized", "commit_authorized",
    "merge_authorized", "promotion_authorized", "provider_effect_authorized",
    "public_effect_authorized", "human_authority",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def verify_raw_slice_receipt(raw_slice_receipt: Any) -> list[str]:
    """Validate the closed PR560 evidence shape without authenticating its producer."""
    if not isinstance(raw_slice_receipt, Mapping):
        return ["RAW_SLICE_NOT_MAPPING"]
    if set(raw_slice_receipt) != set(RAW_SLICE_FIELDS):
        return ["RAW_SLICE_FIELDS_MISMATCH"]

    violations: list[str] = []
    if raw_slice_receipt.get("version") != RAW_SLICE_VERSION:
        violations.append("RAW_SLICE_VERSION_MISMATCH")
    for field in (
        "projection_payload_sha256", "full_source_sha256_hex",
        "target_slice_sha256_hex", "selected_target_semantic_handle_digest_hex",
    ):
        if not _is_sha256(raw_slice_receipt.get(field)):
            violations.append("RAW_SLICE_SHA256_INVALID:" + field)
    if not isinstance(raw_slice_receipt.get("relative_path"), str) or not raw_slice_receipt["relative_path"]:
        violations.append("RAW_SLICE_PATH_INVALID")
    for field in (
        "file_id", "source_generation", "full_source_byte_len", "target_byte_start",
        "target_byte_end", "target_slice_byte_len",
    ):
        value = raw_slice_receipt.get(field)
        if type(value) is not int or value < 0:
            violations.append("RAW_SLICE_INTEGER_INVALID:" + field)
    start = raw_slice_receipt.get("target_byte_start")
    end = raw_slice_receipt.get("target_byte_end")
    length = raw_slice_receipt.get("target_slice_byte_len")
    if type(start) is int and type(end) is int and type(length) is int:
        if start >= end:
            violations.append("RAW_SLICE_EMPTY_OR_REVERSED_SPAN")
        elif end - start != length:
            violations.append("RAW_SLICE_LENGTH_SPAN_MISMATCH")
    for field in _TRUE_FLAGS:
        if raw_slice_receipt.get(field) is not True:
            violations.append("RAW_SLICE_REQUIRED_TRUE:" + field)
    for field in _FALSE_FLAGS:
        if raw_slice_receipt.get(field) is not False:
            violations.append("RAW_SLICE_CEILING_VIOLATED:" + field)
    return list(dict.fromkeys(violations))


def verify_raw_slice_host_plane_separation(
    *,
    raw_slice_receipt: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> list[str]:
    raw_violations = verify_raw_slice_receipt(raw_slice_receipt)
    if raw_violations:
        return raw_violations
    host_violations = verify_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    return ["HOST_" + item for item in host_violations]


def admit_raw_slice_host_plane_separation(
    *,
    raw_slice_receipt: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> dict[str, Any]:
    """Compose the evidence planes while forbidding raw-slice -> host-rank substitution."""
    violations = verify_raw_slice_host_plane_separation(
        raw_slice_receipt=raw_slice_receipt,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError("raw-slice/host-plane separation failed: " + ",".join(violations))

    host = admit_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    raw_digest = hashlib.sha256(_canonical_bytes(dict(raw_slice_receipt))).hexdigest()
    out: dict[str, Any] = {
        "version": VERSION,
        "raw_slice_receipt_digest": raw_digest,
        "raw_slice_exact_current_local_evidence_validated": True,
        "raw_slice_source_currentness_revalidated": True,
        "raw_slice_semantic_identity_proven": False,
        "raw_slice_producer_authenticated": False,
        "raw_slice_promoted_to_host_rank": False,
        "host_gate_states": dict(host["host_gate_states"]),
        "host_disposition": host["disposition"],
        "host_observation_set_complete": host["host_observation_set_complete"],
        "host_resolution_required_for_rank_change": True,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_minted": False,
        "authority": {
            "review_authorized": False, "execution_authorized": False,
            "commit_authorized": False, "merge_authorized": False,
            "promotion_authorized": False, "provider_effect_authorized": False,
            "public_effect_authorized": False, "human_authority": False,
        },
    }
    out["receipt_identity"] = {
        "kind": "DIGEST", "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out

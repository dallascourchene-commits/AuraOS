#!/usr/bin/env python3
"""Keep exact raw-slice evidence below host rank under the causal O10 temporal owner.

PR566 owns the closed PR560 raw-slice evidence validator and the concrete rule that
local exact bytes/currentness cannot impersonate host observations or resolutions.
PR567 owns the causally correct PR556 PRE->POST O10 temporal substrate beneath the
unchanged PR559 five-gate host lattice.

This D0 membrane updates only the owner generation beneath the no-cross-cast rule.
It does not mint host resolver trust, host authority, semantic correctness, producer
identity, or any execution/effect authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_workcapsule_raw_slice_host_plane_separation import verify_raw_slice_receipt
from scripts.aura_workcapsule_causal_temporal_host_observation_admission import (
    admit_causal_temporal_host_observation_admission,
    verify_causal_temporal_host_observation_admission,
)

VERSION = "AURA_WORKCAPSULE_CAUSAL_RAW_SLICE_HOST_PLANE_SEPARATION_V1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_causal_raw_slice_host_plane_separation(
    *,
    raw_slice_receipt: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> list[str]:
    raw_violations = verify_raw_slice_receipt(raw_slice_receipt)
    if raw_violations:
        return raw_violations
    if raw_slice_receipt["target_byte_end"] > raw_slice_receipt["full_source_byte_len"]:
        return ["RAW_SLICE_SPAN_EXCEEDS_FULL_SOURCE"]
    host_violations = verify_causal_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    return ["CAUSAL_HOST_" + item for item in host_violations]


def admit_causal_raw_slice_host_plane_separation(
    *,
    raw_slice_receipt: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> dict[str, Any]:
    """Compose PR566 local evidence separation with PR567 causal host ownership."""
    violations = verify_causal_raw_slice_host_plane_separation(
        raw_slice_receipt=raw_slice_receipt,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError("causal raw-slice/host-plane separation failed: " + ",".join(violations))

    host = admit_causal_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if host.get("causal_temporal_owner_reproved") is not True:
        raise ValueError("CAUSAL_TEMPORAL_OWNER_NOT_REPROVED")
    if host.get("pre_reentry_receipt_reused_for_post_o10") is not True:
        raise ValueError("CAUSAL_PRE_REENTRY_NOT_REUSED")
    if host.get("fresh_post_reentry_receipt_substituted") is not False:
        raise ValueError("CAUSAL_FRESH_POST_REENTRY_SUBSTITUTED")
    if host.get("local_evidence_promoted_to_host_rank") is not False:
        raise ValueError("LOCAL_EVIDENCE_PROMOTED_TO_HOST_RANK")

    raw_digest = hashlib.sha256(_canonical_bytes(dict(raw_slice_receipt))).hexdigest()
    out: dict[str, Any] = {
        "version": VERSION,
        "raw_slice_receipt_digest": raw_digest,
        "raw_slice_exact_current_local_evidence_validated": True,
        "raw_slice_source_currentness_revalidated": True,
        "raw_slice_span_within_full_source": True,
        "raw_slice_semantic_identity_proven": False,
        "raw_slice_producer_authenticated": False,
        "raw_slice_promoted_to_host_rank": False,
        "causal_temporal_owner_reproved": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "pre_closure_status": host["pre_closure_status"],
        "post_closure_status": host["post_closure_status"],
        "post_closure_receipt_identity": host["post_closure_receipt_identity"],
        "host_gate_states": dict(host["host_gate_states"]),
        "host_disposition": host["disposition"],
        "host_observation_set_complete": host["host_observation_set_complete"],
        "host_resolution_required_for_rank_change": True,
        "host_observation_authority_proven": False,
        "resolver_trust_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_minted": False,
        "source_currentness_minted": False,
        "producer_identity_authenticated": False,
        "authority": {
            "review_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out

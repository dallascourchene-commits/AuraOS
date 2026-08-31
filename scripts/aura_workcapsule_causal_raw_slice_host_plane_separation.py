#!/usr/bin/env python3
"""Keep exact raw-slice evidence below the causal-current host observation plane.

PR566 owns the closed PR560 raw-slice evidence validator and the proof-plane
separation law. PR567 owns the current causal temporal substrate beneath the
unchanged PR559 five-gate host lattice. This child composes those owners without
redefining either raw-slice validity or host-resolution semantics.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from scripts.aura_workcapsule_causal_temporal_host_observation_admission import (
    admit_causal_temporal_host_observation_admission,
    verify_causal_temporal_host_observation_admission,
)
from scripts.aura_workcapsule_raw_slice_host_plane_separation import (
    _canonical_bytes,
    verify_raw_slice_receipt,
)

VERSION = "AURA_WORKCAPSULE_CAUSAL_RAW_SLICE_HOST_PLANE_SEPARATION_V1"


def verify_causal_raw_slice_host_plane_separation(
    *,
    raw_slice_receipt: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> list[str]:
    """Verify PR566 local evidence and PR567 causal host admission independently."""
    raw_violations = verify_raw_slice_receipt(raw_slice_receipt)
    if raw_violations:
        return ["RAW_SLICE_" + item for item in raw_violations]
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
    """Compose exact local bytes with causal-current host state without rank promotion."""
    violations = verify_causal_raw_slice_host_plane_separation(
        raw_slice_receipt=raw_slice_receipt,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError(
            "causal raw-slice/host-plane separation failed: " + ",".join(violations)
        )

    host = admit_causal_temporal_host_observation_admission(
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
        "causal_temporal_owner_reproved": bool(host["causal_temporal_owner_reproved"]),
        "pre_reentry_receipt_reused_for_post_o10": bool(
            host["pre_reentry_receipt_reused_for_post_o10"]
        ),
        "fresh_post_reentry_receipt_substituted": bool(
            host["fresh_post_reentry_receipt_substituted"]
        ),
        "host_gate_states": dict(host["host_gate_states"]),
        "host_disposition": host["disposition"],
        "host_observation_set_complete": bool(host["host_observation_set_complete"]),
        "host_resolution_required_for_rank_change": True,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_minted": False,
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

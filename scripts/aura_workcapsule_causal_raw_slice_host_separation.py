#!/usr/bin/env python3
"""Preserve PR566 raw-slice proof-plane separation under PR567's causal host owner.

PR566 proved that exact current raw-slice evidence is local evidence and cannot itself
satisfy PR559 host/control-plane gates. PR567 later replaced the temporal owner beneath
those gates with the stronger causally correct PR556 O10 lifecycle. This membrane keeps
PR566 as the canonical raw-slice evidence validator while delegating every host state to
PR567. It intentionally does not rerun PR566's older temporal owner.

Raw-slice validity, causal temporal closure, host observation completeness, resolver trust,
semantic correctness, and effect authority remain independent claims.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_workcapsule_causal_temporal_host_observation_admission import (
    admit_causal_temporal_host_observation_admission,
    verify_causal_temporal_host_observation_admission,
)
from scripts.aura_workcapsule_raw_slice_host_plane_separation import verify_raw_slice_receipt

VERSION = "AURA_WORKCAPSULE_CAUSAL_RAW_SLICE_HOST_SEPARATION_V1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def verify_causal_raw_slice_host_separation(
    *,
    raw_slice_receipt: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> list[str]:
    """Verify local raw-slice evidence and causal host evidence on separate planes."""
    raw_violations = verify_raw_slice_receipt(raw_slice_receipt)
    if raw_violations:
        return list(raw_violations)
    causal_violations = verify_causal_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    return ["CAUSAL_HOST_" + item for item in causal_violations]


def admit_causal_raw_slice_host_separation(
    *,
    raw_slice_receipt: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> dict[str, Any]:
    """Emit a causal-host/current-raw-slice conjunction without rank promotion."""
    violations = verify_causal_raw_slice_host_separation(
        raw_slice_receipt=raw_slice_receipt,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError(
            "causal raw-slice host separation failed: " + ",".join(violations)
        )

    host = admit_causal_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    raw_digest = hashlib.sha256(_canonical_bytes(dict(raw_slice_receipt))).hexdigest()
    out: dict[str, Any] = {
        "version": VERSION,
        "raw_slice_contract_owner": "PR566.verify_raw_slice_receipt",
        "causal_host_owner": "PR567.admit_causal_temporal_host_observation_admission",
        "raw_slice_receipt_digest": raw_digest,
        "raw_slice_exact_current_local_evidence_validated": True,
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
        "raw_slice_promoted_to_host_rank": False,
        "raw_slice_used_as_host_resolution": False,
        "raw_slice_semantic_identity_proven": False,
        "raw_slice_producer_authenticated": False,
        "host_observation_authority_proven": False,
        "host_resolver_trust_proven": False,
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

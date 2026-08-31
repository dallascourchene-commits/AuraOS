#!/usr/bin/env python3
"""Bind PR563 portable raw-slice evidence to the exact PR567/PR556 causal POST phase.

PR563 owns deterministic cross-runtime raw-slice projection verification and source-coordinate
comparison. PR567 owns the current PR556 causal O10 lifecycle beneath the PR559 host lattice.
This child closes only the missing relation: the portable raw-slice envelope must match exactly
one CURRENT source witness derived inside the same POST phase that produces the admitted O10.

Host observations remain separately resolver-owned and non-authorizing. Raw bytes do not derive
semantic identity, semantic correctness, producer authentication, or any effect authority.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from scripts.aura_k27_astge_portable_raw_slice_causal_handoff import (
    admit_raw_slice_causal_handoff,
    verify_portable_raw_slice_projection,
    verify_raw_slice_against_causal_post_source,
)
from scripts.aura_workcapsule_causal_temporal_host_observation_admission import (
    HostObservationResolverV1,
    admit_causal_temporal_host_observation_admission,
    verify_causal_temporal_host_observation_admission,
)
from scripts.aura_workcapsule_raw_owner_derived_post_closure_transition import (
    _derive_transition_inputs,
)
from scripts.aura_workcapsule_temporal_host_observation_admission import _canonical_bytes

VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_RAW_SLICE_HOST_V1"


def _derive_live_post_projection(temporal_kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """Re-enter the exact PR556 derivation path and return its POST source projection."""
    _pre, post_projection, _candidate, _closure = _derive_transition_inputs(**dict(temporal_kwargs))
    if post_projection.get("source_generation_domain") != "SOURCE":
        raise ValueError("LIVE_POST_SOURCE_GENERATION_DOMAIN_LOST")
    witnesses = post_projection.get("o7_source_witnesses")
    if not isinstance(witnesses, list) or not witnesses:
        raise ValueError("LIVE_POST_SOURCE_WITNESSES_MISSING")
    return post_projection


def _select_unique_live_witness(
    *, raw_slice_projection: dict[str, Any], post_projection: dict[str, Any]
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for witness in post_projection["o7_source_witnesses"]:
        if not isinstance(witness, dict):
            continue
        if not verify_raw_slice_against_causal_post_source(
            raw_slice_projection=raw_slice_projection,
            post_source_witness=witness,
        ):
            matches.append(witness)
    if not matches:
        raise ValueError("NO_LIVE_CAUSAL_POST_SOURCE_MATCH")
    if len(matches) != 1:
        raise ValueError("AMBIGUOUS_LIVE_CAUSAL_POST_SOURCE_MATCH")
    return matches[0]


def verify_live_causal_raw_slice_host(
    *,
    raw_slice_projection: dict[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: HostObservationResolverV1 | None = None,
    **temporal_kwargs: Any,
) -> list[str]:
    """Verify one exact raw-slice envelope belongs to the live causal POST source phase."""
    raw_violations = verify_portable_raw_slice_projection(raw_slice_projection)
    if raw_violations:
        return ["RAW_SLICE_" + item for item in raw_violations]

    temporal_violations = verify_causal_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if temporal_violations:
        return ["CAUSAL_HOST_" + item for item in temporal_violations]

    try:
        post_projection = _derive_live_post_projection(temporal_kwargs)
        _select_unique_live_witness(
            raw_slice_projection=raw_slice_projection,
            post_projection=post_projection,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return ["LIVE_CAUSAL_POST_BINDING_FAILED:" + str(exc)]
    return []


def admit_live_causal_raw_slice_host(
    *,
    raw_slice_projection: dict[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: HostObservationResolverV1 | None = None,
    **temporal_kwargs: Any,
) -> dict[str, Any]:
    violations = verify_live_causal_raw_slice_host(
        raw_slice_projection=raw_slice_projection,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError("live causal raw-slice host binding failed: " + ",".join(violations))

    post_projection = _derive_live_post_projection(temporal_kwargs)
    witness = _select_unique_live_witness(
        raw_slice_projection=raw_slice_projection,
        post_projection=post_projection,
    )
    handoff = admit_raw_slice_causal_handoff(
        raw_slice_projection=raw_slice_projection,
        post_source_witness=witness,
    )
    causal_host = admit_causal_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )

    payload = raw_slice_projection["payload"]
    out: dict[str, Any] = {
        "version": VERSION,
        "live_pr560_to_pr556_causal_slice_join_proven": True,
        "portable_raw_slice_projection_verified": handoff["raw_slice_projection_verified"],
        "live_post_source_coordinate_match_proven": handoff["post_source_coordinate_compatible"],
        "causal_post_owner_reproved_by_child": causal_host["causal_temporal_owner_reproved"],
        "post_source_projection_receipt_identity": post_projection["receipt_identity"],
        "matched_live_post_source_witness_ref": witness["witness_ref"],
        "raw_slice_projection_payload_sha256": raw_slice_projection["payload_sha256"],
        "file_id": handoff["file_id"],
        "relative_path": handoff["relative_path"],
        "source_generation": handoff["source_generation"],
        "full_source_sha256_hex": handoff["full_source_sha256_hex"],
        "full_source_byte_len": handoff["full_source_byte_len"],
        "target_byte_start": handoff["target_byte_start"],
        "target_byte_end": handoff["target_byte_end"],
        "target_slice_sha256_hex": handoff["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": handoff[
            "selected_target_semantic_handle_digest_hex"
        ],
        "causal_pre_closure_status": causal_host["pre_closure_status"],
        "causal_post_closure_status": causal_host["post_closure_status"],
        "causal_post_o10_receipt_identity": causal_host["post_closure_receipt_identity"],
        "pre_reentry_receipt_reused_for_post_o10": causal_host[
            "pre_reentry_receipt_reused_for_post_o10"
        ],
        "fresh_post_reentry_receipt_substituted": causal_host[
            "fresh_post_reentry_receipt_substituted"
        ],
        "host_disposition": causal_host["disposition"],
        "host_gate_states": dict(causal_host["host_gate_states"]),
        "host_observation_set_complete": causal_host["host_observation_set_complete"],
        "host_observation_authority_proven": False,
        "resolver_trust_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "raw_slice_promoted_to_host_rank": False,
        "semantic_handle_derived_from_raw_slice": payload[
            "semantic_handle_derived_from_raw_slice"
        ],
        "semantic_identity_proven_by_raw_slice": payload[
            "semantic_identity_proven_by_raw_slice"
        ],
        "producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
        "source_currentness_minted": False,
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

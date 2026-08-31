#!/usr/bin/env python3
"""Keep PR563 portable raw-slice transport below PR566 host/control-plane rank.

PR563 owns deterministic cross-runtime transport for exact PR560 raw-slice evidence.
PR566 owns the proof-plane law that exact local raw-slice evidence cannot satisfy or
impersonate PR559 host observations. This D0 membrane joins those owners without
creating another raw-slice or host-resolution schema.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_k27_astge_portable_raw_slice_causal_handoff import (
    verify_portable_raw_slice_projection,
)
from scripts.aura_workcapsule_raw_slice_host_plane_separation import (
    RAW_SLICE_FIELDS,
    admit_raw_slice_host_plane_separation,
    verify_raw_slice_host_plane_separation,
    verify_raw_slice_receipt,
)

VERSION = "AURA_WORKCAPSULE_PORTABLE_RAW_SLICE_HOST_PLANE_SEPARATION_V1"
PORTABLE_PREFIX = "PORTABLE_"
RAW_VIEW_PREFIX = "RAW_VIEW_"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def portable_projection_to_raw_slice_receipt(
    raw_slice_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive the exact PR560-shaped receipt view already carried inside PR563.

    This is a projection/view operation only. It does not authenticate the portable
    envelope producer and does not derive raw bytes, semantic identity, or host rank.
    """
    projection = dict(raw_slice_projection) if isinstance(raw_slice_projection, Mapping) else raw_slice_projection
    violations = verify_portable_raw_slice_projection(projection)  # type: ignore[arg-type]
    if violations:
        raise ValueError("portable raw-slice projection invalid: " + ",".join(violations))

    payload = projection["payload"]
    view: dict[str, Any] = {"version": payload["raw_slice_version"]}
    for field in RAW_SLICE_FIELDS:
        if field == "version":
            continue
        view[field] = payload[field]

    if tuple(view) != RAW_SLICE_FIELDS:
        raise ValueError("RAW_VIEW_FIELD_ORDER_MISMATCH")
    raw_violations = verify_raw_slice_receipt(view)
    if raw_violations:
        raise ValueError("derived raw-slice receipt view invalid: " + ",".join(raw_violations))
    return view


def verify_portable_raw_slice_host_plane_separation(
    *,
    raw_slice_projection: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> list[str]:
    """Verify portable transport and delegate the host-rank boundary to PR566."""
    try:
        raw_view = portable_projection_to_raw_slice_receipt(raw_slice_projection)
    except (KeyError, TypeError, ValueError) as exc:
        return [PORTABLE_PREFIX + str(exc)]

    violations = verify_raw_slice_host_plane_separation(
        raw_slice_receipt=raw_view,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    return ["HOST_PLANE_" + item for item in violations]


def admit_portable_raw_slice_host_plane_separation(
    *,
    raw_slice_projection: Mapping[str, Any],
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: Any = None,
    **temporal_kwargs: Any,
) -> dict[str, Any]:
    """Admit transport-safe local evidence while refusing portable -> host rank."""
    violations = verify_portable_raw_slice_host_plane_separation(
        raw_slice_projection=raw_slice_projection,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError("portable raw-slice/host-plane separation failed: " + ",".join(violations))

    raw_view = portable_projection_to_raw_slice_receipt(raw_slice_projection)
    host_plane = admit_raw_slice_host_plane_separation(
        raw_slice_receipt=raw_view,
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    projection = dict(raw_slice_projection)
    out: dict[str, Any] = {
        "version": VERSION,
        "portable_raw_slice_projection_verified": True,
        "portable_raw_slice_projection_digest": projection["payload_sha256"],
        "raw_slice_receipt_view_derived": True,
        "raw_slice_receipt_view_digest": hashlib.sha256(_canonical_bytes(raw_view)).hexdigest(),
        "portable_envelope_promoted_to_host_rank": False,
        "portable_envelope_accepted_as_host_resolution": False,
        "host_resolution_required_for_rank_change": True,
        "host_gate_states": dict(host_plane["host_gate_states"]),
        "host_disposition": host_plane["host_disposition"],
        "host_observation_set_complete": host_plane["host_observation_set_complete"],
        "host_observation_authority_proven": False,
        "producer_authenticated": False,
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "semantic_repair_correctness_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
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

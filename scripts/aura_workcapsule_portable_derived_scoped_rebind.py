#!/usr/bin/env python3
"""Derive PR532-shaped scoped-currentness evidence from one portable higher-owner target.

PR542 owns the continuity-bound portable canonical target and proves that target belongs to the
exact canonical WorkCapsule POST source instance. PR540 owns exact POST-world binding of PR532's
scoped rebind, but deliberately accepts a caller-supplied ``post_edit_witness``.

This D0 membrane consumes both parent consequence paths. It validates and replays PR542, derives
the PR532-shaped post-edit witness deterministically from PR542's one nested canonical-target
projection plus the preserved PRE rejected-currentness observation, and passes only that derived
witness into PR540. Cross-parent target equality is delegated to PR548's canonical receipt-level
shared-target coordinate owner instead of being reimplemented here.

The result is evidence reduction only. It does not authenticate the portable producer or the PRE
re-entry/source-observation producers, bind the structural semantic handle to raw bytes, prove
semantic repair correctness, close re-entry, narrow invalidation, or grant effect authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import aura_workcapsule_scoped_portable_target_identity as shared_target_owner
from scripts.aura_workcapsule_post_source_portable_higher_owner_continuity import (
    admit_post_source_portable_higher_owner_continuity,
    verify_portable_higher_owner_owner_chain_projection,
    verify_post_source_portable_higher_owner_continuity,
)
from scripts.aura_workcapsule_post_world_bound_scoped_rebind import (
    admit_post_world_bound_scoped_rebind,
    verify_post_world_bound_scoped_rebind,
)
from scripts.aura_workcapsule_scoped_post_repair_rebind import POST_EDIT_VERSION

VERSION = "AURA_WORKCAPSULE_PORTABLE_DERIVED_SCOPED_REBIND_V1"
SOURCE = "SOURCE"
STALE = "STALE"
UNKNOWN = "UNKNOWN"
PORTABLE_PREFIX = "PORTABLE_"
SCOPED_PREFIX = "SCOPED_"
SHARED_TARGET_PREFIX = "SHARED_TARGET_"

_FALSE_WITNESS_FIELDS = (
    "old_local_scope_id_currentness_authority",
    "incremental_parser_reuse_used",
    "changed_ranges_currentness_authority",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "semantic_patch_correctness_proven",
    "b_minus_approved",
    "commit_authorized",
    "execution_authorized",
    "human_authority",
    "external_effect_authorized",
    "producer_authenticated",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest_identity(value: Any, scope_profile: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": scope_profile,
        "value": hashlib.sha256(_canonical_bytes(value)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _exact_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label}_NOT_EXACT_INTEGER")
    return value


def _pre_source_generation(source_observation: dict[str, Any]) -> int | None:
    status = source_observation.get("currentness")
    if status == STALE:
        expected = source_observation.get("expected_source_identity")
        if not isinstance(expected, dict):
            raise ValueError("STALE_EXPECTED_SOURCE_IDENTITY_MISSING")
        coordinate = expected.get("source_generation_coordinate")
        if not isinstance(coordinate, dict) or coordinate.get("domain") != SOURCE:
            raise ValueError("STALE_PRE_SOURCE_GENERATION_DOMAIN_LOST")
        return _exact_int(coordinate.get("value"), "STALE_PRE_SOURCE_GENERATION")
    if status == UNKNOWN:
        if source_observation.get("identity_guessed") is not False:
            raise ValueError("UNKNOWN_SOURCE_IDENTITY_GUESSED")
        return None
    raise ValueError("PRE_SOURCE_OBSERVATION_NOT_REJECTED_CURRENTNESS")


def derive_post_edit_witness_from_portable_target(
    *,
    portable_higher_owner_projection: dict[str, Any],
    source_observation: dict[str, Any],
) -> dict[str, Any]:
    """Derive the exact PR532 witness shape from one validated portable target plus PRE state."""
    outer_violations = verify_portable_higher_owner_owner_chain_projection(
        portable_higher_owner_projection
    )
    if outer_violations:
        raise ValueError("portable owner-chain invalid: " + ",".join(outer_violations))

    payload = portable_higher_owner_projection["payload"]["canonical_target_projection"]["payload"]
    if payload.get("source_generation_domain") != SOURCE:
        raise ValueError("PORTABLE_SOURCE_GENERATION_DOMAIN_LOST")
    if payload.get("post_edit_profiled_scope_current") is not True:
        raise ValueError("PORTABLE_POST_EDIT_SCOPE_NOT_CURRENT")

    witness: dict[str, Any] = {
        "version": POST_EDIT_VERSION,
        "file_id": _exact_int(payload.get("file_id"), "PORTABLE_FILE_ID"),
        "relative_path": str(payload.get("relative_path") or ""),
        "pre_source_generation": _pre_source_generation(source_observation),
        "post_source_generation": _exact_int(
            payload.get("source_generation_value"), "PORTABLE_POST_SOURCE_GENERATION"
        ),
        "source_generation_domain": SOURCE,
        "post_body_sha256": str(payload.get("source_sha256_hex") or ""),
        "post_byte_len": _exact_int(payload.get("source_byte_len"), "PORTABLE_SOURCE_BYTE_LEN"),
        "syntax_ordinal": _exact_int(
            payload.get("selected_target_syntax_ordinal"), "PORTABLE_TARGET_SYNTAX_ORDINAL"
        ),
        "byte_start": _exact_int(
            payload.get("selected_target_byte_start"), "PORTABLE_TARGET_BYTE_START"
        ),
        "byte_end": _exact_int(
            payload.get("selected_target_byte_end"), "PORTABLE_TARGET_BYTE_END"
        ),
        "semantic_handle_digest": str(
            payload.get("selected_target_semantic_handle_digest_hex") or ""
        ),
        "post_edit_profiled_scope_current": True,
    }
    if not witness["relative_path"]:
        raise ValueError("PORTABLE_RELATIVE_PATH_MISSING")
    if len(witness["post_body_sha256"]) != 64:
        raise ValueError("PORTABLE_SOURCE_SHA256_MALFORMED")
    if len(witness["semantic_handle_digest"]) != 64:
        raise ValueError("PORTABLE_SEMANTIC_HANDLE_MALFORMED")
    for field in _FALSE_WITNESS_FIELDS:
        witness[field] = False
    return witness


def _portable_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "pre_root": kwargs["pre_root"],
        "pre_codemap": kwargs["pre_codemap"],
        "pre_anchor_manifest": kwargs["pre_anchor_manifest"],
        "pre_witness_manifest": kwargs["pre_witness_manifest"],
        "previous_binding": kwargs["previous_binding"],
        "pre_graph_witness": kwargs["pre_graph_witness"],
        "reentry_receipt": kwargs["reentry_receipt"],
        "pre_observation_closure_receipt": kwargs["pre_observation_closure_receipt"],
        "post_root": kwargs["post_root"],
        "post_codemap": kwargs["post_codemap"],
        "post_anchor_manifest": kwargs["post_anchor_manifest"],
        "post_witness_manifest": kwargs["post_witness_manifest"],
        "post_graph_witness": kwargs["post_graph_witness"],
        "post_observation_bound_receipt": kwargs["post_observation_bound_receipt"],
        "portable_higher_owner_projection": kwargs["portable_higher_owner_projection"],
    }


def _scoped_kwargs(kwargs: dict[str, Any], witness: dict[str, Any]) -> dict[str, Any]:
    return {
        "pre_root": kwargs["pre_root"],
        "pre_codemap": kwargs["pre_codemap"],
        "pre_anchor_manifest": kwargs["pre_anchor_manifest"],
        "pre_witness_manifest": kwargs["pre_witness_manifest"],
        "previous_binding": kwargs["previous_binding"],
        "pre_graph_witness": kwargs["pre_graph_witness"],
        "reentry_receipt": kwargs["reentry_receipt"],
        "post_root": kwargs["post_root"],
        "post_codemap": kwargs["post_codemap"],
        "post_anchor_manifest": kwargs["post_anchor_manifest"],
        "post_witness_manifest": kwargs["post_witness_manifest"],
        "post_graph_witness": kwargs["post_graph_witness"],
        "observation_bound_receipt": kwargs["post_observation_bound_receipt"],
        "reentry_admission": kwargs["reentry_admission"],
        "source_observation": kwargs["source_observation"],
        "dependency_key": kwargs["dependency_key"],
        "post_edit_witness": witness,
    }


def verify_portable_derived_scoped_rebind(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    pre_observation_closure_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    post_observation_bound_receipt: dict[str, Any],
    portable_higher_owner_projection: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
) -> list[str]:
    """Consume PR542 + PR540 and delegate shared-target equality to PR548."""
    kwargs = locals()
    portable_violations = verify_post_source_portable_higher_owner_continuity(
        **_portable_kwargs(kwargs)
    )
    if portable_violations:
        return [PORTABLE_PREFIX + item for item in portable_violations]

    try:
        witness = derive_post_edit_witness_from_portable_target(
            portable_higher_owner_projection=portable_higher_owner_projection,
            source_observation=source_observation,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"DERIVED_WITNESS_FAILED:{exc}"]

    scoped_violations = verify_post_world_bound_scoped_rebind(**_scoped_kwargs(kwargs, witness))
    if scoped_violations:
        return [SCOPED_PREFIX + item for item in scoped_violations]

    portable = admit_post_source_portable_higher_owner_continuity(**_portable_kwargs(kwargs))
    scoped = admit_post_world_bound_scoped_rebind(**_scoped_kwargs(kwargs, witness))
    nested_scoped = scoped["scoped_post_repair_rebind"]
    coordinate_violations = shared_target_owner.verify_shared_target_coordinates(
        scoped_receipt=nested_scoped,
        source_receipt=portable,
    )
    return [SHARED_TARGET_PREFIX + item for item in coordinate_violations]


def admit_portable_derived_scoped_rebind(**kwargs: Any) -> dict[str, Any]:
    """Emit the reduced evidence surface or fail closed."""
    violations = verify_portable_derived_scoped_rebind(**kwargs)
    if violations:
        raise ValueError("portable-derived scoped rebind failed: " + ",".join(violations))

    witness = derive_post_edit_witness_from_portable_target(
        portable_higher_owner_projection=kwargs["portable_higher_owner_projection"],
        source_observation=kwargs["source_observation"],
    )
    portable = admit_post_source_portable_higher_owner_continuity(**_portable_kwargs(kwargs))
    scoped = admit_post_world_bound_scoped_rebind(**_scoped_kwargs(kwargs, witness))
    payload: dict[str, Any] = {
        "version": VERSION,
        "portable_higher_owner_post_source_continuity_consumed": True,
        "post_world_scoped_rebind_consumed": True,
        "post_edit_witness_derived_from_portable_target": True,
        "caller_post_edit_witness_accepted": False,
        "one_portable_target_projection_used": True,
        "shared_target_coordinate_owner": "scripts.aura_workcapsule_scoped_portable_target_identity.verify_shared_target_coordinates",
        "shared_target_coordinate_reproved": True,
        "dependency_key": scoped["dependency_key"],
        "post_source_generation": scoped["post_source_generation"],
        "post_body_sha256": scoped["post_body_sha256"],
        "post_byte_len": scoped["post_byte_len"],
        "semantic_handle_digest": scoped["scoped_post_repair_rebind"]["semantic_handle_digest"],
        "portable_owner_chain_payload_sha256": kwargs["portable_higher_owner_projection"][
            "payload_sha256"
        ],
        "derived_post_edit_witness_identity": _digest_identity(
            witness, "AURA_WORKCAPSULE_DERIVED_PR532_POST_EDIT_WITNESS_V1"
        ),
        "portable_parent_receipt_identity": portable["receipt_identity"],
        "scoped_parent_receipt_identity": scoped["receipt_identity"],
        "reentry_closed": False,
        "reentry_scope_narrowed": False,
        "post_edit_scope_handle_bound_to_raw_bytes": False,
        "portable_projection_producer_authenticated": False,
        "pre_reentry_producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
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
    payload["receipt_identity"] = _digest_identity(
        payload, "AURA_WORKCAPSULE_PORTABLE_DERIVED_SCOPED_REBIND_V1_FULL_PAYLOAD"
    )
    return payload

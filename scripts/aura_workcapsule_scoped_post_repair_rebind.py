#!/usr/bin/env python3
"""Bind one stale/unknown WorkCapsule dependency to a fresh post-repair ASTGE scope witness.

This is a D0 compatibility membrane. It consumes:
- a PR519-shaped exact observation-bound closure admission,
- a PR522-shaped raw-owner stale-safe re-entry admission,
- the exact rejected source observation row selected for re-entry, and
- a PR515-shaped post-edit profiled-scope CURRENT witness.

It proves only that the same dependency identity selected for re-entry now has independently
described fresh scoped currentness evidence. It does not close re-entry, narrow invalidation,
authenticate producers, prove source->graph dependency mapping, or mint semantic/effect authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_observation_bound_exact_verifier import VERSION as CLOSURE_VERSION
from scripts.aura_workcapsule_raw_owner_stale_safe_reentry import VERSION as REENTRY_VERSION

VERSION = "AURA_WORKCAPSULE_SCOPED_POST_REPAIR_REBIND_V1"
POST_EDIT_VERSION = "AURA_ASTGE_POST_EDIT_PROFILED_SCOPE_CURRENT_V1"
SOURCE_DOMAIN = "SOURCE"
STALE = "STALE"
UNKNOWN = "UNKNOWN"
FULL_GRAPH = "FULL_GRAPH"
SELECTED_SOURCES = "SELECTED_SOURCES"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_SCOPED_POST_REPAIR_REBIND_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _dependency_key(value: dict[str, Any]) -> tuple[int, str]:
    return int(value["file_id"]), str(value["relative_path"])


def _authority_is_false(value: Any) -> bool:
    return isinstance(value, dict) and not any(bool(flag) for flag in value.values())


def verify_scoped_post_repair_rebind(
    *,
    closure_admission: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
    post_edit_witness: dict[str, Any],
) -> list[str]:
    """Verify evidence-only post-repair rebinding for one already rejected dependency."""
    violations: list[str] = []

    if closure_admission.get("version") != CLOSURE_VERSION:
        violations.append("UNSUPPORTED_CLOSURE_ADMISSION_VERSION")
    if closure_admission.get("exact_observation_bound_input_reproduction") is not True:
        violations.append("CLOSURE_NOT_EXACT_INPUT_REPRODUCTION")
    if not _authority_is_false(closure_admission.get("authority")):
        violations.append("CLOSURE_AUTHORITY_NOT_FALSE")

    if reentry_admission.get("version") != REENTRY_VERSION:
        violations.append("UNSUPPORTED_REENTRY_ADMISSION_VERSION")
    if reentry_admission.get("raw_source_owner_bound") is not True:
        violations.append("REENTRY_NOT_RAW_SOURCE_OWNER_BOUND")
    if reentry_admission.get("rejected_currentness_exact_reentry_only") is not True:
        violations.append("REENTRY_NOT_REJECTED_CURRENTNESS_ONLY")
    if reentry_admission.get("reentry_required") is not True:
        violations.append("REENTRY_NOT_REQUIRED")
    if reentry_admission.get("current_source_evidence_admitted") is not False:
        violations.append("PRE_REPAIR_CURRENTNESS_LAUNDERED")
    if reentry_admission.get("source_currentness_minted_by_exact_reproduction") is not False:
        violations.append("EXACT_REPRODUCTION_MINTED_CURRENTNESS")
    if not _authority_is_false(reentry_admission.get("authority")):
        violations.append("REENTRY_AUTHORITY_NOT_FALSE")

    try:
        key = _dependency_key(dependency_key)
    except (KeyError, TypeError, ValueError):
        violations.append("MALFORMED_DEPENDENCY_KEY")
        key = None

    rejected_raw = reentry_admission.get("rejected_dependency_keys")
    if not isinstance(rejected_raw, list):
        violations.append("REJECTED_DEPENDENCY_KEYS_MISSING")
        rejected: set[tuple[int, str]] = set()
    else:
        rejected = set()
        for row in rejected_raw:
            try:
                rejected.add(_dependency_key(row))
            except (KeyError, TypeError, ValueError):
                violations.append("MALFORMED_REJECTED_DEPENDENCY_KEY")
        if key is not None and key not in rejected:
            violations.append("DEPENDENCY_NOT_SELECTED_FOR_REENTRY")

    scope = reentry_admission.get("minimum_reentry_scope")
    if scope not in {SELECTED_SOURCES, FULL_GRAPH}:
        violations.append("UNSUPPORTED_REENTRY_SCOPE")

    status = source_observation.get("currentness")
    if status not in {STALE, UNKNOWN}:
        violations.append("SOURCE_OBSERVATION_NOT_REJECTED_CURRENTNESS")

    try:
        if status == STALE:
            expected = source_observation.get("expected_source_identity")
            if not isinstance(expected, dict):
                violations.append("STALE_EXPECTED_IDENTITY_MISSING")
            else:
                observed_key = (int(expected["file_id"]), str(source_observation["relative_path"]))
                if key is not None and observed_key != key:
                    violations.append("SOURCE_OBSERVATION_DEPENDENCY_MISMATCH")
                coordinate = expected.get("source_generation_coordinate")
                if not isinstance(coordinate, dict) or coordinate.get("domain") != SOURCE_DOMAIN:
                    violations.append("STALE_PRE_GENERATION_DOMAIN_LOST")
                elif post_edit_witness.get("pre_source_generation") != coordinate.get("value"):
                    violations.append("STALE_PRE_GENERATION_MISMATCH")
                if source_observation.get("observed_bytes_bound_to_source_generation") is not False:
                    violations.append("STALE_OBSERVED_BYTES_LAUNDERED")
                stale_digest = source_observation.get("observed_body_sha256")
                stale_len = source_observation.get("observed_byte_len")
                if (
                    isinstance(stale_digest, str)
                    and stale_len is not None
                    and post_edit_witness.get("post_body_sha256") == stale_digest
                    and post_edit_witness.get("post_byte_len") == stale_len
                ):
                    violations.append("STALE_OBSERVED_BYTES_RELABELED_AS_POST_GENERATION")
        elif status == UNKNOWN:
            observed_key = (
                int(source_observation["prior_file_id"]),
                str(source_observation["relative_path"]),
            )
            if key is not None and observed_key != key:
                violations.append("SOURCE_OBSERVATION_DEPENDENCY_MISMATCH")
            if source_observation.get("identity_guessed") is not False:
                violations.append("UNKNOWN_IDENTITY_GUESSED")
            if post_edit_witness.get("pre_source_generation") is not None:
                violations.append("UNKNOWN_PRE_GENERATION_RETROACTIVELY_INVENTED")
    except (KeyError, TypeError, ValueError):
        violations.append("MALFORMED_SOURCE_OBSERVATION")

    if post_edit_witness.get("version") != POST_EDIT_VERSION:
        violations.append("UNSUPPORTED_POST_EDIT_WITNESS_VERSION")
    if post_edit_witness.get("post_edit_profiled_scope_current") is not True:
        violations.append("POST_EDIT_SCOPE_NOT_CURRENT")
    if post_edit_witness.get("source_generation_domain") != SOURCE_DOMAIN:
        violations.append("POST_SOURCE_GENERATION_DOMAIN_LOST")
    if key is not None:
        try:
            post_key = (
                int(post_edit_witness["file_id"]),
                str(post_edit_witness["relative_path"]),
            )
            if post_key != key:
                violations.append("POST_EDIT_DEPENDENCY_IDENTITY_MISMATCH")
        except (KeyError, TypeError, ValueError):
            violations.append("MALFORMED_POST_EDIT_DEPENDENCY_IDENTITY")
    pre_generation = post_edit_witness.get("pre_source_generation")
    post_generation = post_edit_witness.get("post_source_generation")
    if post_generation is None:
        violations.append("POST_SOURCE_GENERATION_MISSING")
    elif pre_generation is not None and post_generation == pre_generation:
        violations.append("POST_SOURCE_GENERATION_NOT_ADVANCED")
    if not isinstance(post_edit_witness.get("syntax_ordinal"), int):
        violations.append("CANONICAL_SCOPE_SYNTAX_ORDINAL_MISSING")
    if not isinstance(post_edit_witness.get("byte_start"), int) or not isinstance(
        post_edit_witness.get("byte_end"), int
    ):
        violations.append("CANONICAL_SCOPE_SPAN_MISSING")
    elif post_edit_witness["byte_start"] >= post_edit_witness["byte_end"]:
        violations.append("CANONICAL_SCOPE_SPAN_INVALID")
    if not isinstance(post_edit_witness.get("semantic_handle_digest"), str) or not post_edit_witness.get(
        "semantic_handle_digest"
    ):
        violations.append("CANONICAL_SCOPE_HANDLE_MISSING")

    required_false = (
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
    for field in required_false:
        if post_edit_witness.get(field) is not False:
            violations.append(f"POST_EDIT_CEILING_VIOLATED:{field}")

    if closure_admission.get("closure_status") not in {"HOLD", "CLOSED"}:
        violations.append("UNSUPPORTED_HISTORICAL_CLOSURE_STATUS")

    return list(dict.fromkeys(violations))


def admit_scoped_post_repair_rebind(
    *,
    closure_admission: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
    post_edit_witness: dict[str, Any],
) -> dict[str, Any]:
    """Return a narrow evidence-only rebind receipt or fail closed."""
    violations = verify_scoped_post_repair_rebind(
        closure_admission=closure_admission,
        reentry_admission=reentry_admission,
        source_observation=source_observation,
        dependency_key=dependency_key,
        post_edit_witness=post_edit_witness,
    )
    if violations:
        raise ValueError("scoped post-repair rebind verification failed: " + ",".join(violations))

    payload: dict[str, Any] = {
        "version": VERSION,
        "dependency_key": {
            "file_id": int(dependency_key["file_id"]),
            "relative_path": str(dependency_key["relative_path"]),
        },
        "pre_repair_currentness": str(source_observation["currentness"]),
        "historical_closure_status": str(closure_admission["closure_status"]),
        "reentry_scope_before": str(reentry_admission["minimum_reentry_scope"]),
        "reentry_scope_after": str(reentry_admission["minimum_reentry_scope"]),
        "reentry_required_before": bool(reentry_admission["reentry_required"]),
        "reentry_required_after": bool(reentry_admission["reentry_required"]),
        "post_edit_profiled_scope_current": True,
        "post_source_generation": int(post_edit_witness["post_source_generation"]),
        "post_source_generation_domain": SOURCE_DOMAIN,
        "post_body_sha256": str(post_edit_witness["post_body_sha256"]),
        "post_byte_len": int(post_edit_witness["post_byte_len"]),
        "syntax_ordinal": int(post_edit_witness["syntax_ordinal"]),
        "byte_start": int(post_edit_witness["byte_start"]),
        "byte_end": int(post_edit_witness["byte_end"]),
        "semantic_handle_digest": str(post_edit_witness["semantic_handle_digest"]),
        "same_dependency_identity_bound": True,
        "scoped_post_repair_rebind_evidence": True,
        "historical_stale_unknown_evidence_preserved": True,
        "pre_unknown_generation_retroactively_invented": False,
        "stale_observed_bytes_rebound_to_post_generation": False,
        "reentry_closed": False,
        "reentry_scope_narrowed_by_fresh_scope_context": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "semantic_patch_correctness_proven": False,
        "b_minus_approved": False,
        "closure_admission_producer_authenticated": False,
        "reentry_admission_producer_authenticated": False,
        "post_edit_witness_producer_authenticated": False,
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
    payload["receipt_identity"] = _identity(payload)
    return payload

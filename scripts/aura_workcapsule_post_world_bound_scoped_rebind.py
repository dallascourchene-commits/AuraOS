#!/usr/bin/env python3
"""Bind PR532 scoped post-repair evidence to PR529's exact POST raw world.

PR529 independently replays a two-phase WorkCapsule lifecycle from distinct PRE and
POST raw source-owner inputs. PR532 proves that one rejected WorkCapsule dependency
has fresh post-edit scoped-currentness evidence, but accepts a closure admission as an
input and does not itself bind the post body/generation to a raw POST evidence world.

This D0 membrane composes those owners without stealing their boundaries. It derives
the PR519-shaped closure admission from PR529, regenerates the canonical POST source
projection from the same raw POST inputs, requires the selected dependency's CURRENT
source identity to match the PR532 post-edit witness on file/path, SourceGeneration,
full-body SHA-256, and byte length, then delegates the scoped rebind to PR532.

The rejected PRE re-entry admission, rejected source-observation row, dependency key,
and post-edit structural scope witness remain explicit inputs. This membrane does not
authenticate those producers, bind the structural scope handle to the raw bytes, close
re-entry, narrow invalidation, prove semantics, or authorize effects.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_scoped_post_repair_rebind import (
    admit_scoped_post_repair_rebind,
    verify_scoped_post_repair_rebind,
)
from scripts.aura_workcapsule_two_phase_observation_bound_exact import (
    admit_two_phase_observation_bound_exact,
)
from scripts.aura_workcapsule_two_phase_source_bound_closure import (
    derive_post_reentry_candidate,
)

VERSION = "AURA_WORKCAPSULE_POST_WORLD_BOUND_SCOPED_REBIND_V1"
CLAIM = "EXACT_POST_RAW_WORLD_BOUND_TO_SCOPED_POST_REPAIR_WITNESS"
SOURCE = "SOURCE"
CURRENT = "CURRENT"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_POST_WORLD_BOUND_SCOPED_REBIND_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _key(value: dict[str, Any]) -> tuple[int, str]:
    file_id = value.get("file_id")
    path = value.get("relative_path")
    if type(file_id) is not int or not isinstance(path, str) or not path:
        raise ValueError("dependency key requires exact integer file_id and nonempty relative_path")
    return file_id, path


def _post_source_row(
    *, projection: dict[str, Any], dependency_key: dict[str, Any]
) -> dict[str, Any]:
    key = _key(dependency_key)
    rows = projection.get("o7_source_witnesses")
    if not isinstance(rows, list):
        raise ValueError("POST_SOURCE_WITNESS_LIST_MISSING")
    matched: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            row_key = _key(row)
        except ValueError:
            continue
        if row_key == key:
            matched.append(row)
    if len(matched) != 1:
        raise ValueError(f"POST_SOURCE_WITNESS_CARDINALITY_NOT_ONE:{len(matched)}")
    return matched[0]


def _cross_world_violations(
    *,
    projection: dict[str, Any],
    post_exact_admission: dict[str, Any],
    dependency_key: dict[str, Any],
    post_edit_witness: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    if projection.get("source_generation_domain") != SOURCE:
        violations.append("POST_PROJECTION_SOURCE_GENERATION_DOMAIN_LOST")
    if projection.get("receipt_identity") != post_exact_admission.get("source_observation_identity"):
        violations.append("POST_PROJECTION_NOT_EXACT_POST_OBSERVATION_IDENTITY")

    try:
        row = _post_source_row(projection=projection, dependency_key=dependency_key)
    except ValueError as exc:
        return list(dict.fromkeys(violations + [str(exc)]))

    if row.get("currentness") != CURRENT:
        violations.append("POST_RAW_WORLD_DEPENDENCY_NOT_CURRENT")
    if post_edit_witness.get("source_generation_domain") != SOURCE:
        violations.append("POST_EDIT_SOURCE_GENERATION_DOMAIN_LOST")

    row_generation = row.get("source_generation")
    witness_generation = post_edit_witness.get("post_source_generation")
    if type(row_generation) is not int or type(witness_generation) is not int:
        violations.append("POST_SOURCE_GENERATION_NOT_EXACT_INTEGER")
    elif row_generation != witness_generation:
        violations.append("POST_WORLD_SOURCE_GENERATION_MISMATCH")

    row_len = row.get("source_byte_len")
    witness_len = post_edit_witness.get("post_byte_len")
    if type(row_len) is not int or type(witness_len) is not int:
        violations.append("POST_SOURCE_BYTE_LENGTH_NOT_EXACT_INTEGER")
    elif row_len != witness_len:
        violations.append("POST_WORLD_BYTE_LENGTH_MISMATCH")

    row_sha = row.get("source_sha256")
    witness_sha = post_edit_witness.get("post_body_sha256")
    if not isinstance(row_sha, str) or not isinstance(witness_sha, str):
        violations.append("POST_SOURCE_SHA256_NOT_STRING")
    elif row_sha.lower() != witness_sha.lower():
        violations.append("POST_WORLD_BODY_SHA256_MISMATCH")

    try:
        if _key(row) != _key(post_edit_witness):
            violations.append("POST_WORLD_DEPENDENCY_KEY_MISMATCH")
    except ValueError:
        violations.append("POST_EDIT_DEPENDENCY_KEY_MALFORMED")

    return list(dict.fromkeys(violations))


def _derive_parent_evidence(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    observation_bound_receipt: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    two_phase = admit_two_phase_observation_bound_exact(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        observation_bound_receipt=observation_bound_receipt,
    )
    projection, _candidate = derive_post_reentry_candidate(
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        post_graph_witness=post_graph_witness,
    )
    return two_phase, projection


def verify_post_world_bound_scoped_rebind(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    observation_bound_receipt: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
    post_edit_witness: dict[str, Any],
) -> list[str]:
    """Verify PR532 against the exact POST source world reproduced by PR529."""
    try:
        two_phase, projection = _derive_parent_evidence(
            pre_root=pre_root,
            pre_codemap=pre_codemap,
            pre_anchor_manifest=pre_anchor_manifest,
            pre_witness_manifest=pre_witness_manifest,
            previous_binding=previous_binding,
            pre_graph_witness=pre_graph_witness,
            reentry_receipt=reentry_receipt,
            post_root=post_root,
            post_codemap=post_codemap,
            post_anchor_manifest=post_anchor_manifest,
            post_witness_manifest=post_witness_manifest,
            post_graph_witness=post_graph_witness,
            observation_bound_receipt=observation_bound_receipt,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"POST_WORLD_EXACT_REPLAY_FAILED:{exc}"]

    post_exact = two_phase.get("post_observation_bound_exact_reproduction")
    if not isinstance(post_exact, dict):
        return ["POST_EXACT_CLOSURE_ADMISSION_MISSING"]

    violations = _cross_world_violations(
        projection=projection,
        post_exact_admission=post_exact,
        dependency_key=dependency_key,
        post_edit_witness=post_edit_witness,
    )
    violations.extend(
        f"PR532_{item}"
        for item in verify_scoped_post_repair_rebind(
            closure_admission=post_exact,
            reentry_admission=reentry_admission,
            source_observation=source_observation,
            dependency_key=dependency_key,
            post_edit_witness=post_edit_witness,
        )
    )
    return list(dict.fromkeys(violations))


def admit_post_world_bound_scoped_rebind(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    observation_bound_receipt: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
    post_edit_witness: dict[str, Any],
) -> dict[str, Any]:
    """Return evidence-only POST-world binding or fail closed."""
    violations = verify_post_world_bound_scoped_rebind(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        observation_bound_receipt=observation_bound_receipt,
        reentry_admission=reentry_admission,
        source_observation=source_observation,
        dependency_key=dependency_key,
        post_edit_witness=post_edit_witness,
    )
    if violations:
        raise ValueError("post-world scoped rebind verification failed: " + ",".join(violations))

    two_phase, projection = _derive_parent_evidence(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        observation_bound_receipt=observation_bound_receipt,
    )
    post_exact = two_phase["post_observation_bound_exact_reproduction"]
    row = _post_source_row(projection=projection, dependency_key=dependency_key)
    scoped = admit_scoped_post_repair_rebind(
        closure_admission=post_exact,
        reentry_admission=reentry_admission,
        source_observation=source_observation,
        dependency_key=dependency_key,
        post_edit_witness=post_edit_witness,
    )
    payload: dict[str, Any] = {
        "version": VERSION,
        "claim": CLAIM,
        "post_world_exact_reproduction": True,
        "post_projection_receipt_identity": projection["receipt_identity"],
        "post_exact_source_observation_identity": post_exact["source_observation_identity"],
        "dependency_key": {
            "file_id": row["file_id"],
            "relative_path": row["relative_path"],
        },
        "post_source_generation": row["source_generation"],
        "post_source_generation_domain": SOURCE,
        "post_body_sha256": row["source_sha256"],
        "post_byte_len": row["source_byte_len"],
        "post_source_currentness": row["currentness"],
        "scoped_post_repair_rebind": scoped,
        "caller_closure_admission_accepted": False,
        "caller_post_source_witness_accepted": False,
        "caller_candidate_binding_accepted": False,
        "reentry_closed": False,
        "reentry_scope_narrowed": False,
        "post_edit_scope_producer_authenticated": False,
        "post_edit_scope_handle_bound_to_raw_bytes": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "semantic_patch_correctness_proven": False,
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

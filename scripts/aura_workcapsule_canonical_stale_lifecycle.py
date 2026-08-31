#!/usr/bin/env python3
"""Canonical rejected-currentness WorkCapsule lifecycle convergence.

PR521 proves that a rejected-currentness observation-bound closure is an exact HOLD
consequence of pinned raw source evidence. PR522 proves the corresponding stale-safe
re-entry decision is bound to the same raw source owner rather than to a caller-made
projection. Both independently replay PR509, but independent green receipts are not
by themselves proof that both lifecycle stages consumed the same source-observation
projection or reached the same re-entry decision.

This D0 membrane is a split-brain/TOCTOU sentry. It derives one PR509 projection,
requires the direct PR517 path and PR522's stronger raw-owner path to agree exactly,
requires PR521's HOLD admission to carry that same projection/previous/O8 identity,
and records the observed-graph and candidate-graph inputs as distinct lifecycle roles.
It grants no source CURRENTness, producer authentication, semantic truth, review,
mutation, execution, commit/merge/promotion authority, or external effect.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_closure import HOLD
from scripts.aura_workcapsule_raw_owner_stale_safe_reentry import (
    admit_raw_owner_stale_safe_exact_reentry,
    verify_raw_owner_stale_safe_exact_reentry,
)
from scripts.aura_workcapsule_source_reentry_observation import (
    compile_source_reentry_observations,
    verify_source_reentry_observations,
)
from scripts.aura_workcapsule_stale_exact_reentry import admit_stale_safe_exact_reentry
from scripts.aura_workcapsule_stale_observation_closure_exact_verifier import (
    admit_stale_observation_closure_exact_reproduction,
    verify_stale_observation_closure_exact_reproduction,
)

VERSION = "AURA_WORKCAPSULE_CANONICAL_STALE_LIFECYCLE_V1"
PROJECTION_INVALID_PREFIX = "PROJECTION_"
RAW_OWNER_REENTRY_INVALID_PREFIX = "RAW_OWNER_REENTRY_"
STALE_CLOSURE_INVALID_PREFIX = "STALE_CLOSURE_"
PROJECTION_IDENTITY_SPLIT_BRAIN = "PROJECTION_IDENTITY_SPLIT_BRAIN"
PREVIOUS_BINDING_IDENTITY_SPLIT_BRAIN = "PREVIOUS_BINDING_IDENTITY_SPLIT_BRAIN"
REENTRY_RECEIPT_IDENTITY_SPLIT_BRAIN = "REENTRY_RECEIPT_IDENTITY_SPLIT_BRAIN"
REENTRY_PATH_DECISION_MISMATCH = "REENTRY_PATH_DECISION_MISMATCH"
REJECTED_CURRENTNESS_LIFECYCLE_NOT_HOLD = "REJECTED_CURRENTNESS_LIFECYCLE_NOT_HOLD"
LIFECYCLE_RECEIPT_IDENTITY_MISMATCH = "LIFECYCLE_RECEIPT_IDENTITY_MISMATCH"
LIFECYCLE_NOT_EXACT_RAW_INPUT_REPRODUCTION = "LIFECYCLE_NOT_EXACT_RAW_INPUT_REPRODUCTION"
AUTHORITY_MINTED_BY_CANONICAL_LIFECYCLE = "AUTHORITY_MINTED_BY_CANONICAL_LIFECYCLE"
CURRENTNESS_MINTED_BY_CANONICAL_LIFECYCLE = "CURRENTNESS_MINTED_BY_CANONICAL_LIFECYCLE"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_CANONICAL_STALE_LIFECYCLE_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _graph_role(witness: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "role": role,
        "graph_id": witness.get("graph_id"),
        "graph_generation": witness.get("graph_generation"),
        "graph_basis_identity": witness.get("graph_basis_identity"),
        "currentness": witness.get("currentness"),
        "witness_ref": witness.get("witness_ref"),
        "producer_authenticated": False,
    }


def _decision(admission: dict[str, Any]) -> dict[str, Any]:
    return {
        "minimum_reentry_scope": admission.get("minimum_reentry_scope"),
        "minimum_reentry_source_keys": admission.get("minimum_reentry_source_keys"),
        "rejected_dependency_keys": admission.get("rejected_dependency_keys"),
        "reentry_required": admission.get("reentry_required"),
    }


def verify_canonical_stale_lifecycle_receipt(receipt: dict[str, Any]) -> list[str]:
    """Verify internal cross-layer identity continuity for one lifecycle receipt."""
    violations: list[str] = []
    if receipt.get("version") != VERSION:
        violations.append("UNSUPPORTED_VERSION")

    projection_identity = receipt.get("source_projection_identity")
    direct = receipt.get("direct_stale_safe_admission")
    raw_owner = receipt.get("raw_owner_stale_safe_admission")
    closure = receipt.get("stale_observation_closure_admission")
    if not isinstance(direct, dict) or not isinstance(raw_owner, dict) or not isinstance(closure, dict):
        violations.append("MALFORMED_LIFECYCLE_ADMISSIONS")
    else:
        raw_nested = raw_owner.get("stale_safe_admission")
        if not isinstance(raw_nested, dict):
            violations.append("MALFORMED_RAW_OWNER_STALE_SAFE_ADMISSION")
        else:
            if _decision(direct) != _decision(raw_nested):
                violations.append(REENTRY_PATH_DECISION_MISMATCH)
        if raw_owner.get("source_projection_receipt_identity") != projection_identity:
            violations.append(PROJECTION_IDENTITY_SPLIT_BRAIN)
        if closure.get("source_observation_identity") != projection_identity:
            violations.append(PROJECTION_IDENTITY_SPLIT_BRAIN)
        if direct.get("previous_binding_identity") != receipt.get("previous_binding_identity"):
            violations.append(PREVIOUS_BINDING_IDENTITY_SPLIT_BRAIN)
        if closure.get("previous_binding_identity") != receipt.get("previous_binding_identity"):
            violations.append(PREVIOUS_BINDING_IDENTITY_SPLIT_BRAIN)
        if direct.get("o8_receipt_identity") != receipt.get("reentry_receipt_identity"):
            violations.append(REENTRY_RECEIPT_IDENTITY_SPLIT_BRAIN)
        if closure.get("reentry_receipt_identity") != receipt.get("reentry_receipt_identity"):
            violations.append(REENTRY_RECEIPT_IDENTITY_SPLIT_BRAIN)
        if closure.get("closure_status") != HOLD or receipt.get("closure_status") != HOLD:
            violations.append(REJECTED_CURRENTNESS_LIFECYCLE_NOT_HOLD)
        if receipt.get("canonical_reentry_decision") != _decision(direct):
            violations.append(REENTRY_PATH_DECISION_MISMATCH)

    if receipt.get("projection_identity_continuity_proven") is not True:
        violations.append(PROJECTION_IDENTITY_SPLIT_BRAIN)
    if receipt.get("reentry_path_equivalence_proven") is not True:
        violations.append(REENTRY_PATH_DECISION_MISMATCH)
    if receipt.get("observed_graph_role_distinct_from_candidate_graph_role") is not True:
        violations.append("GRAPH_PHASE_ROLES_COLLAPSED")

    if receipt.get("source_currentness_minted") is not False:
        violations.append(CURRENTNESS_MINTED_BY_CANONICAL_LIFECYCLE)
    for flag in (
        "producer_identity_authenticated",
        "source_observation_producer_authenticated",
        "observed_graph_producer_authenticated",
        "candidate_graph_producer_authenticated",
        "semantic_truth_minted",
        "source_to_graph_dependency_map_proven",
        "node_level_invalidation_cone_proven",
    ):
        if receipt.get(flag) is not False:
            violations.append(AUTHORITY_MINTED_BY_CANONICAL_LIFECYCLE)

    authority = receipt.get("authority")
    if not isinstance(authority, dict) or any(bool(value) for value in authority.values()):
        violations.append(AUTHORITY_MINTED_BY_CANONICAL_LIFECYCLE)

    supplied_identity = receipt.get("receipt_identity")
    without_identity = dict(receipt)
    without_identity.pop("receipt_identity", None)
    if supplied_identity != _identity(without_identity):
        violations.append(LIFECYCLE_RECEIPT_IDENTITY_MISMATCH)
    return list(dict.fromkeys(violations))


def compile_canonical_stale_lifecycle(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Compile one canonical rejected-currentness lifecycle or fail closed."""
    projection = compile_source_reentry_observations(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
    )
    projection_violations = verify_source_reentry_observations(projection)
    if projection_violations:
        raise ValueError(
            "canonical stale lifecycle source projection failed: "
            + ",".join(PROJECTION_INVALID_PREFIX + item for item in projection_violations)
        )

    raw_owner_violations = verify_raw_owner_stale_safe_exact_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    if raw_owner_violations:
        raise ValueError(
            "canonical stale lifecycle raw-owner re-entry failed: "
            + ",".join(RAW_OWNER_REENTRY_INVALID_PREFIX + item for item in raw_owner_violations)
        )

    closure_violations = verify_stale_observation_closure_exact_reproduction(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        observed_graph_witness=observed_graph_witness,
        candidate_graph_witness=candidate_graph_witness,
        closure_receipt=closure_receipt,
    )
    if closure_violations:
        raise ValueError(
            "canonical stale lifecycle closure failed: "
            + ",".join(STALE_CLOSURE_INVALID_PREFIX + item for item in closure_violations)
        )

    direct = admit_stale_safe_exact_reentry(
        source_observation_receipt=projection,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    raw_owner = admit_raw_owner_stale_safe_exact_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    closure = admit_stale_observation_closure_exact_reproduction(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        observed_graph_witness=observed_graph_witness,
        candidate_graph_witness=candidate_graph_witness,
        closure_receipt=closure_receipt,
    )

    projection_identity = projection["receipt_identity"]
    if raw_owner.get("source_projection_receipt_identity") != projection_identity:
        raise ValueError(PROJECTION_IDENTITY_SPLIT_BRAIN)
    if closure.get("source_observation_identity") != projection_identity:
        raise ValueError(PROJECTION_IDENTITY_SPLIT_BRAIN)
    raw_nested = raw_owner.get("stale_safe_admission")
    if not isinstance(raw_nested, dict) or _decision(direct) != _decision(raw_nested):
        raise ValueError(REENTRY_PATH_DECISION_MISMATCH)
    if closure.get("previous_binding_identity") != previous_binding.get("binding_identity"):
        raise ValueError(PREVIOUS_BINDING_IDENTITY_SPLIT_BRAIN)
    if closure.get("reentry_receipt_identity") != reentry_receipt.get("receipt_identity"):
        raise ValueError(REENTRY_RECEIPT_IDENTITY_SPLIT_BRAIN)
    if closure.get("closure_status") != HOLD:
        raise ValueError(REJECTED_CURRENTNESS_LIFECYCLE_NOT_HOLD)

    payload: dict[str, Any] = {
        "version": VERSION,
        "source_projection_identity": projection_identity,
        "previous_binding_identity": previous_binding["binding_identity"],
        "reentry_receipt_identity": reentry_receipt["receipt_identity"],
        "direct_stale_safe_admission": direct,
        "raw_owner_stale_safe_admission": raw_owner,
        "stale_observation_closure_admission": closure,
        "canonical_reentry_decision": _decision(direct),
        "closure_status": HOLD,
        "projection_identity_continuity_proven": True,
        "reentry_path_equivalence_proven": True,
        "observed_graph_phase": _graph_role(observed_graph_witness, "REENTRY_OBSERVATION"),
        "candidate_graph_phase": _graph_role(candidate_graph_witness, "CLOSURE_CANDIDATE"),
        "observed_graph_role_distinct_from_candidate_graph_role": True,
        "source_currentness_minted": False,
        "stale_observed_bytes_bound_to_source_generation": False,
        "unknown_identity_guessed": False,
        "producer_identity_authenticated": False,
        "source_observation_producer_authenticated": False,
        "observed_graph_producer_authenticated": False,
        "candidate_graph_producer_authenticated": False,
        "semantic_truth_minted": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "caller_source_observation_receipt_accepted": False,
        "caller_source_witnesses_accepted": False,
        "caller_sibling_admissions_accepted": False,
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
    internal = verify_canonical_stale_lifecycle_receipt(payload)
    if internal:
        raise ValueError("canonical stale lifecycle internal verification failed: " + ",".join(internal))
    return payload


def verify_canonical_stale_lifecycle(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
    lifecycle_receipt: dict[str, Any],
) -> list[str]:
    """Verify a lifecycle receipt against exact raw inputs and cross-layer relations."""
    violations = verify_canonical_stale_lifecycle_receipt(lifecycle_receipt)
    try:
        expected = compile_canonical_stale_lifecycle(
            root=root,
            codemap=codemap,
            anchor_manifest=anchor_manifest,
            witness_manifest=witness_manifest,
            previous_binding=previous_binding,
            reentry_receipt=reentry_receipt,
            observed_graph_witness=observed_graph_witness,
            candidate_graph_witness=candidate_graph_witness,
            closure_receipt=closure_receipt,
        )
    except ValueError as exc:
        violations.append("EXPECTED_LIFECYCLE_RECOMPILE_FAILED:" + str(exc))
        return list(dict.fromkeys(violations))
    if _canonical_bytes(lifecycle_receipt) != _canonical_bytes(expected):
        violations.append(LIFECYCLE_NOT_EXACT_RAW_INPUT_REPRODUCTION)
    return list(dict.fromkeys(violations))

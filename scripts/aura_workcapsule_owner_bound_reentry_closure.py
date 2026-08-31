#!/usr/bin/env python3
"""End-to-end owner-bound WorkCapsule selective re-entry closure.

PR514 proves that the O8 re-entry plan is the exact consequence of raw ASTGE
source-currentness owner evidence rather than a caller-selected source-witness
list. PR516 proves closure after deriving the candidate source basis from raw
source observations, but deliberately accepts the re-entry receipt as an input.

This D0 membrane closes that final plan-injection seam. The public compile path
accepts no caller re-entry receipt and no caller candidate binding. It derives
the canonical O8 plan through PR514, proves that plan against the raw evidence,
then passes that exact plan to PR516, which independently derives the candidate
binding from the same raw source-owner inputs before closure.

The graph witnesses remain explicit higher-owner inputs. This module does not
authenticate their producers, derive a node-level dependency cone, prove
semantic truth, or grant review/mutation/execution/commit/merge/effect authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_closure import (
    compile_observation_bound_reentry_closure,
    verify_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import (
    admit_source_bound_exact_reentry,
    compile_expected_source_bound_reentry,
)

VERSION = "AURA_WORKCAPSULE_OWNER_BOUND_REENTRY_CLOSURE_V1"
EXACT_END_TO_END_MISMATCH = "OWNER_BOUND_REENTRY_CLOSURE_NOT_EXACT_INPUT_REPRODUCTION"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_OWNER_BOUND_REENTRY_CLOSURE_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _compile(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    source_projection, reentry_receipt = compile_expected_source_bound_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
    )

    reentry_admission = admit_source_bound_exact_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        receipt=reentry_receipt,
    )

    closure = compile_observation_bound_reentry_closure(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=candidate_graph_witness,
    )
    closure_violations = verify_observation_bound_reentry_closure(closure)
    if closure_violations:
        raise ValueError("observation-bound closure is invalid: " + ",".join(closure_violations))

    same_source_observation = (
        closure.get("source_observation_identity") == source_projection.get("receipt_identity")
    )
    if not same_source_observation:
        raise ValueError("re-entry plan and candidate closure used different source observations")
    if closure.get("reentry_receipt_identity") != reentry_receipt.get("receipt_identity"):
        raise ValueError("closure does not bind the owner-derived re-entry receipt")

    payload: dict[str, Any] = {
        "version": VERSION,
        "closure_status": closure["closure_status"],
        "previous_binding_identity": previous_binding["binding_identity"],
        "source_observation_identity": source_projection["receipt_identity"],
        "owner_derived_reentry_receipt_identity": reentry_receipt["receipt_identity"],
        "owner_derived_reentry_scope": reentry_receipt["minimum_reentry_scope"],
        "owner_derived_reentry_source_keys": reentry_receipt["minimum_reentry_source_keys"],
        "derived_candidate_binding_identity": closure["derived_candidate_binding_identity"],
        "source_bound_exact_reentry_admission": reentry_admission,
        "observation_bound_closure": closure,
        "same_raw_source_observation_drives_plan_and_candidate": same_source_observation,
        "caller_reentry_receipt_accepted": False,
        "caller_candidate_binding_accepted": False,
        "source_owner_bound_exact_reentry": True,
        "candidate_source_basis_derived_from_raw_currentness_inputs": True,
        "graph_witness_producer_authenticated": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
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


def compile_owner_bound_reentry_closure(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    """Derive canonical re-entry plan and candidate closure from one raw owner basis."""
    return _compile(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        candidate_graph_witness=candidate_graph_witness,
    )


def verify_owner_bound_reentry_closure(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    receipt: dict[str, Any],
) -> list[str]:
    """Require exact end-to-end reproduction from the raw owner inputs."""
    expected = _compile(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        candidate_graph_witness=candidate_graph_witness,
    )
    violations: list[str] = []
    if _canonical_bytes(receipt) != _canonical_bytes(expected):
        violations.append(EXACT_END_TO_END_MISMATCH)
    return violations


def admit_owner_bound_reentry_closure(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    candidate_graph_witness: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit exact reproduction of the owner-bound lifecycle result, without effect authority."""
    violations = verify_owner_bound_reentry_closure(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        candidate_graph_witness=candidate_graph_witness,
        receipt=receipt,
    )
    if violations:
        raise ValueError("owner-bound re-entry closure verification failed: " + ",".join(violations))
    return {
        "version": VERSION,
        "exact_end_to_end_reproduction": True,
        "closure_status": receipt["closure_status"],
        "source_observation_identity": receipt["source_observation_identity"],
        "owner_derived_reentry_receipt_identity": receipt["owner_derived_reentry_receipt_identity"],
        "derived_candidate_binding_identity": receipt["derived_candidate_binding_identity"],
        "same_raw_source_observation_drives_plan_and_candidate": True,
        "caller_reentry_receipt_accepted": False,
        "caller_candidate_binding_accepted": False,
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

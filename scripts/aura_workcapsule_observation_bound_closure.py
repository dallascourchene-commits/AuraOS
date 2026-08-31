#!/usr/bin/env python3
"""Bind WorkCapsule re-entry closure to freshly derived source-currentness evidence.

PR509 derives WorkCapsule source witnesses by rerunning the source-currentness owner
from raw repository/CODEMAP/anchor/witness inputs. PR512 can prove closure of a
re-entry plan, but its public boundary accepts a caller-prepared candidate binding.
This membrane removes that source-basis injection point: it reruns PR509, compiles
the candidate WorkCapsule binding internally from PR509's exact O7 source witnesses,
and only then delegates closure rules to PR512.

The graph witness remains an explicit higher-owner input and is not authenticated by
this membrane. Source-observation binding does not mint semantic, review, mutation,
execution, commit, merge, provider, public, or human authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_context_binding import compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_closure import CLOSED, HOLD, compile_reentry_closure, verify_reentry_closure
from scripts.aura_workcapsule_reentry_invalidation import verify_reentry_invalidation
from scripts.aura_workcapsule_source_reentry_observation import compile_source_reentry_observations, verify_source_reentry_observations

VERSION = "AURA_WORKCAPSULE_OBSERVATION_BOUND_CLOSURE_V1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_OBSERVATION_BOUND_CLOSURE_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def compile_observation_bound_reentry_closure(*, root: Path, codemap: dict[str, Any], anchor_manifest: dict[str, Any], witness_manifest: dict[str, Any], previous_binding: dict[str, Any], reentry_receipt: dict[str, Any], candidate_graph_witness: dict[str, Any]) -> dict[str, Any]:
    reentry_violations = verify_reentry_invalidation(reentry_receipt)
    if reentry_violations:
        raise ValueError("reentry_receipt is not coherent: " + ",".join(reentry_violations))
    if reentry_receipt.get("previous_binding_identity") != previous_binding.get("binding_identity"):
        raise ValueError("reentry_receipt does not bind the supplied previous_binding")

    source_observation = compile_source_reentry_observations(root=root, codemap=codemap, anchor_manifest=anchor_manifest, witness_manifest=witness_manifest, previous_binding=previous_binding)
    source_violations = verify_source_reentry_observations(source_observation)
    if source_violations:
        raise ValueError("source observation is not coherent: " + ",".join(source_violations))

    candidate_binding = compile_workcapsule_context_binding(capsule=previous_binding["capsule"], graph_witness=candidate_graph_witness, source_witnesses=source_observation["o7_source_witnesses"])
    closure_receipt: dict[str, Any] | None = None
    closure_status = HOLD
    hold_reasons: list[str] = []
    if candidate_binding.get("context_admitted") is not True:
        hold_reasons.append("DERIVED_CANDIDATE_NOT_CURRENT")
    else:
        closure_receipt = compile_reentry_closure(previous_binding=previous_binding, reentry_receipt=reentry_receipt, candidate_binding=candidate_binding)
        closure_violations = verify_reentry_closure(closure_receipt)
        if closure_violations:
            raise ValueError("derived closure receipt is not coherent: " + ",".join(closure_violations))
        closure_status = str(closure_receipt["closure_status"])
        if closure_status != CLOSED:
            hold_reasons.extend(str(reason) for reason in closure_receipt["closure_reasons"])

    payload: dict[str, Any] = {
        "version": VERSION,
        "closure_status": closure_status,
        "previous_binding_identity": previous_binding["binding_identity"],
        "reentry_receipt_identity": reentry_receipt["receipt_identity"],
        "source_observation_identity": source_observation["receipt_identity"],
        "derived_candidate_binding_identity": candidate_binding["binding_identity"],
        "derived_candidate_binding": candidate_binding,
        "source_observation": source_observation,
        "closure_receipt": closure_receipt,
        "hold_reasons": hold_reasons,
        "candidate_source_basis_derived_from_raw_currentness_inputs": True,
        "caller_candidate_binding_accepted": False,
        "source_generation_domain_preserved": source_observation.get("source_generation_domain") == "SOURCE",
        "graph_witness_producer_proven": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
        "authority": {
            "semantic_truth_minted": False,
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


def verify_observation_bound_reentry_closure(receipt: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if receipt.get("version") != VERSION:
        violations.append("UNSUPPORTED_VERSION")
    if receipt.get("closure_status") not in {CLOSED, HOLD}:
        violations.append("INVALID_CLOSURE_STATUS")
    if receipt.get("candidate_source_basis_derived_from_raw_currentness_inputs") is not True:
        violations.append("SOURCE_BASIS_NOT_DERIVED_FROM_RAW_CURRENTNESS_INPUTS")
    if receipt.get("caller_candidate_binding_accepted") is not False:
        violations.append("CALLER_CANDIDATE_BINDING_ACCEPTED")
    if receipt.get("source_generation_domain_preserved") is not True:
        violations.append("SOURCE_GENERATION_DOMAIN_LOST")
    if receipt.get("graph_witness_producer_proven") is not False:
        violations.append("UNPROVEN_GRAPH_PRODUCER_PROMOTED")
    if receipt.get("source_to_graph_dependency_map_proven") is not False:
        violations.append("UNPROVEN_SOURCE_GRAPH_MAP_PROMOTED")
    if receipt.get("node_level_dependency_cone_proven") is not False:
        violations.append("UNPROVEN_NODE_CONE_PROMOTED")

    candidate = receipt.get("derived_candidate_binding")
    source_observation = receipt.get("source_observation")
    if not isinstance(candidate, dict) or not isinstance(source_observation, dict):
        violations.append("MALFORMED_DERIVED_EVIDENCE")
    else:
        if receipt.get("derived_candidate_binding_identity") != candidate.get("binding_identity"):
            violations.append("DERIVED_CANDIDATE_IDENTITY_MISMATCH")
        if receipt.get("source_observation_identity") != source_observation.get("receipt_identity"):
            violations.append("SOURCE_OBSERVATION_IDENTITY_MISMATCH")
        if candidate.get("source_witnesses") != source_observation.get("o7_source_witnesses"):
            violations.append("DERIVED_CANDIDATE_SOURCE_BASIS_MISMATCH")

    closure = receipt.get("closure_receipt")
    if receipt.get("closure_status") == CLOSED:
        if not isinstance(closure, dict) or closure.get("closure_status") != CLOSED:
            violations.append("CLOSED_WITHOUT_CLOSED_OWNER_RECEIPT")
    authority = receipt.get("authority")
    if not isinstance(authority, dict) or any(bool(value) for value in authority.values()):
        violations.append("AUTHORITY_MINTED_BY_OBSERVATION_BOUND_CLOSURE")

    supplied = receipt.get("receipt_identity")
    without = dict(receipt)
    without.pop("receipt_identity", None)
    if supplied != _identity(without):
        violations.append("RECEIPT_IDENTITY_MISMATCH")
    return violations

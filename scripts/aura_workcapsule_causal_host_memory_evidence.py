#!/usr/bin/env python3
"""Admit exact O42 causal-host evidence into provenance memory without authority transfer.

O42 owns the live-causal artifact + causal-host relation and re-proves its bounded
source/target/O10 world at admission time. PR581 owns typed evidence eligibility and
provenance projection. This membrane binds one exact O42 consequence digest to one
PR581 evidence node while preserving distinct currentness and authority domains.

The O42 host-state vector may be remembered as evidence. PR581 node `current` is
separately supplied eligibility metadata; this module does not infer it from O42,
and memory admission never upgrades the host vector into resolver trust, host
observation authority, semantic truth, trusted continuation, or effect authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from scripts.aura_provenance_corroboration_memory_admission import (
    admit_evidence_nodes,
    verify_context,
    verify_evidence_node,
)
from scripts.aura_workcapsule_live_causal_artifact_causal_host_envelope import (
    admit_live_causal_artifact_causal_host_envelope,
    verify_live_causal_artifact_causal_host_envelope,
)

VERSION = "AURA_WORKCAPSULE_CAUSAL_HOST_MEMORY_EVIDENCE_V1"
EVIDENCE_TYPE = "workcapsule.causal-host-evidence"
ARTIFACT_REF_SCHEME = "workcapsule-causal-host-evidence-sha256"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def causal_host_evidence_ref(receipt: Mapping[str, Any]) -> str:
    return f"{ARTIFACT_REF_SCHEME}:{_sha(dict(receipt))}"


def verify_causal_host_memory_evidence(
    *,
    o42_inputs: Mapping[str, Any],
    evidence_node: Mapping[str, Any],
    context: Mapping[str, Any],
) -> list[str]:
    inputs = dict(o42_inputs) if isinstance(o42_inputs, Mapping) else o42_inputs
    try:
        o42_violations = verify_live_causal_artifact_causal_host_envelope(**inputs)  # type: ignore[arg-type]
    except (KeyError, TypeError, ValueError) as exc:
        return ["O42_INPUT_" + str(exc)]
    if o42_violations:
        return ["O42_" + item for item in o42_violations]

    receipt = admit_live_causal_artifact_causal_host_envelope(**inputs)
    expected_ref = causal_host_evidence_ref(receipt)
    node = dict(evidence_node) if isinstance(evidence_node, Mapping) else evidence_node
    ctx = dict(context) if isinstance(context, Mapping) else context

    node_violations = verify_evidence_node(node)  # type: ignore[arg-type]
    if node_violations:
        return ["MEMORY_NODE_" + item for item in node_violations]
    context_violations = verify_context(ctx)  # type: ignore[arg-type]
    if context_violations:
        return ["MEMORY_CONTEXT_" + item for item in context_violations]

    violations: list[str] = []
    if node["artifact_ref"] != expected_ref:
        violations.append("O42_MEMORY_ARTIFACT_REF_MISMATCH")
    if node["artifact_ref_scheme"] != ARTIFACT_REF_SCHEME:
        violations.append("O42_MEMORY_REF_SCHEME_MISMATCH")
    if node["artifact_ref_value"] != expected_ref.split(":", 1)[1]:
        violations.append("O42_MEMORY_REF_VALUE_MISMATCH")
    if node["evidence_type"] != EVIDENCE_TYPE:
        violations.append("O42_MEMORY_EVIDENCE_TYPE_MISMATCH")
    if violations:
        return violations

    admission = admit_evidence_nodes([copy.deepcopy(node)], copy.deepcopy(ctx))
    if admission["eligible_artifact_refs"] != [expected_ref]:
        reasons = admission["excluded_by_artifact_ref"].get(expected_ref, ["NOT_ELIGIBLE"])
        return ["MEMORY_NOT_ELIGIBLE:" + reason for reason in reasons]
    if admission["input_currentness_reproved_by_this_module"] is not False:
        return ["MEMORY_OWNER_CURRENTNESS_CEILING_WIDENED"]
    if admission["claim_world_semantics_reproved_by_this_module"] is not False:
        return ["MEMORY_OWNER_SEMANTIC_CEILING_WIDENED"]
    if admission["producer_authentication_proven"] is not False:
        return ["MEMORY_OWNER_PRODUCER_AUTH_WIDENED"]
    if admission["effect_authority_proven"] is not False:
        return ["MEMORY_OWNER_EFFECT_AUTHORITY_WIDENED"]
    return []


def admit_causal_host_memory_evidence(**kwargs: Any) -> dict[str, Any]:
    violations = verify_causal_host_memory_evidence(**kwargs)
    if violations:
        raise ValueError("causal-host memory evidence failed: " + ",".join(violations))

    inputs = dict(kwargs["o42_inputs"])
    receipt = admit_live_causal_artifact_causal_host_envelope(**inputs)
    node = copy.deepcopy(dict(kwargs["evidence_node"]))
    context = copy.deepcopy(dict(kwargs["context"]))
    admission = admit_evidence_nodes([node], context)
    ref = causal_host_evidence_ref(receipt)
    states = dict(receipt["host_gate_states"])

    out: dict[str, Any] = {
        "version": VERSION,
        "o42_causal_host_evidence_reproved_at_admission": True,
        "pr581_memory_admission_owner_reused": True,
        "causal_host_evidence_artifact_ref": ref,
        "causal_host_evidence_type": EVIDENCE_TYPE,
        "memory_evidence_eligible": True,
        "remembered_host_gate_states": states,
        "remembered_host_gate_state_vector_sha256": _sha(states),
        "remembered_live_causal_artifact_target_ref": receipt[
            "live_causal_artifact_target_ref"
        ],
        "remembered_causal_post_closure_receipt_identity": copy.deepcopy(
            receipt["causal_post_closure_receipt_identity"]
        ),
        "memory_node_currentness_derived_from_o42": False,
        "memory_currentness_reproved_by_child": False,
        "host_state_currentness_reproved_after_memory_admission": False,
        "memory_admission_promotes_host_observation_authority": False,
        "causal_host_resolver_trust_proven": False,
        "causal_host_observation_authority_proven": False,
        "producer_authentication_proven": False,
        "claim_world_semantics_reproved_by_child": False,
        "semantic_truth_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
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
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": _sha(out),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out

#!/usr/bin/env python3
"""Preserve corroborating causal-proof transport class across typed memory admission.

PR594 proves PR568 and PR572 are distinct corroborating proof artifacts and neither
is a causal host-admission envelope. PR581 V2 owns typed evidence/currentness-domain
memory admission. This adapter derives two memory nodes from the exact PR594
consequence and proves that proof-generation currentness cannot cross-cast into
causal-host-envelope currentness.
"""
from __future__ import annotations

from typing import Any, Mapping

from scripts.aura_provenance_corroboration_memory_admission import (
    NODE_VERSION,
    admit_evidence_nodes,
    seal_evidence_node,
)
from scripts.aura_workcapsule_corroboration_preserves_causal_envelope_class import (
    admit_corroboration_preserves_causal_envelope_class,
)

VERSION = "AURA_WORKCAPSULE_CAUSAL_PROOF_TRANSPORT_CURRENTNESS_MEMORY_V1"
PR594_EXACT_HEAD = "9a5a35a85a47f5a8b47a63e6b3927a055172773e"
PR581_V2_EXACT_HEAD = "4b0cdcef93bfaf09d8bb4545a9e022f922067dc7"
EVIDENCE_TYPE = "workcapsule-corroborating-causal-proof-artifact"
CURRENTNESS_DOMAIN = "causal-proof-generation"
RETRIEVAL_USE = "retrieval"
PROOF_CURRENTNESS_USE = "causal-proof-currentness"
HOST_ENVELOPE_CURRENTNESS_USE = "causal-host-envelope-currentness"

RETRIEVAL_CONTEXT = {
    "scope": "arena",
    "use_class": RETRIEVAL_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
PROOF_CURRENTNESS_CONTEXT = {
    "scope": "arena",
    "use_class": PROOF_CURRENTNESS_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
CAUSAL_HOST_ENVELOPE_CURRENTNESS_CONTEXT = {
    "scope": "arena",
    "use_class": HOST_ENVELOPE_CURRENTNESS_USE,
    "accepted_evidence_types": ["workcapsule-causal-host-admission-envelope"],
    "accepted_currentness_domains": ["causal-host-envelope-generation"],
}
CROSS_TRANSPORT_REJECTION = [
    "USE_CLASS_NOT_ALLOWED",
    "EVIDENCE_TYPE_NOT_ACCEPTED",
    "CURRENTNESS_DOMAIN_NOT_ACCEPTED",
]


def _split_ref(ref: Any) -> tuple[str, str]:
    if type(ref) is not str or ":" not in ref:
        raise ValueError("TYPED_PROOF_ARTIFACT_REF_REQUIRED")
    scheme, value = ref.split(":", 1)
    if not scheme or not value:
        raise ValueError("TYPED_PROOF_ARTIFACT_REF_REQUIRED")
    return scheme, value


def _node(*, ref: str, lineage: str, claim_value_ref: str, world_ref: str) -> dict[str, Any]:
    scheme, value = _split_ref(ref)
    return seal_evidence_node(
        {
            "version": NODE_VERSION,
            "artifact_ref": ref,
            "artifact_ref_scheme": scheme,
            "artifact_ref_value": value,
            "evidence_type": EVIDENCE_TYPE,
            "currentness_domain": CURRENTNESS_DOMAIN,
            "claim_key": "workcapsule:corroborated-causal-proof-fact",
            "claim_value_ref": claim_value_ref,
            "world_ref": world_ref,
            "dependency_class_ref": lineage,
            "generation_ref": "pr594:" + PR594_EXACT_HEAD,
            "allowed_scopes": ["arena"],
            "allowed_use_classes": [RETRIEVAL_USE, PROOF_CURRENTNESS_USE],
            "current": True,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": False,
            "supersedes_artifact_refs": [],
        }
    )


def admit_causal_proof_transport_currentness_memory(
    *,
    causal_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
    pr568_receipt: Mapping[str, Any],
    pr572_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive proof memory nodes and keep them out of host-envelope currentness."""
    relation = admit_corroboration_preserves_causal_envelope_class(
        causal_artifact_host_receipt=causal_artifact_host_receipt,
        causal_raw_slice_host_separation_receipt=causal_raw_slice_host_separation_receipt,
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )
    if relation["proof_artifact_refs_distinct"] is not True:
        raise ValueError("PR594_PROOF_ARTIFACT_DISTINCTION_LOST")
    if relation["pr568_proof_is_causal_host_envelope"] is not False:
        raise ValueError("PR568_TRANSPORT_CLASS_WIDENED")
    if relation["pr572_proof_is_causal_host_envelope"] is not False:
        raise ValueError("PR572_TRANSPORT_CLASS_WIDENED")
    if relation["corroboration_converts_proof_to_causal_host_envelope"] is not False:
        raise ValueError("CORROBORATION_TRANSPORT_CLASS_WIDENED")

    corroboration_identity = relation["pr577_corroboration_receipt_identity"]
    if type(corroboration_identity) is not dict or type(corroboration_identity.get("value")) is not str:
        raise ValueError("PR577_CORROBORATION_IDENTITY_REQUIRED")
    claim_value_ref = "workcapsule-corroboration-sha256:" + corroboration_identity["value"]
    world_ref = claim_value_ref
    left = _node(
        ref=relation["pr568_proof_artifact_ref"],
        lineage="proof-lineage:PR568",
        claim_value_ref=claim_value_ref,
        world_ref=world_ref,
    )
    right = _node(
        ref=relation["pr572_proof_artifact_ref"],
        lineage="proof-lineage:PR572",
        claim_value_ref=claim_value_ref,
        world_ref=world_ref,
    )
    nodes = [left, right]
    retrieval = admit_evidence_nodes(nodes, RETRIEVAL_CONTEXT)
    proof_currentness = admit_evidence_nodes(nodes, PROOF_CURRENTNESS_CONTEXT)
    host_envelope_currentness = admit_evidence_nodes(
        nodes, CAUSAL_HOST_ENVELOPE_CURRENTNESS_CONTEXT
    )

    expected_refs = sorted([left["artifact_ref"], right["artifact_ref"]])
    if retrieval["eligible_artifact_refs"] != expected_refs:
        raise ValueError("CORROBORATING_PROOFS_NOT_RETRIEVABLE")
    if proof_currentness["eligible_artifact_refs"] != expected_refs:
        raise ValueError("CORROBORATING_PROOFS_NOT_CURRENT_IN_OWN_DOMAIN")
    if host_envelope_currentness["eligible_artifact_refs"]:
        raise ValueError("PROOF_CURRENTNESS_CROSS_CAST_TO_CAUSAL_HOST_ENVELOPE")
    for ref in expected_refs:
        if host_envelope_currentness["excluded_by_artifact_ref"].get(ref) != CROSS_TRANSPORT_REJECTION:
            raise ValueError("CAUSAL_HOST_ENVELOPE_REJECTION_NOT_THREE_AXIS_FAIL_CLOSED")

    edges = [row for row in retrieval["relations"] if row["kind"] == "CORROBORATES"]
    if len(edges) != 1:
        raise ValueError("EXPECTED_ONE_CORROBORATION_RELATION")
    if edges[0]["dependency_distinct"] is not True or edges[0]["rank_transition_credit"] is not False:
        raise ValueError("CORROBORATION_RELATION_NOT_DISTINCT_AND_RANK_NEUTRAL")
    if retrieval["corroboration_groups"][0]["kappa"] != 2:
        raise ValueError("CORROBORATION_KAPPA_NOT_TWO")

    return {
        "version": VERSION,
        "pr594_exact_head": PR594_EXACT_HEAD,
        "pr581_v2_exact_head": PR581_V2_EXACT_HEAD,
        "pr594_relation_receipt_identity": relation["receipt_identity"],
        "proof_memory_nodes": nodes,
        "retrieval_admission": retrieval,
        "proof_currentness_admission": proof_currentness,
        "causal_host_envelope_currentness_admission": host_envelope_currentness,
        "two_proof_artifacts_remain_two_memory_nodes": True,
        "corroboration_relation_count": 1,
        "corroboration_kappa": 2,
        "proof_current_in_generation": True,
        "causal_host_envelope_currentness_proven": False,
        "proof_to_host_envelope_type_conversion_performed": False,
        "corroboration_rank_transition_performed": False,
        "producer_authenticated": False,
        "semantic_truth_proven": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "effect_authority_proven": False,
        "semantic_k27_authority_minted": False,
        "native_private_transformer_kv_accessed": False,
    }

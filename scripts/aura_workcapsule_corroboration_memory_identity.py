#!/usr/bin/env python3
"""Project PR587 corroborating proof artifacts into PR581 V2 without identity collapse.

PR587 proves that PR568 and PR572 are distinct proof artifacts that corroborate one
bounded live-causal fact while preserving evidence-class boundaries. PR581 V2 owns
typed, storage-free evidence admission. This adapter re-runs PR587, derives exactly
two memory nodes from its proof-artifact refs, and requires PR581 to preserve both
nodes plus one rank-neutral CORROBORATES edge.

No caller may choose artifact refs, evidence type, currentness domain, dependency
class, claim/world identity, use class, currentness, rank, trust, or authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_provenance_corroboration_memory_admission import (
    NODE_VERSION,
    admit_evidence_nodes,
    seal_evidence_node,
)
from scripts.aura_workcapsule_corroboration_preserves_evidence_classes import (
    admit_corroboration_preserves_evidence_classes,
)

VERSION = "AURA_WORKCAPSULE_CORROBORATION_MEMORY_IDENTITY_V1"
PR587_GENERATION = "406b16b347965f82d79afa1fe3700fa5d1381ef0"
PR581_GENERATION = "4b0cdcef93bfaf09d8bb4545a9e022f922067dc7"
PROOF_TYPE = "workcapsule-live-causal-proof-artifact"
CURRENTNESS_DOMAIN = "corroboration-proof-generation"
USE_CLASS = "corroboration-retrieval"
SCOPE = "arena"
CONTEXT = {
    "scope": SCOPE,
    "use_class": USE_CLASS,
    "accepted_evidence_types": [PROOF_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}


def _bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _identity(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": _sha(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _split_proof_ref(ref: Any) -> tuple[str, str]:
    prefix = "aura-proof-artifact-sha256:"
    if not isinstance(ref, str) or not ref.startswith(prefix):
        raise ValueError("PR587_PROOF_ARTIFACT_REF_INVALID")
    value = ref[len(prefix):]
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError("PR587_PROOF_ARTIFACT_DIGEST_INVALID")
    return "aura-proof-artifact-sha256", value


def _node(*, artifact_ref: str, lineage: str, claim_value_ref: str, world_ref: str) -> dict[str, Any]:
    scheme, value = _split_proof_ref(artifact_ref)
    return seal_evidence_node({
        "version": NODE_VERSION,
        "artifact_ref": artifact_ref,
        "artifact_ref_scheme": scheme,
        "artifact_ref_value": value,
        "evidence_type": PROOF_TYPE,
        "currentness_domain": CURRENTNESS_DOMAIN,
        "claim_key": "workcapsule:live-causal-corroborated-fact",
        "claim_value_ref": claim_value_ref,
        "world_ref": world_ref,
        "dependency_class_ref": f"proof-lineage:{lineage}",
        "generation_ref": f"github:commit:{PR587_GENERATION}:{lineage.lower()}",
        "allowed_scopes": [SCOPE],
        "allowed_use_classes": [USE_CLASS],
        "current": True,
        "digest_verified": True,
        "schema_ok": True,
        "revoked": False,
        "supersedes_artifact_refs": [],
    })


def admit_corroboration_memory_identity(
    *,
    live_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
    pr568_receipt: Mapping[str, Any],
    pr572_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    relation = admit_corroboration_preserves_evidence_classes(
        live_artifact_host_receipt=live_artifact_host_receipt,
        causal_raw_slice_host_separation_receipt=causal_raw_slice_host_separation_receipt,
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )
    if relation["proof_artifact_refs_distinct"] is not True:
        raise ValueError("PR587_PROOF_ARTIFACT_DISTINCTION_LOST")
    a_ref = relation["pr568_proof_artifact_ref"]
    b_ref = relation["pr572_proof_artifact_ref"]
    if a_ref == b_ref:
        raise ValueError("PR587_PROOF_ARTIFACT_REFS_COLLAPSED")
    _split_proof_ref(a_ref)
    _split_proof_ref(b_ref)

    corr_identity = relation["pr577_corroboration_receipt_identity"]
    if not isinstance(corr_identity, dict) or not isinstance(corr_identity.get("value"), str):
        raise ValueError("PR587_CORROBORATION_IDENTITY_MISSING")
    world_ref = "sha256:" + corr_identity["value"]
    claim_value_ref = relation["live_artifact_target_ref"]

    node_a = _node(
        artifact_ref=a_ref,
        lineage="PR568",
        claim_value_ref=claim_value_ref,
        world_ref=world_ref,
    )
    node_b = _node(
        artifact_ref=b_ref,
        lineage="PR572",
        claim_value_ref=claim_value_ref,
        world_ref=world_ref,
    )
    admission = admit_evidence_nodes([node_a, node_b], CONTEXT)

    expected_refs = sorted([a_ref, b_ref])
    if admission["eligible_artifact_refs"] != expected_refs:
        raise ValueError("CORROBORATING_PROOF_ARTIFACTS_NOT_BOTH_ELIGIBLE")
    corroborates = [r for r in admission["relations"] if r["kind"] == "CORROBORATES"]
    if len(corroborates) != 1:
        raise ValueError("CORROBORATION_MEMORY_EDGE_CARDINALITY_NOT_ONE")
    edge = corroborates[0]
    if edge["dependency_distinct"] is not True:
        raise ValueError("CORROBORATION_MEMORY_LINEAGES_NOT_DISTINCT")
    if edge["proof_artifacts_interchangeable"] is not False:
        raise ValueError("CORROBORATION_MEMORY_INTERCHANGEABILITY_WIDENED")
    if edge["rank_transition_credit"] is not False:
        raise ValueError("CORROBORATION_MEMORY_GRANTED_RANK_CREDIT")
    groups = admission["corroboration_groups"]
    if len(groups) != 1 or groups[0]["kappa"] != 2:
        raise ValueError("CORROBORATION_MEMORY_KAPPA_NOT_TWO")

    payload: dict[str, Any] = {
        "version": VERSION,
        "pr587_generation": PR587_GENERATION,
        "pr581_generation": PR581_GENERATION,
        "pr587_relation_receipt_identity": relation["receipt_identity"],
        "pr568_memory_node": node_a,
        "pr572_memory_node": node_b,
        "memory_admission": admission,
        "two_proof_artifacts_preserved": True,
        "one_corroborates_edge_preserved": True,
        "dependency_distinct_kappa": 2,
        "artifact_identity_collapse_performed": False,
        "evidence_class_conversion_performed": False,
        "currentness_domain_cross_cast_performed": False,
        "corroboration_rank_transition_performed": False,
        "generation_bound_currentness_only": True,
        "ambient_currentness_reproved": False,
        "producer_authenticated": False,
        "semantic_truth_proven": False,
        "host_observation_authority_proven": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
    }
    out = dict(payload)
    out["receipt_identity"] = _identity(payload)
    return out

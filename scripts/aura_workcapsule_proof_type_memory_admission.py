#!/usr/bin/env python3
"""Bind PR580 proof-object classes into PR581 V2 typed memory admission.

PR580 proves that live-artifact host evidence and causal raw-slice evidence are
non-interchangeable. PR581 V2 separately types evidence objects and their
currentness domains. This adapter preserves both owners and provides two fixed,
effect-free memory views:

* retrieval: both PR580 evidence objects may be retrieved;
* host-evidence-currentness: only the live-host evidence object is eligible.

No caller may choose evidence type, currentness domain, use class, generation,
currentness, rank, resolver, trust, or authority. ``current=True`` on projected
nodes means only that the sealed node is bound to the exact pinned PR580 proof
generation in its explicitly named evidence-generation domain. It does not prove
ambient repository currentness, producer identity, semantic truth, host authority,
or effect authority.
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
from scripts.aura_workcapsule_live_artifact_raw_slice_noninterchangeability import (
    admit_live_artifact_raw_slice_noninterchangeability,
)

VERSION = "AURA_WORKCAPSULE_PROOF_TYPE_MEMORY_ADMISSION_V2"
VIEWS_VERSION = "AURA_WORKCAPSULE_PROOF_TYPE_MEMORY_VIEWS_V2"
PR580_GENERATION = "5d13a9bd5f939fcf2e281a92114a15e99b929c67"
PR581_GENERATION = "4b0cdcef93bfaf09d8bb4545a9e022f922067dc7"

HOST_EVIDENCE_TYPE = "workcapsule-live-artifact-host-evidence"
RAW_EVIDENCE_TYPE = "workcapsule-causal-raw-slice-evidence"
HOST_CURRENTNESS_DOMAIN = "live-artifact-host-evidence-generation"
RAW_CURRENTNESS_DOMAIN = "causal-raw-slice-evidence-generation"
ARENA_SCOPE = "arena"
RETRIEVAL_USE = "retrieval"
HOST_CURRENTNESS_USE = "host-evidence-currentness"

RETRIEVAL_CONTEXT = {
    "scope": ARENA_SCOPE,
    "use_class": RETRIEVAL_USE,
    "accepted_evidence_types": [HOST_EVIDENCE_TYPE, RAW_EVIDENCE_TYPE],
    "accepted_currentness_domains": [HOST_CURRENTNESS_DOMAIN, RAW_CURRENTNESS_DOMAIN],
}
HOST_CURRENTNESS_CONTEXT = {
    "scope": ARENA_SCOPE,
    "use_class": HOST_CURRENTNESS_USE,
    "accepted_evidence_types": [HOST_EVIDENCE_TYPE],
    "accepted_currentness_domains": [HOST_CURRENTNESS_DOMAIN],
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _identity(payload: dict[str, Any], scope: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": scope,
        "value": _sha(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _split_sha256_ref(value: Any) -> tuple[str, str]:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError("PR580_EVIDENCE_REF_NOT_SHA256")
    digest = value.split(":", 1)[1]
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("PR580_EVIDENCE_REF_INVALID_DIGEST")
    return "sha256", digest


def _node(
    *,
    artifact_ref: str,
    evidence_type: str,
    currentness_domain: str,
    claim_key: str,
    claim_value_ref: str,
    world_ref: str,
    dependency_class_ref: str,
    generation_suffix: str,
    allowed_use_classes: list[str],
) -> dict[str, Any]:
    scheme, value = _split_sha256_ref(artifact_ref)
    return seal_evidence_node(
        {
            "version": NODE_VERSION,
            "artifact_ref": artifact_ref,
            "artifact_ref_scheme": scheme,
            "artifact_ref_value": value,
            "evidence_type": evidence_type,
            "currentness_domain": currentness_domain,
            "claim_key": claim_key,
            "claim_value_ref": claim_value_ref,
            "world_ref": world_ref,
            "dependency_class_ref": dependency_class_ref,
            "generation_ref": f"github:commit:{PR580_GENERATION}:{generation_suffix}",
            "allowed_scopes": [ARENA_SCOPE],
            "allowed_use_classes": list(allowed_use_classes),
            "current": True,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": False,
            "supersedes_artifact_refs": [],
        }
    )


def project_pr580_proof_types_to_memory(
    *,
    live_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive two sealed PR581 V2 nodes from one valid PR580 relation."""
    relation = admit_live_artifact_raw_slice_noninterchangeability(
        live_artifact_host_receipt=live_artifact_host_receipt,
        causal_raw_slice_host_separation_receipt=causal_raw_slice_host_separation_receipt,
    )
    host_ref = relation["live_artifact_host_receipt_ref"]
    raw_ref = relation["causal_raw_slice_host_separation_receipt_ref"]
    _split_sha256_ref(host_ref)
    _split_sha256_ref(raw_ref)
    if host_ref == raw_ref:
        raise ValueError("PR580_EVIDENCE_REFERENCES_COLLAPSED")

    relation_world = "sha256:" + relation["receipt_identity"]["value"]
    host_node = _node(
        artifact_ref=host_ref,
        evidence_type=HOST_EVIDENCE_TYPE,
        currentness_domain=HOST_CURRENTNESS_DOMAIN,
        claim_key="workcapsule:live-artifact-host-evidence",
        claim_value_ref=relation["live_artifact_target_ref"],
        world_ref=relation_world,
        dependency_class_ref="owner:PR575-live-artifact-host-evidence",
        generation_suffix="host",
        allowed_use_classes=[RETRIEVAL_USE, HOST_CURRENTNESS_USE],
    )
    raw_node = _node(
        artifact_ref=raw_ref,
        evidence_type=RAW_EVIDENCE_TYPE,
        currentness_domain=RAW_CURRENTNESS_DOMAIN,
        claim_key="workcapsule:causal-raw-slice-local-evidence",
        claim_value_ref=raw_ref,
        world_ref=relation_world,
        dependency_class_ref="owner:PR574-causal-raw-slice-evidence",
        generation_suffix="raw-slice",
        allowed_use_classes=[RETRIEVAL_USE],
    )

    payload: dict[str, Any] = {
        "version": VERSION,
        "pr580_generation": PR580_GENERATION,
        "pr581_generation": PR581_GENERATION,
        "pr580_relation_receipt_identity": relation["receipt_identity"],
        "live_host_memory_node": host_node,
        "raw_slice_memory_node": raw_node,
        "proof_types_derived_from_pr580_relation": True,
        "currentness_domains_derived_not_caller_selected": True,
        "live_host_and_raw_slice_artifacts_distinct": True,
        "raw_slice_used_as_host_resolution": False,
        "proof_artifacts_interchangeable": False,
        "currentness_domains_interchangeable": False,
        "generation_bound_currentness_only": True,
        "ambient_repository_currentness_reproved": False,
        "producer_authenticated": False,
        "semantic_truth_proven": False,
        "host_observation_authority_proven": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
    }
    out = dict(payload)
    out["receipt_identity"] = _identity(payload, VERSION)
    return out


def admit_pr580_proof_type_memory_views(
    *,
    live_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply fixed retrieval and host-evidence-currentness views."""
    projection = project_pr580_proof_types_to_memory(
        live_artifact_host_receipt=live_artifact_host_receipt,
        causal_raw_slice_host_separation_receipt=causal_raw_slice_host_separation_receipt,
    )
    host = projection["live_host_memory_node"]
    raw = projection["raw_slice_memory_node"]
    nodes = [host, raw]
    retrieval = admit_evidence_nodes(nodes, RETRIEVAL_CONTEXT)
    host_currentness = admit_evidence_nodes(nodes, HOST_CURRENTNESS_CONTEXT)

    expected_retrieval = sorted([host["artifact_ref"], raw["artifact_ref"]])
    if retrieval["eligible_artifact_refs"] != expected_retrieval:
        raise ValueError("RETRIEVAL_VIEW_DID_NOT_ADMIT_BOTH_PR580_EVIDENCE_OBJECTS")
    if host_currentness["eligible_artifact_refs"] != [host["artifact_ref"]]:
        raise ValueError("HOST_CURRENTNESS_VIEW_NOT_LIVE_HOST_ONLY")
    raw_reasons = host_currentness["excluded_by_artifact_ref"].get(raw["artifact_ref"])
    expected_reasons = [
        "USE_CLASS_NOT_ALLOWED",
        "EVIDENCE_TYPE_NOT_ACCEPTED",
        "CURRENTNESS_DOMAIN_NOT_ACCEPTED",
    ]
    if raw_reasons != expected_reasons:
        raise ValueError("RAW_SLICE_HOST_CURRENTNESS_REJECTION_NOT_FAIL_CLOSED")

    payload: dict[str, Any] = {
        "version": VIEWS_VERSION,
        "projection_receipt_identity": projection["receipt_identity"],
        "retrieval_admission": retrieval,
        "host_currentness_admission": host_currentness,
        "retrieval_admits_live_host_evidence": True,
        "retrieval_admits_raw_slice_evidence": True,
        "host_currentness_admits_live_host_evidence": True,
        "host_currentness_admits_raw_slice_evidence": False,
        "raw_slice_host_currentness_rejection_reasons": raw_reasons,
        "caller_selected_evidence_type": False,
        "caller_selected_currentness_domain": False,
        "caller_selected_use_class": False,
        "caller_selected_generation": False,
        "caller_selected_currentness": False,
        "memory_admission_reproves_ambient_currentness": False,
        "corroboration_or_memory_count_grants_host_rank": False,
        "producer_authenticated": False,
        "semantic_truth_proven": False,
        "host_observation_authority_proven": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
    }
    out = dict(payload)
    out["receipt_identity"] = _identity(payload, VIEWS_VERSION)
    return out

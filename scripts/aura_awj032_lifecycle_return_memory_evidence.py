#!/usr/bin/env python3
"""Bind an exact AWJ032 lifecycle-return packet to provenance memory as evidence only.

PR586 owns the C2 -> W4 lifecycle-return identity boundary and explicitly does not
supply lifecycle metric values, physical-I/O attestation, producer authentication,
registry admission, policy victory, G2, or effect authority.

PR581 owns storage-free evidence eligibility/provenance admission.  This membrane
joins those exact consequences narrowly: an eligible PR581 evidence node may point
to the deterministic PR586 packet digest, but evidence admission does not convert
the packet into a W4 lifecycle measurement or any stronger authority object.

Input currentness and claim/world semantics remain supplied PR581 admission metadata;
this module does not re-prove either one.
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
from tools.awj032.glm53_owner_host_c2_handoff import (
    OFFICIAL_MODEL_REPO,
    OFFICIAL_MODEL_REVISION,
)
from tools.awj032.glm53_owner_host_lifecycle_return_packet import (
    PR430_EXACT_HOSTED_HEAD,
    PR430_EXACT_HOSTED_RUN_ID,
    REQUIRED_PRODUCER_LIFECYCLE_METRICS,
    REQUIRED_PRODUCER_PROVENANCE_FIELDS,
    RETURN_PACKET_SCHEMA,
    TARGET_LIFECYCLE_REGISTRY_SCHEMA,
    TARGET_LIFECYCLE_SCHEMA,
    OwnerHostLifecycleReturnPacket,
)

VERSION = "AURA_AWJ032_LIFECYCLE_RETURN_MEMORY_EVIDENCE_V1"
EVIDENCE_TYPE = "awj032.lifecycle-return-packet"
ARTIFACT_REF_SCHEME = "awj032-lifecycle-return-sha256"
CLAIM_CEILING = "D0_C2_TO_W4_RETURN_IDENTITY_ONLY_NO_LIFECYCLE_METRICS_OR_AUTHORITY"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def packet_artifact_ref(packet: OwnerHostLifecycleReturnPacket) -> str:
    return f"{ARTIFACT_REF_SCHEME}:{packet.packet_digest}"


def verify_lifecycle_return_packet_ceiling(packet: Any) -> list[str]:
    """Validate the exact PR586 packet shape/ceiling without inventing W4 evidence."""
    if not isinstance(packet, OwnerHostLifecycleReturnPacket):
        return ["PR586_LIFECYCLE_RETURN_PACKET_REQUIRED"]
    violations: list[str] = []
    if packet.schema != RETURN_PACKET_SCHEMA:
        violations.append("PR586_PACKET_SCHEMA_MISMATCH")
    if packet.claim_ceiling != CLAIM_CEILING:
        violations.append("PR586_CLAIM_CEILING_MISMATCH")
    if packet.model_repo != OFFICIAL_MODEL_REPO or packet.model_revision != OFFICIAL_MODEL_REVISION:
        violations.append("PR586_MODEL_SOURCE_DRIFT")
    if tuple(packet.required_lifecycle_metric_fields) != tuple(REQUIRED_PRODUCER_LIFECYCLE_METRICS):
        violations.append("PR586_REQUIRED_METRIC_FIELDS_DRIFT")
    if tuple(packet.required_lifecycle_provenance_fields) != tuple(REQUIRED_PRODUCER_PROVENANCE_FIELDS):
        violations.append("PR586_REQUIRED_PROVENANCE_FIELDS_DRIFT")
    if packet.target_lifecycle_schema != TARGET_LIFECYCLE_SCHEMA:
        violations.append("PR586_TARGET_LIFECYCLE_SCHEMA_DRIFT")
    if packet.target_lifecycle_registry_schema != TARGET_LIFECYCLE_REGISTRY_SCHEMA:
        violations.append("PR586_TARGET_REGISTRY_SCHEMA_DRIFT")
    if packet.target_pr430_exact_hosted_head != PR430_EXACT_HOSTED_HEAD:
        violations.append("PR586_TARGET_PR430_HEAD_DRIFT")
    if packet.target_pr430_exact_hosted_run_id != PR430_EXACT_HOSTED_RUN_ID:
        violations.append("PR586_TARGET_PR430_RUN_DRIFT")
    for field in (
        "lifecycle_metric_vector_supplied_by_this_packet",
        "physical_io_attested_by_this_packet",
        "producer_authenticated_by_this_packet",
        "lifecycle_registry_verified_by_this_packet",
        "real_w4_policy_winner_proven",
        "full_model_runtime_proven",
        "quality_proven",
        "g2_admitted",
        "effect_authority_proven",
    ):
        if getattr(packet, field) is not False:
            violations.append("PR586_CEILING_WIDENED:" + field)
    if not isinstance(packet.packet_digest, str) or len(packet.packet_digest) != 64:
        violations.append("PR586_PACKET_DIGEST_INVALID")
    return violations


def verify_lifecycle_return_memory_evidence(
    *,
    lifecycle_return_packet: OwnerHostLifecycleReturnPacket,
    evidence_node: Mapping[str, Any],
    context: Mapping[str, Any],
) -> list[str]:
    """Require exact packet->typed evidence binding and parent-owned eligibility."""
    packet_violations = verify_lifecycle_return_packet_ceiling(lifecycle_return_packet)
    if packet_violations:
        return ["PACKET_" + item for item in packet_violations]

    node = dict(evidence_node) if isinstance(evidence_node, Mapping) else evidence_node
    ctx = dict(context) if isinstance(context, Mapping) else context
    node_violations = verify_evidence_node(node)  # type: ignore[arg-type]
    if node_violations:
        return ["MEMORY_NODE_" + item for item in node_violations]
    context_violations = verify_context(ctx)  # type: ignore[arg-type]
    if context_violations:
        return ["MEMORY_CONTEXT_" + item for item in context_violations]

    expected_ref = packet_artifact_ref(lifecycle_return_packet)
    violations: list[str] = []
    if node["artifact_ref"] != expected_ref:
        violations.append("LIFECYCLE_RETURN_PACKET_ARTIFACT_REF_MISMATCH")
    if node["artifact_ref_scheme"] != ARTIFACT_REF_SCHEME:
        violations.append("LIFECYCLE_RETURN_PACKET_REF_SCHEME_MISMATCH")
    if node["artifact_ref_value"] != lifecycle_return_packet.packet_digest:
        violations.append("LIFECYCLE_RETURN_PACKET_REF_VALUE_MISMATCH")
    if node["evidence_type"] != EVIDENCE_TYPE:
        violations.append("LIFECYCLE_RETURN_EVIDENCE_TYPE_MISMATCH")
    if violations:
        return violations

    try:
        admission = admit_evidence_nodes([copy.deepcopy(node)], copy.deepcopy(ctx))
    except ValueError as exc:
        return ["MEMORY_ADMISSION_" + str(exc)]
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


def admit_lifecycle_return_memory_evidence(**kwargs: Any) -> dict[str, Any]:
    violations = verify_lifecycle_return_memory_evidence(**kwargs)
    if violations:
        raise ValueError("lifecycle-return memory evidence failed: " + ",".join(violations))

    packet: OwnerHostLifecycleReturnPacket = kwargs["lifecycle_return_packet"]
    node = copy.deepcopy(dict(kwargs["evidence_node"]))
    context = copy.deepcopy(dict(kwargs["context"]))
    admission = admit_evidence_nodes([node], context)
    expected_ref = packet_artifact_ref(packet)

    out: dict[str, Any] = {
        "version": VERSION,
        "pr586_lifecycle_return_packet_ceiling_verified": True,
        "pr581_memory_admission_owner_reused": True,
        "exact_lifecycle_return_packet_digest": packet.packet_digest,
        "lifecycle_return_evidence_artifact_ref": expected_ref,
        "lifecycle_return_evidence_type": EVIDENCE_TYPE,
        "memory_evidence_node_integrity_checked": True,
        "memory_evidence_eligible": True,
        "memory_eligible_artifact_refs": list(admission["eligible_artifact_refs"]),
        "attempt_telemetry_remembered_as_evidence_only": True,
        "memory_admission_is_lifecycle_measurement_admission": False,
        "memory_admission_is_lifecycle_registry_admission": False,
        "memory_admission_is_real_w4_policy_winner": False,
        "attempt_telemetry_promoted_to_lifecycle_metric_vector": False,
        "attempt_reported_physical_read_bytes_independently_attested": False,
        "input_currentness_reproved_by_child": False,
        "claim_world_semantics_reproved_by_child": False,
        "producer_authentication_proven": False,
        "semantic_truth_proven": False,
        "full_model_runtime_proven": False,
        "quality_proven": False,
        "g2_admitted": False,
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

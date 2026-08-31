#!/usr/bin/env python3
"""Project exact AWJ032 lifecycle-return evidence into one typed currentness domain.

PR590 owns the currentness-aware persistent-cognition substrate and exact C2 join.
PR586 owns the nonmetric C2->W4 lifecycle-return packet. This membrane composes
only the missing relation: an exact lifecycle-return packet may be current in its
own evidence-generation domain without becoming current host-observation evidence
or a W4 lifecycle-measurement receipt.

No caller selects evidence type, currentness domain, use class, memory currentness,
lifecycle metrics, producer trust, registry state, policy winner, G2, effects, or
K27 authority.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_provenance_corroboration_memory_admission import (
    NODE_VERSION,
    admit_evidence_nodes,
    seal_evidence_node,
)
from tools.awj032.glm53_owner_host_c2_handoff import (
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    join_owner_host_c2_attempt,
)
from tools.awj032.glm53_owner_host_lifecycle_return_packet import (
    RETURN_PACKET_SCHEMA,
    TARGET_LIFECYCLE_SCHEMA,
    OwnerHostLifecycleReturnPacket,
    build_owner_host_lifecycle_return_packet,
)

VERSION = "AURA_AWJ032_LIFECYCLE_RETURN_CURRENTNESS_DOMAIN_V1"
PR590_EXACT_HEAD = "3b1da2d20f633109944b416bcc27a30112706964"
PR586_EXACT_HEAD = "aa3fcd9a4cefd18dbc991c3e8a450fcfbbb6726b"

EVIDENCE_TYPE = "awj032-lifecycle-return-packet"
CURRENTNESS_DOMAIN = "awj032-lifecycle-return-generation"
RETRIEVAL_USE = "retrieval"
LIFECYCLE_RETURN_CURRENTNESS_USE = "lifecycle-return-currentness"
HOST_OBSERVATION_CURRENTNESS_USE = "host-observation-currentness"
W4_MEASUREMENT_CURRENTNESS_USE = "w4-lifecycle-measurement-currentness"

RETRIEVAL_CONTEXT = {
    "scope": "awj032",
    "use_class": RETRIEVAL_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
LIFECYCLE_RETURN_CURRENTNESS_CONTEXT = {
    "scope": "awj032",
    "use_class": LIFECYCLE_RETURN_CURRENTNESS_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
HOST_OBSERVATION_CURRENTNESS_CONTEXT = {
    "scope": "awj032",
    "use_class": HOST_OBSERVATION_CURRENTNESS_USE,
    "accepted_evidence_types": ["awj032-owner-host-observation"],
    "accepted_currentness_domains": ["host-observation"],
}
W4_MEASUREMENT_CURRENTNESS_CONTEXT = {
    "scope": "awj032",
    "use_class": W4_MEASUREMENT_CURRENTNESS_USE,
    "accepted_evidence_types": ["w4-lifecycle-measurement-receipt"],
    "accepted_currentness_domains": ["w4-lifecycle-measurement"],
}

CROSS_DOMAIN_REJECTION = [
    "USE_CLASS_NOT_ALLOWED",
    "EVIDENCE_TYPE_NOT_ACCEPTED",
    "CURRENTNESS_DOMAIN_NOT_ACCEPTED",
]


def _assert_packet_ceiling(packet: OwnerHostLifecycleReturnPacket) -> None:
    if type(packet) is not OwnerHostLifecycleReturnPacket:
        raise ValueError("EXACT_LIFECYCLE_RETURN_PACKET_REQUIRED")
    if packet.schema != RETURN_PACKET_SCHEMA:
        raise ValueError("LIFECYCLE_RETURN_SCHEMA_DRIFT")
    if packet.target_lifecycle_schema != TARGET_LIFECYCLE_SCHEMA:
        raise ValueError("W4_TARGET_SCHEMA_DRIFT")
    false_fields = (
        "lifecycle_metric_vector_supplied_by_this_packet",
        "physical_io_attested_by_this_packet",
        "producer_authenticated_by_this_packet",
        "lifecycle_registry_verified_by_this_packet",
        "real_w4_policy_winner_proven",
        "full_model_runtime_proven",
        "quality_proven",
        "g2_admitted",
        "effect_authority_proven",
    )
    for field in false_fields:
        if getattr(packet, field) is not False:
            raise ValueError("LIFECYCLE_RETURN_CEILING_WIDENED:" + field)


def _node_from_packet(packet: OwnerHostLifecycleReturnPacket) -> dict[str, Any]:
    _assert_packet_ceiling(packet)
    digest = packet.packet_digest
    ref = "awj032-lifecycle-return-sha256:" + digest
    return seal_evidence_node(
        {
            "version": NODE_VERSION,
            "artifact_ref": ref,
            "artifact_ref_scheme": "awj032-lifecycle-return-sha256",
            "artifact_ref_value": digest,
            "evidence_type": EVIDENCE_TYPE,
            "currentness_domain": CURRENTNESS_DOMAIN,
            "claim_key": "awj032:lifecycle-return-packet",
            "claim_value_ref": ref,
            "world_ref": "aura-awj032-c2-request-sha256:" + packet.c2_request_digest,
            "dependency_class_ref": "aura-awj032-c2-attempt-sha256:" + packet.c2_attempt_receipt_digest,
            "generation_ref": "pr586:" + PR586_EXACT_HEAD,
            "allowed_scopes": ["arena", "awj032"],
            "allowed_use_classes": [RETRIEVAL_USE, LIFECYCLE_RETURN_CURRENTNESS_USE],
            "current": True,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": False,
            "supersedes_artifact_refs": [],
        }
    )


def project_owner_host_lifecycle_return_memory(
    *,
    request: OwnerHostC2CanaryRequest,
    receipt: OwnerHostC2CanaryReceipt,
) -> dict[str, Any]:
    """Derive the exact PR586 packet and admit it only in its owned currentness domain."""
    join = join_owner_host_c2_attempt(request=request, receipt=receipt)
    packet = build_owner_host_lifecycle_return_packet(
        request=request,
        receipt=receipt,
        join=join,
    )
    _assert_packet_ceiling(packet)
    node = _node_from_packet(packet)

    retrieval = admit_evidence_nodes([node], RETRIEVAL_CONTEXT)
    lifecycle_return_currentness = admit_evidence_nodes(
        [node], LIFECYCLE_RETURN_CURRENTNESS_CONTEXT
    )
    host_observation = admit_evidence_nodes([node], HOST_OBSERVATION_CURRENTNESS_CONTEXT)
    w4_measurement = admit_evidence_nodes([node], W4_MEASUREMENT_CURRENTNESS_CONTEXT)

    ref = node["artifact_ref"]
    if retrieval["eligible_artifact_refs"] != [ref]:
        raise ValueError("LIFECYCLE_RETURN_NOT_RETRIEVABLE")
    if lifecycle_return_currentness["eligible_artifact_refs"] != [ref]:
        raise ValueError("LIFECYCLE_RETURN_NOT_CURRENT_IN_OWN_DOMAIN")
    for name, probe in (
        ("HOST_OBSERVATION", host_observation),
        ("W4_LIFECYCLE_MEASUREMENT", w4_measurement),
    ):
        if probe["eligible_artifact_refs"]:
            raise ValueError(name + "_CURRENTNESS_CROSS_CAST")
        if probe["excluded_by_artifact_ref"].get(ref) != CROSS_DOMAIN_REJECTION:
            raise ValueError(name + "_REJECTION_NOT_THREE_AXIS_FAIL_CLOSED")

    return {
        "version": VERSION,
        "pr590_exact_head": PR590_EXACT_HEAD,
        "pr586_exact_head": PR586_EXACT_HEAD,
        "parent_c2_join_logical_id": join.logical_id,
        "lifecycle_return_packet_digest": packet.packet_digest,
        "evidence_node": node,
        "retrieval_admission": retrieval,
        "lifecycle_return_currentness_admission": lifecycle_return_currentness,
        "host_observation_currentness_admission": host_observation,
        "w4_lifecycle_measurement_currentness_admission": w4_measurement,
        "current_true_is_lifecycle_return_generation_scoped": True,
        "lifecycle_return_current_in_generation": True,
        "host_observation_currentness_proven": False,
        "lifecycle_measurement_currentness_proven": False,
        "lifecycle_measurement_receipt_present": False,
        "physical_io_attested": False,
        "producer_authenticated": False,
        "lifecycle_registry_admitted": False,
        "real_w4_policy_winner_proven": False,
        "full_model_runtime_proven": False,
        "quality_proven": False,
        "g2_admitted": False,
        "host_rank_transition_performed": False,
        "effect_authority_proven": False,
        "semantic_truth_proven": False,
        "native_private_transformer_kv_accessed": False,
        "semantic_k27_authority_minted": False,
    }

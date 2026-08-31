#!/usr/bin/env python3
"""Project a bounded ThinkPad storage observation into its owned currentness domain.

PR601 owns typed currentness-domain separation. PR603 owns one real bounded,
read-only buffered file-window observation. This membrane composes only the
missing relation: a valid storage-probe receipt can be current in its own
observation generation without becoming lifecycle-return currentness,
host-observation currentness, W4 lifecycle-measurement currentness, physical
NVMe currentness, producer authentication, model execution, G2, or effects.
"""
from __future__ import annotations

import math
import re
from typing import Any

from scripts.aura_awj032_lifecycle_return_currentness_domain import (
    CROSS_DOMAIN_REJECTION,
    HOST_OBSERVATION_CURRENTNESS_CONTEXT,
    LIFECYCLE_RETURN_CURRENTNESS_CONTEXT,
    W4_MEASUREMENT_CURRENTNESS_CONTEXT,
)
from scripts.aura_provenance_corroboration_memory_admission import (
    NODE_VERSION,
    admit_evidence_nodes,
    seal_evidence_node,
)
from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.thinkpad_bounded_storage_probe import (
    PROBE_MODE,
    PROBE_SCHEMA,
    ThinkPadStorageProbeReceipt,
)

VERSION = "AURA_AWJ032_STORAGE_PROBE_CURRENTNESS_DOMAIN_V1"
PR601_EXACT_HEAD = "5244eaf015abf71293c4e5a92fd1f32c3c2824fb"
PR603_EXACT_HEAD = "9b24b5b99901bdfb5406e0a28aeb8caa0fbf304a"
EVIDENCE_TYPE = "awj032-thinkpad-bounded-storage-probe"
CURRENTNESS_DOMAIN = "awj032-storage-probe-generation"
RETRIEVAL_USE = "retrieval"
STORAGE_PROBE_CURRENTNESS_USE = "storage-probe-currentness"
PHYSICAL_NVME_CURRENTNESS_USE = "physical-nvme-currentness"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

RETRIEVAL_CONTEXT = {
    "scope": "awj032",
    "use_class": RETRIEVAL_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
STORAGE_PROBE_CURRENTNESS_CONTEXT = {
    "scope": "awj032",
    "use_class": STORAGE_PROBE_CURRENTNESS_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
PHYSICAL_NVME_CURRENTNESS_CONTEXT = {
    "scope": "awj032",
    "use_class": PHYSICAL_NVME_CURRENTNESS_USE,
    "accepted_evidence_types": ["awj032-physical-nvme-observation"],
    "accepted_currentness_domains": ["physical-nvme-observation"],
}


def _require_hex64(name: str, value: Any) -> None:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise ValueError("INVALID_SHA256:" + name)


def _assert_probe_receipt(
    request: OwnerHostC2CanaryRequest,
    probe_receipt: ThinkPadStorageProbeReceipt,
) -> None:
    if type(request) is not OwnerHostC2CanaryRequest:
        raise ValueError("EXACT_C2_REQUEST_REQUIRED")
    if type(probe_receipt) is not ThinkPadStorageProbeReceipt:
        raise ValueError("EXACT_STORAGE_PROBE_RECEIPT_REQUIRED")
    if probe_receipt.schema != PROBE_SCHEMA:
        raise ValueError("STORAGE_PROBE_SCHEMA_DRIFT")
    if probe_receipt.probe_mode != PROBE_MODE:
        raise ValueError("STORAGE_PROBE_MODE_DRIFT")
    if probe_receipt.request_digest != request.request_digest:
        raise ValueError("STORAGE_PROBE_REQUEST_DIGEST_MISMATCH")

    false_fields = (
        "page_cache_bypass_proven",
        "physical_nvme_io_attested",
        "storage_medium_nvme_proven",
        "producer_authenticated",
        "model_execution_observed",
        "lifecycle_measurement_admitted",
        "effect_authority_proven",
        "g2_admitted",
    )
    for field in false_fields:
        if getattr(probe_receipt, field) is not False:
            raise ValueError("STORAGE_PROBE_CEILING_WIDENED:" + field)

    _require_hex64("file_identity_digest", probe_receipt.file_identity_digest)
    _require_hex64("window_sha256", probe_receipt.window_sha256)
    _require_hex64("receipt_digest", probe_receipt.receipt_digest)
    if probe_receipt.evidence_ref != (
        "awj032-thinkpad-storage-probe-sha256:" + probe_receipt.receipt_digest
    ):
        raise ValueError("STORAGE_PROBE_EVIDENCE_REF_DRIFT")
    if type(probe_receipt.relative_path) is not str or not probe_receipt.relative_path.strip():
        raise ValueError("STORAGE_PROBE_RELATIVE_PATH_INVALID")
    for name in (
        "file_size_bytes",
        "byte_offset",
        "requested_probe_bytes",
        "logical_bytes_read",
        "read_operations",
        "chunk_bytes",
    ):
        value = getattr(probe_receipt, name)
        if type(value) is not int or value < 0:
            raise ValueError("STORAGE_PROBE_INTEGER_INVALID:" + name)
    if probe_receipt.requested_probe_bytes <= 0:
        raise ValueError("STORAGE_PROBE_REQUESTED_BYTES_INVALID")
    if not 0 < probe_receipt.logical_bytes_read <= probe_receipt.requested_probe_bytes:
        raise ValueError("STORAGE_PROBE_LOGICAL_BYTES_INVALID")
    if probe_receipt.read_operations <= 0 or probe_receipt.chunk_bytes <= 0:
        raise ValueError("STORAGE_PROBE_READ_ACCOUNTING_INVALID")
    if type(probe_receipt.eof_reached) is not bool:
        raise ValueError("STORAGE_PROBE_EOF_BOOLEAN_INVALID")
    for name in ("elapsed_seconds", "observed_logical_read_bytes_per_second"):
        value = getattr(probe_receipt, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("STORAGE_PROBE_FLOAT_INVALID:" + name)
        if not math.isfinite(float(value)) or float(value) <= 0:
            raise ValueError("STORAGE_PROBE_FLOAT_INVALID:" + name)
    expected_bps = probe_receipt.logical_bytes_read / probe_receipt.elapsed_seconds
    if not math.isclose(
        probe_receipt.observed_logical_read_bytes_per_second,
        expected_bps,
        rel_tol=1e-12,
        abs_tol=1e-9,
    ):
        raise ValueError("STORAGE_PROBE_BPS_ACCOUNTING_MISMATCH")


def _node_from_probe(probe_receipt: ThinkPadStorageProbeReceipt) -> dict[str, Any]:
    return seal_evidence_node(
        {
            "version": NODE_VERSION,
            "artifact_ref": probe_receipt.evidence_ref,
            "artifact_ref_scheme": "awj032-thinkpad-storage-probe-sha256",
            "artifact_ref_value": probe_receipt.receipt_digest,
            "evidence_type": EVIDENCE_TYPE,
            "currentness_domain": CURRENTNESS_DOMAIN,
            "claim_key": "awj032:thinkpad-bounded-storage-probe",
            "claim_value_ref": probe_receipt.evidence_ref,
            "world_ref": "aura-awj032-c2-request-sha256:" + probe_receipt.request_digest,
            "dependency_class_ref": (
                "awj032-storage-file-identity-sha256:" + probe_receipt.file_identity_digest
            ),
            "generation_ref": "pr603:" + PR603_EXACT_HEAD,
            "allowed_scopes": ["arena", "awj032"],
            "allowed_use_classes": [RETRIEVAL_USE, STORAGE_PROBE_CURRENTNESS_USE],
            "current": True,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": False,
            "supersedes_artifact_refs": [],
        }
    )


def project_bounded_storage_probe_currentness(
    *,
    request: OwnerHostC2CanaryRequest,
    probe_receipt: ThinkPadStorageProbeReceipt,
) -> dict[str, Any]:
    """Admit exact storage observation only in its owned evidence/currentness domain."""
    _assert_probe_receipt(request, probe_receipt)
    node = _node_from_probe(probe_receipt)
    ref = node["artifact_ref"]

    retrieval = admit_evidence_nodes([node], RETRIEVAL_CONTEXT)
    own = admit_evidence_nodes([node], STORAGE_PROBE_CURRENTNESS_CONTEXT)
    lifecycle_return = admit_evidence_nodes([node], LIFECYCLE_RETURN_CURRENTNESS_CONTEXT)
    host_observation = admit_evidence_nodes([node], HOST_OBSERVATION_CURRENTNESS_CONTEXT)
    w4_measurement = admit_evidence_nodes([node], W4_MEASUREMENT_CURRENTNESS_CONTEXT)
    physical_nvme = admit_evidence_nodes([node], PHYSICAL_NVME_CURRENTNESS_CONTEXT)

    if retrieval["eligible_artifact_refs"] != [ref]:
        raise ValueError("STORAGE_PROBE_NOT_RETRIEVABLE")
    if own["eligible_artifact_refs"] != [ref]:
        raise ValueError("STORAGE_PROBE_NOT_CURRENT_IN_OWN_DOMAIN")
    for name, admission in (
        ("LIFECYCLE_RETURN", lifecycle_return),
        ("HOST_OBSERVATION", host_observation),
        ("W4_LIFECYCLE_MEASUREMENT", w4_measurement),
        ("PHYSICAL_NVME", physical_nvme),
    ):
        if admission["eligible_artifact_refs"]:
            raise ValueError(name + "_CURRENTNESS_CROSS_CAST")
        if admission["excluded_by_artifact_ref"].get(ref) != CROSS_DOMAIN_REJECTION:
            raise ValueError(name + "_REJECTION_NOT_THREE_AXIS_FAIL_CLOSED")

    return {
        "version": VERSION,
        "pr601_exact_head": PR601_EXACT_HEAD,
        "pr603_exact_head": PR603_EXACT_HEAD,
        "storage_probe_receipt_digest": probe_receipt.receipt_digest,
        "evidence_node": node,
        "retrieval_admission": retrieval,
        "storage_probe_currentness_admission": own,
        "lifecycle_return_currentness_admission": lifecycle_return,
        "host_observation_currentness_admission": host_observation,
        "w4_lifecycle_measurement_currentness_admission": w4_measurement,
        "physical_nvme_currentness_admission": physical_nvme,
        "current_true_is_storage_probe_generation_scoped": True,
        "storage_probe_current_in_generation": True,
        "lifecycle_return_currentness_proven": False,
        "host_observation_currentness_proven": False,
        "w4_lifecycle_measurement_currentness_proven": False,
        "physical_nvme_currentness_proven": False,
        "physical_io_attested": False,
        "storage_medium_nvme_proven": False,
        "producer_authenticated": False,
        "model_execution_observed": False,
        "lifecycle_registry_admitted": False,
        "real_w4_policy_winner_proven": False,
        "g2_admitted": False,
        "host_rank_transition_performed": False,
        "effect_authority_proven": False,
        "semantic_truth_proven": False,
        "native_private_transformer_kv_accessed": False,
        "semantic_k27_authority_minted": False,
    }

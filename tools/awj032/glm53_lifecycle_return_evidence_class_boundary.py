"""Preserve the evidence class of an AWJ032 GLM-5.3 C2 lifecycle return packet.

A C2 return packet is transport/integrity evidence about one owner-host attempt. It may
name the downstream lifecycle schema and carry attempt-reported counters, but it is not
itself a producer-owned W4LifecycleMeasurementReceiptV1 and cannot become one through
rewrapping, corroboration, shared references, or digest preservation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.awj032.glm53_owner_host_lifecycle_return_packet import (
    RETURN_PACKET_SCHEMA,
    TARGET_LIFECYCLE_REGISTRY_SCHEMA,
    TARGET_LIFECYCLE_SCHEMA,
    REQUIRED_PRODUCER_LIFECYCLE_METRICS,
    REQUIRED_PRODUCER_PROVENANCE_FIELDS,
    OwnerHostLifecycleReturnPacket,
)

BOUNDARY_SCHEMA = "AWJ032GLM53LifecycleReturnEvidenceClassBoundaryV1"
INPUT_EVIDENCE_CLASS = "C2_ATTEMPT_RETURN_PACKET"
TARGET_EVIDENCE_CLASS = "OWNER_HOST_LIFECYCLE_MEASUREMENT"
CLAIM_CEILING = "D0_EVIDENCE_CLASS_PRESERVATION_ONLY_NO_LIFECYCLE_PRODUCER_AUTH_OR_G2"


class LifecycleReturnEvidenceClassError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LifecycleReturnEvidenceClassError("NONCANONICAL_EVIDENCE_CLASS_RECEIPT") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _exact_false(name: str, value: Any) -> None:
    if type(value) is not bool or value is not False:
        raise LifecycleReturnEvidenceClassError("RETURN_PACKET_CEILING_WIDENED", name)


@dataclass(frozen=True)
class LifecycleReturnEvidenceClassReceipt:
    input_packet_digest: str
    c2_request_digest: str
    c2_attempt_receipt_digest: str
    lifecycle_measurement_ref: str
    input_schema: str = RETURN_PACKET_SCHEMA
    input_evidence_class: str = INPUT_EVIDENCE_CLASS
    output_evidence_class: str = INPUT_EVIDENCE_CLASS
    target_lifecycle_schema: str = TARGET_LIFECYCLE_SCHEMA
    target_lifecycle_registry_schema: str = TARGET_LIFECYCLE_REGISTRY_SCHEMA
    target_evidence_class: str = TARGET_EVIDENCE_CLASS
    same_lifecycle_reference_is_type_conversion: bool = False
    attempt_counters_are_lifecycle_metrics: bool = False
    corroboration_can_upgrade_evidence_class: bool = False
    digest_preservation_can_upgrade_evidence_class: bool = False
    cross_cast_to_lifecycle_measurement_receipt_permitted: bool = False
    independent_lifecycle_producer_receipt_required: bool = True
    independent_registry_verification_required: bool = True
    producer_authenticated: bool = False
    lifecycle_registry_verified: bool = False
    real_w4_policy_winner_proven: bool = False
    full_model_runtime_proven: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    effect_authority_proven: bool = False
    schema: str = BOUNDARY_SCHEMA
    claim_ceiling: str = CLAIM_CEILING

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _digest(self.to_dict())


def preserve_lifecycle_return_evidence_class(
    *, packet: OwnerHostLifecycleReturnPacket
) -> LifecycleReturnEvidenceClassReceipt:
    """Prove the return packet stays in its original evidence class.

    The strict exact type check prevents mappings/subclasses from adding lifecycle metrics,
    trust flags, rank overrides, or alternate schemas at this boundary.
    """
    if type(packet) is not OwnerHostLifecycleReturnPacket:
        raise LifecycleReturnEvidenceClassError("EXACT_C2_RETURN_PACKET_REQUIRED")
    if packet.schema != RETURN_PACKET_SCHEMA:
        raise LifecycleReturnEvidenceClassError("RETURN_PACKET_SCHEMA_MISMATCH")
    if packet.target_lifecycle_schema != TARGET_LIFECYCLE_SCHEMA:
        raise LifecycleReturnEvidenceClassError("TARGET_LIFECYCLE_SCHEMA_DRIFT")
    if packet.target_lifecycle_registry_schema != TARGET_LIFECYCLE_REGISTRY_SCHEMA:
        raise LifecycleReturnEvidenceClassError("TARGET_LIFECYCLE_REGISTRY_SCHEMA_DRIFT")
    if tuple(packet.required_lifecycle_metric_fields) != REQUIRED_PRODUCER_LIFECYCLE_METRICS:
        raise LifecycleReturnEvidenceClassError("LIFECYCLE_METRIC_CATALOG_DRIFT")
    if tuple(packet.required_lifecycle_provenance_fields) != REQUIRED_PRODUCER_PROVENANCE_FIELDS:
        raise LifecycleReturnEvidenceClassError("LIFECYCLE_PROVENANCE_CATALOG_DRIFT")

    for metric_name in REQUIRED_PRODUCER_LIFECYCLE_METRICS:
        if hasattr(packet, metric_name):
            raise LifecycleReturnEvidenceClassError("LIFECYCLE_METRIC_VALUE_CROSS_CAST", metric_name)
    for name in (
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
        _exact_false(name, getattr(packet, name))

    return LifecycleReturnEvidenceClassReceipt(
        input_packet_digest=packet.packet_digest,
        c2_request_digest=packet.c2_request_digest,
        c2_attempt_receipt_digest=packet.c2_attempt_receipt_digest,
        lifecycle_measurement_ref=packet.lifecycle_measurement_ref,
    )

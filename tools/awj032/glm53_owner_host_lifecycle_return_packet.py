"""Fail-closed AWJ032 GLM-5.3 owner-host lifecycle return membrane.

This module composes the exact C2 handoff consequence with the independently hosted
W4 registered-lifecycle evidence boundary without fabricating lifecycle metrics.

It may carry C2 attempt identity and attempt-reported counters forward, but it never
accepts cache-hit ratio, energy, peak RAM, warmup/restart/revalidation, or control-
overhead measurements. Those remain producer-owned fields of the downstream
W4LifecycleMeasurementReceiptV1 contract and require independent registry admission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.awj032.glm53_owner_host_c2_handoff import (
    OFFICIAL_MODEL_REPO,
    OFFICIAL_MODEL_REVISION,
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    OwnerHostC2JoinReceipt,
    join_owner_host_c2_attempt,
)

RETURN_PACKET_SCHEMA = "AWJ032GLM53OwnerHostLifecycleReturnPacketV1"
TARGET_LIFECYCLE_SCHEMA = "W4LifecycleMeasurementReceiptV1"
TARGET_LIFECYCLE_REGISTRY_SCHEMA = "W4LifecycleMeasurementRegistryRecordV1"
PR430_EXACT_HOSTED_HEAD = "a580b01371cf8da93cf2f2e546cd7ee9638969ca"
PR430_EXACT_HOSTED_RUN_ID = 33340830662

# Names only. No values for these producer-owned metrics are accepted by this module.
REQUIRED_PRODUCER_LIFECYCLE_METRICS = (
    "cache_hit_ratio",
    "energy_joules",
    "peak_resident_bytes",
    "warmup_seconds",
    "restart_seconds",
    "revalidation_seconds",
    "control_overhead_seconds",
)

REQUIRED_PRODUCER_PROVENANCE_FIELDS = (
    "owner_host_request_digest",
    "owner_host_observation_digest",
    "owner_host_attestation_ref",
    "scope_ref",
    "source_generation",
    "workload_ref",
    "measurement_campaign_ref",
    "policy_id",
    "preflight_receipt_digest",
    "observer_ref",
    "observer_generation",
    "producer_run_ref",
    "runner_class",
    "runner_instance_ref",
    "physical_io_attested",
    "correctness_reference_equivalent",
    "source_current",
    "measurement_current",
    "independently_observed",
)


class OwnerHostLifecycleReturnError(ValueError):
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
        raise OwnerHostLifecycleReturnError("NONCANONICAL_RETURN_PACKET") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class OwnerHostLifecycleReturnPacket:
    c2_request_digest: str
    c2_attempt_receipt_digest: str
    c2_join_logical_id: str
    lifecycle_measurement_ref: str
    owner_host_observation_id: str
    runner_identity: str
    runner_generation: str
    preflight_receipt_digest: str
    airllm_source_revision: str
    model_repo: str
    model_revision: str
    host_measurement_ref: str
    attempt_reported_payload_bytes: int
    attempt_reported_tensor_read_operations: int
    attempt_reported_physical_read_bytes: int
    attempt_reported_elapsed_seconds: float
    attempt_process_exit_code: int
    attempt_generated_token_count: int
    attempt_generated_output_sha256: str | None
    canary_process_succeeded: bool
    generated_output_observed: bool
    required_lifecycle_metric_fields: tuple[str, ...] = REQUIRED_PRODUCER_LIFECYCLE_METRICS
    required_lifecycle_provenance_fields: tuple[str, ...] = REQUIRED_PRODUCER_PROVENANCE_FIELDS
    target_lifecycle_schema: str = TARGET_LIFECYCLE_SCHEMA
    target_lifecycle_registry_schema: str = TARGET_LIFECYCLE_REGISTRY_SCHEMA
    target_pr430_exact_hosted_head: str = PR430_EXACT_HOSTED_HEAD
    target_pr430_exact_hosted_run_id: int = PR430_EXACT_HOSTED_RUN_ID
    lifecycle_metric_vector_supplied_by_this_packet: bool = False
    physical_io_attested_by_this_packet: bool = False
    producer_authenticated_by_this_packet: bool = False
    lifecycle_registry_verified_by_this_packet: bool = False
    real_w4_policy_winner_proven: bool = False
    full_model_runtime_proven: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    effect_authority_proven: bool = False
    schema: str = RETURN_PACKET_SCHEMA
    claim_ceiling: str = "D0_C2_TO_W4_RETURN_IDENTITY_ONLY_NO_LIFECYCLE_METRICS_OR_AUTHORITY"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def packet_digest(self) -> str:
        return _digest(self.to_dict())


def build_owner_host_lifecycle_return_packet(
    *,
    request: OwnerHostC2CanaryRequest,
    receipt: OwnerHostC2CanaryReceipt,
    join: OwnerHostC2JoinReceipt,
) -> OwnerHostLifecycleReturnPacket:
    """Bind one C2 attempt to the W4 return seam without minting lifecycle metrics."""
    if not isinstance(request, OwnerHostC2CanaryRequest):
        raise OwnerHostLifecycleReturnError("C2_REQUEST_REQUIRED")
    if not isinstance(receipt, OwnerHostC2CanaryReceipt):
        raise OwnerHostLifecycleReturnError("C2_ATTEMPT_RECEIPT_REQUIRED")
    if not isinstance(join, OwnerHostC2JoinReceipt):
        raise OwnerHostLifecycleReturnError("C2_JOIN_RECEIPT_REQUIRED")

    # Recompute the parent relation rather than trusting a caller-authored join object.
    expected_join = join_owner_host_c2_attempt(request=request, receipt=receipt)
    if join.to_dict() != expected_join.to_dict():
        raise OwnerHostLifecycleReturnError("C2_JOIN_NOT_EXACT_PARENT_CONSEQUENCE")
    if receipt.lifecycle_measurement_ref != join.lifecycle_measurement_ref:
        raise OwnerHostLifecycleReturnError("LIFECYCLE_MEASUREMENT_REF_DRIFT")
    if join.request_digest != request.request_digest:
        raise OwnerHostLifecycleReturnError("C2_REQUEST_IDENTITY_DRIFT")
    if join.attempt_receipt_digest != receipt.receipt_digest:
        raise OwnerHostLifecycleReturnError("C2_ATTEMPT_IDENTITY_DRIFT")
    if join.preflight_receipt_digest != request.preflight_receipt_digest:
        raise OwnerHostLifecycleReturnError("PREFLIGHT_IDENTITY_DRIFT")

    # Parent consequence must remain explicitly below the W4 producer/registry boundary.
    if join.producer_authentication_required is not True:
        raise OwnerHostLifecycleReturnError("PRODUCER_AUTHENTICATION_REQUIREMENT_REMOVED")
    if join.lifecycle_registry_required is not True:
        raise OwnerHostLifecycleReturnError("LIFECYCLE_REGISTRY_REQUIREMENT_REMOVED")
    for name, value in (
        ("real_w4_policy_winner_proven", join.real_w4_policy_winner_proven),
        ("full_model_runtime_proven", join.full_model_runtime_proven),
        ("g2_admitted", join.g2_admitted),
        ("effect_authority_proven", join.effect_authority_proven),
    ):
        if value is not False:
            raise OwnerHostLifecycleReturnError("C2_PARENT_CEILING_WIDENED", name)

    if receipt.model_repo != OFFICIAL_MODEL_REPO or receipt.model_revision != OFFICIAL_MODEL_REVISION:
        raise OwnerHostLifecycleReturnError("MODEL_SOURCE_DRIFT")

    return OwnerHostLifecycleReturnPacket(
        c2_request_digest=request.request_digest,
        c2_attempt_receipt_digest=receipt.receipt_digest,
        c2_join_logical_id=join.logical_id,
        lifecycle_measurement_ref=receipt.lifecycle_measurement_ref,
        owner_host_observation_id=receipt.owner_host_observation_id,
        runner_identity=receipt.runner_identity,
        runner_generation=receipt.runner_generation,
        preflight_receipt_digest=request.preflight_receipt_digest,
        airllm_source_revision=receipt.airllm_source_revision,
        model_repo=receipt.model_repo,
        model_revision=receipt.model_revision,
        host_measurement_ref=receipt.host_measurement_ref,
        attempt_reported_payload_bytes=receipt.actual_payload_bytes,
        attempt_reported_tensor_read_operations=receipt.tensor_read_operations,
        attempt_reported_physical_read_bytes=receipt.physical_read_bytes,
        attempt_reported_elapsed_seconds=receipt.elapsed_seconds,
        attempt_process_exit_code=receipt.process_exit_code,
        attempt_generated_token_count=receipt.generated_token_count,
        attempt_generated_output_sha256=receipt.generated_output_sha256,
        canary_process_succeeded=join.canary_process_succeeded,
        generated_output_observed=join.generated_output_observed,
    )

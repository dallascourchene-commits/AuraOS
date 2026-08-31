"""Bind one deterministic ThinkPad storage-plan window to bounded logical-read evidence.

This module composes the exact PR599 planning owner with the exact PR603
read-only storage-probe owner.  It deliberately proves only that a byte window
derived from one deterministic plan decision was logically observed through
PR603's buffered ``pread`` membrane.  It does not prove that the plan was
executed, that the planned backend serviced the read, that the storage medium
was NVMe, that caches were bypassed, or that any performance/effect authority
was earned.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.thinkpad_bounded_storage_probe import (
    MAX_PROBE_BYTES,
    ThinkPadStorageProbeReceipt,
    run_bounded_storage_probe,
)
from tools.awj032.thinkpad_nvme_residency_plan import ThinkPadResidencyPlan

SCHEMA = "AWJ032ThinkPadPlanBoundStorageProbeV1"


class PlanBoundStorageProbeError(ValueError):
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
        raise PlanBoundStorageProbeError("NONCANONICAL_BOUND_PROBE_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanBoundStorageProbeError(code)
    return value.strip()


def _validate_plan_ceiling(plan: ThinkPadResidencyPlan) -> None:
    if (
        plan.physical_io_observed
        or plan.model_execution_observed
        or plan.producer_authenticated
        or plan.performance_claimed
        or plan.effect_authority_proven
        or plan.g2_admitted
    ):
        raise PlanBoundStorageProbeError("PLAN_NONEXECUTION_CEILING_WIDENED")


def _select_decision(plan: ThinkPadResidencyPlan, tensor_id: str):
    wanted = _text(tensor_id, "TENSOR_ID_REQUIRED")
    matches = tuple(d for d in plan.decisions if d.tensor_id == wanted)
    if len(matches) != 1:
        raise PlanBoundStorageProbeError("EXACT_ONE_PLAN_DECISION_REQUIRED", wanted)
    return matches[0]


@dataclass(frozen=True)
class PlanBoundStorageProbeReceipt:
    plan_digest: str
    request_digest: str
    tensor_id: str
    storage_object_ref: str
    planned_mode: str
    planned_aligned_byte_offset: int
    planned_aligned_byte_length: int
    observation_window_byte_offset: int
    observation_window_bytes: int
    full_planned_window_observed: bool
    logical_probe_receipt_digest: str
    logical_probe_evidence_ref: str
    logical_window_sha256: str
    logical_bytes_read: int
    logical_read_operations: int
    logical_read_bytes_per_second: float
    logical_read_observed: bool = True
    plan_identity_bound: bool = True
    planned_backend_observed: bool = False
    planned_backend_executed: bool = False
    storage_plan_compliance_proven: bool = False
    page_cache_bypass_proven: bool = False
    os_page_cache_cold_proven: bool = False
    device_cache_cold_proven: bool = False
    physical_nvme_io_attested: bool = False
    storage_medium_nvme_proven: bool = False
    producer_authenticated: bool = False
    model_execution_observed: bool = False
    lifecycle_measurement_admitted: bool = False
    performance_winner_proven: bool = False
    effect_authority_proven: bool = False
    w4_admitted: bool = False
    g2_admitted: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _digest(self.to_dict())


def run_plan_bound_storage_probe(
    *,
    plan: ThinkPadResidencyPlan,
    request: OwnerHostC2CanaryRequest,
    tensor_id: str,
    chunk_bytes: int,
    max_wall_seconds: float,
) -> PlanBoundStorageProbeReceipt:
    """Observe a deterministic bounded subwindow of one exact plan decision.

    ``storage_plan_digest``, path, byte offset and observation-window length are
    all derived from the typed plan/request pair.  No caller-supplied backend,
    physical-I/O, cache-state, trust or authority assertion is accepted.
    """
    if type(plan) is not ThinkPadResidencyPlan:
        raise PlanBoundStorageProbeError("EXACT_PLAN_TYPE_REQUIRED")
    if type(request) is not OwnerHostC2CanaryRequest:
        raise PlanBoundStorageProbeError("EXACT_C2_REQUEST_TYPE_REQUIRED")
    _validate_plan_ceiling(plan)
    if request.execution_authorized_by_this_contract is not False or request.g2_admitted is not False:
        raise PlanBoundStorageProbeError("C2_REQUEST_AUTHORITY_WIDENED")
    if request.storage_plan_digest != plan.storage_plan_digest:
        raise PlanBoundStorageProbeError("REQUEST_PLAN_DIGEST_MISMATCH")

    decision = _select_decision(plan, tensor_id)
    if decision.aligned_byte_length <= 0:
        raise PlanBoundStorageProbeError("PLANNED_WINDOW_EMPTY")

    observation_window_bytes = min(
        decision.aligned_byte_length,
        request.max_payload_bytes,
        MAX_PROBE_BYTES,
    )
    if observation_window_bytes <= 0:
        raise PlanBoundStorageProbeError("OBSERVATION_WINDOW_EMPTY")

    probe: ThinkPadStorageProbeReceipt = run_bounded_storage_probe(
        request=request,
        relative_path=decision.storage_object_ref,
        byte_offset=decision.aligned_byte_offset,
        probe_bytes=observation_window_bytes,
        chunk_bytes=chunk_bytes,
        max_wall_seconds=max_wall_seconds,
    )

    if probe.request_digest != request.request_digest:
        raise PlanBoundStorageProbeError("LOGICAL_PROBE_REQUEST_MISMATCH")
    if probe.relative_path != decision.storage_object_ref:
        raise PlanBoundStorageProbeError("LOGICAL_PROBE_STORAGE_OBJECT_MISMATCH")
    if probe.byte_offset != decision.aligned_byte_offset:
        raise PlanBoundStorageProbeError("LOGICAL_PROBE_OFFSET_MISMATCH")
    if probe.requested_probe_bytes != observation_window_bytes:
        raise PlanBoundStorageProbeError("LOGICAL_PROBE_WINDOW_MISMATCH")
    if probe.logical_bytes_read != observation_window_bytes:
        raise PlanBoundStorageProbeError("PLANNED_OBSERVATION_WINDOW_NOT_FULLY_READ")
    if (
        probe.page_cache_bypass_proven
        or probe.physical_nvme_io_attested
        or probe.storage_medium_nvme_proven
        or probe.producer_authenticated
        or probe.model_execution_observed
        or probe.lifecycle_measurement_admitted
        or probe.effect_authority_proven
        or probe.g2_admitted
    ):
        raise PlanBoundStorageProbeError("LOGICAL_PROBE_CEILING_WIDENED")

    return PlanBoundStorageProbeReceipt(
        plan_digest=plan.storage_plan_digest,
        request_digest=request.request_digest,
        tensor_id=decision.tensor_id,
        storage_object_ref=decision.storage_object_ref,
        planned_mode=decision.mode,
        planned_aligned_byte_offset=decision.aligned_byte_offset,
        planned_aligned_byte_length=decision.aligned_byte_length,
        observation_window_byte_offset=decision.aligned_byte_offset,
        observation_window_bytes=observation_window_bytes,
        full_planned_window_observed=(observation_window_bytes == decision.aligned_byte_length),
        logical_probe_receipt_digest=probe.receipt_digest,
        logical_probe_evidence_ref=probe.evidence_ref,
        logical_window_sha256=probe.window_sha256,
        logical_bytes_read=probe.logical_bytes_read,
        logical_read_operations=probe.read_operations,
        logical_read_bytes_per_second=probe.observed_logical_read_bytes_per_second,
    )

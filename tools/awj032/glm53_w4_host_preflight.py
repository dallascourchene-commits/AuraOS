"""D0 W4 expert-I/O preflight reducer for AWJ032 GLM-5.3.

This module evaluates already-supplied byte/timing counters. It deliberately keeps
physical byte avoidance separate from prefetch latency overlap and refuses to
manufacture physical-I/O evidence when the pager/cache owner leaves it UNKNOWN.
It is not a host benchmark, model run, cache policy, G2 admission, or end-to-end
performance predictor.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

try:
    from .glm53_pager_cache_telemetry import CacheTelemetryReceipt
except ImportError:  # focused tests from tools/awj032
    from glm53_pager_cache_telemetry import CacheTelemetryReceipt

W4_SCHEMA = "GLM53W4ExpertIOPreflightV1"
COLD_EXPERT_WEIGHT_BYTES_PER_TOKEN = 25_480_396_800


class W4PreflightError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise W4PreflightError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _bytes(name: str, value: Any, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (positive and value == 0):
        raise W4PreflightError(f"{name.upper()}_INVALID")
    return value


def _seconds(name: str, value: Any, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise W4PreflightError(f"{name.upper()}_INVALID")
    out = float(value)
    if not math.isfinite(out) or out < 0 or (positive and out == 0):
        raise W4PreflightError(f"{name.upper()}_INVALID")
    return out


@dataclass(frozen=True)
class W4CounterSnapshot:
    scope_ref: str
    source_generation: str
    workload_ref: str
    logical_expert_bytes_required: int
    physical_demand_expert_bytes: int
    prefetch_useful_bytes: int
    prefetch_waste_bytes: int
    aura_cache_avoided_bytes: int
    os_cache_avoided_bytes: int
    other_proven_avoided_bytes: int
    effective_bandwidth_bytes_per_s: float
    overlap_seconds: float
    queue_seconds: float
    exposed_io_budget_seconds: float | None = None
    physical_io_attested: bool = False
    physical_io_attestation_ref: str | None = None


@dataclass(frozen=True)
class W4PreflightReceipt:
    schema: str
    scope_ref: str
    source_generation: str
    workload_ref: str
    logical_expert_bytes_required: int
    physical_consumed_expert_bytes: int
    physical_total_expert_bytes: int
    physical_demand_expert_bytes: int
    prefetch_useful_bytes: int
    prefetch_waste_bytes: int
    avoided_expert_bytes: int
    aura_cache_avoided_bytes: int
    os_cache_avoided_bytes: int
    other_proven_avoided_bytes: int
    avoid_fraction: float
    effective_bandwidth_bytes_per_s: float
    service_seconds: float
    overlap_seconds: float
    queue_seconds: float
    exposed_seconds: float
    exposed_io_budget_seconds: float | None
    expert_io_budget_met: bool | None
    physical_io_attested: bool
    physical_io_attestation_ref: str | None
    runtime_execution_proven: bool = False
    end_to_end_usability_proven: bool = False
    g2_admitted: bool = False
    claim_ceiling: str = (
        "D0_COUNTER_REDUCTION_ONLY_BYTES_AVOIDED_NE_LATENCY_HIDDEN_"
        "NO_HOST_RUNTIME_OR_END_TO_END_OR_G2_PROOF"
    )


def required_avoid_fraction(
    *,
    logical_expert_bytes_required: int,
    effective_bandwidth_bytes_per_s: float,
    exposed_io_budget_seconds: float,
    overlap_seconds: float = 0.0,
    queue_seconds: float = 0.0,
    prefetch_waste_bytes: int = 0,
) -> float:
    """Necessary first-order byte-avoidance fraction for an exposed I/O budget."""
    logical = _bytes("logical_expert_bytes_required", logical_expert_bytes_required, positive=True)
    bandwidth = _seconds("effective_bandwidth_bytes_per_s", effective_bandwidth_bytes_per_s, positive=True)
    budget = _seconds("exposed_io_budget_seconds", exposed_io_budget_seconds)
    overlap = _seconds("overlap_seconds", overlap_seconds)
    queue = _seconds("queue_seconds", queue_seconds)
    waste = _bytes("prefetch_waste_bytes", prefetch_waste_bytes)
    service_allowance_s = budget - queue + overlap
    if service_allowance_s <= 0:
        return 1.0
    allowed_consumed_bytes = bandwidth * service_allowance_s - waste
    if allowed_consumed_bytes <= 0:
        return 1.0
    return min(1.0, max(0.0, 1.0 - allowed_consumed_bytes / logical))


def evaluate_w4_counters(snapshot: W4CounterSnapshot) -> W4PreflightReceipt:
    scope_ref = _text("scope_ref", snapshot.scope_ref)
    source_generation = _text("source_generation", snapshot.source_generation)
    workload_ref = _text("workload_ref", snapshot.workload_ref)
    logical = _bytes("logical_expert_bytes_required", snapshot.logical_expert_bytes_required, positive=True)
    demand = _bytes("physical_demand_expert_bytes", snapshot.physical_demand_expert_bytes)
    prefetch_useful = _bytes("prefetch_useful_bytes", snapshot.prefetch_useful_bytes)
    prefetch_waste = _bytes("prefetch_waste_bytes", snapshot.prefetch_waste_bytes)
    aura_avoided = _bytes("aura_cache_avoided_bytes", snapshot.aura_cache_avoided_bytes)
    os_avoided = _bytes("os_cache_avoided_bytes", snapshot.os_cache_avoided_bytes)
    other_avoided = _bytes("other_proven_avoided_bytes", snapshot.other_proven_avoided_bytes)
    bandwidth = _seconds(
        "effective_bandwidth_bytes_per_s",
        snapshot.effective_bandwidth_bytes_per_s,
        positive=True,
    )
    overlap = _seconds("overlap_seconds", snapshot.overlap_seconds)
    queue = _seconds("queue_seconds", snapshot.queue_seconds)
    budget = None
    if snapshot.exposed_io_budget_seconds is not None:
        budget = _seconds("exposed_io_budget_seconds", snapshot.exposed_io_budget_seconds)

    if not isinstance(snapshot.physical_io_attested, bool):
        raise W4PreflightError("PHYSICAL_IO_ATTESTED_INVALID")
    attestation_ref = snapshot.physical_io_attestation_ref
    if snapshot.physical_io_attested:
        attestation_ref = _text("physical_io_attestation_ref", attestation_ref)
    elif attestation_ref is not None:
        raise W4PreflightError("UNATTESTED_PHYSICAL_IO_REF_FORBIDDEN")

    physical_consumed = demand + prefetch_useful
    if physical_consumed > logical:
        raise W4PreflightError(
            "CONSUMED_BYTES_EXCEED_LOGICAL_REQUIRED",
            f"logical={logical},consumed={physical_consumed}",
        )
    avoided = logical - physical_consumed
    declared_avoided = aura_avoided + os_avoided + other_avoided
    if declared_avoided != avoided:
        raise W4PreflightError(
            "AVOIDED_BYTE_ACCOUNTING_MISMATCH",
            f"computed={avoided},declared={declared_avoided}",
        )

    physical_total = physical_consumed + prefetch_waste
    service = physical_total / bandwidth
    exposed = max(0.0, service - overlap) + queue
    budget_met = None if budget is None else exposed <= budget

    return W4PreflightReceipt(
        schema=W4_SCHEMA,
        scope_ref=scope_ref,
        source_generation=source_generation,
        workload_ref=workload_ref,
        logical_expert_bytes_required=logical,
        physical_consumed_expert_bytes=physical_consumed,
        physical_total_expert_bytes=physical_total,
        physical_demand_expert_bytes=demand,
        prefetch_useful_bytes=prefetch_useful,
        prefetch_waste_bytes=prefetch_waste,
        avoided_expert_bytes=avoided,
        aura_cache_avoided_bytes=aura_avoided,
        os_cache_avoided_bytes=os_avoided,
        other_proven_avoided_bytes=other_avoided,
        avoid_fraction=avoided / logical,
        effective_bandwidth_bytes_per_s=bandwidth,
        service_seconds=service,
        overlap_seconds=overlap,
        queue_seconds=queue,
        exposed_seconds=exposed,
        exposed_io_budget_seconds=budget,
        expert_io_budget_met=budget_met,
        physical_io_attested=snapshot.physical_io_attested,
        physical_io_attestation_ref=attestation_ref,
    )


def snapshot_from_cache_telemetry(
    receipt: CacheTelemetryReceipt,
    *,
    scope_ref: str,
    source_generation: str,
    workload_ref: str,
    effective_bandwidth_bytes_per_s: float,
    overlap_seconds: float = 0.0,
    queue_seconds: float = 0.0,
    exposed_io_budget_seconds: float | None = None,
) -> W4CounterSnapshot:
    """Adapt the current cache owner only when physical bytes are actually observed.

    The current cache owner does not prefetch, so useful/waste prefetch bytes are
    exactly zero here. If backend physical bytes are UNKNOWN, W4 stays blocked.
    """
    if not isinstance(receipt, CacheTelemetryReceipt):
        raise W4PreflightError("CACHE_TELEMETRY_RECEIPT_REQUIRED")
    if receipt.physical_io_attested is not True:
        raise W4PreflightError("PHYSICAL_IO_UNATTESTED")
    if receipt.physical_expert_bytes_read is None:
        raise W4PreflightError("PHYSICAL_BYTES_UNOBSERVED")
    physical = _bytes("physical_expert_bytes_read", receipt.physical_expert_bytes_read)
    logical = _bytes("cache_bytes_served", receipt.cache_bytes_served) + _bytes(
        "logical_backend_bytes_required", receipt.logical_backend_bytes_required
    )
    if logical <= 0:
        raise W4PreflightError("LOGICAL_EXPERT_BYTES_REQUIRED_INVALID")
    aura_avoided = _bytes("cache_bytes_served", receipt.cache_bytes_served)
    computed_avoided = logical - physical
    if computed_avoided < 0:
        raise W4PreflightError("PHYSICAL_BYTES_EXCEED_LOGICAL_REQUIRED")
    if computed_avoided != aura_avoided:
        raise W4PreflightError(
            "AVOIDED_BYTES_PROVENANCE_INCOMPLETE",
            f"computed={computed_avoided},aura_cache={aura_avoided}",
        )
    attestation_ref = receipt.backend_attestation_id
    if not isinstance(attestation_ref, str) or not attestation_ref.strip():
        raise W4PreflightError("PHYSICAL_IO_ATTESTATION_REF_REQUIRED")

    return W4CounterSnapshot(
        scope_ref=scope_ref,
        source_generation=source_generation,
        workload_ref=workload_ref,
        logical_expert_bytes_required=logical,
        physical_demand_expert_bytes=physical,
        prefetch_useful_bytes=0,
        prefetch_waste_bytes=0,
        aura_cache_avoided_bytes=aura_avoided,
        os_cache_avoided_bytes=0,
        other_proven_avoided_bytes=0,
        effective_bandwidth_bytes_per_s=effective_bandwidth_bytes_per_s,
        overlap_seconds=overlap_seconds,
        queue_seconds=queue_seconds,
        exposed_io_budget_seconds=exposed_io_budget_seconds,
        physical_io_attested=True,
        physical_io_attestation_ref=attestation_ref.strip(),
    )

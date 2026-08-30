"""D0 storage-only feasibility reducer for the GLM-5.3 expert pager.

This module converts source-bound pager telemetry into explicit reuse and
bandwidth requirements. It deliberately does not promote a storage-only result
to end-to-end model performance: compute, host-to-device transfer, KV/context,
thermal behavior, and other costs remain separate evidence planes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable

SCHEMA = "GLM53IOFeasibilityReceiptV1"
DEFAULT_COLD_EXPERT_BYTES_PER_TOKEN = 25_480_396_800


@dataclass(frozen=True)
class TargetClass:
    name: str
    target_expert_io_seconds: float


@dataclass(frozen=True)
class TargetResult:
    name: str
    target_expert_io_seconds: float
    required_reuse: float
    observed_expert_io_seconds: float | None
    disposition: str


@dataclass(frozen=True)
class IOFeasibilityReceipt:
    schema: str
    logical_expert_bytes_required: int
    physical_expert_bytes_read: int | None
    effective_storage_bandwidth_bytes_per_second: float
    observed_reuse: float | None
    io_amplification: bool | None
    targets: tuple[TargetResult, ...]
    claim_ceiling: str = "STORAGE_ONLY_NOT_END_TO_END_PERFORMANCE_OR_G2_ADMISSION"
    g2_admitted: bool = False

    def to_dict(self) -> dict:
        out = asdict(self)
        out["targets"] = [asdict(item) for item in self.targets]
        return out


def _positive_finite(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and > 0")
    return value


def required_reuse(
    *,
    logical_expert_bytes_required: int,
    effective_storage_bandwidth_bytes_per_second: float,
    target_expert_io_seconds: float,
) -> float:
    """Return the minimum reuse fraction needed to satisfy a storage time budget."""
    if logical_expert_bytes_required <= 0:
        raise ValueError("logical_expert_bytes_required must be > 0")
    bandwidth = _positive_finite(
        effective_storage_bandwidth_bytes_per_second,
        "effective_storage_bandwidth_bytes_per_second",
    )
    target = _positive_finite(target_expert_io_seconds, "target_expert_io_seconds")
    requirement = 1.0 - (bandwidth * target) / logical_expert_bytes_required
    return min(1.0, max(0.0, requirement))


def observed_reuse(
    *, logical_expert_bytes_required: int, physical_expert_bytes_read: int | None
) -> float | None:
    """Return measured R_io, preserving UNKNOWN when physical I/O is unattested."""
    if logical_expert_bytes_required <= 0:
        raise ValueError("logical_expert_bytes_required must be > 0")
    if physical_expert_bytes_read is None:
        return None
    if physical_expert_bytes_read < 0:
        raise ValueError("physical_expert_bytes_read must be >= 0 or None")
    raw = 1.0 - physical_expert_bytes_read / logical_expert_bytes_required
    return min(1.0, max(0.0, raw))


def evaluate_io_feasibility(
    *,
    logical_expert_bytes_required: int = DEFAULT_COLD_EXPERT_BYTES_PER_TOKEN,
    physical_expert_bytes_read: int | None,
    effective_storage_bandwidth_bytes_per_second: float,
    targets: Iterable[TargetClass],
) -> IOFeasibilityReceipt:
    """Evaluate storage-only feasibility against caller-supplied latency classes.

    ``physical_expert_bytes_read=None`` is a first-class UNKNOWN state. It is
    never converted to zero. Target names and latency budgets are supplied by
    the caller so this reducer does not invent an interactive/batch SLA.
    """
    if logical_expert_bytes_required <= 0:
        raise ValueError("logical_expert_bytes_required must be > 0")
    bandwidth = _positive_finite(
        effective_storage_bandwidth_bytes_per_second,
        "effective_storage_bandwidth_bytes_per_second",
    )
    reuse = observed_reuse(
        logical_expert_bytes_required=logical_expert_bytes_required,
        physical_expert_bytes_read=physical_expert_bytes_read,
    )
    amplification = (
        None
        if physical_expert_bytes_read is None
        else physical_expert_bytes_read > logical_expert_bytes_required
    )
    observed_seconds = (
        None
        if physical_expert_bytes_read is None
        else physical_expert_bytes_read / bandwidth
    )

    results: list[TargetResult] = []
    seen_names: set[str] = set()
    for target in targets:
        name = str(target.name).strip()
        if not name:
            raise ValueError("target name must be non-empty")
        if name in seen_names:
            raise ValueError(f"duplicate target name: {name}")
        seen_names.add(name)
        target_seconds = _positive_finite(
            target.target_expert_io_seconds, "target_expert_io_seconds"
        )
        needed = required_reuse(
            logical_expert_bytes_required=logical_expert_bytes_required,
            effective_storage_bandwidth_bytes_per_second=bandwidth,
            target_expert_io_seconds=target_seconds,
        )
        if observed_seconds is None:
            disposition = "UNKNOWN_PHYSICAL_IO"
        elif observed_seconds <= target_seconds:
            disposition = "MEETS_STORAGE_BUDGET"
        else:
            disposition = "MISSES_STORAGE_BUDGET"
        results.append(
            TargetResult(
                name=name,
                target_expert_io_seconds=target_seconds,
                required_reuse=needed,
                observed_expert_io_seconds=observed_seconds,
                disposition=disposition,
            )
        )

    if not results:
        raise ValueError("at least one target class is required")

    return IOFeasibilityReceipt(
        schema=SCHEMA,
        logical_expert_bytes_required=logical_expert_bytes_required,
        physical_expert_bytes_read=physical_expert_bytes_read,
        effective_storage_bandwidth_bytes_per_second=bandwidth,
        observed_reuse=reuse,
        io_amplification=amplification,
        targets=tuple(results),
    )

"""Deterministic ThinkPad-first NVMe/RAM residency and prefetch planner.

This module is intentionally a *planner*, not an I/O engine.  It consumes a
measured-or-synthetic host storage profile plus bounded tensor-slice metadata
and emits a deterministic storage plan suitable for binding into the AWJ032 C2
handoff as ``storage_plan_digest``.

It never samples the host, performs file I/O, loads model weights, executes a
model, measures throughput, authenticates a producer, or admits G2.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Iterable

PLAN_SCHEMA = "AWJ032ThinkPadNVMeResidencyPlanV1"
PROFILE_KINDS = frozenset({"OWNER_HOST_MEASURED", "SYNTHETIC_TEST"})
ROLES = frozenset({"weight", "expert", "kv", "index", "router", "other"})
TEMPERATURES = frozenset({"HOT", "WARM", "COLD"})
RAM_RESIDENT = "RAM_RESIDENT"
ASYNC_NVME_PREFETCH = "ASYNC_NVME_PREFETCH"
MMAP_DEMAND = "MMAP_DEMAND"
DIRECT_SYNC = "DIRECT_SYNC"


class ThinkPadResidencyPlanError(ValueError):
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
        raise ThinkPadResidencyPlanError("NONCANONICAL_PLAN_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ThinkPadResidencyPlanError(code)
    return value.strip()


def _exact_bool(value: Any, code: str) -> bool:
    if type(value) is not bool:
        raise ThinkPadResidencyPlanError(code)
    return value


def _positive_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ThinkPadResidencyPlanError(code)
    return value


def _nonnegative_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ThinkPadResidencyPlanError(code)
    return value


def _positive_float(value: Any, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ThinkPadResidencyPlanError(code)
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ThinkPadResidencyPlanError(code)
    return value


def _page_aligned_span(offset: int, length: int, page_size: int) -> tuple[int, int]:
    start = (offset // page_size) * page_size
    end_unaligned = offset + length
    end = ((end_unaligned + page_size - 1) // page_size) * page_size
    return start, end - start


@dataclass(frozen=True)
class HostStorageProfile:
    profile_kind: str
    available_ram_bytes: int
    nvme_sequential_read_bytes_per_second: int
    page_size_bytes: int = 4096
    io_uring_supported: bool = False
    mmap_supported: bool = True
    direct_io_supported: bool = False
    source_ref: str = "unspecified"

    def __post_init__(self) -> None:
        if self.profile_kind not in PROFILE_KINDS:
            raise ThinkPadResidencyPlanError("PROFILE_KIND_INVALID")
        _positive_int(self.available_ram_bytes, "AVAILABLE_RAM_BYTES_INVALID")
        _positive_int(
            self.nvme_sequential_read_bytes_per_second,
            "NVME_SEQUENTIAL_READ_BPS_INVALID",
        )
        page_size = _positive_int(self.page_size_bytes, "PAGE_SIZE_BYTES_INVALID")
        if page_size & (page_size - 1):
            raise ThinkPadResidencyPlanError("PAGE_SIZE_MUST_BE_POWER_OF_TWO")
        _exact_bool(self.io_uring_supported, "IO_URING_SUPPORT_FLAG_INVALID")
        _exact_bool(self.mmap_supported, "MMAP_SUPPORT_FLAG_INVALID")
        _exact_bool(self.direct_io_supported, "DIRECT_IO_SUPPORT_FLAG_INVALID")
        _text(self.source_ref, "PROFILE_SOURCE_REF_REQUIRED")


@dataclass(frozen=True)
class TensorSlice:
    tensor_id: str
    storage_object_ref: str
    byte_offset: int
    byte_length: int
    first_use_step: int
    compute_slack_seconds: float
    reuse_count: int = 1
    role: str = "weight"
    temperature: str = "WARM"

    def __post_init__(self) -> None:
        _text(self.tensor_id, "TENSOR_ID_REQUIRED")
        _text(self.storage_object_ref, "STORAGE_OBJECT_REF_REQUIRED")
        _nonnegative_int(self.byte_offset, "BYTE_OFFSET_INVALID")
        _positive_int(self.byte_length, "BYTE_LENGTH_INVALID")
        _nonnegative_int(self.first_use_step, "FIRST_USE_STEP_INVALID")
        _positive_float(self.compute_slack_seconds, "COMPUTE_SLACK_SECONDS_INVALID")
        _positive_int(self.reuse_count, "REUSE_COUNT_INVALID")
        if self.role not in ROLES:
            raise ThinkPadResidencyPlanError("ROLE_INVALID", self.role)
        if self.temperature not in TEMPERATURES:
            raise ThinkPadResidencyPlanError("TEMPERATURE_INVALID", self.temperature)


@dataclass(frozen=True)
class ResidencyPolicy:
    min_ram_reserve_bytes: int
    max_resident_bytes: int
    max_prefetch_bytes: int
    buffer_count: int = 2
    max_prefetch_lead_steps: int = 4
    adjacent_gap_bytes: int = 4096

    def __post_init__(self) -> None:
        _nonnegative_int(self.min_ram_reserve_bytes, "MIN_RAM_RESERVE_INVALID")
        _nonnegative_int(self.max_resident_bytes, "MAX_RESIDENT_BYTES_INVALID")
        _positive_int(self.max_prefetch_bytes, "MAX_PREFETCH_BYTES_INVALID")
        _positive_int(self.buffer_count, "BUFFER_COUNT_INVALID")
        _positive_int(self.max_prefetch_lead_steps, "MAX_PREFETCH_LEAD_STEPS_INVALID")
        _nonnegative_int(self.adjacent_gap_bytes, "ADJACENT_GAP_BYTES_INVALID")


@dataclass(frozen=True)
class ResidencyDecision:
    tensor_id: str
    storage_object_ref: str
    mode: str
    aligned_byte_offset: int
    aligned_byte_length: int
    first_use_step: int
    issue_step: int | None
    prefetch_lead_steps: int
    buffer_slot: int | None
    estimated_read_seconds: float
    role: str
    temperature: str
    reuse_count: int


@dataclass(frozen=True)
class PrefetchBatch:
    batch_id: str
    storage_object_ref: str
    issue_step: int
    buffer_slot: int
    aligned_byte_offset: int
    aligned_byte_length: int
    tensor_ids: tuple[str, ...]


@dataclass(frozen=True)
class ThinkPadResidencyPlan:
    host_profile: HostStorageProfile
    policy: ResidencyPolicy
    decisions: tuple[ResidencyDecision, ...]
    prefetch_batches: tuple[PrefetchBatch, ...]
    ram_budget_bytes: int
    ram_committed_bytes: int
    physical_io_observed: bool = False
    model_execution_observed: bool = False
    producer_authenticated: bool = False
    performance_claimed: bool = False
    effect_authority_proven: bool = False
    g2_admitted: bool = False
    schema: str = PLAN_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def plan_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def storage_plan_digest(self) -> str:
        """Digest intended for AWJ032 C2 ``storage_plan_digest`` binding."""
        return self.plan_digest


def _ram_priority(item: tuple[TensorSlice, int, int]) -> tuple[int, int, int, str]:
    tensor, _, aligned_length = item
    temperature_rank = {"HOT": 0, "WARM": 1, "COLD": 2}[tensor.temperature]
    # Reuse-first, then smaller aligned footprint. This is a deterministic
    # laptop-memory heuristic, not a performance theorem.
    return (temperature_rank, -tensor.reuse_count, aligned_length, tensor.tensor_id)


def _coalesce_prefetch_batches(
    decisions: Iterable[ResidencyDecision],
    policy: ResidencyPolicy,
) -> tuple[PrefetchBatch, ...]:
    candidates = sorted(
        (d for d in decisions if d.mode == ASYNC_NVME_PREFETCH),
        key=lambda d: (
            d.issue_step if d.issue_step is not None else -1,
            d.buffer_slot if d.buffer_slot is not None else -1,
            d.storage_object_ref,
            d.aligned_byte_offset,
            d.tensor_id,
        ),
    )
    batches: list[PrefetchBatch] = []
    current: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        payload = {
            "storage_object_ref": current["storage_object_ref"],
            "issue_step": current["issue_step"],
            "buffer_slot": current["buffer_slot"],
            "aligned_byte_offset": current["aligned_byte_offset"],
            "aligned_byte_length": current["aligned_byte_length"],
            "tensor_ids": tuple(current["tensor_ids"]),
        }
        batches.append(PrefetchBatch(batch_id=_digest(payload), **payload))
        current = None

    for decision in candidates:
        assert decision.issue_step is not None
        assert decision.buffer_slot is not None
        if current is None:
            current = {
                "storage_object_ref": decision.storage_object_ref,
                "issue_step": decision.issue_step,
                "buffer_slot": decision.buffer_slot,
                "aligned_byte_offset": decision.aligned_byte_offset,
                "aligned_byte_length": decision.aligned_byte_length,
                "tensor_ids": [decision.tensor_id],
            }
            continue

        current_end = current["aligned_byte_offset"] + current["aligned_byte_length"]
        gap = decision.aligned_byte_offset - current_end
        merged_end = max(
            current_end,
            decision.aligned_byte_offset + decision.aligned_byte_length,
        )
        merged_length = merged_end - current["aligned_byte_offset"]
        same_lane = (
            current["storage_object_ref"] == decision.storage_object_ref
            and current["issue_step"] == decision.issue_step
            and current["buffer_slot"] == decision.buffer_slot
        )
        if (
            same_lane
            and 0 <= gap <= policy.adjacent_gap_bytes
            and merged_length <= policy.max_prefetch_bytes
        ):
            current["aligned_byte_length"] = merged_length
            current["tensor_ids"].append(decision.tensor_id)
        else:
            flush()
            current = {
                "storage_object_ref": decision.storage_object_ref,
                "issue_step": decision.issue_step,
                "buffer_slot": decision.buffer_slot,
                "aligned_byte_offset": decision.aligned_byte_offset,
                "aligned_byte_length": decision.aligned_byte_length,
                "tensor_ids": [decision.tensor_id],
            }
    flush()
    return tuple(batches)


def build_thinkpad_residency_plan(
    *,
    host_profile: HostStorageProfile,
    tensors: Iterable[TensorSlice],
    policy: ResidencyPolicy,
) -> ThinkPadResidencyPlan:
    """Build one deterministic, non-executing ThinkPad storage plan."""
    if type(host_profile) is not HostStorageProfile:
        raise ThinkPadResidencyPlanError("HOST_PROFILE_TYPE_INVALID")
    if type(policy) is not ResidencyPolicy:
        raise ThinkPadResidencyPlanError("POLICY_TYPE_INVALID")

    tensor_list = list(tensors)
    if not tensor_list:
        raise ThinkPadResidencyPlanError("TENSOR_SET_EMPTY")
    if any(type(item) is not TensorSlice for item in tensor_list):
        raise ThinkPadResidencyPlanError("TENSOR_TYPE_INVALID")
    ids = [item.tensor_id for item in tensor_list]
    if len(ids) != len(set(ids)):
        raise ThinkPadResidencyPlanError("DUPLICATE_TENSOR_ID")

    aligned: list[tuple[TensorSlice, int, int]] = []
    for tensor in tensor_list:
        offset, length = _page_aligned_span(
            tensor.byte_offset,
            tensor.byte_length,
            host_profile.page_size_bytes,
        )
        aligned.append((tensor, offset, length))

    usable_after_reserve = max(
        0, host_profile.available_ram_bytes - policy.min_ram_reserve_bytes
    )
    ram_budget = min(usable_after_reserve, policy.max_resident_bytes)
    ram_committed = 0
    ram_ids: set[str] = set()
    for tensor, _, aligned_length in sorted(aligned, key=_ram_priority):
        if tensor.temperature == "COLD" and tensor.reuse_count == 1:
            continue
        if tensor.temperature != "HOT" and tensor.reuse_count <= 1:
            continue
        if aligned_length <= ram_budget - ram_committed:
            ram_ids.add(tensor.tensor_id)
            ram_committed += aligned_length

    decisions: list[ResidencyDecision] = []
    for tensor, aligned_offset, aligned_length in sorted(
        aligned, key=lambda x: (x[0].first_use_step, x[0].tensor_id)
    ):
        estimated_read_seconds = (
            aligned_length / host_profile.nvme_sequential_read_bytes_per_second
        )
        if tensor.tensor_id in ram_ids:
            decisions.append(
                ResidencyDecision(
                    tensor_id=tensor.tensor_id,
                    storage_object_ref=tensor.storage_object_ref,
                    mode=RAM_RESIDENT,
                    aligned_byte_offset=aligned_offset,
                    aligned_byte_length=aligned_length,
                    first_use_step=tensor.first_use_step,
                    issue_step=None,
                    prefetch_lead_steps=0,
                    buffer_slot=None,
                    estimated_read_seconds=estimated_read_seconds,
                    role=tensor.role,
                    temperature=tensor.temperature,
                    reuse_count=tensor.reuse_count,
                )
            )
            continue

        slack = _positive_float(
            tensor.compute_slack_seconds, "COMPUTE_SLACK_SECONDS_INVALID"
        )
        lead_steps = max(1, math.ceil(estimated_read_seconds / slack))
        if (
            host_profile.io_uring_supported
            and aligned_length <= policy.max_prefetch_bytes
            and lead_steps <= policy.max_prefetch_lead_steps
        ):
            issue_step = max(0, tensor.first_use_step - lead_steps)
            slot = issue_step % policy.buffer_count
            mode = ASYNC_NVME_PREFETCH
        elif host_profile.mmap_supported:
            issue_step = None
            slot = None
            mode = MMAP_DEMAND
            lead_steps = 0
        elif host_profile.direct_io_supported:
            issue_step = None
            slot = None
            mode = DIRECT_SYNC
            lead_steps = 0
        else:
            raise ThinkPadResidencyPlanError(
                "NO_SUPPORTED_STORAGE_PATH", tensor.tensor_id
            )

        decisions.append(
            ResidencyDecision(
                tensor_id=tensor.tensor_id,
                storage_object_ref=tensor.storage_object_ref,
                mode=mode,
                aligned_byte_offset=aligned_offset,
                aligned_byte_length=aligned_length,
                first_use_step=tensor.first_use_step,
                issue_step=issue_step,
                prefetch_lead_steps=lead_steps,
                buffer_slot=slot,
                estimated_read_seconds=estimated_read_seconds,
                role=tensor.role,
                temperature=tensor.temperature,
                reuse_count=tensor.reuse_count,
            )
        )

    batches = _coalesce_prefetch_batches(decisions, policy)
    return ThinkPadResidencyPlan(
        host_profile=host_profile,
        policy=policy,
        decisions=tuple(decisions),
        prefetch_batches=batches,
        ram_budget_bytes=ram_budget,
        ram_committed_bytes=ram_committed,
    )

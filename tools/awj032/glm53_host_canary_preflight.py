"""Deterministic GLM-5.3 host/canary preflight compiler for AWJ032 G2-G4.

D0 planning only. This module does not sample the host, download/model weights,
execute a canary, or grant G2. It converts an externally measured ThinkPad/WSL
snapshot, an exact representation/storage plan, and W4-admissible backend I/O
evidence into reproducible feasibility math and explicit canary planning state.

The central separation is:
  measurement -> deterministic planning receipt -> separate effect admission.
A planning PASS is never execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

try:
    from .glm53_backend_io_evidence_guard import W4BackendEvidence, W4_EVIDENCE_SCHEMA
except ImportError:
    from glm53_backend_io_evidence_guard import W4BackendEvidence, W4_EVIDENCE_SCHEMA

SCHEMA = "GLM53HostCanaryPreflightReceiptV1"
HOST_SCHEMA = "GLM53HostSnapshotV1"
STORAGE_SCHEMA = "GLM53RepresentationStoragePlanV1"
IO_BOUND_SCHEMA = "GLM53ColdExpertIOBoundV1"


class HostPreflightError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
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
        raise HostPreflightError("NONCANONICAL_PREFLIGHT_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HostPreflightError(code)
    return value.strip()


def _nonneg_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise HostPreflightError(code)
    return value


def _positive_int(value: Any, code: str) -> int:
    out = _nonneg_int(value, code)
    if out == 0:
        raise HostPreflightError(code)
    return out


def _nonneg_float(value: Any, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
        raise HostPreflightError(code)
    return float(value)


def _positive_float(value: Any, code: str) -> float:
    out = _nonneg_float(value, code)
    if out <= 0:
        raise HostPreflightError(code)
    return out


@dataclass(frozen=True)
class HostSnapshot:
    observation_id: str
    currentness_ref: str
    cpu_model: str
    cpu_logical_cores: int
    ram_total_bytes: int
    ram_available_bytes: int
    ram_commit_available_bytes: int
    gpu_present: bool
    gpu_model: str | None
    vram_total_bytes: int
    vram_available_bytes: int
    gpu_driver: str | None
    cuda_capability: str | None
    nvme_model: str
    filesystem: str
    free_space_bytes: int
    sequential_read_bytes_per_s: int
    sequential_write_bytes_per_s: int
    random_read_iops: int
    thermal_celsius: float
    power_source: str
    battery_percent: float | None
    foreground_load_percent: float
    python_version: str
    torch_version: str
    transformers_version: str
    airllm_revision: str
    schema: str = HOST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != HOST_SCHEMA:
            raise HostPreflightError("HOST_SCHEMA_MISMATCH")
        for value, code in (
            (self.observation_id, "HOST_OBSERVATION_ID_REQUIRED"),
            (self.currentness_ref, "HOST_CURRENTNESS_REF_REQUIRED"),
            (self.cpu_model, "CPU_MODEL_REQUIRED"),
            (self.nvme_model, "NVME_MODEL_REQUIRED"),
            (self.filesystem, "FILESYSTEM_REQUIRED"),
            (self.power_source, "POWER_SOURCE_REQUIRED"),
            (self.python_version, "PYTHON_VERSION_REQUIRED"),
            (self.torch_version, "TORCH_VERSION_REQUIRED"),
            (self.transformers_version, "TRANSFORMERS_VERSION_REQUIRED"),
            (self.airllm_revision, "AIRLLM_REVISION_REQUIRED"),
        ):
            _text(value, code)
        _positive_int(self.cpu_logical_cores, "CPU_LOGICAL_CORES_INVALID")
        _positive_int(self.ram_total_bytes, "RAM_TOTAL_INVALID")
        _nonneg_int(self.ram_available_bytes, "RAM_AVAILABLE_INVALID")
        _nonneg_int(self.ram_commit_available_bytes, "RAM_COMMIT_AVAILABLE_INVALID")
        if self.ram_available_bytes > self.ram_total_bytes:
            raise HostPreflightError("RAM_AVAILABLE_EXCEEDS_TOTAL")
        if not isinstance(self.gpu_present, bool):
            raise HostPreflightError("GPU_PRESENT_BOOL_REQUIRED")
        _nonneg_int(self.vram_total_bytes, "VRAM_TOTAL_INVALID")
        _nonneg_int(self.vram_available_bytes, "VRAM_AVAILABLE_INVALID")
        if self.vram_available_bytes > self.vram_total_bytes:
            raise HostPreflightError("VRAM_AVAILABLE_EXCEEDS_TOTAL")
        if self.gpu_present:
            _text(self.gpu_model, "GPU_MODEL_REQUIRED")
            _text(self.gpu_driver, "GPU_DRIVER_REQUIRED")
            _text(self.cuda_capability, "CUDA_CAPABILITY_REQUIRED")
        elif any(value not in (None, "", 0) for value in (self.gpu_model, self.gpu_driver, self.cuda_capability, self.vram_total_bytes, self.vram_available_bytes)):
            raise HostPreflightError("GPU_ABSENT_FIELDS_INCONSISTENT")
        _nonneg_int(self.free_space_bytes, "FREE_SPACE_INVALID")
        _positive_int(self.sequential_read_bytes_per_s, "SEQUENTIAL_READ_BPS_INVALID")
        _positive_int(self.sequential_write_bytes_per_s, "SEQUENTIAL_WRITE_BPS_INVALID")
        _positive_int(self.random_read_iops, "RANDOM_READ_IOPS_INVALID")
        _nonneg_float(self.thermal_celsius, "THERMAL_CELSIUS_INVALID")
        if self.power_source not in {"AC", "BATTERY"}:
            raise HostPreflightError("POWER_SOURCE_INVALID")
        if self.battery_percent is not None:
            battery = _nonneg_float(self.battery_percent, "BATTERY_PERCENT_INVALID")
            if battery > 100:
                raise HostPreflightError("BATTERY_PERCENT_INVALID")
        load = _nonneg_float(self.foreground_load_percent, "FOREGROUND_LOAD_INVALID")
        if load > 100:
            raise HostPreflightError("FOREGROUND_LOAD_INVALID")

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class RepresentationStoragePlan:
    model_revision: str
    representation_id: str
    published_source_bytes: int
    representation_bytes: int
    temporary_conversion_bytes: int
    c2_canary_bytes: int
    safety_reserve_bytes: int
    source_recoverable: bool
    schema: str = STORAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != STORAGE_SCHEMA:
            raise HostPreflightError("STORAGE_SCHEMA_MISMATCH")
        _text(self.model_revision, "MODEL_REVISION_REQUIRED")
        _text(self.representation_id, "REPRESENTATION_ID_REQUIRED")
        _positive_int(self.published_source_bytes, "PUBLISHED_SOURCE_BYTES_INVALID")
        _positive_int(self.representation_bytes, "REPRESENTATION_BYTES_INVALID")
        _nonneg_int(self.temporary_conversion_bytes, "TEMPORARY_CONVERSION_BYTES_INVALID")
        _positive_int(self.c2_canary_bytes, "C2_CANARY_BYTES_INVALID")
        _nonneg_int(self.safety_reserve_bytes, "SAFETY_RESERVE_BYTES_INVALID")
        if not isinstance(self.source_recoverable, bool):
            raise HostPreflightError("SOURCE_RECOVERABLE_BOOL_REQUIRED")
        if not self.source_recoverable:
            raise HostPreflightError("SOURCE_RECOVERABILITY_REQUIRED")

    @property
    def c2_required_free_bytes(self) -> int:
        return self.c2_canary_bytes + self.safety_reserve_bytes

    @property
    def c3_required_free_bytes(self) -> int:
        # Full representation plus temporary conversion working space and reserve.
        return self.representation_bytes + self.temporary_conversion_bytes + self.safety_reserve_bytes

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class ColdExpertIOBound:
    sparse_layers: int
    routed_experts_per_token: int
    shared_experts_per_layer: int
    bytes_per_expert: int
    schema: str = IO_BOUND_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != IO_BOUND_SCHEMA:
            raise HostPreflightError("IO_BOUND_SCHEMA_MISMATCH")
        _positive_int(self.sparse_layers, "SPARSE_LAYERS_INVALID")
        _positive_int(self.routed_experts_per_token, "ROUTED_EXPERTS_INVALID")
        _nonneg_int(self.shared_experts_per_layer, "SHARED_EXPERTS_INVALID")
        _positive_int(self.bytes_per_expert, "BYTES_PER_EXPERT_INVALID")

    @property
    def cold_expert_bytes_per_token(self) -> int:
        return self.sparse_layers * (self.routed_experts_per_token + self.shared_experts_per_layer) * self.bytes_per_expert

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class PerformanceTarget:
    name: str
    max_seconds_per_token: float

    def __post_init__(self) -> None:
        _text(self.name, "PERFORMANCE_TARGET_NAME_REQUIRED")
        _positive_float(self.max_seconds_per_token, "PERFORMANCE_TARGET_SECONDS_INVALID")


@dataclass(frozen=True)
class HostCanaryPreflightReceipt:
    host_digest: str
    storage_plan_digest: str
    io_bound_digest: str
    w4_binding_digest: str
    w4_attestation_id: str
    logical_expert_bytes_required: int
    physical_expert_bytes_read: int
    measured_reuse_ratio: float
    physical_io_amplification: bool
    measured_backend_read_seconds: float
    measured_physical_read_bytes_per_s: float | None
    cold_nvme_floor_seconds_per_token: float
    target_min_reuse_ratio: Mapping[str, float]
    c2_storage_ready: bool
    c3_storage_ready: bool
    host_measurement_complete: bool
    w4_evidence_admissible: bool
    planning_ready: bool
    next_canary: str
    execution_authorized: bool
    effect_authorized: bool
    g2_admitted: bool
    large_checkpoint_admitted: bool
    runtime_execution_proven: bool
    receipt_digest: str
    schema: str = SCHEMA
    claim_ceiling: str = "D0_HOST_CANARY_PLANNING_ONLY_NO_CHECKPOINT_EFFECT_OR_G2_PROOF"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _target_min_reuse(io_bound: ColdExpertIOBound, host: HostSnapshot, targets: Sequence[PerformanceTarget]) -> dict[str, float]:
    names: set[str] = set()
    out: dict[str, float] = {}
    cold_bytes = io_bound.cold_expert_bytes_per_token
    bandwidth = host.sequential_read_bytes_per_s
    for target in targets:
        if target.name in names:
            raise HostPreflightError("PERFORMANCE_TARGET_DUPLICATE", target.name)
        names.add(target.name)
        max_physical_bytes = bandwidth * target.max_seconds_per_token
        required = 1.0 - (max_physical_bytes / cold_bytes)
        out[target.name] = max(0.0, min(1.0, required))
    return dict(sorted(out.items()))


def compile_host_canary_preflight(
    *,
    host: HostSnapshot,
    storage: RepresentationStoragePlan,
    io_bound: ColdExpertIOBound,
    w4: W4BackendEvidence,
    logical_expert_bytes_required: int,
    targets: Sequence[PerformanceTarget] = (),
) -> HostCanaryPreflightReceipt:
    """Compile D0 host feasibility math from already-measured evidence.

    `planning_ready` means the supplied host/W4 evidence is internally sufficient
    to plan the next bounded effect. It never means C2 is authorized or G2 passed.
    """
    if not isinstance(host, HostSnapshot):
        raise HostPreflightError("HOST_SNAPSHOT_REQUIRED")
    if not isinstance(storage, RepresentationStoragePlan):
        raise HostPreflightError("STORAGE_PLAN_REQUIRED")
    if not isinstance(io_bound, ColdExpertIOBound):
        raise HostPreflightError("IO_BOUND_REQUIRED")
    if getattr(w4, "schema", None) != W4_EVIDENCE_SCHEMA:
        raise HostPreflightError("W4_EVIDENCE_REQUIRED")
    if not w4.physical_io_attested or not w4.w4_metrics_complete or not w4.w4_admissible:
        raise HostPreflightError("W4_EVIDENCE_NOT_ADMISSIBLE")
    if w4.g2_admitted:
        raise HostPreflightError("W4_AUTHORITY_WIDENING")
    binding_digest = _text(w4.binding_digest, "W4_BINDING_DIGEST_REQUIRED")
    attestation_id = _text(w4.attestation_id, "W4_ATTESTATION_ID_REQUIRED")
    physical = _nonneg_int(w4.physical_expert_bytes_read, "W4_PHYSICAL_BYTES_REQUIRED")
    elapsed_ms = _nonneg_float(w4.read_elapsed_ms, "W4_READ_ELAPSED_REQUIRED")
    _nonneg_int(w4.physical_read_operations, "W4_READ_OPERATIONS_REQUIRED")
    _text(w4.page_cache_provenance, "W4_PAGE_CACHE_PROVENANCE_REQUIRED")
    logical = _positive_int(logical_expert_bytes_required, "LOGICAL_EXPERT_BYTES_REQUIRED")
    if physical > 0 and elapsed_ms == 0:
        raise HostPreflightError("POSITIVE_PHYSICAL_BYTES_REQUIRE_ELAPSED_TIME")

    reuse_raw = 1.0 - (physical / logical)
    reuse = max(0.0, min(1.0, reuse_raw))
    amplification = physical > logical
    elapsed_s = elapsed_ms / 1000.0
    measured_bps = None if physical == 0 or elapsed_s == 0 else physical / elapsed_s
    cold_floor_s = io_bound.cold_expert_bytes_per_token / host.sequential_read_bytes_per_s
    target_reuse = _target_min_reuse(io_bound, host, targets)

    c2_storage_ready = host.free_space_bytes >= storage.c2_required_free_bytes
    c3_storage_ready = host.free_space_bytes >= storage.c3_required_free_bytes
    planning_ready = c2_storage_ready and w4.w4_admissible
    next_canary = "C2_EFFECT_ADMISSION_REQUIRED" if planning_ready else "BLOCKED_RESOURCE"

    payload = {
        "schema": SCHEMA,
        "host_digest": host.digest,
        "storage_plan_digest": storage.digest,
        "io_bound_digest": io_bound.digest,
        "w4_binding_digest": binding_digest,
        "w4_attestation_id": attestation_id,
        "logical_expert_bytes_required": logical,
        "physical_expert_bytes_read": physical,
        "measured_reuse_ratio": reuse,
        "physical_io_amplification": amplification,
        "measured_backend_read_seconds": elapsed_s,
        "measured_physical_read_bytes_per_s": measured_bps,
        "cold_nvme_floor_seconds_per_token": cold_floor_s,
        "target_min_reuse_ratio": target_reuse,
        "c2_storage_ready": c2_storage_ready,
        "c3_storage_ready": c3_storage_ready,
        "host_measurement_complete": True,
        "w4_evidence_admissible": True,
        "planning_ready": planning_ready,
        "next_canary": next_canary,
        "execution_authorized": False,
        "effect_authorized": False,
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
    }
    return HostCanaryPreflightReceipt(**payload, receipt_digest=_digest(payload))

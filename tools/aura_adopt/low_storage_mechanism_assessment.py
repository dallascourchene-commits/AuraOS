"""AURA-ADOPT-001 ZF-06A low-storage mechanism assessment.

Pure evidence reducer. It does not benchmark a device, execute a mechanism,
or convert historical mechanism names or literature claims into device
performance claims.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from enum import Enum
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA = "LowStorageMechanismAssessmentV1"


class AssessmentError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class EvidenceClass(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    LITERATURE_REPORTED = "LITERATURE_REPORTED"
    REPOSITORY_BENCHMARK = "REPOSITORY_BENCHMARK"
    BROWSER_MEASURED = "BROWSER_MEASURED"
    ANDROID_MEASURED = "ANDROID_MEASURED"
    UNKNOWN = "UNKNOWN"


class FidelityClass(str, Enum):
    EXACT = "EXACT"
    BOUNDED_ACCEPTED = "BOUNDED_ACCEPTED"
    BOUNDED_LOSS = "BOUNDED_LOSS"
    UNKNOWN = "UNKNOWN"


class ResponsibilityClass(str, Enum):
    TRANSFORMER_KV_CACHE = "TRANSFORMER_KV_CACHE"
    COORDINATE_MEMORY = "COORDINATE_MEMORY"
    ARTIFACT_COMPRESSION = "ARTIFACT_COMPRESSION"
    MODEL_STATE = "MODEL_STATE"


class Disposition(str, Enum):
    RETAIN = "RETAIN"
    CONDITIONAL = "CONDITIONAL"
    DEMOTE = "DEMOTE"
    UNKNOWN = "UNKNOWN"


RESPONSIBILITY_METRIC_FLOORS = {
    ResponsibilityClass.TRANSFORMER_KV_CACHE: frozenset({
        "logical_payload_bytes", "encoded_or_retained_bytes", "peak_working_memory_bytes",
        "kv_cache_peak_bytes", "ttft_ms", "prefill_ms", "decode_ms_per_token",
        "recompute_or_cache_load_ms",
    }),
    ResponsibilityClass.COORDINATE_MEMORY: frozenset({
        "logical_payload_bytes", "encoded_or_retained_bytes", "peak_working_memory_bytes",
        "encode_ms", "decode_or_reopen_ms", "lookup_ms",
    }),
    ResponsibilityClass.ARTIFACT_COMPRESSION: frozenset({
        "logical_payload_bytes", "encoded_or_retained_bytes", "peak_working_memory_bytes",
        "encode_ms", "decode_or_reopen_ms",
    }),
    ResponsibilityClass.MODEL_STATE: frozenset({
        "logical_payload_bytes", "encoded_or_retained_bytes", "peak_working_memory_bytes",
        "startup_ms", "decode_or_reopen_ms", "downloaded_bytes",
    }),
}


def _text(v: Any, code: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise AssessmentError(code)
    return v.strip()


def _num(v: Any, code: str) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise AssessmentError(code)
    f = float(v)
    if f < 0:
        raise AssessmentError(code)
    return f


def _positive_int(v: Any, code: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise AssessmentError(code)
    return v


def _canonical(v: Any) -> bytes:
    try:
        return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise AssessmentError("NONCANONICAL_ASSESSMENT") from exc


def _digest(domain: str, v: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(v)).hexdigest()


@dataclass(frozen=True)
class BenchmarkScenario:
    workload_id: str
    model_ref: str
    runtime_ref: str
    execution_environment_ref: str
    prompt_tokens: int
    generated_tokens: int
    batch_size: int
    configured_context_tokens: int

    def __post_init__(self) -> None:
        for value, code in (
            (self.workload_id, "WORKLOAD_ID_REQUIRED"),
            (self.model_ref, "MODEL_REF_REQUIRED"),
            (self.runtime_ref, "RUNTIME_REF_REQUIRED"),
            (self.execution_environment_ref, "EXECUTION_ENVIRONMENT_REF_REQUIRED"),
        ):
            _text(value, code)
        for value, code in (
            (self.prompt_tokens, "PROMPT_TOKENS_INVALID"),
            (self.generated_tokens, "GENERATED_TOKENS_INVALID"),
            (self.batch_size, "BATCH_SIZE_INVALID"),
            (self.configured_context_tokens, "CONFIGURED_CONTEXT_TOKENS_INVALID"),
        ):
            _positive_int(value, code)
        if self.prompt_tokens + self.generated_tokens > self.configured_context_tokens:
            raise AssessmentError("WORKLOAD_EXCEEDS_CONFIGURED_CONTEXT")


@dataclass(frozen=True)
class MetricSet:
    logical_payload_bytes: int | None
    encoded_or_retained_bytes: int | None
    peak_working_memory_bytes: int | None
    startup_ms: float | None
    encode_ms: float | None
    decode_or_reopen_ms: float | None
    lookup_ms: float | None
    downloaded_bytes: int | None
    network_bytes: int | None
    energy_proxy: float | None = None
    kv_cache_peak_bytes: int | None = None
    ttft_ms: float | None = None
    prefill_ms: float | None = None
    decode_ms_per_token: float | None = None
    recompute_or_cache_load_ms: float | None = None

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if value is not None:
                _num(value, f"INVALID_METRIC:{f.name}")


METRIC_NAMES = frozenset(f.name for f in fields(MetricSet))


@dataclass(frozen=True)
class MeasuredPathEvidence:
    evidence_ref: str
    source_generation: str
    currentness_ref: str
    responsibility: ResponsibilityClass
    candidate_mechanism_observed: bool
    kv_cache_write_observed: bool = False
    kv_cache_read_observed: bool = False

    def __post_init__(self) -> None:
        for value, code in (
            (self.evidence_ref, "PATH_EVIDENCE_REF_REQUIRED"),
            (self.source_generation, "PATH_SOURCE_GENERATION_REQUIRED"),
            (self.currentness_ref, "PATH_CURRENTNESS_REF_REQUIRED"),
        ):
            _text(value, code)
        if not isinstance(self.responsibility, ResponsibilityClass):
            raise AssessmentError("PATH_RESPONSIBILITY_REQUIRED")
        for name in ("candidate_mechanism_observed", "kv_cache_write_observed", "kv_cache_read_observed"):
            if type(getattr(self, name)) is not bool:
                raise AssessmentError("PATH_OBSERVATION_BOOL_REQUIRED", name)


@dataclass(frozen=True)
class HostEvidenceBinding:
    witness_ref: str
    source_generation: str
    currentness_ref: str
    currentness_status: str

    def __post_init__(self) -> None:
        for value, code in (
            (self.witness_ref, "HOST_WITNESS_REF_REQUIRED"),
            (self.source_generation, "HOST_SOURCE_GENERATION_REQUIRED"),
            (self.currentness_ref, "HOST_CURRENTNESS_REF_REQUIRED"),
        ):
            _text(value, code)
        if self.currentness_status != "CURRENT":
            raise AssessmentError("HOST_EVIDENCE_NOT_CURRENT")


@dataclass(frozen=True)
class MechanismEvidence:
    mechanism_id: str
    mechanism_version: str
    source_ref: str
    source_generation: str
    currentness_ref: str
    responsibility: ResponsibilityClass
    responsibility_detail: str
    platform_scope: tuple[str, ...]
    baseline_id: str
    logical_payload_id: str
    quality_target: str
    scenario: BenchmarkScenario
    required_metrics: tuple[str, ...]
    candidate: MetricSet
    baseline: MetricSet
    path_evidence: MeasuredPathEvidence
    fidelity: FidelityClass
    fidelity_evidence_ref: str | None
    quality_threshold_ref: str | None
    evidence_class: EvidenceClass
    benchmark_ref: str | None
    counterexample: str
    trust_update_overhead: str
    invalidators: tuple[str, ...]
    host_evidence: HostEvidenceBinding | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for value, code in (
            (self.mechanism_id, "MECHANISM_ID_REQUIRED"),
            (self.mechanism_version, "MECHANISM_VERSION_REQUIRED"),
            (self.source_ref, "SOURCE_REF_REQUIRED"),
            (self.source_generation, "SOURCE_GENERATION_REQUIRED"),
            (self.currentness_ref, "CURRENTNESS_REF_REQUIRED"),
            (self.responsibility_detail, "RESPONSIBILITY_DETAIL_REQUIRED"),
            (self.baseline_id, "BASELINE_ID_REQUIRED"),
            (self.logical_payload_id, "LOGICAL_PAYLOAD_ID_REQUIRED"),
            (self.quality_target, "QUALITY_TARGET_REQUIRED"),
            (self.counterexample, "COUNTEREXAMPLE_REQUIRED"),
            (self.trust_update_overhead, "TRUST_UPDATE_OVERHEAD_REQUIRED"),
        ):
            _text(value, code)
        if not isinstance(self.responsibility, ResponsibilityClass):
            raise AssessmentError("RESPONSIBILITY_CLASS_REQUIRED")
        if not isinstance(self.scenario, BenchmarkScenario):
            raise AssessmentError("BENCHMARK_SCENARIO_REQUIRED")
        if not isinstance(self.path_evidence, MeasuredPathEvidence):
            raise AssessmentError("MEASURED_PATH_EVIDENCE_REQUIRED")
        if self.path_evidence.responsibility is not self.responsibility:
            raise AssessmentError("PATH_RESPONSIBILITY_MISMATCH")
        if not self.path_evidence.candidate_mechanism_observed:
            raise AssessmentError("CANDIDATE_MECHANISM_NOT_OBSERVED_ON_PATH")
        if self.responsibility is ResponsibilityClass.TRANSFORMER_KV_CACHE and not (
            self.path_evidence.kv_cache_write_observed and self.path_evidence.kv_cache_read_observed
        ):
            raise AssessmentError("KV_CACHE_IN_PATH_EVIDENCE_REQUIRED")
        if not isinstance(self.evidence_class, EvidenceClass):
            raise AssessmentError("EVIDENCE_CLASS_REQUIRED")
        if not isinstance(self.fidelity, FidelityClass):
            raise AssessmentError("FIDELITY_CLASS_REQUIRED")
        if not isinstance(self.platform_scope, tuple) or not self.platform_scope:
            raise AssessmentError("PLATFORM_SCOPE_REQUIRED")
        if any(not isinstance(x, str) or not x.strip() for x in self.platform_scope):
            raise AssessmentError("PLATFORM_SCOPE_INVALID")
        if not isinstance(self.required_metrics, tuple) or not self.required_metrics:
            raise AssessmentError("REQUIRED_METRICS_REQUIRED")
        invalid_metrics = sorted(set(self.required_metrics) - METRIC_NAMES)
        if invalid_metrics:
            raise AssessmentError("REQUIRED_METRIC_INVALID", ",".join(invalid_metrics))
        if len(set(self.required_metrics)) != len(self.required_metrics):
            raise AssessmentError("REQUIRED_METRIC_DUPLICATE")
        floor = RESPONSIBILITY_METRIC_FLOORS[self.responsibility]
        missing_floor = sorted(floor - set(self.required_metrics))
        if missing_floor:
            raise AssessmentError("RESPONSIBILITY_METRIC_FLOOR_MISSING", ",".join(missing_floor))
        if self.candidate.logical_payload_bytes is None or self.baseline.logical_payload_bytes is None:
            raise AssessmentError("LOGICAL_PAYLOAD_SIZE_REQUIRED")
        if self.candidate.logical_payload_bytes != self.baseline.logical_payload_bytes:
            raise AssessmentError("LOGICAL_PAYLOAD_SIZE_MISMATCH")
        if not isinstance(self.invalidators, tuple) or not self.invalidators:
            raise AssessmentError("INVALIDATORS_REQUIRED")
        if self.fidelity in {FidelityClass.EXACT, FidelityClass.BOUNDED_ACCEPTED} and not self.fidelity_evidence_ref:
            raise AssessmentError("FIDELITY_EVIDENCE_REQUIRED")
        if self.fidelity is FidelityClass.BOUNDED_ACCEPTED and not self.quality_threshold_ref:
            raise AssessmentError("QUALITY_THRESHOLD_REF_REQUIRED")
        if self.evidence_class in {
            EvidenceClass.LITERATURE_REPORTED, EvidenceClass.ANDROID_MEASURED,
            EvidenceClass.BROWSER_MEASURED, EvidenceClass.REPOSITORY_BENCHMARK,
        } and not self.benchmark_ref:
            raise AssessmentError("BENCHMARK_REF_REQUIRED")
        if self.evidence_class is EvidenceClass.ANDROID_MEASURED and not isinstance(self.host_evidence, HostEvidenceBinding):
            raise AssessmentError("ANDROID_HOST_EVIDENCE_REQUIRED")


def _ratio(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    if baseline == 0:
        return 1.0 if candidate == 0 else None
    return candidate / baseline


def _added_from_zero(candidate: float | None, baseline: float | None) -> bool:
    return baseline == 0 and candidate is not None and candidate > 0


def assess(e: MechanismEvidence) -> Mapping[str, Any]:
    if not isinstance(e, MechanismEvidence):
        raise AssessmentError("MECHANISM_EVIDENCE_REQUIRED")
    c, b = e.candidate, e.baseline
    reasons: list[str] = []

    effective_required = tuple(sorted(set(e.required_metrics) | RESPONSIBILITY_METRIC_FLOORS[e.responsibility]))
    required_unknown = tuple(name for name in effective_required if getattr(c, name) is None or getattr(b, name) is None)

    ratios = {
        "retained_bytes": _ratio(c.encoded_or_retained_bytes, b.encoded_or_retained_bytes),
        "peak_working_memory": _ratio(c.peak_working_memory_bytes, b.peak_working_memory_bytes),
        "startup": _ratio(c.startup_ms, b.startup_ms),
        "encode": _ratio(c.encode_ms, b.encode_ms),
        "decode_or_reopen": _ratio(c.decode_or_reopen_ms, b.decode_or_reopen_ms),
        "lookup": _ratio(c.lookup_ms, b.lookup_ms),
        "downloaded_bytes": _ratio(c.downloaded_bytes, b.downloaded_bytes),
        "network_bytes": _ratio(c.network_bytes, b.network_bytes),
        "kv_cache_peak_bytes": _ratio(c.kv_cache_peak_bytes, b.kv_cache_peak_bytes),
        "ttft": _ratio(c.ttft_ms, b.ttft_ms),
        "prefill": _ratio(c.prefill_ms, b.prefill_ms),
        "decode_ms_per_token": _ratio(c.decode_ms_per_token, b.decode_ms_per_token),
        "recompute_or_cache_load": _ratio(c.recompute_or_cache_load_ms, b.recompute_or_cache_load_ms),
    }
    ratio_metric_map = {
        "peak_working_memory": "peak_working_memory_bytes", "startup": "startup_ms",
        "encode": "encode_ms", "decode_or_reopen": "decode_or_reopen_ms", "lookup": "lookup_ms",
        "downloaded_bytes": "downloaded_bytes", "network_bytes": "network_bytes",
        "kv_cache_peak_bytes": "kv_cache_peak_bytes", "ttft": "ttft_ms", "prefill": "prefill_ms",
        "decode_ms_per_token": "decode_ms_per_token", "recompute_or_cache_load": "recompute_or_cache_load_ms",
    }
    storage_ratio = ratios["retained_bytes"]
    added_burdens = tuple(sorted(
        metric_name for metric_name in effective_required
        if metric_name != "encoded_or_retained_bytes" and _added_from_zero(getattr(c, metric_name), getattr(b, metric_name))
    ))

    if e.evidence_class is EvidenceClass.UNKNOWN:
        disposition = Disposition.UNKNOWN
        reasons.append("MEASURED_EVIDENCE_UNKNOWN")
    elif required_unknown:
        disposition = Disposition.UNKNOWN
        reasons.extend(f"REQUIRED_METRIC_UNKNOWN:{name}" for name in required_unknown)
    elif storage_ratio is None:
        disposition = Disposition.UNKNOWN
        reasons.append("STORAGE_RATIO_UNKNOWN")
    elif e.fidelity is FidelityClass.UNKNOWN:
        disposition = Disposition.UNKNOWN
        reasons.append("FIDELITY_UNKNOWN")
    elif e.fidelity is FidelityClass.BOUNDED_LOSS:
        disposition = Disposition.CONDITIONAL
        reasons.append("LOSSY_REQUIRES_QUALITY_DISPOSITION")
    else:
        hidden_cost = any(
            ratio is not None and ratio > 2.0
            for ratio_name, ratio in ratios.items()
            if ratio_name != "retained_bytes" and ratio_metric_map.get(ratio_name) in effective_required
        )
        if storage_ratio >= 1.0:
            disposition = Disposition.DEMOTE
            reasons.append("NO_RETAINED_BYTE_REDUCTION")
        elif added_burdens:
            disposition = Disposition.CONDITIONAL
            reasons.extend(f"ADDED_BURDEN_FROM_ZERO_BASELINE:{name}" for name in added_burdens)
        elif hidden_cost:
            disposition = Disposition.CONDITIONAL
            reasons.append("STORAGE_WIN_WITH_GT2X_MEASURED_LIFECYCLE_COST")
        else:
            disposition = Disposition.RETAIN
            reasons.append("QUALITY_ADMITTED_STORAGE_WIN_NO_GT2X_MEASURED_REGRESSION")

    if e.evidence_class in {EvidenceClass.SYNTHETIC, EvidenceClass.LITERATURE_REPORTED} and disposition is Disposition.RETAIN:
        disposition = Disposition.CONDITIONAL
        reasons.append("LITERATURE_CANNOT_PROVE_LOCAL_DEVICE_LIFECYCLE_WIN" if e.evidence_class is EvidenceClass.LITERATURE_REPORTED else "SYNTHETIC_CANNOT_PROVE_DEVICE_LIFECYCLE_WIN")
    if e.host_evidence is None and "ANDROID" in {x.upper() for x in e.platform_scope}:
        reasons.append("ANDROID_VIABILITY_NOT_PROVEN_WITHOUT_HOST_EVIDENCE")
        if disposition is Disposition.RETAIN:
            disposition = Disposition.CONDITIONAL

    host_binding_state = "CURRENT_BOUND" if e.host_evidence is not None else "UNBOUND"
    logical = {
        "schema": SCHEMA, "mechanism_id": e.mechanism_id, "mechanism_version": e.mechanism_version,
        "source_ref": e.source_ref, "source_generation": e.source_generation, "currentness_ref": e.currentness_ref,
        "responsibility": e.responsibility.value, "responsibility_detail": e.responsibility_detail,
        "platform_scope": e.platform_scope, "baseline_id": e.baseline_id, "logical_payload_id": e.logical_payload_id,
        "quality_target": e.quality_target, "scenario": asdict(e.scenario), "required_metrics": e.required_metrics,
        "effective_required_metrics": effective_required, "candidate": asdict(c), "baseline": asdict(b),
        "path_evidence": {**asdict(e.path_evidence), "responsibility": e.path_evidence.responsibility.value},
        "ratios": ratios, "added_burdens": added_burdens, "fidelity": e.fidelity.value,
        "fidelity_evidence_ref": e.fidelity_evidence_ref, "quality_threshold_ref": e.quality_threshold_ref,
        "evidence_class": e.evidence_class.value, "benchmark_ref": e.benchmark_ref,
        "counterexample": e.counterexample, "trust_update_overhead": e.trust_update_overhead,
        "host_evidence": asdict(e.host_evidence) if e.host_evidence else None, "host_binding_state": host_binding_state,
        "invalidators": e.invalidators, "disposition": disposition.value, "reasons": tuple(reasons),
        "effect_authorized": False, "device_viability_proven": False,
    }
    return {**logical, "logical_id": "lsm-" + _digest("LOW_STORAGE_MECHANISM_ASSESSMENT_V1", logical)[:32], "claim_ceiling": "EVIDENCE_REDUCER_ONLY_NO_DEVICE_BENCHMARK_OR_INSTALL_EFFECT"}


def inventory_status(mechanism_id: str, *, current_code_refs: Sequence[str], measurement_refs: Sequence[str]) -> Mapping[str, Any]:
    mid = _text(mechanism_id, "MECHANISM_ID_REQUIRED")
    code = tuple(_text(x, "CODE_REF_INVALID") for x in current_code_refs)
    measurements = tuple(_text(x, "MEASUREMENT_REF_INVALID") for x in measurement_refs)
    if not code:
        status = "NO_CURRENT_EXECUTABLE_MAPPING_FOUND"
    elif not measurements:
        status = "EXECUTABLE_MAPPING_PRESENT_MEASUREMENT_MISSING"
    else:
        status = "READY_FOR_ASSESSMENT"
    return {"mechanism_id": mid, "current_code_refs": code, "measurement_refs": measurements, "status": status}

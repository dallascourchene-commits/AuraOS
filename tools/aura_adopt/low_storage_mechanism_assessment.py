"""AURA-ADOPT-001 ZF-06A low-storage mechanism assessment.

Pure evidence reducer. It does not benchmark a device, execute a mechanism,
or convert historical mechanism names into performance claims.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
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
    REPOSITORY_BENCHMARK = "REPOSITORY_BENCHMARK"
    BROWSER_MEASURED = "BROWSER_MEASURED"
    ANDROID_MEASURED = "ANDROID_MEASURED"
    UNKNOWN = "UNKNOWN"


class FidelityClass(str, Enum):
    EXACT = "EXACT"
    BOUNDED_LOSS = "BOUNDED_LOSS"
    UNKNOWN = "UNKNOWN"


class Disposition(str, Enum):
    RETAIN = "RETAIN"
    CONDITIONAL = "CONDITIONAL"
    DEMOTE = "DEMOTE"
    UNKNOWN = "UNKNOWN"


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


def _canonical(v: Any) -> bytes:
    try:
        return json.dumps(
            v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    except (TypeError, ValueError) as exc:
        raise AssessmentError("NONCANONICAL_ASSESSMENT") from exc


def _digest(domain: str, v: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(v)).hexdigest()


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

    def __post_init__(self) -> None:
        for name in (
            "logical_payload_bytes", "encoded_or_retained_bytes", "peak_working_memory_bytes",
            "startup_ms", "encode_ms", "decode_or_reopen_ms", "lookup_ms",
            "downloaded_bytes", "network_bytes", "energy_proxy",
        ):
            value = getattr(self, name)
            if value is not None:
                _num(value, f"INVALID_METRIC:{name}")


@dataclass(frozen=True)
class MechanismEvidence:
    mechanism_id: str
    mechanism_version: str
    source_ref: str
    source_generation: str
    currentness_ref: str
    responsibility: str
    platform_scope: tuple[str, ...]
    baseline_id: str
    logical_payload_id: str
    quality_target: str
    candidate: MetricSet
    baseline: MetricSet
    fidelity: FidelityClass
    fidelity_evidence_ref: str | None
    evidence_class: EvidenceClass
    benchmark_ref: str | None
    counterexample: str
    trust_update_overhead: str
    invalidators: tuple[str, ...]
    host_witness_ref: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for value, code in (
            (self.mechanism_id, "MECHANISM_ID_REQUIRED"),
            (self.mechanism_version, "MECHANISM_VERSION_REQUIRED"),
            (self.source_ref, "SOURCE_REF_REQUIRED"),
            (self.source_generation, "SOURCE_GENERATION_REQUIRED"),
            (self.currentness_ref, "CURRENTNESS_REF_REQUIRED"),
            (self.responsibility, "RESPONSIBILITY_REQUIRED"),
            (self.baseline_id, "BASELINE_ID_REQUIRED"),
            (self.logical_payload_id, "LOGICAL_PAYLOAD_ID_REQUIRED"),
            (self.quality_target, "QUALITY_TARGET_REQUIRED"),
            (self.counterexample, "COUNTEREXAMPLE_REQUIRED"),
            (self.trust_update_overhead, "TRUST_UPDATE_OVERHEAD_REQUIRED"),
        ):
            _text(value, code)
        if not isinstance(self.evidence_class, EvidenceClass):
            raise AssessmentError("EVIDENCE_CLASS_REQUIRED")
        if not isinstance(self.fidelity, FidelityClass):
            raise AssessmentError("FIDELITY_CLASS_REQUIRED")
        if not isinstance(self.platform_scope, tuple) or not self.platform_scope:
            raise AssessmentError("PLATFORM_SCOPE_REQUIRED")
        if any(not isinstance(x, str) or not x.strip() for x in self.platform_scope):
            raise AssessmentError("PLATFORM_SCOPE_INVALID")
        if not isinstance(self.invalidators, tuple) or not self.invalidators:
            raise AssessmentError("INVALIDATORS_REQUIRED")
        if self.fidelity is FidelityClass.EXACT and not self.fidelity_evidence_ref:
            raise AssessmentError("EXACT_FIDELITY_EVIDENCE_REQUIRED")
        if (
            self.evidence_class
            in {EvidenceClass.ANDROID_MEASURED, EvidenceClass.BROWSER_MEASURED, EvidenceClass.REPOSITORY_BENCHMARK}
            and not self.benchmark_ref
        ):
            raise AssessmentError("BENCHMARK_REF_REQUIRED")
        if self.evidence_class is EvidenceClass.ANDROID_MEASURED and not self.host_witness_ref:
            raise AssessmentError("ANDROID_HOST_WITNESS_REQUIRED")


def _ratio(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None or baseline == 0:
        return None
    return candidate / baseline


def assess(e: MechanismEvidence) -> Mapping[str, Any]:
    if not isinstance(e, MechanismEvidence):
        raise AssessmentError("MECHANISM_EVIDENCE_REQUIRED")
    c, b = e.candidate, e.baseline
    reasons: list[str] = []
    storage_ratio = _ratio(c.encoded_or_retained_bytes, b.encoded_or_retained_bytes)
    memory_ratio = _ratio(c.peak_working_memory_bytes, b.peak_working_memory_bytes)
    startup_ratio = _ratio(c.startup_ms, b.startup_ms)
    reopen_ratio = _ratio(c.decode_or_reopen_ms, b.decode_or_reopen_ms)
    download_ratio = _ratio(c.downloaded_bytes, b.downloaded_bytes)
    network_ratio = _ratio(c.network_bytes, b.network_bytes)

    if e.evidence_class is EvidenceClass.UNKNOWN:
        disposition = Disposition.UNKNOWN
        reasons.append("MEASURED_EVIDENCE_UNKNOWN")
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
            r is not None and r > 2.0
            for r in (memory_ratio, startup_ratio, reopen_ratio, download_ratio, network_ratio)
        )
        if storage_ratio >= 1.0:
            disposition = Disposition.DEMOTE
            reasons.append("NO_RETAINED_BYTE_REDUCTION")
        elif hidden_cost:
            disposition = Disposition.CONDITIONAL
            reasons.append("STORAGE_WIN_WITH_GT2X_MEASURED_LIFECYCLE_COST")
        else:
            disposition = Disposition.RETAIN
            reasons.append("EXACT_FIDELITY_STORAGE_WIN_NO_GT2X_MEASURED_REGRESSION")

    if e.evidence_class is EvidenceClass.SYNTHETIC and disposition is Disposition.RETAIN:
        disposition = Disposition.CONDITIONAL
        reasons.append("SYNTHETIC_CANNOT_PROVE_DEVICE_LIFECYCLE_WIN")
    if e.host_witness_ref is None and "ANDROID" in {x.upper() for x in e.platform_scope}:
        reasons.append("ANDROID_VIABILITY_NOT_PROVEN_WITHOUT_HOST_WITNESS")
        if disposition is Disposition.RETAIN:
            disposition = Disposition.CONDITIONAL

    logical = {
        "schema": SCHEMA,
        "mechanism_id": e.mechanism_id,
        "mechanism_version": e.mechanism_version,
        "source_ref": e.source_ref,
        "source_generation": e.source_generation,
        "currentness_ref": e.currentness_ref,
        "responsibility": e.responsibility,
        "platform_scope": e.platform_scope,
        "baseline_id": e.baseline_id,
        "logical_payload_id": e.logical_payload_id,
        "quality_target": e.quality_target,
        "candidate": asdict(c),
        "baseline": asdict(b),
        "ratios": {
            "retained_bytes": storage_ratio,
            "peak_working_memory": memory_ratio,
            "startup": startup_ratio,
            "decode_or_reopen": reopen_ratio,
            "downloaded_bytes": download_ratio,
            "network_bytes": network_ratio,
        },
        "fidelity": e.fidelity.value,
        "fidelity_evidence_ref": e.fidelity_evidence_ref,
        "evidence_class": e.evidence_class.value,
        "benchmark_ref": e.benchmark_ref,
        "counterexample": e.counterexample,
        "trust_update_overhead": e.trust_update_overhead,
        "host_witness_ref": e.host_witness_ref,
        "invalidators": e.invalidators,
        "disposition": disposition.value,
        "reasons": tuple(reasons),
        "effect_authorized": False,
        "device_viability_proven": bool(
            e.evidence_class is EvidenceClass.ANDROID_MEASURED and e.host_witness_ref
        ),
    }
    return {
        **logical,
        "logical_id": "lsm-" + _digest("LOW_STORAGE_MECHANISM_ASSESSMENT_V1", logical)[:32],
        "claim_ceiling": "EVIDENCE_REDUCER_ONLY_NO_DEVICE_BENCHMARK_OR_INSTALL_EFFECT",
    }


def inventory_status(
    mechanism_id: str, *, current_code_refs: Sequence[str], measurement_refs: Sequence[str]
) -> Mapping[str, Any]:
    mid = _text(mechanism_id, "MECHANISM_ID_REQUIRED")
    code = tuple(_text(x, "CODE_REF_INVALID") for x in current_code_refs)
    measurements = tuple(_text(x, "MEASUREMENT_REF_INVALID") for x in measurement_refs)
    if not code:
        status = "NO_CURRENT_EXECUTABLE_MAPPING_FOUND"
    elif not measurements:
        status = "EXECUTABLE_MAPPING_PRESENT_MEASUREMENT_MISSING"
    else:
        status = "READY_FOR_ASSESSMENT"
    return {
        "mechanism_id": mid,
        "current_code_refs": code,
        "measurement_refs": measurements,
        "status": status,
    }

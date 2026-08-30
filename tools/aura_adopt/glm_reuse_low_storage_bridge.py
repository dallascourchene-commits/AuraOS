"""Bridge AWJ032 GLM host-I/O reuse evidence into ZF-06A low-storage assessment.

D0 evidence composition only. This module deliberately separates three questions:
1. Did selected-expert caching/paging reduce physical expert I/O for a scoped trace?
2. Did the representation actually reduce retained/encoded bytes?
3. Did any storage win preserve bounded lifecycle, memory, download and fidelity costs?

A high GLM `measured_reuse_ratio` is never projected into ZF-06A
`encoded_or_retained_bytes`. Retained-storage evidence must arrive independently.
This bridge performs no model execution, host sampling, checkpoint effect, device
benchmark, install, provider call, or G2 admission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping

try:
    from .low_storage_mechanism_assessment import (
        BenchmarkScenario,
        EvidenceClass,
        FidelityClass,
        MechanismEvidence,
        MetricSet,
        assess,
    )
except ImportError:
    from low_storage_mechanism_assessment import (
        BenchmarkScenario,
        EvidenceClass,
        FidelityClass,
        MechanismEvidence,
        MetricSet,
        assess,
    )

PREFLIGHT_SCHEMA = "GLM53HostCanaryPreflightReceiptV1"
OBSERVATION_SCHEMA = "GLMStorageLifecycleObservationV1"
BRIDGE_SCHEMA = "GLMReuseLowStorageBridgeV1"


class GLMStorageBridgeError(ValueError):
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
        raise GLMStorageBridgeError("NONCANONICAL_BRIDGE_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GLMStorageBridgeError(code)
    return value.strip()


def _nonnegative(value: Any, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GLMStorageBridgeError(code)
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise GLMStorageBridgeError(code)
    return result


def _nonnegative_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GLMStorageBridgeError(code)
    return value


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GLMStorageBridgeError(code)
    return value


@dataclass(frozen=True)
class GLMStorageLifecycleObservationV1:
    observation_ref: str
    source_generation: str
    currentness_ref: str
    candidate_retained_bytes: int
    baseline_retained_bytes: int
    candidate_peak_working_memory_bytes: int
    baseline_peak_working_memory_bytes: int
    candidate_startup_ms: float
    baseline_startup_ms: float
    candidate_reopen_ms: float
    baseline_reopen_ms: float
    candidate_downloaded_bytes: int
    baseline_downloaded_bytes: int
    candidate_network_bytes: int
    baseline_network_bytes: int
    fidelity: FidelityClass
    fidelity_evidence_ref: str
    evidence_class: EvidenceClass
    benchmark_ref: str
    trust_update_overhead: str
    counterexample: str
    host_witness_ref: str | None = None
    schema: str = OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != OBSERVATION_SCHEMA:
            raise GLMStorageBridgeError("OBSERVATION_SCHEMA_MISMATCH")
        for value, code in (
            (self.observation_ref, "OBSERVATION_REF_REQUIRED"),
            (self.source_generation, "SOURCE_GENERATION_REQUIRED"),
            (self.currentness_ref, "CURRENTNESS_REF_REQUIRED"),
            (self.fidelity_evidence_ref, "FIDELITY_EVIDENCE_REF_REQUIRED"),
            (self.benchmark_ref, "BENCHMARK_REF_REQUIRED"),
            (self.trust_update_overhead, "TRUST_UPDATE_OVERHEAD_REQUIRED"),
            (self.counterexample, "COUNTEREXAMPLE_REQUIRED"),
        ):
            _text(value, code)
        for value, code in (
            (self.candidate_retained_bytes, "CANDIDATE_RETAINED_BYTES_INVALID"),
            (self.baseline_retained_bytes, "BASELINE_RETAINED_BYTES_INVALID"),
            (self.candidate_peak_working_memory_bytes, "CANDIDATE_PEAK_MEMORY_INVALID"),
            (self.baseline_peak_working_memory_bytes, "BASELINE_PEAK_MEMORY_INVALID"),
            (self.candidate_downloaded_bytes, "CANDIDATE_DOWNLOADED_BYTES_INVALID"),
            (self.baseline_downloaded_bytes, "BASELINE_DOWNLOADED_BYTES_INVALID"),
            (self.candidate_network_bytes, "CANDIDATE_NETWORK_BYTES_INVALID"),
            (self.baseline_network_bytes, "BASELINE_NETWORK_BYTES_INVALID"),
        ):
            _nonnegative_int(value, code)
        if self.baseline_retained_bytes == 0:
            raise GLMStorageBridgeError("BASELINE_RETAINED_BYTES_ZERO")
        for value, code in (
            (self.candidate_startup_ms, "CANDIDATE_STARTUP_MS_INVALID"),
            (self.baseline_startup_ms, "BASELINE_STARTUP_MS_INVALID"),
            (self.candidate_reopen_ms, "CANDIDATE_REOPEN_MS_INVALID"),
            (self.baseline_reopen_ms, "BASELINE_REOPEN_MS_INVALID"),
        ):
            _nonnegative(value, code)
        if not isinstance(self.fidelity, FidelityClass):
            raise GLMStorageBridgeError("FIDELITY_CLASS_REQUIRED")
        if not isinstance(self.evidence_class, EvidenceClass):
            raise GLMStorageBridgeError("EVIDENCE_CLASS_REQUIRED")

    @property
    def digest(self) -> str:
        row = asdict(self)
        row["fidelity"] = self.fidelity.value
        row["evidence_class"] = self.evidence_class.value
        return _digest(row)


def validate_glm_preflight(preflight: Mapping[str, Any]) -> Mapping[str, Any]:
    row = _mapping(preflight, "GLM_PREFLIGHT_MAPPING_REQUIRED")
    if row.get("schema") != PREFLIGHT_SCHEMA:
        raise GLMStorageBridgeError("GLM_PREFLIGHT_SCHEMA_MISMATCH")
    for field in (
        "execution_authorized",
        "effect_authorized",
        "g2_admitted",
        "large_checkpoint_admitted",
        "runtime_execution_proven",
    ):
        if row.get(field) is not False:
            raise GLMStorageBridgeError("GLM_PREFLIGHT_AUTHORITY_WIDENING", field)
    if row.get("host_measurement_complete") is not True:
        raise GLMStorageBridgeError("GLM_HOST_MEASUREMENT_INCOMPLETE")
    if row.get("w4_evidence_admissible") is not True:
        raise GLMStorageBridgeError("GLM_W4_EVIDENCE_NOT_ADMISSIBLE")
    logical = _nonnegative_int(
        row.get("logical_expert_bytes_required"), "GLM_LOGICAL_EXPERT_BYTES_INVALID"
    )
    physical = _nonnegative_int(
        row.get("physical_expert_bytes_read"), "GLM_PHYSICAL_EXPERT_BYTES_INVALID"
    )
    if logical <= 0:
        raise GLMStorageBridgeError("GLM_LOGICAL_EXPERT_BYTES_ZERO")
    expected_reuse = max(0.0, min(1.0, 1.0 - (physical / logical)))
    observed_reuse = _nonnegative(row.get("measured_reuse_ratio"), "GLM_REUSE_RATIO_INVALID")
    if observed_reuse > 1.0 or not math.isclose(observed_reuse, expected_reuse, rel_tol=1e-12, abs_tol=1e-12):
        raise GLMStorageBridgeError("GLM_REUSE_RATIO_MISMATCH")
    if bool(row.get("physical_io_amplification")) != (physical > logical):
        raise GLMStorageBridgeError("GLM_IO_AMPLIFICATION_MISMATCH")
    _text(row.get("receipt_digest"), "GLM_PREFLIGHT_RECEIPT_DIGEST_REQUIRED")
    return row


def unresolved_storage_frontier(preflight: Mapping[str, Any]) -> dict[str, Any]:
    """Expose verified I/O reuse while refusing to invent retained-storage metrics."""
    row = validate_glm_preflight(preflight)
    body = {
        "schema": BRIDGE_SCHEMA,
        "decision": "STORAGE_LIFECYCLE_MEASUREMENT_REQUIRED",
        "glm_preflight_receipt_digest": row["receipt_digest"],
        "measured_io_reuse_ratio": row["measured_reuse_ratio"],
        "physical_io_amplification": row["physical_io_amplification"],
        "retained_storage_reduction_proven": False,
        "candidate_retained_bytes": None,
        "baseline_retained_bytes": None,
        "effect_authorized": False,
        "device_viability_proven": False,
    }
    body["frontier_digest"] = _digest(body)
    return body


def compile_glm_low_storage_evidence(
    *,
    preflight: Mapping[str, Any],
    storage_observation: GLMStorageLifecycleObservationV1,
    scenario: BenchmarkScenario,
    mechanism_id: str,
    mechanism_version: str,
    mechanism_source_ref: str,
    logical_payload_id: str,
    quality_target: str,
    quality_threshold_ref: str | None = None,
) -> MechanismEvidence:
    """Create ZF-06A evidence without converting I/O reuse into storage reduction."""
    row = validate_glm_preflight(preflight)
    if not isinstance(storage_observation, GLMStorageLifecycleObservationV1):
        raise GLMStorageBridgeError("STORAGE_LIFECYCLE_OBSERVATION_REQUIRED")
    if not isinstance(scenario, BenchmarkScenario):
        raise GLMStorageBridgeError("BENCHMARK_SCENARIO_REQUIRED")

    # These dimensions come only from the independent storage/lifecycle observation.
    candidate = MetricSet(
        logical_payload_bytes=row["logical_expert_bytes_required"],
        encoded_or_retained_bytes=storage_observation.candidate_retained_bytes,
        peak_working_memory_bytes=storage_observation.candidate_peak_working_memory_bytes,
        startup_ms=storage_observation.candidate_startup_ms,
        encode_ms=None,
        decode_or_reopen_ms=storage_observation.candidate_reopen_ms,
        lookup_ms=None,
        downloaded_bytes=storage_observation.candidate_downloaded_bytes,
        network_bytes=storage_observation.candidate_network_bytes,
        energy_proxy=None,
        kv_cache_peak_bytes=None,
        ttft_ms=None,
        prefill_ms=None,
        decode_ms_per_token=None,
        recompute_or_cache_load_ms=None,
    )
    baseline = MetricSet(
        logical_payload_bytes=row["logical_expert_bytes_required"],
        encoded_or_retained_bytes=storage_observation.baseline_retained_bytes,
        peak_working_memory_bytes=storage_observation.baseline_peak_working_memory_bytes,
        startup_ms=storage_observation.baseline_startup_ms,
        encode_ms=None,
        decode_or_reopen_ms=storage_observation.baseline_reopen_ms,
        lookup_ms=None,
        downloaded_bytes=storage_observation.baseline_downloaded_bytes,
        network_bytes=storage_observation.baseline_network_bytes,
        energy_proxy=None,
        kv_cache_peak_bytes=None,
        ttft_ms=None,
        prefill_ms=None,
        decode_ms_per_token=None,
        recompute_or_cache_load_ms=None,
    )

    benchmark_ref = (
        f"{storage_observation.benchmark_ref}|glm-preflight:{row['receipt_digest']}|"
        f"storage-observation:{storage_observation.digest}"
    )
    return MechanismEvidence(
        mechanism_id=_text(mechanism_id, "MECHANISM_ID_REQUIRED"),
        mechanism_version=_text(mechanism_version, "MECHANISM_VERSION_REQUIRED"),
        source_ref=_text(mechanism_source_ref, "MECHANISM_SOURCE_REF_REQUIRED"),
        source_generation=storage_observation.source_generation,
        currentness_ref=storage_observation.currentness_ref,
        responsibility="Reduce retained representation/storage while preserving bounded GLM lifecycle costs; expert I/O reuse remains a separate measured benefit.",
        platform_scope=("THINKPAD_WSL",),
        baseline_id=f"glm-baseline:{storage_observation.observation_ref}",
        logical_payload_id=_text(logical_payload_id, "LOGICAL_PAYLOAD_ID_REQUIRED"),
        quality_target=_text(quality_target, "QUALITY_TARGET_REQUIRED"),
        scenario=scenario,
        required_metrics=(
            "encoded_or_retained_bytes",
            "peak_working_memory_bytes",
            "startup_ms",
            "decode_or_reopen_ms",
            "downloaded_bytes",
            "network_bytes",
        ),
        candidate=candidate,
        baseline=baseline,
        fidelity=storage_observation.fidelity,
        fidelity_evidence_ref=storage_observation.fidelity_evidence_ref,
        quality_threshold_ref=quality_threshold_ref,
        evidence_class=storage_observation.evidence_class,
        benchmark_ref=benchmark_ref,
        counterexample=(
            storage_observation.counterexample
            + f"; GLM measured I/O reuse={row['measured_reuse_ratio']:.6f} is explicitly not retained-storage proof."
        ),
        trust_update_overhead=storage_observation.trust_update_overhead,
        invalidators=(
            "GLM preflight/W4 source changes",
            "storage or lifecycle observation currentness changes",
            "logical payload or quality target changes",
            "host/filesystem/cache regime changes",
        ),
        host_witness_ref=storage_observation.host_witness_ref,
        notes=(
            f"glm_io_reuse_ratio={row['measured_reuse_ratio']};"
            f"physical_io_amplification={row['physical_io_amplification']};"
            "retained_bytes_source=independent_storage_observation"
        ),
    )


def assess_glm_low_storage_candidate(**kwargs: Any) -> Mapping[str, Any]:
    evidence = compile_glm_low_storage_evidence(**kwargs)
    result = dict(assess(evidence))
    preflight = validate_glm_preflight(kwargs["preflight"])
    result["glm_io_reuse_ratio"] = preflight["measured_reuse_ratio"]
    result["glm_io_reuse_is_retained_storage_proof"] = False
    result["bridge_digest"] = _digest(
        {
            "assessment_logical_id": result["logical_id"],
            "glm_preflight_receipt_digest": preflight["receipt_digest"],
            "glm_io_reuse_ratio": preflight["measured_reuse_ratio"],
            "storage_observation_digest": kwargs["storage_observation"].digest,
        }
    )
    return result

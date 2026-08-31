"""Software-only spatial-display simulation benchmark evidence contract.

This adapts the owner-host cold/warm/restart measurement discipline to the
imported hologram/eye-tracking proposal. It may record software execution
latency. It cannot self-mint ThinkPad identity, thermal/power evidence, optical
correctness, physical display performance, or effect authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Sequence


SCHEMA = "AURA_K27_SPATIAL_DISPLAY_SIM_BENCHMARK_V1"
PHASES = ("PROCESS_COLD", "PROCESS_WARM", "RESTART")
COMPONENTS = {
    "ASM_PROPAGATION",
    "PHASE_STEERING",
    "EYE_POSE_ESTIMATE",
    "PHASE_MASK_SERIALIZATION",
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(name: str, value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value.lower()


def _positive(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class SimulationBenchmarkRequest:
    imported_source_sha256: str
    component: str
    implementation_generation: str
    runtime_generation: str
    environment_sha256: str
    input_fixture_sha256: str
    device_selector: str
    width_px: int
    height_px: int
    precision: str
    warmup_iterations: int
    measured_iterations: int
    candidate_latency_claim_ns: int

    def validate(self) -> None:
        _sha("imported_source_sha256", self.imported_source_sha256)
        _sha("environment_sha256", self.environment_sha256)
        _sha("input_fixture_sha256", self.input_fixture_sha256)
        if self.component not in COMPONENTS:
            raise ValueError("unsupported benchmark component")
        for name in ("implementation_generation", "runtime_generation", "device_selector", "precision"):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        _positive("width_px", self.width_px)
        _positive("height_px", self.height_px)
        _positive("warmup_iterations", self.warmup_iterations)
        _positive("measured_iterations", self.measured_iterations)
        _positive("candidate_latency_claim_ns", self.candidate_latency_claim_ns)

    def digest(self) -> str:
        self.validate()
        return hashlib.sha256(_canonical_json(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SimulationPhaseSample:
    phase: str
    request_sha256: str
    process_identity: str
    observed_runtime_device: str
    observed_runtime_generation: str
    iterations: int
    elapsed_total_ns: int
    output_sha256: str

    def validate(self) -> None:
        if self.phase not in PHASES:
            raise ValueError("invalid phase")
        _sha("request_sha256", self.request_sha256)
        _sha("output_sha256", self.output_sha256)
        for name in ("process_identity", "observed_runtime_device", "observed_runtime_generation"):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        _positive("iterations", self.iterations)
        _positive("elapsed_total_ns", self.elapsed_total_ns)

    @property
    def average_latency_ns(self) -> float:
        return self.elapsed_total_ns / self.iterations


@dataclass(frozen=True)
class SimulationBenchmarkGate:
    admitted_software_measurement: bool
    refusals: tuple[str, ...]
    process_phase_semantics_exact: bool
    request_identity_exact: bool
    iteration_count_exact: bool
    candidate_threshold_met_in_warm_phase: bool
    thinkpad_identity_proven: bool = False
    thermal_power_proven: bool = False
    physical_optics_proven: bool = False
    real_display_performance_proven: bool = False
    effect_authority: bool = False


def validate_simulation_samples(
    *,
    request: SimulationBenchmarkRequest,
    samples: Sequence[SimulationPhaseSample],
) -> SimulationBenchmarkGate:
    request.validate()
    refusals: list[str] = []
    if len(samples) != 3:
        return SimulationBenchmarkGate(
            admitted_software_measurement=False,
            refusals=("EXACTLY_THREE_PHASES_REQUIRED",),
            process_phase_semantics_exact=False,
            request_identity_exact=False,
            iteration_count_exact=False,
            candidate_threshold_met_in_warm_phase=False,
        )

    for sample in samples:
        sample.validate()

    phase_exact = tuple(sample.phase for sample in samples) == PHASES
    if not phase_exact:
        refusals.append("PHASE_ORDER_MISMATCH")

    process_exact = (
        samples[0].process_identity == samples[1].process_identity
        and samples[2].process_identity != samples[0].process_identity
    )
    if not process_exact:
        refusals.append("PROCESS_COLD_WARM_RESTART_IDENTITY_MISMATCH")

    request_digest = request.digest()
    request_exact = all(sample.request_sha256 == request_digest for sample in samples)
    if not request_exact:
        refusals.append("REQUEST_IDENTITY_MISMATCH")

    iteration_exact = all(sample.iterations == request.measured_iterations for sample in samples)
    if not iteration_exact:
        refusals.append("MEASURED_ITERATION_COUNT_MISMATCH")

    runtime_generation_exact = all(
        sample.observed_runtime_generation == request.runtime_generation for sample in samples
    )
    if not runtime_generation_exact:
        refusals.append("RUNTIME_GENERATION_MISMATCH")

    process_phase_semantics_exact = phase_exact and process_exact
    warm_threshold_met = samples[1].average_latency_ns <= request.candidate_latency_claim_ns

    return SimulationBenchmarkGate(
        admitted_software_measurement=not refusals,
        refusals=tuple(refusals),
        process_phase_semantics_exact=process_phase_semantics_exact,
        request_identity_exact=request_exact,
        iteration_count_exact=iteration_exact,
        candidate_threshold_met_in_warm_phase=warm_threshold_met,
    )


def build_simulation_benchmark_receipt(
    *,
    request: SimulationBenchmarkRequest,
    samples: Sequence[SimulationPhaseSample],
    gate: SimulationBenchmarkGate,
    parent_artifact_ids: Sequence[str],
) -> Mapping[str, object]:
    parents = tuple(parent_artifact_ids)
    if len(parents) != 2 or len(set(parents)) != 2 or any(not parent for parent in parents):
        raise ValueError("exactly two distinct non-empty parent artifact IDs are required")
    request.validate()
    for sample in samples:
        sample.validate()

    payload = {
        "schema": SCHEMA,
        "parent_artifact_ids": parents,
        "request": asdict(request),
        "request_sha256": request.digest(),
        "samples": [asdict(sample) for sample in samples],
        "average_latency_ns": [sample.average_latency_ns for sample in samples],
        "gate": asdict(gate),
        "claim_ceiling": {
            "host_is_user_thinkpad": False,
            "host_identity_authenticated": False,
            "os_page_cache_cold": False,
            "device_cache_cold": False,
            "thermal_power_measured": False,
            "physical_optics_measured": False,
            "panel_or_slm_latency_measured": False,
            "optical_quality_proven": False,
            "candidate_claim_generalized_to_hardware": False,
            "performance_winner_proven": False,
            "display_effect_authorized": False,
            "gate10_promoted": False,
        },
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "receipt_sha256": digest}


def verify_simulation_benchmark_receipt(receipt: Mapping[str, object]) -> bool:
    expected = {
        "schema",
        "parent_artifact_ids",
        "request",
        "request_sha256",
        "samples",
        "average_latency_ns",
        "gate",
        "claim_ceiling",
        "receipt_sha256",
    }
    if set(receipt) != expected or receipt.get("schema") != SCHEMA:
        return False
    ceiling = receipt.get("claim_ceiling")
    if not isinstance(ceiling, dict) or not ceiling or any(v is not False for v in ceiling.values()):
        return False
    payload = {key: receipt[key] for key in expected if key != "receipt_sha256"}
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return receipt.get("receipt_sha256") == digest

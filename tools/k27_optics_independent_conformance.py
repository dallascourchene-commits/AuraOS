"""Producer-traversed independent numerical conformance for K27 optics.

The canonical receipt path accepts no caller-selected findings, source digest,
parents, tolerances, or PASS bit. It executes both formula paths over the frozen
matrix internally and binds a code-owned imported-source identity. Agreement is
software evidence only; physical optics/performance/authority remain false.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import cmath
import hashlib
import json
import math
from typing import Mapping, Sequence

import k27_optics_candidate_falsifier as imported

SCHEMA = "AURA_K27_OPTICS_INDEPENDENT_CONFORMANCE_V2"
CANONICAL_PARENT_ARTIFACT_IDS = (
    "1l8FLO6a0ebJX1D4L2VP5PThii4P_vcGGrGMxBHYy_Ew",
    "10OUpjrsvxaVfJprxqCIuGcX9cB0V58noo4mbzYW4peg",
)
IMPORTED_SOURCE_SHA256 = "56d8593284d37ce03a2762dedc2390878ee6d271a0f1f100a5e245ad01080d6d"
COMPLEX_TOLERANCE = 1e-9
PHASE_TOLERANCE_RADIANS = 1e-9

CLAIM_CEILING = {
    "independent_software_agreement_is_physical_optics_truth": False,
    "optical_hardware_observed": False,
    "speckle_free_proven": False,
    "zero_light_leakage_proven": False,
    "display_latency_proven": False,
    "image_quality_proven": False,
    "optical_safety_proven": False,
    "deployment_ready": False,
    "effect_authority": False,
    "gate10_promoted": False,
    "semantic_k27_authority": False,
    "native_transformer_kv_accessed": False,
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def circular_phase_error(a: float, b: float) -> float:
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


@dataclass(frozen=True)
class ASMConformanceCase:
    fx_cycles_per_m: float
    fy_cycles_per_m: float
    z_m: float
    wavelength_m: float


@dataclass(frozen=True)
class SteeringConformanceCase:
    base_phase_radians: float
    sample_x_m: float
    sample_y_m: float
    eye_x_m: float
    eye_y_m: float
    eye_z_m: float
    wavelength_m: float


@dataclass(frozen=True)
class ConformanceFinding:
    domain: str
    case_index: int
    class_agreement: bool
    numeric_error: float
    within_tolerance: bool


def independent_asm_transfer(case: ASMConformanceCase) -> tuple[complex, bool]:
    values = (case.fx_cycles_per_m, case.fy_cycles_per_m, case.z_m, case.wavelength_m)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("all ASM case values must be finite")
    if case.wavelength_m <= 0.0:
        raise ValueError("wavelength_m must be positive")
    k = 2.0 * math.pi / case.wavelength_m
    kx = 2.0 * math.pi * case.fx_cycles_per_m
    ky = 2.0 * math.pi * case.fy_cycles_per_m
    kz_sq = k * k - kx * kx - ky * ky
    if kz_sq < 0.0:
        return 0j, False
    return cmath.exp(1j * math.sqrt(max(0.0, kz_sq)) * case.z_m), True


def independent_phase_steering(case: SteeringConformanceCase) -> float:
    values = (
        case.base_phase_radians, case.sample_x_m, case.sample_y_m,
        case.eye_x_m, case.eye_y_m, case.eye_z_m, case.wavelength_m,
    )
    if not all(math.isfinite(v) for v in values):
        raise ValueError("all steering case values must be finite")
    if case.eye_z_m <= 0.0 or case.wavelength_m <= 0.0:
        raise ValueError("eye_z_m and wavelength_m must be positive")
    theta_x = math.atan2(case.eye_x_m, math.hypot(case.eye_y_m, case.eye_z_m))
    theta_y = math.atan2(case.eye_y_m, math.hypot(case.eye_x_m, case.eye_z_m))
    k = 2.0 * math.pi / case.wavelength_m
    tilt = k * (case.sample_x_m * math.sin(theta_x) + case.sample_y_m * math.sin(theta_y))
    curvature = (k / (2.0 * case.eye_z_m)) * (
        case.sample_x_m * case.sample_x_m + case.sample_y_m * case.sample_y_m
    )
    total = case.base_phase_radians + tilt + curvature
    return math.atan2(math.sin(total), math.cos(total))


def default_asm_grid() -> tuple[ASMConformanceCase, ...]:
    wavelength = 532e-9
    cutoff = 1.0 / wavelength
    return (
        ASMConformanceCase(0.0, 0.0, 0.03, wavelength),
        ASMConformanceCase(1_000.0, 2_000.0, 0.03, wavelength),
        ASMConformanceCase(100_000.0, -50_000.0, 0.06, wavelength),
        ASMConformanceCase(0.5 * cutoff, 0.0, 0.02, wavelength),
        ASMConformanceCase(0.7 * cutoff, 0.7 * cutoff, 0.04, wavelength),
        ASMConformanceCase(1.01 * cutoff, 0.0, 0.03, wavelength),
        ASMConformanceCase(0.8 * cutoff, 0.8 * cutoff, 0.03, wavelength),
    )


def default_steering_grid() -> tuple[SteeringConformanceCase, ...]:
    wavelength = 532e-9
    return tuple(
        SteeringConformanceCase(base, sx, sy, ex, ey, ez, wavelength)
        for base, sx, sy, ex, ey, ez in (
            (0.0, 0.0, 0.0, 0.0, 0.0, 0.35),
            (0.1, 1e-4, -2e-4, 0.02, 0.005, 0.35),
            (-0.4, -3e-4, 1e-4, -0.03, 0.01, 0.30),
            (1.2, 4e-4, 5e-4, 0.04, -0.015, 0.40),
            (-2.0, -5e-4, -4e-4, -0.02, -0.02, 0.25),
        )
    )


def run_independent_conformance(
    *,
    asm_cases: Sequence[ASMConformanceCase] | None = None,
    steering_cases: Sequence[SteeringConformanceCase] | None = None,
    complex_tolerance: float = COMPLEX_TOLERANCE,
    phase_tolerance_radians: float = PHASE_TOLERANCE_RADIANS,
) -> tuple[ConformanceFinding, ...]:
    if (
        isinstance(complex_tolerance, bool)
        or isinstance(phase_tolerance_radians, bool)
        or complex_tolerance <= 0.0
        or phase_tolerance_radians <= 0.0
    ):
        raise ValueError("tolerances must be positive real values")
    asm_cases = tuple(default_asm_grid() if asm_cases is None else asm_cases)
    steering_cases = tuple(default_steering_grid() if steering_cases is None else steering_cases)
    findings: list[ConformanceFinding] = []
    for index, case in enumerate(asm_cases):
        a = imported.angular_spectrum_transfer(
            fx_cycles_per_m=case.fx_cycles_per_m,
            fy_cycles_per_m=case.fy_cycles_per_m,
            z_m=case.z_m,
            wavelength_m=case.wavelength_m,
        )
        b_transfer, b_propagating = independent_asm_transfer(case)
        class_agreement = a.propagating == b_propagating
        numeric_error = abs(a.transfer - b_transfer)
        findings.append(ConformanceFinding(
            "ASM", index, class_agreement, numeric_error,
            class_agreement and numeric_error <= complex_tolerance,
        ))
    for index, case in enumerate(steering_cases):
        a = imported.phase_steering_sample(
            base_phase_radians=case.base_phase_radians,
            sample_x_m=case.sample_x_m,
            sample_y_m=case.sample_y_m,
            eye_x_m=case.eye_x_m,
            eye_y_m=case.eye_y_m,
            eye_z_m=case.eye_z_m,
            wavelength_m=case.wavelength_m,
        )
        b = independent_phase_steering(case)
        error = circular_phase_error(a.phase_radians, b)
        findings.append(ConformanceFinding(
            "STEERING", index, True, error, error <= phase_tolerance_radians
        ))
    return tuple(findings)


def _canonical_receipt_payload() -> dict[str, object]:
    findings = run_independent_conformance()
    return {
        "schema": SCHEMA,
        "producer_schema": "AURA_K27_OPTICS_CANONICAL_CONFORMANCE_PRODUCER_V1",
        "parent_artifact_ids": CANONICAL_PARENT_ARTIFACT_IDS,
        "imported_source_sha256": IMPORTED_SOURCE_SHA256,
        "matrix_identity": {
            "asm_cases": [asdict(case) for case in default_asm_grid()],
            "steering_cases": [asdict(case) for case in default_steering_grid()],
            "complex_tolerance": COMPLEX_TOLERANCE,
            "phase_tolerance_radians": PHASE_TOLERANCE_RADIANS,
        },
        "findings": [asdict(f) for f in findings],
        "software_independent_conformance_pass": bool(findings) and all(f.within_tolerance for f in findings),
        "caller_findings_accepted": False,
        "caller_source_sha_accepted": False,
        "caller_parent_ids_accepted": False,
        "claim_ceiling": dict(CLAIM_CEILING),
    }


def build_conformance_receipt() -> Mapping[str, object]:
    """Run the canonical producer and seal its exact consequence.

    Deliberately zero-argument: callers cannot provide findings/source/parents.
    """
    payload = _canonical_receipt_payload()
    return {
        **payload,
        "receipt_sha256": hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest(),
    }


def verify_conformance_receipt(receipt: Mapping[str, object]) -> bool:
    """Re-run the canonical producer; hash-valid caller semantics are insufficient."""
    if not isinstance(receipt, Mapping):
        return False
    try:
        expected = build_conformance_receipt()
    except (TypeError, ValueError):
        return False
    return dict(receipt) == dict(expected)

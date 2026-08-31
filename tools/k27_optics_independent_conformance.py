"""Independent numerical conformance for the imported K27 optics proposal.

This module applies the ASTGE independent-oracle lesson to two bounded optics
relations already retained by Aura as software references:

1. band-limited angular-spectrum transfer;
2. paraxial pupil/exit-pupil phase steering.

Agreement between two formulations raises software semantic confidence only.
It does not prove physical optics, display performance, image quality, safety,
or deployment readiness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import cmath
import hashlib
import json
import math
from typing import Mapping, Sequence

import k27_optics_candidate_falsifier as imported


SCHEMA = "AURA_K27_OPTICS_INDEPENDENT_CONFORMANCE_V1"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def circular_phase_error(a: float, b: float) -> float:
    """Smallest absolute phase difference on the circle."""
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
    """Independent k-vector formulation of the ASM transfer sample.

    Unlike the imported reference's dimensionless lambda*f radial expression,
    this computes physical wave-vector components first:
      k=2pi/lambda, kx=2pi*fx, ky=2pi*fy, kz^2=k^2-kx^2-ky^2.
    """
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
    kz = math.sqrt(max(0.0, kz_sq))
    return cmath.exp(1j * kz * case.z_m), True


def independent_phase_steering(case: SteeringConformanceCase) -> float:
    """Angle-based equivalent of the imported direction-cosine steering model.

    Direction cosines are reconstructed via orthogonal atan2 angles rather than
    direct division by the 3-D norm. Wrapping uses atan2(sin,cos), independently
    from the imported modulo implementation.
    """
    values = (
        case.base_phase_radians,
        case.sample_x_m,
        case.sample_y_m,
        case.eye_x_m,
        case.eye_y_m,
        case.eye_z_m,
        case.wavelength_m,
    )
    if not all(math.isfinite(v) for v in values):
        raise ValueError("all steering case values must be finite")
    if case.eye_z_m <= 0.0 or case.wavelength_m <= 0.0:
        raise ValueError("eye_z_m and wavelength_m must be positive")

    theta_x = math.atan2(case.eye_x_m, math.hypot(case.eye_y_m, case.eye_z_m))
    theta_y = math.atan2(case.eye_y_m, math.hypot(case.eye_x_m, case.eye_z_m))
    sin_x = math.sin(theta_x)
    sin_y = math.sin(theta_y)
    k = 2.0 * math.pi / case.wavelength_m
    tilt = k * (case.sample_x_m * sin_x + case.sample_y_m * sin_y)
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
        SteeringConformanceCase(
            base_phase_radians=base,
            sample_x_m=sx,
            sample_y_m=sy,
            eye_x_m=ex,
            eye_y_m=ey,
            eye_z_m=ez,
            wavelength_m=wavelength,
        )
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
    complex_tolerance: float = 1e-9,
    phase_tolerance_radians: float = 1e-9,
) -> tuple[ConformanceFinding, ...]:
    if complex_tolerance <= 0.0 or phase_tolerance_radians <= 0.0:
        raise ValueError("tolerances must be positive")
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
        findings.append(
            ConformanceFinding(
                domain="ASM",
                case_index=index,
                class_agreement=class_agreement,
                numeric_error=numeric_error,
                within_tolerance=class_agreement and numeric_error <= complex_tolerance,
            )
        )

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
        b_phase = independent_phase_steering(case)
        error = circular_phase_error(a.phase_radians, b_phase)
        findings.append(
            ConformanceFinding(
                domain="STEERING",
                case_index=index,
                class_agreement=True,
                numeric_error=error,
                within_tolerance=error <= phase_tolerance_radians,
            )
        )
    return tuple(findings)


def build_conformance_receipt(
    *,
    parent_artifact_ids: Sequence[str],
    imported_source_sha256: str,
    findings: Sequence[ConformanceFinding],
) -> Mapping[str, object]:
    parents = tuple(parent_artifact_ids)
    if len(parents) != 2 or len(set(parents)) != 2 or any(not p for p in parents):
        raise ValueError("exactly two distinct non-empty parent artifact IDs are required")
    if not isinstance(imported_source_sha256, str) or len(imported_source_sha256) != 64:
        raise ValueError("imported_source_sha256 must be a SHA-256 digest")
    try:
        int(imported_source_sha256, 16)
    except ValueError as exc:
        raise ValueError("imported_source_sha256 must be hexadecimal") from exc

    closed = bool(findings) and all(f.within_tolerance for f in findings)
    payload = {
        "schema": SCHEMA,
        "parent_artifact_ids": parents,
        "imported_source_sha256": imported_source_sha256.lower(),
        "findings": [asdict(f) for f in findings],
        "software_independent_conformance_pass": closed,
        "claim_ceiling": {
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
        },
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "receipt_sha256": digest}


def verify_conformance_receipt(receipt: Mapping[str, object]) -> bool:
    expected = {
        "schema",
        "parent_artifact_ids",
        "imported_source_sha256",
        "findings",
        "software_independent_conformance_pass",
        "claim_ceiling",
        "receipt_sha256",
    }
    if set(receipt) != expected or receipt.get("schema") != SCHEMA:
        return False
    ceiling = receipt.get("claim_ceiling")
    if not isinstance(ceiling, dict) or not ceiling or any(v is not False for v in ceiling.values()):
        return False
    payload = {k: receipt[k] for k in expected if k != "receipt_sha256"}
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return receipt.get("receipt_sha256") == digest

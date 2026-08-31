"""Bounded falsifier/reference membrane for the imported K27 spatial-display proposal.

This module deliberately does not implement a production holographic display.
It provides:
- exact current K27 ternary coordinate arithmetic;
- a scalar reference for the phase-prism/curvature steering approximation;
- a scalar angular-spectrum transfer-function reference;
- a closed, source-bound receipt that preserves unsupported claims as false.

No external package is required so the contract can be re-proved in minimal CI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import cmath
import hashlib
import json
import math
from typing import Mapping, Sequence


RECEIPT_SCHEMA = "AURA_K27_OPTICS_IMPORTED_CANDIDATE_FALSIFIER_V1"
K27_SCHEME = "K27-B3MOD27-XYZ-v1"
PHASE_STEERING_MODEL = "PARAXIAL_PHASE_TILT_PLUS_QUADRATIC_CURVATURE_APPROX_V1"


def _strict_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, not bool or another scalar type")
    return value


def k27_cell(x: int, y: int, z: int) -> int:
    """Return the exact 27-cell ternary address 9*x + 3*y + z."""
    x = _strict_int("x", x)
    y = _strict_int("y", y)
    z = _strict_int("z", z)
    for name, value in (("x", x), ("y", y), ("z", z)):
        if value not in (0, 1, 2):
            raise ValueError(f"{name} must be ternary: 0, 1, or 2")
    return 9 * x + 3 * y + z


def imported_packed_coordinate(wavelength: int, depth_tier: int, invariant_rule: int) -> int:
    """Reproduce the proposal's enum-shift packing for falsification only.

    The imported draft uses enums 1..3 shifted into a 64-bit integer. This is
    not the current K27 ternary address law and therefore cannot be admitted as
    a K27 cell without an explicit adapter.
    """
    for name, value in (
        ("wavelength", wavelength),
        ("depth_tier", depth_tier),
        ("invariant_rule", invariant_rule),
    ):
        value = _strict_int(name, value)
        if value not in (1, 2, 3):
            raise ValueError(f"{name} must be one of the imported enum values 1..3")
    return (wavelength << 32) | (depth_tier << 16) | invariant_rule


def wrap_phase_radians(value: float) -> float:
    """Wrap phase to [-pi, pi)."""
    if not math.isfinite(value):
        raise ValueError("phase must be finite")
    return (value + math.pi) % (2.0 * math.pi) - math.pi


@dataclass(frozen=True)
class SteeringSample:
    phase_radians: float
    model: str = PHASE_STEERING_MODEL
    exact_scene_unbinding_proven: bool = False
    varifocal_correctness_proven: bool = False
    hardware_latency_proven: bool = False


def phase_steering_sample(
    *,
    base_phase_radians: float,
    sample_x_m: float,
    sample_y_m: float,
    eye_x_m: float,
    eye_y_m: float,
    eye_z_m: float,
    wavelength_m: float,
) -> SteeringSample:
    """Evaluate the imported prism + quadratic-curvature formula at one sample.

    This is a paraxial steering approximation. It is not a proof that a full
    holographic scene has been exactly "unbound", that accommodation is correct,
    or that a physical display reaches any latency target.
    """
    values = (
        base_phase_radians,
        sample_x_m,
        sample_y_m,
        eye_x_m,
        eye_y_m,
        eye_z_m,
        wavelength_m,
    )
    if not all(math.isfinite(v) for v in values):
        raise ValueError("all steering inputs must be finite")
    if eye_z_m <= 0.0:
        raise ValueError("eye_z_m must be positive")
    if wavelength_m <= 0.0:
        raise ValueError("wavelength_m must be positive")

    distance = math.sqrt(eye_x_m**2 + eye_y_m**2 + eye_z_m**2)
    sin_theta_x = eye_x_m / distance
    sin_theta_y = eye_y_m / distance
    k = 2.0 * math.pi / wavelength_m
    tilt = k * (sample_x_m * sin_theta_x + sample_y_m * sin_theta_y)
    curvature = (k / (2.0 * eye_z_m)) * (sample_x_m**2 + sample_y_m**2)
    return SteeringSample(wrap_phase_radians(base_phase_radians + tilt + curvature))


@dataclass(frozen=True)
class AngularSpectrumSample:
    transfer: complex
    propagating: bool
    transfer_magnitude: float
    energy_conservation_proven: bool = False
    speckle_free_proven: bool = False


def angular_spectrum_transfer(
    *,
    fx_cycles_per_m: float,
    fy_cycles_per_m: float,
    z_m: float,
    wavelength_m: float,
) -> AngularSpectrumSample:
    """Reference one spatial-frequency transfer sample.

    Propagating modes use H=exp(i*k*z*sqrt(1-(lambda fx)^2-(lambda fy)^2)).
    Evanescent modes are explicitly band-limited to zero, matching the imported
    proposal's mask. A unit-magnitude propagating transfer function does not by
    itself prove system-level energy conservation or speckle suppression.
    """
    values = (fx_cycles_per_m, fy_cycles_per_m, z_m, wavelength_m)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("all ASM inputs must be finite")
    if wavelength_m <= 0.0:
        raise ValueError("wavelength_m must be positive")

    radial = (wavelength_m * fx_cycles_per_m) ** 2 + (
        wavelength_m * fy_cycles_per_m
    ) ** 2
    if radial > 1.0:
        return AngularSpectrumSample(0j, False, 0.0)

    k = 2.0 * math.pi / wavelength_m
    kz = k * math.sqrt(max(0.0, 1.0 - radial))
    transfer = cmath.exp(1j * kz * z_m)
    return AngularSpectrumSample(transfer, True, abs(transfer))


@dataclass(frozen=True)
class ClaimFinding:
    key: str
    admitted: bool
    reason: str


def imported_candidate_findings() -> tuple[ClaimFinding, ...]:
    """Return consequence-changing findings earned by this membrane."""
    return (
        ClaimFinding(
            "IMPORTED_SHIFT_PACKING_IS_CURRENT_K27",
            False,
            "Imported 1..3 enum bit-shifts are not K27 ternary 9X+3Y+Z.",
        ),
        ClaimFinding(
            "UNIT_MAGNITUDE_ASM_OR_STRING_ASSERTION_PROVES_SYSTEM_ENERGY_CONSERVATION",
            False,
            "A transfer sample or serialized invariant label is not a measured system invariant.",
        ),
        ClaimFinding(
            "ENERGY_CONSERVATION_PREVENTS_COHERENT_SPECKLE",
            False,
            "Speckle is a coherent-interference image-quality problem requiring independent mitigation/measurement.",
        ),
        ClaimFinding(
            "PHASE_TILT_PLUS_CURVATURE_IS_EXACT_SCENE_UNBINDING",
            False,
            "The formula is retained only as a bounded paraxial steering approximation.",
        ),
        ClaimFinding(
            "MONOCULAR_ASSUMED_IPD_DEPTH_IS_METRIC_EYE_POSE",
            False,
            "Metric eye pose requires calibration/measurement; assumed IPD plus image landmarks is an estimate.",
        ),
        ClaimFinding(
            "ZERO_FORWARD_LIGHT_LEAKAGE_OR_100_PERCENT_PRIVATE_OVERLAY_PROVEN",
            False,
            "No optical leakage measurement or physical prototype receipt is present.",
        ),
        ClaimFinding(
            "DISPLAY_DEPLOYMENT_READY",
            False,
            "Simulation/reference code is not a hardware integration, safety, latency, or image-quality qualification.",
        ),
    )


NEGATIVE_CEILING = {
    "semantic_k27_authority": False,
    "native_transformer_kv_accessed": False,
    "optical_energy_conservation_proven": False,
    "speckle_free_proven": False,
    "zero_light_leakage_proven": False,
    "metric_eye_pose_proven": False,
    "exact_scene_unbinding_proven": False,
    "varifocal_correctness_proven": False,
    "hardware_latency_proven": False,
    "display_safety_proven": False,
    "deployment_ready": False,
    "effect_authority": False,
    "gate10_promoted": False,
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_import_receipt(
    *,
    imported_source_sha256: str,
    external_evidence_refs: Sequence[str] = (),
) -> Mapping[str, object]:
    """Build a deterministic evidence-only receipt.

    external_evidence_refs are navigation/provenance strings only. They do not
    alter the negative ceiling or mint optical/K27 authority.
    """
    if len(imported_source_sha256) != 64:
        raise ValueError("imported_source_sha256 must be a 64-character hex digest")
    try:
        int(imported_source_sha256, 16)
    except ValueError as exc:
        raise ValueError("imported_source_sha256 must be hexadecimal") from exc

    refs = tuple(sorted(set(str(ref) for ref in external_evidence_refs)))
    payload = {
        "schema": RECEIPT_SCHEMA,
        "k27_scheme": K27_SCHEME,
        "imported_source_sha256": imported_source_sha256.lower(),
        "external_evidence_refs": refs,
        "findings": [asdict(finding) for finding in imported_candidate_findings()],
        "claim_ceiling": dict(sorted(NEGATIVE_CEILING.items())),
        "retained_mechanics": [
            "bandlimited_angular_spectrum_reference",
            "pupil_or_exit_pupil_steering_as_candidate_mechanism",
            "phase_tilt_plus_quadratic_curvature_as_approximation",
            "eye_tracking_as_external_observation_input",
            "k27_as_lookup_currentness_reopen_metadata_only",
        ],
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "receipt_sha256": digest}


def verify_import_receipt(receipt: Mapping[str, object]) -> bool:
    """Fail closed unless the closed receipt is byte-consequence consistent."""
    expected_keys = {
        "schema",
        "k27_scheme",
        "imported_source_sha256",
        "external_evidence_refs",
        "findings",
        "claim_ceiling",
        "retained_mechanics",
        "receipt_sha256",
    }
    if set(receipt) != expected_keys:
        return False
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("k27_scheme") != K27_SCHEME:
        return False
    ceiling = receipt.get("claim_ceiling")
    if ceiling != dict(sorted(NEGATIVE_CEILING.items())):
        return False
    findings = receipt.get("findings")
    if findings != [asdict(finding) for finding in imported_candidate_findings()]:
        return False
    payload = {key: receipt[key] for key in expected_keys if key != "receipt_sha256"}
    expected_digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return receipt.get("receipt_sha256") == expected_digest

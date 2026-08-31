#!/usr/bin/env python3
"""Measured optical invariants for Aura spatial/holographic candidate work.

The witness names the implemented propagator honestly (angular spectrum),
measures power and roundtrip field error, and separates a phase-only projection
from full complex-field propagation. It does not infer speckle elimination,
physical-device fidelity, or authority from a metadata string.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SCHEMA = "AURA_SPATIAL_OPTICAL_INVARIANT_WITNESS_V1"
PROPAGATOR = "ANGULAR_SPECTRUM_PROPAGATING_BAND_ONLY_V1"


class OpticalContractError(ValueError):
    pass


def optical_power(field: np.ndarray) -> float:
    field = np.asarray(field, dtype=np.complex128)
    if field.ndim != 2 or field.size == 0:
        raise OpticalContractError("field:NONEMPTY_2D_REQUIRED")
    return float(np.sum(np.abs(field) ** 2, dtype=np.float64))


def normalized_field_error(observed: np.ndarray, expected: np.ndarray) -> float:
    observed = np.asarray(observed, dtype=np.complex128)
    expected = np.asarray(expected, dtype=np.complex128)
    if observed.shape != expected.shape or expected.size == 0:
        raise OpticalContractError("field:SHAPE_MISMATCH")
    denom = float(np.linalg.norm(expected))
    if denom == 0.0:
        raise OpticalContractError("field:ZERO_REFERENCE_NORM")
    return float(np.linalg.norm(observed - expected) / denom)


def speckle_contrast(field: np.ndarray) -> float:
    intensity = np.abs(np.asarray(field, dtype=np.complex128)) ** 2
    mean = float(np.mean(intensity))
    if mean <= 0.0:
        raise OpticalContractError("field:NONPOSITIVE_MEAN_INTENSITY")
    return float(np.std(intensity) / mean)


def angular_spectrum_propagate(
    field: np.ndarray,
    *,
    dx_m: float,
    dy_m: float,
    wavelength_m: float,
    distance_m: float,
) -> np.ndarray:
    """Discrete unitary angular-spectrum propagation for propagating modes.

    Evanescent modes are explicitly rejected by zeroing their transfer terms;
    the receipt therefore reports the retained spectral fraction. A power-
    conservation claim is admissible only when the input has negligible energy
    outside the propagating band for the chosen sampling.
    """
    field = np.asarray(field, dtype=np.complex128)
    if field.ndim != 2 or field.size == 0:
        raise OpticalContractError("field:NONEMPTY_2D_REQUIRED")
    for name, value in (("dx_m", dx_m), ("dy_m", dy_m), ("wavelength_m", wavelength_m)):
        if not np.isfinite(value) or value <= 0.0:
            raise OpticalContractError(f"{name}:POSITIVE_FINITE_REQUIRED")
    if not np.isfinite(distance_m):
        raise OpticalContractError("distance_m:FINITE_REQUIRED")

    ny, nx = field.shape
    fx = np.fft.fftfreq(nx, d=dx_m)
    fy = np.fft.fftfreq(ny, d=dy_m)
    fxx, fyy = np.meshgrid(fx, fy)
    radicand = 1.0 - (wavelength_m * fxx) ** 2 - (wavelength_m * fyy) ** 2
    propagating = radicand >= 0.0
    transfer = np.zeros(field.shape, dtype=np.complex128)
    k = 2.0 * np.pi / wavelength_m
    transfer[propagating] = np.exp(
        1j * k * distance_m * np.sqrt(radicand[propagating])
    )
    spectrum = np.fft.fft2(field, norm="ortho")
    return np.fft.ifft2(spectrum * transfer, norm="ortho")


def propagating_spectral_power_fraction(
    field: np.ndarray,
    *,
    dx_m: float,
    dy_m: float,
    wavelength_m: float,
) -> float:
    field = np.asarray(field, dtype=np.complex128)
    ny, nx = field.shape
    fx = np.fft.fftfreq(nx, d=dx_m)
    fy = np.fft.fftfreq(ny, d=dy_m)
    fxx, fyy = np.meshgrid(fx, fy)
    mask = 1.0 - (wavelength_m * fxx) ** 2 - (wavelength_m * fyy) ** 2 >= 0.0
    spectrum = np.fft.fft2(field, norm="ortho")
    spectral_power = np.abs(spectrum) ** 2
    total = float(np.sum(spectral_power))
    if total == 0.0:
        raise OpticalContractError("field:ZERO_SPECTRAL_POWER")
    return float(np.sum(spectral_power[mask]) / total)


def phase_only_projection(field: np.ndarray, *, preserve_total_power: bool = True) -> np.ndarray:
    field = np.asarray(field, dtype=np.complex128)
    if field.ndim != 2 or field.size == 0:
        raise OpticalContractError("field:NONEMPTY_2D_REQUIRED")
    amplitude = 1.0
    if preserve_total_power:
        amplitude = np.sqrt(optical_power(field) / field.size)
    return amplitude * np.exp(1j * np.angle(field))


def validate_codec_filename(path: str | Path, codec: str) -> None:
    """Reject extension/codec cross-casts from imported spatial drafts."""
    suffix = Path(path).suffix.casefold()
    codec = codec.casefold()
    expected = {"zlib": ".zlib", "zstd": ".zst", "gzip": ".gz"}
    if codec not in expected:
        raise OpticalContractError("codec:UNSUPPORTED")
    if suffix != expected[codec]:
        raise OpticalContractError("codec:EXTENSION_MISMATCH")


@dataclass(frozen=True)
class OpticalInvariantReceiptV1:
    schema: str
    propagator: str
    shape: tuple[int, int]
    dx_m: float
    dy_m: float
    wavelength_m: float
    distance_m: float
    propagating_spectral_power_fraction: float
    forward_power_relative_residual: float
    full_field_roundtrip_nrmse: float
    phase_only_power_relative_residual: float
    phase_only_roundtrip_nrmse: float
    phase_only_reconstruction_speckle_contrast: float
    power_conservation_measured: bool
    full_field_roundtrip_measured: bool
    phase_only_power_matched: bool
    phase_only_full_field_fidelity_proven: bool
    speckle_elimination_proven: bool
    rayleigh_sommerfeld_implementation_proven: bool
    physical_display_fidelity_proven: bool
    semantic_k27_authority: bool
    native_transformer_kv_accessed: bool
    receipt_sha256: str = ""


def measure_invariants(
    field: np.ndarray,
    *,
    dx_m: float,
    dy_m: float,
    wavelength_m: float,
    distance_m: float,
    power_tolerance: float = 1e-10,
    roundtrip_tolerance: float = 1e-10,
) -> OpticalInvariantReceiptV1:
    source = np.asarray(field, dtype=np.complex128)
    retained = propagating_spectral_power_fraction(
        source, dx_m=dx_m, dy_m=dy_m, wavelength_m=wavelength_m
    )
    forward = angular_spectrum_propagate(
        source,
        dx_m=dx_m,
        dy_m=dy_m,
        wavelength_m=wavelength_m,
        distance_m=distance_m,
    )
    backward = angular_spectrum_propagate(
        forward,
        dx_m=dx_m,
        dy_m=dy_m,
        wavelength_m=wavelength_m,
        distance_m=-distance_m,
    )
    p0 = optical_power(source)
    p1 = optical_power(forward)
    forward_residual = abs(p1 - p0) / p0
    full_error = normalized_field_error(backward, source)

    phase_only = phase_only_projection(forward, preserve_total_power=True)
    p_phase = optical_power(phase_only)
    phase_power_residual = abs(p_phase - p1) / p1
    phase_back = angular_spectrum_propagate(
        phase_only,
        dx_m=dx_m,
        dy_m=dy_m,
        wavelength_m=wavelength_m,
        distance_m=-distance_m,
    )
    phase_error = normalized_field_error(phase_back, source)
    contrast = speckle_contrast(phase_back)

    measured_power = retained >= 1.0 - 1e-12 and forward_residual <= power_tolerance
    measured_roundtrip = retained >= 1.0 - 1e-12 and full_error <= roundtrip_tolerance
    phase_power_matched = phase_power_residual <= power_tolerance

    unsigned = OpticalInvariantReceiptV1(
        schema=SCHEMA,
        propagator=PROPAGATOR,
        shape=tuple(int(v) for v in source.shape),
        dx_m=dx_m,
        dy_m=dy_m,
        wavelength_m=wavelength_m,
        distance_m=distance_m,
        propagating_spectral_power_fraction=retained,
        forward_power_relative_residual=forward_residual,
        full_field_roundtrip_nrmse=full_error,
        phase_only_power_relative_residual=phase_power_residual,
        phase_only_roundtrip_nrmse=phase_error,
        phase_only_reconstruction_speckle_contrast=contrast,
        power_conservation_measured=measured_power,
        full_field_roundtrip_measured=measured_roundtrip,
        phase_only_power_matched=phase_power_matched,
        phase_only_full_field_fidelity_proven=False,
        speckle_elimination_proven=False,
        rayleigh_sommerfeld_implementation_proven=False,
        physical_display_fidelity_proven=False,
        semantic_k27_authority=False,
        native_transformer_kv_accessed=False,
    )
    raw = json.dumps(asdict(unsigned), sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    return OpticalInvariantReceiptV1(**{**asdict(unsigned), "receipt_sha256": digest})


def deterministic_fixture(size: int = 64) -> np.ndarray:
    if size < 16:
        raise OpticalContractError("fixture:SIZE_TOO_SMALL")
    y, x = np.mgrid[-1:1:complex(size), -1:1:complex(size)]
    amplitude = (
        0.2
        + np.exp(-4.0 * (x * x + y * y))
        + 0.3 * np.exp(-20.0 * ((x - 0.3) ** 2 + (y + 0.2) ** 2))
    )
    phase = 0.7 * x + 1.1 * y + 0.5 * x * y
    return amplitude * np.exp(1j * phase)


if __name__ == "__main__":
    receipt = measure_invariants(
        deterministic_fixture(),
        dx_m=8e-6,
        dy_m=8e-6,
        wavelength_m=532e-9,
        distance_m=0.03,
    )
    print(json.dumps(asdict(receipt), indent=2, sort_keys=True))

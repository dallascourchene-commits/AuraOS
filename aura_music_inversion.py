"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c8-[Q-SYS:MUSIC_INVERSION]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Bounded Subspace Search)
DEPENDENCIES: dataclasses, math, numpy, typing
FUNCTIONS: MusicPeak, MusicComponentPeak, MusicSpectrumResult, MusicComponentResult,
build_hankel_snapshots, music_frequency_search, music_component_search, dominant_music_angle
SYNOPSIS: Edge-bounded MUSIC-style inversion for Aura waves. High-dimensional
inputs are converted to small projected snapshots before covariance/SVD; the
10,000-D path never enters eigendecomposition.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class MusicPeak:
    index: int
    angle: float
    frequency: float
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MusicComponentPeak:
    key: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MusicSpectrumResult:
    peaks: list[MusicPeak]
    spectrum: np.ndarray
    scan_angles: np.ndarray
    singular_values: list[float]
    covariance_shape: tuple[int, int]
    projected_snapshot_shape: tuple[int, int]
    source_dimension: int
    snapshot_count: int
    signal_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "peaks": [peak.to_dict() for peak in self.peaks],
            "singular_values": self.singular_values,
            "covariance_shape": self.covariance_shape,
            "projected_snapshot_shape": self.projected_snapshot_shape,
            "source_dimension": self.source_dimension,
            "snapshot_count": self.snapshot_count,
            "signal_count": self.signal_count,
        }


@dataclass(frozen=True)
class MusicComponentResult:
    peaks: list[MusicComponentPeak]
    scores: dict[str, float]
    singular_values: list[float]
    covariance_shape: tuple[int, int]
    projected_snapshot_shape: tuple[int, int]
    source_dimension: int
    snapshot_count: int
    signal_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "peaks": [peak.to_dict() for peak in self.peaks],
            "scores": self.scores,
            "singular_values": self.singular_values,
            "covariance_shape": self.covariance_shape,
            "projected_snapshot_shape": self.projected_snapshot_shape,
            "source_dimension": self.source_dimension,
            "snapshot_count": self.snapshot_count,
            "signal_count": self.signal_count,
        }


def build_hankel_snapshots(
    samples: np.ndarray,
    *,
    window_length: int,
    max_snapshots: int = 512,
) -> np.ndarray:
    """Build bounded sliding-window snapshots from a 1D signal."""
    signal = np.asarray(samples, dtype=np.complex64).reshape(-1)
    if signal.size < 4:
        raise ValueError("MUSIC frequency search requires at least four samples")
    window = int(max(2, min(window_length, signal.size - 1)))
    available = signal.size - window + 1
    count = int(max(1, min(available, max_snapshots)))
    starts = np.unique(np.linspace(0, available - 1, count, dtype=np.int64))
    snapshots = np.empty((window, len(starts)), dtype=np.complex64)
    for col, start in enumerate(starts):
        snapshots[:, col] = signal[start:start + window]
    return snapshots


def _projection_plan(source_dimension: int, projection_dim: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    idx = np.arange(source_dimension, dtype=np.uint64)
    hashed = (idx * np.uint64(11400714819323198485) + np.uint64(seed)) & np.uint64(0xFFFF_FFFF_FFFF_FFFF)
    buckets = (hashed % np.uint64(projection_dim)).astype(np.intp)
    signs = np.where(((hashed >> np.uint64(33)) & np.uint64(1)) == 0, 1.0, -1.0).astype(np.float32)
    signs /= np.float32(math.sqrt(max(1.0, source_dimension / float(projection_dim))))
    return buckets, signs


def _project_snapshots(
    snapshots: np.ndarray,
    *,
    projection_dim: int,
    seed: int = 1729,
) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray] | None, int]:
    matrix = np.asarray(snapshots, dtype=np.complex64)
    if matrix.ndim != 2:
        raise ValueError("snapshots must be a 2D matrix shaped (dimension, snapshot_count)")
    source_dimension = int(matrix.shape[0])
    if source_dimension <= projection_dim:
        return matrix, None, source_dimension
    buckets, signs = _projection_plan(source_dimension, projection_dim, seed)
    projected = np.zeros((projection_dim, matrix.shape[1]), dtype=np.complex64)
    np.add.at(projected, buckets, signs[:, None] * matrix)
    return projected, (buckets, signs), source_dimension


def _project_component(
    vector: np.ndarray,
    *,
    projection_plan: tuple[np.ndarray, np.ndarray] | None,
    projection_dim: int,
) -> np.ndarray:
    component = np.asarray(vector, dtype=np.complex64).reshape(-1)
    if projection_plan is None:
        if component.size != projection_dim:
            raise ValueError("component dimension does not match snapshot dimension")
        return component
    buckets, signs = projection_plan
    if component.size != len(buckets):
        raise ValueError("component dimension does not match original snapshot dimension")
    projected = np.zeros(projection_dim, dtype=np.complex64)
    np.add.at(projected, buckets, signs * component)
    return projected


def _limit_snapshot_count(snapshots: np.ndarray, max_snapshots: int) -> np.ndarray:
    if snapshots.shape[1] <= max_snapshots:
        return snapshots
    cols = np.unique(np.linspace(0, snapshots.shape[1] - 1, max_snapshots, dtype=np.int64))
    return snapshots[:, cols]


def _covariance_svd(
    snapshots: np.ndarray,
    *,
    signal_count: int | None,
    diagonal_loading: float,
) -> tuple[np.ndarray, list[float], int]:
    if snapshots.ndim != 2 or snapshots.shape[1] == 0:
        raise ValueError("MUSIC requires at least one snapshot column")
    covariance = (snapshots @ snapshots.conj().T) / np.float32(max(1, snapshots.shape[1]))
    if diagonal_loading > 0:
        scale = float(np.trace(covariance).real / max(1, covariance.shape[0]))
        covariance = covariance + np.eye(covariance.shape[0], dtype=np.complex64) * np.float32(diagonal_loading * max(scale, 1e-12))
    u, s, _ = np.linalg.svd(covariance.astype(np.complex64), full_matrices=True)
    if signal_count is None:
        floor = max(float(s[0]) * 0.05, 1e-8) if len(s) else 1e-8
        estimated = int(np.sum(s > floor))
        signal_count = max(1, min(estimated, max(1, covariance.shape[0] - 1)))
    signal_count = int(max(1, min(signal_count, max(1, covariance.shape[0] - 1))))
    return u[:, signal_count:], [float(item) for item in s], signal_count


def _pseudospectrum_from_noise(noise_subspace: np.ndarray, steering: np.ndarray, epsilon: float) -> np.ndarray:
    steering_norm = steering / np.maximum(np.linalg.norm(steering, axis=0, keepdims=True), epsilon)
    projection = noise_subspace.conj().T @ steering_norm
    denom = np.sum(np.abs(projection) ** 2, axis=0)
    return (1.0 / np.maximum(denom, epsilon)).astype(np.float32)


def _select_peaks(
    spectrum: np.ndarray,
    angles: np.ndarray,
    *,
    top_k: int,
    min_peak_distance: int,
) -> list[MusicPeak]:
    if spectrum.size == 0:
        return []
    left = np.roll(spectrum, 1)
    right = np.roll(spectrum, -1)
    local = np.where((spectrum >= left) & (spectrum >= right))[0]
    candidates = local if local.size else np.argsort(spectrum)[::-1]
    ordered = sorted((int(idx) for idx in candidates), key=lambda idx: float(spectrum[idx]), reverse=True)
    chosen: list[int] = []
    for idx in ordered:
        if all(min(abs(idx - prev), spectrum.size - abs(idx - prev)) >= min_peak_distance for prev in chosen):
            chosen.append(idx)
        if len(chosen) >= top_k:
            break
    if not chosen:
        chosen = [int(np.argmax(spectrum))]
    return [
        MusicPeak(
            index=idx,
            angle=float(angles[idx]),
            frequency=float((angles[idx] % (2 * np.pi)) / (2 * np.pi)),
            score=float(spectrum[idx]),
        )
        for idx in chosen[:top_k]
    ]


def music_frequency_search(
    samples: np.ndarray,
    *,
    sample_resolution: int = 512,
    signal_count: int | None = None,
    top_k: int = 3,
    window_length: int | None = None,
    max_subspace_dim: int = 64,
    max_snapshots: int = 512,
    frequency_range: tuple[float, float] = (0.0, 2 * np.pi),
    min_peak_distance: int | None = None,
    diagonal_loading: float = 1e-6,
    epsilon: float = 1e-9,
) -> MusicSpectrumResult:
    """Run bounded MUSIC frequency search over a 1D signal or snapshot matrix."""
    arr = np.asarray(samples)
    if arr.ndim == 1:
        n = arr.reshape(-1).size
        window = int(window_length or min(max_subspace_dim, max(8, n // 4)))
        snapshots = build_hankel_snapshots(arr, window_length=min(window, max_subspace_dim), max_snapshots=max_snapshots)
    elif arr.ndim == 2:
        snapshots = _limit_snapshot_count(np.asarray(arr, dtype=np.complex64), max_snapshots)
        if snapshots.shape[0] > max_subspace_dim:
            snapshots, _, source_dimension = _project_snapshots(snapshots, projection_dim=max_subspace_dim)
        else:
            source_dimension = int(snapshots.shape[0])
    else:
        raise ValueError("samples must be 1D or 2D")

    source_dimension = int(arr.shape[0] if arr.ndim == 2 else arr.reshape(-1).size)
    snapshots = _limit_snapshot_count(np.asarray(snapshots, dtype=np.complex64), max_snapshots)
    if snapshots.shape[0] > max_subspace_dim:
        snapshots, _, _ = _project_snapshots(snapshots, projection_dim=max_subspace_dim)

    noise, singular_values, used_signal_count = _covariance_svd(
        snapshots,
        signal_count=signal_count,
        diagonal_loading=diagonal_loading,
    )
    angles = np.linspace(frequency_range[0], frequency_range[1], sample_resolution, endpoint=False, dtype=np.float32)
    sensor_index = np.arange(snapshots.shape[0], dtype=np.float32)
    steering = np.exp(1j * np.outer(sensor_index, angles)).astype(np.complex64)
    spectrum = _pseudospectrum_from_noise(noise, steering, epsilon)
    distance = min_peak_distance or max(1, sample_resolution // max(8, top_k * 8))
    peaks = _select_peaks(spectrum, angles, top_k=top_k, min_peak_distance=distance)
    return MusicSpectrumResult(
        peaks=peaks,
        spectrum=spectrum,
        scan_angles=angles,
        singular_values=singular_values,
        covariance_shape=(int(snapshots.shape[0]), int(snapshots.shape[0])),
        projected_snapshot_shape=(int(snapshots.shape[0]), int(snapshots.shape[1])),
        source_dimension=source_dimension,
        snapshot_count=int(snapshots.shape[1]),
        signal_count=used_signal_count,
    )


def music_component_search(
    snapshots: np.ndarray,
    component_library: Mapping[str, np.ndarray],
    *,
    signal_count: int | None = None,
    top_k: int = 3,
    projection_dim: int = 64,
    max_snapshots: int = 256,
    projection_seed: int = 1729,
    diagonal_loading: float = 1e-6,
    epsilon: float = 1e-9,
) -> MusicComponentResult:
    """Score named candidate components against the noise subspace."""
    raw_snapshots = np.asarray(snapshots, dtype=np.complex64)
    if raw_snapshots.ndim != 2:
        raise ValueError("snapshots must be a 2D matrix shaped (dimension, snapshot_count)")
    raw_snapshots = _limit_snapshot_count(raw_snapshots, max_snapshots)
    projected, plan, source_dimension = _project_snapshots(
        raw_snapshots,
        projection_dim=projection_dim,
        seed=projection_seed,
    )
    noise, singular_values, used_signal_count = _covariance_svd(
        projected,
        signal_count=signal_count,
        diagonal_loading=diagonal_loading,
    )
    scores: dict[str, float] = {}
    for key, vector in component_library.items():
        component = _project_component(vector, projection_plan=plan, projection_dim=projected.shape[0])
        norm = float(np.linalg.norm(component))
        if norm <= epsilon:
            scores[str(key)] = 0.0
            continue
        component = (component / np.float32(norm)).reshape(-1, 1)
        denom = float(np.sum(np.abs(noise.conj().T @ component) ** 2))
        scores[str(key)] = float(1.0 / max(denom, epsilon))
    peaks = [
        MusicComponentPeak(key=key, score=score)
        for key, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    ]
    return MusicComponentResult(
        peaks=peaks,
        scores=scores,
        singular_values=singular_values,
        covariance_shape=(int(projected.shape[0]), int(projected.shape[0])),
        projected_snapshot_shape=(int(projected.shape[0]), int(projected.shape[1])),
        source_dimension=source_dimension,
        snapshot_count=int(projected.shape[1]),
        signal_count=used_signal_count,
    )


def dominant_music_angle(
    samples: np.ndarray,
    *,
    sample_resolution: int = 256,
    signal_count: int | None = 1,
    max_subspace_dim: int = 64,
) -> float:
    """Compatibility helper returning the strongest MUSIC peak angle in radians."""
    result = music_frequency_search(
        samples,
        sample_resolution=sample_resolution,
        signal_count=signal_count,
        top_k=1,
        max_subspace_dim=max_subspace_dim,
    )
    if not result.peaks:
        raise ValueError("MUSIC search produced no peaks")
    return result.peaks[0].angle

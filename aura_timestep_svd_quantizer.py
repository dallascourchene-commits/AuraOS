"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fb-[Q-SYS:TIMESTEP_SVD_QUANTIZER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Precision-Aware Edge Inference)
DEPENDENCIES: numpy, hashlib, time, asyncio
FUNCTIONS: SVDOutlierCompensator, DynamicClippingTracker, W4A4Quantizer, AsyncExpertQuantizationEngine, TimestepAwareSVDQuantizer, quantize_w4a4, dequantize_w4a4
SYNOPSIS: Timestep-Aware SVD Outlier Suppression with Dynamic Clipping Ratio Adjustment for W4A4 Quantization of MoE Activations (Claim N16). Operates fully asynchronously per expert. Uses the same SVD median-threshold operation as aura_spectral_memory._apply_spectral_filter (Axiom A5: Fractal Self-Organization -- one algebra, every scale). Pure NumPy, no GPU, compatible with 4GB RAM Termux constraint.
[/AURA_MASTER_KEY]

Timestep-Aware SVD Quantization Engine (Claim N16)
=====================================================

The core operation is identical to aura_spectral_memory._apply_spectral_filter:
    U, S, Vh = SVD(A)
    filtered_S = S * (S > median(S))
    C = U @ diag(filtered_S) @ Vh

Applied here at the quantization scale:
    1. SVD outlier compensation (absorb outliers into low-rank branch)
    2. Dynamic clipping ratio (grammar that constrains the activation range)
    3. 4-bit uniform quantization (W4A4)
    4. Async per-expert execution (MoE-aware)

Axiom mapping:
    A1: Activations are regions of the 10,000-D field
    A2: Compensation matrix C_t is a holographic projection of outlier topology
    A5: Same SVD+median operation as spectral_memory, at quantization scale
    P2: Clipping ratio rho_t is the grammar constraining what passes through
    P3: Dynamic rho_t adapts toward minimum reconstruction error (coherence)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Any

import numpy as np

# ── Constants ──
_DEFAULT_BITS = 4          # W4A4
_QUANT_LEVELS = 2 ** _DEFAULT_BITS   # 16 levels for 4-bit
_HALF_LEVELS = _QUANT_LEVELS // 2    # 8


# ═══════════════════════════════════════════════════════════════════════
# SVD Outlier Compensation
# ═══════════════════════════════════════════════════════════════════════

class SVDOutlierCompensator:
    """
    Absorb activation outliers using a low-rank SVD branch.

    Same principle as aura_spectral_memory._apply_spectral_filter:
        filtered_S = S * (S > median(S))

    But here we return both the compensated activation AND the
    low-rank residual (the outlier energy that was absorbed).
    """

    def compensate(
        self,
        activation: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
        """
        SVD outlier compensation for a single activation matrix.

        Args:
            activation: shape (m, n) activation matrix at timestep t

        Returns:
            (compensated, residual, stats)
            - compensated: activation with outliers absorbed
            - residual: the low-rank outlier component
            - stats: diagnostic metrics
        """
        if activation.ndim == 1:
            activation = activation.reshape(1, -1)

        _m, _n = activation.shape

        # SVD decomposition (same as spectral_memory line 25)
        U, S, Vh = np.linalg.svd(activation, full_matrices=False)

        # Median threshold (same as spectral_memory line 26)
        median_sv = float(np.median(S))
        mask = S > median_sv

        # Low-rank compensation: retain only above-median singular values
        S_compensated = S * mask
        S_residual = S * (~mask)

        # Reconstruct
        compensated = U @ np.diag(S_compensated) @ Vh
        residual = U @ np.diag(S_residual) @ Vh

        # Stats
        total_energy = float(np.sum(S ** 2))
        retained_energy = float(np.sum(S_compensated ** 2))
        outlier_energy = float(np.sum(S_residual ** 2))

        stats = {
            "singular_values": len(S),
            "retained_components": int(np.sum(mask)),
            "suppressed_components": int(np.sum(~mask)),
            "median_sv": median_sv,
            "max_sv": float(np.max(S)),
            "energy_retained_ratio": retained_energy / (total_energy + 1e-12),
            "outlier_energy_ratio": outlier_energy / (total_energy + 1e-12),
        }

        return compensated, residual, stats


# ═══════════════════════════════════════════════════════════════════════
# Dynamic Clipping Ratio Tracker
# ═══════════════════════════════════════════════════════════════════════

class DynamicClippingTracker:
    """
    Maintains a per-expert clipping ratio rho_t that adapts over timesteps.

    Principle P2 (Grammar Precedes Content): rho_t constrains the dynamic
    range like a grammar constrains valid expressions. P3 (Coherence is
    Attractor): rho_t drifts toward the value that minimizes reconstruction
    error, using exponential moving average of optimal clipping ratios.

    rho_t = alpha * rho_{t-1} + (1-alpha) * rho_optimal_t
    """

    def __init__(self, initial_ratio: float = 0.95, alpha: float = 0.9):
        self.rho = initial_ratio
        self.alpha = alpha
        self.history: list[float] = []
        self._search_grid = np.linspace(0.5, 1.0, 11)  # [0.5, 0.55, ..., 1.0]

    def update(self, activation: np.ndarray, quantized: np.ndarray) -> float:
        """
        Update clipping ratio based on reconstruction error.
        Searches for the rho that minimizes MSE between original and
        dequantized activation.
        """
        if activation.size == 0:
            return self.rho

        abs_max = float(np.max(np.abs(activation)))
        if abs_max < 1e-12:
            return self.rho

        best_rho = self.rho
        best_mse = float('inf')

        for candidate_rho in self._search_grid:
            clipped = np.clip(activation, -candidate_rho * abs_max, candidate_rho * abs_max)
            q = _quantize_array(clipped, candidate_rho * abs_max)
            dq = _dequantize_array(q, candidate_rho * abs_max)
            mse = float(np.mean((activation - dq) ** 2))
            if mse < best_mse:
                best_mse = mse
                best_rho = candidate_rho

        # EMA update (P3: drift toward coherence)
        self.rho = self.alpha * self.rho + (1 - self.alpha) * best_rho
        self.history.append(self.rho)

        return self.rho

    @property
    def current_ratio(self) -> float:
        return self.rho


# ═══════════════════════════════════════════════════════════════════════
# W4A4 Quantization Primitives
# ═══════════════════════════════════════════════════════════════════════

def _quantize_array(x: np.ndarray, abs_max: float) -> np.ndarray:
    """Uniform symmetric 4-bit quantization."""
    if abs_max < 1e-12:
        return np.zeros_like(x, dtype=np.int8)
    scale = abs_max / _HALF_LEVELS
    return np.clip(
        np.round(x / scale).astype(np.int8),
        -_HALF_LEVELS, _HALF_LEVELS - 1
    )


def _dequantize_array(q: np.ndarray, abs_max: float) -> np.ndarray:
    """Dequantize 4-bit integers back to float."""
    scale = abs_max / _HALF_LEVELS
    return q.astype(np.float32) * scale


def quantize_w4a4(
    activation: np.ndarray,
    clipping_ratio: float = 0.95,
) -> tuple[np.ndarray, float]:
    """
    W4A4 quantization with clipping.

    Args:
        activation: float32 activation tensor
        clipping_ratio: fraction of dynamic range to preserve

    Returns:
        (quantized_int8, scale_factor)
    """
    abs_max = float(np.max(np.abs(activation)))
    clipped_max = clipping_ratio * abs_max
    clipped = np.clip(activation, -clipped_max, clipped_max)
    quantized = _quantize_array(clipped, clipped_max)
    return quantized, clipped_max


def dequantize_w4a4(quantized: np.ndarray, scale: float) -> np.ndarray:
    """Dequantize W4A4 back to float32."""
    return _dequantize_array(quantized, scale)


# ═══════════════════════════════════════════════════════════════════════
# Full Timestep-Aware SVD Quantizer
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class QuantizationResult:
    """Result of quantizing one activation at one timestep."""
    quantized: np.ndarray          # int8 quantized values
    scale: float                   # dequantization scale factor
    clipping_ratio: float          # rho_t used
    svd_stats: dict[str, float]    # SVD compensation diagnostics
    reconstruction_mse: float      # error metric
    timestep: int
    expert_id: str
    elapsed_ms: float


class TimestepAwareSVDQuantizer:
    """
    Full N16 implementation: timestep-aware SVD outlier suppression
    with dynamic clipping for W4A4 quantization.

    Usage:
        quantizer = TimestepAwareSVDQuantizer()
        result = quantizer.quantize_activation(activation, timestep=t, expert_id="expert_0")
        dequantized = dequantize_w4a4(result.quantized, result.scale)
    """

    def __init__(self, initial_clipping_ratio: float = 0.95, ema_alpha: float = 0.9):
        self.compensator = SVDOutlierCompensator()
        self._expert_trackers: dict[str, DynamicClippingTracker] = {}
        self._initial_ratio = initial_clipping_ratio
        self._ema_alpha = ema_alpha
        self._total_quantized = 0

    def _get_tracker(self, expert_id: str) -> DynamicClippingTracker:
        """Get or create per-expert clipping tracker."""
        if expert_id not in self._expert_trackers:
            self._expert_trackers[expert_id] = DynamicClippingTracker(
                initial_ratio=self._initial_ratio,
                alpha=self._ema_alpha,
            )
        return self._expert_trackers[expert_id]

    def quantize_activation(
        self,
        activation: np.ndarray,
        timestep: int = 0,
        expert_id: str = "default",
    ) -> QuantizationResult:
        """
        Quantize a single expert's activation at a given timestep.

        Pipeline:
        1. SVD outlier compensation (absorb outliers into low-rank branch)
        2. Dynamic clipping (per-expert adaptive ratio)
        3. W4A4 quantization
        4. Update clipping ratio from reconstruction error
        """
        t0 = time.perf_counter()

        # 1. SVD outlier compensation
        compensated, _residual, svd_stats = self.compensator.compensate(activation)

        # 2. Get per-expert clipping ratio
        tracker = self._get_tracker(expert_id)
        rho_t = tracker.current_ratio

        # 3. W4A4 quantization with dynamic clipping
        quantized, scale = quantize_w4a4(compensated, clipping_ratio=rho_t)

        # 4. Measure reconstruction error
        dequantized = dequantize_w4a4(quantized, scale)
        mse = float(np.mean((compensated - dequantized) ** 2))

        # 5. Update clipping ratio for next timestep
        tracker.update(compensated, quantized)

        self._total_quantized += 1
        elapsed = (time.perf_counter() - t0) * 1000

        return QuantizationResult(
            quantized=quantized,
            scale=scale,
            clipping_ratio=rho_t,
            svd_stats=svd_stats,
            reconstruction_mse=mse,
            timestep=timestep,
            expert_id=expert_id,
            elapsed_ms=elapsed,
        )

    def get_expert_stats(self) -> dict[str, Any]:
        """Get per-expert clipping ratio history and stats."""
        return {
            eid: {
                "current_ratio": tracker.current_ratio,
                "history_length": len(tracker.history),
                "ratio_range": (
                    min(tracker.history) if tracker.history else 0,
                    max(tracker.history) if tracker.history else 0,
                ),
            }
            for eid, tracker in self._expert_trackers.items()
        }

    @property
    def total_quantized(self) -> int:
        return self._total_quantized


# ═══════════════════════════════════════════════════════════════════════
# Async Per-Expert Quantization Engine (MoE-aware)
# ═══════════════════════════════════════════════════════════════════════

class AsyncExpertQuantizationEngine:
    """
    Asynchronous quantization engine for MoE architectures.

    Each expert's activations are quantized independently and concurrently.
    Axiom A5: the same SVD+clip+quantize pipeline at every expert scale.
    """

    def __init__(self, num_experts: int = 2, **kwargs):
        self.quantizers: dict[str, TimestepAwareSVDQuantizer] = {
            f"expert_{i}": TimestepAwareSVDQuantizer(**kwargs)
            for i in range(num_experts)
        }

    async def quantize_expert_activations(
        self,
        expert_activations: dict[str, np.ndarray],
        timestep: int = 0,
    ) -> dict[str, QuantizationResult]:
        """
        Quantize all experts' activations concurrently.

        Args:
            expert_activations: {expert_id: activation_matrix}
            timestep: current inference timestep

        Returns:
            {expert_id: QuantizationResult}
        """
        results = {}
        tasks = []

        for expert_id, activation in expert_activations.items():
            quantizer = self.quantizers.get(expert_id)
            if quantizer is None:
                quantizer = TimestepAwareSVDQuantizer()
                self.quantizers[expert_id] = quantizer
            tasks.append((expert_id, quantizer, activation, timestep))

        # Run per-expert quantization concurrently via asyncio
        async def _quantize_one(eid, q, act, ts):
            # Run in thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, q.quantize_activation, act, ts, eid
            )
            return eid, result

        coros = [_quantize_one(eid, q, act, ts) for eid, q, act, ts in tasks]
        completed = await asyncio.gather(*coros)

        for eid, result in completed:
            results[eid] = result

        return results

    def get_all_stats(self) -> dict[str, Any]:
        """Aggregate stats across all experts."""
        return {
            eid: q.get_expert_stats()
            for eid, q in self.quantizers.items()
        }


# ═══════════════════════════════════════════════════════════════════════
# Integration Helper
# ═══════════════════════════════════════════════════════════════════════

def compute_compression_efficiency(
    original: np.ndarray,
    result: QuantizationResult,
) -> dict[str, float]:
    """
    Compute the RHFT efficiency equation for quantization.

    E = (kappa * R) / (tau + epsilon)
    where:
        kappa = energy retention ratio from SVD (coherence)
        R = 1 - normalized_MSE (resonance / fidelity)
        tau = computation time in seconds (friction)
        epsilon = compression loss as fraction (extraction cost)
    """
    kappa = result.svd_stats.get("energy_retained_ratio", 1.0)
    mse_norm = result.reconstruction_mse / (float(np.var(original)) + 1e-12)
    R = max(0.0, 1.0 - mse_norm)
    tau = result.elapsed_ms / 1000.0
    epsilon = mse_norm

    E = (kappa * R) / (tau + epsilon + 1e-9)

    original_bytes = original.nbytes
    quantized_bytes = result.quantized.nbytes + 4  # +4 for scale float

    return {
        "efficiency_E": E,
        "kappa_coherence": kappa,
        "R_fidelity": R,
        "tau_friction_s": tau,
        "epsilon_loss": epsilon,
        "compression_ratio": original_bytes / max(1, quantized_bytes),
        "original_bytes": original_bytes,
        "quantized_bytes": quantized_bytes,
        "memory_reduction_pct": (1.0 - quantized_bytes / original_bytes) * 100,
        "bits_per_element": _DEFAULT_BITS,
    }


# ═══════════════════════════════════════════════════════════════════════
# CLI Demo
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Timestep-Aware SVD Quantization (Claim N16) Demo ===\n")

    quantizer = TimestepAwareSVDQuantizer()

    # Simulate MoE activations with outliers across timesteps
    rng = np.random.default_rng(42)

    for t in range(5):
        # Normal activations + sparse outliers (the problem N16 solves)
        activation = rng.standard_normal((64, 128)).astype(np.float32)
        # Inject sparse outliers (3% of values are 20x normal magnitude)
        outlier_mask = rng.random((64, 128)) < 0.03
        activation[outlier_mask] *= 20.0

        result = quantizer.quantize_activation(activation, timestep=t, expert_id="expert_0")
        eff = compute_compression_efficiency(activation, result)

        print(f"  Timestep {t}:")
        print(f"    Clipping ratio: {result.clipping_ratio:.4f}")
        print(f"    SVD retained: {result.svd_stats['retained_components']}/{result.svd_stats['singular_values']} components")
        print(f"    Reconstruction MSE: {result.reconstruction_mse:.6f}")
        print(f"    Compression: {eff['compression_ratio']:.1f}x ({eff['memory_reduction_pct']:.0f}% reduction)")
        print(f"    Efficiency E: {eff['efficiency_E']:.2f}")
        print(f"    Latency: {result.elapsed_ms:.2f}ms")
        print()

    stats = quantizer.get_expert_stats()
    print(f"  Expert stats: {stats}")
    print(f"  Total activations quantized: {quantizer.total_quantized}")
    print("\nDemo complete.")

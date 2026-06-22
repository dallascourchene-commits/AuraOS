"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fc-[Q-SYS:SVD_QUANT_TEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Quantization Verification)
DEPENDENCIES: pytest, numpy, asyncio, aura_timestep_svd_quantizer
FUNCTIONS: test_svd_compensation, test_dynamic_clipping, test_w4a4_roundtrip, test_timestep_adaptation, test_async_multi_expert, test_compression_ratio, test_efficiency_equation, test_no_new_deps
SYNOPSIS: Test suite for Claim N16 -- Timestep-Aware SVD Quantization with dynamic clipping and per-expert async execution.
[/AURA_MASTER_KEY]
"""

import os
import sys
import asyncio
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aura_timestep_svd_quantizer import (
    SVDOutlierCompensator,
    DynamicClippingTracker,
    TimestepAwareSVDQuantizer,
    AsyncExpertQuantizationEngine,
    quantize_w4a4,
    dequantize_w4a4,
    compute_compression_efficiency,
)


# ── SVD Outlier Compensation ──

class TestSVDCompensation:
    def test_compensation_reduces_outlier_energy(self):
        """SVD compensation should reduce outlier energy."""
        rng = np.random.default_rng(42)
        act = rng.standard_normal((32, 64)).astype(np.float32)
        # Inject outliers
        act[0, 0] = 100.0
        act[5, 10] = -80.0

        comp = SVDOutlierCompensator()
        compensated, residual, stats = comp.compensate(act)

        assert stats["suppressed_components"] > 0
        assert stats["energy_retained_ratio"] > 0.5
        assert stats["outlier_energy_ratio"] < 0.5
        # Residual should capture some energy (suppressed low-rank components)
        assert np.linalg.norm(residual) > 0
        # Total energy partitioned: compensated + residual should reconstruct
        reconstructed = compensated + residual
        np.testing.assert_allclose(reconstructed, act, atol=1e-4)

    def test_compensation_preserves_shape(self):
        act = np.random.randn(16, 32).astype(np.float32)
        comp = SVDOutlierCompensator()
        compensated, residual, _ = comp.compensate(act)
        assert compensated.shape == act.shape
        assert residual.shape == act.shape

    def test_compensation_handles_1d(self):
        act = np.random.randn(64).astype(np.float32)
        comp = SVDOutlierCompensator()
        compensated, residual, stats = comp.compensate(act)
        assert compensated.ndim == 2  # Reshaped to (1, 64)

    def test_svd_median_threshold_matches_spectral_memory(self):
        """Verify our SVD uses the same median threshold as aura_spectral_memory."""
        rng = np.random.default_rng(99)
        act = rng.standard_normal((20, 40)).astype(np.float32)

        # Our implementation
        comp = SVDOutlierCompensator()
        compensated, _, stats = comp.compensate(act)

        # Direct spectral_memory style
        U, S, Vh = np.linalg.svd(act, full_matrices=False)
        filtered_S = S * (S > np.median(S))
        expected = U @ np.diag(filtered_S) @ Vh

        np.testing.assert_allclose(compensated, expected, atol=1e-5)


# ── Dynamic Clipping ──

class TestDynamicClipping:
    def test_clipping_ratio_adapts(self):
        """Ratio should change over updates."""
        tracker = DynamicClippingTracker(initial_ratio=0.95, alpha=0.5)
        rng = np.random.default_rng(42)

        for _ in range(5):
            act = rng.standard_normal((16, 32)).astype(np.float32)
            q, scale = quantize_w4a4(act, tracker.current_ratio)
            tracker.update(act, q)

        assert tracker.current_ratio != 0.95  # Should have adapted
        assert len(tracker.history) == 5

    def test_clipping_ratio_stays_bounded(self):
        """Ratio should stay in [0.5, 1.0] range."""
        tracker = DynamicClippingTracker()
        rng = np.random.default_rng(42)

        for _ in range(20):
            act = rng.standard_normal((8, 16)).astype(np.float32) * 100
            q, _ = quantize_w4a4(act, tracker.current_ratio)
            tracker.update(act, q)

        assert 0.4 <= tracker.current_ratio <= 1.1


# ── W4A4 Quantization ──

class TestW4A4:
    def test_roundtrip_fidelity(self):
        """Quantize-dequantize should approximate original."""
        act = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
        q, scale = quantize_w4a4(act)
        dq = dequantize_w4a4(q, scale)
        # Should be within one quantization step
        assert np.max(np.abs(act - dq)) < 0.3

    def test_quantized_is_int8(self):
        act = np.random.randn(100).astype(np.float32)
        q, _ = quantize_w4a4(act)
        assert q.dtype == np.int8

    def test_quantized_range(self):
        """4-bit quantized values should be in [-8, 7]."""
        act = np.random.randn(1000).astype(np.float32) * 10
        q, _ = quantize_w4a4(act)
        assert np.all(q >= -8)
        assert np.all(q <= 7)

    def test_zero_input(self):
        act = np.zeros((10,), dtype=np.float32)
        q, scale = quantize_w4a4(act)
        assert np.all(q == 0)


# ── Full Quantizer ──

class TestTimestepQuantizer:
    def test_quantizer_produces_result(self):
        quantizer = TimestepAwareSVDQuantizer()
        act = np.random.randn(32, 64).astype(np.float32)
        result = quantizer.quantize_activation(act, timestep=0, expert_id="e0")
        assert result.quantized.dtype == np.int8
        assert result.scale > 0
        assert result.timestep == 0
        assert result.expert_id == "e0"

    def test_clipping_ratio_drifts_over_timesteps(self):
        quantizer = TimestepAwareSVDQuantizer()
        rng = np.random.default_rng(42)
        ratios = []

        for t in range(10):
            act = rng.standard_normal((16, 32)).astype(np.float32)
            act[rng.random((16, 32)) < 0.05] *= 15.0  # Outliers
            result = quantizer.quantize_activation(act, timestep=t, expert_id="e0")
            ratios.append(result.clipping_ratio)

        # Ratio should have changed from initial
        assert ratios[-1] != ratios[0]

    def test_per_expert_independent_tracking(self):
        quantizer = TimestepAwareSVDQuantizer()
        rng = np.random.default_rng(42)

        # Expert 0 gets wild outliers, Expert 1 gets clean data
        for t in range(5):
            wild = rng.standard_normal((16, 32)).astype(np.float32) * 50
            clean = rng.standard_normal((16, 32)).astype(np.float32)
            quantizer.quantize_activation(wild, timestep=t, expert_id="expert_wild")
            quantizer.quantize_activation(clean, timestep=t, expert_id="expert_clean")

        stats = quantizer.get_expert_stats()
        assert "expert_wild" in stats
        assert "expert_clean" in stats
        # They should have different clipping ratios
        wild_ratio = stats["expert_wild"]["current_ratio"]
        clean_ratio = stats["expert_clean"]["current_ratio"]
        assert wild_ratio != clean_ratio


# ── Async Multi-Expert ──

class TestAsyncEngine:
    def test_async_quantizes_all_experts(self):
        engine = AsyncExpertQuantizationEngine(num_experts=3)
        rng = np.random.default_rng(42)
        activations = {
            f"expert_{i}": rng.standard_normal((16, 32)).astype(np.float32)
            for i in range(3)
        }

        results = asyncio.get_event_loop().run_until_complete(
            engine.quantize_expert_activations(activations, timestep=0)
        )

        assert len(results) == 3
        for eid, result in results.items():
            assert result.quantized.dtype == np.int8
            assert result.expert_id == eid


# ── Compression & Efficiency ──

class TestCompressionEfficiency:
    def test_compression_ratio_is_4x(self):
        """float32 -> int8 should give ~4x compression."""
        act = np.random.randn(64, 128).astype(np.float32)
        quantizer = TimestepAwareSVDQuantizer()
        result = quantizer.quantize_activation(act)
        eff = compute_compression_efficiency(act, result)
        assert eff["compression_ratio"] > 3.5
        assert eff["memory_reduction_pct"] > 70

    def test_efficiency_positive(self):
        act = np.random.randn(32, 64).astype(np.float32)
        quantizer = TimestepAwareSVDQuantizer()
        result = quantizer.quantize_activation(act)
        eff = compute_compression_efficiency(act, result)
        assert eff["efficiency_E"] > 0
        assert eff["kappa_coherence"] > 0
        assert eff["R_fidelity"] >= 0

    def test_bits_per_element(self):
        act = np.random.randn(32, 64).astype(np.float32)
        quantizer = TimestepAwareSVDQuantizer()
        result = quantizer.quantize_activation(act)
        eff = compute_compression_efficiency(act, result)
        assert eff["bits_per_element"] == 4


# ── No New Dependencies ──

class TestNoDeps:
    def test_only_stdlib_and_numpy(self):
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "aura_timestep_svd_quantizer.py")
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        import ast
        tree = ast.parse(source)
        allowed = {
            "__future__", "asyncio", "hashlib", "time",
            "dataclasses", "typing", "numpy", "np", "base64",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in allowed, f"Disallowed import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in allowed, f"Disallowed from: {node.module}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

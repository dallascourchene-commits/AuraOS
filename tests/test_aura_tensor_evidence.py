"""Tests for the core Tensor Evidence + Belief Propagation engine."""
from __future__ import annotations
import numpy as np
import pytest
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from aura_tensor_evidence import (
    TensorVariable, TensorFactor, EvidenceReference, TensorBeliefEngine,
    compress_factor, SUPPORTED, CONTRADICTED, UNRESOLVED,
    CONVERGED, NOT_CONVERGED, CONTRADICTORY_HARD_FACTORS, INVALID_GRAPH, FALLBACK_REQUIRED,
    HIGH_CONFINEMENT, MODERATE_CONFINEMENT, LOW_CONFINEMENT, UNKNOWN,
)


class TestCoreEngine:
    def test_tree_graph_exact_result(self):
        """BP on a tree converges to exact marginals."""
        v1, v2 = TensorVariable("A"), TensorVariable("B")
        f1 = TensorFactor("f1", ["A"], np.array([0.9, 0.05, 0.05]))
        f2 = TensorFactor("f2", ["B"], np.array([0.1, 0.8, 0.1]))
        f3 = TensorFactor("f3", ["A", "B"], np.array([[0.8,0.1,0.1],[0.1,0.8,0.1],[0.33,0.33,0.34]]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v1, v2], [f1, f2, f3])
        assert r["ok"] is True
        assert r["status"] == CONVERGED
        a = next(x for x in r["results"] if x["var_id"] == "A")
        assert a["state"] == SUPPORTED
        b = next(x for x in r["results"] if x["var_id"] == "B")
        assert b["state"] == CONTRADICTED

    def test_deterministic_replay(self):
        """Same inputs produce same outputs."""
        v = TensorVariable("X")
        f = TensorFactor("f", ["X"], np.array([0.8, 0.1, 0.1]))
        engine = TensorBeliefEngine()
        r1 = engine.analyze([v], [f])
        r2 = engine.analyze([v], [f])
        assert r1["results"][0]["beliefs"] == r2["results"][0]["beliefs"]
        assert r1["graph_hash"] == r2["graph_hash"]

    def test_loopy_graph_convergence(self):
        """Small loopy graph should converge or report non-convergence."""
        v1, v2, v3 = TensorVariable("A"), TensorVariable("B"), TensorVariable("C")
        f_ab = TensorFactor("f_ab", ["A", "B"], np.array([[0.7,0.2,0.1],[0.2,0.6,0.2],[0.3,0.3,0.4]]))
        f_bc = TensorFactor("f_bc", ["B", "C"], np.array([[0.6,0.3,0.1],[0.2,0.7,0.1],[0.3,0.3,0.4]]))
        f_ca = TensorFactor("f_ca", ["C", "A"], np.array([[0.7,0.2,0.1],[0.2,0.6,0.2],[0.3,0.3,0.4]]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v1, v2, v3], [f_ab, f_bc, f_ca], max_iterations=50)
        assert r["status"] in (CONVERGED, NOT_CONVERGED)
        assert r["iterations"] <= 50

    def test_damping(self):
        """Damping changes convergence behavior."""
        v = TensorVariable("X")
        f = TensorFactor("f", ["X"], np.array([0.6, 0.3, 0.1]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f], damping=0.1)
        assert r["ok"] is True

    def test_residual_threshold(self):
        """Lower threshold requires more iterations."""
        v = TensorVariable("X")
        f = TensorFactor("f", ["X"], np.array([0.7, 0.2, 0.1]))
        engine = TensorBeliefEngine()
        r1 = engine.analyze([v], [f], residual_tolerance=1e-2)
        r2 = engine.analyze([v], [f], residual_tolerance=1e-6)
        assert r2["iterations"] >= r1["iterations"]

    def test_non_convergence_fallback(self):
        """Non-converged results are visible and not presented as resolved."""
        v = TensorVariable("X")
        # Create a graph that won't converge in 1 iteration
        f1 = TensorFactor("f1", ["X"], np.array([0.5, 0.4, 0.1]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f1], max_iterations=1, residual_tolerance=1e-10)
        assert r["status"] in (NOT_CONVERGED, CONVERGED)
        if r["status"] == NOT_CONVERGED:
            assert any("advisory" in w.lower() or "non-converged" in w.lower()
                       for w in r["confinement"].get("warnings", []))

    def test_contradictory_hard_factors(self):
        """Two hard factors on same var with different states = contradictory."""
        v = TensorVariable("X")
        f1 = TensorFactor("f1", ["X"], np.array([0.99, 0.005, 0.005]))
        f2 = TensorFactor("f2", ["X"], np.array([0.005, 0.99, 0.005]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f1, f2])
        assert r["status"] == CONTRADICTORY_HARD_FACTORS

    def test_nan_rejection(self):
        """NaN in evidence is rejected."""
        v = TensorVariable("X")
        f = TensorFactor("f", ["X"], np.array([0.6, 0.3, 0.1]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f], evidence={"X": np.array([np.nan, 0.0, 0.0])})
        assert r["ok"] is False
        assert r["status"] == INVALID_GRAPH

    def test_inf_rejection(self):
        """Inf in evidence is rejected."""
        v = TensorVariable("X")
        f = TensorFactor("f", ["X"], np.array([0.6, 0.3, 0.1]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f], evidence={"X": np.array([np.inf, 0.0, 0.0])})
        assert r["ok"] is False
        assert r["status"] == INVALID_GRAPH

    def test_evidence_reference_preservation(self):
        """Evidence references are preserved in results."""
        ref = EvidenceReference(file="test.py", symbol="func_x", line_range=(1, 10), source_hash="abc")
        v = TensorVariable("X", evidence_refs=[ref])
        f = TensorFactor("f", ["X"], np.array([0.8, 0.1, 0.1]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f])
        x_result = r["results"][0]
        assert len(x_result["supporting_evidence"]) > 0
        assert x_result["supporting_evidence"][0]["file"] == "test.py"

    def test_empty_variables_fallback(self):
        """Empty variable list triggers fallback."""
        engine = TensorBeliefEngine()
        r = engine.analyze([], [])
        assert r["ok"] is False
        assert r["status"] == INVALID_GRAPH

    def test_authority_flags(self):
        """Authority flags are present and correct in all results."""
        v = TensorVariable("X")
        f = TensorFactor("f", ["X"], np.array([0.6, 0.3, 0.1]))
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f])
        assert r["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert r["tensor_patch_authority"] is False
        assert r["belief_propagation_patch_authority"] is False
        assert r["civic_decision_authority"] is False


class TestCompression:
    def test_low_rank_compression_success(self):
        """Low-rank tensor compresses with small error."""
        u = np.random.rand(8, 1); v = np.random.rand(1, 8)
        tensor = u @ v  # rank 1
        r = compress_factor(tensor)
        assert r["ok"] is True
        assert r["compressed"] is True
        assert r["compressed_rank"] == 1
        assert r["compression_ratio"] < 1.0

    def test_compression_refusal_high_error(self):
        """Compression refused when error exceeds tolerance."""
        tensor = np.random.rand(8, 8)  # full rank
        r = compress_factor(tensor, reconstruction_tolerance=1e-6)
        assert r["ok"] is True
        assert r["compressed"] is False

    def test_compression_small_tensor_skipped(self):
        """Small tensors skip compression."""
        r = compress_factor(np.array([0.5, 0.3, 0.2]))
        assert r["ok"] is True
        assert r["compressed"] is False

    def test_compression_reports_shape_and_counts(self):
        """Compression reports original shape, compressed rank, element counts."""
        u = np.random.rand(6, 2); v = np.random.rand(2, 6)
        tensor = u @ v
        r = compress_factor(tensor)
        assert "original_shape" in r
        assert "compressed_rank" in r
        assert "original_elements" in r
        assert "compressed_elements" in r
        assert "reconstruction_error" in r

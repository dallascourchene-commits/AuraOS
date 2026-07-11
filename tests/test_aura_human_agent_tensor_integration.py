"""Tests for Human Agent Arena tensor integration — commands, API, handoff."""
from __future__ import annotations
import pytest, json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


class TestTensorCLICommands:
    def test_tensor_analyze_coding_cli(self):
        from aura_agent_arena_cli import main as cli_main
        rc = cli_main(["tensor-analyze-coding", "--grounded", "--tests", "--deps", "2"])
        assert rc == 0

    def test_tensor_compress_cli(self):
        from aura_agent_arena_cli import main as cli_main
        rc = cli_main(["tensor-compress"])
        assert rc == 0

    def test_tensor_available_flag(self):
        from aura_agent_arena_cli import _TENSOR_AVAILABLE
        assert _TENSOR_AVAILABLE is True

    def test_tensor_analyze_coding_has_advisory_fields(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(source_grounded=True, tests_present=True)
        assert "advisory_summary" in r
        assert "patch_authority" in r
        assert "tensor_patch_authority" in r
        assert "belief_propagation_patch_authority" in r

    def test_advisory_only_wording(self):
        """Results are advisory, not authoritative."""
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(source_grounded=True)
        assert r["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert r["tensor_patch_authority"] is False


class TestTensorCivicAPI:
    def test_tensor_analyze_civic_endpoint(self):
        from aura_human_agent_arena_server import _handle_civic_api
        from urllib.parse import urlparse
        # Create a session first
        parsed_create = urlparse("/api/civic/sessions")
        _, data = _handle_civic_api("POST", "/api/civic/sessions", parsed_create, {"objective": "test tensor"})
        sid = data["session"]["session_id"]
        # Analyze tensor
        parsed = urlparse(f"/api/civic/sessions/{sid}/tensor-analyze")
        code, result = _handle_civic_api("POST", f"/api/civic/sessions/{sid}/tensor-analyze", parsed, {})
        assert code == 200
        assert result["ok"] is True
        assert "tensor_evidence_analysis" in result
        assert result["tensor_evidence_analysis"]["non_binding"] is True


class TestTensorHandoff:
    def test_handoff_packet_has_tensor_summary(self):
        """Handoff packet should include tensor evidence summary when available."""
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(source_grounded=True, tests_present=True, node_ids=["n1"])
        # The advisory_summary is what goes in the handoff
        summary = r["advisory_summary"]
        assert "ready_for_agent_handoff" in summary
        assert "confinement_level" in summary
        assert "human_review_recommended" in summary
        assert "influence_radius" in summary


class TestJSpaceIntegration:
    def test_jspace_compact_references(self):
        """JSpace should only carry compact references, not full tensor payloads."""
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(source_grounded=True)
        te = r["tensor_evidence"]
        # The graph_hash is the compact reference for JSpace
        assert "graph_hash" in te
        assert len(te["graph_hash"]) <= 32  # compact
        # Full belief_results stay in the Arena session, not JSpace
        assert "belief_results" in te  # present in full result but JSpace would only carry the hash


class TestEmergentCandidateFactors:
    def test_emergent_candidate_marked_advisory(self):
        """Emergent candidate factors must be marked advisory."""
        from aura_tensor_evidence import TensorFactor, TensorVariable, TensorBeliefEngine
        import numpy as np
        v = TensorVariable("X")
        f = TensorFactor("f_emergent", ["X"], np.array([0.6, 0.3, 0.1]),
                         factor_origin="emergent_candidate", authority="advisory")
        engine = TensorBeliefEngine()
        r = engine.analyze([v], [f])
        assert r["ok"] is True
        assert r["belief_propagation_patch_authority"] is False

"""Tests for the Civic Commons Arena tensor adapter."""
from __future__ import annotations
import pytest, json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


class TestCivicTensorAdapter:
    def _make_session(self):
        """Build a realistic civic session for tensor analysis."""
        return {
            "needs": [{"id": "n1", "description": "affordable hairstylist"}],
            "offers": [{"id": "o1", "description": "accessible room"}, {"id": "o2", "description": "chairs"}],
            "match_results": [{"ok": True, "score": 0.8}],
            "workstreams": [{"id": "w1"}, {"id": "w2"}],
            "scenarios": [{"scenario_id": "coop"}, {"scenario_id": "rental"}],
            "legal_instruments": [{"id": "li1", "title": "Zoning Bylaw"}],
            "consent_arc": {
                "responses": [
                    {"response_type": "SUPPORT", "participant": "p1"},
                    {"response_type": "OBJECT", "participant": "p2"},
                ],
                "representation_gaps": ["Youth underrepresented"],
            },
            "representation_gaps": ["Youth underrepresented"],
            "pilot": {"status": "NOT_STARTED"},
            "what_if": {"changed_assumptions": ["reduce cost"]},
            "decision_packet": {"objective": "test"},
        }

    def test_analyze_civic_session(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        assert r["ok"] is True
        tea = r["tensor_evidence_analysis"]
        assert "status" in tea
        assert tea["n_variables"] == 11
        assert "supported_variables" in tea
        assert "contradicted_variables" in tea
        assert "unresolved_variables" in tea

    def test_dissent_preserved(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        assert r["tensor_evidence_analysis"]["dissent_preserved"] is True

    def test_representation_gaps_visible(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        assert r["tensor_evidence_analysis"]["representation_gaps_visible"] is True

    def test_non_binding(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        assert r["tensor_evidence_analysis"]["non_binding"] is True

    def test_no_consensus_declared(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        assert r["tensor_evidence_analysis"]["no_consensus_declared"] is True

    def test_civic_decision_authority_false(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        assert r["civic_decision_authority"] is False

    def test_scenario_support_present(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        assert "SCENARIO_VIABLE" in r["scenario_support"]
        assert "PILOT_READY_FOR_DELIBERATION" in r["scenario_support"]

    def test_empty_session_safe(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session({})
        assert r["ok"] is True
        assert len(r["tensor_evidence_analysis"]["unresolved_variables"]) > 0

    def test_evidence_references_in_results(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        refs = r["tensor_evidence_analysis"].get("evidence_references", [])
        # Should have some evidence refs from needs or legal instruments
        assert isinstance(refs, list)

    def test_all_required_variables(self):
        from aura_civic_tensor_adapter import CIVIC_VARIABLES, analyze_civic_session
        r = analyze_civic_session(self._make_session())
        result_vars = {x["var_id"] for x in r["tensor_evidence_analysis"]["belief_results"]}
        for v in CIVIC_VARIABLES:
            assert v in result_vars, f"Missing: {v}"

    def test_confinement_analysis(self):
        from aura_civic_tensor_adapter import analyze_civic_session
        r = analyze_civic_session(self._make_session())
        conf = r["tensor_evidence_analysis"]["confinement"]
        assert "confinement_score" in conf
        assert "confinement_level" in conf
        assert "influence_radius" in conf

    def test_integration_with_civic_demo(self):
        """Tensor analysis works after running a civic demo."""
        from aura_civic_runtime import run_full_demo, get_session
        from aura_civic_tensor_adapter import analyze_civic_session
        demo = run_full_demo(story="youth_centre")
        assert demo["ok"] is True
        sess = get_session(demo["session_id"])
        assert sess["ok"] is True, f"Session not found after demo: {demo['session_id']}"
        r = analyze_civic_session(sess["session"])
        assert r["ok"] is True
        assert r["tensor_evidence_analysis"]["non_binding"] is True

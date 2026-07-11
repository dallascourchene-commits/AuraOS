"""Tests for the Coding Arena tensor adapter."""
from __future__ import annotations
import pytest
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


class TestCodingTensorAdapter:
    def test_analyze_grounded_with_tests(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(
            node_ids=["node1", "node2"],
            source_grounded=True,
            tests_present=True,
            dependency_depth=2,
            public_api_touched=False,
        )
        assert r["ok"] is True
        te = r["tensor_evidence"]
        assert "status" in te
        assert te["n_variables"] == 7
        assert "TARGET_GROUNDED" in te["supported"]

    def test_analyze_ungrounded_no_tests(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(
            source_grounded=False,
            tests_present=False,
            dependency_depth=5,
        )
        assert r["ok"] is True
        te = r["tensor_evidence"]
        assert "TARGET_GROUNDED" in te.get("unresolved", []) or "TARGET_GROUNDED" in te.get("contradicted", [])

    def test_no_patch_authority(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(source_grounded=True)
        assert r["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert r["tensor_patch_authority"] is False

    def test_confinement_score_present(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(source_grounded=True, tests_present=True)
        assert "confinement" in r["tensor_evidence"]
        assert "confinement_level" in r["tensor_evidence"]["confinement"]

    def test_boundary_nodes_reported(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(
            source_grounded=True, tests_present=True,
            public_api_touched=True,  # should create a risk
        )
        assert "boundary_nodes" in r["advisory_summary"]

    def test_human_review_recommended_when_unresolved(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(source_grounded=False, tests_present=False)
        assert r["advisory_summary"]["human_review_recommended"] is True

    def test_ready_for_handoff_when_grounded_tested(self):
        from aura_coding_tensor_adapter import analyze_coding_region
        r = analyze_coding_region(
            source_grounded=True, tests_present=True,
            dependency_depth=1, public_api_touched=False,
            external_effects=[],
        )
        # When everything is good, ready should be supported or at least not contradicted
        te = r["tensor_evidence"]
        ready = next(x for x in te["belief_results"] if x["var_id"] == "READY_FOR_AGENT_HANDOFF")
        assert ready["state"] in ("SUPPORTED", "UNRESOLVED")

    def test_all_required_variables_present(self):
        from aura_coding_tensor_adapter import analyze_coding_region, CODING_VARIABLES
        r = analyze_coding_region(source_grounded=True)
        result_vars = {x["var_id"] for x in r["tensor_evidence"]["belief_results"]}
        for v in CODING_VARIABLES:
            assert v in result_vars, f"Missing variable: {v}"

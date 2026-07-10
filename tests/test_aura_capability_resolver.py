"""Tests for Aura Capability Genome Resolver."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_capability_resolver import resolve_capabilities, PATCH_AUTHORITY


class TestCapabilityResolver:
    def test_basic_resolution(self):
        result = resolve_capabilities("refactor fireworks egress", repo_root=REPO_ROOT)
        assert result["version"] == "AURA_CAPABILITY_RESOLUTION_V1"
        assert result["objective"] == "refactor fireworks egress"
        assert "objective_hash" in result
        assert "codemap_digest" in result
        assert "topology_health" in result
        assert "exact_matches" in result
        assert "related_functions" in result
        assert "existing_affordances" in result
        assert "reuse_plan" in result
        assert "do_not_reinvent" in result
        assert "missing_capabilities" in result
        assert "read_slice_commands" in result
        assert "confidence" in result

    def test_exact_file_resolution(self):
        result = resolve_capabilities("test", target_files=["aura_llm_egress.py"], repo_root=REPO_ROOT)
        assert len(result["exact_matches"]) > 0
        assert result["exact_matches"][0]["file"] == "aura_llm_egress.py"
        assert result["exact_matches"][0]["grounding_class"] == "EXACT"

    def test_related_functions_found(self):
        result = resolve_capabilities("refactor fireworks egress", repo_root=REPO_ROOT)
        assert len(result["related_functions"]) > 0

    def test_no_hallucinated_symbols(self):
        result = resolve_capabilities("nonexistent_xyz_abc", repo_root=REPO_ROOT)
        for rf in result["related_functions"]:
            assert rf.get("file") is not None

    def test_do_not_reinvent(self):
        result = resolve_capabilities("refactor coding arena", repo_root=REPO_ROOT)
        assert len(result["do_not_reinvent"]) > 0

    def test_invariants(self):
        result = resolve_capabilities("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False

    def test_topology_health_included(self):
        result = resolve_capabilities("test", repo_root=REPO_ROOT)
        assert "topology_health" in result
        assert "topology_nodes" in result["topology_health"]

    def test_confidence_is_float(self):
        result = resolve_capabilities("test", repo_root=REPO_ROOT)
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

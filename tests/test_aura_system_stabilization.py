"""Tests for Aura System Stabilization Report."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_system_stabilization import stabilization_status, PATCH_AUTHORITY


class TestStabilization:
    def test_basic_report(self):
        result = stabilization_status(repo_root=REPO_ROOT)
        assert "ok" in result
        assert "git" in result
        assert "codemap" in result
        assert "lexc" in result
        assert "blocking_findings" in result
        assert "recommended_next_gate" in result

    def test_codemap_counts(self):
        result = stabilization_status(repo_root=REPO_ROOT)
        assert result["codemap"]["file_count"] > 0
        assert result["codemap"]["symbol_index_count"] > 0

    def test_lexc_validity(self):
        result = stabilization_status(repo_root=REPO_ROOT)
        assert result["lexc"]["complete_routes"] > 0

    def test_affordance_counts(self):
        result = stabilization_status(repo_root=REPO_ROOT)
        assert result["affordances"]["total"] >= 18

    def test_invariants(self):
        result = stabilization_status(repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False

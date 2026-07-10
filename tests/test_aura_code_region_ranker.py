"""Tests for Aura Code Region Ranker."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_code_region_ranker import rank_code_regions, PATCH_AUTHORITY


class TestRanker:
    def test_ranking(self):
        result = rank_code_regions("refactor fireworks egress", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "ranked_regions" in result
        assert "confidence" in result
        assert "context_efficiency_ratio" in result

    def test_respects_max_lines(self):
        result = rank_code_regions("test", repo_root=REPO_ROOT, max_lines=50)
        assert result["total_lines_selected"] <= 50
        # Also test with symbol-heavy objective to validate symbol-only budget enforcement
        result2 = rank_code_regions("WorkbenchState BLOCKED_SECURITY_RISK", repo_root=REPO_ROOT, max_lines=30)
        assert result2["total_lines_selected"] <= 30

    def test_has_localization_confidence(self):
        result = rank_code_regions("refactor", repo_root=REPO_ROOT)
        assert result["localization_confidence"] in ("high", "medium", "low")

    def test_invariants(self):
        result = rank_code_regions("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False

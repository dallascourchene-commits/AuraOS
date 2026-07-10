"""Tests for Aura Coding MUSIC Lane."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_coding_music_lane import music_rank_code_regions, music_to_ranking_evidence, PATCH_AUTHORITY


class TestMusicLane:
    def test_advisory(self):
        result = music_rank_code_regions("test", ["f1.py"], repo_root=REPO_ROOT)
        assert result.get("advisory_only", True) is True

    def test_ranking_evidence(self):
        result = music_to_ranking_evidence({"ranked_candidates": [{"candidate": "f1.py", "score": 0.5}]})
        assert result["advisory_only"] is True
        assert "advisory" in result["note"].lower()

    def test_invariants(self):
        result = music_rank_code_regions("test", [], repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY

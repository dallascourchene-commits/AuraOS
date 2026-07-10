"""Tests for Aura MUSIC + Mitosis Adapter."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_music_mitosis_adapter import (
    music_rank_cockpit_candidates, mitosis_split_objective, mitosis_to_phase_capsules,
    mitosis_to_agent_act_capsules, PATCH_AUTHORITY,
)


class TestMusicRank:
    def test_advisory_only(self):
        result = music_rank_cockpit_candidates("test", ["file1.py", "file2.py"])
        assert result["ok"] is True
        assert result["advisory_only"] is True
        assert "advisory" in result["note"].lower()

    def test_invariants(self):
        result = music_rank_cockpit_candidates("test", [])
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestMitosisSplit:
    def test_produces_children(self):
        result = mitosis_split_objective("Refactor routing. Fix tests. Update docs.")
        assert result["ok"] is True
        assert result["child_count"] > 0
        for child in result["children"]:
            assert "child_id" in child
            assert "objective" in child
            assert "patch_authority" in child

    def test_child_has_parent_objective(self):
        result = mitosis_split_objective("Do something complex")
        for child in result["children"]:
            assert child["parent_objective"] == "Do something complex"

    def test_invariants(self):
        result = mitosis_split_objective("test")
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False


class TestPhaseCapsules:
    def test_convert(self):
        split = mitosis_split_objective("Test objective")
        result = mitosis_to_phase_capsules(split["children"])
        assert result["ok"] is True
        assert len(result["phase_capsules"]) > 0


class TestActCapsules:
    def test_convert(self):
        split = mitosis_split_objective("Test objective")
        result = mitosis_to_agent_act_capsules(split["children"])
        assert result["ok"] is True
        assert len(result["act_capsules"]) > 0

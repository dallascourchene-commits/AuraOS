"""Tests for Aura Work Splitter."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_work_splitter import split_large_objective, work_split_to_act_capsules, PATCH_AUTHORITY


class TestWorkSplitter:
    def test_split(self):
        result = split_large_objective("Do A. Do B. Do C.", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["child_tasks"]) > 0
        for c in result["child_tasks"]:
            assert "patch_authority" in c

    def test_to_act_capsules(self):
        split = split_large_objective("Test", repo_root=REPO_ROOT)
        result = work_split_to_act_capsules(split, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["act_capsules"]) > 0

    def test_invariants(self):
        result = split_large_objective("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY

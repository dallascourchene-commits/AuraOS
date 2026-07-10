"""Tests for Aura Refactor Candidate."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_refactor_candidate import detect_refactor_candidates, candidate_to_grounding_requirement, PATCH_AUTHORITY


class TestRefactorCandidate:
    def test_advisory_only(self):
        graph = {"objective": "test", "files": ["f1.py"], "symbols": ["s1"], "tests": []}
        result = detect_refactor_candidates(graph, repo_root=REPO_ROOT)
        assert result["advisory_only"] is True

    def test_cannot_patch_without_grounding(self):
        c = {"candidate_id": "C1", "current_evidence": [], "missing_evidence": ["grounding_ok"]}
        result = candidate_to_grounding_requirement(c)
        assert result["can_patch"] is False

    def test_invariants(self):
        graph = {"objective": "test", "files": ["f1.py"], "symbols": ["s1"]}
        result = detect_refactor_candidates(graph, repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY

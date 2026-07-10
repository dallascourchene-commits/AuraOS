"""Tests for Aura Coding Research Lane."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_coding_research_lane import search_research_manifest, build_research_evidence_packet, PATCH_AUTHORITY


class TestResearchLane:
    def test_offline_search(self):
        result = search_research_manifest("agentless", repo_root=REPO_ROOT, offline=True)
        assert result["ok"] is True
        assert result.get("offline", True) is True

    def test_evidence_advisory(self):
        result = build_research_evidence_packet("test", repo_root=REPO_ROOT, offline=True)
        assert result.get("advisory_only", True) is True

    def test_invariants(self):
        result = search_research_manifest("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY

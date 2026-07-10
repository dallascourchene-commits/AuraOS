"""Tests for Aura Change Graph."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_change_graph import build_change_graph, change_graph_to_act_capsules, change_graph_to_review_packet, PATCH_AUTHORITY


class TestChangeGraph:
    def test_build(self):
        result = build_change_graph("test", {"files": ["f1.py"], "symbols": ["s1"]}, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "graph_id" in result
        assert "files" in result
        assert "symbols" in result

    def test_to_act_capsules(self):
        g = build_change_graph("test", {"files": ["f1.py"]}, repo_root=REPO_ROOT)
        result = change_graph_to_act_capsules(g)
        assert result["ok"] is True
        assert len(result["act_capsules"]) > 0

    def test_to_review_packet(self):
        g = build_change_graph("test", {"files": ["f1.py"]}, repo_root=REPO_ROOT)
        result = change_graph_to_review_packet(g)
        assert result["ok"] is True
        assert "review_packet" in result

    def test_invariants(self):
        g = build_change_graph("test", repo_root=REPO_ROOT)
        assert g["patch_authority"] == PATCH_AUTHORITY

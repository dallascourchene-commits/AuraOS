"""Tests for Aura Topology Health."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_topology_health import (
    check_codemap_health, topology_health_packet, detect_topology_regression,
    suggest_topology_repair, PATCH_AUTHORITY,
)


class TestTopologyHealth:
    def test_codemap_health(self):
        result = check_codemap_health(repo_root=REPO_ROOT)
        assert "topology_nodes" in result
        assert "symbol_index_count" in result
        assert result["patch_authority"] == PATCH_AUTHORITY

    def test_health_packet(self):
        result = topology_health_packet(repo_root=REPO_ROOT)
        assert "ok" in result
        assert "topology_nodes" in result
        assert "next_gate" in result
        assert result["patch_authority"] == PATCH_AUTHORITY

    def test_detects_zero_node_topology(self):
        result = topology_health_packet(repo_root=REPO_ROOT)
        # Current CODEMAP has 0 topology nodes
        assert result["topology_nodes"] == 0
        assert result["next_gate"] == "NEED_TOPOLOGY_REPAIR"
        assert "topology" in result.get("missing_topology_reason", "").lower()

    def test_regression_detected(self):
        result = detect_topology_regression(repo_root=REPO_ROOT)
        assert result["regression_detected"] is True

    def test_repair_suggestion(self):
        result = suggest_topology_repair(repo_root=REPO_ROOT)
        assert len(result["repair_command_suggestion"]) > 0

    def test_symbol_index_healthy(self):
        result = topology_health_packet(repo_root=REPO_ROOT)
        assert result["symbol_index_count"] > 0

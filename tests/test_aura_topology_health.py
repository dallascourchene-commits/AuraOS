"""Tests for Aura Topology Health."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_topology_health import (
    check_codemap_health, topology_health_packet, detect_topology_regression,
    suggest_topology_repair, PATCH_AUTHORITY,
)


@pytest.fixture
def mock_healthy_codemap():
    """Mock CODEMAP with healthy topology."""
    return {
        "coverage": {"included_file_count": 50},
        "topology": {
            "source": "test_topology",
            "file_index": {"file1.py": {"degree": 2}, "file2.py": {"degree": 1}},
        },
        "summary": {
            "topology_nodes": 100,
            "topology_edges": 99,
            "topology_source": "test_topology",
        },
        "symbol_index": {
            "test_func": [{"file": "file1.py", "line": 10, "end_line": 20}],
            "test_class": [{"file": "file2.py", "line": 5, "end_line": 30}],
        },
        "command_index": {"test_cmd": ["cmd1"]},
    }


@pytest.fixture
def mock_zero_node_codemap():
    """Mock CODEMAP with zero nodes."""
    return {
        "coverage": {"included_file_count": 10},
        "topology": {"source": "empty_topology", "file_index": {}},
        "summary": {
            "topology_nodes": 0,
            "topology_edges": 0,
            "topology_source": "empty_topology",
        },
        "symbol_index": {"test_func": [{"file": "file1.py", "line": 10}]},
        "command_index": {},
    }


@pytest.fixture
def mock_regression_baseline():
    """Mock regression baseline data."""
    return {
        "topology_nodes": 100,
        "topology_edges": 99,
        "topology_source": "baseline_topology",
    }


class TestTopologyHealth:
    def test_codemap_health(self, mock_healthy_codemap):
        with patch("aura_topology_health._load_codemap", return_value=mock_healthy_codemap):
            result = check_codemap_health(repo_root=REPO_ROOT)
            assert "topology_nodes" in result
            assert "symbol_index_count" in result
            assert result["patch_authority"] == PATCH_AUTHORITY
            assert result["topology_nodes"] == 100
            assert result["symbol_index_count"] == 2

    def test_health_packet(self, mock_healthy_codemap):
        with patch("aura_topology_health._load_codemap", return_value=mock_healthy_codemap):
            result = topology_health_packet(repo_root=REPO_ROOT)
            assert "ok" in result
            assert "topology_nodes" in result
            assert "next_gate" in result
            assert result["patch_authority"] == PATCH_AUTHORITY

    def test_detects_zero_node_topology(self, mock_zero_node_codemap):
        with patch("aura_topology_health._load_codemap", return_value=mock_zero_node_codemap):
            result = topology_health_packet(repo_root=REPO_ROOT)
            # Mock CODEMAP has 0 topology nodes
            assert result["topology_nodes"] == 0
            assert result["next_gate"] == "NEED_TOPOLOGY_REPAIR"
            assert "topology" in result.get("missing_topology_reason", "").lower()

    def test_regression_detected(self, mock_zero_node_codemap, mock_regression_baseline):
        with patch("aura_topology_health._load_codemap", return_value=mock_zero_node_codemap):
            result = detect_topology_regression(previous=mock_regression_baseline, repo_root=REPO_ROOT)
            assert result["regression_detected"] is True
            assert result["baseline_available"] is True

    def test_regression_no_baseline(self, mock_healthy_codemap):
        with patch("aura_topology_health._load_codemap", return_value=mock_healthy_codemap):
            result = detect_topology_regression(repo_root=REPO_ROOT)
            # No baseline file → uses default baseline; healthy topology = no regression
            assert result["regression_detected"] is False

    def test_repair_suggestion(self, mock_zero_node_codemap):
        with patch("aura_topology_health._load_codemap", return_value=mock_zero_node_codemap):
            result = suggest_topology_repair(repo_root=REPO_ROOT)
            assert len(result["repair_command_suggestion"]) > 0

    def test_symbol_index_healthy(self, mock_healthy_codemap):
        with patch("aura_topology_health._load_codemap", return_value=mock_healthy_codemap):
            result = topology_health_packet(repo_root=REPO_ROOT)
            assert result["symbol_index_count"] > 0

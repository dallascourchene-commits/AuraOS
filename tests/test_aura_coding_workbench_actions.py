"""Tests for Aura Coding Workbench Actions."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_coding_workbench_actions import (
    open_workspace, scope_task, localize_code, rank_code_regions, slice_context,
    build_change_graph, detect_refactor_candidates, split_work, prepare_agent_handoff,
    PATCH_AUTHORITY,
)


class TestActions:
    def test_open_workspace(self):
        result = open_workspace(repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "topology_health" in result

    def test_scope_task(self):
        result = scope_task("Refactor routing", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["next_gate"] == "TASK_SCOPED"

    def test_localize_code(self):
        result = localize_code("refactor fireworks", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "localized_files" in result

    def test_rank_code_regions(self):
        result = rank_code_regions("refactor fireworks", repo_root=REPO_ROOT, max_lines=100)
        assert result["ok"] is True
        assert result["total_lines_selected"] <= 100

    def test_slice_context(self):
        loc = {"localized_files": ["f1.py"], "localized_symbols": ["sym1"]}
        result = slice_context(loc, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "sliced_files" in result

    def test_build_change_graph_blocks_on_degraded_topology(self):
        from unittest.mock import patch
        with patch("aura_topology_health.topology_health_packet") as mock_health:
            mock_health.return_value = {"topology_nodes": 0}
            result = build_change_graph("test", repo_root=REPO_ROOT)
            # Topology is degraded (0 nodes) so this should block
            assert result["ok"] is False
            assert result.get("next_gate") == "NEED_TOPOLOGY_REPAIR"

    def test_detect_refactor_candidates(self):
        graph = {"objective": "test", "files": ["f1.py"], "symbols": ["sym1"], "tests": []}
        result = detect_refactor_candidates(graph, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["advisory_only"] is True

    def test_split_work(self):
        result = split_work("Do A. Do B.", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["child_tasks"]) > 0

    def test_prepare_agent_handoff(self):
        result = prepare_agent_handoff("C1", agent="hermes", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["human_approval_required"] is True

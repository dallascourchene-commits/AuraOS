"""Tests for Aura Coding Workbench Sequence."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_coding_workbench_sequence import (
    WorkbenchState, GATE_DEFINITIONS, get_gate, can_transition, workbench_state_machine,
    PATCH_AUTHORITY,
)


class TestWorkbenchSequence:
    def test_has_18_states(self):
        assert len(list(WorkbenchState)) == 18

    def test_all_states_have_gates(self):
        assert len(GATE_DEFINITIONS) == 18

    def test_sequential_transition(self):
        assert can_transition(WorkbenchState.WORKSPACE_OPENED, WorkbenchState.TASK_SCOPED) is True

    def test_skip_blocked(self):
        assert can_transition(WorkbenchState.WORKSPACE_OPENED, WorkbenchState.PATCH_STAGED) is False

    def test_needs_topology_repair_blocks_graph(self):
        gate = get_gate(WorkbenchState.NEED_TOPOLOGY_REPAIR)
        assert "build_change_graph" in gate.blocked_actions

    def test_human_review_required(self):
        gate = get_gate(WorkbenchState.HUMAN_REVIEW_REQUIRED)
        assert gate.human_approval_required is True

    def test_state_machine_packet(self):
        result = workbench_state_machine()
        assert result["ok"] is True
        assert result["state_count"] == 18
        assert result["patch_authority"] == PATCH_AUTHORITY

"""Tests for Aura Cockpit Planner."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_cockpit_planner import (
    plan_objective_with_goap, objective_to_phase_capsules,
    phase_capsules_to_workflow_gates, phase_capsules_to_agent_runbook,
    PATCH_AUTHORITY,
)


class TestGOAPPlan:
    def test_produces_phases(self):
        result = plan_objective_with_goap("Refactor Fireworks egress", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["plan"]["phases"]) == 9

    def test_phase_has_required_fields(self):
        result = plan_objective_with_goap("test", repo_root=REPO_ROOT)
        for phase in result["plan"]["phases"]:
            assert "allowed_actions" in phase
            assert "blocked_actions" in phase
            assert "human_approval_required" in phase

    def test_invariants(self):
        result = plan_objective_with_goap("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestPhaseCapsules:
    def test_produces_capsules(self):
        result = objective_to_phase_capsules("test", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["phase_capsules"]) == 9


class TestWorkflowGates:
    def test_mapping(self):
        capsules = objective_to_phase_capsules("test", repo_root=REPO_ROOT)
        result = phase_capsules_to_workflow_gates(capsules["phase_capsules"], repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["gate_mapping"]) == 9


class TestRunbook:
    def test_produces_runbook(self):
        capsules = objective_to_phase_capsules("test", repo_root=REPO_ROOT)
        result = phase_capsules_to_agent_runbook(capsules["phase_capsules"], repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["runbook"]) > 0

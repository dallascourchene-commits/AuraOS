"""Tests for Aura Cockpit Swarm."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_cockpit_swarm import (
    build_swarm_plan, assign_agent_roles, agent_lane_compatibility,
    swarm_plan_to_agent_handoffs, PATCH_AUTHORITY,
)


class TestSwarmPlan:
    def test_builds_plan(self):
        result = build_swarm_plan("test objective", agents=["hermes", "codex"])
        assert result["ok"] is True
        plan = result["swarm_plan"]
        assert "hermes" in plan["agents"]
        assert "codex" in plan["agents"]
        assert len(plan["assignments"]) == 2

    def test_no_execution_note(self):
        result = build_swarm_plan("test")
        assert "no worker executes" in result["note"].lower()

    def test_token_budgets(self):
        result = build_swarm_plan("test", agents=["hermes", "codex"])
        budgets = result["swarm_plan"]["token_budgets"]
        assert "hermes" in budgets
        assert "codex" in budgets

    def test_invariants(self):
        result = build_swarm_plan("test")
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestAgentRoles:
    def test_assign(self):
        result = assign_agent_roles("test", ["hermes", "codex"])
        assert result["ok"] is True
        assert len(result["assignments"]) == 2


class TestLaneCompatibility:
    def test_hermes(self):
        result = agent_lane_compatibility("hermes")
        assert result["ok"] is True
        assert len(result["compatible_lanes"]) > 0


class TestHandoffs:
    def test_convert(self):
        plan = build_swarm_plan("test", agents=["hermes"])
        result = swarm_plan_to_agent_handoffs(plan["swarm_plan"])
        assert result["ok"] is True
        assert len(result["handoffs"]) == 1
        assert result["handoffs"][0]["human_approval_required"] is True

"""Tests for Aura Agent Workbench Interface."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_agent_workbench_interface import list_agent_actions, agent_workbench_contract, execute_workbench_action, PATCH_AUTHORITY


class TestWorkbenchInterface:
    def test_list_actions(self):
        actions = list_agent_actions()
        assert len(actions) == 15
        names = [a["name"] for a in actions]
        assert "search_code" in names
        assert "stage_patch" in names
        assert "prepare_pr" in names

    def test_contract(self):
        result = agent_workbench_contract("hermes")
        assert result["ok"] is True
        assert result["agent"] == "hermes"
        assert len(result["rules"]) > 0

    def test_execute_known_action(self):
        result = execute_workbench_action("search_code", {"query": "test"})
        assert result["ok"] is True

    def test_execute_unknown_action(self):
        result = execute_workbench_action("unknown_action")
        assert result["ok"] is False

    def test_invariants(self):
        result = agent_workbench_contract()
        assert result["patch_authority"] == PATCH_AUTHORITY

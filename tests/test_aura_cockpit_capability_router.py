"""Tests for Aura Cockpit Capability Router."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_cockpit_capability_router import route_capability_lanes, PATCH_AUTHORITY


class TestRouter:
    def test_research_routing(self):
        result = route_capability_lanes("research this approach before refactor")
        selected = [l["lane_id"] for l in result["selected_lanes"]]
        assert "research_arxiv_lane" in selected

    def test_split_routing(self):
        result = route_capability_lanes("split this huge refactor into smaller PRs")
        selected = [l["lane_id"] for l in result["selected_lanes"]]
        assert "mitosis_decomposition_lane" in selected

    def test_skill_routing(self):
        result = route_capability_lanes("find skills Aura already has for this")
        selected = [l["lane_id"] for l in result["selected_lanes"]]
        assert "skillweaver_lane" in selected

    def test_swarm_routing(self):
        result = route_capability_lanes("coordinate Hermes and Codex")
        selected = [l["lane_id"] for l in result["selected_lanes"]]
        assert "mesh_swarm_lane" in selected

    def test_test_routing(self):
        result = route_capability_lanes("what tests prove this")
        selected = [l["lane_id"] for l in result["selected_lanes"]]
        assert "resonant_test_oracle_lane" in selected

    def test_default_lanes_included(self):
        result = route_capability_lanes("simple objective")
        selected = [l["lane_id"] for l in result["selected_lanes"]]
        assert "goap_planner_lane" in selected
        assert "audit_staking_lane" in selected

    def test_rejected_lanes(self):
        result = route_capability_lanes("test objective")
        assert len(result["rejected_lanes"]) > 0

    def test_invariants(self):
        result = route_capability_lanes("test")
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False

    def test_advisory_layers_listed(self):
        result = route_capability_lanes("research approach")
        assert isinstance(result["advisory_layers"], list)

"""Tests for Aura Capability Lane Registry."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_capability_lane_registry import (
    load_capability_lanes, get_lane, list_lane_ids, lane_registry_packet, explain_lane,
    PATCH_AUTHORITY, VSA_PATCH_AUTHORITY,
)


class TestLaneRegistry:
    def test_has_17_lanes(self):
        lanes = load_capability_lanes()
        assert len(lanes) == 17

    def test_includes_all_required_lanes(self):
        ids = set(list_lane_ids())
        required = {"music_coding_lane", "mitosis_decomposition_lane", "research_arxiv_lane",
                     "skillweaver_lane", "mesh_swarm_lane", "mcp_gateway_lane", "plugin_registry_lane",
                     "goap_planner_lane", "live_architect_lane", "associative_core_lane",
                     "phase_capsule_lane", "audit_staking_lane", "federation_lane",
                     "empirical_lab_lane", "resonant_test_oracle_lane",
                     "symbolic_trace_memory_lane", "module_manifest_lane"}
        assert required.issubset(ids), f"Missing: {required - ids}"

    def test_all_lanes_have_patch_authority(self):
        for lane in load_capability_lanes():
            assert lane.patch_authority == PATCH_AUTHORITY
            assert lane.vsa_patch_authority is VSA_PATCH_AUTHORITY

    def test_lane_registry_packet(self):
        result = lane_registry_packet()
        assert result["ok"] is True
        assert result["lane_count"] == 17
        assert result["patch_authority"] == PATCH_AUTHORITY

    def test_get_lane(self):
        lane = get_lane("music_coding_lane")
        assert lane is not None
        assert lane.name == "MUSIC Coding Arena"

    def test_get_lane_not_found(self):
        assert get_lane("nonexistent") is None

    def test_explain_lane(self):
        result = explain_lane("goap_planner_lane")
        assert result["ok"] is True
        assert "lane" in result

    def test_all_advisory_only(self):
        for lane in load_capability_lanes():
            assert lane.advisory_only is True

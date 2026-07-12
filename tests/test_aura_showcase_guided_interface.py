"""Contracts for the presenter-friendly Winnipeg showcase interface."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def isolated_civic_runtime(monkeypatch):
    import aura_civic_runtime as runtime

    monkeypatch.setattr(runtime, "_store_instance", "IN_MEMORY_ONLY")
    monkeypatch.setattr(runtime, "_ephemeral_store_instance", "IN_MEMORY_ONLY")
    runtime._sessions.clear()
    yield
    runtime._sessions.clear()


def _advance_to(session_id: str, step_id: str):
    from aura_civic_guided_project import advance_project, get_guide

    guide = get_guide(session_id)
    while guide["current_step"]["step_id"] != step_id:
        guide = advance_project(session_id)
        assert guide["ok"] is True, json.dumps(guide, indent=2, default=str)
    return guide


def test_every_guided_gate_exposes_ranked_inspectable_actions():
    from aura_civic_guided_project import advance_project, start_project

    guide = start_project("winnipeg_pathways")
    while True:
        actions = guide["available_actions"]
        assert actions
        weights = [action["route_weight"] for action in actions]
        assert weights == sorted(weights, reverse=True)
        assert all(0 <= weight <= 1 for weight in weights)
        for action in actions:
            assert set(action["intent_slots"]) == {"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"}
            assert action["binding"] is False
            assert action["why_available"]
        assert guide["route_notice"].startswith("Route weights rank deterministic")
        blocked_ids = {item["action_id"] for item in guide["blocked_actions"]}
        assert {"BINDING_VOTE", "ALLOCATE_FUNDS", "MAP_VULNERABLE_PEOPLE", "AUTO_SUBMIT"} <= blocked_ids
        if not guide["can_advance"]:
            break
        guide = advance_project(guide["session"]["session_id"])
        assert guide["ok"] is True


def test_map_gate_offers_test_community_candidate_and_handoff_actions():
    from aura_civic_guided_project import start_project

    guide = start_project("winnipeg_pathways")
    guide = _advance_to(guide["session"]["session_id"], "EXPLORE_MAP")
    by_effect = {action["effect"]: action for action in guide["available_actions"]}
    assert "FOCUS_TEST_COMMUNITY" in by_effect
    assert by_effect["FOCUS_TEST_COMMUNITY"]["args"]["zoom"] == 14
    assert "REVEAL_CANDIDATE" in by_effect
    assert by_effect["REVEAL_CANDIDATE"]["args"]["zoom"] == 12
    assert "PREFILL_RESPONSE" in by_effect
    assert "OPEN_HANDOFF" in by_effect


def test_fixture_contains_synthetic_west_broadway_overlay():
    from aura_civic_winnipeg_fixture import TRUTH_SYNTHETIC, winnipeg_pathways_fixtures

    fixture = winnipeg_pathways_fixtures()
    features = {feature["properties"]["feature_id"]: feature for feature in fixture["geojson"]["features"]}
    community = features["WP-TEST-COMMUNITY"]
    assert community["geometry"]["type"] == "Polygon"
    assert community["properties"]["type"] == "neighbourhood"
    assert community["properties"]["truth_class"] == TRUTH_SYNTHETIC
    assert "Synthetic Test Community" in community["properties"]["name"]
    assert fixture["basemap"]["provider"] == "OpenStreetMap"
    assert fixture["basemap"]["network_optional"] is True
    assert fixture["basemap"]["offline_fallback"]


def test_browser_assets_disclose_basemap_and_render_weighted_menu():
    index = (REPO_ROOT / "aura_showcase" / "index.html").read_text(encoding="utf-8")
    civic = (REPO_ROOT / "aura_showcase" / "civic.js").read_text(encoding="utf-8")
    assert 'id="route-actions"' in index
    assert 'id="basemap-tiles"' in index
    assert "OpenStreetMap contributors" in index
    assert "tile.openstreetmap.org/{z}/{x}/{y}.png" in civic
    assert "navigator.onLine" in civic
    assert "MAP_VULNERABLE_PEOPLE" not in civic

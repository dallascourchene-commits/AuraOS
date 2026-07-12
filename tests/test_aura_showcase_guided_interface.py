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


def test_human_agent_state_projects_exact_wfst_recommendations_and_blocks():
    from aura_human_agent_workflow import HumanAgentWorkflow

    workflow = HumanAgentWorkflow(REPO_ROOT)
    try:
        objective = "Investigate a grounded Winnipeg map presentation issue."
        workflow.objective = objective
        workflow.evidence.update({
            "objective": objective,
            "grounding": {"truth_class": "EXACT_REPOSITORY_FACTS"},
        })
        plan_state = workflow.get_state()
        assert plan_state["current_phase"] == "PLAN"
        assert plan_state["grammar_version"] == "human-agent-wfst-v1"
        ranked_actions = [item for item in plan_state["available"] if not item.get("meta_transition")]
        assert ranked_actions[0]["transition_id"] == "HUMAN.PREPARE_CAPSULE"
        assert ranked_actions[0]["provenance"]["action_id"] == "prepare_capsule"
        assert set(ranked_actions[0]["rank"]) >= {
            "unresolved_risk",
            "declared_evidence_gap",
            "empirical_uncertainty",
            "semantic_ambiguity",
            "negative_user_fit",
        }

        workflow.evidence.update({
            "plan_phase_hash": "plan-hash",
            "act_capsules": [{"capsule_id": "CAP-1"}],
        })
        act_state = workflow.get_state()
        assert act_state["current_phase"] == "ACT"
        blocked = {item["transition_id"]: item for item in act_state["blocked"]}
        assert "HUMAN.STAGE_PATCH" in blocked
        assert {"candidate_diff", "affected_files"} <= set(blocked["HUMAN.STAGE_PATCH"]["missing_evidence"])
        assert blocked["HUMAN.STAGE_PATCH"]["fail_closed"] is True
    finally:
        workflow.close()


def test_showcase_status_discloses_optional_basemap_network_access():
    from aura_showcase_server import dispatch_showcase_request

    class FakeState:
        default_session_id = ""
        demo_project = "winnipeg_pathways"

    status, _, raw = dispatch_showcase_request(FakeState(), "GET", "/api/showcase/status")
    payload = json.loads(raw)
    assert status == 200
    assert payload["zero_raw_civic_data_network_calls"] is True
    assert payload["optional_public_basemap_network_calls"] is True
    assert payload["basemap_provider"].startswith("OpenStreetMap")
    assert "zero_raw_network_calls" not in payload


def test_browser_assets_disclose_basemap_and_render_both_guided_menus():
    index = (REPO_ROOT / "aura_showcase" / "index.html").read_text(encoding="utf-8")
    civic = (REPO_ROOT / "aura_showcase" / "civic.js").read_text(encoding="utf-8")
    human = (REPO_ROOT / "aura_showcase" / "human.js").read_text(encoding="utf-8")
    assert 'id="route-actions"' in index
    assert 'id="basemap-tiles"' in index
    assert 'id="human-recommended-actions"' in index
    assert 'id="human-blocked-actions"' in index
    assert "OpenStreetMap contributors" in index
    assert "tile.openstreetmap.org/{z}/{x}/{y}.png" in civic
    assert "navigator.onLine" in civic
    assert "rankVector" in human
    assert "failed_guards" in human
    assert "workflow.available" in human
    assert "MAP_VULNERABLE_PEOPLE" not in civic

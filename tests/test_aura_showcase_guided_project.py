"""Focused contracts for the Winnipeg Civic + Human Agent showcase."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
        assert guide["can_advance"] is True
        guide = advance_project(session_id)
        assert guide["ok"] is True, json.dumps(guide, indent=2, default=str)
    return guide


def test_project_registry_includes_winnipeg_pathways():
    from aura_civic_projects import get_project, list_projects

    listing = list_projects()
    ids = {item["project_id"] for item in listing["projects"]}
    assert "winnipeg_pathways" in ids
    project = get_project("winnipeg_pathways")
    assert project.jurisdiction_id == "winnipeg_mb_ca"
    assert "no_person_level_vulnerability_mapping" in project.mandatory_constraints
    assert project.demo_issue["human_review_required"] is True


def test_legacy_projects_use_the_defined_explore_map_step():
    from aura_civic_projects import list_projects

    projects = {item["project_id"]: item for item in list_projects()["projects"]}
    for project_id in ("hairstylist", "youth_centre", "council_pulse"):
        assert "EXPLORE_MAP" in projects[project_id]["guided_steps"]
        assert "EXPLORE" not in projects[project_id]["guided_steps"]


def test_unknown_project_returns_structured_failure():
    from aura_civic_guided_project import start_project
    from aura_civic_projects import get_project

    lookup = get_project("missing-project")
    assert lookup["ok"] is False
    assert lookup["error"] == "unknown_civic_project"
    result = start_project("missing-project")
    assert result == lookup


def test_winnipeg_fixture_is_synthetic_and_uses_safe_aggregate_heatmap():
    from aura_civic_map import PROHIBITED_HEATMAPS, SAFE_HEATMAP_SIGNALS, validate_heatmap
    from aura_civic_projects import TRUTH_SYNTHETIC, winnipeg_pathways_fixtures

    fixtures = winnipeg_pathways_fixtures()
    assert fixtures["heatmap"]["metric"] in SAFE_HEATMAP_SIGNALS
    assert fixtures["heatmap"]["metric"] not in PROHIBITED_HEATMAPS
    assert validate_heatmap(fixtures["heatmap"])["ok"] is True
    assert fixtures["heatmap"]["truth_class"] == TRUTH_SYNTHETIC
    assert all(item["truth_class"] == TRUTH_SYNTHETIC for item in fixtures["needs"])
    assert all(item["truth_class"] == TRUTH_SYNTHETIC for item in fixtures["offers"])
    assert all(item["truth_class"] == TRUTH_SYNTHETIC for item in fixtures["scenarios"])
    serialized = json.dumps(fixtures).lower()
    assert '"person_level_homelessness"' not in serialized
    assert '"person_level_addiction"' not in serialized
    assert '"indigenous_identity"' not in serialized


def test_guided_project_starts_non_binding_and_context_is_not_identity_inferred():
    from aura_civic_guided_project import start_project

    guide = start_project("winnipeg_pathways")
    assert guide["ok"] is True
    assert guide["current_step"]["step_id"] == "WELCOME"
    assert guide["project"]["non_binding"] is True
    assert guide["vsa_patch_authority"] is False
    profile_set = guide["session"]["profile_set"]
    assert "winnipeg_mb_ca" in profile_set["jurisdiction_profile_refs"]
    assert "treaty1_context" not in profile_set.get("context_lens_refs", [])


def test_candidate_is_hidden_at_11_and_visible_at_12():
    from aura_civic_guided_project import project_map, start_project

    guide = start_project("winnipeg_pathways")
    session_id = guide["session"]["session_id"]
    guide = _advance_to(session_id, "EXPLORE_MAP")
    assert guide["demo_issue_available"] is True

    zoom_11 = project_map(session_id, zoom=11)
    zoom_12 = project_map(session_id, zoom=12)
    assert zoom_11["ok"] is True
    assert zoom_12["ok"] is True
    ids_11 = {feature["properties"]["feature_id"] for feature in zoom_11["geojson"]["features"]}
    ids_12 = {feature["properties"]["feature_id"] for feature in zoom_12["geojson"]["features"]}
    assert "WP-CANDIDATE-1" not in ids_11
    assert "WP-CANDIDATE-1" in ids_12
    assert zoom_11["suppressed_counts"]["zoom"] >= 1
    assert zoom_12["jurisdiction_id"] == "winnipeg_mb_ca"
    assert zoom_12["accessible_table_parity"] is True


def test_guided_organs_preserve_receipts_and_no_hidden_winner():
    from aura_civic_guided_project import start_project

    guide = start_project("winnipeg_pathways")
    session_id = guide["session"]["session_id"]
    guide = _advance_to(session_id, "COMPARE_SCENARIOS")
    assert guide["summary"]["workstream_count"] > 0
    assert guide["summary"]["scenario_count"] > 0
    assert guide["summary"]["organ_receipt_count"] >= 6
    comparison_text = json.dumps(guide["session"].get("music_comparison", {})).lower()
    assert '"winner"' not in comparison_text


def test_response_preserves_reservation_without_binding_vote():
    from aura_civic_guided_project import record_response, start_project

    guide = start_project("winnipeg_pathways")
    session_id = guide["session"]["session_id"]
    result = record_response(session_id, {
        "response_type": "CONSENT_WITH_RESERVATION",
        "statement": "Evening transportation must be resolved before a pilot starts.",
    })
    assert result["ok"] is True
    import aura_civic_runtime as runtime
    session = runtime.get_session(session_id)["session"]
    assert session["consent_responses"][0]["binding"] is False
    assert "vote_cast" not in json.dumps(session).lower()


def test_concurrent_responses_are_serialized_without_lost_updates():
    from aura_civic_guided_project import record_response, start_project
    import aura_civic_runtime as runtime

    guide = start_project("winnipeg_pathways")
    session_id = guide["session"]["session_id"]
    statements = [f"community-response-{index}" for index in range(16)]

    def submit(statement: str):
        return record_response(session_id, {
            "response_type": "CONSENT_WITH_RESERVATION",
            "statement": statement,
        })

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(submit, statements))

    assert all(result["ok"] is True for result in results)
    session = runtime.get_session(session_id)["session"]
    recorded = {item["statement"] for item in session["guide_responses"]}
    consent_recorded = {item["statement"] for item in session["consent_responses"]}
    assert recorded == set(statements)
    assert consent_recorded == set(statements)


def test_handoff_packet_uses_exact_files_and_never_mutates_production():
    from aura_civic_guided_project import start_project
    from aura_showcase_handoff import build_handoff_packet

    guide = start_project("winnipeg_pathways")
    session_id = guide["session"]["session_id"]
    packet = build_handoff_packet(REPO_ROOT, session_id)
    assert packet["ok"] is True, packet
    assert packet["grounding"]["grounding"] == "grounded"
    assert packet["grounding"]["source_hashes"]
    assert packet["test_targets"] == ["tests/test_aura_showcase_guided_project.py"]
    assert packet["production_mutation"] is False
    assert packet["automatic_commit"] is False
    assert packet["automatic_push"] is False
    assert packet["automatic_merge"] is False
    assert "CANDIDATE_FOCUS_ZOOM" in packet["candidate_diff"]


def test_handoff_imports_exact_evidence_into_guarded_workflow():
    from aura_civic_guided_project import start_project
    from aura_human_agent_workflow import HumanAgentWorkflow
    from aura_showcase_handoff import import_handoff_into_workflow

    guide = start_project("winnipeg_pathways")
    session_id = guide["session"]["session_id"]
    workflow = HumanAgentWorkflow(REPO_ROOT)
    try:
        result = import_handoff_into_workflow(workflow, REPO_ROOT, session_id)
        assert result["ok"] is True, result
        assert workflow.objective.startswith("Investigate why the Winnipeg Pathways")
        assert workflow.evidence["grounding"]["truth_class"] == "EXACT_REPOSITORY_FACTS"
        assert "aura_showcase/app.js" in workflow.evidence["affected_files"]
        assert workflow.evidence["test_targets"] == ["tests/test_aura_showcase_guided_project.py"]
        assert "CANDIDATE_FOCUS_ZOOM" in workflow.evidence["candidate_diff"]
        assert result["handoff"]["automatic_merge"] is False
    finally:
        workflow.close()


def test_showcase_dispatch_lists_and_starts_projects():
    from aura_showcase_server import dispatch_showcase_request

    class FakeState:
        demo_project = "winnipeg_pathways"
        default_session_id = ""

    state = FakeState()
    status, content_type, raw = dispatch_showcase_request(state, "GET", "/api/showcase/projects")
    assert status == 200
    assert content_type.startswith("application/json")
    payload = json.loads(raw)
    assert payload["ok"] is True

    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/projects/winnipeg_pathways/start",
        {},
    )
    started = json.loads(raw)
    assert status == 200
    assert started["ok"] is True
    assert state.default_session_id == started["session"]["session_id"]

    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/projects/missing-project/start",
        {},
    )
    rejected = json.loads(raw)
    assert status == 400
    assert rejected["ok"] is False
    assert rejected["error"] == "unknown_civic_project"

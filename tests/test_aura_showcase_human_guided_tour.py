"""Static contracts for the Human Agent guided workspace and Observatory navigation."""
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_human_agent_arena_has_optional_real_workflow_tour():
    human = (REPO_ROOT / "aura_showcase" / "human.js").read_text(encoding="utf-8")

    assert "HUMAN_STAGE_COUNT = 7" in human
    assert "INTAKE" in human
    assert "FRAME" in human
    assert "GROUND" in human
    assert "PLAN" in human
    assert "ACT" in human
    assert "PROVE" in human
    assert "DECIDE" in human
    assert "Start suggested demo" in human
    assert "Exit tour" in human
    assert "View complete workspace" in human
    assert "Free workspace mode" in human


def test_human_tour_calls_existing_guarded_workflow_actions():
    human = (REPO_ROOT / "aura_showcase" / "human.js").read_text(encoding="utf-8")

    for action_id in (
        "set_objective",
        "ground_context",
        "prepare_capsule",
        "stage_patch",
        "run_tests",
        "verify_patch",
        "check_hotswap",
        "human_review",
        "export_handoff",
    ):
        assert f"runAction('{action_id}'" in human

    assert "/api/human-agent/workflow/action" in human
    assert "candidate_diff" in human
    assert "affected_files" in human
    assert "test_targets" in human
    assert "approved: false" in human
    assert "No merge requested" in human


def test_human_tour_preserves_free_exploration_and_authority_boundaries():
    human = (REPO_ROOT / "aura_showcase" / "human.js").read_text(encoding="utf-8")

    assert "S.humanWorkspace.tourActive" in human
    assert "S.humanWorkspace.overviewActive" in human
    assert "Agent output remains a proposal" in human
    assert "production will not be mutated" in human
    assert "automatic merge blocked" in human
    assert "Open Aura Observatory" in human
    assert "Open Learning Arena" in human


def test_observatory_next_button_compiles_then_advances_reliably():
    human = (REPO_ROOT / "aura_showcase" / "human.js").read_text(encoding="utf-8")

    assert "installObservatoryNavigationRepair" in human
    assert "Compile and show lexical addresses" in human
    assert "await S.compileIntent?.()" in human
    assert "S.showLearningStage(1)" in human
    assert "event.stopImmediatePropagation()" in human
    assert "document.addEventListener('click'" in human
    assert "$('bulk-intent-input')?.addEventListener('input', syncNextButton)" in human

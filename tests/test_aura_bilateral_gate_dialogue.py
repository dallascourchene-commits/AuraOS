"""Focused PR2 proof for bilateral Gate Dialogue compilation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_CONTEXT = {
    "task_id": "civic_map_overlay",
    "selected_node": {
        "id": "node:aura_showcase/civic.js:refreshMap",
        "label": "refreshMap",
        "file_path": "aura_showcase/civic.js",
        "symbol": "refreshMap",
        "node_type": "function",
        "line_range": [120, 180],
        "projection_truth": "EXACT_TOPOLOGY",
    },
    "dependencies": ["project_map_manifest", "drawMap"],
    "callers": ["renderCivicGuide"],
    "tests": ["tests/test_aura_showcase_guided_interface.py"],
}


@pytest.fixture
def workflow():
    from aura_human_agent_workflow import HumanAgentWorkflow

    item = HumanAgentWorkflow(REPO_ROOT)
    try:
        yield item
    finally:
        item.close()


def test_strict_refinement_requires_clarification_and_compiles(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService, BILATERAL_MARKER

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment=f"{BILATERAL_MARKER} Keep the selected renderer calibrated.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert proposal["status"] == "CLARIFICATION_REQUIRED"
    assert proposal["can_confirm_intent"] is False

    clarified = service.address(
        comment=(
            f"[AURA_CLARIFICATION_ANSWER:{proposal['proposal_id']}] "
            "Do not widen the selected file scope or mutate canonical geometry."
        ),
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert clarified["status"] == "PENDING_HUMAN_APPROVAL"
    assert clarified["can_confirm_intent"] is True
    assert clarified["paired_teach_back"]["will_do"]
    assert clarified["paired_teach_back"]["will_not_do"]

    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="test_human",
    )
    assert approved["ok"] is True
    compilation = approved["canonical_compilation"]
    assert compilation["intent_packet"]["mode"] == "PROPOSE"
    assert compilation["intent_packet"]["authority"]["edit"] is False
    assert compilation["semantic_ledger"]["intent_digest"] == compilation["intent_packet"]["intent_digest"]
    assert compilation["confirmation_receipt"]["human_disposition"] == "CONFIRMED"
    assert compilation["refinement_session"]["current_stage"] == "COMPILED"
    assert compilation["u7_references"]["current_reproof_required_before_learning"] is True
    assert approved["production_mutation"] is False
    assert approved["automatic_merge"] is False
    assert workflow.objective == ""


def test_refinement_fails_closed_for_missing_answer_or_stale_node(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService, BILATERAL_MARKER

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment=f"{BILATERAL_MARKER} Explain the selected node.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    denied = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
    )
    assert denied["reason"] == "clarification_required"

    changed = {
        **NODE_CONTEXT,
        "selected_node": {**NODE_CONTEXT["selected_node"], "symbol": "drawMap"},
    }
    stale = service.address(
        comment=f"[AURA_CLARIFICATION_ANSWER:{proposal['proposal_id']}] Do not change source truth.",
        node_context=changed,
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert stale["reason"] == "stale_topology_selection"
    assert stale["fail_closed"] is True


def test_legacy_one_turn_api_remains_compatible(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Frame this selected renderer as the bounded objective.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert proposal["status"] == "PENDING_HUMAN_APPROVAL"
    assert proposal["negative_requirements"]
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
    )
    assert approved["ok"] is True
    assert approved["next_action"]["action_id"] == "set_objective"


def test_affordance_map_declares_current_review_learning_extension():
    """Replace the stale pre-extension baseline assertion with the committed contract."""
    data = json.loads((REPO_ROOT / ".aura" / "AFFORDANCE_MAP.json").read_text(encoding="utf-8"))
    assert data["mode"] == "generated_placeholder_with_review_learning_extension"
    assert data["source_of_truth"] == (
        "aura_affordance_directory.SEED_AFFORDANCES plus bounded extension entries"
    )
    assert "advisory-only" in data["note"]
    assert any(item.get("id") == "aura.coding_waboose.review_lessons" for item in data["affordances"])

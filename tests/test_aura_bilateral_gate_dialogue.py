"""Focused PR2 proof for bilateral Gate Dialogue compilation."""
from __future__ import annotations

import json
import subprocess
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


def test_confirmation_audit_record_does_not_stale_itself(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Address this node. Do not widen scope.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
    )
    assert approved["ok"] is True
    status = service.status()
    assert status["confirmed"][-1]["confirmation_currency"] == "CURRENT"
    assert status["confirmed"][-1]["stale_reasons"] == []


def test_contradiction_clarification_preserves_the_selected_side():
    from aura_bilateral_intent_compiler import (
        analyze_bilateral_request,
        apply_clarification,
    )
    from aura_intent_refinement import AmbiguityClass

    request = "Widen the selected file scope. Do not widen the selected file scope."
    positive_analysis = analyze_bilateral_request(request)
    positive_question = next(
        item
        for item in positive_analysis.questions
        if item.ambiguity_class == AmbiguityClass.CONTRADICTION.value
    )
    positive_choice, negative_choice = positive_question.candidate_answers
    positive_resolved = apply_clarification(
        positive_analysis,
        question=positive_question,
        answer=positive_choice,
    )
    assert positive_choice in positive_resolved.positive_requirements
    assert all(
        item.statement != negative_choice and item.target != negative_choice
        for item in positive_resolved.negative_requirements
    )

    negative_analysis = analyze_bilateral_request(request)
    negative_question = next(
        item
        for item in negative_analysis.questions
        if item.ambiguity_class == AmbiguityClass.CONTRADICTION.value
    )
    positive_choice, negative_choice = negative_question.candidate_answers
    negative_resolved = apply_clarification(
        negative_analysis,
        question=negative_question,
        answer=negative_choice,
    )
    assert positive_choice not in negative_resolved.positive_requirements
    assert any(
        item.statement == negative_choice or item.target == negative_choice
        for item in negative_resolved.negative_requirements
    )
    assert negative_resolved.teach_back is not None

def test_repository_identity_detects_same_path_content_drift(tmp_path):
    from aura_arena_gate_dialogue import _repository_identity

    def git(*args):
        subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init")
    git("config", "user.name", "Aura Test")
    git("config", "user.email", "aura-test@example.invalid")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    git("add", "tracked.txt")
    git("commit", "-m", "base")

    tracked.write_text("candidate one\n", encoding="utf-8")
    first = _repository_identity(tmp_path)
    tracked.write_text("candidate two\n", encoding="utf-8")
    second = _repository_identity(tmp_path)
    assert first["source_tree_digest"] != second["source_tree_digest"]

    untracked = tmp_path / "new.txt"
    untracked.write_text("untracked one\n", encoding="utf-8")
    third = _repository_identity(tmp_path)
    untracked.write_text("untracked two\n", encoding="utf-8")
    fourth = _repository_identity(tmp_path)
    assert third["source_tree_digest"] != fourth["source_tree_digest"]

def test_legacy_one_turn_contradiction_preserves_prohibition(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Widen the selected file scope. Do not widen the selected file scope.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert proposal["status"] == "PENDING_HUMAN_APPROVAL"
    assert any(
        item.get("target") == "widen the selected file scope"
        for item in proposal["negative_requirements"]
    )
    assert "Widen the selected file scope." not in proposal["positive_requirements"]

def test_confirmation_status_reports_expired_receipt(workflow, monkeypatch):
    import aura_arena_gate_dialogue as gate_module

    now = 1_800_000_000.0
    monkeypatch.setattr(gate_module.time, "time", lambda: now)
    service = gate_module.ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment=(
            f"{gate_module.BILATERAL_MARKER} "
            "Frame this selected renderer. Do not widen its scope."
        ),
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
    )
    assert approved["ok"] is True

    monkeypatch.setattr(
        gate_module.time,
        "time",
        lambda: now + gate_module.SESSION_TTL_SECONDS + 1.0,
    )
    status = service.status()
    assert status["confirmed"][0]["confirmation_currency"] == "STALE"
    assert "confirmation_expired" in status["confirmed"][0]["stale_reasons"]


def test_affordance_map_declares_current_review_learning_extension():
    """Replace the stale pre-extension baseline assertion with the committed contract."""
    data = json.loads((REPO_ROOT / ".aura" / "AFFORDANCE_MAP.json").read_text(encoding="utf-8"))
    assert data["mode"] == "generated_placeholder_with_review_learning_extension"
    assert data["source_of_truth"] == (
        "aura_affordance_directory.SEED_AFFORDANCES plus bounded extension entries"
    )
    assert "advisory-only" in data["note"]
    assert any(item.get("id") == "aura.coding_waboose.review_lessons" for item in data["affordances"])


def test_reviewer_identity_bound_to_authenticated_operator(workflow):
    import aura_arena_gate_dialogue as gate_module

    service = gate_module.ArenaGateDialogueService(
        REPO_ROOT, workflow, operator_identity="authenticated_operator_alice"
    )
    proposal = service.address(
        comment=(
            f"{gate_module.BILATERAL_MARKER} "
            "Frame this selected renderer. Do not widen its scope."
        ),
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    # Caller attempts to forge a different reviewer name
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="forged_attacker_identity",
    )
    assert approved["ok"] is True
    assert approved["decision"]["reviewer"] == "authenticated_operator_alice"
    assert approved["canonical_compilation"]["confirmation_receipt"]["human_reviewer"] == "authenticated_operator_alice"


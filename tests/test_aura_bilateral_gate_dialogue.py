"""Focused PR2 proof for bilateral Gate Dialogue compilation."""
from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

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


def test_mixed_positive_and_negative_clauses_do_not_self_contradict():
    from aura_bilateral_intent_compiler import analyze_bilateral_request

    analysis = analyze_bilateral_request(
        "Add logging, but do not change the API."
    )
    assert analysis.positive_requirements == ("Add logging",)
    assert [item.target for item in analysis.negative_requirements] == [
        "change the API"
    ]
    assert not any(
        item.ambiguity_class == "CONTRADICTION"
        for item in analysis.questions
    )

    negative_first = analyze_bilateral_request(
        "Do not change the API, but add logging."
    )
    assert negative_first.positive_requirements == ("add logging.",)
    assert [item.target for item in negative_first.negative_requirements] == [
        "change the API"
    ]


def test_clarification_recomputes_contradictions_before_confirmation():
    from aura_bilateral_intent_compiler import (
        analyze_bilateral_request,
        apply_clarification,
    )

    analysis = analyze_bilateral_request("Add logging.")
    question = analysis.questions[0]
    updated = apply_clarification(
        analysis,
        question=question,
        answer="Do not add logging.",
    )
    assert updated.teach_back is None
    assert any(
        item.ambiguity_class == "CONTRADICTION"
        for item in updated.questions
    )


def test_negative_only_request_uses_bounded_positive_fallback():
    from aura_bilateral_intent_compiler import analyze_bilateral_request

    analysis = analyze_bilateral_request("Do not change the API.")
    assert analysis.positive_requirements == (
        "Preserve the confirmed prohibition and locked guardrails.",
    )
    assert [item.target for item in analysis.negative_requirements] == [
        "change the API"
    ]
    assert analysis.questions == ()
    assert analysis.teach_back is not None


def test_clarification_audit_retains_question_and_answer_link(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService, BILATERAL_MARKER

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment=f"{BILATERAL_MARKER} Add logging.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    question = proposal["next_clarification_question"]
    clarified = service.address(
        comment=(
            f"[AURA_CLARIFICATION_ANSWER:{proposal['proposal_id']}] "
            "Do not change the API."
        ),
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    session = service._runtime[proposal["proposal_id"]]["session"]
    assert clarified["can_confirm_intent"] is True
    assert session.questions_asked[0]["question_id"] == question["question_id"]
    assert session.answers_received[0]["question_id"] == question["question_id"]
    assert session.answers_received[0]["question"] == question["question"]
    assert len(workflow.gate_dialogue_audit) >= 2
    assert workflow.gate_dialogue_audit[-1]["prior_audit_digest"] == (
        workflow.gate_dialogue_audit[-2]["audit_digest"]
    )


def test_invalid_topology_path_fails_closed_without_exception(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    invalid = {
        **NODE_CONTEXT,
        "selected_node": {
            **NODE_CONTEXT["selected_node"],
            "file_path": "../outside.py",
        },
    }
    result = service.address(
        comment="Add logging. Do not change the API.",
        node_context=invalid,
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert result["ok"] is False
    assert result["reason"] == "invalid_or_stale_topology_path"
    assert result["fail_closed"] is True


def test_legacy_pathless_objective_confirmation_uses_existing_owner(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Frame a bounded objective. Do not widen its scope.",
        node_context={},
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context={},
        stage_hint="FRAME",
    )
    assert approved["ok"] is True
    receipt = approved["canonical_compilation"]["confirmation_receipt"]
    assert receipt["allowed_path_set_digest"]
    evidence_slice = approved["canonical_compilation"]["execution_references"][
        "arena_evidence_slice"
    ]
    assert evidence_slice["items"]
    assert receipt["unified_execution_binding_ref"].startswith(
        "aura://unified-memory-continuity/execution-binding-request/"
    )
    assert (
        approved["canonical_compilation"]["execution_references"][
            "binding_status"
        ]
        == "AWAITING_CANONICAL_ACT_CAPSULE"
    )
    assert approved["canonical_compilation"]["u7_references"][
        "u7_binding_digest"
    ]


def test_packaged_repository_identity_uses_trusted_build_commit(
    tmp_path, monkeypatch
):
    import aura_arena_gate_dialogue as gate_module

    def unavailable(*args, **kwargs):
        raise FileNotFoundError("git metadata omitted")

    commit = "a" * 40
    monkeypatch.setattr(gate_module.subprocess, "run", unavailable)
    monkeypatch.setenv("AURA_SOURCE_COMMIT", commit)
    identity = gate_module._repository_identity(tmp_path)
    assert identity["repository_head"] == commit
    assert identity["working_tree_clean"] is True
    assert identity["identity_source"] == "trusted_build_environment"


def test_backend_requires_and_single_uses_current_confirmation(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService
    from aura_human_agent_arena_server import dispatch_api_request

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Frame a guarded objective. Do not widen its scope.",
        node_context={},
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context={},
        stage_hint="FRAME",
    )
    compilation = approved["canonical_compilation"]
    receipt = compilation["confirmation_receipt"]
    decision = approved["decision"]
    coding = SimpleNamespace()
    state = SimpleNamespace(
        repo_root=REPO_ROOT,
        workflow=workflow,
        gate_dialogue=service,
        coding_workbench=coding,
    )

    denied_status, denied = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/action",
        {
            "action_id": "set_objective",
            "payload": {"objective": "Guarded objective"},
        },
    )
    assert denied_status == 409
    assert denied["reason"] == "current_confirmation_receipt_required"

    guarded_payload = {
        "objective": "Guarded objective",
        "confirmation_id": receipt["confirmation_id"],
        "confirmation_receipt_id": receipt["confirmation_id"],
        "intent_digest": compilation["intent_packet"]["intent_digest"],
        "semantic_ledger_digest": compilation["semantic_ledger"]["ledger_digest"],
        "repository_head": receipt["repository_head"],
        "source_tree_digest": receipt["source_tree_digest"],
        "workflow_id": decision["workflow_id"],
        "phase_hash": decision["phase_hash"],
        "node_digest": decision["node_digest"],
    }
    status, result = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/action",
        {"action_id": "set_objective", "payload": guarded_payload},
    )
    assert status == 200
    assert result["ok"] is True
    assert result["bilateral_confirmation_authorization"]["single_use"] is True

    replay_status, replay = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/action",
        {"action_id": "set_objective", "payload": guarded_payload},
    )
    assert replay_status == 409
    assert replay["reason"] == "confirmation_receipt_already_consumed"


def test_non_boolean_gate_approval_fails_closed(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Frame a guarded objective. Do not widen its scope.",
        node_context={},
        stage_hint="FRAME",
        prefer_model=False,
    )
    denied = service.approve(
        proposal_id=proposal["proposal_id"],
        approved="false",  # type: ignore[arg-type]
        current_node_context={},
        stage_hint="FRAME",
    )
    assert denied["ok"] is False
    assert denied["reason"] == "approved_must_be_boolean"
    assert proposal["proposal_id"] in service.pending


def test_backend_command_requires_current_confirmation_but_meta_does_not(
    workflow,
):
    from aura_arena_gate_dialogue import ArenaGateDialogueService
    from aura_human_agent_arena_server import dispatch_api_request

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    state = SimpleNamespace(
        repo_root=REPO_ROOT,
        workflow=workflow,
        gate_dialogue=service,
        coding_workbench=SimpleNamespace(),
    )
    meta_status, meta = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/command",
        {"command": "help", "payload": {}},
    )
    assert meta_status == 200
    assert meta["status"] == "META_COMPLETED"
    assert workflow.objective == ""

    proposal = service.address(
        comment="Frame a command objective. Do not widen its scope.",
        node_context={},
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context={},
        stage_hint="FRAME",
    )
    denied_status, denied = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/command",
        {"command": "Command objective", "payload": {}},
    )
    assert denied_status == 409
    assert denied["reason"] == "current_confirmation_receipt_required"

    compilation = approved["canonical_compilation"]
    receipt = compilation["confirmation_receipt"]
    decision = approved["decision"]
    confirmation = {
        "confirmation_id": receipt["confirmation_id"],
        "confirmation_receipt_id": receipt["confirmation_id"],
        "intent_digest": compilation["intent_packet"]["intent_digest"],
        "semantic_ledger_digest": compilation["semantic_ledger"]["ledger_digest"],
        "repository_head": receipt["repository_head"],
        "source_tree_digest": receipt["source_tree_digest"],
        "workflow_id": decision["workflow_id"],
        "phase_hash": decision["phase_hash"],
        "node_digest": decision["node_digest"],
    }
    status, result = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/command",
        {"command": "Command objective", "payload": confirmation},
    )
    assert status == 200
    assert result["ok"] is True
    assert workflow.objective == "Command objective"
    assert result["bilateral_confirmation_authorization"]["single_use"] is True


def test_confirmation_consumption_is_atomic_under_race(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Frame an atomic objective. Do not widen its scope.",
        node_context={},
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context={},
        stage_hint="FRAME",
    )
    compilation = approved["canonical_compilation"]
    receipt = compilation["confirmation_receipt"]
    decision = approved["decision"]
    payload = {
        "confirmation_id": receipt["confirmation_id"],
        "confirmation_receipt_id": receipt["confirmation_id"],
        "intent_digest": compilation["intent_packet"]["intent_digest"],
        "semantic_ledger_digest": compilation["semantic_ledger"]["ledger_digest"],
        "repository_head": receipt["repository_head"],
        "source_tree_digest": receipt["source_tree_digest"],
        "workflow_id": decision["workflow_id"],
        "phase_hash": decision["phase_hash"],
        "node_digest": decision["node_digest"],
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: service.authorize_workflow_action(
                    action_id="set_objective",
                    action_payload=payload,
                ),
                range(2),
            )
        )
    assert sum(result.get("ok") is True for result in results) == 1
    assert sum(
        result.get("reason") == "confirmation_receipt_already_consumed"
        for result in results
    ) == 1


def test_browser_and_container_bind_confirmation_and_packaged_identity():
    javascript = (
        REPO_ROOT / "aura_showcase" / "gate-dialogue.js"
    ).read_text(encoding="utf-8")
    for field in (
        "confirmation_receipt_id",
        "workflow_id",
        "phase_hash",
        "node_digest",
        "repository_head",
        "source_tree_digest",
    ):
        assert field in javascript
    assert (
        "else if (!hasEvidence('verification_packet')) "
        "result = await action('verify_patch');"
    ) in javascript
    assert (
        "if (result.ok && !hasEvidence('verification_packet'))"
        not in javascript
    )

    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "publish-ghcr-showcase.yml"
    ).read_text(encoding="utf-8")
    assert "ARG AURA_SOURCE_COMMIT" in dockerfile
    assert "AURA_SOURCE_COMMIT=${AURA_SOURCE_COMMIT}" in dockerfile
    assert "AURA_SOURCE_COMMIT=${{ github.sha }}" in workflow_text

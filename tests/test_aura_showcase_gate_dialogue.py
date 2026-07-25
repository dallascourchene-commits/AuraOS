"""PR 2 proof for canonical bilateral integration and Gate Dialogue."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SLOT_KEYS = {"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"}
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
    "relations": [
        {
            "relation": "calls",
            "source": "node:aura_showcase/civic.js:refreshMap",
            "target": "node:aura_showcase/civic.js:drawMap",
            "label": "drawMap",
        }
    ],
}


@pytest.fixture
def workflow():
    from aura_human_agent_workflow import HumanAgentWorkflow

    item = HumanAgentWorkflow(REPO_ROOT)
    try:
        yield item
    finally:
        item.close()


@pytest.fixture
def service(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    return ArenaGateDialogueService(REPO_ROOT, workflow)


def _address(service, comment: str = ""):
    return service.address(
        comment=comment
        or (
            "Keep the selected renderer visible while changing representation modes. "
            "Do not modify canonical geometry, infer approval, hide missing assets, "
            "or touch files outside the selected renderer and its focused tests."
        ),
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )


def _confirm(service, proposal):
    return service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="test_human",
        note="CONFIRM_INTENT:Confirmed after reviewing both polarities and guardrails.",
    )


def test_address_compiles_bilateral_refinement_without_action_authority(service, workflow):
    proposal = _address(service)

    assert proposal["ok"] is True
    assert proposal["status"] == "PENDING_INTENT_CONFIRMATION"
    assert proposal["node_context"]["selected_node"]["file_path"] == "aura_showcase/civic.js"
    assert set(proposal["intent_trace"]["slots"]) == SLOT_KEYS
    assert proposal["intent_trace"]["model_calls_made"] == 0
    assert proposal["response_provenance"]["model_used"] is False
    refinement = proposal["refinement"]
    assert refinement["positive_requirements"]
    assert any("Do not" in item for item in refinement["negative_requirements"])
    assert len(refinement["hard_guardrails"]) >= 7
    assert refinement["editable_guardrails"]
    assert refinement["paired_teach_back"]["will_do"]
    assert refinement["paired_teach_back"]["will_not_do"]
    assert refinement["paired_teach_back"]["will_stop_or_escalate_if"]
    assert proposal["recommended_action"]["action_id"] == "set_objective"
    assert proposal["approval_scope"] == "advance_existing_guarded_workflow_only"
    assert proposal["production_mutation"] is False
    assert proposal["automatic_commit"] is False
    assert proposal["automatic_push"] is False
    assert proposal["automatic_merge"] is False
    assert workflow.objective == ""


def test_gate_approval_requires_separate_intent_confirmation(service, workflow):
    proposal = _address(service)

    denied = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="test_human",
        note="Proceed.",
    )
    assert denied["ok"] is False
    assert denied["reason"] == "intent_confirmation_required"
    assert workflow.objective == ""

    confirmed = _confirm(service, proposal)
    assert confirmed["ok"] is True
    assert confirmed["status"] == "INTENT_CONFIRMED_PENDING_GATE_APPROVAL"
    receipt = confirmed["confirmation_receipt"]
    assert receipt["human_disposition"] == "CONFIRMED"
    assert receipt["confirmation_status"] == "CONFIRMED"
    assert receipt["repository_head"] == confirmed["repository_head"]
    assert confirmed["canonical_bundle"]["confirmation_id"] == receipt["confirmation_id"]

    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="test_human",
        note="Approved to attempt the existing guarded gate only.",
    )
    assert approved["ok"] is True
    assert approved["status"] == "APPROVED_FOR_NEXT_GUARDED_GATE"
    assert approved["next_action"]["action_id"] == "set_objective"
    assert approved["decision"]["advance_authority"] == "existing_guarded_workflow_only"
    assert approved["decision"]["confirmation_id"] == receipt["confirmation_id"]
    assert workflow.objective == ""
    ledger = workflow.evidence["approved_gate_intents"]
    assert ledger[-1]["proposal_id"] == proposal["proposal_id"]
    assert ledger[-1]["production_mutation"] is False


def test_confirmed_bundle_uses_canonical_owners_and_reference_only_u7(service):
    proposal = _address(service)
    confirmed = _confirm(service, proposal)
    bundle = confirmed["canonical_bundle"]

    from aura_unified_memory_continuity import (
        ArenaEvidenceSlice,
        IntentPacket,
        SemanticLedger,
    )

    intent = bundle["intent_packet"]
    ledger = bundle["semantic_ledger"]
    evidence = bundle["arena_evidence_slice"]
    assert intent["version"] == IntentPacket.__dataclass_fields__["version"].default
    assert ledger["version"] == SemanticLedger.__dataclass_fields__["version"].default
    assert evidence["version"] == ArenaEvidenceSlice.__dataclass_fields__["version"].default
    assert ledger["intent_digest"] == intent["intent_digest"]
    assert evidence["objective_digest"] == intent["intent_digest"]
    assert any(item["truth_class"] == "EXACT_RECEIPT" for item in evidence["items"])
    assert any(
        "Do not modify canonical geometry" in item
        for item in intent["prohibitions"]
    )
    assert bundle["owner_refs"]["intent_packet"].endswith(".IntentPacket")
    assert bundle["owner_refs"]["semantic_ledger"].endswith(".SemanticLedger")
    assert bundle["act_capsule_envelope"] == {}
    assert bundle["u7_references"]["proposal_only"] is True
    assert bundle["u7_references"]["learning_promotion_authority"] is False
    assert bundle["u7_references"]["p0_prediction_ref"] == ""
    assert bundle["authority"]["automatic_merge"] is False
    assert bundle["authority"]["production_mutation"] is False


def test_targeted_clarification_precedes_teach_back_without_anchor(service):
    proposal = service.address(
        comment="Fix it, but do not let it do that again.",
        node_context={},
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert proposal["status"] == "PENDING_CLARIFICATION"
    question = proposal["next_clarification_question"]
    assert question["question"]
    assert question["why_it_changes_execution"]

    clarified = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context={},
        stage_hint="FRAME",
        reviewer="test_human",
        note="CLARIFY_INTENT:The exact current guarded FRAME gate and its declared objective.",
    )
    # More than one high-information question may remain; each call resolves one.
    while clarified["status"] == "PENDING_CLARIFICATION":
        clarified = service.approve(
            proposal_id=proposal["proposal_id"],
            approved=True,
            current_node_context={},
            stage_hint="FRAME",
            reviewer="test_human",
            note="CLARIFY_INTENT:The current guarded FRAME gate only.",
        )
    assert clarified["status"] == "PENDING_INTENT_CONFIRMATION"
    assert clarified["refinement"]["paired_teach_back"]["will_do"]
    assert clarified["refinement"]["paired_teach_back"]["will_not_do"]
    assert clarified["refinement"]["definitions"]


def test_correction_can_add_guardrail_but_cannot_remove_hard_guardrail(service):
    proposal = _address(service)
    hard_id = proposal["refinement"]["hard_guardrails"][0]["guardrail_id"]

    denied = service.correct_intent(
        proposal_id=proposal["proposal_id"],
        rejected_soft_guardrail_ids=[hard_id],
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="test_human",
    )
    assert denied["ok"] is False
    assert denied["reason"] == "hard_guardrail_removal_forbidden"

    corrected = service.correct_intent(
        proposal_id=proposal["proposal_id"],
        added_guardrails=[
            "Do not add a fallback image unless it is visibly labelled and human-confirmed."
        ],
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="test_human",
    )
    assert corrected["ok"] is True
    assert corrected["status"] == "PENDING_INTENT_CONFIRMATION"
    assert any(
        item["source_class"] == "HUMAN_ADDED"
        for item in corrected["refinement"]["human_added_guardrails"]
    )


def test_confirmation_and_approval_fail_closed_when_context_changes(service, workflow):
    proposal = _address(service)
    changed_node = {
        **NODE_CONTEXT,
        "selected_node": {
            **NODE_CONTEXT["selected_node"],
            "id": "other-node",
            "symbol": "drawMap",
        },
    }
    stale = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=changed_node,
        stage_hint="FRAME",
        note="CONFIRM_INTENT:Confirm.",
    )
    assert stale["ok"] is False
    assert stale["reason"] == "stale_topology_selection"
    assert stale["fail_closed"] is True

    second = _address(service)
    framed = workflow.execute_guarded(
        "set_objective", {"objective": "Investigate the selected renderer."}
    )
    assert framed["ok"] is True
    stale_phase = service.approve(
        proposal_id=second["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        note="CONFIRM_INTENT:Confirm.",
    )
    assert stale_phase["ok"] is False
    assert stale_phase["reason"] in {
        "stale_workflow_phase",
        "stale_workflow_evidence",
    }


def test_guidance_projects_guardrail_reasons_and_missing_decisions(service, workflow):
    from aura_human_agent_guidance import (
        answer_guidance_question,
        build_guidance_packet,
    )

    proposal = _address(service)
    packet = build_guidance_packet(workflow.get_state(), proposal["refinement"])
    assert packet["hard_guardrails"]
    assert packet["hard_guardrails"][0]["removal_possible"] is False
    answer = answer_guidance_question(packet, "Can this hard guardrail be removed?")
    assert answer["kind"] == "guardrail_removability"
    assert "cannot be removed" in answer["answer"]


def test_showcase_routes_preserve_two_separate_human_actions(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService
    from aura_showcase_server import dispatch_showcase_request

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    state = SimpleNamespace(repo_root=REPO_ROOT, gate_dialogue=service)

    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/human/gate/address",
        {
            "comment": (
                "Address this file and its tests. Do not change geometry or "
                "grant merge authority."
            ),
            "node_context": NODE_CONTEXT,
            "stage_hint": "FRAME",
            "prefer_model": False,
        },
    )
    proposal = json.loads(raw)
    assert status == 200
    assert proposal["status"] == "PENDING_INTENT_CONFIRMATION"

    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/human/gate/approve",
        {
            "proposal_id": proposal["proposal_id"],
            "approved": True,
            "current_node_context": NODE_CONTEXT,
            "stage_hint": "FRAME",
            "reviewer": "test_human",
            "note": "CONFIRM_INTENT:Confirmed bilateral intent only.",
        },
    )
    confirmation = json.loads(raw)
    assert status == 200
    assert confirmation["status"] == "INTENT_CONFIRMED_PENDING_GATE_APPROVAL"

    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/human/gate/approve",
        {
            "proposal_id": proposal["proposal_id"],
            "approved": True,
            "current_node_context": NODE_CONTEXT,
            "stage_hint": "FRAME",
            "reviewer": "test_human",
            "note": "Approve existing guarded gate only.",
        },
    )
    decision = json.loads(raw)
    assert status == 200
    assert decision["approved"] is True
    assert decision["decision"]["confirmation_id"] == confirmation["confirmation_receipt"]["confirmation_id"]
    assert decision["automatic_merge"] is False


def test_browser_gate_dialogue_renders_required_bilateral_sections():
    from aura_showcase_server import _static_response

    javascript = (
        REPO_ROOT / "aura_showcase" / "gate-dialogue.js"
    ).read_text(encoding="utf-8")
    for text in (
        "Your request",
        "What Aura thinks you want",
        "What Aura thinks you do not want",
        "Terms needing definition",
        "Proposed hard guardrails",
        "Proposed editable guardrails",
        "Human-added guardrails",
        "Positive example",
        "Negative example",
        "Aura’s paired teach-back",
        "Confirm bilateral intent",
        "Correct",
        "Add Guardrail",
        "Defer",
        "CLARIFY_INTENT:",
        "CONFIRM_INTENT:",
        "/api/showcase/human/gate/address",
        "/api/showcase/human/gate/approve",
        "S.runHumanAction",
        "run_tests",
        "verify_patch",
        "approved: false",
        "No production approval or merge was granted.",
    ):
        assert text in javascript

    status, content_type, body = _static_response("/")
    assert status == 200
    assert content_type.startswith("text/html")
    assert b'<script src="gate-dialogue.js"></script>' in body

    status, content_type, body = _static_response("/gate-dialogue.js")
    assert status == 200
    assert "javascript" in content_type
    assert b"PENDING_INTENT_CONFIRMATION" in body
    assert b"INTENT_CONFIRMED_PENDING_GATE_APPROVAL" in body

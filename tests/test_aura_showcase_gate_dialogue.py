"""Contracts for topology-anchored, human-approved Arena gate dialogue."""
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


def test_gate_dialogue_is_node_anchored_and_proposal_only(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Check whether this renderer can use a stale response and tell me the safest next step.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )

    assert proposal["ok"] is True
    assert proposal["status"] == "PENDING_HUMAN_APPROVAL"
    assert proposal["node_context"]["selected_node"]["file_path"] == "aura_showcase/civic.js"
    assert proposal["node_context"]["dependencies"] == ["project_map_manifest", "drawMap"]
    assert set(proposal["intent_trace"]["slots"]) == SLOT_KEYS
    assert proposal["intent_trace"]["model_calls_made"] == 0
    assert proposal["response_provenance"]["model_used"] is False
    assert proposal["recommended_action"]["action_id"] == "set_objective"
    assert proposal["approval_scope"] == "advance_existing_guarded_workflow_only"
    assert proposal["production_mutation"] is False
    assert proposal["automatic_commit"] is False
    assert proposal["automatic_push"] is False
    assert proposal["automatic_merge"] is False
    assert workflow.objective == ""


def test_approval_records_exact_gate_but_does_not_execute_action(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Frame this selected renderer as the bounded objective.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        reviewer="test_human",
        note="Proceed to the existing guarded action only.",
    )

    assert approved["ok"] is True
    assert approved["status"] == "APPROVED_FOR_NEXT_GUARDED_GATE"
    assert approved["next_action"]["action_id"] == "set_objective"
    assert approved["decision"]["advance_authority"] == "existing_guarded_workflow_only"
    assert workflow.objective == ""
    ledger = workflow.evidence["approved_gate_intents"]
    assert ledger[-1]["proposal_id"] == proposal["proposal_id"]
    assert ledger[-1]["approved"] is True
    assert ledger[-1]["production_mutation"] is False


def test_gate_approval_fails_closed_when_phase_or_node_changes(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Explain this selected node before the next gate.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    changed_node = {
        **NODE_CONTEXT,
        "selected_node": {**NODE_CONTEXT["selected_node"], "id": "other-node", "symbol": "drawMap"},
    }
    stale_node = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=changed_node,
        stage_hint="FRAME",
    )
    assert stale_node["ok"] is False
    assert stale_node["reason"] == "stale_topology_selection"
    assert stale_node["fail_closed"] is True

    second = service.address(
        comment="Explain this node again.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    framed = workflow.execute_guarded("set_objective", {"objective": "Investigate the selected renderer."})
    assert framed["ok"] is True
    stale_phase = service.approve(
        proposal_id=second["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
    )
    assert stale_phase["ok"] is False
    assert stale_phase["reason"] in {"stale_workflow_phase", "stale_workflow_evidence"}


def test_showcase_routes_expose_address_and_approval(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService
    from aura_showcase_server import dispatch_showcase_request

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    state = SimpleNamespace(repo_root=REPO_ROOT, gate_dialogue=service)

    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/human/gate/address",
        {
            "comment": "Address this file and its tests before proceeding.",
            "node_context": NODE_CONTEXT,
            "stage_hint": "FRAME",
            "prefer_model": False,
        },
    )
    proposal = json.loads(raw)
    assert status == 200
    assert proposal["status"] == "PENDING_HUMAN_APPROVAL"

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
        },
    )
    decision = json.loads(raw)
    assert status == 200
    assert decision["approved"] is True
    assert decision["automatic_merge"] is False


def test_browser_gate_dialogue_is_injected_and_uses_real_guarded_actions():
    from aura_showcase_server import _static_response

    javascript = (REPO_ROOT / "aura_showcase" / "gate-dialogue.js").read_text(encoding="utf-8")
    assert "human-gate-comment" in javascript
    assert "human-gate-address" in javascript
    assert "human-gate-approve" in javascript
    assert "/api/showcase/human/gate/address" in javascript
    assert "/api/showcase/human/gate/approve" in javascript
    assert "current_node_context" in javascript
    assert "S.runHumanAction" in javascript
    assert "run_tests" in javascript
    assert "verify_patch" in javascript
    assert "approved: false" in javascript
    assert "automatic merge" in javascript.lower()

    status, content_type, body = _static_response("/")
    assert status == 200
    assert content_type.startswith("text/html")
    assert b'<script src="gate-dialogue.js"></script>' in body

    status, content_type, body = _static_response("/gate-dialogue.js")
    assert status == 200
    assert "javascript" in content_type
    assert b"PENDING_HUMAN_APPROVAL" in body

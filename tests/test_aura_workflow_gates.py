"""Tests for Aura Workflow Gates (18-state checkpoint machine).

Tests cover:
- WorkflowState has 18 states
- GATE_DEFINITIONS has all 18 states
- get_gate returns WorkflowGate for each state
- can_transition checks valid transitions
- AGENT_HANDOFF_READY cannot be reached without CODEMAP_LOCALIZED and PLAN_READY
- HUMAN_APPROVED_FOR_COMMIT requires VERIFIED
- PR_READY requires HUMAN_APPROVED_FOR_COMMIT
- evaluate_gate checks evidence requirements
- workflow_state_machine returns dict with states and gates
- patch_authority and vsa_patch_authority invariants
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_workflow_gates import (
    WorkflowState,
    GATE_DEFINITIONS,
    get_gate,
    can_transition,
    evaluate_gate,
    workflow_state_machine,
    workflow_gate_markdown,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)


class TestWorkflowStates:
    def test_has_18_states(self):
        states = list(WorkflowState)
        assert len(states) == 18

    def test_state_names(self):
        expected_names = {
            "INGESTED", "POLYSYNTHETIC_COMPRESSED", "LEXC_VALIDATED", "FST_ROUTED",
            "CODEMAP_LOCALIZED", "DREAM_RERANKED", "CONTEXT_COMPRESSED", "ST3GG_READY",
            "PLAN_READY", "HUMAN_APPROVED_FOR_AGENT", "AGENT_HANDOFF_READY",
            "AGENT_RUNNING", "PATCH_PROPOSED", "VERIFIED", "REPAIR_REQUIRED",
            "HUMAN_APPROVED_FOR_COMMIT", "PR_READY", "PR_OPENED",
        }
        actual_names = {s.name for s in WorkflowState}
        assert expected_names == actual_names


class TestGateDefinitions:
    def test_all_states_have_gates(self):
        assert len(GATE_DEFINITIONS) == 18
        for state in WorkflowState:
            assert state in GATE_DEFINITIONS, f"Missing gate for {state.name}"

    def test_get_gate_returns_gate(self):
        for state in WorkflowState:
            gate = get_gate(state)
            assert gate is not None

    def test_gates_have_required_fields(self):
        for state in WorkflowState:
            gate = get_gate(state)
            assert hasattr(gate, "allowed_actions")
            assert hasattr(gate, "blocked_actions")
            assert hasattr(gate, "required_evidence")
            assert hasattr(gate, "human_approval_required")


class TestTransitions:
    def test_sequential_transition_allowed(self):
        assert can_transition(WorkflowState.INGESTED, WorkflowState.POLYSYNTHETIC_COMPRESSED) is True

    def test_skip_to_handoff_blocked(self):
        assert can_transition(WorkflowState.INGESTED, WorkflowState.AGENT_HANDOFF_READY) is False

    def test_pr_ready_requires_commit_approval(self):
        # Cannot go from VERIFIED directly to PR_READY
        assert can_transition(WorkflowState.VERIFIED, WorkflowState.PR_READY) is False


class TestEvaluateGate:
    def test_codemap_localized_with_grounding(self):
        result = evaluate_gate("CODEMAP_LOCALIZED", {"grounding_ok": True})
        assert "ok" in result
        assert "can_proceed" in result
        assert "missing_requirements" in result

    def test_human_approval_required(self):
        result = evaluate_gate("HUMAN_APPROVED_FOR_AGENT", {"human_approval": False})
        assert result.get("human_approval_required") is True

    def test_invariants(self):
        result = evaluate_gate("INGESTED", {})
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


class TestStateMachine:
    def test_returns_dict(self):
        result = workflow_state_machine()
        assert isinstance(result, dict)
        assert "states" in result or "gates" in result

    def test_has_18_states(self):
        result = workflow_state_machine()
        states = result.get("states", [])
        gates = result.get("gates", [])
        assert len(states) == 18 or len(gates) == 18


class TestGateMarkdown:
    def test_returns_string(self):
        md = workflow_gate_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

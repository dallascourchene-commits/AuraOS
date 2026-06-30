"""
Tests for Aura Coding Arena Workflow Memory.

Proves:
1. Workflow events serialize safely (JSON round-trip)
2. Corrupt patch failures are recorded
3. QDKT observation is emitted
4. DREAM feedback rows are emitted
5. Research proposals cannot bypass verifier gates
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aura_coding_arena_workflow import (
    ALLOW_ARENA_STAGING,
    ALLOW_MUTATION,
    BuilderContextRecord,
    CodingArenaWorkflowMemory,
    PatchAttemptRecord,
    RepairAttemptRecord,
    WorkflowEvent,
    WorkflowOutcome,
    convert_research_proposal_to_action_capsule,
    enforce_research_no_direct_mutation,
    get_coding_arena_memory,
    validate_research_staging_gate,
)


# ---------------------------------------------------------------------------
# Test 1: Workflow events serialize safely
# ---------------------------------------------------------------------------

class TestWorkflowEventSerialization:
    """Prove that all workflow event types serialize and deserialize safely."""

    def test_workflow_event_round_trip(self):
        """WorkflowEvent to_dict -> json -> from_dict preserves all fields."""
        event = WorkflowEvent(
            event_id="EVT-test123",
            workflow_id="WF-test456",
            event_type="plan_candidate",
            timestamp=1234567890.0,
            phase="plan",
            payload={"candidate_id": "local_free", "score": 0.54},
            phase_hash="abc123",
        )
        d = event.to_dict()
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)
        restored = WorkflowEvent.from_dict(deserialized)
        assert restored.event_id == event.event_id
        assert restored.workflow_id == event.workflow_id
        assert restored.event_type == event.event_type
        assert restored.timestamp == event.timestamp
        assert restored.phase == event.phase
        assert restored.payload == event.payload
        assert restored.phase_hash == event.phase_hash

    def test_all_record_types_serialize(self):
        """All record dataclasses serialize to valid JSON."""
        patch_record = PatchAttemptRecord(
            task_id="A-LIVE-1",
            status="preflight_failed",
            preflight={"ok": False, "rejections": ["empty_diff"]},
            diff_hash="abc123",
        )
        builder_record = BuilderContextRecord(
            task_id="A-LIVE-1",
            target_file="aura_node.py",
            target_symbol="main",
            source_excerpt_length=500,
            nearby_tests_count=3,
            callers_count=5,
            neighbors_count=2,
        )
        repair_record = RepairAttemptRecord(
            task_id="A-LIVE-1",
            repair_ok=False,
            rejections_before=["empty_diff"],
            rejections_after=["still_empty"],
        )
        outcome = WorkflowOutcome(
            workflow_id="WF-test",
            success=False,
            hotswap_ready=False,
            failures_count=2,
            stage="blocked",
        )
        for record in [patch_record, builder_record, repair_record, outcome]:
            d = record.to_dict()
            serialized = json.dumps(d)
            assert isinstance(serialized, str)
            deserialized = json.loads(serialized)
            assert isinstance(deserialized, dict)

    def test_batch_append_serializes_all(self):
        """Batch append writes all events as valid JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            memory = CodingArenaWorkflowMemory(ledger_path=ledger)
            events = [
                WorkflowEvent(
                    event_id=f"EVT-{i}",
                    workflow_id="WF-batch",
                    event_type="plan_candidate",
                    timestamp=float(i),
                    phase="plan",
                    payload={"index": i},
                )
                for i in range(5)
            ]
            memory.append_batch(events)
            lines = ledger.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 5
            for line in lines:
                record = json.loads(line)
                assert record["workflow_id"] == "WF-batch"
                assert "version" in record


# ---------------------------------------------------------------------------
# Test 2: Corrupt patch failures are recorded
# ---------------------------------------------------------------------------

class TestCorruptPatchFailures:
    """Prove that corrupt/failed patch attempts are recorded in the workflow trace."""

    def test_preflight_failure_recorded(self):
        """A failed preflight result is recorded with status 'preflight_failed'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            memory = CodingArenaWorkflowMemory(ledger_path=ledger)
            wf_id = memory.begin_workflow("test corrupt patch", "aura_node.py")

            # Simulate a corrupt/failed preflight
            failed_preflight = MagicMock()
            failed_preflight.to_dict.return_value = {
                "ok": False,
                "rejections": ["empty_diff", "malformed_header"],
                "git_check_result": None,
                "diff": "",
            }
            memory.record_patch_preflight(wf_id, "A-LIVE-1", failed_preflight)

            trace = memory.get_workflow_trace(wf_id)
            assert len(trace) >= 1
            preflight_event = trace[-1]
            assert preflight_event["event_type"] == "patch_preflight_result"
            payload = preflight_event["payload"]
            assert payload["status"] == "preflight_failed"
            assert payload["preflight"]["ok"] is False
            assert "empty_diff" in payload["preflight"]["rejections"]

    def test_repair_failure_recorded(self):
        """A failed repair attempt is recorded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            memory = CodingArenaWorkflowMemory(ledger_path=ledger)
            wf_id = memory.begin_workflow("test repair failure", "aura_node.py")

            failed_repair = MagicMock()
            failed_repair.to_dict.return_value = {
                "ok": False,
                "repaired_diff": "",
                "rejections_before": ["empty_diff"],
                "rejections_after": ["still_broken"],
            }
            memory.record_repair_attempt(wf_id, "A-LIVE-1", failed_repair)

            trace = memory.get_workflow_trace(wf_id)
            repair_event = trace[-1]
            assert repair_event["event_type"] == "repair_attempt"
            payload = repair_event["payload"]
            assert payload["repair_ok"] is False
            assert "still_broken" in payload["rejections_after"]


# ---------------------------------------------------------------------------
# Test 3: QDKT observation is emitted
# ---------------------------------------------------------------------------

class TestQDKTObservation:
    """Prove that workflow outcomes emit QDKT observations."""

    def test_qdkt_observe_called_on_outcome(self):
        """record_outcome calls qdkt.observe with coding_arena_workflow_outcome."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            mock_qdkt = MagicMock()
            memory = CodingArenaWorkflowMemory(ledger_path=ledger, qdkt=mock_qdkt)
            wf_id = memory.begin_workflow("test qdkt", "aura_node.py")

            outcome = WorkflowOutcome(
                workflow_id=wf_id,
                success=True,
                hotswap_ready=True,
                failures_count=0,
                stage="verified",
            )
            memory.record_outcome(wf_id, outcome)

            mock_qdkt.observe.assert_called_once()
            call_args = mock_qdkt.observe.call_args
            assert call_args.args[0] == "coding_arena_workflow_outcome"
            payload = call_args.args[1]
            assert payload["success"] is True
            assert payload["hotswap_ready"] is True
            assert payload["workflow_id"] == wf_id

    def test_qdkt_observe_called_on_failure(self):
        """record_outcome calls qdkt.observe even on failed outcomes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            mock_qdkt = MagicMock()
            memory = CodingArenaWorkflowMemory(ledger_path=ledger, qdkt=mock_qdkt)
            wf_id = memory.begin_workflow("test qdkt fail", "aura_node.py")

            outcome = WorkflowOutcome(
                workflow_id=wf_id,
                success=False,
                hotswap_ready=False,
                failures_count=3,
                stage="blocked",
            )
            memory.record_outcome(wf_id, outcome)

            mock_qdkt.observe.assert_called_once()
            payload = mock_qdkt.observe.call_args.args[1]
            assert payload["success"] is False
            assert payload["failures_count"] == 3


# ---------------------------------------------------------------------------
# Test 4: DREAM feedback rows are emitted
# ---------------------------------------------------------------------------

class TestDreamFeedback:
    """Prove that context usefulness is wired into DREAM feedback."""

    def test_dream_feedback_called_with_context(self):
        """record_outcome calls record_arena_retrieval_feedback with DreamCandidates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            mock_dream_fn = MagicMock()
            memory = CodingArenaWorkflowMemory(
                ledger_path=ledger,
                dream_feedback_fn=mock_dream_fn,
            )
            wf_id = memory.begin_workflow("test dream", "aura_node.py")

            # Create a mock context packet with source excerpt
            mock_packet = MagicMock()
            mock_packet.to_dict.return_value = {
                "target_file": "aura_node.py",
                "target_symbol": "main",
                "source_excerpt": "def main(): ...",
                "nearby_tests": ["test_aura.py"],
                "callers": ["run()"],
                "neighbors": ["helper()"],
            }

            outcome = WorkflowOutcome(
                workflow_id=wf_id,
                success=True,
                hotswap_ready=True,
                failures_count=0,
                stage="verified",
                intent="test dream",
            )
            memory.record_outcome(wf_id, outcome, context_packets=[mock_packet])

            mock_dream_fn.assert_called_once()
            call_args = mock_dream_fn.call_args
            candidates = call_args.args[1]
            assert len(candidates) > 0
            # Verify candidates include source excerpt and test entries
            candidate_types = [c.candidate_type for c in candidates]
            assert "source_excerpt" in candidate_types
            assert "nearby_test" in candidate_types

    def test_dream_feedback_not_called_without_context(self):
        """record_outcome does not call DREAM when no context packets provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            mock_dream_fn = MagicMock()
            memory = CodingArenaWorkflowMemory(
                ledger_path=ledger,
                dream_feedback_fn=mock_dream_fn,
            )
            wf_id = memory.begin_workflow("test no dream", "aura_node.py")

            outcome = WorkflowOutcome(
                workflow_id=wf_id,
                success=True,
                hotswap_ready=True,
                failures_count=0,
                stage="verified",
            )
            memory.record_outcome(wf_id, outcome)
            mock_dream_fn.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: Research proposals cannot bypass verifier gates
# ---------------------------------------------------------------------------

class TestResearchGateEnforcement:
    """Prove that research proposals cannot bypass verifier gates."""

    def test_allow_mutation_is_allow_arena_staging(self):
        """ALLOW_MUTATION alias equals ALLOW_ARENA_STAGING."""
        assert ALLOW_MUTATION == ALLOW_ARENA_STAGING
        assert ALLOW_ARENA_STAGING == "ALLOW_ARENA_STAGING"

    def test_enforce_research_no_direct_mutation(self):
        """enforce_research_no_direct_mutation wraps output with staging policy."""
        research_output = {
            "concept": "test concept",
            "proposed_patch": "def foo(): pass",
            "target_modules": ["aura_node.py"],
        }
        envelope = enforce_research_no_direct_mutation(research_output)
        assert envelope["direct_mutation_allowed"] is False
        assert envelope["mutation_policy"] == "arena_staging_required"
        assert envelope["must_convert_to_action_capsule"] is True
        assert envelope["must_pass_staging_gate"] is True

    def test_staging_gate_blocks_missing_source_context(self):
        """validate_research_staging_gate blocks when source context is missing."""
        proposal = {"concept": "test", "proposed_patch": "code"}
        allowed, reason = validate_research_staging_gate(
            proposal,
            source_context=None,
            tests=["test_foo.py"],
            preflight_result=MagicMock(),
        )
        assert allowed is False
        assert "missing target source context" in reason

    def test_staging_gate_blocks_missing_tests(self):
        """validate_research_staging_gate blocks when tests are missing."""
        proposal = {"concept": "test", "proposed_patch": "code"}
        allowed, reason = validate_research_staging_gate(
            proposal,
            source_context={"target_file": "aura_node.py"},
            tests=None,
            preflight_result=MagicMock(),
        )
        assert allowed is False
        assert "no tests identified" in reason

    def test_staging_gate_blocks_missing_preflight(self):
        """validate_research_staging_gate blocks when preflight is missing."""
        proposal = {"concept": "test", "proposed_patch": "code"}
        allowed, reason = validate_research_staging_gate(
            proposal,
            source_context={"target_file": "aura_node.py"},
            tests=["test_foo.py"],
            preflight_result=None,
        )
        assert allowed is False
        assert "no preflight validation" in reason

    def test_staging_gate_blocks_failed_preflight(self):
        """validate_research_staging_gate blocks when preflight fails."""
        proposal = {"concept": "test", "proposed_patch": "code"}
        failed_preflight = MagicMock()
        failed_preflight.to_dict.return_value = {
            "ok": False,
            "rejections": ["syntax_error"],
        }
        allowed, reason = validate_research_staging_gate(
            proposal,
            source_context={"target_file": "aura_node.py"},
            tests=["test_foo.py"],
            preflight_result=failed_preflight,
        )
        assert allowed is False
        assert "preflight validation failed" in reason

    def test_staging_gate_passes_with_all_requirements(self):
        """validate_research_staging_gate passes when all requirements are met."""
        proposal = {"concept": "test", "proposed_patch": "code"}
        passed_preflight = MagicMock()
        passed_preflight.to_dict.return_value = {
            "ok": True,
            "rejections": [],
        }
        allowed, reason = validate_research_staging_gate(
            proposal,
            source_context={"target_file": "aura_node.py"},
            tests=["test_foo.py"],
            preflight_result=passed_preflight,
        )
        assert allowed is True
        assert "passed" in reason

    def test_research_proposal_converts_to_action_capsule(self):
        """convert_research_proposal_to_action_capsule produces a valid ActionCapsule."""
        proposal = {
            "concept": "test concept",
            "proposed_patch": "def foo(): pass",
            "target_modules": ["aura_node.py"],
            "gate_decision": "ALLOW_ARENA_STAGING",
            "gate_score": 0.85,
        }
        capsule = convert_research_proposal_to_action_capsule(proposal)
        assert capsule is not None
        assert capsule.role == "research_act_worker"
        assert capsule.expected_output == "UNIFIED_DIFF"
        assert "direct_production_write" in capsule.forbidden_actions
        assert "bypass_verifier" in capsule.forbidden_actions
        assert capsule.metadata.get("mutation_policy") == "arena_staging_required"

    def test_research_output_cannot_directly_mutate(self):
        """Research output envelope explicitly forbids direct mutation."""
        research_output = {"concept": "test", "proposed_patch": "code"}
        envelope = enforce_research_no_direct_mutation(research_output)
        # The envelope must be used for staging, not direct application
        assert envelope["direct_mutation_allowed"] is False
        # The staging path must be followed
        assert envelope["staging_path"] == "Aura_Staging/research_refactor_request.json"


# ---------------------------------------------------------------------------
# Test 6: Singleton accessor
# ---------------------------------------------------------------------------

class TestSingletonAccessor:
    """Test the get_coding_arena_memory singleton."""

    def test_singleton_returns_same_instance(self):
        """get_coding_arena_memory returns the same instance on repeated calls."""
        # Reset module-level singleton and force initialization with a temp-backed ledger
        import importlib
        acaw = importlib.import_module("aura_coding_arena_workflow")
        acaw._CODING_ARENA_MEMORY = None
        orig_cls = acaw.CodingArenaWorkflowMemory
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_singleton_workflows.jsonl"
            try:
                # Patch the constructor to ensure the singleton is created with our ledger
                acaw.CodingArenaWorkflowMemory = lambda *a, **k: orig_cls(ledger_path=ledger)
                m1 = acaw.get_coding_arena_memory()
                m2 = acaw.get_coding_arena_memory()
                assert m1 is m2
                assert isinstance(m1, orig_cls)
            finally:
                acaw.CodingArenaWorkflowMemory = orig_cls
                acaw._CODING_ARENA_MEMORY = None


# ---------------------------------------------------------------------------
# Test 7: Full workflow trace
# ---------------------------------------------------------------------------

class TestFullWorkflowTrace:
    """Test a complete workflow trace with all event types."""

    def test_complete_workflow_records_all_events(self):
        """A complete workflow records all event types in the JSONL trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "test_workflows.jsonl"
            mock_qdkt = MagicMock()
            memory = CodingArenaWorkflowMemory(ledger_path=ledger, qdkt=mock_qdkt)
            wf_id = memory.begin_workflow("complete workflow test", "aura_node.py")

            # Record all event types
            memory.record_plan_candidate(wf_id, {"candidate_id": "local_free", "source": "deterministic", "score": 0.54, "plan": {}})
            memory.record_shadow_critique(wf_id, {"critic_id": "scope", "approved": True, "score": 0.6, "blockers": []})
            memory.record_builder_context(wf_id, MagicMock(to_dict=lambda: {"target_file": "aura_node.py", "source_excerpt": "code", "nearby_tests": [], "callers": [], "neighbors": []}), "A-LIVE-1")
            memory.record_patch_submission(wf_id, {"task_id": "A-LIVE-1", "diff": "diff --git a/file b/file", "affected_files": ["aura_node.py"]})
            memory.record_patch_preflight(wf_id, "A-LIVE-1", MagicMock(to_dict=lambda: {"ok": True, "rejections": []}))
            memory.record_temp_workspace_apply(wf_id, MagicMock(to_dict=lambda: {"ok": True, "checks": [], "failures": []}))
            memory.record_py_compile_test_topology(wf_id, MagicMock(to_dict=lambda: {"ok": True, "test_results": {}, "topology_delta": {"summary": {}}}))
            memory.record_premium_judge_decision(wf_id, {"approved": True, "role": "premium_judge"})
            memory.record_hotswap_decision(wf_id, {"status": "ready", "hotswap_ready": True})

            outcome = WorkflowOutcome(
                workflow_id=wf_id,
                success=True,
                hotswap_ready=True,
                failures_count=0,
                stage="verified",
                intent="complete workflow test",
                target_file="aura_node.py",
            )
            memory.record_outcome(wf_id, outcome)

            trace = memory.get_workflow_trace(wf_id)
            event_types = [e["event_type"] for e in trace]
            assert "plan_candidate" in event_types
            assert "shadow_critique" in event_types
            assert "builder_context_packet" in event_types
            assert "patch_submission" in event_types
            assert "patch_preflight_result" in event_types
            assert "temp_workspace_apply_result" in event_types
            assert "py_compile_test_topology_delta_result" in event_types
            assert "premium_judge_decision" in event_types
            assert "hotswap_decision" in event_types
            assert "workflow_outcome" in event_types

            # Verify QDKT was called
            mock_qdkt.observe.assert_called_once()
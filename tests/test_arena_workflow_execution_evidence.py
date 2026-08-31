from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.arena_workflow_execution_evidence import WorkflowEvidenceError, classify


FIXTURE = Path("tests/fixtures/workflow_execution_evidence_observations_v1.json")


class ArenaWorkflowExecutionEvidenceTests(unittest.TestCase):
    def test_two_independent_action_required_zero_job_observations_are_prejob_gates(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(len(fixture["observations"]), 2)
        for observation in fixture["observations"]:
            evidence = classify(observation["run"], observation["jobs"])
            self.assertEqual(evidence.classification, "PRE_JOB_ACTION_REQUIRED")
            self.assertTrue(evidence.provider_pre_job_gate_observed)
            self.assertFalse(evidence.executed_job_failure_observed)
            self.assertFalse(evidence.semantic_test_failure_proven)

    def test_real_completed_failed_job_is_not_prejob_gate(self):
        run = {
            "id": 1,
            "name": "semantic-owner",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "failure",
        }
        jobs = [{"status": "completed", "conclusion": "failure"}]
        evidence = classify(run, jobs)
        self.assertEqual(evidence.classification, "EXECUTED_JOB_FAILURE_OBSERVED")
        self.assertFalse(evidence.provider_pre_job_gate_observed)
        self.assertTrue(evidence.executed_job_failure_observed)
        self.assertFalse(evidence.semantic_test_failure_proven)

    def test_successful_job_record_is_execution_evidence_not_semantic_authority(self):
        run = {
            "id": 2,
            "name": "bounded-owner",
            "head_sha": "b" * 40,
            "status": "completed",
            "conclusion": "success",
        }
        jobs = [{"status": "completed", "conclusion": "success"}]
        evidence = classify(run, jobs)
        self.assertEqual(evidence.classification, "EXECUTED_JOB_SUCCESS_OBSERVED")
        self.assertTrue(evidence.executed_job_success_observed)
        self.assertFalse(evidence.semantic_test_success_proven)
        self.assertFalse(evidence.effect_authority)

    def test_queued_and_running_are_not_terminal_failure_evidence(self):
        for status in ("queued", "pending", "requested", "waiting"):
            run = {"id": 3, "name": "queued", "head_sha": "c" * 40, "status": status, "conclusion": None}
            evidence = classify(run, [])
            self.assertEqual(evidence.classification, "RUN_NOT_YET_EXECUTION_EVIDENCE")
            self.assertFalse(evidence.executed_job_failure_observed)
        run = {"id": 4, "name": "running", "head_sha": "d" * 40, "status": "in_progress", "conclusion": None}
        self.assertEqual(classify(run, []).classification, "RUN_IN_PROGRESS")

    def test_terminal_zero_jobs_other_than_action_required_stays_nondecisive(self):
        run = {"id": 5, "name": "skipped", "head_sha": "e" * 40, "status": "completed", "conclusion": "skipped"}
        evidence = classify(run, [])
        self.assertEqual(evidence.classification, "TERMINAL_WITHOUT_JOB_EVIDENCE")
        self.assertFalse(evidence.executed_job_failure_observed)

    def test_job_record_without_failure_or_success_is_nondecisive(self):
        run = {"id": 6, "name": "cancelled", "head_sha": "f" * 40, "status": "completed", "conclusion": "cancelled"}
        jobs = [{"status": "completed", "conclusion": "cancelled"}]
        evidence = classify(run, jobs)
        self.assertEqual(evidence.classification, "JOB_RECORD_PRESENT_NONDECISIVE")
        self.assertFalse(evidence.executed_job_failure_observed)
        self.assertFalse(evidence.executed_job_success_observed)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(WorkflowEvidenceError):
            classify({}, [])
        with self.assertRaises(WorkflowEvidenceError):
            classify({"id": 1, "name": "x", "head_sha": "0" * 40, "status": "completed", "conclusion": None}, {})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from tools.arena_workflow_execution_evidence import WorkflowEvidenceError
from tools.aura_hyperscale_work_admission import EvidenceObservation
from tools.aura_execution_aware_hyperscale_admission import (
    ROUTE_INSUFFICIENT,
    ROUTE_PROVIDER_HOLD,
    ROUTE_SEMANTIC,
    ROUTE_WAIT,
    route_workflow_through_hyperscale,
)


HEAD = "a" * 40


def run(*, status: str = "completed", conclusion: str | None = "success", run_id: int = 1):
    return {
        "id": run_id,
        "name": "fixture",
        "head_sha": HEAD,
        "status": status,
        "conclusion": conclusion,
    }


def job(*, status: str = "completed", conclusion: str | None = "success"):
    return {"status": status, "conclusion": conclusion}


class AuraExecutionAwareHyperScaleAdmissionTests(unittest.TestCase):
    def test_pre_job_action_required_cannot_mint_exploration(self):
        receipt = route_workflow_through_hyperscale(
            run=run(conclusion="action_required"),
            jobs=[],
            semantic_disposition="SEMANTIC_SIBLING",
            hard_gates_pass=True,
            exploration_benefit_score=100,
            exploration_cost_score=1,
        )
        self.assertEqual(receipt.route, ROUTE_PROVIDER_HOLD)
        self.assertEqual(receipt.execution_classification, "PRE_JOB_ACTION_REQUIRED")
        self.assertFalse(receipt.semantic_admission_evaluated)
        self.assertIsNone(receipt.semantic_admission_payload)
        self.assertTrue(receipt.provider_eligibility_repair_required)
        self.assertFalse(receipt.provider_gate_counts_as_semantic_failure)
        self.assertFalse(receipt.provider_gate_counts_as_new_sck)
        self.assertFalse(receipt.provider_gate_counts_as_new_egk)
        self.assertFalse(receipt.automatic_retry_scheduled)

    def test_pre_job_action_required_cannot_mint_verification(self):
        observation = EvidenceObservation("only", ("LEAF",), 1, 1)
        receipt = route_workflow_through_hyperscale(
            run=run(conclusion="action_required"),
            jobs=[],
            semantic_disposition="SUPPORT_MERGE",
            hard_gates_pass=True,
            unresolved_leaves=("LEAF",),
            observations=(observation,),
            verification_benefit_score=100,
        )
        self.assertEqual(receipt.route, ROUTE_PROVIDER_HOLD)
        self.assertFalse(receipt.semantic_admission_evaluated)
        self.assertIsNone(receipt.semantic_admission_digest)

    def test_in_progress_waits_without_hyperscale_admission(self):
        receipt = route_workflow_through_hyperscale(
            run=run(status="in_progress", conclusion=None),
            jobs=[job(status="in_progress", conclusion=None)],
            semantic_disposition="SEMANTIC_SIBLING",
            hard_gates_pass=True,
            exploration_benefit_score=9,
            exploration_cost_score=1,
        )
        self.assertEqual(receipt.route, ROUTE_WAIT)
        self.assertFalse(receipt.semantic_admission_evaluated)

    def test_queued_waits_without_hyperscale_admission(self):
        receipt = route_workflow_through_hyperscale(
            run=run(status="queued", conclusion=None),
            jobs=[],
            semantic_disposition="SUPPORT_MERGE",
            hard_gates_pass=True,
        )
        self.assertEqual(receipt.route, ROUTE_WAIT)
        self.assertFalse(receipt.semantic_admission_evaluated)

    def test_terminal_zero_job_non_provider_state_is_insufficient(self):
        receipt = route_workflow_through_hyperscale(
            run=run(conclusion="cancelled"),
            jobs=[],
            semantic_disposition="SEMANTIC_SIBLING",
            hard_gates_pass=True,
            exploration_benefit_score=9,
            exploration_cost_score=1,
        )
        self.assertEqual(receipt.route, ROUTE_INSUFFICIENT)
        self.assertEqual(receipt.execution_classification, "TERMINAL_WITHOUT_JOB_EVIDENCE")
        self.assertFalse(receipt.semantic_admission_evaluated)

    def test_executed_failure_can_reach_existing_exploration_owner_without_deriving_semantics(self):
        receipt = route_workflow_through_hyperscale(
            run=run(conclusion="failure"),
            jobs=[job(conclusion="failure")],
            semantic_disposition="SEMANTIC_SIBLING",
            hard_gates_pass=True,
            exploration_benefit_score=3,
            exploration_cost_score=1,
        )
        self.assertEqual(receipt.route, ROUTE_SEMANTIC)
        self.assertEqual(receipt.execution_classification, "EXECUTED_JOB_FAILURE_OBSERVED")
        self.assertTrue(receipt.semantic_admission_evaluated)
        self.assertEqual(receipt.semantic_admission_payload["mode"], "EXPLORATION")
        self.assertTrue(receipt.semantic_admission_payload["admitted"])
        self.assertFalse(receipt.execution_evidence_grants_semantic_meaning)

    def test_executed_success_can_reach_existing_verification_owner(self):
        observation = EvidenceObservation("bounded", ("LEAF",), 1, 8)
        receipt = route_workflow_through_hyperscale(
            run=run(conclusion="success"),
            jobs=[job(conclusion="success")],
            semantic_disposition="SUPPORT_MERGE",
            hard_gates_pass=True,
            unresolved_leaves=("LEAF",),
            observations=(observation,),
            verification_benefit_score=2,
        )
        self.assertEqual(receipt.route, ROUTE_SEMANTIC)
        self.assertEqual(receipt.execution_classification, "EXECUTED_JOB_SUCCESS_OBSERVED")
        self.assertEqual(receipt.semantic_admission_payload["mode"], "VERIFICATION")
        self.assertEqual(receipt.semantic_admission_payload["selected_observation_ids"], ("bounded",))
        self.assertTrue(receipt.semantic_admission_payload["eligible_to_add_new_egk"])

    def test_process_duplicate_remains_no_work_after_execution(self):
        receipt = route_workflow_through_hyperscale(
            run=run(),
            jobs=[job()],
            semantic_disposition="PROCESS_DUPLICATE",
            hard_gates_pass=True,
        )
        self.assertEqual(receipt.route, ROUTE_SEMANTIC)
        self.assertEqual(receipt.semantic_admission_payload["mode"], "NO_WORK_PROCESS_DUPLICATE")
        self.assertFalse(receipt.semantic_admission_payload["admitted"])

    def test_execution_classification_never_infers_semantic_disposition(self):
        receipt = route_workflow_through_hyperscale(
            run=run(),
            jobs=[job()],
            semantic_disposition="EXECUTED_JOB_SUCCESS_OBSERVED",
            hard_gates_pass=True,
            exploration_benefit_score=100,
            exploration_cost_score=1,
        )
        self.assertEqual(receipt.route, ROUTE_SEMANTIC)
        self.assertEqual(receipt.semantic_admission_payload["mode"], "REJECTED")
        self.assertFalse(receipt.semantic_admission_payload["admitted"])
        self.assertFalse(receipt.execution_evidence_grants_semantic_meaning)

    def test_job_record_defeats_run_label_only_provider_classification(self):
        receipt = route_workflow_through_hyperscale(
            run=run(conclusion="action_required"),
            jobs=[job(conclusion="failure")],
            semantic_disposition="PROCESS_DUPLICATE",
            hard_gates_pass=True,
        )
        self.assertEqual(receipt.execution_classification, "EXECUTED_JOB_FAILURE_OBSERVED")
        self.assertEqual(receipt.route, ROUTE_SEMANTIC)

    def test_nonpromotion_ceiling_is_fixed(self):
        receipt = route_workflow_through_hyperscale(
            run=run(conclusion="action_required"),
            jobs=[],
            semantic_disposition="SEMANTIC_SIBLING",
            hard_gates_pass=True,
        )
        for key in (
            "provider_gate_counts_as_semantic_failure",
            "provider_gate_counts_as_new_sck",
            "provider_gate_counts_as_new_egk",
            "execution_evidence_grants_semantic_meaning",
            "execution_evidence_grants_effect_authority",
            "automatic_retry_scheduled",
            "process_retry_inflates_evidence_mass",
            "k27_coordinate_growth_grants_semantic_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(receipt, key), key)

    def test_receipt_is_deterministic(self):
        kwargs = dict(
            run=run(conclusion="action_required", run_id=42),
            jobs=[],
            semantic_disposition="SUPPORT_MERGE",
            hard_gates_pass=True,
        )
        a = route_workflow_through_hyperscale(**kwargs)
        b = route_workflow_through_hyperscale(**kwargs)
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_parent_classifier_validation_is_preserved(self):
        with self.assertRaises(WorkflowEvidenceError):
            route_workflow_through_hyperscale(
                run={"id": True, "name": "x", "head_sha": HEAD, "status": "completed", "conclusion": "success"},
                jobs=[],
                semantic_disposition="PROCESS_DUPLICATE",
                hard_gates_pass=True,
            )


if __name__ == "__main__":
    unittest.main()

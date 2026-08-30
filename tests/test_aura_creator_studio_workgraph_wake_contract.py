import unittest

from aura_creator_studio_workgraph import (
    Priority,
    WorkItem,
    WorkState,
    WorkerSpec,
    project_workgraph,
)
from aura_creator_studio_workgraph_wake_contract import (
    choose_worker,
    compile_wake_bindings,
    validate_wake_intent_binding,
)

NOW = 2_000_000
CURRENT = "front-door-r8"


def worker(worker_id):
    return WorkerSpec(
        worker_id=worker_id,
        worker_class="CHATGPT",
        capabilities=("python",),
        join_ref=f"join:{worker_id}",
        currentness_basis=CURRENT,
        effect_ceiling="D0",
    )


def work(residual="close H-C/H-G seam"):
    return WorkItem(
        work_id="H-C-WAKE-1",
        state=WorkState.OPEN,
        priority=Priority.P0,
        parent_objective="CS-HARNESS-001",
        residual=residual,
        currentness_basis=CURRENT,
        required_capabilities=("python",),
        cost_ceiling_microusd=0,
        hydration_refs=("drive:hc",),
    )


def snapshot(workers, *, residual="close H-C/H-G seam", invalidators=()):
    return project_workgraph(
        project_id="CS-PROJ-001",
        canonical_orientation_ref="drive:front-door",
        canonical_orientation_revision=CURRENT,
        board_ref="drive:board",
        board_revision="board-r1",
        generated_at_ms=NOW,
        workers=workers,
        work_items=(work(residual),),
        route_policy_ref="drive:route",
        currentness_invalidators=invalidators,
    )


class WorkGraphWakeContractTests(unittest.TestCase):
    def test_candidate_worker_churn_does_not_mint_new_logical_work_version(self):
        first = compile_wake_bindings(snapshot((worker("W1"),)), mission_id="CS-HARNESS-001")[0]
        second = compile_wake_bindings(snapshot((worker("W1"), worker("W2"))), mission_id="CS-HARNESS-001")[0]
        self.assertEqual(first.work_version, second.work_version)
        self.assertEqual(first.assignment_key, second.assignment_key)
        self.assertNotEqual(first.candidate_worker_ids, second.candidate_worker_ids)

    def test_semantic_work_change_mints_new_work_version_and_assignment_key(self):
        first = compile_wake_bindings(snapshot((worker("W1"),)), mission_id="CS-HARNESS-001")[0]
        second = compile_wake_bindings(snapshot((worker("W1"),), residual="different residual"), mission_id="CS-HARNESS-001")[0]
        self.assertNotEqual(first.work_version, second.work_version)
        self.assertNotEqual(first.assignment_key, second.assignment_key)

    def test_stale_projection_emits_no_eligible_wake_binding(self):
        bindings = compile_wake_bindings(
            snapshot((worker("W1"),), invalidators=("front-door-moved",)),
            mission_id="CS-HARNESS-001",
        )
        self.assertEqual((), bindings)

    def test_worker_selection_is_deterministic_and_distinctness_aware(self):
        binding = compile_wake_bindings(snapshot((worker("W2"), worker("W1"))), mission_id="CS-HARNESS-001")[0]
        self.assertEqual("W1", choose_worker(binding))
        self.assertEqual("W2", choose_worker(binding, already_assigned=frozenset({"W1"})))
        self.assertIsNone(choose_worker(binding, already_assigned=frozenset({"W1", "W2"})))

    def test_current_hg_wake_intent_fields_validate_fail_closed(self):
        binding = compile_wake_bindings(snapshot((worker("W1"),)), mission_id="CS-HARNESS-001")[0]
        good = {
            "mission_id": "CS-HARNESS-001",
            "worker_id": "W1",
            "work_id": binding.work_id,
            "work_version": binding.work_version,
            "execution_authorized": False,
            "provider_calls_authorized": False,
            "background_execution_claimed": False,
        }
        self.assertEqual((True, ()), validate_wake_intent_binding(good, binding))
        bad = dict(good, worker_id="W9", background_execution_claimed=True)
        valid, reasons = validate_wake_intent_binding(bad, binding)
        self.assertFalse(valid)
        self.assertIn("WORKER_NOT_ELIGIBLE_FOR_BINDING", reasons)
        self.assertIn("BACKGROUND_EXECUTION_CLAIM_FORBIDDEN", reasons)


if __name__ == "__main__":
    unittest.main()

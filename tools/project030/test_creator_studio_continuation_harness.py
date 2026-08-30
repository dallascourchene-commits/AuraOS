import unittest

from creator_studio_continuation_harness import (
    HarnessRefusal,
    HarnessState,
    Residual,
    WorkItem,
    WorkerContext,
    advance_gate,
    assert_terminal_allowed,
    claim_best_available,
    complete_and_continue,
    continuation_snapshot,
)


MISSION = "CS-HARNESS-001"
CANONICAL = "CREATOR-STUDIO-PUBG"


def state_with(*items):
    state = HarnessState(MISSION, CANONICAL, temporary_mission=True)
    for item in items:
        state.add_work(item)
    return state


class ContinuationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.worker = WorkerContext("W-A", frozenset({"python", "verify"}))

    def test_finish_release_scan_claims_next_without_reprompt(self):
        state = state_with(
            WorkItem("A", MISSION, "first", priority=1),
            WorkItem("B", MISSION, "second", priority=2),
        )
        self.assertEqual(claim_best_available(state, self.worker).work_id, "A")
        nxt = complete_and_continue(state, self.worker, "A")
        self.assertEqual(nxt.action, "CLAIM_AND_CONTINUE")
        self.assertEqual(nxt.work_id, "B")
        self.assertFalse(nxt.requires_inference)

    def test_material_residual_compiles_successor_and_claims_it(self):
        state = state_with(WorkItem("A", MISSION, "first"))
        claim_best_available(state, self.worker)
        nxt = complete_and_continue(
            state,
            self.worker,
            "A",
            residuals=[Residual("Build verifier for newly found seam", MISSION, consequence=5)],
        )
        self.assertTrue(nxt.work_id.startswith("GROUP-WO-"))
        self.assertEqual(state.work[nxt.work_id].parent_work_id, "A")

    def test_duplicate_residual_is_deduplicated(self):
        state = state_with(WorkItem("A", MISSION, "first"), WorkItem("B", MISSION, "second"))
        claim_best_available(state, self.worker)
        residual = Residual("Same residual", MISSION, consequence=1)
        complete_and_continue(state, self.worker, "A", residuals=[residual, residual])
        generated = [work for work in state.work.values() if work.work_id.startswith("GROUP-WO-")]
        self.assertEqual(len(generated), 1)

    def test_nonmaterial_or_zero_consequence_residual_does_not_create_busywork(self):
        state = state_with(WorkItem("A", MISSION, "first"))
        claim_best_available(state, self.worker)
        action = complete_and_continue(
            state,
            self.worker,
            "A",
            residuals=[
                Residual("write another summary", MISSION, consequence=0),
                Residual("pretty but unbound", MISSION, consequence=9, material=False),
            ],
        )
        self.assertEqual(action.reason, "NO_ELIGIBLE_WORK_AFTER_REVIEW")
        self.assertEqual(len(state.work), 1)

    def test_dependencies_block_until_complete(self):
        state = state_with(
            WorkItem("A", MISSION, "first", priority=1),
            WorkItem("B", MISSION, "depends", dependencies=("A",), priority=0),
        )
        self.assertEqual(claim_best_available(state, self.worker).work_id, "A")
        self.assertEqual(complete_and_continue(state, self.worker, "A").work_id, "B")

    def test_claimed_work_is_not_duplicated(self):
        state = state_with(WorkItem("A", MISSION, "only"))
        self.assertEqual(claim_best_available(state, self.worker).work_id, "A")
        other = WorkerContext("W-B", frozenset({"python"}))
        self.assertEqual(claim_best_available(state, other).reason, "NO_ELIGIBLE_WORK_AFTER_REVIEW")

    def test_comparative_capability_filter(self):
        state = state_with(
            WorkItem("A", MISSION, "needs verify", required_capabilities=frozenset({"verify"})),
            WorkItem("B", MISSION, "needs blender", required_capabilities=frozenset({"blender"})),
        )
        self.assertEqual(claim_best_available(state, self.worker).work_id, "A")

    def test_priority_then_review_then_backburner(self):
        for stage, reason in (
            ("PRIORITY", "CLAIM_PRIORITY"),
            ("REVIEW", "CLAIM_REVIEW"),
            ("BACKBURNER", "CLAIM_BACKBURNER"),
        ):
            with self.subTest(stage=stage):
                state = state_with(WorkItem("X", MISSION, "x", stage=stage))
                self.assertEqual(claim_best_available(state, self.worker).reason, reason)

    def test_wrong_mission_work_is_not_selected(self):
        state = state_with(WorkItem("X", "OTHER", "wrong mission"))
        self.assertEqual(claim_best_available(state, self.worker).reason, "NO_ELIGIBLE_WORK_AFTER_REVIEW")

    def test_currentness_forces_rebase(self):
        state = state_with(WorkItem("A", MISSION, "work"))
        state.currentness = "STALE"
        action = claim_best_available(state, self.worker)
        self.assertEqual(action.action, "REBASE")
        self.assertEqual(action.reason, "SUPERSEDED_CURRENTNESS")

    def test_premature_chat_terminal_is_refused_while_work_remains(self):
        state = state_with(WorkItem("A", MISSION, "work"))
        with self.assertRaisesRegex(HarnessRefusal, "PREMATURE_TERMINAL_REFUSED"):
            assert_terminal_allowed(state, self.worker, "ANSWER_DELIVERED")

    def test_no_eligible_work_terminal_is_fail_closed_if_work_exists(self):
        state = state_with(WorkItem("A", MISSION, "work"))
        with self.assertRaisesRegex(HarnessRefusal, "ELIGIBLE_WORK_REMAINS"):
            assert_terminal_allowed(state, self.worker, "NO_ELIGIBLE_WORK_AFTER_REVIEW")

    def test_gate_requires_sequential_durable_evidence(self):
        state = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_REQUIRED"):
            advance_gate(state, 1, [])
        self.assertEqual(advance_gate(state, 1, ["receipt:1"]), 1)
        with self.assertRaisesRegex(HarnessRefusal, "GATE_SEQUENCE_VIOLATION"):
            advance_gate(state, 3, ["receipt:3"])

    def test_gate10_automatically_restores_canonical_mission(self):
        state = state_with()
        for gate in range(1, 11):
            advance_gate(state, gate, [f"receipt:{gate}"])
        action = claim_best_available(state, self.worker)
        self.assertEqual(action.reason, "GATE10_COMPLETE_CANONICAL_MISSION_RESTORED")
        self.assertEqual(state.active_mission_id, CANONICAL)
        self.assertFalse(state.temporary_mission)

    def test_deterministic_value_first_cost_aware_ranking(self):
        state = state_with(
            WorkItem("cheap-low-unlock", MISSION, "a", dependency_unlock=1, estimated_total_cost=0),
            WorkItem("high-unlock", MISSION, "b", dependency_unlock=5, estimated_total_cost=10),
            WorkItem("high-unlock-cheap", MISSION, "c", dependency_unlock=5, estimated_total_cost=0),
        )
        self.assertEqual(claim_best_available(state, self.worker).work_id, "high-unlock-cheap")

    def test_snapshot_declares_scheduler_zero_inference(self):
        state = state_with(WorkItem("A", MISSION, "work"))
        snapshot = continuation_snapshot(state, self.worker)
        self.assertFalse(snapshot["scheduler_requires_inference"])
        self.assertEqual(snapshot["eligible_counts"]["PRIORITY"], 1)


if __name__ == "__main__":
    unittest.main()

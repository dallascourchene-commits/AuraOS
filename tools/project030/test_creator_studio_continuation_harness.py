import copy
import unittest

from creator_studio_continuation_harness import (
    GATE_EVIDENCE_REQUIREMENTS,
    GateEvidence,
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


def evidence_for(gate):
    return [
        GateEvidence(
            evidence_class=evidence_class,
            ref=f"Drive:receipt:g{gate}:{index}",
        )
        for index, evidence_class in enumerate(
            sorted(GATE_EVIDENCE_REQUIREMENTS[gate]), start=1
        )
    ]


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

    def test_invalid_residual_is_transactional_and_leaves_state_unchanged(self):
        state = state_with(WorkItem("A", MISSION, "first"))
        claim_best_available(state, self.worker)
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(HarnessRefusal, "INVALID_RESIDUAL_STAGE"):
            complete_and_continue(
                state,
                self.worker,
                "A",
                residuals=[Residual("bad stage", MISSION, consequence=1, stage="INVALID")],
            )
        self.assertEqual(state.work["A"].state, before.work["A"].state)
        self.assertEqual(state.claims, before.claims)
        self.assertEqual(state.completed, before.completed)
        self.assertEqual(state.residual_fingerprints, before.residual_fingerprints)
        self.assertEqual(state.history, before.history)
        self.assertEqual(state._sequence, before._sequence)

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

    def test_worker_cannot_take_second_claim(self):
        state = state_with(
            WorkItem("A", MISSION, "first", priority=1),
            WorkItem("B", MISSION, "second", priority=2),
        )
        first = claim_best_available(state, self.worker)
        second = claim_best_available(state, self.worker)
        self.assertEqual(first.work_id, "A")
        self.assertEqual(second.action, "CONTINUE_ACTIVE_CLAIM")
        self.assertEqual(second.work_id, "A")
        self.assertEqual(state.work["B"].state, "OPEN")

    def test_corrupt_multiple_claims_for_one_worker_fail_closed(self):
        state = state_with(
            WorkItem("A", MISSION, "a"),
            WorkItem("B", MISSION, "b"),
        )
        state.claims = {"A": self.worker.worker_id, "B": self.worker.worker_id}
        state.work["A"].state = "ACTIVE"
        state.work["B"].state = "ACTIVE"
        with self.assertRaisesRegex(HarnessRefusal, "WORKER_MULTIPLE_ACTIVE_CLAIMS"):
            claim_best_available(state, self.worker)

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

    def test_no_eligible_terminal_rejects_worker_with_active_claim(self):
        state = state_with(WorkItem("A", MISSION, "work"))
        claim_best_available(state, self.worker)
        with self.assertRaisesRegex(HarnessRefusal, "ACTIVE_CLAIM_REMAINS"):
            assert_terminal_allowed(state, self.worker, "NO_ELIGIBLE_WORK_AFTER_REVIEW")

    def test_gate_requires_typed_evidence_not_arbitrary_strings(self):
        state = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_TYPE_REQUIRED"):
            advance_gate(state, 1, ["receipt:1"])

    def test_gate_requires_sequential_required_evidence_class(self):
        state = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_REQUIRED"):
            advance_gate(state, 1, [])
        self.assertEqual(advance_gate(state, 1, evidence_for(1)), 1)
        with self.assertRaisesRegex(HarnessRefusal, "GATE_SEQUENCE_VIOLATION"):
            advance_gate(state, 3, evidence_for(3))

    def test_gate_rejects_missing_required_evidence_class(self):
        state = state_with()
        wrong = [GateEvidence("SOMETHING_ELSE", "Drive:wrong")]
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_CLASS_MISSING"):
            advance_gate(state, 1, wrong)

    def test_gate_rejects_unverified_or_stale_or_unbound_evidence(self):
        for bad, code in (
            (GateEvidence("ARENA_ADMISSION_RECEIPT", "Drive:x", verified=False), "GATE_EVIDENCE_NOT_VERIFIED"),
            (GateEvidence("ARENA_ADMISSION_RECEIPT", "Drive:x", currentness="STALE"), "GATE_EVIDENCE_NOT_CURRENT"),
            (GateEvidence("ARENA_ADMISSION_RECEIPT", "Drive:x", receipt_bound=False), "GATE_EVIDENCE_NOT_RECEIPT_BOUND"),
        ):
            with self.subTest(code=code):
                state = state_with()
                with self.assertRaisesRegex(HarnessRefusal, code):
                    advance_gate(state, 1, [bad])

    def test_gate10_requires_all_convergence_evidence_classes(self):
        state = state_with()
        for gate in range(1, 10):
            advance_gate(state, gate, evidence_for(gate))
        partial = evidence_for(10)[:-1]
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_CLASS_MISSING"):
            advance_gate(state, 10, partial)

    def test_gate10_automatically_restores_canonical_mission_once(self):
        state = state_with()
        for gate in range(1, 11):
            advance_gate(state, gate, evidence_for(gate))
        action = claim_best_available(state, self.worker)
        self.assertEqual(action.reason, "GATE10_COMPLETE_CANONICAL_MISSION_RESTORED")
        self.assertEqual(state.active_mission_id, CANONICAL)
        self.assertFalse(state.temporary_mission)
        self.assertTrue(state.canonical_mission_restored)
        returns = [event for event in state.history if event.get("event") == "MISSION_RETURN"]
        self.assertEqual(len(returns), 1)

        state.add_work(WorkItem("CANONICAL-WORK", CANONICAL, "resume creator studio"))
        second = claim_best_available(state, self.worker)
        self.assertEqual(second.action, "CLAIM_AND_CONTINUE")
        self.assertEqual(second.work_id, "CANONICAL-WORK")
        returns = [event for event in state.history if event.get("event") == "MISSION_RETURN"]
        self.assertEqual(len(returns), 1)

    def test_explicit_second_restore_is_refused(self):
        state = state_with()
        for gate in range(1, 11):
            advance_gate(state, gate, evidence_for(gate))
        claim_best_available(state, self.worker)
        from creator_studio_continuation_harness import restore_canonical_mission
        with self.assertRaisesRegex(HarnessRefusal, "CANONICAL_MISSION_ALREADY_RESTORED"):
            restore_canonical_mission(state)

    def test_owner_stop_terminal_requires_owner_stop_state(self):
        state = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "OWNER_STOP_NOT_EVIDENCED"):
            assert_terminal_allowed(state, self.worker, "OWNER_STOP")
        state.owner_stop = True
        assert_terminal_allowed(state, self.worker, "OWNER_STOP")

    def test_external_boundary_terminal_requires_evidence(self):
        state = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "EXTERNAL_BOUNDARY_EVIDENCE_REQUIRED"):
            assert_terminal_allowed(state, self.worker, "BLOCKED_EXTERNAL_BOUNDARY")
        state.external_boundary_refs.add("Drive:authority-blocker")
        assert_terminal_allowed(state, self.worker, "BLOCKED_EXTERNAL_BOUNDARY")

    def test_superseded_terminal_requires_noncurrent_state(self):
        state = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "CURRENTNESS_NOT_SUPERSEDED"):
            assert_terminal_allowed(state, self.worker, "SUPERSEDED_CURRENTNESS")
        state.currentness = "STALE"
        assert_terminal_allowed(state, self.worker, "SUPERSEDED_CURRENTNESS")

    def test_gate10_terminal_requires_typed_gate10_evidence(self):
        state = state_with()
        state.gate = 10
        with self.assertRaisesRegex(HarnessRefusal, "GATE10_EVIDENCE_NOT_BOUND"):
            assert_terminal_allowed(state, self.worker, "GATE10_COMPLETE")

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
        self.assertEqual(snapshot["worker_active_claims"], [])


if __name__ == "__main__":
    unittest.main()

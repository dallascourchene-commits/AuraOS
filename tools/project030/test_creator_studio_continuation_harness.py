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
    s = HarnessState(MISSION, CANONICAL, temporary_mission=True)
    for item in items:
        s.add_work(item)
    return s


class ContinuationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.worker = WorkerContext("W-A", frozenset({"python", "verify"}))

    def test_finish_release_scan_claims_next_without_reprompt(self):
        s = state_with(
            WorkItem("A", MISSION, "first", priority=1),
            WorkItem("B", MISSION, "second", priority=2),
        )
        first = claim_best_available(s, self.worker)
        self.assertEqual(first.work_id, "A")
        nxt = complete_and_continue(s, self.worker, "A")
        self.assertEqual(nxt.action, "CLAIM_AND_CONTINUE")
        self.assertEqual(nxt.work_id, "B")
        self.assertFalse(nxt.requires_inference)

    def test_material_residual_compiles_successor_and_claims_it(self):
        s = state_with(WorkItem("A", MISSION, "first"))
        claim_best_available(s, self.worker)
        nxt = complete_and_continue(
            s,
            self.worker,
            "A",
            residuals=[Residual("Build verifier for newly found seam", MISSION, consequence=5)],
        )
        self.assertTrue(nxt.work_id.startswith("GROUP-WO-"))
        self.assertEqual(s.work[nxt.work_id].parent_work_id, "A")

    def test_duplicate_residual_is_deduplicated(self):
        s = state_with(WorkItem("A", MISSION, "first"), WorkItem("B", MISSION, "second"))
        claim_best_available(s, self.worker)
        r = Residual("Same residual", MISSION, consequence=1)
        complete_and_continue(s, self.worker, "A", residuals=[r, r])
        generated = [w for w in s.work.values() if w.work_id.startswith("GROUP-WO-")]
        self.assertEqual(len(generated), 1)

    def test_nonmaterial_or_zero_consequence_residual_does_not_create_busywork(self):
        s = state_with(WorkItem("A", MISSION, "first"))
        claim_best_available(s, self.worker)
        action = complete_and_continue(
            s,
            self.worker,
            "A",
            residuals=[
                Residual("write another summary", MISSION, consequence=0),
                Residual("pretty but unbound", MISSION, consequence=9, material=False),
            ],
        )
        self.assertEqual(action.reason, "NO_ELIGIBLE_WORK_AFTER_REVIEW")
        self.assertEqual(len(s.work), 1)

    def test_dependencies_block_until_complete(self):
        s = state_with(
            WorkItem("A", MISSION, "first", priority=1),
            WorkItem("B", MISSION, "depends", dependencies=("A",), priority=0),
        )
        self.assertEqual(claim_best_available(s, self.worker).work_id, "A")
        self.assertEqual(complete_and_continue(s, self.worker, "A").work_id, "B")

    def test_claimed_work_is_not_duplicated(self):
        s = state_with(WorkItem("A", MISSION, "only"))
        self.assertEqual(claim_best_available(s, self.worker).work_id, "A")
        other = WorkerContext("W-B", frozenset({"python"}))
        self.assertEqual(claim_best_available(s, other).reason, "NO_ELIGIBLE_WORK_AFTER_REVIEW")

    def test_comparative_capability_filter(self):
        s = state_with(
            WorkItem("A", MISSION, "needs verify", required_capabilities=frozenset({"verify"})),
            WorkItem("B", MISSION, "needs blender", required_capabilities=frozenset({"blender"})),
        )
        self.assertEqual(claim_best_available(s, self.worker).work_id, "A")

    def test_priority_then_review_then_backburner(self):
        for stage, reason in (("PRIORITY", "CLAIM_PRIORITY"), ("REVIEW", "CLAIM_REVIEW"), ("BACKBURNER", "CLAIM_BACKBURNER")):
            with self.subTest(stage=stage):
                s = state_with(WorkItem("X", MISSION, "x", stage=stage))
                self.assertEqual(claim_best_available(s, self.worker).reason, reason)

    def test_wrong_mission_work_is_not_selected(self):
        s = state_with(WorkItem("X", "OTHER", "wrong mission"))
        self.assertEqual(claim_best_available(s, self.worker).reason, "NO_ELIGIBLE_WORK_AFTER_REVIEW")

    def test_currentness_forces_rebase(self):
        s = state_with(WorkItem("A", MISSION, "work"))
        s.currentness = "STALE"
        action = claim_best_available(s, self.worker)
        self.assertEqual(action.action, "REBASE")
        self.assertEqual(action.reason, "SUPERSEDED_CURRENTNESS")

    def test_premature_chat_terminal_is_refused_while_work_remains(self):
        s = state_with(WorkItem("A", MISSION, "work"))
        with self.assertRaisesRegex(HarnessRefusal, "PREMATURE_TERMINAL_REFUSED"):
            assert_terminal_allowed(s, self.worker, "ANSWER_DELIVERED")

    def test_no_eligible_work_terminal_is_fail_closed_if_work_exists(self):
        s = state_with(WorkItem("A", MISSION, "work"))
        with self.assertRaisesRegex(HarnessRefusal, "ELIGIBLE_WORK_REMAINS"):
            assert_terminal_allowed(s, self.worker, "NO_ELIGIBLE_WORK_AFTER_REVIEW")

    def test_gate_requires_sequential_typed_evidence(self):
        s = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_REQUIRED"):
            advance_gate(s, 1, [])
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_SHAPE_INVALID"):
            advance_gate(s, 1, ["receipt:1"])
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_CLASS_MISSING"):
            advance_gate(s, 1, [GateEvidence("WRONG_CLASS", "receipt:1")])
        self.assertEqual(
            advance_gate(s, 1, [GateEvidence("ARENA_ADMISSION_RECEIPT", "receipt:1")]),
            1,
        )
        with self.assertRaisesRegex(HarnessRefusal, "GATE_SEQUENCE_VIOLATION"):
            advance_gate(
                s,
                3,
                [GateEvidence("CONTINUATION_REPLAY_RECEIPT", "receipt:3")],
            )

    def test_gate10_requires_all_convergence_evidence_classes(self):
        s = state_with()
        for gate in range(1, 10):
            evidence_class = next(iter(GATE_EVIDENCE_REQUIREMENTS[gate]))
            advance_gate(s, gate, [GateEvidence(evidence_class, f"receipt:{gate}")])
        incomplete = [
            GateEvidence("DIFFERENT_J_REVIEW_RECEIPT", "review"),
            GateEvidence("RESTART_REPLAY_RECEIPT", "restart"),
        ]
        with self.assertRaisesRegex(HarnessRefusal, "GATE_EVIDENCE_CLASS_MISSING"):
            advance_gate(s, 10, incomplete)

    def test_gate10_automatically_restores_canonical_mission(self):
        s = state_with()
        for gate in range(1, 11):
            evidence = [
                GateEvidence(evidence_class, f"receipt:{gate}:{evidence_class}")
                for evidence_class in sorted(GATE_EVIDENCE_REQUIREMENTS[gate])
            ]
            advance_gate(s, gate, evidence)
        action = claim_best_available(s, self.worker)
        self.assertEqual(action.reason, "GATE10_COMPLETE_CANONICAL_MISSION_RESTORED")
        self.assertEqual(s.active_mission_id, CANONICAL)
        self.assertFalse(s.temporary_mission)

    def test_owner_stop_terminal_requires_owner_stop_predicate(self):
        s = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "OWNER_STOP_NOT_BOUND"):
            assert_terminal_allowed(s, self.worker, "OWNER_STOP")
        s.owner_stop = True
        assert_terminal_allowed(s, self.worker, "OWNER_STOP")

    def test_external_boundary_terminal_requires_bound_evidence(self):
        s = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "EXTERNAL_BOUNDARY_NOT_BOUND"):
            assert_terminal_allowed(s, self.worker, "BLOCKED_EXTERNAL_BOUNDARY")
        s.external_boundary_ref = "owner-decision:cost"
        assert_terminal_allowed(s, self.worker, "BLOCKED_EXTERNAL_BOUNDARY")

    def test_superseded_currentness_terminal_requires_stale_state(self):
        s = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "CURRENTNESS_NOT_SUPERSEDED"):
            assert_terminal_allowed(s, self.worker, "SUPERSEDED_CURRENTNESS")
        s.currentness = "STALE-R10"
        assert_terminal_allowed(s, self.worker, "SUPERSEDED_CURRENTNESS")

    def test_gate10_terminal_requires_gate10(self):
        s = state_with()
        with self.assertRaisesRegex(HarnessRefusal, "GATE10_NOT_REACHED"):
            assert_terminal_allowed(s, self.worker, "GATE10_COMPLETE")

    def test_deterministic_value_first_cost_aware_ranking(self):
        s = state_with(
            WorkItem("cheap-low-unlock", MISSION, "a", dependency_unlock=1, estimated_total_cost=0),
            WorkItem("high-unlock", MISSION, "b", dependency_unlock=5, estimated_total_cost=10),
            WorkItem("high-unlock-cheap", MISSION, "c", dependency_unlock=5, estimated_total_cost=0),
        )
        self.assertEqual(claim_best_available(s, self.worker).work_id, "high-unlock-cheap")

    def test_snapshot_declares_scheduler_zero_inference(self):
        s = state_with(WorkItem("A", MISSION, "work"))
        snap = continuation_snapshot(s, self.worker)
        self.assertFalse(snap["scheduler_requires_inference"])
        self.assertEqual(snap["eligible_counts"]["PRIORITY"], 1)


if __name__ == "__main__":
    unittest.main()

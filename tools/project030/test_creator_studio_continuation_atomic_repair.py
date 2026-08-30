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
    claim_best_available,
    complete_and_continue,
    restore_canonical_mission,
)

MISSION = "CS-HARNESS-001"
CANONICAL = "CREATOR-STUDIO-PUBG"


def state_with(*items):
    state = HarnessState(MISSION, CANONICAL, temporary_mission=True)
    for item in items:
        state.add_work(item)
    return state


class AtomicContinuationRepairTests(unittest.TestCase):
    def setUp(self):
        self.worker = WorkerContext("W-A", frozenset({"python", "verify"}))

    def test_worker_with_active_claim_continues_instead_of_double_claiming(self):
        state = state_with(
            WorkItem("A", MISSION, "first", priority=1),
            WorkItem("B", MISSION, "second", priority=2),
        )
        first = claim_best_available(state, self.worker)
        self.assertEqual(first.work_id, "A")
        second = claim_best_available(state, self.worker)
        self.assertEqual(second.action, "CONTINUE_ACTIVE_CLAIM")
        self.assertEqual(second.work_id, "A")
        self.assertEqual(state.claims, {"A": "W-A"})
        self.assertEqual(state.work["B"].state, "OPEN")

    def test_multiple_existing_worker_claims_fail_closed(self):
        state = state_with(
            WorkItem("A", MISSION, "first"),
            WorkItem("B", MISSION, "second"),
        )
        state.work["A"].state = "ACTIVE"
        state.work["B"].state = "ACTIVE"
        state.claims.update({"A": "W-A", "B": "W-A"})
        with self.assertRaisesRegex(HarnessRefusal, "WORKER_MULTIPLE_ACTIVE_CLAIMS"):
            claim_best_available(state, self.worker)

    def test_invalid_successor_rolls_back_finish_release_transaction(self):
        state = state_with(WorkItem("A", MISSION, "first"))
        claim_best_available(state, self.worker)
        history_before = list(state.history)
        sequence_before = state._sequence
        with self.assertRaisesRegex(HarnessRefusal, "INVALID_RESIDUAL_STAGE"):
            complete_and_continue(
                state,
                self.worker,
                "A",
                residuals=[
                    Residual(
                        "bad staged successor",
                        MISSION,
                        consequence=1,
                        stage="NOT_A_STAGE",
                    )
                ],
            )
        self.assertEqual(state.work["A"].state, "ACTIVE")
        self.assertEqual(state.claims, {"A": "W-A"})
        self.assertNotIn("A", state.completed)
        self.assertEqual(state.history, history_before)
        self.assertEqual(state._sequence, sequence_before)

    def test_gate10_mission_return_is_one_shot_and_then_scans_canonical_work(self):
        state = state_with()
        for gate in range(1, 11):
            evidence = [
                GateEvidence(kind, f"receipt:{gate}:{kind}")
                for kind in sorted(GATE_EVIDENCE_REQUIREMENTS[gate])
            ]
            advance_gate(state, gate, evidence)
        first = claim_best_available(state, self.worker)
        self.assertEqual(first.reason, "GATE10_COMPLETE_CANONICAL_MISSION_RESTORED")
        returns = [event for event in state.history if event.get("event") == "MISSION_RETURN"]
        self.assertEqual(len(returns), 1)
        second = claim_best_available(state, self.worker)
        self.assertEqual(second.reason, "NO_ELIGIBLE_WORK_AFTER_REVIEW")
        returns = [event for event in state.history if event.get("event") == "MISSION_RETURN"]
        self.assertEqual(len(returns), 1)
        with self.assertRaisesRegex(HarnessRefusal, "CANONICAL_MISSION_ALREADY_RESTORED"):
            restore_canonical_mission(state)

    def test_gate10_after_restore_can_claim_canonical_mission_work(self):
        state = state_with()
        state.add_work(WorkItem("C", CANONICAL, "canonical next work"))
        for gate in range(1, 11):
            evidence = [
                GateEvidence(kind, f"receipt:{gate}:{kind}")
                for kind in sorted(GATE_EVIDENCE_REQUIREMENTS[gate])
            ]
            advance_gate(state, gate, evidence)
        claim_best_available(state, self.worker)
        next_action = claim_best_available(state, self.worker)
        self.assertEqual(next_action.action, "CLAIM_AND_CONTINUE")
        self.assertEqual(next_action.work_id, "C")


if __name__ == "__main__":
    unittest.main()

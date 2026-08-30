import tempfile
import unittest
from pathlib import Path

from creator_studio_continuation_harness import (
    HarnessRefusal,
    HarnessState,
    Residual,
    WorkItem,
    WorkerContext,
    advance_gate,
    claim_best_available,
    complete_and_continue,
)
from creator_studio_wake_adapter import ArenaWakeScheduler, FileWakeLedger

MISSION = "CS-HARNESS-001"
CANONICAL = "CREATOR-STUDIO-PUBG"


def state_with(*items):
    state = HarnessState(MISSION, CANONICAL, temporary_mission=True)
    for item in items:
        state.add_work(item)
    return state


class DifferentJIntegrationRegressions(unittest.TestCase):
    """Cross-lane regressions found while integrating H-A/H-B/H-G/WorkGraph.

    These tests are intentionally stronger than the isolated H-B/H-G reference
    batteries.  They encode the continual-work invariants required before the
    H-F fresh-worker probe and live Gate-10 credit.
    """

    def test_gate10_returns_mission_once_then_claims_canonical_work(self):
        worker = WorkerContext("W")
        state = state_with(WorkItem("CREATIVE", CANONICAL, "continue Creator Studio"))
        for gate in range(1, 11):
            advance_gate(state, gate, [f"receipt:{gate}"])
        first = claim_best_available(state, worker)
        self.assertEqual(first.reason, "GATE10_COMPLETE_CANONICAL_MISSION_RESTORED")
        self.assertFalse(state.temporary_mission)
        second = claim_best_available(state, worker)
        self.assertEqual(second.action, "CLAIM_AND_CONTINUE")
        self.assertEqual(second.work_id, "CREATIVE")
        returns = [event for event in state.history if event["event"] == "MISSION_RETURN"]
        self.assertEqual(len(returns), 1)

    def test_one_ordinary_worker_cannot_accumulate_two_claims(self):
        worker = WorkerContext("W")
        state = state_with(
            WorkItem("A", MISSION, "first"),
            WorkItem("B", MISSION, "second"),
        )
        first = claim_best_available(state, worker)
        second = claim_best_available(state, worker)
        self.assertEqual(first.work_id, "A")
        self.assertNotEqual(second.work_id, "B")
        self.assertEqual(sum(owner == "W" for owner in state.claims.values()), 1)

    def test_corrupt_multiple_claim_state_fails_closed(self):
        worker = WorkerContext("W")
        state = state_with(
            WorkItem("A", MISSION, "first"),
            WorkItem("B", MISSION, "second"),
        )
        for work_id in ("A", "B"):
            state.work[work_id].state = "ACTIVE"
            state.claims[work_id] = "W"
        with self.assertRaisesRegex(HarnessRefusal, "MULTIPLE_ACTIVE_CLAIMS"):
            claim_best_available(state, worker)

    def test_bad_late_residual_does_not_partially_finish_parent(self):
        worker = WorkerContext("W")
        state = state_with(WorkItem("A", MISSION, "first"))
        claim_best_available(state, worker)
        residuals = [
            Residual("valid successor", MISSION, consequence=1),
            Residual("bad successor", MISSION, consequence=1, stage="NOT_A_STAGE"),
        ]
        with self.assertRaisesRegex(HarnessRefusal, "INVALID_RESIDUAL_STAGE"):
            complete_and_continue(state, worker, "A", residuals=residuals)
        self.assertEqual(state.work["A"].state, "ACTIVE")
        self.assertNotIn("A", state.completed)
        self.assertEqual(state.claims.get("A"), "W")
        self.assertFalse(any(work_id.startswith("GROUP-WO-") for work_id in state.work))

    def test_one_wake_scan_targets_each_ordinary_worker_at_most_once(self):
        with tempfile.TemporaryDirectory() as td:
            scheduler = ArenaWakeScheduler(FileWakeLedger(Path(td)))
            state = state_with(
                WorkItem("A", MISSION, "first"),
                WorkItem("B", MISSION, "second"),
            )
            events = scheduler.scan_and_emit(state, [WorkerContext("W")])
            self.assertLessEqual(sum(event.worker_id == "W" for event in events), 1)

    def test_busy_worker_is_not_targeted_for_another_work_wake(self):
        with tempfile.TemporaryDirectory() as td:
            scheduler = ArenaWakeScheduler(FileWakeLedger(Path(td)))
            state = state_with(
                WorkItem("A", MISSION, "active"),
                WorkItem("B", MISSION, "new"),
            )
            state.work["A"].state = "ACTIVE"
            state.claims["A"] = "W"
            events = scheduler.scan_and_emit(state, [WorkerContext("W")])
            self.assertEqual(events, [])

    def test_same_work_version_is_not_retargeted_to_second_worker(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = FileWakeLedger(Path(td))
            scheduler = ArenaWakeScheduler(ledger)
            state = state_with(
                WorkItem("A", MISSION, "work", required_capabilities=frozenset({"python"}))
            )
            b = WorkerContext("B", frozenset({"python"}))
            a = WorkerContext("A", frozenset({"python", "verify"}))
            first = scheduler.scan_and_emit(state, [b], work_versions={"A": "wg-digest-1"})
            second = scheduler.scan_and_emit(state, [a, b], work_versions={"A": "wg-digest-1"})
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            self.assertEqual(len(ledger.events()), 1)

    def test_changed_work_semantics_change_default_wake_version(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = FileWakeLedger(Path(td))
            scheduler = ArenaWakeScheduler(ledger)
            state = state_with(WorkItem("A", MISSION, "first"))
            worker = WorkerContext("W")
            first = scheduler.scan_and_emit(state, [worker])
            state.work["A"].objective = "materially changed"
            second = scheduler.scan_and_emit(state, [worker])
            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertNotEqual(first[0].work_version, second[0].work_version)


if __name__ == "__main__":
    unittest.main()

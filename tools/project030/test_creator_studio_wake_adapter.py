import tempfile
import threading
import unittest
from pathlib import Path

from creator_studio_continuation_harness import HarnessState, WorkItem, WorkerContext
from creator_studio_wake_adapter import ArenaWakeScheduler, FileWakeLedger, WakeIntent


MISSION = "CS-HARNESS-001"
CANONICAL = "CREATOR-STUDIO-PUBG"


class WakeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = FileWakeLedger(Path(self.tmp.name) / "wake")
        self.scheduler = ArenaWakeScheduler(self.ledger)
        self.a = WorkerContext("A", frozenset({"python", "verify"}))
        self.b = WorkerContext("B", frozenset({"python"}))

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        return HarnessState(MISSION, CANONICAL, temporary_mission=True)

    def test_newly_eligible_work_emits_one_targeted_wake(self):
        state = self.state()
        state.add_work(WorkItem("W1", MISSION, "test", required_capabilities=frozenset({"python"})))
        events = self.scheduler.scan_and_emit(state, [self.b, self.a])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "WORK_ELIGIBLE")
        self.assertEqual(events[0].work_id, "W1")
        self.assertEqual(events[0].worker_id, "A")
        self.assertFalse(events[0].execution_authorized)
        self.assertFalse(events[0].background_execution_claimed)

    def test_repeated_scan_is_idempotent_on_disk(self):
        state = self.state()
        state.add_work(WorkItem("W1", MISSION, "test"))
        self.scheduler.scan_and_emit(state, [self.a])
        self.scheduler.scan_and_emit(state, [self.a])
        self.assertEqual(len(self.ledger.events()), 1)

    def test_dependency_completion_wakes_newly_eligible_work_version(self):
        state = self.state()
        state.add_work(WorkItem("A0", MISSION, "dependency"))
        state.add_work(WorkItem("B0", MISSION, "dependent", dependencies=("A0",)))
        first = self.scheduler.scan_and_emit(state, [self.a], work_versions={"A0": "v1", "B0": "v1"})
        self.assertEqual([event.work_id for event in first], ["A0"])
        state.work["A0"].state = "COMPLETE"
        state.completed.add("A0")
        second = self.scheduler.scan_and_emit(state, [self.a], work_versions={"B0": "v1"})
        self.assertEqual([event.work_id for event in second], ["B0"])

    def test_claimed_work_does_not_emit_wake(self):
        state = self.state()
        state.add_work(WorkItem("W1", MISSION, "test"))
        state.claims["W1"] = "OTHER"
        self.assertEqual(self.scheduler.scan_and_emit(state, [self.a]), [])

    def test_capability_mismatch_does_not_emit(self):
        state = self.state()
        state.add_work(WorkItem("W1", MISSION, "gpu", required_capabilities=frozenset({"gpu"})))
        self.assertEqual(self.scheduler.scan_and_emit(state, [self.a, self.b]), [])

    def test_stale_currentness_emits_rebase_not_work(self):
        state = self.state()
        state.currentness = "STALE-R9"
        state.add_work(WorkItem("W1", MISSION, "test"))
        events = self.scheduler.scan_and_emit(state, [self.a, self.b])
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event.event_type == "CURRENTNESS_REBASE_REQUIRED" for event in events))
        self.assertTrue(all(event.work_id is None for event in events))

    def test_reopen_version_allows_new_wake_without_rewriting_old_event(self):
        state = self.state()
        state.add_work(WorkItem("W1", MISSION, "test"))
        self.scheduler.scan_and_emit(state, [self.a], work_versions={"W1": "v1"})
        self.scheduler.scan_and_emit(state, [self.a], work_versions={"W1": "v2"})
        self.assertEqual(len(self.ledger.events()), 2)

    def test_restart_reuses_durable_ledger_idempotently(self):
        state = self.state()
        state.add_work(WorkItem("W1", MISSION, "test"))
        self.scheduler.scan_and_emit(state, [self.a])
        restarted = ArenaWakeScheduler(FileWakeLedger(self.ledger.root))
        restarted.scan_and_emit(state, [self.a])
        self.assertEqual(len(self.ledger.events()), 1)

    def test_atomic_append_same_intent_concurrently_lands_one_file(self):
        intent = WakeIntent(
            schema="CreatorStudioWakeIntentV1",
            event_id="same-event",
            event_type="WORK_ELIGIBLE",
            mission_id=MISSION,
            worker_id="A",
            work_id="W1",
            work_version="v1",
            reason="test",
        )
        outcomes = []
        errors = []
        barrier = threading.Barrier(8)

        def writer():
            try:
                barrier.wait()
                outcomes.append(self.ledger.append(intent))
            except Exception as exc:
                errors.append(repr(exc))

        threads = [threading.Thread(target=writer) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(self.ledger.events()), 1)
        self.assertEqual(outcomes.count("APPENDED"), 1)
        self.assertEqual(outcomes.count("IDEMPOTENT_REPLAY"), 7)


if __name__ == "__main__":
    unittest.main()

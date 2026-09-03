import tempfile
import time
import unittest
from pathlib import Path

from reference_kernel import (
    JoinContextCompiler,
    JSpaceEvent,
    JSpaceStore,
    ReconcileEngine,
    SourceState,
)


class CurrentnessIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JSpaceStore(Path(self.tmp.name) / "jspace.db")
        self.store.add_dep("src", "consumer")

    def tearDown(self):
        self.tmp.cleanup()

    def seed(self, *, current: bool = True, generation: str = "g1") -> None:
        payload = {
            "source_sequence": 1,
            "semantic_root": "R",
            "current": current,
        }
        event = JSpaceEvent(
            "seed-currentness",
            "RECONCILIATION" if current else "CURRENTNESS_INVALIDATION",
            1,
            "seed",
            "src",
            generation,
            "epoch-seed",
            "src",
            payload,
            time.time_ns(),
        )
        self.store.append(event)

    def engine(self, visit: str) -> ReconcileEngine:
        return ReconcileEngine(
            self.store,
            jid=1,
            visit_id=visit,
            owner_epoch=f"epoch-{visit}",
        )

    def snapshot(self, *, current: bool, generation: str = "g1") -> SourceState:
        return SourceState("src", generation, current, 1, "R")

    def reconcile(self, visit: str, *, current: bool, generation: str = "g1"):
        return self.engine(visit).reconcile(
            [self.snapshot(current=current, generation=generation)],
            all_nodes={"src", "consumer", "cold"},
            capability_nodes={"src", "consumer"},
        )

    def test_identical_false_snapshot_is_noop_after_first_invalidation(self):
        self.seed(current=True)
        first = self.reconcile("v1", current=False)
        second = self.reconcile("v1", current=False)
        self.assertEqual(("src",), first.changed_sources)
        self.assertEqual("NOOP_SOURCE_SNAPSHOT", second.disposition)
        self.assertEqual((), second.changed_sources)
        self.assertEqual((), second.appended_events)
        self.assertEqual((), second.affected)

    def test_identical_false_snapshot_in_new_visit_does_not_conflict_or_rewake(self):
        self.seed(current=True)
        self.reconcile("v1", current=False)
        replay = self.reconcile("v2", current=False)
        self.assertEqual("NOOP_SOURCE_SNAPSHOT", replay.disposition)
        self.assertEqual((), replay.changed_sources)
        self.assertEqual((), replay.appended_events)

    def test_false_to_true_same_cursor_is_material_currentness_change(self):
        self.seed(current=True)
        self.reconcile("v1", current=False)
        restored = self.reconcile("v2", current=True)
        self.assertEqual(("src",), restored.changed_sources)
        state = self.store.project()[1]
        self.assertIs(True, state["source_currentness"]["src|src"])

    def test_true_false_true_false_cycle_uses_distinct_material_events(self):
        self.seed(current=True)
        first_false = self.reconcile("v1", current=False)
        restored = self.reconcile("v2", current=True)
        second_false = self.reconcile("v3", current=False)
        self.assertEqual(("src",), first_false.changed_sources)
        self.assertEqual(("src",), restored.changed_sources)
        self.assertEqual(("src",), second_false.changed_sources)
        self.assertEqual(1, len(first_false.appended_events))
        self.assertEqual(1, len(restored.appended_events))
        self.assertEqual(1, len(second_false.appended_events))
        self.assertEqual(3, len({
            first_false.appended_events[0],
            restored.appended_events[0],
            second_false.appended_events[0],
        }))

    def test_join_context_excludes_explicitly_invalidated_source(self):
        self.seed(current=True)
        self.reconcile("v1", current=False)
        context = JoinContextCompiler().compile(
            store=self.store,
            jid=1,
            protocol_root="protocol",
            intent_root="intent",
            current_branch_head="head",
            active_residual="residual",
            affected={"src", "consumer"},
            required_sources={"src"},
            next_obligation="wait",
        )
        self.assertEqual((), context.current_sources)

    def test_join_context_readmits_source_after_currentness_restoration(self):
        self.seed(current=True)
        self.reconcile("v1", current=False)
        self.reconcile("v2", current=True)
        context = JoinContextCompiler().compile(
            store=self.store,
            jid=1,
            protocol_root="protocol",
            intent_root="intent",
            current_branch_head="head",
            active_residual="residual",
            affected={"src"},
            required_sources={"src"},
            next_obligation="resume",
        )
        self.assertEqual((("src", "g1"),), context.current_sources)

    def test_provider_rebind_same_root_keeps_currentness_without_semantic_wake(self):
        self.seed(current=True, generation="g1")
        receipt = self.reconcile("v1", current=True, generation="g2")
        self.assertEqual((), receipt.changed_sources)
        self.assertEqual(("src",), receipt.rebound_sources)
        self.assertEqual((), receipt.affected)
        self.assertIs(True, self.store.project()[1]["source_currentness"]["src|src"])

    def test_invalid_currentness_type_fails_closed(self):
        event = JSpaceEvent(
            "invalid-currentness",
            "RECONCILIATION",
            1,
            "v1",
            "src",
            "g1",
            "epoch",
            "src",
            {"source_sequence": 1, "semantic_root": "R", "current": "yes"},
            time.time_ns(),
        )
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCE_CURRENTNESS"):
            self.store.append(event)


if __name__ == "__main__":
    unittest.main()

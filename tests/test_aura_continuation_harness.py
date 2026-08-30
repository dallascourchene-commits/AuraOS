from pathlib import Path
import tempfile
import unittest

from core import aura_continuation_harness as h


HANDOFF = {
    "artifact_refs": [], "tests": ["unit"], "unresolved_residual": None,
    "exact_next_action": "scan", "invalidators": [], "source_refs": [],
    "effect_status": "D0_ONLY",
}


class ContinuationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.path = Path(self.td.name) / "workgraph.json"
        self.store = h.JsonWorkGraphStore(self.path)
        self.hm = h.ContinuationHarness(self.store, lease_s=10)
        self.a = h.WorkerIdentity("A", "visit-a", ("python",))
        self.b = h.WorkerIdentity("B", "visit-b", ("python",))

    def tearDown(self):
        self.td.cleanup()

    def test_priority_and_capability_selection(self):
        self.hm.add_cell(h.WorkCell("low", "low", priority="P2"))
        self.hm.add_cell(h.WorkCell("high", "high", priority="P0", required_capabilities=["python"]))
        self.assertEqual(self.hm.claim_next(self.a, now=100).cell_id, "high")

    def test_two_workers_cannot_claim_same_cell(self):
        self.hm.add_cell(h.WorkCell("x", "x"))
        self.assertEqual(self.hm.claim_next(self.a, now=100).cell_id, "x")
        self.assertIsNone(self.hm.claim_next(self.b, now=101))

    def test_stale_claim_recovery_uses_new_fence(self):
        self.hm.add_cell(h.WorkCell("x", "x"))
        old = self.hm.claim_next(self.a, now=100)
        new = self.hm.claim_next(self.b, now=111)
        self.assertEqual(new.cell_id, "x")
        self.assertGreater(new.fence, old.fence)
        with self.assertRaises(h.StaleFence):
            self.hm.heartbeat(old, now=112)

    def test_heartbeat_extends_lease(self):
        self.hm.add_cell(h.WorkCell("x", "x"))
        r = self.hm.claim_next(self.a, now=100)
        r2 = self.hm.heartbeat(r, now=105)
        self.assertEqual(r2.lease_expires_at, 115)
        self.assertEqual(self.store.snapshot()["cells"]["x"]["state"], "IN_PROGRESS")

    def test_dependency_wakeup_after_close(self):
        self.hm.add_cell(h.WorkCell("a", "a", priority="P0"))
        self.hm.add_cell(h.WorkCell("b", "b", priority="P0", dependencies=["a"]))
        r = self.hm.claim_next(self.a, now=100)
        self.assertEqual(r.cell_id, "a")
        self.assertEqual(self.hm.complete(r, handoff=HANDOFF, now=101), ("b",))
        self.assertEqual(self.hm.claim_next(self.b, now=102).cell_id, "b")

    def test_no_change_tick_is_zero_provider_calls(self):
        tick = self.hm.tick(self.a, now=100)
        self.assertEqual(tick.action, "IDLE_NO_CHANGE")
        self.assertEqual(tick.provider_calls, 0)
        self.assertFalse(tick.changed)

    def test_d1_cell_is_not_autonomously_claimed(self):
        self.hm.add_cell(h.WorkCell("d1", "needs owner", effect_class="D1"))
        tick = self.hm.tick(self.a, now=100)
        self.assertEqual(tick.action, "IDLE_NO_CHANGE")
        self.assertEqual(tick.reason, "NO_ELIGIBLE_CELL")

    def test_successor_compiler_deduplicates_explicit_residual(self):
        residual = {"kind": "missing-test", "owner": "W08"}
        first = self.hm.compile_successor(residual, title="repair")
        second = self.hm.compile_successor(residual, title="repair again")
        self.assertEqual(first, second)
        self.assertEqual(len(self.store.snapshot()["cells"]), 1)

    def test_restart_replays_persisted_workgraph_without_duplicate_claim(self):
        self.hm.add_cell(h.WorkCell("x", "x"))
        r = self.hm.claim_next(self.a, now=100)
        hm2 = h.ContinuationHarness(h.JsonWorkGraphStore(self.path), lease_s=10)
        self.assertIsNone(hm2.claim_next(self.b, now=101))
        self.assertEqual(hm2.heartbeat(r, now=102).cell_id, "x")

    def test_completion_requires_full_handoff(self):
        self.hm.add_cell(h.WorkCell("x", "x"))
        r = self.hm.claim_next(self.a, now=100)
        with self.assertRaises(h.InvalidTransition):
            self.hm.complete(r, handoff={"tests": []}, now=101)

    def test_stale_worker_cannot_complete_after_recovery(self):
        self.hm.add_cell(h.WorkCell("x", "x"))
        old = self.hm.claim_next(self.a, now=100)
        self.hm.claim_next(self.b, now=111)
        with self.assertRaises(h.StaleFence):
            self.hm.complete(old, handoff=HANDOFF, now=112)

    def test_artifact_index_is_content_deduplicated(self):
        self.hm.add_cell(h.WorkCell("x", "x"))
        r = self.hm.claim_next(self.a, now=100)
        art = {"ref": "file-A", "sha256": "abc"}
        self.hm.complete(r, handoff=HANDOFF, artifacts=[art, art], now=101)
        self.assertEqual(len(self.store.snapshot()["artifacts"]), 1)


if __name__ == "__main__":
    unittest.main()

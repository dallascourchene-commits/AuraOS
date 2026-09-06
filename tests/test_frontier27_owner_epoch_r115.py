from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
import unittest

from tools.arena.worker_cells.gpt56sol_frontier27_owner_epoch.owner_epoch import FrontierEpochOwnerProcess

REPO = Path(__file__).resolve().parents[1]
OWNER_SOURCE = REPO / "tools" / "arena" / "frontier27_runtime.py"
# Rebound from exact hosted PR825 checkout after the older R11.3/R11.4 donor
# identity d255abf8... failed currentness on the first R11.5 hosted attempt.
EXPECTED_OWNER_SHA256 = "a9a31401e6440241c5eb1095390b706d3fe3f9e6460dac984510007cd1485e20"
SPEC = {
    "size": 1024,
    "capacity": 4,
    "tier": {
        "name": "ram",
        "capacity_bytes": 1_000_000,
        "bandwidth": 1_000_000.0,
        "joules_per_gb": 1.0,
    },
    "window_s": 1.0,
    "budget_j": 10.0,
}


class FrontierOwnerEpochR115Tests(unittest.TestCase):
    def make(self):
        source = OWNER_SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), EXPECTED_OWNER_SHA256)
        return FrontierEpochOwnerProcess(source, EXPECTED_OWNER_SHA256, SPEC)

    def test_canonical_owner_source_is_exactly_pinned(self):
        self.assertEqual(hashlib.sha256(OWNER_SOURCE.read_bytes()).hexdigest(), EXPECTED_OWNER_SHA256)

    def test_parent_cannot_retain_raw_owner_reference(self):
        with self.make() as owner:
            self.assertFalse(hasattr(owner, "owner"))
            self.assertFalse(hasattr(owner, "r"))
            self.assertEqual(owner.snapshot().mutation_epoch, 0)

    def test_identical_governed_write_advances_epoch(self):
        with self.make() as owner:
            s0 = owner.snapshot()
            s1 = owner.governed_write(s0.full_state)
            self.assertEqual(s1.full_state_root, s0.full_state_root)
            self.assertEqual(s1.commit_generation, s0.commit_generation)
            self.assertEqual(s1.mutation_epoch, s0.mutation_epoch + 1)

    def test_aba_restore_blocks_stale_commit(self):
        with self.make() as owner:
            snap = owner.snapshot()
            result, post, source_root = owner.project_pinned(snap, [[1, 2]], [[1]])
            self.assertEqual(source_root, EXPECTED_OWNER_SHA256)
            away = json.loads(json.dumps(snap.full_state))
            away["hits"] += 7
            owner.governed_write(away)
            restored = owner.governed_write(snap.full_state)
            self.assertEqual(restored.full_state_root, snap.full_state_root)
            self.assertEqual(restored.mutation_epoch, snap.mutation_epoch + 2)
            receipt = owner.commit(snap, post, result)
            self.assertFalse(receipt.admitted)
            self.assertEqual(receipt.reason, "HOLD_MUTATION_EPOCH")

    def test_clean_pinned_transaction_commits_once(self):
        with self.make() as owner:
            before = owner.snapshot()
            receipt = owner.transact([[1, 2]], [[1]])
            self.assertTrue(receipt.admitted)
            self.assertEqual(receipt.commit_generation, before.commit_generation + 1)
            self.assertEqual(receipt.mutation_epoch, before.mutation_epoch + 1)
            self.assertEqual(receipt.owner_source_root, EXPECTED_OWNER_SHA256)

    def test_direct_governed_run_advances_epoch_not_generation(self):
        with self.make() as owner:
            before = owner.snapshot()
            _, after = owner.run([[1]], [[]])
            self.assertEqual(after.commit_generation, before.commit_generation)
            self.assertGreater(after.mutation_epoch, before.mutation_epoch)

    def test_concurrent_aba_writer_blocks_projected_transaction(self):
        with self.make() as owner:
            snap = owner.snapshot()
            result, post, _ = owner.project_pinned(snap, [[1, 2, 3]], [[1]])
            away = json.loads(json.dumps(snap.full_state))
            away["misses"] += 1

            def writer():
                owner.governed_write(away)
                owner.governed_write(snap.full_state)

            t = threading.Thread(target=writer)
            t.start(); t.join()
            receipt = owner.commit(snap, post, result)
            self.assertFalse(receipt.admitted)
            self.assertEqual(receipt.reason, "HOLD_MUTATION_EPOCH")

    def test_pinned_transition_is_deterministic_on_same_snapshot(self):
        with self.make() as owner:
            snap = owner.snapshot()
            a = owner.project_pinned(snap, [[1, 2, 3]], [[1, 4]])
            b = owner.project_pinned(snap, [[1, 2, 3]], [[1, 4]])
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()

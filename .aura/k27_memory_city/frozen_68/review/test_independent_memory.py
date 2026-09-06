"""Independent correctness checks; all databases live in this review directory."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

REVIEW = Path(__file__).resolve().parent
sys.path.insert(0, str(REVIEW.parent / "memory_city"))

from persistent_memory import MemoryStore, MemoryConflict, StaleMemory
from world_atlas import FrameAddress, FrameAtlas, FrameTransform, WorldFrame


class IndependentMemoryReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="isolated-", dir=REVIEW)
        self.file = Path(self.tmp.name) / "memory.sqlite"
        self.store = MemoryStore(self.file)
        self.store.register_frame("city", "g1")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def publish(self, key, payload, *, expected=None, epoch=None, dependencies=None):
        return self.store.publish(
            key, payload, FrameAddress("city", "g1", (0,), key),
            source_url="fixture:review", source_version="1",
            expected_revision=expected, expected_epoch=epoch, dependencies=dependencies,
        )["revision_id"]

    def test_project_rejects_source_generation_change_during_projection(self):
        # WAL permits a writer to commit while this reader holds its snapshot.
        self.store.db.execute("PRAGMA journal_mode=WAL")
        self.publish("A", {"value": 1})
        self.store.register_frame("view", "v1")
        atlas = FrameAtlas()
        atlas.add_frame(WorldFrame("city", "g1", "epoch", "CANONICAL"))
        atlas.add_frame(WorldFrame("view", "v1", "epoch", "GENERATED"))
        atlas.add_transform(FrameTransform("city", "g1", "view", "v1"))
        original = atlas.project
        with MemoryStore(self.file) as other:
            def interleaved(address, destination):
                # There is no instant when source g1 and destination v2 are
                # both current: retire g1 first, then introduce v2.
                other.register_frame("city", "g2", expected_generation="g1")
                other.register_frame("view", "v2", expected_generation="v1")
                atlas.add_frame(WorldFrame("view", "v2", "epoch", "GENERATED"))
                atlas.add_transform(FrameTransform("city", "g1", "view", "v2"))
                return original(address, destination)
            with patch.object(atlas, "project", side_effect=interleaved):
                with self.assertRaises(StaleMemory):
                    self.store.project("A", atlas, "view")
        self.assertFalse(self.store.db.in_transaction)

    def test_projection_may_return_coherent_old_snapshot(self):
        self.store.db.execute("PRAGMA journal_mode=WAL")
        self.publish("A", 1)
        self.store.register_frame("view", "v1")
        atlas = FrameAtlas()
        atlas.add_frame(WorldFrame("city", "g1", "epoch", "CANONICAL"))
        atlas.add_frame(WorldFrame("view", "v1", "epoch", "GENERATED"))
        atlas.add_transform(FrameTransform("city", "g1", "view", "v1"))
        original = atlas.project
        with MemoryStore(self.file) as other:
            def interleaved(address, destination):
                other.register_frame("city", "g2", expected_generation="g1")
                return original(address, destination)
            with patch.object(atlas, "project", side_effect=interleaved):
                projected = self.store.project("A", atlas, "view")
        self.assertEqual(projected, FrameAddress("view", "v1", (0,), "A"))
        self.assertFalse(self.store.db.in_transaction)
        with self.assertRaises(StaleMemory):
            self.store.get("A")

    def test_publish_does_not_lose_concurrent_retraction(self):
        observed = self.publish("A", {"value": 1})
        observed_epoch = self.store.get("A")["epoch"]
        with MemoryStore(self.file) as other:
            other.retract("A", expected_revision=observed, expected_epoch=observed_epoch)
        with self.assertRaises((MemoryConflict, StaleMemory)):
            self.publish("A", {"value": 2}, expected=observed, epoch=observed_epoch)
        self.assertEqual(self.store.get("A", allow_stale=True)["state"], "retracted")

    def test_aba_same_revision_does_not_restore_old_cas_token(self):
        observed = self.publish("A", {"value": 1})
        epoch = self.store.get("A")["epoch"]
        with MemoryStore(self.file) as other:
            other.retract("A", expected_revision=observed, expected_epoch=epoch)
            retired = other.get("A", allow_stale=True)
            restored = other.publish("A", {"value": 1}, FrameAddress("city", "g1", (0,), "A"),
                source_url="fixture:review", source_version="1",
                expected_revision=observed, expected_epoch=retired["epoch"])
        self.assertEqual(restored["revision_id"], observed)
        self.assertGreater(restored["epoch"], epoch)
        with self.assertRaises(MemoryConflict):
            self.publish("A", {"value": 2}, expected=observed, epoch=epoch)
        with self.assertRaises(MemoryConflict):
            self.store.retract("A", expected_revision=observed, expected_epoch=epoch)

    def test_dependency_invalidation_changes_lifecycle_cas(self):
        a = self.publish("A", 1)
        b = self.publish("B", 1, dependencies={"A": a})
        a_epoch, b_epoch = self.store.get("A")["epoch"], self.store.get("B")["epoch"]
        new_a = self.publish("A", 2, expected=a, epoch=a_epoch)
        with self.assertRaises(MemoryConflict):
            self.publish("B", 2, expected=b, epoch=b_epoch, dependencies={"A": new_a})
        self.assertGreater(self.store.get("B", allow_stale=True)["epoch"], b_epoch)

    def test_version_two_without_required_tables_is_rejected_on_open(self):
        path = Path(self.tmp.name) / "unrelated.sqlite"
        db = sqlite3.connect(path)
        try:
            db.execute("CREATE TABLE unrelated(value TEXT)")
            db.execute("PRAGMA user_version=2")
            db.commit()
        finally:
            db.close()
        opened = None
        try:
            with self.assertRaises(ValueError):
                opened = MemoryStore(path)
        finally:
            if opened is not None:
                opened.close()

    def test_failed_retraction_rolls_back_state_and_dependencies(self):
        a = self.publish("A", 1)
        b = self.publish("B", 1, dependencies={"A": a})
        epoch = self.store.get("A")["epoch"]
        with patch.object(self.store, "_invalidate", side_effect=RuntimeError("review interruption")):
            with self.assertRaises(RuntimeError):
                self.store.retract("A", expected_revision=a, expected_epoch=epoch)
        self.assertEqual(self.store.get("A")["revision_id"], a)
        self.assertEqual(self.store.get("B")["revision_id"], b)
        self.assertEqual(self.store.get("A")["epoch"], epoch)

    def test_failed_frame_update_rolls_back_generation_and_states(self):
        a = self.publish("A", 1)
        b = self.publish("B", 1, dependencies={"A": a})
        with patch.object(self.store, "_invalidate", side_effect=RuntimeError("review interruption")):
            with self.assertRaises(RuntimeError):
                self.store.register_frame("city", "g2", expected_generation="g1")
        self.assertEqual(self.store.get("A")["revision_id"], a)
        self.assertEqual(self.store.get("B")["revision_id"], b)
        self.assertEqual(self.store.db.execute("SELECT generation FROM frames WHERE frame_id='city'").fetchone()[0], "g1")

    def test_diamond_dependencies_invalidate_once_and_keep_independent_branch(self):
        a = self.publish("A", 1)
        b = self.publish("B", 1, dependencies={"A": a})
        c = self.publish("C", 1, dependencies={"A": a})
        self.publish("D", 1, dependencies={"B": b, "C": c})
        e = self.publish("E", 1)
        epoch = self.store.get("A")["epoch"]
        result = self.store.publish("A", 2, FrameAddress("city", "g1", (0,), "A"),
            source_url="fixture:review", source_version="1", expected_revision=a, expected_epoch=epoch)
        self.assertEqual(result["invalidated"], ["B", "C", "D"])
        self.assertEqual(self.store.get("E")["revision_id"], e)


if __name__ == "__main__":
    unittest.main()

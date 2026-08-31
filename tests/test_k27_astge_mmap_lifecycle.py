from __future__ import annotations

from dataclasses import replace
import os
import tempfile
import unittest
from unittest.mock import patch

import k27_astge_mmap_lifecycle as life
import k27_astge_reference as ref


class ASTGEMmapLifecycleTests(unittest.TestCase):
    def fixture(self, td: str, *, depth: int = 4, branching: int = 3):
        graph = ref.build_balanced_tree(depth, branching)
        nodes = os.path.join(td, "graph.nodes")
        edges = os.path.join(td, "graph.edges")
        ref.serialize_graph(nodes, edges, graph)
        return graph, nodes, edges

    def test_unchanged_generation_preserves_reference_cone(self):
        with tempfile.TemporaryDirectory() as td:
            graph, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                receipt = reader.validate_generation()
                self.assertTrue(receipt.observed_generation_current)
                self.assertTrue(receipt.path_identity_verified)
                self.assertTrue(receipt.exact_size_verified)
                self.assertTrue(receipt.full_content_digest_verified)
                self.assertFalse(receipt.concurrent_mutation_race_proven_safe)
                self.assertFalse(receipt.sigbus_impossible_proven)
                self.assertFalse(receipt.native_engine_safety_proven)
                self.assertFalse(receipt.external_effect)
                guarded = reader.query_affected_cone(0, 3)
            self.assertEqual(ref.heap_query_affected_cone(graph, 0, 3), guarded)

    def test_nodes_truncation_is_rejected_before_delegate_mmap_read(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                os.truncate(nodes, os.path.getsize(nodes) - ref.NODE_SIZE)
                with patch.object(reader._reader, "get_node", side_effect=AssertionError("delegate touched")):
                    with self.assertRaisesRegex(life.MmapLifecycleError, "NODES_FILE_TRUNCATED"):
                        reader.get_node(0)

    def test_edges_truncation_is_rejected_before_query(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                os.truncate(edges, os.path.getsize(edges) - ref.BLOCK_SIZE)
                with patch.object(reader._reader, "query_affected_cone", side_effect=AssertionError("delegate touched")):
                    with self.assertRaisesRegex(life.MmapLifecycleError, "EDGES_FILE_TRUNCATED"):
                        reader.query_affected_cone(0, 2)

    def test_path_replacement_is_distinct_from_open_fd_generation(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            replacement_nodes = os.path.join(td, "replacement.nodes")
            replacement_edges = os.path.join(td, "replacement.edges")
            ref.serialize_graph(replacement_nodes, replacement_edges, ref.build_balanced_tree(4, 3))
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                os.replace(replacement_nodes, nodes)
                with self.assertRaisesRegex(life.MmapLifecycleError, "NODES_PATH_REPLACED"):
                    reader.validate_generation()

    def test_same_size_in_place_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                with open(nodes, "r+b") as handle:
                    original = handle.read(1)
                    handle.seek(0)
                    handle.write(bytes([original[0] ^ 0x01]))
                    handle.flush()
                    os.fsync(handle.fileno())
                with self.assertRaisesRegex(life.MmapLifecycleError, "NODES_FILE_CONTENT_DRIFT"):
                    reader.get_node(0)

    def test_missing_path_is_rejected_even_while_open_fd_exists(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                os.unlink(nodes)
                with self.assertRaisesRegex(life.MmapLifecycleError, "NODES_PATH_MISSING"):
                    reader.validate_generation()

    def test_closed_reader_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            reader = life.LifecycleGuardedMmapGraphReader(nodes, edges)
            reader.close()
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_LIFECYCLE_CLOSED"):
                reader.validate_generation()
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_LIFECYCLE_CLOSED"):
                reader.get_node(0)

    def test_bounded_slice_rejects_negative_unknown_and_past_end(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                self.assertEqual(ref.NODE_SIZE, len(reader.read_bounded_slice("nodes", 0, ref.NODE_SIZE)))
                with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_SLICE_RANGE_INVALID"):
                    reader.read_bounded_slice("nodes", -1, 1)
                with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_SLICE_ROLE_INVALID"):
                    reader.read_bounded_slice("other", 0, 1)  # type: ignore[arg-type]
                with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_SLICE_OUT_OF_RANGE"):
                    reader.read_bounded_slice("edges", os.path.getsize(edges), 1)

    def test_reopen_establishes_new_generation_after_explicit_rebuild(self):
        with tempfile.TemporaryDirectory() as td:
            graph, nodes, edges = self.fixture(td)
            reader = life.LifecycleGuardedMmapGraphReader(nodes, edges)
            old_generation = reader.validate_generation().combined_generation_digest
            reader.close()
            replacement_graph = ref.build_balanced_tree(3, 4)
            ref.serialize_graph(nodes, edges, replacement_graph)
            fresh = life.LifecycleGuardedMmapGraphReader(nodes, edges)
            try:
                new_generation = fresh.validate_generation().combined_generation_digest
                self.assertNotEqual(old_generation, new_generation)
                self.assertEqual(
                    ref.heap_query_affected_cone(replacement_graph, 0, 2),
                    fresh.query_affected_cone(0, 2),
                )
            finally:
                fresh.close()

    def test_generation_receipt_is_deterministic_while_files_are_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                a = reader.validate_generation()
                b = reader.validate_generation()
                self.assertEqual(a, b)
                self.assertEqual(a.combined_generation_digest, b.combined_generation_digest)

    def test_metadata_only_generation_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                st = os.stat(nodes)
                os.utime(nodes, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
                with self.assertRaisesRegex(life.MmapLifecycleError, "NODES_FILE_METADATA_DRIFT"):
                    reader.validate_generation()

    def test_claim_ceiling_is_explicitly_non_native(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            with life.LifecycleGuardedMmapGraphReader(nodes, edges) as reader:
                receipt = reader.validate_generation()
                self.assertFalse(receipt.concurrent_mutation_race_proven_safe)
                self.assertFalse(receipt.sigbus_impossible_proven)
                self.assertFalse(receipt.native_engine_safety_proven)


if __name__ == "__main__":
    unittest.main()

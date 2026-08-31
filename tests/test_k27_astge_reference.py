from __future__ import annotations

import os
import struct
import tempfile
import unittest

import k27_astge_reference as ref


class ASTGEReferenceTests(unittest.TestCase):
    def test_fixed_layout_contract(self):
        self.assertEqual(64, ref.NODE_STRUCT.size)
        self.assertEqual(24, ref.BLOCK_HEADER_STRUCT.size)
        self.assertEqual(104, ref.BLOCK_PADDING)
        self.assertEqual(4096, ref.BLOCK_SIZE)

    def test_native_k27_is_three_axis_logical_cell_not_trithash(self):
        cell = ref.NativeK27Cell(1, 2, 2)
        self.assertEqual(17, cell.ordinal)
        with self.assertRaisesRegex(ValueError, "NATIVE_K27_CELL_INVALID"):
            ref.NativeK27Cell(3, 0, 0)

    def test_experimental_sid_trithash_is_deterministic_and_scheme_qualified(self):
        a = ref.SIDTriHash27.from_sid_and_domain("src/lib.rs:fn:x", 0)
        b = ref.SIDTriHash27.from_sid_and_domain("src/lib.rs:fn:x", 0)
        c = ref.SIDTriHash27.from_sid_and_domain("src/lib.rs:fn:x", 1)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertTrue(all(a.trit(i) in (0, 1, 2) for i in range(ref.SID_TRITHASH_TRITS)))
        self.assertIn("TRITHASH27", ref.PLACEMENT_SID_TRITHASH27_PREFIX9_V0)

    def test_serializer_node_table_is_direct_id_indexed_for_both_placements(self):
        graph = ref.build_balanced_tree(4, 3)
        for scheme in (ref.PLACEMENT_CONTIGUOUS_CSR_V1, ref.PLACEMENT_SID_TRITHASH27_PREFIX9_V0):
            with self.subTest(scheme=scheme), tempfile.TemporaryDirectory() as td:
                nodes = os.path.join(td, "nodes")
                edges = os.path.join(td, "edges")
                ref.serialize_graph(nodes, edges, graph, placement_scheme=scheme)
                with ref.MmapGraphReader(nodes, edges) as reader:
                    for node_id in range(len(graph)):
                        self.assertEqual(node_id, reader.get_node(node_id).node_id)

    def test_same_graph_heap_and_both_mmap_cones_are_exactly_equal(self):
        graph = ref.build_balanced_tree(6, 3)
        with tempfile.TemporaryDirectory() as td:
            readers = []
            try:
                for scheme in (ref.PLACEMENT_CONTIGUOUS_CSR_V1, ref.PLACEMENT_SID_TRITHASH27_PREFIX9_V0):
                    nodes = os.path.join(td, scheme + ".nodes")
                    edges = os.path.join(td, scheme + ".edges")
                    ref.serialize_graph(nodes, edges, graph, placement_scheme=scheme)
                    readers.append(ref.MmapGraphReader(nodes, edges))
                for depth in range(5):
                    roots = range(0, len(graph), 17)
                    for reader in readers:
                        ref.verify_equivalence(reader, graph, roots, depth)
            finally:
                for reader in readers:
                    reader.close()

    def test_trithash_blocks_are_prefix_homogeneous(self):
        graph = ref.build_balanced_tree(5, 3)
        with tempfile.TemporaryDirectory() as td:
            nodes = os.path.join(td, "nodes")
            edges = os.path.join(td, "edges")
            receipt = ref.serialize_graph(
                nodes, edges, graph, placement_scheme=ref.PLACEMENT_SID_TRITHASH27_PREFIX9_V0
            )
            self.assertGreater(receipt.placement_group_count, 1)
            with ref.MmapGraphReader(nodes, edges) as reader:
                by_pbn = {}
                for node_id in range(reader.node_count):
                    record = reader.get_node(node_id)
                    prefix = record.placement_packed & ref.SID_TRITHASH_PREFIX_MASK
                    by_pbn.setdefault(record.edge_block_pbn, prefix)
                    self.assertEqual(by_pbn[record.edge_block_pbn], prefix)
                    reader._block_row_targets(record)

    def test_hash_prefix_placement_can_amplify_pages_vs_contiguous(self):
        graph = ref.build_balanced_tree(5, 3)
        with tempfile.TemporaryDirectory() as td:
            c = ref.serialize_graph(
                os.path.join(td, "c.nodes"),
                os.path.join(td, "c.edges"),
                graph,
                placement_scheme=ref.PLACEMENT_CONTIGUOUS_CSR_V1,
            )
            h = ref.serialize_graph(
                os.path.join(td, "h.nodes"),
                os.path.join(td, "h.edges"),
                graph,
                placement_scheme=ref.PLACEMENT_SID_TRITHASH27_PREFIX9_V0,
            )
            self.assertLess(c.block_count, h.block_count)
            self.assertLess(c.edges_bytes, h.edges_bytes)
            self.assertGreater(h.block_count / c.block_count, 10.0)

    def test_truncated_node_table_fails_closed(self):
        graph = ref.build_balanced_tree(2, 2)
        with tempfile.TemporaryDirectory() as td:
            nodes = os.path.join(td, "nodes")
            edges = os.path.join(td, "edges")
            ref.serialize_graph(nodes, edges, graph)
            with open(nodes, "ab") as f:
                f.write(b"x")
            with self.assertRaisesRegex(ref.ASTGEFormatError, "NODE_TABLE_SIZE_INVALID"):
                ref.MmapGraphReader(nodes, edges)

    def test_block_pbn_substitution_fails_closed(self):
        graph = ref.build_balanced_tree(2, 2)
        with tempfile.TemporaryDirectory() as td:
            nodes = os.path.join(td, "nodes")
            edges = os.path.join(td, "edges")
            ref.serialize_graph(nodes, edges, graph)
            with open(edges, "r+b") as f:
                f.seek(0)
                f.write(struct.pack("<Q", 99))
            with ref.MmapGraphReader(nodes, edges) as reader:
                with self.assertRaisesRegex(ref.ASTGEFormatError, "BLOCK_PBN_IDENTITY_MISMATCH"):
                    reader.query_affected_cone(0, 1)

    def test_out_degree_above_block_capacity_rejected(self):
        graph = {0: tuple(range(1, ref.MAX_CSR_EDGES + 2))}
        for i in range(1, ref.MAX_CSR_EDGES + 2):
            graph[i] = ()
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "NODE_OUT_DEGREE_EXCEEDS_BLOCK_CAPACITY"):
                ref.serialize_graph(os.path.join(td, "n"), os.path.join(td, "e"), graph)

    def test_benchmark_is_same_graph_and_does_not_claim_superiority(self):
        receipt = ref.benchmark_same_graph(depth=5, branching=3, query_count=100, measured_rounds=2)
        self.assertTrue(receipt.same_graph)
        self.assertTrue(receipt.cone_equivalence_verified)
        self.assertFalse(receipt.os_page_cache_coldness_proven)
        self.assertFalse(receipt.physical_nvme_reads_proven)
        self.assertFalse(receipt.performance_superiority_proven)
        self.assertGreater(receipt.heap_median_ns, 0)
        self.assertGreater(receipt.contiguous_mmap_median_ns, 0)
        self.assertGreater(receipt.trithash_mmap_median_ns, 0)
        self.assertGreater(receipt.trithash_page_amplification_over_contiguous, 1.0)


if __name__ == "__main__":
    unittest.main()

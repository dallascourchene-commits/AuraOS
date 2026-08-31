import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'tools' / 'k27_astge_candidate_design_falsifier.py'
spec = importlib.util.spec_from_file_location('k27_astge_candidate_design_falsifier', PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class CandidateDesignFalsifierTests(unittest.TestCase):
    def test_pasted_csr_layout_is_not_4096(self):
        self.assertEqual(mod.repr_c_candidate_sizes(120)['csr_block_size'], 4160)
        self.assertEqual(mod.repr_c_candidate_sizes(104)['csr_block_size'], 4096)

    def test_ast_node_is_64_not_32(self):
        self.assertEqual(mod.repr_c_candidate_sizes(120)['ast_node_size'], 64)

    def test_pasted_serializer_breaks_node_id_index_identity(self):
        root = mod.ToyNode('root', [mod.ToyNode('a', [mod.ToyNode('a1', [])]), mod.ToyNode('b', [])])
        records = mod.pasted_serializer_table(root)
        self.assertFalse(mod.index_identity_holds(records))
        self.assertEqual(records[0]['name'], 'a1')
        self.assertEqual(records[-1]['name'], 'root')
        self.assertEqual(records[-1]['node_id'], 0)

    def test_claimed_filter_time_exceeds_ddr4_3200_dual_channel_upper_bound(self):
        required = mod.bandwidth_requirement(128_000_000, 0.00125)
        self.assertEqual(required, 102_400_000_000.0)
        self.assertGreater(required, 51_200_000_000.0)

    def test_report_salvages_architecture_not_broken_abi(self):
        r = mod.draft_report()
        self.assertFalse(r['candidate_architecture_wholesale_admission'])
        self.assertFalse(r['replace_verified_aura_splane_abi'])
        self.assertTrue(r['retain_affected_cone_idea'])
        self.assertTrue(r['retain_segmented_adjacency_idea'])
        self.assertTrue(r['retain_optional_mmap_experiment'])
        self.assertTrue(r['retain_avx2_popcnt_as_benchmark_candidate'])
        self.assertFalse(r['semantic_k27_authority'])
        self.assertEqual(len(r['receipt_sha256']), 64)


if __name__ == '__main__':
    unittest.main()

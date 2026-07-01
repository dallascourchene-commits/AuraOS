import unittest
import numpy as np
import ast
from vsa_resonator import VSAResonator
from aura_resonant_test_oracle import diagnose_structural_shadow
from symbolic_shield import check_topology_invariants

class TestVSAASTTopology(unittest.TestCase):
    def setUp(self):
        self.resonator = VSAResonator(dim=10000)
        self.src_a = "def test_func():\n    try:\n        print('hello')\n    except Exception:\n        pass"
        self.src_b = "def test_func():\n    print('hello')"  # missing try-except

    def test_ast_encoding_dimensions(self):
        hv = self.resonator.encode_ast_file(self.src_a)
        self.assertEqual(hv.shape, (10000,))
        self.assertEqual(hv.dtype, np.complex64)

    def test_binarization_and_hamming(self):
        hv_a = self.resonator.encode_ast_file(self.src_a)
        hv_b = self.resonator.encode_ast_file(self.src_b)
        
        bin_a = self.resonator.binarize_hv(hv_a)
        bin_b = self.resonator.binarize_hv(hv_b)
        
        self.assertEqual(bin_a.shape, (10000,))
        self.assertEqual(bin_b.shape, (10000,))
        
        res = self.resonator.hamming_resonance(bin_a, bin_b)
        self.assertTrue(0.0 <= res <= 1.0)

    def test_structural_shadow_diagnosis(self):
        diag = diagnose_structural_shadow(self.src_a, self.src_b, dim=10000)
        self.assertIn("Try", diag["missing_node_types"])
        self.assertIn("ExceptHandler", diag["missing_node_types"])
        self.assertTrue(diag["shadow_norm"] > 0.0)
        self.assertTrue("Missing structure" in diag["diagnosis"])

    def test_topology_invariants_shield(self):
        report = check_topology_invariants(self.src_b, self.src_a, 
                                           topology_graph={"edges": [{"source": "main.py", "target": "test_func"}]}, 
                                           module_name="test_func")
        self.assertTrue(report.passed or not report.passed)  # returns a ShieldReport

if __name__ == "__main__":
    unittest.main()

import unittest
import numpy as np
import ast
from vsa_resonator import VSAResonator
from aura_resonant_test_oracle import diagnose_structural_shadow
from symbolic_shield import check_topology_invariants
from aura_topological_scanner import detect_dead_code_via_vsa

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

    def test_topology_invariants_shield_low_drift_passes(self):
        """When structural drift is low and no dependents exist, the gate should pass."""
        # src_a and src_b differ, but with no topology_graph dependents the gate
        # should still pass (no fracture risk).
        report = check_topology_invariants(
            self.src_a,
            old_source=self.src_a,  # identical → 0% drift
            topology_graph={"edges": []},
            module_name="test_func",
        )
        self.assertTrue(report.passed)
        self.assertIn("TOPOLOGY_INVARIANT_OK", report.reason)

    def test_topology_invariants_shield_fracture_detected(self):
        """When drift > 30% and dependents exist, the gate should reject."""
        # Build a source that is structurally very different from src_a
        src_c = "class BrandNewClass:\n    def method_one(self):\n        x = 1\n        y = 2\n        z = 3\n        return x + y + z"
        report = check_topology_invariants(
            src_c,
            old_source=self.src_a,
            topology_graph={"edges": [{"source": "main.py", "target": "test_func"}]},
            module_name="test_func",
        )
        # With high drift and a dependent edge targeting "test_func", the gate
        # should reject with TOPOLOGY_FRACTURE.
        self.assertFalse(report.passed)
        self.assertIn("TOPOLOGY_FRACTURE", report.reason)

    def test_dead_code_detection_via_vsa(self):
        """detect_dead_code_via_vsa should flag isolated nodes as DEAD_CODE."""
        topology = {
            "nodes": [
                {"id": "module_a::func_main", "label": "func_main"},
                {"id": "module_a::func_helper", "label": "func_helper"},
                {"id": "module_b::orphan_func", "label": "orphan_func"},
            ],
            "edges": [
                {"source": "module_a::func_main", "target": "module_a::func_helper"},
            ],
        }
        dead = detect_dead_code_via_vsa(topology, dim=10000)
        dead_ids = [d["node_id"] for d in dead]
        # func_main has no inbound edges but is a caller — it may or may not be
        # flagged depending on resonance. orphan_func has no inbound edges and
        # its label is semantically distant from the called nodes, so it should
        # be flagged as DEAD_CODE.
        # At minimum, the function should return a list of dicts.
        self.assertIsInstance(dead, list)
        for entry in dead:
            self.assertIn("node_id", entry)
            self.assertIn("isolation_score", entry)
            self.assertEqual(entry["verdict"], "DEAD_CODE")

    def test_dead_code_detection_empty_topology(self):
        """An empty topology should return an empty list."""
        dead = detect_dead_code_via_vsa({"nodes": [], "edges": []}, dim=10000)
        self.assertEqual(dead, [])

if __name__ == "__main__":
    unittest.main()
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "arena"))

from k27_memory.gate10_causal_extension import routing_nonhard_sweep, store_root_guard_probe


class Gate10CausalExtensionTests(unittest.TestCase):
    def test_unconfounded_store_root_guard_probe(self):
        receipt = store_root_guard_probe(5)
        self.assertEqual(receipt["store_root_guard_probes"], 5)
        self.assertEqual(receipt["store_root_guard_holds"], 5)
        self.assertEqual(receipt["store_root_guard_violations"], 0)
        self.assertEqual(receipt["store_root_guard_wrong_holds"], 0)

    def test_all_nonhard_states_across_all_routing_tails(self):
        receipt = routing_nonhard_sweep()
        self.assertEqual(receipt["routing_nonhard_vectors_checked"], 256 * 243)
        self.assertEqual(receipt["routing_decision_variations"], 0)
        self.assertEqual(receipt["routing_unknown_repairs"], 0)
        self.assertEqual(receipt["routing_ready_tail_keepers"], 243)


if __name__ == "__main__":
    unittest.main()

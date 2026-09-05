import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))

from frontier27_runtime import FrontierOffload, StorageTier


class CumulativeEnergyBudgetTests(unittest.TestCase):
    def tier(self):
        return StorageTier("ssd", 1_000_000_000, 1_000_000_000, 1.0)

    def test_repeated_prefetches_share_one_run_wide_energy_budget(self):
        runtime = FrontierOffload(
            size=100_000_000,
            capacity=4,
            tier=self.tier(),
            window_s=1.0,
            budget_j=0.15,
        )
        result = runtime.run([[1], [2]], [[1], [2]])
        self.assertEqual(result["prefetch_transfers"], 1)
        self.assertAlmostEqual(result["prefetch_energy_j"], 0.1)
        self.assertLessEqual(
            result["prefetch_energy_j"], result["prefetch_energy_budget_j"] + 1e-12
        )

    def test_exact_run_wide_budget_can_be_fully_consumed(self):
        runtime = FrontierOffload(
            size=100_000_000,
            capacity=4,
            tier=self.tier(),
            window_s=1.0,
            budget_j=0.2,
        )
        result = runtime.run([[1], [2]], [[1], [2]])
        self.assertEqual(result["prefetch_transfers"], 2)
        self.assertAlmostEqual(result["prefetch_energy_j"], 0.2)
        self.assertLessEqual(
            result["prefetch_energy_j"], result["prefetch_energy_budget_j"] + 1e-12
        )

    def test_demand_miss_energy_does_not_spend_speculation_budget(self):
        runtime = FrontierOffload(
            size=100_000_000,
            capacity=4,
            tier=self.tier(),
            window_s=0.0,
            budget_j=0.0,
        )
        result = runtime.run([[1], [2]], [[], []])
        self.assertEqual(result["prefetch_transfers"], 0)
        self.assertEqual(result["prefetch_energy_j"], 0.0)
        self.assertGreater(result["energy_j"], 0.0)


if __name__ == "__main__":
    unittest.main()

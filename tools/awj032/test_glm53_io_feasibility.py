import math
import unittest

import glm53_io_feasibility as f


class IOFeasibilityTests(unittest.TestCase):
    def test_cold_one_gbps_one_second_requires_about_96_percent_reuse(self):
        reuse = f.required_reuse(
            logical_expert_bytes_required=f.DEFAULT_COLD_EXPERT_BYTES_PER_TOKEN,
            effective_storage_bandwidth_bytes_per_second=1_000_000_000,
            target_expert_io_seconds=1.0,
        )
        self.assertAlmostEqual(0.9607541, reuse, places=6)

    def test_large_time_budget_needs_no_reuse(self):
        reuse = f.required_reuse(
            logical_expert_bytes_required=f.DEFAULT_COLD_EXPERT_BYTES_PER_TOKEN,
            effective_storage_bandwidth_bytes_per_second=5_000_000_000,
            target_expert_io_seconds=10.0,
        )
        self.assertEqual(0.0, reuse)

    def test_unknown_physical_bytes_remain_unknown(self):
        receipt = f.evaluate_io_feasibility(
            physical_expert_bytes_read=None,
            effective_storage_bandwidth_bytes_per_second=3_000_000_000,
            targets=[f.TargetClass("INTERACTIVE", 1.0)],
        )
        self.assertIsNone(receipt.observed_reuse)
        self.assertIsNone(receipt.io_amplification)
        self.assertEqual("UNKNOWN_PHYSICAL_IO", receipt.targets[0].disposition)
        self.assertFalse(receipt.g2_admitted)

    def test_cache_only_zero_backend_bytes_is_full_observed_reuse(self):
        receipt = f.evaluate_io_feasibility(
            physical_expert_bytes_read=0,
            effective_storage_bandwidth_bytes_per_second=2_000_000_000,
            targets=[f.TargetClass("INTERACTIVE", 1.0)],
        )
        self.assertEqual(1.0, receipt.observed_reuse)
        self.assertEqual(0.0, receipt.targets[0].observed_expert_io_seconds)
        self.assertEqual("MEETS_STORAGE_BUDGET", receipt.targets[0].disposition)

    def test_measured_bytes_classify_each_caller_supplied_budget(self):
        receipt = f.evaluate_io_feasibility(
            physical_expert_bytes_read=2_000_000_000,
            effective_storage_bandwidth_bytes_per_second=2_000_000_000,
            targets=[
                f.TargetClass("INTERACTIVE", 0.5),
                f.TargetClass("COLD_BATCH", 2.0),
                f.TargetClass("OVERNIGHT", 20.0),
            ],
        )
        self.assertEqual(
            [
                "MISSES_STORAGE_BUDGET",
                "MEETS_STORAGE_BUDGET",
                "MEETS_STORAGE_BUDGET",
            ],
            [target.disposition for target in receipt.targets],
        )

    def test_physical_io_amplification_clamps_reuse_to_zero_but_stays_visible(self):
        logical = f.DEFAULT_COLD_EXPERT_BYTES_PER_TOKEN
        receipt = f.evaluate_io_feasibility(
            logical_expert_bytes_required=logical,
            physical_expert_bytes_read=logical + 1,
            effective_storage_bandwidth_bytes_per_second=5_000_000_000,
            targets=[f.TargetClass("BATCH", 10.0)],
        )
        self.assertEqual(0.0, receipt.observed_reuse)
        self.assertTrue(receipt.io_amplification)

    def test_receipt_claim_ceiling_never_promotes_g2(self):
        receipt = f.evaluate_io_feasibility(
            physical_expert_bytes_read=1_000_000,
            effective_storage_bandwidth_bytes_per_second=1_000_000_000,
            targets=[f.TargetClass("TEST", 1.0)],
        )
        data = receipt.to_dict()
        self.assertFalse(data["g2_admitted"])
        self.assertEqual(
            "STORAGE_ONLY_NOT_END_TO_END_PERFORMANCE_OR_G2_ADMISSION",
            data["claim_ceiling"],
        )

    def test_bad_units_fail_closed(self):
        for bandwidth in (0, -1, math.inf, math.nan):
            with self.subTest(bandwidth=bandwidth):
                with self.assertRaises(ValueError):
                    f.evaluate_io_feasibility(
                        physical_expert_bytes_read=0,
                        effective_storage_bandwidth_bytes_per_second=bandwidth,
                        targets=[f.TargetClass("TEST", 1.0)],
                    )
        with self.assertRaises(ValueError):
            f.evaluate_io_feasibility(
                physical_expert_bytes_read=-1,
                effective_storage_bandwidth_bytes_per_second=1.0,
                targets=[f.TargetClass("TEST", 1.0)],
            )

    def test_empty_or_duplicate_targets_fail_closed(self):
        with self.assertRaises(ValueError):
            f.evaluate_io_feasibility(
                physical_expert_bytes_read=0,
                effective_storage_bandwidth_bytes_per_second=1.0,
                targets=[],
            )
        with self.assertRaises(ValueError):
            f.evaluate_io_feasibility(
                physical_expert_bytes_read=0,
                effective_storage_bandwidth_bytes_per_second=1.0,
                targets=[f.TargetClass("A", 1.0), f.TargetClass("A", 2.0)],
            )


if __name__ == "__main__":
    unittest.main()

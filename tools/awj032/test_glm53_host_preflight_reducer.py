import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).with_name("glm53_host_preflight_reducer.py")
SPEC = importlib.util.spec_from_file_location("glm53_host_preflight_reducer", PATH)
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
assert SPEC.loader is not None
SPEC.loader.exec_module(m)


class HostPreflightReducerTests(unittest.TestCase):
    def test_known_5gbps_one_second_lower_bounds(self):
        r = m.reduce_host_preflight(
            measurement={"sustained_read_gbps": 5.0},
            targets_seconds_per_token={"INTERACTIVE": 1.0},
            g1_hard_false_proven=False,
            g2_tiny_fixture_pass=False,
        )
        warm = r["target_results"]["INTERACTIVE"]["shared_resident"]["routed_reuse_required_bounded"]
        cold = r["target_results"]["INTERACTIVE"]["shared_cold"]["routed_reuse_required_bounded"]
        self.assertAlmostEqual(warm, 0.779242, places=5)
        self.assertAlmostEqual(cold, 0.904242, places=5)
        self.assertTrue(r["unknown_costs_are_zero_only_for_optimistic_lower_bound"])
        self.assertFalse(r["g3_gate_prerequisites_satisfied"])
        self.assertFalse(r["g3_admitted"])

    def test_nonstorage_cost_can_make_target_unattainable_without_admission(self):
        r = m.reduce_host_preflight(
            measurement={
                "sustained_read_gbps": 5.0,
                "non_storage_seconds_per_token": 1.1,
                "fixed_other_gb_per_token": 0.0,
            },
            targets_seconds_per_token={"X": 1.0},
            g1_hard_false_proven=True,
            g2_tiny_fixture_pass=True,
        )
        self.assertFalse(r["target_results"]["X"]["shared_resident"]["attainable_under_assumptions"])
        self.assertTrue(r["g3_gate_prerequisites_satisfied"])
        self.assertFalse(r["g3_admitted"])

    def test_observed_reuse_preserves_amplification_signal(self):
        r = m.observed_reuse(logical_expert_gb=10, physical_expert_gb=12)
        self.assertTrue(r["io_amplification"])
        self.assertEqual(0.0, r["bounded_reuse"])
        self.assertLess(r["raw_reuse"], 0)

    def test_storage_fit_unknown_without_representation(self):
        r = m.reduce_host_preflight(
            measurement={"sustained_read_gbps": 2.0, "disk_free_gb": 900},
            targets_seconds_per_token={"BATCH": 30},
            g1_hard_false_proven=False,
            g2_tiny_fixture_pass=False,
        )
        self.assertEqual("UNKNOWN", r["storage_fit"])
        self.assertFalse(r["large_checkpoint_admitted"])

    def test_storage_fit_is_measured_not_admission(self):
        r = m.reduce_host_preflight(
            measurement={
                "sustained_read_gbps": 2.0,
                "disk_free_gb": 900,
                "required_representation_gb": 800,
            },
            targets_seconds_per_token={"BATCH": 30},
            g1_hard_false_proven=True,
            g2_tiny_fixture_pass=True,
        )
        self.assertTrue(r["storage_fit"])
        self.assertFalse(r["g3_admitted"])
        self.assertFalse(r["g4_admitted"])

    def test_logical_id_deterministic(self):
        kwargs = dict(
            measurement={"sustained_read_gbps": 3.0},
            targets_seconds_per_token={"OVERNIGHT": 120},
            g1_hard_false_proven=False,
            g2_tiny_fixture_pass=False,
        )
        self.assertEqual(
            m.reduce_host_preflight(**kwargs)["logical_id"],
            m.reduce_host_preflight(**kwargs)["logical_id"],
        )


if __name__ == "__main__":
    unittest.main()

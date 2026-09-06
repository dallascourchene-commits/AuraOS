import math
import unittest

from tools.arena.frontier27_runtime import FrontierOffload, LegacyOffload, StorageTier
from tools.arena.worker_cells.gpt56sol_frontier27_numeric_preflight.transactional_preflight import (
    MAX_GOVERNED_INT,
    _finite_scalar,
    run_frontier_totalized,
    run_legacy_totalized,
)


class TransactionalPreflightTests(unittest.TestCase):
    def tier(self, *, bandwidth=1_000_000_000.0, jpgb=2.0, capacity=1_000_000_000):
        return StorageTier("ssd", capacity, bandwidth, jpgb)

    def state(self, f):
        return (tuple(f.r.r.items()), f.r.hits, f.r.misses)

    def test_scalar_totality_rejects_huge_int_without_overflow(self):
        self.assertFalse(_finite_scalar(10**1000))
        self.assertTrue(_finite_scalar(MAX_GOVERNED_INT))

    def test_frontier_rejects_unbounded_size_before_mutation(self):
        f = FrontierOffload(MAX_GOVERNED_INT + 1, 4, self.tier(), 0.1, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [(1,)], [(1,)])
        self.assertEqual(self.state(f), before)

    def test_legacy_rejects_unbounded_size_as_valueerror(self):
        l = LegacyOffload(MAX_GOVERNED_INT + 1, 1.0, 1.0)
        with self.assertRaises(ValueError):
            run_legacy_totalized(l, [(1,)], [(1,)])

    def test_window_product_overflow_rejected_before_mutation(self):
        f = FrontierOffload(1024, 4, self.tier(bandwidth=1e308), 1000.0, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [(1,)], [(1,)])
        self.assertEqual(self.state(f), before)

    def test_tiny_bandwidth_nonfinite_seconds_rejected_before_mutation(self):
        f = FrontierOffload(1024, 4, self.tier(bandwidth=5e-324), 0.0, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [(1,)], [()])
        self.assertEqual(self.state(f), before)

    def test_nonfinite_energy_rejected_before_mutation(self):
        f = FrontierOffload(MAX_GOVERNED_INT, 4, self.tier(jpgb=1e308, capacity=MAX_GOVERNED_INT), 0.0, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [(1,)], [()] )
        self.assertEqual(self.state(f), before)

    def test_nested_non_integer_route_rejected_before_mutation(self):
        f = FrontierOffload(1024, 4, self.tier(), 0.1, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [(1,), ("bad",)], [(1,), (2,)])
        self.assertEqual(self.state(f), before)

    def test_nested_non_integer_prediction_rejected_before_mutation(self):
        f = FrontierOffload(1024, 4, self.tier(), 0.1, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [(1,), (2,)], [(1,), (object(),)])
        self.assertEqual(self.state(f), before)

    def test_owner_exception_rolls_back_exact_state(self):
        f = FrontierOffload(1024, 4, self.tier(), 0.1, 10.0)
        run_frontier_totalized(f, [(1,)], [()])
        before = self.state(f)
        original = f.run
        def boom(routes, preds):
            f.r.access(999)
            raise RuntimeError("synthetic owner failure")
        f.run = boom
        try:
            with self.assertRaises(RuntimeError):
                run_frontier_totalized(f, [(2,)], [()])
        finally:
            f.run = original
        self.assertEqual(self.state(f), before)

    def test_nonfinite_owner_result_rolls_back_exact_state(self):
        f = FrontierOffload(1024, 4, self.tier(), 0.1, 10.0)
        before = self.state(f)
        original = f.run
        def bad_result(routes, preds):
            f.r.access(999)
            return {"bytes": 1, "seconds": math.inf, "energy_j": 0.0, "hit_rate": 0.0, "prefetch_transfers": 0}
        f.run = bad_result
        try:
            with self.assertRaises(ValueError):
                run_frontier_totalized(f, [(2,)], [()])
        finally:
            f.run = original
        self.assertEqual(self.state(f), before)

    def test_ordinary_frontier_semantics_preserved(self):
        f = FrontierOffload(1024, 4, self.tier(), 0.1, 10.0)
        got = run_frontier_totalized(f, [(1, 2)], [(1, 3)])
        self.assertTrue(math.isfinite(got["seconds"]))
        self.assertTrue(math.isfinite(got["energy_j"]))
        self.assertGreaterEqual(got["bytes"], 0)

    def test_ordinary_legacy_semantics_preserved(self):
        l = LegacyOffload(1024, 1_000_000_000.0, 2.0)
        got = run_legacy_totalized(l, [(1, 2)], [(1, 3)])
        self.assertTrue(math.isfinite(got["seconds"]))
        self.assertTrue(math.isfinite(got["energy_j"]))

    def test_equal_length_checked_before_owner(self):
        f = FrontierOffload(1024, 4, self.tier(), 0.1, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [(1,)], [(1,), (2,)])
        self.assertEqual(self.state(f), before)

    def test_prediction_byte_cap_bound(self):
        f = FrontierOffload(MAX_GOVERNED_INT, 4, self.tier(capacity=MAX_GOVERNED_INT), 0.0, 10.0)
        before = self.state(f)
        with self.assertRaises(ValueError):
            run_frontier_totalized(f, [()], [(1, 2)])
        self.assertEqual(self.state(f), before)


if __name__ == "__main__":
    unittest.main()

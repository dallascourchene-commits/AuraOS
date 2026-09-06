import math
import multiprocessing as mp
import time
import unittest

from tools.arena.worker_cells.gpt56sol_invocation_watchdog.watchdog_canary import WatchdogReceipt, run_watchdog_canary


class WatchdogCanaryTests(unittest.TestCase):
    def test_01_finite_materialization_completes_after_ready(self):
        r = run_watchdog_canary("finite")
        self.assertTrue(r.ready_observed)
        self.assertEqual(r.disposition, "COMPLETED")
        self.assertEqual(r.records, 2)
        self.assertEqual(len(r.payload_root), 64)
        self.assertEqual(r.worker_exitcode, 0)

    def test_02_ordinary_iterator_failure_is_governed_after_ready(self):
        r = run_watchdog_canary("ordinary_reject")
        self.assertTrue(r.ready_observed)
        self.assertEqual(r.disposition, "GOVERNED_REJECT")
        self.assertEqual(r.error_type, "ValueError")
        self.assertEqual(r.worker_exitcode, 0)

    def test_03_non_returning_next_is_bounded_after_ready(self):
        started = time.monotonic()
        r = run_watchdog_canary("non_returning_next", startup_deadline_s=1.0, execution_deadline_s=0.05, cleanup_grace_s=0.25)
        elapsed = time.monotonic() - started
        self.assertTrue(r.ready_observed)
        self.assertIn(r.disposition, {"EXECUTION_TIMEOUT_TERMINATED", "EXECUTION_TIMEOUT_KILLED"})
        self.assertIsNotNone(r.worker_exitcode)
        self.assertLess(elapsed, 2.0)

    def test_04_parent_state_is_not_contaminated_by_timeout(self):
        sentinel = {"generation": 7, "items": [1, 2, 3]}; before = repr(sentinel)
        r = run_watchdog_canary("non_returning_next", execution_deadline_s=0.05)
        self.assertTrue(r.ready_observed)
        self.assertEqual(repr(sentinel), before)

    def test_05_repeated_ready_hangs_leave_no_active_child(self):
        baseline = {p.pid for p in mp.active_children()}
        for _ in range(3):
            r = run_watchdog_canary("non_returning_next", execution_deadline_s=0.04)
            self.assertTrue(r.ready_observed)
            self.assertIn(r.disposition, {"EXECUTION_TIMEOUT_TERMINATED", "EXECUTION_TIMEOUT_KILLED"})
        time.sleep(0.02)
        self.assertEqual({p.pid for p in mp.active_children()}, baseline)

    def test_06_invalid_scenario_rejected_before_spawn(self):
        with self.assertRaises(ValueError): run_watchdog_canary("unknown")

    def test_07_invalid_startup_deadline_rejected(self):
        for value in (0.0, -1.0, math.inf, math.nan):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): run_watchdog_canary("finite", startup_deadline_s=value)

    def test_08_invalid_execution_deadline_rejected(self):
        with self.assertRaises(ValueError): run_watchdog_canary("finite", execution_deadline_s=0.0)

    def test_09_invalid_cleanup_grace_rejected(self):
        with self.assertRaises(ValueError): run_watchdog_canary("finite", cleanup_grace_s=0.0)

    def test_10_non_float_deadline_rejected(self):
        with self.assertRaises(ValueError): run_watchdog_canary("finite", execution_deadline_s=1)

    def test_11_unsupported_start_method_rejected(self):
        with self.assertRaises(ValueError): run_watchdog_canary("finite", start_method="not-a-method")

    def test_12_stable_evidence_excludes_platform_exitcode(self):
        r = WatchdogReceipt("non_returning_next", "EXECUTION_TIMEOUT_TERMINATED", True, -15)
        self.assertNotIn("worker_exitcode", r.stable_evidence())
        self.assertTrue(r.stable_evidence()["ready_observed"])

    def test_13_finite_receipt_is_deterministic(self):
        a = run_watchdog_canary("finite").stable_evidence(); b = run_watchdog_canary("finite").stable_evidence()
        self.assertEqual(a, b)


if __name__ == "__main__": unittest.main()

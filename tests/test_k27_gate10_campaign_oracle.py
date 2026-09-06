import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools' / 'arena'))

from k27_memory.gate10_campaign_oracle import (
    CampaignOracleError, HOLD_STALE_DEPENDENCY, HOLD_STORE_ROOT_CONFLICT,
    classify_round, completion_fields, trace_entry,
)

ROOT = "a" * 64
WIN = ("WIN", 0, "r", 2, ("dep",), "b" * 64)
STORE_HOLD = (HOLD_STORE_ROOT_CONFLICT, 1, "MemoryConflict")
STALE_HOLD = (HOLD_STALE_DEPENDENCY, 1, "StaleMemory")


class Gate10CampaignOracleTests(unittest.TestCase):
    def test_exact_single_winner_and_store_root_losers_is_valid(self):
        out = classify_round([WIN, STORE_HOLD, STORE_HOLD, STORE_HOLD, STORE_HOLD], 5)
        self.assertTrue(out.valid)
        self.assertEqual(out.reason, "OK")
        self.assertEqual(out.winner, WIN)
        self.assertEqual((out.false_accept_delta, out.false_hold_delta), (0, 0))

    def test_zero_winner_is_structured_failure(self):
        out = classify_round([STORE_HOLD] * 5, 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "NON_SINGLE_WINNER")
        self.assertIsNone(out.winner)
        self.assertGreater(out.false_accept_delta, 0)

    def test_multiple_winners_is_structured_failure(self):
        out = classify_round([WIN, WIN, STORE_HOLD, STORE_HOLD, STORE_HOLD], 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "NON_SINGLE_WINNER")
        self.assertIsNone(out.winner)

    def test_attempt_count_mismatch_fails_closed(self):
        out = classify_round([WIN, STORE_HOLD, STORE_HOLD, STORE_HOLD], 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "ATTEMPT_COUNT_MISMATCH")

    def test_stale_dependency_status_cannot_masquerade_as_store_root_loser(self):
        out = classify_round([WIN, STORE_HOLD, STORE_HOLD, STORE_HOLD, STALE_HOLD], 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "UNEXPECTED_STATUS")
        self.assertGreater(out.false_hold_delta, 0)

    def test_trace_binds_post_repair_root(self):
        out = trace_entry(7, WIN, 9, ROOT)
        self.assertEqual(out["root"], ROOT)
        self.assertEqual(out["root_scope"], "POST_DEPENDENCY_REPAIR")
        self.assertEqual((out["round"], out["src_epoch"], out["dep_epoch"]), (7, 2, 9))

    def test_trace_rejects_non_digest_root(self):
        with self.assertRaises(CampaignOracleError):
            trace_entry(0, WIN, 1, "not-a-root")

    def test_completion_requires_all_rounds_and_no_failures(self):
        full = completion_fields([{}] * 750, [], 750)
        self.assertEqual(full, {"campaign_complete": True, "completed_rounds": 750, "round_failures": 0})
        short = completion_fields([{}] * 749, [], 750)
        self.assertFalse(short["campaign_complete"])
        failed = completion_fields([{}] * 750, [{"round": 1}], 750)
        self.assertFalse(failed["campaign_complete"])


if __name__ == "__main__":
    unittest.main()

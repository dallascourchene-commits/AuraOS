import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools' / 'arena'))

from k27_memory.gate10_campaign_oracle import (
    CampaignOracleError, HOLD_STALE_DEPENDENCY, HOLD_STORE_ROOT_CONFLICT,
    campaign_root_from_trace, classify_round, completion_fields, execution_fields, trace_entry,
)

REV = "1" * 64
ROOT = "a" * 64
STORE = "b" * 64
WIN = ("WIN", 0, REV, 2, ("dep",), STORE)
STORE_HOLD_1 = (HOLD_STORE_ROOT_CONFLICT, 1, "MemoryConflict")
STORE_HOLD_2 = (HOLD_STORE_ROOT_CONFLICT, 2, "MemoryConflict")
STORE_HOLD_3 = (HOLD_STORE_ROOT_CONFLICT, 3, "MemoryConflict")
STORE_HOLD_4 = (HOLD_STORE_ROOT_CONFLICT, 4, "MemoryConflict")
STALE_HOLD = (HOLD_STALE_DEPENDENCY, 4, "StaleMemory")


class Gate10CampaignOracleTests(unittest.TestCase):
    def canonical_round(self):
        return [WIN, STORE_HOLD_1, STORE_HOLD_2, STORE_HOLD_3, STORE_HOLD_4]

    def test_exact_single_winner_and_store_root_losers_is_valid(self):
        out = classify_round(self.canonical_round(), 5)
        self.assertTrue(out.valid)
        self.assertEqual(out.reason, "OK")
        self.assertEqual(out.winner, WIN)
        self.assertEqual(out.malformed_count, 0)

    def test_zero_winner_is_structured_failure(self):
        rows=[(HOLD_STORE_ROOT_CONFLICT, i, "MemoryConflict") for i in range(5)]
        out = classify_round(rows, 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "NON_SINGLE_WINNER")
        self.assertIsNone(out.winner)

    def test_multiple_winners_is_structured_failure(self):
        win2=("WIN",1,REV,2,("dep",),STORE)
        rows=[WIN,win2,STORE_HOLD_2,STORE_HOLD_3,STORE_HOLD_4]
        out = classify_round(rows, 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "NON_SINGLE_WINNER")

    def test_attempt_count_mismatch_fails_closed(self):
        out = classify_round(self.canonical_round()[:-1], 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "ATTEMPT_COUNT_MISMATCH")

    def test_stale_dependency_status_cannot_masquerade_as_store_root_loser(self):
        rows=[WIN,STORE_HOLD_1,STORE_HOLD_2,STORE_HOLD_3,STALE_HOLD]
        out = classify_round(rows, 5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason, "UNEXPECTED_STATUS")

    def test_truncated_win_is_malformed_not_valid(self):
        rows=[("WIN",),STORE_HOLD_1,STORE_HOLD_2,STORE_HOLD_3,STORE_HOLD_4]
        out=classify_round(rows,5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason,"MALFORMED_ROW")
        self.assertEqual(out.malformed_count,1)
        self.assertIsNone(out.winner)

    def test_truncated_hold_is_malformed(self):
        rows=[WIN,(HOLD_STORE_ROOT_CONFLICT,1),STORE_HOLD_2,STORE_HOLD_3,STORE_HOLD_4]
        out=classify_round(rows,5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason,"MALFORMED_ROW")

    def test_bad_win_digest_is_malformed(self):
        bad=("WIN",0,"not-a-digest",2,("dep",),STORE)
        rows=[bad,STORE_HOLD_1,STORE_HOLD_2,STORE_HOLD_3,STORE_HOLD_4]
        out=classify_round(rows,5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason,"MALFORMED_ROW")

    def test_hold_exception_must_match_status(self):
        bad=(HOLD_STORE_ROOT_CONFLICT,1,"StaleMemory")
        rows=[WIN,bad,STORE_HOLD_2,STORE_HOLD_3,STORE_HOLD_4]
        out=classify_round(rows,5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason,"MALFORMED_ROW")

    def test_duplicate_worker_identity_fails_closed(self):
        dup=(HOLD_STORE_ROOT_CONFLICT,1,"MemoryConflict")
        rows=[WIN,STORE_HOLD_1,dup,STORE_HOLD_3,STORE_HOLD_4]
        out=classify_round(rows,5)
        self.assertFalse(out.valid)
        self.assertEqual(out.reason,"WORKER_IDENTITY_MISMATCH")


    def test_execution_fields_report_actual_not_target_on_partial_run(self):
        out=execution_fields(rounds=750, workers=5, concurrent_attempts=5, stale_dependency_probes=0, dependency_repairs=0)
        self.assertEqual(out["target_concurrent_attempts"],3750)
        self.assertEqual(out["attempts"],5)
        self.assertEqual(out["target_stale_dependency_probes"],750)
        self.assertEqual(out["stale_dependency_probes"],0)
        self.assertEqual(out["target_campaign_round_write_attempts"],5250)
        self.assertEqual(out["total_write_attempts"],5)

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
        full_trace = [{"round": i} for i in range(750)]
        full = completion_fields(full_trace, [], 750)
        self.assertEqual(full, {"campaign_complete": True, "completed_rounds": 750, "round_failures": 0, "round_identity_complete": True})
        short = completion_fields(full_trace[:-1], [], 750)
        self.assertFalse(short["campaign_complete"])
        self.assertFalse(short["round_identity_complete"])
        failed = completion_fields(full_trace, [{"round": 1}], 750)
        self.assertFalse(failed["campaign_complete"])

    def test_completion_rejects_duplicate_round_identity(self):
        trace = [{"round": i} for i in range(750)]
        trace[-1] = {"round": 748}
        out = completion_fields(trace, [], 750)
        self.assertEqual(out["completed_rounds"], 750)
        self.assertFalse(out["round_identity_complete"])
        self.assertFalse(out["campaign_complete"])

    def canonical_trace(self):
        return [
            {"round": i, "src_epoch": i + 2, "dep_epoch": i + 2, "root": f"{i:064x}", "root_scope": "POST_DEPENDENCY_REPAIR"}
            for i in range(4)
        ]

    def test_campaign_root_is_recomputable_from_complete_trace(self):
        trace = self.canonical_trace()
        root1 = campaign_root_from_trace(trace)
        root2 = campaign_root_from_trace([dict(row) for row in trace])
        self.assertEqual(root1, root2)
        self.assertEqual(len(root1), 64)

    def test_campaign_root_changes_when_evidence_changes(self):
        trace = self.canonical_trace()
        root1 = campaign_root_from_trace(trace)
        changed = [dict(row) for row in trace]
        changed[-1]["root"] = "f" * 64
        self.assertNotEqual(root1, campaign_root_from_trace(changed))

    def test_campaign_root_rejects_missing_or_duplicate_round(self):
        trace = self.canonical_trace()
        trace[2]["round"] = 1
        with self.assertRaises(CampaignOracleError):
            campaign_root_from_trace(trace)

    def test_campaign_root_rejects_noncanonical_trace_row(self):
        trace = self.canonical_trace()
        trace[0]["extra"] = True
        with self.assertRaises(CampaignOracleError):
            campaign_root_from_trace(trace)


if __name__ == "__main__":
    unittest.main()

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parent
MODULE_PATH = ROOT / "benchmark_contract.py"
spec = importlib.util.spec_from_file_location("bughound_benchmark_contract", MODULE_PATH)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
assert spec.loader is not None
spec.loader.exec_module(b)


class BugHoundBenchmarkContractTests(unittest.TestCase):
    def test_case_digest_is_deterministic(self):
        self.assertEqual(b.seeded_generation_case().case_digest, b.seeded_generation_case().case_digest)

    def test_holdout_patch_visibility_fails_closed(self):
        case = b.seeded_generation_case()
        leaked = b.BugCase(
            case_id=case.case_id,
            bug_family=case.bug_family,
            capability_mode=case.capability_mode,
            case_validity_state=case.case_validity_state,
            leakage_state="HOLDOUT",
            source_generation=case.source_generation,
            trigger_id=case.trigger_id,
            oracle_id=case.oracle_id,
            causal_cone=case.causal_cone,
            buggy_source=case.buggy_source,
            fixed_source=case.fixed_source,
            fixed_patch_visible_to_candidate=True,
        )
        with self.assertRaises(b.BugBenchmarkError) as ctx:
            leaked.normalized()
        self.assertEqual("HOLDOUT_PATCH_LEAKAGE_FORBIDDEN", ctx.exception.code)

    def test_disputed_case_cannot_mint_accepted_receipt(self):
        receipt = b.run_seeded_generation_benchmark()
        case = receipt.case
        disputed = b.BugCase(
            case_id=case.case_id,
            bug_family=case.bug_family,
            capability_mode=case.capability_mode,
            case_validity_state="DISPUTED",
            leakage_state=case.leakage_state,
            source_generation=case.source_generation,
            trigger_id=case.trigger_id,
            oracle_id=case.oracle_id,
            causal_cone=case.causal_cone,
            buggy_source=case.buggy_source,
            fixed_source=case.fixed_source,
            fixed_patch_visible_to_candidate=case.fixed_patch_visible_to_candidate,
        )
        bad = b.MatchedBenchmarkReceipt(
            case=disputed,
            control_buggy=receipt.control_buggy,
            control_fixed=receipt.control_fixed,
            bughound_buggy=receipt.bughound_buggy,
            bughound_fixed=receipt.bughound_fixed,
        )
        with self.assertRaises(b.BugBenchmarkError) as ctx:
            bad.normalized()
        self.assertEqual("VALIDATED_CASE_REQUIRED_FOR_ACCEPTED_RECEIPT", ctx.exception.code)

    def test_happy_path_control_misses_seeded_bug(self):
        receipt = b.run_seeded_generation_benchmark()
        self.assertFalse(receipt.control_buggy.detected)
        self.assertEqual(1, receipt.control_buggy.tests_run)
        self.assertEqual((), receipt.control_buggy.failed_checks)

    def test_invariant_route_detects_buggy_revision(self):
        receipt = b.run_seeded_generation_benchmark()
        self.assertTrue(receipt.bughound_buggy.detected)
        self.assertEqual(2, receipt.bughound_buggy.tests_run)
        self.assertEqual(("stale-generation-rejected",), receipt.bughound_buggy.failed_checks)

    def test_invariant_route_does_not_flag_fixed_revision(self):
        receipt = b.run_seeded_generation_benchmark()
        self.assertFalse(receipt.bughound_fixed.detected)
        self.assertEqual((), receipt.bughound_fixed.failed_checks)

    def test_fixed_revision_does_not_break_control(self):
        receipt = b.run_seeded_generation_benchmark()
        self.assertFalse(receipt.control_fixed.detected)

    def test_seeded_issue_guided_case_gets_zero_proactive_credit(self):
        normalized = b.run_seeded_generation_benchmark().normalized()
        self.assertEqual("ISSUE_GUIDED_FIX", normalized["case"]["capability_mode"])
        self.assertFalse(normalized["proactive_discovery_credited"])
        self.assertEqual(
            "ONE_VALIDATED_SEEDED_ISSUE_GUIDED_CASE_NOT_PROACTIVE_DISCOVERY_CAPABILITY",
            normalized["claim_ceiling"],
        )

    def test_attempted_proactive_credit_fails_closed(self):
        receipt = b.run_seeded_generation_benchmark()
        widened = b.MatchedBenchmarkReceipt(
            case=receipt.case,
            control_buggy=receipt.control_buggy,
            control_fixed=receipt.control_fixed,
            bughound_buggy=receipt.bughound_buggy,
            bughound_fixed=receipt.bughound_fixed,
            proactive_discovery_credited=True,
        )
        with self.assertRaises(b.BugBenchmarkError) as ctx:
            widened.normalized()
        self.assertEqual(
            "PROACTIVE_DISCOVERY_CREDIT_FORBIDDEN_IN_SEEDED_ISSUE_GUIDED_CASE",
            ctx.exception.code,
        )

    def test_unknown_cost_latency_metrics_are_preserved(self):
        normalized = b.run_seeded_generation_benchmark().normalized()
        for run in normalized["runs"]:
            self.assertEqual(0, run["provider_calls"])
            self.assertIsNone(run["provider_cost"])
            self.assertIsNone(run["wall_latency_ms"])
        self.assertEqual(
            ["provider_cost", "wall_latency_ms"],
            normalized["unknown_metrics_preserved"],
        )

    def test_run_candidate_digest_mismatch_fails_closed(self):
        receipt = b.run_seeded_generation_benchmark()
        wrong = b.BugBenchmarkRun(
            case_digest="0" * 64,
            route=receipt.control_buggy.route,
            candidate_revision="BUGGY",
            tests_run=1,
            failed_checks=(),
            detected=False,
        )
        bad = b.MatchedBenchmarkReceipt(
            case=receipt.case,
            control_buggy=wrong,
            control_fixed=receipt.control_fixed,
            bughound_buggy=receipt.bughound_buggy,
            bughound_fixed=receipt.bughound_fixed,
        )
        with self.assertRaises(b.BugBenchmarkError) as ctx:
            bad.normalized()
        self.assertEqual("MATCHED_CASE_DIGEST_MISMATCH", ctx.exception.code)

    def test_receipt_digest_is_deterministic(self):
        self.assertEqual(
            b.run_seeded_generation_benchmark().receipt_digest,
            b.run_seeded_generation_benchmark().receipt_digest,
        )


if __name__ == "__main__":
    unittest.main()

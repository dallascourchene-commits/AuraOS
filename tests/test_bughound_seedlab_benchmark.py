import unittest

from tools.bughound.seedlab_benchmark import (
    BenchmarkError,
    FindingV1,
    TOPOLOGY_REGISTRY,
    Visibility,
    build_matched_plan,
    oracle_self_test_findings,
    run_harness_oracle,
    score_findings,
    seeded_cases,
)


class BugHoundSeedLabTests(unittest.TestCase):
    def setUp(self):
        self.cases = seeded_cases()

    def test_canonical_topology_registry_exact(self):
        self.assertEqual(
            {
                "W0": "SIMPLE_DAG",
                "W1": "RECIPROCAL_TRIADIC_HELIX",
                "W2": "ANTIPRISM_PERMUTATION_AUDIT",
                "W3": "TOROID_TRIGGERED_CYCLE",
                "W4": "BUTTERFLY_REDUCTION_TREE",
                "W5": "DIAMOND_AUTHOR_CHALLENGE_VERIFY_REDUCE",
                "W6": "OCTET_WORK_STEAL_GRID",
                "W7": "KAGOME_GYROID_SPARSE_CHALLENGE_MESH",
                "W8": "PYROCHLORE_RECOVERY_GOSSIP_RECONSTITUTION",
            },
            dict(TOPOLOGY_REGISTRY),
        )

    def test_seed_case_digests_are_deterministic_and_unique(self):
        first = [case.case_digest for case in self.cases]
        second = [case.case_digest for case in seeded_cases()]
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)))

    def test_ground_truth_oracles_are_consistent(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                result = run_harness_oracle(case)
                self.assertTrue(result.ground_truth_consistent)
                self.assertFalse(result.benchmark_candidate_credit)
                self.assertFalse(result.authority)

    def test_matched_basis_is_topology_neutral(self):
        basis = {
            build_matched_plan(w, self.cases, worker_budget=3, tool_budget=2).match_basis_digest
            for w in TOPOLOGY_REGISTRY
        }
        self.assertEqual(1, len(basis))

    def test_run_plan_identity_changes_with_topology(self):
        plans = [build_matched_plan(w, self.cases) for w in TOPOLOGY_REGISTRY]
        self.assertEqual(len(plans), len({p.run_plan_digest for p in plans}))

    def test_oracle_self_test_scores_perfect_but_is_not_candidate_evidence(self):
        plan = build_matched_plan("W0", self.cases)
        findings = oracle_self_test_findings(self.cases)
        score = score_findings(plan, self.cases, findings)
        self.assertEqual(3, score.true_positive)
        self.assertEqual(1, score.true_negative)
        self.assertEqual(1.0, score.recall)
        self.assertEqual(1.0, score.precision)
        self.assertEqual(0.0, score.false_positive_rate)
        self.assertEqual(1.0, score.localization_accuracy)
        self.assertTrue(score.valid_for_comparison)
        self.assertFalse(score.authority)
        self.assertFalse(score.external_effect)
        self.assertFalse(score.promotion_authorized)
        self.assertTrue(all(f.evidence_class == "HARNESS_ORACLE_SELF_TEST" for f in findings))

    def test_empty_candidate_has_undefined_precision_not_fabricated_zero(self):
        plan = build_matched_plan("W0", self.cases)
        score = score_findings(plan, self.cases, [])
        self.assertEqual(0.0, score.recall)
        self.assertIsNone(score.precision)
        self.assertEqual(0.0, score.false_positive_rate)

    def test_false_positive_is_measured_on_clean_control(self):
        clean = next(c for c in self.cases if not c.is_bug)
        plan = build_matched_plan("W5", self.cases)
        score = score_findings(
            plan,
            self.cases,
            [FindingV1(case_id=clean.case_id, detected=True, localized_symbols=("admit",))],
        )
        self.assertEqual(1, score.false_positive)
        self.assertEqual(1.0, score.false_positive_rate)
        self.assertEqual(0, score.true_positive)

    def test_holdout_patch_exposure_invalidates_comparison(self):
        holdout = next(c for c in self.cases if c.visibility is Visibility.HOLDOUT)
        plan = build_matched_plan("W1", self.cases)
        score = score_findings(
            plan,
            self.cases,
            [],
            fixed_patch_visible_case_ids=(holdout.case_id,),
        )
        self.assertEqual("LEAKAGE_INVALIDATED", score.leakage_state)
        self.assertFalse(score.valid_for_comparison)

    def test_global_patch_visibility_invalidates_comparison(self):
        plan = build_matched_plan("W2", self.cases, fixed_patch_visible=True)
        score = score_findings(plan, self.cases, [])
        self.assertEqual("LEAKAGE_INVALIDATED", score.leakage_state)
        self.assertFalse(score.valid_for_comparison)

    def test_duplicate_findings_fail_closed(self):
        plan = build_matched_plan("W0", self.cases)
        f = FindingV1(case_id=self.cases[0].case_id, detected=True)
        with self.assertRaises(BenchmarkError) as ctx:
            score_findings(plan, self.cases, [f, f])
        self.assertEqual("DUPLICATE_FINDING", ctx.exception.code)

    def test_unknown_finding_case_fails_closed(self):
        plan = build_matched_plan("W0", self.cases)
        with self.assertRaises(BenchmarkError) as ctx:
            score_findings(plan, self.cases, [FindingV1(case_id="UNKNOWN", detected=True)])
        self.assertEqual("FINDING_CASE_UNKNOWN", ctx.exception.code)

    def test_plan_case_set_drift_fails_closed(self):
        plan = build_matched_plan("W0", self.cases)
        with self.assertRaises(BenchmarkError) as ctx:
            score_findings(plan, self.cases[:-1], [])
        self.assertEqual("PLAN_CASE_SET_MISMATCH", ctx.exception.code)

    def test_unknown_topology_fails_closed(self):
        with self.assertRaises(BenchmarkError) as ctx:
            build_matched_plan("W9", self.cases)
        self.assertEqual("TOPOLOGY_UNKNOWN", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()

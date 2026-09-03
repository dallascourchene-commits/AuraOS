import random
import unittest

from tools.bughound.corpus_hydration import (
    Audience,
    BenchmarkObservation,
    CORPORA,
    CorpusRole,
    HydrationLevel,
    Purpose,
    admit_dataset,
    compute_scores,
    corpus_manifest_digest,
    descriptor,
    hydration_view,
    hyper1000_cells,
    k27_manifest,
    validate_split,
)


class CorpusHydrationTests(unittest.TestCase):
    def test_registry_has_distinct_ids(self):
        self.assertEqual(len(CORPORA), len({c.corpus_id for c in CORPORA}))

    def test_manifest_is_deterministic(self):
        self.assertEqual(corpus_manifest_digest(), corpus_manifest_digest())
        self.assertEqual(64, len(corpus_manifest_digest()))

    def test_k27_is_deterministic_but_not_identity(self):
        a = descriptor("ARVO")
        self.assertEqual(a.k27_xyz, descriptor("ARVO").k27_xyz)
        self.assertEqual(3, len(a.k27_xyz))
        self.assertNotEqual(str(a.k27_xyz), a.url_sha256)

    def test_arvo_earns_l4_blind_eval(self):
        a = admit_dataset("ARVO", Purpose.BLIND_EVAL, HydrationLevel.L4)
        self.assertEqual("ADMIT_LOCAL_ONLY", a.disposition)
        self.assertFalse(a.live_target_authorized)

    def test_magma_earns_l4_blind_eval(self):
        self.assertEqual("ADMIT_LOCAL_ONLY", admit_dataset("MAGMA", Purpose.BLIND_EVAL, HydrationLevel.L4).disposition)

    def test_vul4j_earns_l4_blind_eval(self):
        self.assertEqual("ADMIT_LOCAL_ONLY", admit_dataset("VUL4J", Purpose.BLIND_EVAL, HydrationLevel.L4).disposition)

    def test_secbench_earns_l4_but_no_external_authority(self):
        a = admit_dataset("SEC_BENCH", Purpose.BLIND_EVAL, HydrationLevel.L4)
        self.assertEqual("ADMIT_LOCAL_ONLY", a.disposition)
        self.assertFalse(a.testing_authorized)
        self.assertFalse(a.credentials_authorized)
        self.assertFalse(a.external_effect)

    def test_vulngym_stops_at_l3(self):
        self.assertEqual("HOLD_LEVEL_UNEARNED", admit_dataset("VULNGYM", Purpose.BLIND_EVAL, HydrationLevel.L4).disposition)
        self.assertEqual("ADMIT_LOCAL_ONLY", admit_dataset("VULNGYM", Purpose.BLIND_EVAL, HydrationLevel.L3).disposition)

    def test_cisco_stops_at_l3(self):
        self.assertEqual("HOLD_LEVEL_UNEARNED", admit_dataset("CISCO_VLB", Purpose.BLIND_EVAL, HydrationLevel.L4).disposition)

    def test_cvefixes_not_l4(self):
        self.assertEqual("HOLD_LEVEL_UNEARNED", admit_dataset("CVEFIXES", Purpose.BLIND_EVAL, HydrationLevel.L4).disposition)

    def test_snyk_reference_not_independent_ground_truth(self):
        self.assertEqual("HOLD_NOT_BLIND_EVAL", admit_dataset("SNYK_VULNBENCH_JS", Purpose.BLIND_EVAL, HydrationLevel.L3).disposition)
        self.assertEqual("ADMIT_LOCAL_ONLY", admit_dataset("SNYK_VULNBENCH_JS", Purpose.DIAGNOSTIC, HydrationLevel.L3).disposition)

    def test_train_cannot_consume_blind_eval(self):
        self.assertEqual("HOLD_EVAL_CONTAMINATION", admit_dataset("ARVO", Purpose.TRAIN, HydrationLevel.L2).disposition)

    def test_trainer_cannot_hydrate_blind_eval(self):
        with self.assertRaisesRegex(ValueError, "TRAINER_CANNOT_HYDRATE"):
            hydration_view("ARVO", HydrationLevel.L2, Audience.TRAINER)

    def test_solver_never_sees_arvo_gold(self):
        v = hydration_view("ARVO", HydrationLevel.L4, Audience.SOLVER)
        for field in ("patch", "poc", "trigger", "oracle_output", "fixed_reference"):
            self.assertIn(field, v.withheld)
            self.assertNotIn(field, v.fields)

    def test_solver_never_sees_vulngym_trace_gold(self):
        v = hydration_view("VULNGYM", HydrationLevel.L3, Audience.SOLVER)
        for field in ("entry_points", "critical_operations", "vulnerability_trace", "patch"):
            self.assertIn(field, v.withheld)

    def test_evaluator_may_hold_gold(self):
        v = hydration_view("ARVO", HydrationLevel.L4, Audience.EVALUATOR)
        self.assertIn("sealed_oracle_handle", v.fields)
        self.assertFalse(v.authority)

    def test_good_train_eval_split(self):
        ok, problems = validate_split(
            ["NIST_JULIET_CPP", "CVEFIXES", "PRIMEVUL"],
            ["ARVO", "VULNGYM", "CISCO_VLB", "MAGMA", "VUL4J", "SEC_BENCH"],
        )
        self.assertTrue(ok, problems)

    def test_same_corpus_split_fails(self):
        ok, problems = validate_split(["PRIMEVUL"], ["PRIMEVUL"])
        self.assertFalse(ok)
        self.assertIn("CORPUS_ID_OVERLAP", problems)

    def test_blind_eval_in_training_split_fails(self):
        ok, problems = validate_split(["ARVO"], ["VULNGYM"])
        self.assertFalse(ok)
        self.assertIn("NONTRAIN_IN_TRAIN:ARVO", problems)

    def test_diagnostic_not_blind_eval(self):
        ok, problems = validate_split(["PRIMEVUL"], ["SNYK_VULNBENCH_JS"])
        self.assertFalse(ok)
        self.assertIn("NONBLIND_IN_EVAL:SNYK_VULNBENCH_JS", problems)

    def test_score_requires_independent_support(self):
        s = compute_scores([
            BenchmarkObservation("v1", True, True, False),
            BenchmarkObservation("n1", False, False, False),
        ])
        self.assertEqual(0, s["true_positive_supported"])
        self.assertEqual(1, s["unsupported_positive"])
        self.assertEqual(0.0, s["recall"])

    def test_patched_false_positive_counts(self):
        s = compute_scores([
            BenchmarkObservation("v1", True, True, True),
            BenchmarkObservation("patched", False, True, True),
        ])
        self.assertEqual(1, s["false_positive_clean_or_patched"])
        self.assertLess(s["precision"], 1.0)

    def test_l4_credit_requires_repro_and_clean_counterfactual(self):
        s = compute_scores([
            BenchmarkObservation("a", True, True, True, reproduced=True, counterfactual_clean=True),
            BenchmarkObservation("b", True, True, True, reproduced=True, counterfactual_clean=False),
        ])
        self.assertEqual(1, s["l4_verified"])

    def test_file_localization_f1(self):
        s = compute_scores([
            BenchmarkObservation("a", True, True, True, localized_files=("a.py",), ground_truth_files=("a.py", "b.py")),
        ])
        self.assertAlmostEqual(2 / 3, s["mean_file_f1"])

    def test_trace_coverage(self):
        s = compute_scores([BenchmarkObservation("a", True, True, True, trace_edges_hit=3, trace_edges_total=4)])
        self.assertEqual(0.75, s["mean_trace_coverage"])

    def test_repeatability(self):
        s = compute_scores([BenchmarkObservation("a", True, True, True, repeat_hits=4, repeats=5)])
        self.assertEqual(0.8, s["mean_repeatability"])

    def test_precision_undefined_with_no_positive_predictions(self):
        s = compute_scores([BenchmarkObservation("clean", False, False, False)])
        self.assertIsNone(s["precision"])

    def test_hyper1000_exact(self):
        cells = hyper1000_cells()
        self.assertEqual(1000, len(cells))
        self.assertEqual(1000, len(set(cells)))

    def test_all_k27_entries_keep_full_url_hash(self):
        entries = k27_manifest()
        self.assertEqual(len(CORPORA), len(entries))
        for e in entries:
            self.assertEqual(64, len(e["url_sha256"]))
            self.assertEqual("K27-B3MOD27-XYZ-v1", e["scheme"])
            self.assertEqual("RETRIEVAL_REOPEN_METADATA_ONLY", e["claim_ceiling"])

    def test_no_admission_mints_authority(self):
        for c in CORPORA:
            for p in Purpose:
                for level in HydrationLevel:
                    a = admit_dataset(c.corpus_id, p, level)
                    self.assertFalse(a.testing_authorized)
                    self.assertFalse(a.live_target_authorized)
                    self.assertFalse(a.credentials_authorized)
                    self.assertFalse(a.submission_authorized)
                    self.assertFalse(a.payment_authorized)
                    self.assertFalse(a.external_effect)

    def test_randomized_contamination_reference_equivalence(self):
        rng = random.Random(27)
        ids = [c.corpus_id for c in CORPORA]
        for _ in range(100_000):
            cid = rng.choice(ids)
            purpose = rng.choice(list(Purpose))
            level = rng.choice(list(HydrationLevel))
            c = descriptor(cid)
            got = admit_dataset(cid, purpose, level).disposition
            if c.role == CorpusRole.QUARANTINED:
                expected = "HOLD_QUARANTINED"
            elif level > c.max_hydration:
                expected = "HOLD_LEVEL_UNEARNED"
            elif purpose == Purpose.TRAIN and c.role != CorpusRole.TRAIN_HYDRATE:
                expected = "HOLD_EVAL_CONTAMINATION"
            elif purpose == Purpose.BLIND_EVAL and c.role != CorpusRole.BLIND_EVAL:
                expected = "HOLD_NOT_BLIND_EVAL"
            elif purpose == Purpose.BLIND_EVAL and not c.real_world:
                expected = "HOLD_NOT_REAL_WORLD"
            elif purpose == Purpose.BLIND_EVAL and not c.independent_ground_truth:
                expected = "HOLD_TRUTH_NOT_INDEPENDENT"
            elif purpose == Purpose.BLIND_EVAL and level == HydrationLevel.L4 and not (
                c.reproducible and c.oracle_class.value not in {"NONE", "REFERENCE_MATCH"}
            ):
                expected = "HOLD_L4_ORACLE_UNPROVEN"
            elif purpose == Purpose.DIAGNOSTIC and c.role == CorpusRole.TRAIN_HYDRATE:
                expected = "ADMIT_DIAGNOSTIC_ONLY"
            else:
                expected = "ADMIT_LOCAL_ONLY"
            self.assertEqual(expected, got, (cid, purpose, level, c))


if __name__ == "__main__":
    unittest.main()

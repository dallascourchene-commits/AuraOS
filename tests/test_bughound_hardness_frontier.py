import importlib.util
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hardness_frontier", ROOT / "tools/bughound/hardness_frontier.py")
M = importlib.util.module_from_spec(SPEC)
sys.modules[M.__name__] = M
assert SPEC.loader is not None
SPEC.loader.exec_module(M)

ROOT_DIGEST = "a" * 64
CUT_DIGEST = "b" * 64
EVAL_GEN = "eval-v1"
CORPUS_GEN = "corpus-v1"


def facts(**kw):
    base = dict(
        interprocedural_hops=1,
        cross_file_span=1,
        trace_depth=2,
        statefulness=0,
        control_flow_ambiguity=0,
        historical_signal_scarcity=0,
        oracle_cost=0,
        patch_distance=0,
    )
    base.update(kw)
    return M.RawHardnessFactsV1(**base)


def seal(target, f, policy=None, eval_gen=EVAL_GEN, root=ROOT_DIGEST, cut=CUT_DIGEST):
    policy = policy or M.HardnessPolicyV1()
    return M.compile_evaluator_seal(
        opaque_target=target,
        benchmark_semantic_root=root,
        historical_cut_digest=cut,
        corpus_generation=CORPUS_GEN,
        evaluator_generation=eval_gen,
        facts=f,
        policy=policy,
    )


class HardnessFrontierTests(unittest.TestCase):
    def test_axis_contract_exact(self):
        self.assertEqual(len(M.AXES), 8)
        self.assertEqual(len(set(M.AXES)), 8)

    def test_omega8_is_exact_3_pow_8(self):
        cells = M.omega8_lattice()
        self.assertEqual(len(cells), 6561)
        self.assertEqual(len({c.levels for c in cells}), 6561)

    def test_realistic_34_hop_case_bins_high(self):
        v = M.vectorize(facts(interprocedural_hops=34), M.HardnessPolicyV1())
        self.assertEqual(v.as_map()["interprocedural_hops"], 2)

    def test_vector_thresholds(self):
        p = M.HardnessPolicyV1()
        self.assertEqual(M.vectorize(facts(interprocedural_hops=1), p).levels[0], 0)
        self.assertEqual(M.vectorize(facts(interprocedural_hops=2), p).levels[0], 1)
        self.assertEqual(M.vectorize(facts(interprocedural_hops=5), p).levels[0], 2)

    def test_extreme_stratum(self):
        p = M.HardnessPolicyV1()
        f = facts(interprocedural_hops=8, cross_file_span=5, trace_depth=9, statefulness=2)
        self.assertEqual(seal("x", f, p).stratum, "EXTREME_FRONTIER")

    def test_two_high_axes_are_hard_tail(self):
        p = M.HardnessPolicyV1()
        f = facts(interprocedural_hops=8, cross_file_span=5)
        self.assertEqual(seal("x", f, p).stratum, "HARD_TAIL")

    def test_policy_changes_identity(self):
        a = M.HardnessPolicyV1()
        b = M.HardnessPolicyV1(interproc_high=6)
        self.assertNotEqual(a.digest, b.digest)

    def test_facts_change_seal_identity(self):
        a = seal("x", facts(interprocedural_hops=5))
        b = seal("x", facts(interprocedural_hops=6))
        self.assertNotEqual(a.facts_digest, b.facts_digest)
        self.assertNotEqual(a.seal_digest, b.seal_digest)


    def test_forged_seal_digest_fails(self):
        p = M.HardnessPolicyV1()
        good = seal("x", facts(interprocedural_hops=8), p)
        forged = M.EvaluatorHardnessSealV1(
            opaque_target=good.opaque_target,
            benchmark_semantic_root=good.benchmark_semantic_root,
            historical_cut_digest=good.historical_cut_digest,
            corpus_generation=good.corpus_generation,
            evaluator_generation=good.evaluator_generation,
            policy_digest=good.policy_digest,
            facts_digest=good.facts_digest,
            vector=good.vector,
            stratum=good.stratum,
            seal_digest="0" * 64,
        )
        with self.assertRaises(ValueError):
            M.build_frontier_report([forged], [M.CaseOutcomeV1("x", True)],
                                    expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN, policy=p)

    def test_solver_projection_contains_no_hardness(self):
        s = seal("opaque-1", facts(interprocedural_hops=34, trace_depth=10, oracle_cost=2))
        projection = s.solver_projection()
        M.validate_solver_projection(projection)
        text = repr(projection).lower()
        for axis in M.AXES:
            self.assertNotIn(axis, text)
        self.assertNotIn("hard_tail", text)

    def test_solver_projection_injected_hardness_fails(self):
        with self.assertRaises(ValueError):
            M.validate_solver_projection({"opaque_target": "x", "instruction": "inspect", "trace_depth": 2})

    def test_solver_projection_vulnerability_label_fails(self):
        with self.assertRaises(ValueError):
            M.validate_solver_projection({"opaque_target": "x", "instruction": "find CVE-2025-1234"})

    def test_empty_report_fails(self):
        with self.assertRaises(ValueError):
            M.build_frontier_report([], [], expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN,
                                    policy=M.HardnessPolicyV1())

    def test_case_set_mismatch_fails(self):
        s = [seal("x", facts())]
        with self.assertRaises(ValueError):
            M.build_frontier_report(s, [M.CaseOutcomeV1("y", True)],
                                    expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN,
                                    policy=M.HardnessPolicyV1())

    def test_evaluator_generation_drift_fails(self):
        s = [seal("x", facts(), eval_gen="old")]
        with self.assertRaises(ValueError):
            M.build_frontier_report(s, [M.CaseOutcomeV1("x", True)],
                                    expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN,
                                    policy=M.HardnessPolicyV1())

    def test_semantic_root_drift_fails(self):
        s = [seal("x", facts(), root="c" * 64)]
        with self.assertRaises(ValueError):
            M.build_frontier_report(s, [M.CaseOutcomeV1("x", True)],
                                    expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN,
                                    policy=M.HardnessPolicyV1())

    def test_wilson_empty_is_undefined(self):
        i = M.wilson_interval(0, 0, 1.96)
        self.assertIsNone(i.point)
        self.assertIsNone(i.low)
        self.assertIsNone(i.high)

    def test_easy_bulk_cannot_hide_hard_failures(self):
        p = M.HardnessPolicyV1(min_slice_cases=2, hard_tail_recall_floor=0.20, per_axis_high_recall_floor=0.10)
        seals = []
        outs = []
        for i in range(100):
            t = f"easy-{i}"
            seals.append(seal(t, facts(), p))
            outs.append(M.CaseOutcomeV1(t, True))
        hard_facts = facts(interprocedural_hops=8, cross_file_span=5, trace_depth=8,
                           statefulness=2, control_flow_ambiguity=2,
                           historical_signal_scarcity=2, oracle_cost=2, patch_distance=2)
        for i in range(4):
            t = f"hard-{i}"
            seals.append(seal(t, hard_facts, p))
            outs.append(M.CaseOutcomeV1(t, False))
        r = M.build_frontier_report(seals, outs,
                                    expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN, policy=p)
        self.assertGreater(r.overall.point, 0.95)
        self.assertEqual(r.hard_tail.point, 0.0)
        self.assertEqual(r.claim_status, "HOLD_HARDNESS_FRONTIER_DEBT")
        self.assertIn("HARD_TAIL_RECALL_FLOOR_NOT_MET", r.unmet_debts)

    def test_all_hard_slices_must_be_supported(self):
        p = M.HardnessPolicyV1(min_slice_cases=2, hard_tail_recall_floor=0.1, per_axis_high_recall_floor=0.1)
        seals = []
        outs = []
        for i in range(4):
            t = f"c-{i}"
            seals.append(seal(t, facts(interprocedural_hops=8), p))
            outs.append(M.CaseOutcomeV1(t, True))
        r = M.build_frontier_report(seals, outs,
                                    expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN, policy=p)
        self.assertEqual(r.claim_status, "HOLD_HARDNESS_FRONTIER_DEBT")
        self.assertTrue(any(d.startswith("INSUFFICIENT_HIGH_AXIS_CASES:cross_file_span") for d in r.unmet_debts))

    def test_supported_when_every_high_slice_and_hard_tail_clear(self):
        p = M.HardnessPolicyV1(min_slice_cases=2, hard_tail_recall_floor=0.1, per_axis_high_recall_floor=0.1)
        seals = []
        outs = []
        hard = facts(interprocedural_hops=8, cross_file_span=5, trace_depth=8,
                     statefulness=2, control_flow_ambiguity=2,
                     historical_signal_scarcity=2, oracle_cost=2, patch_distance=2)
        for i in range(20):
            t = f"h-{i}"
            seals.append(seal(t, hard, p))
            outs.append(M.CaseOutcomeV1(t, True))
        r = M.build_frontier_report(seals, outs,
                                    expected_benchmark_semantic_root=ROOT_DIGEST,
                                    expected_historical_cut_digest=CUT_DIGEST,
                                    expected_evaluator_generation=EVAL_GEN, policy=p)
        self.assertEqual(r.claim_status, "HARDNESS_FRONTIER_COVERAGE_SUPPORTED")
        self.assertEqual(r.unmet_debts, ())
        self.assertFalse(r.generalized_real_world_superiority)

    def test_report_digest_deterministic_under_input_order(self):
        p = M.HardnessPolicyV1(min_slice_cases=1, hard_tail_recall_floor=0, per_axis_high_recall_floor=0)
        hard = facts(interprocedural_hops=8, cross_file_span=5, trace_depth=8,
                     statefulness=2, control_flow_ambiguity=2,
                     historical_signal_scarcity=2, oracle_cost=2, patch_distance=2)
        seals = [seal("a", hard, p), seal("b", hard, p)]
        outs = [M.CaseOutcomeV1("a", True), M.CaseOutcomeV1("b", False)]
        r1 = M.build_frontier_report(seals, outs, expected_benchmark_semantic_root=ROOT_DIGEST,
                                     expected_historical_cut_digest=CUT_DIGEST,
                                     expected_evaluator_generation=EVAL_GEN, policy=p)
        r2 = M.build_frontier_report(list(reversed(seals)), list(reversed(outs)),
                                     expected_benchmark_semantic_root=ROOT_DIGEST,
                                     expected_historical_cut_digest=CUT_DIGEST,
                                     expected_evaluator_generation=EVAL_GEN, policy=p)
        self.assertEqual(r1.report_digest, r2.report_digest)

    def test_k27_preserves_full_source_identity(self):
        a = M.k27_coordinate("https://arxiv.org/abs/2608.02001")
        b = M.k27_coordinate("https://aclanthology.org/2026.findings-acl.1786/")
        self.assertEqual(len(a[3]), 64)
        self.assertNotEqual(a[3], b[3])
        self.assertTrue(all(0 <= x < 27 for x in a[:3]))

    def test_randomized_reference_policy(self):
        rng = random.Random(12012026)
        p = M.HardnessPolicyV1()
        for i in range(100_000):
            f = M.RawHardnessFactsV1(
                interprocedural_hops=rng.randrange(0, 40),
                cross_file_span=rng.randrange(1, 10),
                trace_depth=rng.randrange(1, 15),
                statefulness=rng.randrange(3),
                control_flow_ambiguity=rng.randrange(3),
                historical_signal_scarcity=rng.randrange(3),
                oracle_cost=rng.randrange(3),
                patch_distance=rng.randrange(3),
            )
            got = M.vectorize(f, p).levels
            ref = (
                2 if f.interprocedural_hops >= p.interproc_high else 1 if f.interprocedural_hops >= p.interproc_medium else 0,
                2 if f.cross_file_span >= p.files_high else 1 if f.cross_file_span >= p.files_medium else 0,
                2 if f.trace_depth >= p.trace_high else 1 if f.trace_depth >= p.trace_medium else 0,
                f.statefulness,
                f.control_flow_ambiguity,
                f.historical_signal_scarcity,
                f.oracle_cost,
                f.patch_distance,
            )
            self.assertEqual(got, ref, msg=f"random case {i}")


if __name__ == "__main__":
    unittest.main()

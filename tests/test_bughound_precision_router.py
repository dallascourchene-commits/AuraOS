import random
import unittest

from tools.bughound.precision_router import (
    CaseState,
    PrecisionTier,
    TIER_COST,
    difficulty_vector,
    hyper1000_cells,
    naive_full_cost,
    route_case,
    routed_cost,
)


def state(**kw):
    base = dict(
        case_id="c",
        corpus_id="ARVO",
        expected_generation="g1",
        observed_generation="g1",
        hydrated_level=4,
        dependency_complete=True,
        local_oracle_available=True,
        budget_units_remaining=100,
    )
    base.update(kw)
    return CaseState(**base)


class RouterTests(unittest.TestCase):
    def test_stale_source_rehydrates_from_l0(self):
        d = route_case(state(observed_generation="g2"))
        self.assertEqual("REHYDRATE_FROM_L0_SOURCE_GENERATION", d.disposition)
        self.assertTrue(d.stale_evidence_invalidated)

    def test_oracle_generation_drift_reopens_l4(self):
        d = route_case(state(oracle_generation="o1", observed_oracle_generation="o2"))
        self.assertEqual(PrecisionTier.T7_L4_COUNTERFACTUAL, d.tier)

    def test_structural(self):
        self.assertEqual(PrecisionTier.T2_STRUCTURAL, route_case(state(unresolved_structural=True)).tier)

    def test_path(self):
        self.assertEqual(PrecisionTier.T3_PATH_SENSITIVE, route_case(state(unresolved_path=True)).tier)

    def test_interproc(self):
        self.assertEqual(PrecisionTier.T4_INTERPROCEDURAL_DATAFLOW, route_case(state(unresolved_interprocedural=True)).tier)

    def test_stateful(self):
        self.assertEqual(PrecisionTier.T5_STATEFUL_SYMBOLIC, route_case(state(unresolved_stateful=True)).tier)

    def test_dynamic(self):
        self.assertEqual(PrecisionTier.T6_LOCAL_DYNAMIC, route_case(state(dynamic_evidence_required=True)).tier)

    def test_counterfactual(self):
        self.assertEqual(PrecisionTier.T7_L4_COUNTERFACTUAL, route_case(state(l4_counterfactual_required=True)).tier)

    def test_no_residual(self):
        self.assertEqual("NO_DEEPER_ANALYSIS_REQUIRED", route_case(state()).disposition)

    def test_dependency_unknown_widens_to_l7_when_oracle_available(self):
        d = route_case(state(dependency_complete=False))
        self.assertEqual(PrecisionTier.T7_L4_COUNTERFACTUAL, d.tier)
        self.assertTrue(d.widened_for_incomplete_dependencies)

    def test_dependency_unknown_widens_to_dynamic_without_oracle(self):
        d = route_case(state(dependency_complete=False, local_oracle_available=False))
        self.assertEqual(PrecisionTier.T6_LOCAL_DYNAMIC, d.tier)

    def test_l4_without_oracle_holds(self):
        self.assertEqual(
            "HOLD_L4_LOCAL_ORACLE_UNAVAILABLE",
            route_case(state(l4_counterfactual_required=True, local_oracle_available=False)).disposition,
        )

    def test_budget_stop(self):
        self.assertEqual("STOP_BUDGET_EXHAUSTED", route_case(state(unresolved_path=True, budget_units_remaining=1)).disposition)

    def test_network_requirement_holds(self):
        self.assertEqual("HOLD_EXTERNAL_EFFECT_REQUIREMENT", route_case(state(network_required=True)).disposition)

    def test_credentials_requirement_holds(self):
        self.assertEqual("HOLD_EXTERNAL_EFFECT_REQUIREMENT", route_case(state(credentials_required=True)).disposition)

    def test_no_route_mints_authority(self):
        cases = [
            state(),
            state(unresolved_path=True),
            state(dynamic_evidence_required=True),
            state(l4_counterfactual_required=True),
            state(observed_generation="g2"),
            state(network_required=True),
        ]
        for s in cases:
            d = route_case(s)
            self.assertFalse(any((
                d.testing_authorized,
                d.network_authorized,
                d.credentials_authorized,
                d.submission_authorized,
                d.payment_authorized,
                d.external_effect,
            )))

    def test_decision_digest_deterministic(self):
        self.assertEqual(
            route_case(state(unresolved_path=True)).decision_digest,
            route_case(state(unresolved_path=True)).decision_digest,
        )

    def test_difficulty_vector_separate_axes(self):
        self.assertEqual(
            (0, 1, 1, 0, 0, 0, 1),
            difficulty_vector(state(unresolved_path=True, unresolved_interprocedural=True, dependency_complete=False)),
        )

    def test_hyper1000(self):
        self.assertEqual(1000, len(set(hyper1000_cells())))

    def test_routing_cheaper_than_naive_on_mixed_local_cases(self):
        xs = [
            state(),
            state(unresolved_structural=True),
            state(unresolved_path=True),
            state(unresolved_interprocedural=True),
            state(unresolved_stateful=True),
            state(dynamic_evidence_required=True),
            state(l4_counterfactual_required=True),
        ]
        self.assertLess(routed_cost(xs), naive_full_cost(xs))

    def test_tier_priority_deepest_required(self):
        self.assertEqual(
            PrecisionTier.T6_LOCAL_DYNAMIC,
            route_case(state(unresolved_structural=True, unresolved_path=True, dynamic_evidence_required=True)).tier,
        )

    def test_empty_case_fails(self):
        with self.assertRaisesRegex(ValueError, "CASE_ID_AND_CORPUS_REQUIRED"):
            route_case(state(case_id=""))

    def test_cost_zero_on_hold(self):
        self.assertEqual(0, route_case(state(l4_counterfactual_required=True, local_oracle_available=False)).cost_units)

    def test_stale_source_precedes_deep_work(self):
        self.assertEqual(
            PrecisionTier.T1_CURRENTNESS,
            route_case(state(observed_generation="g2", l4_counterfactual_required=True)).tier,
        )

    def test_randomized_reference_equivalence(self):
        rng = random.Random(2709)
        for i in range(100_000):
            s = state(
                case_id=f"c{i}",
                observed_generation="g2" if rng.random() < 0.04 else "g1",
                dependency_complete=rng.random() > 0.08,
                unresolved_structural=rng.random() < 0.15,
                unresolved_path=rng.random() < 0.12,
                unresolved_interprocedural=rng.random() < 0.10,
                unresolved_stateful=rng.random() < 0.08,
                dynamic_evidence_required=rng.random() < 0.06,
                l4_counterfactual_required=rng.random() < 0.04,
                local_oracle_available=rng.random() > 0.15,
                budget_units_remaining=rng.randint(0, 30),
                network_required=rng.random() < 0.01,
                credentials_required=rng.random() < 0.01,
            )
            d = route_case(s)
            if s.network_required or s.credentials_required:
                expected = "HOLD_EXTERNAL_EFFECT_REQUIREMENT"
            elif s.expected_generation != s.observed_generation:
                expected = "REHYDRATE_FROM_L0_SOURCE_GENERATION"
            else:
                if not s.dependency_complete:
                    t = PrecisionTier.T7_L4_COUNTERFACTUAL if s.local_oracle_available else PrecisionTier.T6_LOCAL_DYNAMIC
                elif s.l4_counterfactual_required:
                    t = PrecisionTier.T7_L4_COUNTERFACTUAL
                elif s.dynamic_evidence_required:
                    t = PrecisionTier.T6_LOCAL_DYNAMIC
                elif s.unresolved_stateful:
                    t = PrecisionTier.T5_STATEFUL_SYMBOLIC
                elif s.unresolved_interprocedural:
                    t = PrecisionTier.T4_INTERPROCEDURAL_DATAFLOW
                elif s.unresolved_path:
                    t = PrecisionTier.T3_PATH_SENSITIVE
                elif s.unresolved_structural:
                    t = PrecisionTier.T2_STRUCTURAL
                else:
                    t = PrecisionTier.T1_CURRENTNESS
                if t == PrecisionTier.T7_L4_COUNTERFACTUAL and not s.local_oracle_available:
                    expected = "HOLD_L4_LOCAL_ORACLE_UNAVAILABLE"
                elif s.budget_units_remaining < TIER_COST[t]:
                    expected = "STOP_BUDGET_EXHAUSTED"
                elif t == PrecisionTier.T1_CURRENTNESS:
                    expected = "NO_DEEPER_ANALYSIS_REQUIRED"
                else:
                    expected = "RUN_MINIMUM_SUFFICIENT_LOCAL_TIER"
            self.assertEqual(expected, d.disposition, (s, d))


if __name__ == "__main__":
    unittest.main()

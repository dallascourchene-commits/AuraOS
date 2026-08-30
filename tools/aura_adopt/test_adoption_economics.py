import unittest

from tools.aura_adopt.adoption_economics import (
    AcceptedValueEvidence, AcceptedValueEvidenceClass, CostKind, CostObservation,
    EconomicsError, EvidenceBinding, ExactMicrounitRatio, MoneyEvidenceClass,
    ObservationStatus, ReuseEvidence, ReuseKind, build_economics_receipt,
    compare_economics, compile_economics_admission,
)

CURRENCY = "USD_MICRO"


def evidence(generation="g1"):
    return EvidenceBinding(
        "drive://route", "sha256:route", generation,
        f"current:{generation}", "SOURCE_BOUND_REFERENCE",
    )


def known_cost(
    kind,
    value=0,
    evidence_class=MoneyEvidenceClass.MEASURED,
    source=None,
):
    return CostObservation(
        kind, ObservationStatus.KNOWN, value, CURRENCY, evidence_class,
        source or f"measure://{kind.value}", "g1", "current:g1"
    )


def na_cost(kind):
    return CostObservation(
        kind, ObservationStatus.NOT_APPLICABLE, None, CURRENCY,
        MoneyEvidenceClass.MEASURED, f"measure://{kind.value}", "g1",
        "current:g1", "not required on this route"
    )


def unknown_cost(kind):
    return CostObservation(
        kind, ObservationStatus.UNKNOWN, None, CURRENCY,
        MoneyEvidenceClass.UNKNOWN, f"measure://{kind.value}", "g1",
        "current:g1", "not measured"
    )


def all_na_costs():
    return [na_cost(kind) for kind in CostKind]


def accepted(
    count=1,
    attempts=1,
    evidence_class=AcceptedValueEvidenceClass.TECHNICAL_EXECUTED,
):
    return AcceptedValueEvidence(
        count,
        attempts,
        evidence_class,
        "verify://fixture",
        "receipt://accepted",
        (
            "consent://fixture"
            if evidence_class is AcceptedValueEvidenceClass.CONSENTED_STUDY
            else None
        ),
    )


def reuse(
    *,
    kind=ReuseKind.KV_CACHE,
    source_ref="kv://run",
    current=True,
    isolated=True,
    avoided=50,
    evidence_class=MoneyEvidenceClass.MEASURED,
):
    return ReuseEvidence(
        kind=kind,
        status=ObservationStatus.KNOWN,
        source_ref=source_ref,
        source_generation="g1",
        currentness_ref="current:g1",
        evidence_class=evidence_class,
        principal_scope="tenant-a",
        source_current=current,
        source_current_evidence_ref=(
            "receipt://currentness" if current is True else None
        ),
        privacy_isolated=isolated,
        privacy_isolation_evidence_ref=(
            "receipt://privacy-isolation" if isolated is True else None
        ),
        avoided_provider_microunits=avoided,
        avoided_recompute_units=1000,
        avoided_latency_ms=20,
    )


def make_receipt(
    route_id="route-a",
    costs=None,
    accepted_value=None,
    reuse_evidence=(),
    cohort=None,
    generation="g1",
    measurement_window_ref="window://fixture",
):
    return build_economics_receipt(
        route_id=route_id,
        mission_ref="aura://arena/mission/global-adoption-zero-friction/v1",
        measurement_window_ref=measurement_window_ref,
        currency=CURRENCY,
        cohort=cohort or {
            "device_class": "browser",
            "skill_class": "nontechnical-creator",
            "connectivity_class": "normal",
        },
        route_evidence=(evidence(generation),),
        friction_receipt_ref="drive://friction",
        accepted_value=accepted_value or accepted(),
        costs=costs if costs is not None else all_na_costs(),
        reuse_evidence=reuse_evidence,
    )


class AdoptionEconomicsTests(unittest.TestCase):
    def test_zero_burden_technical_route_is_not_user_cpav(self):
        r = make_receipt()
        self.assertEqual(0, r.lifecycle_monetary_total_microunits)
        self.assertEqual(ExactMicrounitRatio(0, 1), r.cpav_ratio)
        self.assertIsNone(r.user_cpav_ratio)
        self.assertEqual("RESOLVED_TECHNICAL", r.disposition)

    def test_user_cpav_is_exact_normalized_ratio(self):
        costs = all_na_costs()
        costs[0] = known_cost(CostKind.ONE_TIME_SETUP, 601)
        costs[1] = known_cost(CostKind.PROVIDER, 300)
        r = make_receipt(
            costs=costs,
            accepted_value=accepted(
                3, 4, AcceptedValueEvidenceClass.USER_EXPLICIT
            ),
        )
        self.assertEqual(901, r.lifecycle_monetary_total_microunits)
        self.assertEqual(ExactMicrounitRatio(901, 3), r.user_cpav_ratio)
        self.assertEqual(
            {"numerator_microunits": 901, "denominator_accepted_values": 3},
            r.to_dict()["user_cpav_ratio"],
        )

    def test_exact_ratio_normalizes_without_float(self):
        self.assertEqual(
            ExactMicrounitRatio(300, 1),
            ExactMicrounitRatio(900, 3),
        )
        with self.assertRaises(EconomicsError):
            ExactMicrounitRatio(1, 0)

    def test_zero_accepted_never_divides(self):
        costs = all_na_costs()
        costs[1] = known_cost(CostKind.PROVIDER, 500)
        r = make_receipt(
            costs=costs,
            accepted_value=accepted(
                0, 1, AcceptedValueEvidenceClass.USER_EXPLICIT
            ),
        )
        self.assertIsNone(r.cpav_ratio)
        self.assertEqual("NO_ACCEPTED_VALUE", r.disposition)
        a = compile_economics_admission(
            r, max_user_cpav_microunits=1000, allow_paid_candidate=True
        )
        self.assertFalse(a.paid_route_candidate)

    def test_unknown_cost_propagates(self):
        costs = all_na_costs()
        costs[1] = unknown_cost(CostKind.PROVIDER)
        r = make_receipt(costs=costs)
        self.assertIsNone(r.lifecycle_monetary_total_microunits)
        self.assertIn("PROVIDER", r.unknown_cost_kinds)

    def test_scenario_cost_not_observed(self):
        costs = all_na_costs()
        costs[1] = known_cost(
            CostKind.PROVIDER, 123, MoneyEvidenceClass.SCENARIO
        )
        r = make_receipt(costs=costs)
        self.assertIsNone(r.lifecycle_monetary_total_microunits)
        self.assertIn("PROVIDER", r.scenario_cost_kinds)

    def test_missing_cost_kind_fails(self):
        with self.assertRaises(EconomicsError) as ctx:
            make_receipt(costs=all_na_costs()[:-1])
        self.assertEqual("COST_KIND_COVERAGE_INVALID", ctx.exception.code)

    def test_duplicate_cost_kind_fails(self):
        costs = all_na_costs()
        costs[-1] = na_cost(CostKind.PROVIDER)
        with self.assertRaises(EconomicsError):
            make_receipt(costs=costs)

    def test_na_cannot_hide_value(self):
        with self.assertRaises(EconomicsError) as ctx:
            CostObservation(
                CostKind.PROVIDER,
                ObservationStatus.NOT_APPLICABLE,
                1,
                CURRENCY,
                MoneyEvidenceClass.MEASURED,
                "x",
                "g",
                "c",
                "n/a",
            )
        self.assertEqual(
            "NONKNOWN_COST_MUST_NOT_HAVE_VALUE", ctx.exception.code
        )

    def test_estimate_requires_policy_source(self):
        with self.assertRaises(EconomicsError) as ctx:
            known_cost(
                CostKind.LOCAL_ENERGY,
                10,
                MoneyEvidenceClass.ESTIMATED_WITH_POLICY,
                "measure://energy",
            )
        self.assertEqual(
            "ESTIMATED_COST_POLICY_REF_REQUIRED", ctx.exception.code
        )

    def test_validated_kv_reuse_builds_counterfactual_not_negative_cash(self):
        costs = all_na_costs()
        costs[1] = known_cost(CostKind.PROVIDER, 100)
        r = make_receipt(
            costs=costs,
            reuse_evidence=(reuse(avoided=50),),
        )
        self.assertEqual(100, r.lifecycle_monetary_total_microunits)
        self.assertEqual(50, r.validated_avoided_provider_microunits)
        self.assertEqual(150, r.counterfactual_without_reuse_microunits)
        self.assertEqual(
            ExactMicrounitRatio(150, 1),
            r.counterfactual_cpav_ratio,
        )

    def test_reuse_true_currentness_requires_evidence_ref(self):
        with self.assertRaises(EconomicsError) as ctx:
            ReuseEvidence(
                ReuseKind.KV_CACHE,
                ObservationStatus.KNOWN,
                "kv://run",
                "g1",
                "current:g1",
                MoneyEvidenceClass.MEASURED,
                "tenant-a",
                True,
                None,
                True,
                "receipt://privacy",
                50,
            )
        self.assertEqual(
            "SOURCE_CURRENT_EVIDENCE_REF_REQUIRED", ctx.exception.code
        )

    def test_reuse_true_privacy_requires_evidence_ref(self):
        with self.assertRaises(EconomicsError) as ctx:
            ReuseEvidence(
                ReuseKind.KV_CACHE,
                ObservationStatus.KNOWN,
                "kv://run",
                "g1",
                "current:g1",
                MoneyEvidenceClass.MEASURED,
                "tenant-a",
                True,
                "receipt://current",
                True,
                None,
                50,
            )
        self.assertEqual(
            "PRIVACY_ISOLATION_EVIDENCE_REF_REQUIRED", ctx.exception.code
        )

    def test_unisolated_kv_cache_gets_no_credit(self):
        r = make_receipt(
            reuse_evidence=(reuse(isolated=False),),
        )
        self.assertIsNone(r.validated_avoided_provider_microunits)
        self.assertTrue(
            any("PRIVACY_ISOLATION" in x for x in r.unresolved_reuse)
        )

    def test_stale_coordinate_cache_gets_no_credit(self):
        r = make_receipt(
            reuse_evidence=(
                reuse(
                    kind=ReuseKind.COORDINATE_MEMORY,
                    source_ref="coord://old",
                    current=False,
                ),
            ),
        )
        self.assertIsNone(r.validated_avoided_provider_microunits)
        self.assertTrue(
            any("SOURCE_CURRENTNESS" in x for x in r.unresolved_reuse)
        )

    def test_scenario_reuse_never_gets_monetary_credit(self):
        r = make_receipt(
            reuse_evidence=(
                reuse(evidence_class=MoneyEvidenceClass.SCENARIO),
            ),
        )
        self.assertIsNone(r.validated_avoided_provider_microunits)
        self.assertTrue(
            any("MONEY_EVIDENCE" in x for x in r.unresolved_reuse)
        )

    def test_cache_invalidation_is_explicit_cost(self):
        costs = all_na_costs()
        costs[-1] = known_cost(CostKind.CACHE_INVALIDATION, 70)
        self.assertEqual(
            70,
            make_receipt(costs=costs)
            .lifecycle_monetary_total_microunits,
        )

    def test_private_cohort_rejected(self):
        with self.assertRaises(EconomicsError) as ctx:
            make_receipt(cohort={"email": "a@example.com"})
        self.assertEqual(
            "COHORT_FIELD_NOT_PRIVACY_MINIMAL", ctx.exception.code
        )

    def test_identity_stable_across_sequence_order(self):
        costs = all_na_costs()
        reuse_items = (
            ReuseEvidence(
                ReuseKind.RECIPE,
                ObservationStatus.NOT_APPLICABLE,
                "recipe://x",
                "g1",
                "current:g1",
                MoneyEvidenceClass.MEASURED,
                "arena",
                True,
                "receipt://current",
                True,
                "receipt://privacy",
                reason="no money claim",
            ),
            ReuseEvidence(
                ReuseKind.WORKCAPSULE,
                ObservationStatus.NOT_APPLICABLE,
                "capsule://x",
                "g1",
                "current:g1",
                MoneyEvidenceClass.MEASURED,
                "arena",
                True,
                "receipt://current",
                True,
                "receipt://privacy",
                reason="no money claim",
            ),
        )
        a = make_receipt(costs=costs, reuse_evidence=reuse_items)
        b = make_receipt(
            costs=list(reversed(costs)),
            reuse_evidence=tuple(reversed(reuse_items)),
        )
        self.assertEqual(a.logical_id, b.logical_id)

    def test_source_generation_changes_identity(self):
        self.assertNotEqual(
            make_receipt(generation="g1").logical_id,
            make_receipt(generation="g2").logical_id,
        )

    def test_accepted_cannot_exceed_attempts(self):
        with self.assertRaises(EconomicsError) as ctx:
            accepted(2, 1)
        self.assertEqual(
            "ACCEPTED_VALUE_EXCEEDS_ATTEMPTS", ctx.exception.code
        )

    def test_consented_study_requires_consent(self):
        with self.assertRaises(EconomicsError):
            AcceptedValueEvidence(
                1,
                1,
                AcceptedValueEvidenceClass.CONSENTED_STUDY,
                "v",
                "r",
            )

    def test_paid_candidate_needs_positive_provider_cost(self):
        user = make_receipt(
            accepted_value=accepted(
                1, 1, AcceptedValueEvidenceClass.USER_EXPLICIT
            )
        )
        a = compile_economics_admission(
            user,
            max_user_cpav_microunits=100,
            allow_paid_candidate=True,
        )
        self.assertEqual(
            "NO_PAID_PROVIDER_COST_EVIDENCE", a.disposition
        )
        self.assertFalse(a.paid_route_candidate)

    def test_paid_candidate_needs_user_evidence_and_explicit_allow(self):
        technical_costs = all_na_costs()
        technical_costs[1] = known_cost(CostKind.PROVIDER, 10)
        a = compile_economics_admission(
            make_receipt(costs=technical_costs),
            max_user_cpav_microunits=100,
            allow_paid_candidate=True,
        )
        self.assertEqual("NEEDS_USER_VALUE_EVIDENCE", a.disposition)

        costs = all_na_costs()
        costs[1] = known_cost(CostKind.PROVIDER, 10)
        user = make_receipt(
            costs=costs,
            accepted_value=accepted(
                1, 1, AcceptedValueEvidenceClass.USER_EXPLICIT
            ),
        )
        b = compile_economics_admission(
            user,
            max_user_cpav_microunits=100,
            allow_paid_candidate=False,
        )
        self.assertFalse(b.paid_route_candidate)
        c = compile_economics_admission(
            user,
            max_user_cpav_microunits=100,
            allow_paid_candidate=True,
        )
        self.assertTrue(c.paid_route_candidate)
        self.assertFalse(c.payment_authorized)
        self.assertFalse(c.provider_authorized)

    def test_cpav_ceiling_comparison_is_exact(self):
        costs = all_na_costs()
        costs[1] = known_cost(CostKind.PROVIDER, 301)
        user = make_receipt(
            costs=costs,
            accepted_value=accepted(
                3, 3, AcceptedValueEvidenceClass.USER_EXPLICIT
            ),
        )
        below = compile_economics_admission(
            user,
            max_user_cpav_microunits=100,
            allow_paid_candidate=True,
        )
        self.assertEqual("EXCEEDS_CPAV_POLICY", below.disposition)
        exact_or_above = compile_economics_admission(
            user,
            max_user_cpav_microunits=101,
            allow_paid_candidate=True,
        )
        self.assertTrue(exact_or_above.paid_route_candidate)

    def test_exceeds_policy_not_candidate(self):
        costs = all_na_costs()
        costs[1] = known_cost(CostKind.PROVIDER, 500)
        user = make_receipt(
            costs=costs,
            accepted_value=accepted(
                1, 1, AcceptedValueEvidenceClass.USER_EXPLICIT
            ),
        )
        a = compile_economics_admission(
            user,
            max_user_cpav_microunits=100,
            allow_paid_candidate=True,
        )
        self.assertEqual("EXCEEDS_CPAV_POLICY", a.disposition)
        self.assertFalse(a.paid_route_candidate)

    def test_comparison_never_claims_overall_preference(self):
        a = make_receipt(route_id="a")
        costs = all_na_costs()
        costs[1] = known_cost(CostKind.PROVIDER, 10)
        b = make_receipt(route_id="b", costs=costs)
        c = compare_economics(a, b)
        self.assertTrue(c.comparable)
        self.assertEqual("a", c.lower_cpav_route_id)
        self.assertFalse(c.overall_route_preference_claimed)
        self.assertEqual(10, c.cpav_delta_ratio.numerator_microunits)

    def test_comparison_suppresses_cross_cohort_scalar(self):
        a = make_receipt(route_id="a")
        b = make_receipt(
            route_id="b",
            cohort={
                "device_class": "android",
                "skill_class": "nontechnical-creator",
            },
        )
        c = compare_economics(a, b)
        self.assertFalse(c.comparable)
        self.assertIn("COHORT", c.incompatibilities)
        self.assertIsNone(c.cpav_delta_ratio)

    def test_comparison_suppresses_cross_evidence_scalar(self):
        a = make_receipt(route_id="a")
        b = make_receipt(
            route_id="b",
            accepted_value=accepted(
                1, 1, AcceptedValueEvidenceClass.USER_EXPLICIT
            ),
        )
        c = compare_economics(a, b)
        self.assertFalse(c.comparable)
        self.assertIn(
            "ACCEPTED_VALUE_EVIDENCE_CLASS", c.incompatibilities
        )

    def test_comparison_suppresses_cross_window_scalar(self):
        a = make_receipt(
            route_id="a",
            measurement_window_ref="window://one",
        )
        b = make_receipt(
            route_id="b",
            measurement_window_ref="window://two",
        )
        c = compare_economics(a, b)
        self.assertFalse(c.comparable)
        self.assertIn("MEASUREMENT_WINDOW", c.incompatibilities)
        self.assertIsNone(c.cpav_delta_ratio)

    def test_serialized_effect_fields_hard_false(self):
        data = make_receipt().to_dict()
        self.assertFalse(data["payment_authorized"])
        self.assertFalse(data["provider_authorized"])
        self.assertFalse(data["execution_authorized"])
        self.assertTrue(data["logical_id"].startswith("aecon-"))


if __name__ == "__main__":
    unittest.main()

import copy
import json
import unittest
from dataclasses import replace
from pathlib import Path

import jsonschema

from tools.aura_adopt.adoption_economics import (
    AcceptedValueEvidence, AcceptedValueEvidenceClass, CostKind, CostObservation,
    EconomicsError, EvidenceBinding, ExactMicrounitRatio, MoneyEvidenceClass,
    ObservationStatus, ReuseEvidence, ReuseKind, build_economics_receipt,
    compare_economics, compile_economics_admission, validate_economics_receipt_dict,
    verify_economics_receipt,
)


def ev(ref="route:a", current="cur:1", klass="SOURCE_BOUND"):
    return EvidenceBinding(ref, "sha256:" + "1" * 64, "gen:1", current, klass)


def cost(kind, value=0, evidence=MoneyEvidenceClass.MEASURED, status=ObservationStatus.KNOWN,
         currency="USD", source_current=True, source_current_evidence_ref="cur-proof:1",
         policy_ref=None, reason=None):
    return CostObservation(kind, status, value if status is ObservationStatus.KNOWN else None,
                           currency, evidence, f"cost:{kind.value}", "gen:1", "cur:1",
                           source_current, source_current_evidence_ref, policy_ref, reason)


def costs(provider=100, *, provider_evidence=MoneyEvidenceClass.MEASURED):
    out=[]
    for k in CostKind:
        v = provider if k is CostKind.PROVIDER else (5 if k is CostKind.CACHE_INVALIDATION else 0)
        e = provider_evidence if k is CostKind.PROVIDER else MoneyEvidenceClass.MEASURED
        policy = "policy:provider-v1" if e is MoneyEvidenceClass.ESTIMATED_WITH_POLICY else None
        out.append(cost(k, v, e, policy_ref=policy))
    return out


def accepted(cls=AcceptedValueEvidenceClass.USER_EXPLICIT, accepted_count=2, attempts=3):
    return AcceptedValueEvidence(accepted_count, attempts, cls, "verifier:1", "accept:1",
                                 "consent:1" if cls is AcceptedValueEvidenceClass.CONSENTED_STUDY else None)


def reuse(ref="reuse:1", *, principal="principal:cohortA", currency="USD",
          avoided=40, source_current=True, privacy=True,
          evidence=MoneyEvidenceClass.MEASURED):
    return ReuseEvidence(ref, ReuseKind.KV_CACHE, ObservationStatus.KNOWN, "cache:1", "gen:1",
                         "cur:1", evidence, principal, currency, source_current,
                         "cur-proof:cache" if source_current else None, privacy,
                         "privacy-proof:cache" if privacy else None, avoided, 4, 5, None)


def receipt(**overrides):
    kwargs=dict(route_id="route-a", mission_ref="mission:adopt",
                accepted_value_definition_ref="avdef:v1", measurement_window_ref="window:1",
                principal_scope="principal:cohortA", currency="USD",
                cohort={"device_class":"desktop_laptop","skill_class":"nontechnical_creator"},
                route_evidence=[ev()], friction_receipt_ref="friction:1",
                accepted_value=accepted(), costs=costs(), reuse_evidence=[])
    kwargs.update(overrides)
    return build_economics_receipt(**kwargs)


class ZF10EconomicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_path = Path(__file__).parents[2] / "schemas" / "adoption_economics_receipt_v1.schema.json"
        cls.schema = json.loads(schema_path.read_text())
        jsonschema.Draft202012Validator.check_schema(cls.schema)
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def assertCode(self, code, fn):
        with self.assertRaises(EconomicsError) as cm:
            fn()
        self.assertEqual(code, cm.exception.code)

    def test_01_exact_ratio_preserves_over_2pow53(self):
        a=ExactMicrounitRatio(2**53,1); b=ExactMicrounitRatio(2**53+1,1)
        self.assertEqual(-1,a.compare(b)); self.assertNotEqual(a.logical(),b.logical())

    def test_02_cost_kind_coverage_required(self):
        self.assertCode("COST_KIND_COVERAGE_INVALID", lambda: receipt(costs=costs()[:-1]))

    def test_03_duplicate_cost_kind_rejected(self):
        cs=costs(); cs[-1]=cost(CostKind.PROVIDER, 5)
        self.assertCode("COST_KIND_COVERAGE_INVALID", lambda: receipt(costs=cs))

    def test_04_unknown_cost_keeps_total_unresolved(self):
        cs=costs(); cs[0]=cost(CostKind.ONE_TIME_SETUP,status=ObservationStatus.UNKNOWN,
                               evidence=MoneyEvidenceClass.UNKNOWN, source_current=None,
                               source_current_evidence_ref=None, reason="not measured")
        r=receipt(costs=cs); self.assertIsNone(r.lifecycle_monetary_total_microunits); self.assertIsNone(r.cpav_ratio)

    def test_05_scenario_cost_keeps_total_unresolved(self):
        cs=costs(); cs[0]=cost(CostKind.ONE_TIME_SETUP, 1, MoneyEvidenceClass.SCENARIO)
        r=receipt(costs=cs); self.assertEqual("UNRESOLVED", r.lifecycle_cost_provenance); self.assertIn("ONE_TIME_SETUP",r.scenario_cost_kinds)

    def test_06_estimated_cost_is_typed_not_observed(self):
        cs=costs(provider_evidence=MoneyEvidenceClass.ESTIMATED_WITH_POLICY)
        r=receipt(costs=cs); self.assertEqual("ESTIMATED", r.lifecycle_cost_provenance); self.assertEqual("RESOLVED_ESTIMATED_USER",r.disposition)

    def test_07_estimated_cost_cannot_admit_paid(self):
        r=receipt(costs=costs(provider_evidence=MoneyEvidenceClass.ESTIMATED_WITH_POLICY))
        a=compile_economics_admission(r,max_user_cpav_microunits=1000,allow_paid_candidate=True)
        self.assertFalse(a.paid_route_candidate); self.assertEqual("NEEDS_OBSERVED_COST_EVIDENCE",a.disposition)

    def test_08_na_requires_specific_assertion_evidence(self):
        self.assertCode("NA_COST_EVIDENCE_REQUIRED", lambda: cost(CostKind.PROVIDER,status=ObservationStatus.NOT_APPLICABLE,evidence=MoneyEvidenceClass.UNKNOWN,reason="none"))

    def test_09_na_requires_currentness(self):
        self.assertCode("NA_COST_SOURCE_NOT_CURRENT", lambda: cost(CostKind.PROVIDER,status=ObservationStatus.NOT_APPLICABLE,evidence=MoneyEvidenceClass.NOT_APPLICABLE_ASSERTION,source_current=False,source_current_evidence_ref=None,reason="not used"))

    def test_10_valid_na_is_zero_but_evidenced(self):
        cs=costs(); cs[1]=cost(CostKind.PROVIDER,status=ObservationStatus.NOT_APPLICABLE,evidence=MoneyEvidenceClass.NOT_APPLICABLE_ASSERTION,reason="route has no provider")
        r=receipt(costs=cs); self.assertEqual("OBSERVED",r.lifecycle_cost_provenance); self.assertEqual(5,r.lifecycle_monetary_total_microunits)

    def test_11_zero_accepted_value_has_no_cpav(self):
        r=receipt(accepted_value=accepted(accepted_count=0,attempts=3)); self.assertIsNone(r.cpav_ratio); self.assertEqual("NO_ACCEPTED_VALUE",r.disposition)

    def test_12_technical_acceptance_never_user_cpav(self):
        r=receipt(accepted_value=accepted(AcceptedValueEvidenceClass.TECHNICAL_EXECUTED)); self.assertIsNotNone(r.cpav_ratio); self.assertIsNone(r.user_cpav_ratio)

    def test_13_accepted_cannot_exceed_attempts(self):
        self.assertCode("ACCEPTED_VALUE_EXCEEDS_ATTEMPTS", lambda: accepted(accepted_count=4,attempts=3))

    def test_14_duplicate_reuse_evidence_ref_rejected(self):
        x=reuse(); y=replace(x, avoided_provider_microunits=41)
        self.assertCode("DUPLICATE_REUSE_EVIDENCE", lambda: receipt(reuse_evidence=[x,y]))

    def test_15_duplicate_logical_reuse_rejected(self):
        x=reuse(); self.assertCode("DUPLICATE_REUSE_EVIDENCE", lambda: receipt(reuse_evidence=[x,x]))

    def test_16_valid_reuse_is_counterfactual_only(self):
        r=receipt(reuse_evidence=[reuse()]); self.assertEqual(105,r.lifecycle_monetary_total_microunits); self.assertEqual(40,r.validated_avoided_provider_microunits); self.assertEqual(145,r.counterfactual_without_reuse_microunits)

    def test_17_principal_mismatch_blocks_reuse_credit(self):
        r=receipt(reuse_evidence=[reuse(principal="principal:other")]); self.assertIsNone(r.validated_avoided_provider_microunits); self.assertTrue(any("PRINCIPAL_SCOPE" in x for x in r.unresolved_reuse))

    def test_18_currency_mismatch_blocks_reuse_credit(self):
        r=receipt(reuse_evidence=[reuse(currency="EUR")]); self.assertIsNone(r.validated_avoided_provider_microunits); self.assertTrue(any("CURRENCY" in x for x in r.unresolved_reuse))

    def test_19_uncurrent_reuse_blocks_credit(self):
        r=receipt(reuse_evidence=[reuse(source_current=False)]); self.assertIsNone(r.validated_avoided_provider_microunits)

    def test_20_unisolated_reuse_blocks_credit(self):
        r=receipt(reuse_evidence=[reuse(privacy=False)]); self.assertIsNone(r.validated_avoided_provider_microunits)

    def test_21_estimated_reuse_blocks_money_credit(self):
        r=receipt(reuse_evidence=[reuse(evidence=MoneyEvidenceClass.ESTIMATED_WITH_POLICY)]); self.assertIsNone(r.validated_avoided_provider_microunits)

    def test_22_cache_invalidation_cost_is_counted(self):
        r=receipt(); self.assertEqual(105,r.lifecycle_monetary_total_microunits)

    def test_23_forged_derived_receipt_is_rejected(self):
        r=receipt(); forged=replace(r,user_cpav_ratio=ExactMicrounitRatio(0,1))
        self.assertCode("ECONOMICS_RECEIPT_DERIVATION_MISMATCH", lambda: compile_economics_admission(forged,max_user_cpav_microunits=1000,allow_paid_candidate=True))

    def test_24_forged_logical_id_is_rejected(self):
        r=receipt(); forged=replace(r,logical_id="aecon-"+"0"*64)
        self.assertCode("ECONOMICS_RECEIPT_DERIVATION_MISMATCH", lambda: verify_economics_receipt(forged))

    def test_25_paid_route_requires_positive_observed_provider_cost(self):
        cs=costs(provider=0); r=receipt(costs=cs); a=compile_economics_admission(r,max_user_cpav_microunits=1000,allow_paid_candidate=True)
        self.assertEqual("NO_PAID_PROVIDER_COST_EVIDENCE",a.disposition); self.assertFalse(a.paid_route_candidate)

    def test_26_paid_route_candidate_still_has_no_authority(self):
        r=receipt(); a=compile_economics_admission(r,max_user_cpav_microunits=1000,allow_paid_candidate=True)
        self.assertTrue(a.paid_route_candidate); self.assertFalse(a.payment_authorized or a.provider_authorized or a.execution_authorized)

    def test_27_mission_mismatch_blocks_comparison(self):
        c=receipt(route_id="route-b",mission_ref="mission:other"); x=compare_economics(receipt(),c); self.assertFalse(x.comparable); self.assertIn("MISSION",x.incompatibilities)

    def test_28_value_definition_mismatch_blocks_comparison(self):
        c=receipt(route_id="route-b",accepted_value_definition_ref="avdef:v2"); x=compare_economics(receipt(),c); self.assertIn("ACCEPTED_VALUE_DEFINITION",x.incompatibilities)

    def test_29_window_mismatch_blocks_comparison(self):
        c=receipt(route_id="route-b",measurement_window_ref="window:2"); self.assertIn("MEASUREMENT_WINDOW",compare_economics(receipt(),c).incompatibilities)

    def test_30_provenance_mismatch_blocks_comparison(self):
        c=receipt(route_id="route-b",costs=costs(provider_evidence=MoneyEvidenceClass.ESTIMATED_WITH_POLICY)); self.assertIn("COST_PROVENANCE",compare_economics(receipt(),c).incompatibilities)

    def test_31_total_sort_key_makes_route_evidence_order_invariant(self):
        e1=ev("route:a",current="cur:1",klass="A"); e2=ev("route:a",current="cur:2",klass="B")
        r1=receipt(route_evidence=[e1,e2]); r2=receipt(route_evidence=[e2,e1]); self.assertEqual(r1.logical_id,r2.logical_id)

    def test_32_duplicate_route_evidence_rejected(self):
        e=ev(); self.assertCode("DUPLICATE_ROUTE_EVIDENCE",lambda: receipt(route_evidence=[e,e]))

    def test_33_private_or_freeform_cohort_value_rejected(self):
        self.assertCode("COHORT_VALUE_NOT_PRIVACY_MINIMAL",lambda: receipt(cohort={"device_class":"alice@example.com"}))

    def test_34_schema_validates_real_receipt(self):
        self.validator.validate(receipt(reuse_evidence=[reuse()]).to_dict())

    def test_35_schema_rejects_technical_user_cpav(self):
        d=receipt(accepted_value=accepted(AcceptedValueEvidenceClass.TECHNICAL_EXECUTED)).to_dict(); d["user_cpav_ratio"]={"numerator_microunits":1,"denominator_accepted_values":1}
        self.assertTrue(list(self.validator.iter_errors(d)))

    def test_36_schema_requires_each_cost_kind(self):
        d=receipt().to_dict(); d["costs"]=[copy.deepcopy(d["costs"][1]) for _ in range(7)]
        self.assertTrue(list(self.validator.iter_errors(d)))

    def test_37_semantic_validator_rejects_accepted_gt_attempts(self):
        d=receipt().to_dict(); d["accepted_value"]["accepted_count"]=10; d["accepted_value"]["attempt_count"]=1
        self.assertCode("ACCEPTED_VALUE_EXCEEDS_ATTEMPTS",lambda: validate_economics_receipt_dict(d))

    def test_38_schema_has_semantic_validator_extension(self):
        self.assertEqual("tools.aura_adopt.adoption_economics.validate_economics_receipt_dict",self.schema["x-aura-semantic-validator"])

    def test_39_authority_flags_are_hard_false_in_schema(self):
        d=receipt().to_dict(); d["payment_authorized"]=True
        self.assertTrue(list(self.validator.iter_errors(d)))

    def test_40_receipt_serialization_is_json_canonicalizable(self):
        d=receipt(reuse_evidence=[reuse()]).to_dict(); json.dumps(d,sort_keys=True,allow_nan=False)


if __name__ == "__main__":
    unittest.main()

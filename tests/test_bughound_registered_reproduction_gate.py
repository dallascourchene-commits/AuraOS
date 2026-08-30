from __future__ import annotations

from dataclasses import replace
import unittest

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.registered_reproduction_gate import (
    BugHoundIndependentReproductionRegistryRecordV1,
    _compose_registered_independent_reproduction,
    admit_with_registered_independent_reproduction,
    independent_reproduction_registry_receipt,
    registered_reproduction_parameter_names,
)


class RegisteredIndependentReproductionGateTests(unittest.TestCase):
    def mission(self):
        return BugHoundCashMissionInputV1(
            profile_id="BUGHOUND_CASH_BOUNTY_V1",
            program_ref="program://cash",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            program_state="ACTIVE",
            cash_reward_state="VERIFIED_CURRENT_CASH_REWARD",
            reward_currency="USD",
            reward_floor_minor=10000,
            reward_ceiling_minor=50000,
            payout_rules_digest="payout-v1",
            scope_state="CURRENT_SCOPE_BOUND",
            scope_rules_digest="scope-v1",
            source_state="CURRENT_SOURCE_BOUND",
            source_currentness_ref="source-v1",
            testing_ceiling="PUBLIC_SOURCE_AND_LOCAL_AUTHORIZED_ONLY",
        )

    def candidate(self):
        return BountyCandidateEvidenceV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            security_invariant_digest="inv-1",
            causal_cone_digest="cone-1",
            discovery_receipt_digest="disc-1",
            discovery_reproduction_state="REPRODUCED_CURRENT",
            claimed_consequence_band="CONSERVATIVE_MEDIUM",
        )

    def repro(self):
        return IndependentBountyReproductionReceiptV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            reproducer_ref="reproducer://independent-1",
            reproducer_generation="repro-gen-1",
            result="REPRODUCED_CURRENT",
            witness_digest="witness-1",
            environment_digest="env-1",
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-v1",
        )

    def record(self, repro=None):
        repro = repro or self.repro()
        return BugHoundIndependentReproductionRegistryRecordV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            reproduction_receipt_digest=repro.receipt_digest,
            reproducer_ref=repro.reproducer_ref,
            reproducer_generation=repro.reproducer_generation,
            witness_digest=repro.witness_digest,
            environment_digest=repro.environment_digest,
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-v1",
            registry_receipt_ref="registry://receipt/current",
            registry_observer_ref="registry://observer/independent",
            registry_observer_generation="registry-gen-1",
            registry_current=True,
            independently_observed=True,
        )

    def private_admit(self, *, repro=None, record=None):
        repro = repro or self.repro()
        record = record or self.record(repro)
        return _compose_registered_independent_reproduction(
            mission_input=self.mission(),
            candidate=self.candidate(),
            independent_reproduction=repro,
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-current-1",
            record=record,
        )

    def public_kwargs(self):
        return dict(
            mission_input=self.mission(),
            candidate=self.candidate(),
            independent_reproduction=self.repro(),
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-current-1",
        )

    def test_private_exact_record_plumbs_without_effect_authority(self):
        out = self.private_admit()
        self.assertTrue(out.independent_reproduction_registry_proven)
        self.assertFalse(out.duplicate_check_producer_proven)
        self.assertFalse(out.report_lint_producer_proven)
        self.assertFalse(out.program_admissibility_producer_proven)
        self.assertFalse(out.external_effect)
        self.assertFalse(out.submission_authorized)
        self.assertTrue(out.candidate_admission.ready_for_human_submission_review)

    def test_production_registry_is_source_owned_empty_hold(self):
        receipt = independent_reproduction_registry_receipt()
        self.assertEqual("BUGHOUND_INDEPENDENT_REPRODUCTION_REGISTRY_HOLD_V2", receipt.registry_generation)
        self.assertEqual((), receipt.record_digests)
        self.assertEqual(0, receipt.active_record_count)
        self.assertFalse(receipt.authority)
        self.assertFalse(receipt.external_effect)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED"):
            admit_with_registered_independent_reproduction(**self.public_kwargs())

    def test_public_signature_has_no_caller_trust_root(self):
        params = set(registered_reproduction_parameter_names())
        for forbidden in (
            "registry_lookup",
            "registry",
            "records",
            "record",
            "expected_independent_reproduction_digest",
            "expected_reproducer_ref",
            "expected_reproducer_generation",
            "trusted",
        ):
            self.assertNotIn(forbidden, params)

    def test_caller_registry_lookup_override_is_not_an_api(self):
        with self.assertRaises(TypeError):
            admit_with_registered_independent_reproduction(
                **self.public_kwargs(), registry_lookup=lambda _: self.record()
            )

    def test_caller_record_override_is_not_an_api(self):
        with self.assertRaises(TypeError):
            admit_with_registered_independent_reproduction(
                **self.public_kwargs(), record=self.record()
            )

    def test_caller_expected_fields_are_not_an_api(self):
        for field in (
            "expected_independent_reproduction_digest",
            "expected_reproducer_ref",
            "expected_reproducer_generation",
        ):
            with self.subTest(field=field):
                with self.assertRaises(TypeError):
                    admit_with_registered_independent_reproduction(
                        **self.public_kwargs(), **{field: "forged"}
                    )

    def test_receipt_digest_substitution_fails_privately(self):
        with self.assertRaisesRegex(ValueError, "REPRODUCTION_RECEIPT_DIGEST_MISMATCH"):
            self.private_admit(record=replace(self.record(), reproduction_receipt_digest="wrong"))

    def test_reproducer_identity_substitution_fails_privately(self):
        with self.assertRaisesRegex(ValueError, "REPRODUCER_REF_MISMATCH"):
            self.private_admit(record=replace(self.record(), reproducer_ref="other"))

    def test_reproducer_generation_substitution_fails_privately(self):
        with self.assertRaisesRegex(ValueError, "REPRODUCER_GENERATION_MISMATCH"):
            self.private_admit(record=replace(self.record(), reproducer_generation="other"))

    def test_witness_and_environment_substitution_fail_privately(self):
        for field in ("witness_digest", "environment_digest"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field.upper() + "_MISMATCH"):
                    self.private_admit(record=replace(self.record(), **{field: "other"}))

    def test_scope_and_source_currentness_substitution_fail_privately(self):
        with self.assertRaisesRegex(ValueError, "SCOPE_RULES_DIGEST_MISMATCH"):
            self.private_admit(record=replace(self.record(), scope_rules_digest="other"))
        with self.assertRaisesRegex(ValueError, "SOURCE_CURRENTNESS_REF_MISMATCH"):
            self.private_admit(record=replace(self.record(), source_currentness_ref="old"))

    def test_stale_nonindependent_or_revoked_record_fails_privately(self):
        cases = (
            (replace(self.record(), registry_current=False), "REGISTRY_STALE"),
            (replace(self.record(), independently_observed=False), "INDEPENDENT_OBSERVER_REQUIRED"),
            (replace(self.record(), revoked=True), "INDEPENDENT_REPRODUCTION_REVOKED"),
        )
        for record, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(ValueError, code):
                    self.private_admit(record=record)

    def test_registry_effect_or_authority_widening_fails_privately(self):
        for field in (
            "live_target_testing_authorized",
            "credential_use_authorized",
            "submission_authorized",
            "claim_or_payment_authorized",
            "external_effect",
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.private_admit(record=replace(self.record(), **{field: True}))

    def test_reproduction_external_effect_fails_public_before_registry(self):
        kwargs = self.public_kwargs()
        kwargs["independent_reproduction"] = replace(self.repro(), external_effect=True)
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN"):
            admit_with_registered_independent_reproduction(**kwargs)

    def test_target_substitution_fails_privately(self):
        with self.assertRaisesRegex(ValueError, "TARGET_REF_MISMATCH"):
            self.private_admit(record=replace(self.record(), target_ref="target://other"))

    def test_private_fixture_output_digest_is_deterministic(self):
        self.assertEqual(
            self.private_admit().receipt_digest,
            self.private_admit().receipt_digest,
        )


if __name__ == "__main__":
    unittest.main()

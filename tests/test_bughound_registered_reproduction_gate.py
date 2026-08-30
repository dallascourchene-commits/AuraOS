from __future__ import annotations

from dataclasses import replace
from unittest import mock
import inspect
import unittest

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
import tools.bughound.registered_reproduction_gate as registry_mod
from tools.bughound.registered_reproduction_gate import (
    BugHoundIndependentReproductionRegistryRecordV1,
    REGISTRY_GENERATION,
    admit_with_registered_independent_reproduction,
    independent_reproduction_registry_receipt,
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

    def admit(self, *, repro=None, record=None, **extra):
        repro = repro or self.repro()
        record = record or self.record(repro)
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            return admit_with_registered_independent_reproduction(
                mission_input=self.mission(),
                candidate=self.candidate(),
                independent_reproduction=repro,
                duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
                duplicate_check_currentness_ref="dup-current-1",
                report_lint_state="REPORT_LINT_CLEAN",
                report_digest="report-1",
                program_admissibility_state="CURRENTLY_ADMISSIBLE",
                program_admissibility_ref="program-current-1",
                **extra,
            )

    def test_registered_path_plumbs_to_candidate_without_effect_authority(self):
        out = self.admit()
        self.assertTrue(out.independent_reproduction_registry_proven)
        self.assertEqual(REGISTRY_GENERATION, out.registry_generation)
        self.assertTrue(out.registry_digest)
        self.assertFalse(out.duplicate_check_producer_proven)
        self.assertFalse(out.report_lint_producer_proven)
        self.assertFalse(out.program_admissibility_producer_proven)
        self.assertFalse(out.external_effect)
        self.assertFalse(out.submission_authorized)
        self.assertTrue(out.candidate_admission.ready_for_human_submission_review)

    def test_default_production_registry_is_empty_hold(self):
        registry = independent_reproduction_registry_receipt()
        self.assertEqual(REGISTRY_GENERATION, registry.registry_generation)
        self.assertEqual((), registry.record_digests)
        self.assertEqual(0, registry.active_record_count)
        self.assertFalse(registry.authority)
        self.assertFalse(registry.external_effect)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED"):
            admit_with_registered_independent_reproduction(
                mission_input=self.mission(), candidate=self.candidate(),
                independent_reproduction=self.repro(),
                duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
                duplicate_check_currentness_ref="dup-current-1",
                report_lint_state="REPORT_LINT_CLEAN", report_digest="report-1",
                program_admissibility_state="CURRENTLY_ADMISSIBLE",
                program_admissibility_ref="program-current-1",
            )

    def test_public_signature_has_no_caller_trust_root_parameters(self):
        params = set(inspect.signature(admit_with_registered_independent_reproduction).parameters)
        for forbidden in (
            "expected_independent_reproduction_digest",
            "expected_reproducer_ref",
            "expected_reproducer_generation",
            "registry_lookup",
            "registry",
            "registry_record",
        ):
            self.assertNotIn(forbidden, params)

    def test_caller_registry_lookup_override_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, "CALLER_REPRODUCTION_REGISTRY_FORBIDDEN"):
            admit_with_registered_independent_reproduction(
                mission_input=self.mission(),
                candidate=self.candidate(),
                independent_reproduction=self.repro(),
                duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
                duplicate_check_currentness_ref="dup-current-1",
                report_lint_state="REPORT_LINT_CLEAN",
                report_digest="report-1",
                program_admissibility_state="CURRENTLY_ADMISSIBLE",
                program_admissibility_ref="program-current-1",
                registry_lookup=lambda _: self.record(),
            )

    def test_caller_expected_digest_override_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, "CALLER_REPRODUCTION_EXPECTATION_FORBIDDEN"):
            self.admit(expected_independent_reproduction_digest="forged")

    def test_caller_expected_reproducer_override_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, "CALLER_REPRODUCTION_EXPECTATION_FORBIDDEN"):
            self.admit(expected_reproducer_ref="reproducer://caller")

    def test_receipt_digest_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "REPRODUCTION_RECEIPT_DIGEST_MISMATCH"):
            self.admit(record=replace(self.record(), reproduction_receipt_digest="wrong"))

    def test_reproducer_identity_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "REPRODUCER_REF_MISMATCH"):
            self.admit(record=replace(self.record(), reproducer_ref="other"))

    def test_reproducer_generation_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "REPRODUCER_GENERATION_MISMATCH"):
            self.admit(record=replace(self.record(), reproducer_generation="other"))

    def test_witness_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_DIGEST_MISMATCH"):
            self.admit(record=replace(self.record(), witness_digest="other"))

    def test_environment_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "ENVIRONMENT_DIGEST_MISMATCH"):
            self.admit(record=replace(self.record(), environment_digest="other"))

    def test_scope_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "SCOPE_RULES_DIGEST_MISMATCH"):
            self.admit(record=replace(self.record(), scope_rules_digest="other"))

    def test_source_currentness_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_CURRENTNESS_REF_MISMATCH"):
            self.admit(record=replace(self.record(), source_currentness_ref="old"))

    def test_stale_registry_fails(self):
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_STALE"):
            self.admit(record=replace(self.record(), registry_current=False))

    def test_nonindependent_observer_fails(self):
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_OBSERVER_REQUIRED"):
            self.admit(record=replace(self.record(), independently_observed=False))

    def test_revoked_record_fails(self):
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REVOKED"):
            self.admit(record=replace(self.record(), revoked=True))

    def test_registry_external_effect_widening_fails(self):
        with self.assertRaisesRegex(ValueError, "REPRO_REGISTRY_EXTERNAL_EFFECT_FORBIDDEN"):
            self.admit(record=replace(self.record(), external_effect=True))

    def test_reproduction_external_effect_fails_before_registry(self):
        repro = replace(self.repro(), external_effect=True)
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN"):
            self.admit(repro=repro, record=self.record(repro))

    def test_target_substitution_fails(self):
        with self.assertRaisesRegex(ValueError, "TARGET_REF_MISMATCH"):
            self.admit(record=replace(self.record(), target_ref="target://other"))

    def test_ambiguous_exact_digest_registry_fails_closed(self):
        repro = self.repro()
        a = self.record(repro)
        b = replace(a, registry_receipt_ref="registry://receipt/other")
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (a, b)):
            with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_AMBIGUOUS"):
                admit_with_registered_independent_reproduction(
                    mission_input=self.mission(),
                    candidate=self.candidate(),
                    independent_reproduction=repro,
                    duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
                    duplicate_check_currentness_ref="dup-current-1",
                    report_lint_state="REPORT_LINT_CLEAN",
                    report_digest="report-1",
                    program_admissibility_state="CURRENTLY_ADMISSIBLE",
                    program_admissibility_ref="program-current-1",
                )

    def test_output_digest_is_deterministic(self):
        self.assertEqual(self.admit().receipt_digest, self.admit().receipt_digest)


if __name__ == "__main__":
    unittest.main()

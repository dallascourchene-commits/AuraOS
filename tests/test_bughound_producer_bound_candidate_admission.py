from __future__ import annotations

from dataclasses import replace
import unittest

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.candidate_evidence_registry import (
    CandidateEvidenceProducerRecordV1,
    REGISTRY_GENERATION,
    candidate_evidence_registry_receipt,
)
from tools.bughound.producer_bound_candidate_admission import (
    BugHoundCashCandidateEvidenceBundleV1,
    _compose_registered_candidate_receipt,
    admit_producer_bound_cash_bounty_candidate_for_human_review,
    producer_bound_admission_parameter_names,
    seal_candidate_evidence_bundle,
    validate_candidate_evidence_bundle,
)


class ProducerBoundCandidateAdmissionTests(unittest.TestCase):
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
            security_invariant_digest="invariant-1",
            causal_cone_digest="cone-1",
            discovery_receipt_digest="discovery-1",
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

    def bundle(self, **changes):
        values = dict(
            producer_ref="producer://cash-evidence-registry",
            producer_generation="producer-gen-1",
            producer_currentness_ref="producer-current-1",
            candidate=self.candidate(),
            independent_reproduction=self.repro(),
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-admission-1",
        )
        values.update(changes)
        return BugHoundCashCandidateEvidenceBundleV1(**values)

    def record(self, bundle=None, **changes):
        bundle = bundle or self.bundle()
        repro = bundle.independent_reproduction
        values = dict(
            producer_ref=bundle.producer_ref,
            producer_generation=bundle.producer_generation,
            producer_currentness_ref=bundle.producer_currentness_ref,
            evidence_bundle_digest=bundle.bundle_digest,
            target_ref=bundle.candidate.target_ref,
            target_generation=bundle.candidate.target_generation,
            scope_rules_digest=repro.scope_rules_digest,
            source_currentness_ref=repro.source_currentness_ref,
            independent_reproduction_digest=repro.receipt_digest,
            duplicate_check_currentness_ref=bundle.duplicate_check_currentness_ref,
            report_digest=bundle.report_digest,
            program_admissibility_ref=bundle.program_admissibility_ref,
        )
        values.update(changes)
        return CandidateEvidenceProducerRecordV1(**values)

    def validation(self, bundle=None):
        return validate_candidate_evidence_bundle(
            mission_input=self.mission(), evidence_bundle=bundle or self.bundle()
        )

    def test_production_registry_is_source_owned_empty_hold(self):
        registry = candidate_evidence_registry_receipt()
        self.assertEqual("BUGHOUND_CANDIDATE_EVIDENCE_REGISTRY_HOLD_V1", REGISTRY_GENERATION)
        self.assertEqual(0, registry.active_producer_count)
        self.assertEqual((), registry.record_digests)
        self.assertFalse(registry.authority)
        self.assertFalse(registry.external_effect)

    def test_public_consequence_abi_has_no_caller_trust_root(self):
        self.assertEqual(
            {"mission_input", "evidence_bundle"},
            set(producer_bound_admission_parameter_names()),
        )
        for forbidden in (
            "producer_envelope",
            "producer_secret",
            "verifier_held_producer_secret",
            "expected_producer_ref",
            "expected_producer_generation",
            "registry",
            "registry_record",
            "trusted",
            "producer_trust_proven",
            "independent_reproduction",
            "duplicate_pressure_state",
            "report_lint_state",
            "program_admissibility_state",
        ):
            self.assertNotIn(forbidden, producer_bound_admission_parameter_names())

    def test_caller_hmac_is_integrity_only_not_authentication(self):
        bundle = self.bundle()
        a = seal_candidate_evidence_bundle(bundle, producer_secret=b"caller-a")
        b = seal_candidate_evidence_bundle(bundle, producer_secret=b"caller-b")
        self.assertNotEqual(a.mac_hex, b.mac_hex)
        self.assertFalse(a.producer_authentication_proven)
        self.assertFalse(a.authority)
        self.assertFalse(a.external_effect)

    def test_valid_lower_bundle_is_preserved_but_not_promoted(self):
        receipt = self.validation()
        self.assertTrue(receipt.lower_ready_for_human_submission_review)
        self.assertEqual("READY_FOR_HUMAN_SUBMISSION_REVIEW", receipt.lower_status)
        self.assertFalse(receipt.candidate_producer_trust_proven)
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertFalse(receipt.authority)
        self.assertFalse(receipt.external_effect)

    def test_public_admission_fails_closed_without_source_owned_producer(self):
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_PRODUCER_TRUST_UNPROVEN"):
            admit_producer_bound_cash_bounty_candidate_for_human_review(
                mission_input=self.mission(), evidence_bundle=self.bundle()
            )

    def test_private_future_registry_fixture_can_promote_only_exact_lower_result(self):
        bundle = self.bundle()
        receipt = _compose_registered_candidate_receipt(
            validation=self.validation(bundle),
            evidence_bundle=bundle,
            record=self.record(bundle),
        )
        self.assertTrue(receipt.candidate_producer_trust_proven)
        self.assertTrue(receipt.ready_for_human_submission_review)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.credential_use_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.claim_or_payment_authorized)
        self.assertFalse(receipt.external_effect)

    def test_registry_bundle_digest_substitution_fails(self):
        bundle = self.bundle()
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_BINDING_MISMATCH"):
            _compose_registered_candidate_receipt(
                validation=self.validation(bundle),
                evidence_bundle=bundle,
                record=self.record(bundle, evidence_bundle_digest="0" * 64),
            )

    def test_registry_producer_currentness_substitution_fails(self):
        bundle = self.bundle()
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_BINDING_MISMATCH"):
            _compose_registered_candidate_receipt(
                validation=self.validation(bundle),
                evidence_bundle=bundle,
                record=self.record(bundle, producer_currentness_ref="stale"),
            )

    def test_revoked_or_unobserved_registry_record_fails(self):
        bundle = self.bundle()
        for changes in (
            {"revoked": True},
            {"current": False},
            {"independently_observed": False},
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_NOT_CURRENT"):
                    _compose_registered_candidate_receipt(
                        validation=self.validation(bundle),
                        evidence_bundle=bundle,
                        record=self.record(bundle, **changes),
                    )

    def test_registry_authority_or_effect_widening_fails(self):
        bundle = self.bundle()
        for changes in ({"authority": True}, {"external_effect": True}):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_AUTHORITY_WIDENED"):
                    _compose_registered_candidate_receipt(
                        validation=self.validation(bundle),
                        evidence_bundle=bundle,
                        record=self.record(bundle, **changes),
                    )

    def test_external_effect_reproduction_fails_before_registry_resolution(self):
        bundle = self.bundle(
            independent_reproduction=replace(self.repro(), external_effect=True)
        )
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN"):
            self.validation(bundle)

    def test_public_known_root_stays_blocked_even_with_exact_private_registry_fixture(self):
        bundle = self.bundle(duplicate_pressure_state="PUBLICLY_KNOWN_ROOT_CAUSE")
        validation = self.validation(bundle)
        self.assertFalse(validation.lower_ready_for_human_submission_review)
        receipt = _compose_registered_candidate_receipt(
            validation=validation,
            evidence_bundle=bundle,
            record=self.record(bundle),
        )
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertEqual("BOUNTY_CANDIDATE_BLOCKED", receipt.status)

    def test_validation_digest_is_deterministic(self):
        self.assertEqual(self.validation().validation_digest, self.validation().validation_digest)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import replace
import unittest

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.producer_bound_candidate_admission import (
    BugHoundCashCandidateEvidenceBundleV1,
    admit_producer_bound_cash_bounty_candidate_for_human_review,
    producer_bound_admission_parameter_names,
    seal_candidate_evidence_bundle,
)


class ProducerBoundCandidateAdmissionTests(unittest.TestCase):
    SECRET = b"arena-held-producer-secret"

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

    def bundle(self):
        return BugHoundCashCandidateEvidenceBundleV1(
            producer_ref="producer://cash-evidence-registry",
            producer_generation="producer-gen-1",
            candidate=self.candidate(),
            independent_reproduction=self.repro(),
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-admission-1",
        )

    def admit(self, *, bundle=None, envelope=None, secret=None, ref=None, generation=None):
        bundle = bundle or self.bundle()
        envelope = envelope or seal_candidate_evidence_bundle(
            bundle, producer_secret=self.SECRET
        )
        return admit_producer_bound_cash_bounty_candidate_for_human_review(
            mission_input=self.mission(),
            evidence_bundle=bundle,
            producer_envelope=envelope,
            verifier_held_producer_secret=self.SECRET if secret is None else secret,
            expected_producer_ref=ref or "producer://cash-evidence-registry",
            expected_producer_generation=generation or "producer-gen-1",
        )

    def test_exact_producer_bound_bundle_can_reach_human_review_only(self):
        receipt = self.admit()
        self.assertTrue(receipt.candidate_producer_trust_proven)
        self.assertTrue(receipt.ready_for_human_submission_review)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.credential_use_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.claim_or_payment_authorized)
        self.assertFalse(receipt.external_effect)

    def test_public_abi_has_no_bare_assertion_leaves(self):
        names = set(producer_bound_admission_parameter_names())
        for forbidden in (
            "duplicate_pressure_state",
            "report_lint_state",
            "program_admissibility_state",
            "independent_reproduction",
            "expected_independent_reproduction_digest",
            "benchmark_score",
            "seeded_true_positive",
            "adjudication",
            "oracle",
            "trusted",
            "producer_trust_proven",
        ):
            self.assertNotIn(forbidden, names)

    def test_wrong_verifier_secret_fails(self):
        with self.assertRaisesRegex(ValueError, "PRODUCER_AUTHENTICATION_FAILED"):
            self.admit(secret=b"wrong")

    def test_wrong_expected_producer_ref_fails(self):
        with self.assertRaisesRegex(ValueError, "PRODUCER_REF_MISMATCH"):
            self.admit(ref="producer://wrong")

    def test_wrong_expected_producer_generation_fails(self):
        with self.assertRaisesRegex(ValueError, "PRODUCER_GENERATION_MISMATCH"):
            self.admit(generation="producer-gen-2")

    def test_tampered_duplicate_state_fails_old_envelope(self):
        original = self.bundle()
        envelope = seal_candidate_evidence_bundle(original, producer_secret=self.SECRET)
        tampered = replace(original, duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE_X")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_BUNDLE_DIGEST_MISMATCH"):
            self.admit(bundle=tampered, envelope=envelope)

    def test_tampered_report_lint_fails_old_envelope(self):
        original = self.bundle()
        envelope = seal_candidate_evidence_bundle(original, producer_secret=self.SECRET)
        tampered = replace(original, report_lint_state="REPORT_DRAFT")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_BUNDLE_DIGEST_MISMATCH"):
            self.admit(bundle=tampered, envelope=envelope)

    def test_tampered_program_admissibility_fails_old_envelope(self):
        original = self.bundle()
        envelope = seal_candidate_evidence_bundle(original, producer_secret=self.SECRET)
        tampered = replace(original, program_admissibility_state="UNKNOWN")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_BUNDLE_DIGEST_MISMATCH"):
            self.admit(bundle=tampered, envelope=envelope)

    def test_tampered_reproduction_fails_old_envelope(self):
        original = self.bundle()
        envelope = seal_candidate_evidence_bundle(original, producer_secret=self.SECRET)
        tampered_repro = replace(original.independent_reproduction, witness_digest="forged")
        tampered = replace(original, independent_reproduction=tampered_repro)
        with self.assertRaisesRegex(ValueError, "EVIDENCE_BUNDLE_DIGEST_MISMATCH"):
            self.admit(bundle=tampered, envelope=envelope)

    def test_freshly_sealed_external_effect_reproduction_still_fails_lower_gate(self):
        original = self.bundle()
        bad_repro = replace(original.independent_reproduction, external_effect=True)
        bad = replace(original, independent_reproduction=bad_repro)
        envelope = seal_candidate_evidence_bundle(bad, producer_secret=self.SECRET)
        with self.assertRaisesRegex(ValueError, "REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN"):
            self.admit(bundle=bad, envelope=envelope)

    def test_freshly_sealed_public_known_root_still_blocks_candidate(self):
        original = replace(self.bundle(), duplicate_pressure_state="PUBLICLY_KNOWN_ROOT_CAUSE")
        envelope = seal_candidate_evidence_bundle(original, producer_secret=self.SECRET)
        receipt = self.admit(bundle=original, envelope=envelope)
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertEqual(receipt.status, "BOUNTY_CANDIDATE_BLOCKED")

    def test_envelope_producer_ref_substitution_fails(self):
        bundle = self.bundle()
        envelope = seal_candidate_evidence_bundle(bundle, producer_secret=self.SECRET)
        forged = replace(envelope, producer_ref="producer://other")
        with self.assertRaisesRegex(ValueError, "ENVELOPE_PRODUCER_REF_MISMATCH"):
            self.admit(bundle=bundle, envelope=forged)

    def test_envelope_generation_substitution_fails(self):
        bundle = self.bundle()
        envelope = seal_candidate_evidence_bundle(bundle, producer_secret=self.SECRET)
        forged = replace(envelope, producer_generation="producer-gen-other")
        with self.assertRaisesRegex(ValueError, "ENVELOPE_PRODUCER_GENERATION_MISMATCH"):
            self.admit(bundle=bundle, envelope=forged)

    def test_receipt_is_deterministic(self):
        self.assertEqual(self.admit().receipt_digest, self.admit().receipt_digest)


if __name__ == "__main__":
    unittest.main()

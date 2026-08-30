from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
    admit_cash_bounty_candidate_for_human_review,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1


class BugHoundCashCandidateAdmissionTests(unittest.TestCase):
    def mission(self) -> BugHoundCashMissionInputV1:
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

    def candidate(self) -> BountyCandidateEvidenceV1:
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

    def repro(self) -> IndependentBountyReproductionReceiptV1:
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

    def admit(self, **overrides):
        repro = overrides.pop("independent_reproduction", self.repro())
        kwargs = dict(
            mission_input=self.mission(),
            candidate=self.candidate(),
            independent_reproduction=repro,
            expected_independent_reproduction_digest=repro.receipt_digest,
            expected_reproducer_ref="reproducer://independent-1",
            expected_reproducer_generation="repro-gen-1",
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-check-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-admission-1",
        )
        kwargs.update(overrides)
        return admit_cash_bounty_candidate_for_human_review(**kwargs)

    def test_exact_real_bounty_evidence_reaches_human_review_only(self) -> None:
        receipt = self.admit()
        self.assertEqual(receipt.status, "READY_FOR_HUMAN_SUBMISSION_REVIEW")
        self.assertTrue(receipt.ready_for_human_submission_review)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.credential_use_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.claim_or_payment_authorized)
        self.assertFalse(receipt.external_effect)

    def test_api_accepts_no_benchmark_score_or_adjudication(self) -> None:
        names = set(inspect.signature(admit_cash_bounty_candidate_for_human_review).parameters)
        self.assertNotIn("benchmark_score", names)
        self.assertNotIn("seeded_true_positive", names)
        self.assertNotIn("adjudication", names)
        self.assertNotIn("oracle", names)

    def test_internal_profile_cannot_enter_candidate_admission(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_NON_CASH_PROFILE_REJECTED"):
            self.admit(mission_input=replace(self.mission(), profile_id="BUGHOUND_AURAOS_INTERNAL"))

    def test_candidate_target_generation_must_match_cash_mission(self) -> None:
        with self.assertRaisesRegex(ValueError, "BOUNTY_CANDIDATE_GENERATION_MISMATCH"):
            self.admit(candidate=replace(self.candidate(), target_generation="old"))

    def test_discovery_must_be_reproduced_before_independent_repro_credit(self) -> None:
        with self.assertRaisesRegex(ValueError, "BOUNTY_DISCOVERY_REPRODUCTION_REQUIRED"):
            self.admit(candidate=replace(self.candidate(), discovery_reproduction_state="STATIC_ONLY"))

    def test_independent_reproducer_identity_is_consumer_bound(self) -> None:
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCER_REF_MISMATCH"):
            self.admit(expected_reproducer_ref="reproducer://different")

    def test_independent_reproducer_generation_is_consumer_bound(self) -> None:
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCER_GENERATION_MISMATCH"):
            self.admit(expected_reproducer_generation="repro-gen-2")

    def test_reproduction_digest_must_match_independent_expectation(self) -> None:
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCTION_EXPECTATION_MISMATCH"):
            self.admit(expected_independent_reproduction_digest="forged")

    def test_reproduction_scope_must_match_current_program_scope(self) -> None:
        bad = replace(self.repro(), scope_rules_digest="scope-old")
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCTION_SCOPE_MISMATCH"):
            self.admit(
                independent_reproduction=bad,
                expected_independent_reproduction_digest=bad.receipt_digest,
            )

    def test_reproduction_currentness_must_match_current_source(self) -> None:
        bad = replace(self.repro(), source_currentness_ref="source-old")
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCTION_CURRENTNESS_MISMATCH"):
            self.admit(
                independent_reproduction=bad,
                expected_independent_reproduction_digest=bad.receipt_digest,
            )

    def test_reproduction_external_effect_is_rejected(self) -> None:
        bad = replace(self.repro(), external_effect=True)
        with self.assertRaisesRegex(ValueError, "BOUNTY_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN"):
            self.admit(
                independent_reproduction=bad,
                expected_independent_reproduction_digest=bad.receipt_digest,
            )

    def test_publicly_known_root_cause_blocks_submission_review(self) -> None:
        receipt = self.admit(duplicate_pressure_state="PUBLICLY_KNOWN_ROOT_CAUSE")
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertIn("PUBLIC_ROOT_CAUSE_ALREADY_KNOWN", receipt.blockers)

    def test_high_duplicate_pressure_requires_manual_duplicate_review(self) -> None:
        receipt = self.admit(duplicate_pressure_state="HIGH_DUPLICATE_PRESSURE")
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertIn("MANUAL_DUPLICATE_REVIEW_REQUIRED", receipt.blockers)

    def test_unknown_duplicate_pressure_does_not_fabricate_novelty(self) -> None:
        receipt = self.admit(duplicate_pressure_state="UNKNOWN")
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertIn("DUPLICATE_PRESSURE_UNRESOLVED", receipt.blockers)

    def test_report_lint_is_required(self) -> None:
        receipt = self.admit(report_lint_state="REPORT_DRAFT")
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertIn("REPORT_LINT_REQUIRED", receipt.blockers)

    def test_current_program_admissibility_is_required(self) -> None:
        receipt = self.admit(program_admissibility_state="UNKNOWN")
        self.assertFalse(receipt.ready_for_human_submission_review)
        self.assertIn("PROGRAM_ADMISSIBILITY_REQUIRED", receipt.blockers)

    def test_medium_duplicate_pressure_can_remain_reportable_without_private_claim(self) -> None:
        receipt = self.admit(duplicate_pressure_state="MEDIUM_DUPLICATE_PRESSURE")
        self.assertTrue(receipt.ready_for_human_submission_review)

    def test_candidate_receipt_is_deterministic(self) -> None:
        self.assertEqual(self.admit().receipt_digest, self.admit().receipt_digest)


if __name__ == "__main__":
    unittest.main()

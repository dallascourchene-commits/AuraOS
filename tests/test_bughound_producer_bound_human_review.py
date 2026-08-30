from __future__ import annotations

from dataclasses import replace
import inspect
import unittest
from unittest.mock import patch

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1, admit_cash_bounty_mission
from tools.bughound.candidate_evidence_registry import CandidateEvidenceProducerRecordV1
from tools.bughound.cash_scheduler import BugHoundCashSchedulerDecisionV1
from tools.bughound.producer_bound_candidate_admission import (
    BugHoundCashCandidateEvidenceBundleV1,
    _compose_registered_candidate_receipt,
    validate_candidate_evidence_bundle,
)
from tools.bughound.producer_bound_human_review import (
    _compose_from_producer_bound_candidate,
    compile_producer_bound_cash_human_review_packet,
    producer_bound_human_review_parameter_names,
)


class ProducerBoundHumanReviewTests(unittest.TestCase):
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

    def producer_candidate(self, bundle=None):
        bundle = bundle or self.bundle()
        return _compose_registered_candidate_receipt(
            validation=validate_candidate_evidence_bundle(
                mission_input=self.mission(), evidence_bundle=bundle
            ),
            evidence_bundle=bundle,
            record=self.record(bundle),
        )

    def scheduler(self, **changes):
        mission = admit_cash_bounty_mission(self.mission())
        values = dict(
            work_item_id="work-1",
            next_action="NO_LOCAL_RESIDUAL_HUMAN_GATE_ONLY",
            selected_gap=None,
            stop_reason="EVIDENCE_GAPS_CLOSED",
            unresolved_gaps=(),
            mission_receipt_digest=mission.receipt_digest,
        )
        values.update(changes)
        return BugHoundCashSchedulerDecisionV1(**values)

    def test_public_human_review_abi_forces_raw_inputs_not_serialized_trust(self):
        self.assertEqual(
            {"mission_input", "evidence_bundle", "scheduler_decision"},
            set(producer_bound_human_review_parameter_names()),
        )
        for forbidden in (
            "candidate_admission",
            "producer_bound_candidate",
            "producer_receipt",
            "registry",
            "registry_record",
            "trusted",
            "producer_trust_proven",
            "producer_secret",
            "expected_producer_ref",
            "expected_producer_generation",
        ):
            self.assertNotIn(forbidden, producer_bound_human_review_parameter_names())

    def test_public_path_fails_closed_while_production_producer_registry_is_empty(self):
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_PRODUCER_TRUST_UNPROVEN"):
            compile_producer_bound_cash_human_review_packet(
                mission_input=self.mission(),
                evidence_bundle=self.bundle(),
                scheduler_decision=self.scheduler(),
            )

    def test_public_path_invokes_canonical_producer_admission_exactly_once(self):
        bundle = self.bundle()
        candidate = self.producer_candidate(bundle)
        with patch(
            "tools.bughound.producer_bound_human_review.admit_producer_bound_cash_bounty_candidate_for_human_review",
            return_value=candidate,
        ) as mocked:
            packet = compile_producer_bound_cash_human_review_packet(
                mission_input=self.mission(),
                evidence_bundle=bundle,
                scheduler_decision=self.scheduler(),
            )
        mocked.assert_called_once_with(mission_input=self.mission(), evidence_bundle=bundle)
        self.assertTrue(packet.candidate_producer_trust_proven)
        self.assertTrue(packet.ready_for_human_review)
        self.assertFalse(packet.human_authorization_verified)
        self.assertFalse(packet.live_target_testing_authorized)
        self.assertFalse(packet.credential_use_authorized)
        self.assertFalse(packet.submission_authorized)
        self.assertFalse(packet.claim_or_payment_authorized)
        self.assertFalse(packet.external_effect)

    def test_private_future_registered_producer_path_builds_digest_bound_packet(self):
        bundle = self.bundle()
        packet = _compose_from_producer_bound_candidate(
            mission_input=self.mission(),
            evidence_bundle=bundle,
            producer_bound_candidate=self.producer_candidate(bundle),
            scheduler_decision=self.scheduler(),
        )
        self.assertEqual(bundle.bundle_digest, packet.evidence_bundle_digest)
        self.assertEqual(self.repro().receipt_digest, packet.independent_reproduction_digest)
        self.assertEqual("READY_FOR_HUMAN_REVIEW_DECISION", packet.status)
        self.assertEqual(packet.packet_digest, packet.packet_digest)

    def test_false_producer_trust_cannot_be_reduced_to_human_review_packet(self):
        candidate = replace(
            self.producer_candidate(),
            candidate_producer_trust_proven=False,
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_HUMAN_REVIEW_PRODUCER_TRUST_REQUIRED"):
            _compose_from_producer_bound_candidate(
                mission_input=self.mission(),
                evidence_bundle=self.bundle(),
                producer_bound_candidate=candidate,
                scheduler_decision=self.scheduler(),
            )

    def test_scheduler_must_be_at_human_gate(self):
        with self.assertRaisesRegex(ValueError, "BUGHOUND_HUMAN_REVIEW_SCHEDULER_NOT_AT_HUMAN_GATE"):
            _compose_from_producer_bound_candidate(
                mission_input=self.mission(),
                evidence_bundle=self.bundle(),
                producer_bound_candidate=self.producer_candidate(),
                scheduler_decision=self.scheduler(
                    next_action="BUILD_CAUSAL_MODEL",
                    selected_gap="G_CAUSAL_MODEL",
                    stop_reason=None,
                    unresolved_gaps=("G_CAUSAL_MODEL",),
                ),
            )

    def test_candidate_effect_authority_widening_fails(self):
        candidate = replace(self.producer_candidate(), submission_authorized=True)
        with self.assertRaisesRegex(ValueError, "SUBMISSION_AUTHORIZED_MUST_BE_FALSE"):
            _compose_from_producer_bound_candidate(
                mission_input=self.mission(),
                evidence_bundle=self.bundle(),
                producer_bound_candidate=candidate,
                scheduler_decision=self.scheduler(),
            )

    def test_scheduler_effect_authority_widening_fails(self):
        with self.assertRaisesRegex(ValueError, "EXTERNAL_EFFECT_MUST_BE_FALSE"):
            _compose_from_producer_bound_candidate(
                mission_input=self.mission(),
                evidence_bundle=self.bundle(),
                producer_bound_candidate=self.producer_candidate(),
                scheduler_decision=self.scheduler(external_effect=True),
            )

    def test_evidence_bundle_substitution_fails(self):
        bundle = self.bundle()
        altered = replace(bundle, report_digest="report-2")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_HUMAN_REVIEW_EVIDENCE_BUNDLE_MISMATCH"):
            _compose_from_producer_bound_candidate(
                mission_input=self.mission(),
                evidence_bundle=altered,
                producer_bound_candidate=self.producer_candidate(bundle),
                scheduler_decision=self.scheduler(),
            )

    def test_serialized_candidate_parameter_cannot_enter_public_boundary(self):
        with self.assertRaises(TypeError):
            compile_producer_bound_cash_human_review_packet(
                mission_input=self.mission(),
                evidence_bundle=self.bundle(),
                scheduler_decision=self.scheduler(),
                candidate_admission=self.producer_candidate(),
            )


if __name__ == "__main__":
    unittest.main()

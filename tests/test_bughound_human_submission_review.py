from __future__ import annotations

from dataclasses import fields, replace
import inspect
import unittest

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
    admit_cash_bounty_candidate_for_human_review,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.cash_scheduler import CashBountyWorkStateV1, schedule_next_cash_bounty_step
from tools.bughound.human_submission_review import (
    BugHoundCashHumanReviewPacketV1,
    UPSTREAM_TRUST_BLOCKER,
    compile_cash_bounty_human_review_packet,
)


class BugHoundHumanSubmissionReviewTests(unittest.TestCase):
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

    def candidate_admission(self):
        candidate = BountyCandidateEvidenceV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            security_invariant_digest="invariant-1",
            causal_cone_digest="cone-1",
            discovery_receipt_digest="discovery-1",
            discovery_reproduction_state="REPRODUCED_CURRENT",
            claimed_consequence_band="CONSERVATIVE_MEDIUM",
        )
        repro = IndependentBountyReproductionReceiptV1(
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
        return admit_cash_bounty_candidate_for_human_review(
            mission_input=self.mission(),
            candidate=candidate,
            independent_reproduction=repro,
            expected_independent_reproduction_digest=repro.receipt_digest,
            expected_reproducer_ref=repro.reproducer_ref,
            expected_reproducer_generation=repro.reproducer_generation,
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-current-1",
        )

    def scheduler(self, gaps=("G_EXTERNAL_ACCEPTANCE",)):
        return schedule_next_cash_bounty_step(
            mission_input=self.mission(),
            work_state=CashBountyWorkStateV1(
                work_item_id="cash-work-1",
                unresolved_gaps=tuple(gaps),
                duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
                probe_budget_minutes=60,
                active_probe_minutes=10,
                survivor_state="REPRODUCED_SURVIVOR",
                source_generation="repo-gen-1",
                currentness_ref="source-v1",
            ),
        )

    def compile(self, candidate=None, scheduler=None, mission=None):
        return compile_cash_bounty_human_review_packet(
            mission_input=mission or self.mission(),
            candidate_admission=candidate or self.candidate_admission(),
            scheduler_decision=scheduler or self.scheduler(),
        )

    def test_current_lower_plane_candidate_compiles_but_stays_producer_trust_blocked(self):
        packet = self.compile()
        self.assertEqual(packet.status, "HUMAN_REVIEW_PACKET_EVIDENCE_TRUST_REQUIRED")
        self.assertEqual(packet.candidate_id, "candidate-1")
        self.assertEqual(packet.blockers, (UPSTREAM_TRUST_BLOCKER,))
        self.assertFalse(packet.candidate_producer_trust_proven)
        self.assertFalse(packet.human_authorization_verified)
        self.assertFalse(packet.ready_for_human_review)
        self.assertTrue(packet.packet_digest)
        self.assertFalse(packet.live_target_testing_authorized)
        self.assertFalse(packet.credential_use_authorized)
        self.assertFalse(packet.submission_authorized)
        self.assertFalse(packet.claim_or_payment_authorized)
        self.assertFalse(packet.external_effect)

    def test_closed_local_gaps_do_not_erase_producer_trust_blocker(self):
        packet = self.compile(scheduler=self.scheduler(()))
        self.assertEqual(packet.status, "HUMAN_REVIEW_PACKET_EVIDENCE_TRUST_REQUIRED")
        self.assertIn(UPSTREAM_TRUST_BLOCKER, packet.blockers)
        self.assertFalse(packet.ready_for_human_review)

    def test_non_human_scheduler_action_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "BUGHOUND_REVIEW_SCHEDULER_NOT_AT_HUMAN_GATE"):
            self.compile(scheduler=self.scheduler(("G_REPRO",)))

    def test_blocked_candidate_is_rejected(self):
        blocked = replace(
            self.candidate_admission(),
            status="BOUNTY_CANDIDATE_BLOCKED",
            blockers=("MANUAL_DUPLICATE_REVIEW_REQUIRED",),
            ready_for_human_submission_review=False,
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_CANDIDATE_NOT_READY_FOR_LOWER_PLANE_PACKET"):
            self.compile(candidate=blocked)

    def test_candidate_authority_widening_is_rejected(self):
        widened = replace(self.candidate_admission(), submission_authorized=True)
        with self.assertRaisesRegex(ValueError, "BUGHOUND_CANDIDATE_SUBMISSION_AUTHORIZED_MUST_BE_FALSE"):
            self.compile(candidate=widened)

    def test_scheduler_authority_widening_is_rejected(self):
        widened = replace(self.scheduler(), external_effect=True)
        with self.assertRaisesRegex(ValueError, "BUGHOUND_SCHEDULER_EXTERNAL_EFFECT_MUST_BE_FALSE"):
            self.compile(scheduler=widened)

    def test_stale_mission_binding_is_rejected(self):
        stale = replace(self.mission(), target_generation="repo-gen-2")
        with self.assertRaises(ValueError):
            self.compile(mission=stale)

    def test_scheduler_mission_digest_is_consumer_bound(self):
        bad = replace(self.scheduler(), mission_receipt_digest="wrong")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_REVIEW_SCHEDULER_MISSION_MISMATCH"):
            self.compile(scheduler=bad)

    def test_packet_schema_has_no_payload_submission_channel_or_caller_trust_override(self):
        names = {f.name for f in fields(BugHoundCashHumanReviewPacketV1)}
        for forbidden in (
            "exploit_payload",
            "request_body",
            "live_target_action",
            "credential",
            "submission_endpoint",
            "submission_token",
        ):
            self.assertNotIn(forbidden, names)
        api_names = set(inspect.signature(compile_cash_bounty_human_review_packet).parameters)
        for forbidden in (
            "benchmark_score",
            "oracle",
            "producer_trust_proven",
            "trusted",
            "human_authorization_ref",
        ):
            self.assertNotIn(forbidden, api_names)

    def test_packet_digest_is_deterministic(self):
        self.assertEqual(self.compile().packet_digest, self.compile().packet_digest)


if __name__ == "__main__":
    unittest.main()

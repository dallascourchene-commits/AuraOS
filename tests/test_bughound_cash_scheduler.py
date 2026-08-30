from __future__ import annotations

from dataclasses import replace
import unittest

from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.cash_scheduler import CashBountyWorkStateV1, schedule_next_cash_bounty_step


class BugHoundCashSchedulerTests(unittest.TestCase):
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

    def state(self, gaps=("G_CAUSAL_MODEL",)):
        return CashBountyWorkStateV1(
            work_item_id="cash-work-1",
            unresolved_gaps=tuple(gaps),
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            probe_budget_minutes=60,
            active_probe_minutes=5,
            survivor_state="UNPROVEN",
            source_generation="repo-gen-1",
            currentness_ref="source-v1",
        )

    def test_routes_earliest_consequence_gap_only(self):
        d = schedule_next_cash_bounty_step(
            mission_input=self.mission(),
            work_state=self.state(("G_REPRO", "G_CAUSAL_MODEL", "G_DUPLICATE")),
        )
        self.assertEqual(d.selected_gap, "G_CAUSAL_MODEL")
        self.assertEqual(d.next_action, "BUILD_CAUSAL_MODEL")

    def test_gap_route_table(self):
        expected = {
            "G_CAUSAL_MODEL": "BUILD_CAUSAL_MODEL",
            "G_REACHABILITY": "PROVE_REACHABILITY_LOCALLY",
            "G_CONTROL": "BUILD_NEGATIVE_CONTROL",
            "G_SINK": "PROVE_CONSEQUENCE_SINK_LOCALLY",
            "G_REPRO": "REPRODUCE_IN_CURRENT_AUTHORIZED_LOCAL_ENVIRONMENT",
            "G_INDEPENDENT_REPRO": "REQUEST_INDEPENDENT_REPRODUCTION_ARTIFACT",
            "G_DUPLICATE": "CHECK_PUBLIC_DUPLICATE_PRESSURE",
            "G_REPORT_QUALITY": "LINT_DISCLOSURE_SAFE_REPORT",
            "G_EXTERNAL_ACCEPTANCE": "PREPARE_HUMAN_SUBMISSION_REVIEW",
        }
        for gap, action in expected.items():
            with self.subTest(gap=gap):
                d = schedule_next_cash_bounty_step(
                    mission_input=self.mission(), work_state=self.state((gap,))
                )
                self.assertEqual(d.next_action, action)
                self.assertEqual(d.selected_gap, gap)
                self.assertFalse(d.external_effect)

    def test_budget_exhaustion_stops_before_more_work(self):
        d = schedule_next_cash_bounty_step(
            mission_input=self.mission(),
            work_state=replace(self.state(), active_probe_minutes=60),
        )
        self.assertEqual(d.next_action, "STOP_AND_COLLAPSE")
        self.assertEqual(d.stop_reason, "PROBE_BUDGET_EXHAUSTED")

    def test_public_known_root_cause_parks(self):
        d = schedule_next_cash_bounty_step(
            mission_input=self.mission(),
            work_state=replace(
                self.state(("G_DUPLICATE",)),
                duplicate_pressure_state="PUBLICLY_KNOWN_ROOT_CAUSE",
            ),
        )
        self.assertEqual(d.next_action, "PARK_AND_COLLAPSE_NEGATIVE_KNOWLEDGE")

    def test_high_duplicate_pressure_parks_weak_candidate(self):
        d = schedule_next_cash_bounty_step(
            mission_input=self.mission(),
            work_state=replace(
                self.state(("G_REPRO", "G_DUPLICATE")),
                duplicate_pressure_state="HIGH_DUPLICATE_PRESSURE",
                survivor_state="UNPROVEN",
            ),
        )
        self.assertEqual(d.next_action, "PARK_PENDING_DIFFERENTIATING_EVIDENCE")

    def test_high_duplicate_pressure_does_not_override_reproduced_survivor(self):
        d = schedule_next_cash_bounty_step(
            mission_input=self.mission(),
            work_state=replace(
                self.state(("G_DUPLICATE",)),
                duplicate_pressure_state="HIGH_DUPLICATE_PRESSURE",
                survivor_state="REPRODUCED_SURVIVOR",
            ),
        )
        self.assertEqual(d.next_action, "CHECK_PUBLIC_DUPLICATE_PRESSURE")

    def test_no_gaps_stops_at_human_gate(self):
        d = schedule_next_cash_bounty_step(
            mission_input=self.mission(), work_state=self.state(())
        )
        self.assertEqual(d.next_action, "NO_LOCAL_RESIDUAL_HUMAN_GATE_ONLY")
        self.assertEqual(d.stop_reason, "EVIDENCE_GAPS_CLOSED")
        self.assertFalse(d.submission_authorized)

    def test_non_cash_internal_profile_fails_at_scheduler_entry(self):
        with self.assertRaisesRegex(ValueError, "BUGHOUND_NON_CASH_PROFILE_REJECTED"):
            schedule_next_cash_bounty_step(
                mission_input=replace(self.mission(), profile_id="BUGHOUND_AURAOS_INTERNAL"),
                work_state=self.state(),
            )

    def test_stale_source_generation_fails(self):
        with self.assertRaisesRegex(ValueError, "BUGHOUND_WORK_SOURCE_GENERATION_MISMATCH"):
            schedule_next_cash_bounty_step(
                mission_input=self.mission(),
                work_state=replace(self.state(), source_generation="old"),
            )

    def test_stale_currentness_ref_fails(self):
        with self.assertRaisesRegex(ValueError, "BUGHOUND_WORK_CURRENTNESS_MISMATCH"):
            schedule_next_cash_bounty_step(
                mission_input=self.mission(),
                work_state=replace(self.state(), currentness_ref="old"),
            )

    def test_unknown_gap_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "BUGHOUND_UNKNOWN_EVIDENCE_GAP"):
            schedule_next_cash_bounty_step(
                mission_input=self.mission(), work_state=self.state(("G_MAGIC",))
            )

    def test_duplicate_gap_identity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "BUGHOUND_DUPLICATE_EVIDENCE_GAP"):
            schedule_next_cash_bounty_step(
                mission_input=self.mission(),
                work_state=self.state(("G_REPRO", "G_REPRO")),
            )

    def test_scheduler_never_grants_effect_authority(self):
        d = schedule_next_cash_bounty_step(
            mission_input=self.mission(), work_state=self.state(("G_EXTERNAL_ACCEPTANCE",))
        )
        self.assertEqual(d.next_action, "PREPARE_HUMAN_SUBMISSION_REVIEW")
        self.assertFalse(d.live_target_testing_authorized)
        self.assertFalse(d.credential_use_authorized)
        self.assertFalse(d.submission_authorized)
        self.assertFalse(d.claim_or_payment_authorized)
        self.assertFalse(d.external_effect)

    def test_decision_digest_is_deterministic(self):
        a = schedule_next_cash_bounty_step(mission_input=self.mission(), work_state=self.state())
        b = schedule_next_cash_bounty_step(mission_input=self.mission(), work_state=self.state())
        self.assertEqual(a.decision_digest, b.decision_digest)


if __name__ == "__main__":
    unittest.main()

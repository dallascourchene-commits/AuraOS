from __future__ import annotations

from dataclasses import replace
import unittest

from tools.bughound.bounty_mission import (
    BugHoundCashMissionInputV1,
    admit_cash_bounty_mission,
)
from tools.bughound.target_profile import AURAOS_HARDENING_PROFILE_ID


class BugHoundCashMissionTests(unittest.TestCase):
    def clean(self) -> BugHoundCashMissionInputV1:
        return BugHoundCashMissionInputV1(
            profile_id="BUGHOUND_CASH_BOUNTY_V1",
            program_ref="program://authorized-cash-bounty",
            target_ref="target://example/in-scope",
            target_generation="gen-20260830",
            program_state="ACTIVE",
            cash_reward_state="VERIFIED_CURRENT_CASH_REWARD",
            reward_currency="USD",
            reward_floor_minor=10000,
            reward_ceiling_minor=50000,
            payout_rules_digest="payout-digest-v1",
            scope_state="CURRENT_SCOPE_BOUND",
            scope_rules_digest="scope-digest-v1",
            source_state="CURRENT_SOURCE_BOUND",
            source_currentness_ref="source-currentness-v1",
            testing_ceiling="PUBLIC_SOURCE_AND_LOCAL_AUTHORIZED_ONLY",
            duplicate_pressure_state="UNKNOWN",
        )

    def test_current_cash_bounty_research_is_admitted_pre_effect(self) -> None:
        receipt = admit_cash_bounty_mission(self.clean())
        self.assertTrue(receipt.cash_bounty_mission_admitted)
        self.assertTrue(receipt.payout_current)
        self.assertTrue(receipt.scope_current)
        self.assertTrue(receipt.source_current)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.credential_use_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.claim_or_payment_authorized)
        self.assertFalse(receipt.external_effect)

    def test_auraos_bughound_profile_is_rejected_only_by_cash_compiler(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "BUGHOUND_CASH_COMPILER_PROFILE_MISMATCH"
        ):
            admit_cash_bounty_mission(
                replace(self.clean(), profile_id=AURAOS_HARDENING_PROFILE_ID)
            )

    def test_noncash_vdp_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_CASH_REWARD_NOT_CURRENT"):
            admit_cash_bounty_mission(replace(self.clean(), cash_reward_state="NO_CASH_REWARD"))

    def test_archived_or_historical_reward_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_PROGRAM_NOT_ACTIVE"):
            admit_cash_bounty_mission(replace(self.clean(), program_state="ARCHIVED"))

    def test_unknown_or_stale_scope_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_SCOPE_NOT_CURRENT"):
            admit_cash_bounty_mission(replace(self.clean(), scope_state="UNKNOWN"))

    def test_stale_source_currentness_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_SOURCE_NOT_CURRENT"):
            admit_cash_bounty_mission(replace(self.clean(), source_state="STALE"))

    def test_missing_scope_digest_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "SCOPE_RULES_DIGEST_REQUIRED"):
            admit_cash_bounty_mission(replace(self.clean(), scope_rules_digest=""))

    def test_reward_range_must_be_coherent(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_REWARD_RANGE_INVALID"):
            admit_cash_bounty_mission(
                replace(self.clean(), reward_floor_minor=60000, reward_ceiling_minor=50000)
            )

    def test_non_cash_currency_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_CASH_CURRENCY_REQUIRED"):
            admit_cash_bounty_mission(replace(self.clean(), reward_currency="POINTS"))

    def test_receipt_digest_is_deterministic(self) -> None:
        a = admit_cash_bounty_mission(self.clean())
        b = admit_cash_bounty_mission(self.clean())
        self.assertEqual(a.receipt_digest, b.receipt_digest)


if __name__ == "__main__":
    unittest.main()

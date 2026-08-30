from __future__ import annotations

from dataclasses import replace
import unittest

from tools.bughound.target_profile import (
    AURAOS_HARDENING_PROFILE_ID,
    CASH_BOUNTY_PROFILE_ID,
    ENGINE_ID,
    BugHoundTargetProfileV1,
    bind_target_profile,
)


class BugHoundTargetProfileTests(unittest.TestCase):
    def cash(self) -> BugHoundTargetProfileV1:
        return BugHoundTargetProfileV1(
            profile_id=CASH_BOUNTY_PROFILE_ID,
            profile_kind="EXTERNAL_CASH_BOUNTY",
            target_ref="program://cash/target",
            target_generation="cash-gen-1",
        )

    def auraos_historical_marker(self) -> BugHoundTargetProfileV1:
        return BugHoundTargetProfileV1(
            profile_id=AURAOS_HARDENING_PROFILE_ID,
            profile_kind="INTERNAL_AURAOS_HARDENING",
            target_ref="repo://AuraOS",
            target_generation="auraos-head-1",
        )

    def test_cash_profile_is_the_only_registered_bughound_profile(self) -> None:
        cash = bind_target_profile(self.cash())
        self.assertEqual(cash.engine_id, ENGINE_ID)
        self.assertTrue(cash.cash_mission_eligible)
        self.assertFalse(cash.auraos_hardening)
        self.assertFalse(cash.cross_profile_authority_credit)
        self.assertFalse(cash.payout_authority)
        self.assertFalse(cash.live_target_testing_authority)
        self.assertFalse(cash.submission_authority)
        self.assertFalse(cash.external_effect)

    def test_auraos_hardening_historical_marker_is_not_registered(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_PROFILE_NOT_REGISTERED"):
            bind_target_profile(self.auraos_historical_marker())

    def test_cash_profile_kind_cannot_be_cross_cast(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_PROFILE_KIND_MISMATCH"):
            bind_target_profile(
                replace(self.cash(), profile_kind="INTERNAL_AURAOS_HARDENING")
            )

    def test_unknown_profile_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_PROFILE_NOT_REGISTERED"):
            bind_target_profile(
                replace(self.cash(), profile_id="BUGHOUND_UNKNOWN_PROFILE")
            )

    def test_profile_receipt_digest_is_deterministic(self) -> None:
        self.assertEqual(
            bind_target_profile(self.cash()).receipt_digest,
            bind_target_profile(self.cash()).receipt_digest,
        )


if __name__ == "__main__":
    unittest.main()

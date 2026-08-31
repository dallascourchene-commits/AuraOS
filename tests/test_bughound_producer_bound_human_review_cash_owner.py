from __future__ import annotations

from dataclasses import replace
import unittest

from test_bughound_producer_bound_human_review import ProducerBoundHumanReviewTests
from tools.bughound.producer_bound_human_review import (
    compile_producer_bound_cash_human_review_packet,
)


class ProducerBoundHumanReviewCashOwnerTests(unittest.TestCase):
    def test_historical_auraos_profile_cannot_cross_human_review_gate(self):
        fixture = ProducerBoundHumanReviewTests()
        noncash_mission = replace(
            fixture.mission(),
            profile_id="BUGHOUND_AURAOS_HARDENING_V1",
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_NON_CASH_PROFILE_REJECTED"):
            compile_producer_bound_cash_human_review_packet(
                mission_input=noncash_mission,
                evidence_bundle=fixture.bundle(),
                scheduler_decision=fixture.scheduler(),
            )


if __name__ == "__main__":
    unittest.main()

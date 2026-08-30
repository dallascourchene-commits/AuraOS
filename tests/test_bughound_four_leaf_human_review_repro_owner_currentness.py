from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

import tools.bughound.four_leaf_human_review as human_review
import tools.bughound.registered_reproduction_gate as reproduction_owner
from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1


class FourLeafHumanReviewReproductionOwnerCurrentnessTests(unittest.TestCase):
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
            reproducer_generation="reproducer-gen-1",
            result="REPRODUCED_CURRENT",
            witness_digest="witness-1",
            environment_digest="environment-1",
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-v1",
        )

    def record(
        self,
        *,
        observer_ref: str = "registry://observer/independent",
        registry_receipt_ref: str = "registry://receipt/1",
    ):
        repro = self.repro()
        return reproduction_owner.BugHoundIndependentReproductionRegistryRecordV1(
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
            registry_receipt_ref=registry_receipt_ref,
            registry_observer_ref=observer_ref,
            registry_observer_generation="observer-gen-1",
            registry_current=True,
            independently_observed=True,
        )

    def test_human_review_module_consumes_current_reproduction_owner_functions(self):
        self.assertIs(
            human_review.admit_with_registered_independent_reproduction,
            reproduction_owner.admit_with_registered_independent_reproduction,
        )
        self.assertIs(
            human_review.independent_reproduction_registry_receipt,
            reproduction_owner.independent_reproduction_registry_receipt,
        )
        self.assertTrue(hasattr(reproduction_owner, "_validate_registry_record_shape"))
        self.assertTrue(hasattr(reproduction_owner, "_registry_receipt_from_records"))
        self.assertEqual(
            "BUGHOUND_INDEPENDENT_REPRODUCTION_REGISTRY_HOLD_V3",
            reproduction_owner.REGISTRY_GENERATION,
        )

    def test_same_principal_observer_cannot_enter_human_review_owner_registry(self):
        invalid = self.record(observer_ref="reproducer://independent-1")
        with patch.object(reproduction_owner, "_CANONICAL_REPRODUCTION_RECORDS", (invalid,)):
            with self.assertRaisesRegex(
                ValueError,
                "INDEPENDENT_REPRODUCTION_OBSERVER_PRODUCER_SEPARATION_REQUIRED",
            ):
                human_review.independent_reproduction_registry_receipt()

    def test_distinct_observer_receipt_is_v3_and_content_bound_without_authority(self):
        valid = self.record()
        with patch.object(reproduction_owner, "_CANONICAL_REPRODUCTION_RECORDS", (valid,)):
            receipt = human_review.independent_reproduction_registry_receipt()
        self.assertEqual("BugHoundIndependentReproductionRegistryReceiptV3", receipt.schema)
        self.assertEqual(reproduction_owner.REGISTRY_GENERATION, receipt.registry_generation)
        self.assertEqual((valid.record_digest,), receipt.record_digests)
        self.assertTrue(receipt.registry_digest)
        self.assertEqual(1, receipt.active_record_count)
        self.assertFalse(receipt.authority)
        self.assertFalse(receipt.external_effect)

    def test_multiple_valid_current_reproduction_records_are_ambiguous(self):
        repro = self.repro()
        a = self.record()
        b = replace(a, registry_receipt_ref="registry://receipt/2")
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_AMBIGUOUS"):
            reproduction_owner._resolve_from_records(
                records=(a, b),
                reproduction=repro,
                candidate=self.candidate(),
                mission_input=self.mission(),
            )


if __name__ == "__main__":
    unittest.main()

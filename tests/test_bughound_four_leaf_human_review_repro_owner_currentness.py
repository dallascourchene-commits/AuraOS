from __future__ import annotations

import unittest
from unittest.mock import patch

import tools.bughound.four_leaf_human_review as human_review
import tools.bughound.registered_reproduction_gate as reproduction_owner


class FourLeafHumanReviewReproductionOwnerCurrentnessTests(unittest.TestCase):
    def record(self, *, observer_ref: str = "registry://observer/independent"):
        return reproduction_owner.BugHoundIndependentReproductionRegistryRecordV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            reproduction_receipt_digest="reproduction-digest-1",
            reproducer_ref="reproducer://independent-1",
            reproducer_generation="reproducer-gen-1",
            witness_digest="witness-1",
            environment_digest="environment-1",
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-v1",
            registry_receipt_ref="registry://receipt/1",
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

    def test_same_principal_observer_cannot_enter_human_review_owner_registry(self):
        invalid = self.record(observer_ref="reproducer://independent-1")
        with patch.object(
            reproduction_owner,
            "_CANONICAL_REPRODUCTION_RECORDS",
            (invalid,),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "INDEPENDENT_REPRODUCTION_OBSERVER_PRODUCER_SEPARATION_REQUIRED",
            ):
                human_review.independent_reproduction_registry_receipt()

    def test_distinct_observer_can_be_counted_but_grants_no_authority(self):
        valid = self.record()
        with patch.object(
            reproduction_owner,
            "_CANONICAL_REPRODUCTION_RECORDS",
            (valid,),
        ):
            receipt = human_review.independent_reproduction_registry_receipt()
        self.assertEqual(1, receipt.active_record_count)
        self.assertFalse(receipt.authority)
        self.assertFalse(receipt.external_effect)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from copy import deepcopy
import unittest

from tools import aura_pre_attempt_lifecycle_lineage as q21
from tools import aura_q22_materialization_support_lifecycle as public_q22
from tools import aura_materialization_support_lifecycle_lineage as inner_q22


class Q22ExactLineageGuardTests(unittest.TestCase):
    def bind(self, lineage=None):
        return public_q22.bind_materialization_support_to_exact_lineage(
            support=inner_q22.example_support(),
            lineage=lineage or public_q22.example_lineage(),
        )

    def test_canonical_q21_lineage_binds(self):
        result = self.bind()
        self.assertTrue(result.bounded_support_associated_with_lineage)
        self.assertFalse(result.support_fresh_at_pre_attempt_proven)
        self.assertFalse(result.support_fresh_at_effect_boundary_proven)
        self.assertFalse(result.execution_authorized)

    def test_self_resealed_arbitrary_lineage_digest_is_rejected(self):
        forged = public_q22.example_lineage()
        forged["lineage_digest"] = "f" * 64
        body = dict(forged)
        body.pop("receipt_digest", None)
        typed = q21.PreAttemptLifecycleLineageReceipt(**body)
        forged["receipt_digest"] = typed.receipt_digest
        with self.assertRaisesRegex(ValueError, "Q22_LINEAGE_DIGEST_MISMATCH"):
            self.bind(lineage=forged)

    def test_noncanonical_k27_extra_field_is_rejected_not_identity_bearing(self):
        forged = public_q22.example_lineage()
        forged["k27_coordinate"] = [5, 3, 9]
        with self.assertRaisesRegex(ValueError, "Q22_LINEAGE_NONCANONICAL_FIELDS"):
            self.bind(lineage=forged)

    def test_noncanonical_cache_extra_field_is_rejected(self):
        forged = public_q22.example_lineage()
        forged["cache_key"] = "retrieval-only"
        with self.assertRaisesRegex(ValueError, "Q22_LINEAGE_NONCANONICAL_FIELDS"):
            self.bind(lineage=forged)

    def test_q21_identity_field_change_requires_matching_lineage_recomputation(self):
        forged = deepcopy(public_q22.example_lineage())
        forged["owner_state_epoch"] = "epoch-forged-without-lineage-recompute"
        body = dict(forged)
        body.pop("receipt_digest", None)
        typed = q21.PreAttemptLifecycleLineageReceipt(**body)
        forged["receipt_digest"] = typed.receipt_digest
        with self.assertRaisesRegex(ValueError, "Q22_LINEAGE_DIGEST_MISMATCH"):
            self.bind(lineage=forged)

    def test_public_example_reconstructs_exact_q21_lineage_algebra(self):
        lineage = public_q22.example_lineage()
        typed = public_q22._canonical_q21_receipt(lineage)
        self.assertEqual(typed.lineage_digest, lineage["lineage_digest"])
        self.assertEqual(typed.receipt_digest, lineage["receipt_digest"])


if __name__ == "__main__":
    unittest.main()

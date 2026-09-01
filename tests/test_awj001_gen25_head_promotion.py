import dataclasses
import unittest

from tools.awj001 import awj001_gen25_head_promotion as p


class AWJ001Gen25PromotionTests(unittest.TestCase):
    def test_positive_emits_typed_head_promotion(self):
        r = p.assess_and_promote()
        self.assertIsInstance(r, p.HeadPromotionReceipt)
        self.assertEqual(r.event_type, p.PROMOTED)
        self.assertEqual(r.generation, 25)
        self.assertEqual(r.predecessor_head, "3aeb8f3db921201f")
        self.assertEqual(len(r.head), 16)
        self.assertEqual(r.join_address, f"awj://AWJ-001?g=25&head={r.head}")
        self.assertTrue(r.current_at_promotion_cut)
        self.assertFalse(r.current_at_future_use_proven)
        r.validate_claim_ceiling()

    def test_deterministic_receipt(self):
        a = p.assess_and_promote()
        b = p.assess_and_promote()
        self.assertEqual(a.head, b.head)
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(a.currentness_observation_digest, b.currentness_observation_digest)

    def test_stale_predecessor_holds(self):
        cut = dataclasses.replace(p.PromotionCut(), authoritative_head="deadbeefdeadbeef")
        self.assertEqual(p.assess_and_promote(cut=cut), p.HOLD_PREDECESSOR)

    def test_newer_typed_head_prevents_fork(self):
        cut = dataclasses.replace(p.PromotionCut(), newer_typed_head_observed=True)
        self.assertEqual(p.assess_and_promote(cut=cut), p.HOLD_CURRENTNESS)

    def test_contradictory_owner_disposition_holds(self):
        cut = dataclasses.replace(p.PromotionCut(), contradictory_later_owner_disposition_observed=True)
        self.assertEqual(p.assess_and_promote(cut=cut), p.HOLD_CURRENTNESS)

    def test_revoked_promotion_authority_holds(self):
        self.assertEqual(p.assess_and_promote(promotion_authorized=False), p.HOLD_AUTHORITY)

    def test_candidate_ref_missing_holds(self):
        cut = dataclasses.replace(p.PromotionCut(), exact_candidate_ref_observed=False)
        self.assertEqual(p.assess_and_promote(cut=cut), p.HOLD_CANDIDATE)

    def test_claim_ceiling_rejects_future_currentness_overclaim(self):
        r = p.assess_and_promote()
        bad = dataclasses.replace(r, current_at_future_use_proven=True)
        with self.assertRaises(ValueError):
            bad.validate_claim_ceiling()

    def test_claim_ceiling_rejects_public_authority_widening(self):
        r = p.assess_and_promote()
        bad = dataclasses.replace(r, public_effect_authorized=True)
        with self.assertRaises(ValueError):
            bad.validate_claim_ceiling()

    def test_complete_different_j(self):
        self.assertEqual(p.prove_different_j(), 256)

    def test_core_laws(self):
        self.assertIn("HeadCandidate!=CurrentHead", p.LAWS)
        self.assertIn("QueuePresence!=Execution", p.LAWS)
        self.assertIn("NewerTypedHeadObserved=>NoForkHold", p.LAWS)
        self.assertIn("CurrentAtPromotionCut!=CurrentAtFutureUse", p.LAWS)
        self.assertIn("CoordinateMemory!=MODEL_PREFIX_KV", p.LAWS)


if __name__ == "__main__":
    unittest.main()

import unittest
from dataclasses import replace
from itertools import product

from campaign import fixture, run
from successor_admission_gate import (
    Disposition, evaluate_successor_pair, independent_oracle,
    omega8_classify, thirteen_d_collapse,
)


class SuccessorAdmissionGateTests(unittest.TestCase):
    def setUp(self):
        self.ctx, self.a, self.b = fixture()

    def test_valid_pair_is_eligible(self):
        self.assertEqual(evaluate_successor_pair([self.a, self.b], self.ctx).disposition, Disposition.ELIGIBLE_TO_MINT_SUCCESSOR)

    def test_exactly_two_required(self):
        self.assertEqual(evaluate_successor_pair([self.a], self.ctx).disposition, Disposition.HOLD)
        self.assertEqual(evaluate_successor_pair([self.a, self.b, self.a], self.ctx).disposition, Disposition.HOLD)

    def test_current_actor_rejected(self):
        r = evaluate_successor_pair([replace(self.a, actor_id=self.ctx.current_actor_id), self.b], self.ctx)
        self.assertIn("P1_NOT_FOREIGN_ACTOR", r.reasons)

    def test_same_actor_rejected(self):
        r = evaluate_successor_pair([self.a, replace(self.b, actor_id=self.a.actor_id)], self.ctx)
        self.assertIn("PARENT_ACTORS_NOT_DISTINCT", r.reasons)

    def test_same_lineage_rejected(self):
        r = evaluate_successor_pair([self.a, replace(self.b, lineage_root=self.a.lineage_root)], self.ctx)
        self.assertIn("PARENT_LINEAGES_NOT_DISTINCT", r.reasons)

    def test_strict_post_cut(self):
        r = evaluate_successor_pair([replace(self.a, created_at=self.ctx.predecessor_cut), self.b], self.ctx)
        self.assertIn("P1_NOT_POST_CUT", r.reasons)

    def test_future_dated_rejected(self):
        r = evaluate_successor_pair([self.a, replace(self.b, created_at="2026-09-06T00:50:00.001Z")], self.ctx)
        self.assertIn("P2_FUTURE_DATED", r.reasons)

    def test_projection_rejected(self):
        r = evaluate_successor_pair([replace(self.a, projection_of="x"), self.b], self.ctx)
        self.assertIn("P1_PROJECTION_ONLY", r.reasons)

    def test_nonterminal_rejected(self):
        r = evaluate_successor_pair([self.a, replace(self.b, artifact_class="HYPERSCALE_APPEND")], self.ctx)
        self.assertIn("P2_NOT_SEMANTIC_TERMINAL", r.reasons)

    def test_same_effect_rejected(self):
        b = replace(self.b, consequence_axes=self.a.consequence_axes, consequence_action=self.a.consequence_action, invariant_delta=self.a.invariant_delta)
        r = evaluate_successor_pair([self.a, b], self.ctx)
        self.assertIn("PARENT_CONSEQUENCES_NOT_DISTINCT", r.reasons)

    def test_same_receipt_rejected(self):
        r = evaluate_successor_pair([self.a, replace(self.b, receipt_root=self.a.receipt_root)], self.ctx)
        self.assertIn("PARENT_RECEIPTS_NOT_DISTINCT", r.reasons)

    def test_same_derivation_rejected(self):
        r = evaluate_successor_pair([self.a, replace(self.b, derivation_root=self.a.derivation_root)], self.ctx)
        self.assertIn("PARENT_DERIVATIONS_NOT_DISTINCT", r.reasons)

    def test_k27_is_deterministic(self):
        r1 = evaluate_successor_pair([self.a, self.b], self.ctx)
        r2 = evaluate_successor_pair([self.b, self.a], self.ctx)
        self.assertEqual(r1.pair_root, r2.pair_root)
        self.assertEqual(r1.k27_coordinate, r2.k27_coordinate)

    def test_authority_is_clamped_d0(self):
        self.assertEqual(evaluate_successor_pair([self.a, self.b], self.ctx).authority_ceiling, "D0")

    def test_oracle_agrees_on_valid_and_invalid(self):
        self.assertEqual(independent_oracle([self.a, self.b], self.ctx), Disposition.ELIGIBLE_TO_MINT_SUCCESSOR)
        bad = replace(self.b, actor_id=self.a.actor_id)
        self.assertEqual(independent_oracle([self.a, bad], self.ctx), Disposition.QUARANTINE)

    def test_bad_root_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate_successor_pair([replace(self.a, receipt_root="bad"), self.b], self.ctx)

    def test_bad_time_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate_successor_pair([replace(self.a, created_at="2026-09-06 00:20"), self.b], self.ctx)

    def test_omega8_exactly_one_keeper(self):
        keepers = sum(omega8_classify(s) == Disposition.ELIGIBLE_TO_MINT_SUCCESSOR for s in product((0,1,2), repeat=8))
        self.assertEqual(keepers, 1)

    def test_13d_context_cannot_repair_invalid(self):
        for tail in product((0,1,2), repeat=5):
            self.assertNotEqual(thirteen_d_collapse((0,2,2,2,2,2,2,2), tail), Disposition.ELIGIBLE_TO_MINT_SUCCESSOR)

    def test_13d_context_cannot_repair_unresolved(self):
        for tail in product((0,1,2), repeat=5):
            self.assertNotEqual(thirteen_d_collapse((1,2,2,2,2,2,2,2), tail), Disposition.ELIGIBLE_TO_MINT_SUCCESSOR)

    def test_campaign_has_zero_false_admissions(self):
        s = run()
        self.assertEqual(s["hs1000_cases"], 1000)
        self.assertEqual(s["hs1000_false_admissions"], 0)
        self.assertEqual(s["oracle"]["mismatches"], 0)
        self.assertEqual(s["omega8"][Disposition.ELIGIBLE_TO_MINT_SUCCESSOR.value], 1)
        self.assertEqual(s["13d"]["invalid_repairs"], 0)
        self.assertEqual(s["13d"]["unresolved_repairs"], 0)


if __name__ == "__main__":
    unittest.main()

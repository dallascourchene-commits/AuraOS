from __future__ import annotations

from dataclasses import replace
import unittest

from tools import aura_noncompensatory_evidence_product_gate as n1


DIGEST = "a" * 64


def signal(outcome=n1.SUPPORTS, strength=1, signal_id="s1"):
    return n1.EvidenceSignal(signal_id, outcome, strength, "TEST_SCOPE", DIGEST)


def gate(passed=True, gate_id="g1"):
    return n1.HardGate(gate_id, passed, "TEST_DOMAIN", None if passed else "BLOCKED")


class NonCompensatoryEvidenceProductGateTests(unittest.TestCase):
    def test_exact_parent_fixture_holds_despite_favorable_evidence(self):
        r = n1.current_parent_fixture()
        self.assertEqual(r.disposition, n1.HOLD_HARD_GATE)
        self.assertTrue(r.positive_evidence_present)
        self.assertFalse(r.all_hard_gates_pass)
        self.assertFalse(r.evidence_policy_evaluated)
        self.assertFalse(r.bounded_proposal_eligible)

    def test_arbitrarily_large_support_cannot_bypass_failed_gate(self):
        r = n1.current_parent_fixture(support_strength=10**18)
        self.assertEqual(r.max_support_strength, 10**18)
        self.assertEqual(r.disposition, n1.HOLD_HARD_GATE)
        self.assertFalse(r.bounded_proposal_eligible)
        self.assertFalse(r.evidence_can_compensate_for_failed_gate)
        self.assertFalse(r.evidence_magnitude_changes_feasibility)

    def test_all_gates_pass_and_support_is_bounded_eligible(self):
        r = n1.evaluate_product_gate(signals=(signal(),), gates=(gate(),))
        self.assertEqual(r.disposition, n1.ELIGIBLE_BOUNDED_PROPOSAL)
        self.assertTrue(r.evidence_policy_evaluated)
        self.assertTrue(r.bounded_proposal_eligible)

    def test_neutral_evidence_stops_when_feasible(self):
        r = n1.evaluate_product_gate(signals=(signal(n1.NEUTRAL),), gates=(gate(),))
        self.assertEqual(r.disposition, n1.STOP_NO_POSITIVE_EVIDENCE)
        self.assertFalse(r.bounded_proposal_eligible)

    def test_opposing_evidence_stops_when_feasible(self):
        r = n1.evaluate_product_gate(signals=(signal(n1.OPPOSES),), gates=(gate(),))
        self.assertEqual(r.disposition, n1.STOP_OPPOSING_EVIDENCE)
        self.assertFalse(r.bounded_proposal_eligible)

    def test_one_failed_gate_dominates_other_passes(self):
        r = n1.evaluate_product_gate(
            signals=(signal(strength=999),), gates=(gate(True, "g1"), gate(False, "g2"))
        )
        self.assertEqual(r.failed_gate_ids, ("g2",))
        self.assertEqual(r.disposition, n1.HOLD_HARD_GATE)

    def test_duplicate_gate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_GATE_ID"):
            n1.evaluate_product_gate(signals=(signal(),), gates=(gate(True), gate(True)))

    def test_unknown_outcome_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_EVIDENCE_OUTCOME"):
            n1.evaluate_product_gate(signals=(signal("MAYBE"),), gates=(gate(),))

    def test_coordinate_like_metadata_cannot_flip_gate(self):
        base = n1.current_parent_fixture()
        altered_signal = replace(
            signal(strength=10**12),
            signal_id="k27:26,1,16",
            scope="EXTERNAL_COORDINATE_ONLY",
        )
        r = n1.evaluate_product_gate(
            signals=(altered_signal,),
            gates=(n1.HardGate("source", False, "SOURCE", "SOURCE_BYTES_MISSING"),),
        )
        self.assertEqual(r.disposition, n1.HOLD_HARD_GATE)
        self.assertFalse(r.k27_coordinate_grants_constraint_satisfaction)
        self.assertFalse(base.k27_coordinate_grants_constraint_satisfaction)

    def test_receipt_deterministic(self):
        self.assertEqual(n1.current_parent_fixture().receipt_digest, n1.current_parent_fixture().receipt_digest)

    def test_claim_ceiling(self):
        r = n1.current_parent_fixture()
        for key in (
            "evidence_can_compensate_for_failed_gate",
            "evidence_magnitude_changes_feasibility",
            "k27_coordinate_grants_constraint_satisfaction",
            "semantic_truth_minted",
            "effect_authority_granted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(r, key), key)


if __name__ == "__main__":
    unittest.main()

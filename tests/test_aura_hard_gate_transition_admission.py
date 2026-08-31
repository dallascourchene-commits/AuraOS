from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_hard_gate_transition_admission import (
    EvidenceDescriptorRef,
    GateEvidenceState,
    ProductState,
    TransitionRequest,
    evaluate_hard_gate_transition,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def gate(gate_id: str, passed: bool, generation: str, receipt: str, **overrides):
    base = GateEvidenceState(
        gate_id=gate_id,
        gate_scope_digest=A if gate_id == "source" else B,
        evidence_generation=generation,
        receipt_digest=receipt,
        verification_state="EXACT_GREEN" if passed else "HOLD",
        blocker=None if passed else f"{gate_id.upper()}_BLOCKED",
        passed=passed,
    )
    return replace(base, **overrides)


def evidence(**overrides):
    base = EvidenceDescriptorRef(descriptor_digest=C, evidence_generation="evidence-gen-4")
    return replace(base, **overrides)


def request(*, before_gates=None, after_gates=None, evidence_before=None, evidence_after=None, target="source"):
    return TransitionRequest(
        schema_version="AURA-HARD-GATE-TRANSITION-v1",
        transition_id="transition:source:1",
        domain_id="generic.bounded.proposal",
        target_gate_id=target,
        before=ProductState(tuple(before_gates or (
            gate("source", False, "source-gen-1", "1" * 64),
            gate("authority", True, "authority-gen-1", "2" * 64),
        ))),
        after=ProductState(tuple(after_gates or (
            gate("source", True, "source-gen-2", "3" * 64),
            gate("authority", True, "authority-gen-1", "2" * 64),
        ))),
        evidence_before=evidence_before or evidence(),
        evidence_after=evidence_after or evidence(),
        source_currentness_root="currentness-root-9",
    )


class HardGateTransitionAdmissionTests(unittest.TestCase):
    def test_exact_single_gate_closure_changes_feasibility(self):
        result = evaluate_hard_gate_transition(request())
        self.assertEqual(result.disposition, "ELIGIBLE_BOUNDED_PROPOSAL")
        self.assertTrue(result.proposal_eligible)
        self.assertFalse(result.before_product_feasible)
        self.assertTrue(result.after_product_feasible)
        self.assertEqual(result.changed_hard_gate_ids, ("source",))
        self.assertIsNotNone(result.transition_receipt_digest)
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.provider_effect_authorized)
        self.assertFalse(result.gate10_promoted)

    def test_transition_receipt_is_deterministic(self):
        a = evaluate_hard_gate_transition(request())
        b = evaluate_hard_gate_transition(request())
        self.assertEqual(a.transition_receipt_digest, b.transition_receipt_digest)

    def test_evidence_change_during_gate_closure_is_not_attributed_to_gate_alone(self):
        result = evaluate_hard_gate_transition(
            request(evidence_after=evidence(descriptor_digest=D))
        )
        self.assertEqual(result.disposition, "REVIEW")
        self.assertEqual(result.reason_code, "EVIDENCE_CHANGED_WITH_GATE_CLOSURE")
        self.assertFalse(result.proposal_eligible)

    def test_evidence_generation_change_also_forces_review(self):
        result = evaluate_hard_gate_transition(
            request(evidence_after=evidence(evidence_generation="evidence-gen-5"))
        )
        self.assertEqual(result.reason_code, "EVIDENCE_CHANGED_WITH_GATE_CLOSURE")

    def test_same_gate_generation_cannot_mint_transition(self):
        after = (
            gate("source", True, "source-gen-1", "3" * 64),
            gate("authority", True, "authority-gen-1", "2" * 64),
        )
        result = evaluate_hard_gate_transition(request(after_gates=after))
        self.assertEqual(result.disposition, "HOLD")
        self.assertEqual(result.reason_code, "GATE_EVIDENCE_GENERATION_DID_NOT_ADVANCE")

    def test_same_receipt_digest_cannot_mint_transition(self):
        after = (
            gate("source", True, "source-gen-2", "1" * 64),
            gate("authority", True, "authority-gen-1", "2" * 64),
        )
        result = evaluate_hard_gate_transition(request(after_gates=after))
        self.assertEqual(result.reason_code, "GATE_CLOSURE_RECEIPT_DID_NOT_CHANGE")

    def test_scope_change_requires_new_gate_relation(self):
        after = (
            gate("source", True, "source-gen-2", "3" * 64, gate_scope_digest=D),
            gate("authority", True, "authority-gen-1", "2" * 64),
        )
        result = evaluate_hard_gate_transition(request(after_gates=after))
        self.assertEqual(result.disposition, "REVIEW")
        self.assertEqual(result.reason_code, "GATE_SCOPE_CHANGED_REQUIRES_NEW_GATE")

    def test_other_gate_change_is_not_single_gate_transition(self):
        after = (
            gate("source", True, "source-gen-2", "3" * 64),
            gate("authority", True, "authority-gen-2", "4" * 64),
        )
        result = evaluate_hard_gate_transition(request(after_gates=after))
        self.assertEqual(result.reason_code, "MULTIPLE_OR_WRONG_HARD_GATE_CHANGES")
        self.assertFalse(result.proposal_eligible)

    def test_other_gate_remaining_false_keeps_product_blocked(self):
        before = (
            gate("source", False, "source-gen-1", "1" * 64),
            gate("authority", False, "authority-gen-1", "2" * 64),
        )
        after = (
            gate("source", True, "source-gen-2", "3" * 64),
            gate("authority", False, "authority-gen-1", "2" * 64),
        )
        result = evaluate_hard_gate_transition(request(before_gates=before, after_gates=after))
        self.assertEqual(result.disposition, "HOLD")
        self.assertEqual(result.reason_code, "OTHER_HARD_GATE_REMAINS_BLOCKING")
        self.assertFalse(result.proposal_eligible)
        self.assertIsNotNone(result.transition_receipt_digest)

    def test_action_required_cannot_be_passed_gate(self):
        bad_after = (
            gate(
                "source", True, "source-gen-2", "3" * 64,
                verification_state="ACTION_REQUIRED"
            ),
            gate("authority", True, "authority-gen-1", "2" * 64),
        )
        with self.assertRaisesRegex(ValueError, "PASSED_GATE_REQUIRES_EXACT_GREEN"):
            evaluate_hard_gate_transition(request(after_gates=bad_after))

    def test_fail_to_fail_and_pass_to_pass_are_not_closure(self):
        fail_after = (
            gate("source", False, "source-gen-2", "3" * 64),
            gate("authority", True, "authority-gen-1", "2" * 64),
        )
        result = evaluate_hard_gate_transition(request(after_gates=fail_after))
        self.assertEqual(result.reason_code, "TARGET_GATE_MUST_TRANSITION_FAIL_TO_PASS")

        before_pass = (
            gate("source", True, "source-gen-1", "1" * 64),
            gate("authority", False, "authority-gen-1", "2" * 64),
        )
        after_pass = (
            gate("source", True, "source-gen-2", "3" * 64),
            gate("authority", False, "authority-gen-1", "2" * 64),
        )
        result2 = evaluate_hard_gate_transition(request(before_gates=before_pass, after_gates=after_pass))
        self.assertEqual(result2.reason_code, "TARGET_GATE_MUST_TRANSITION_FAIL_TO_PASS")

    def test_gate_set_change_is_review_not_silent_reinterpretation(self):
        after = (
            gate("source", True, "source-gen-2", "3" * 64),
            gate("authority", True, "authority-gen-1", "2" * 64),
            gate("new-gate", True, "new-gen-1", "4" * 64, gate_scope_digest=D),
        )
        result = evaluate_hard_gate_transition(request(after_gates=after))
        self.assertEqual(result.disposition, "REVIEW")
        self.assertEqual(result.reason_code, "HARD_GATE_SET_CHANGED")


if __name__ == "__main__":
    unittest.main()

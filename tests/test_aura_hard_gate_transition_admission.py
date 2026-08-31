from dataclasses import replace
import unittest

from tools import aura_hard_gate_transition_admission as t
from tools import aura_noncompensatory_evidence_product_gate as n1


class HardGateTransitionAdmissionTests(unittest.TestCase):
    def parts(self):
        signal = n1.EvidenceSignal(
            signal_id="bounded-signal",
            outcome=n1.SUPPORTS,
            strength=7,
            scope="REPRESENTATIVE_ONLY",
            evidence_digest="1" * 64,
        )
        evidence = t.EvidenceGeneration(signal=signal, generation="evidence-generation-1")
        scope = t._sha("gate-scope")
        before = t.GateEvidenceState(
            gate_id="source-gate",
            domain="SOURCE",
            gate_scope_digest=scope,
            evidence_generation="gate-generation-before",
            receipt_digest="2" * 64,
            passed=False,
            blocker="MISSING_EXACT_SOURCE_EVIDENCE",
            exact_green=True,
        )
        after = t.GateEvidenceState(
            gate_id="source-gate",
            domain="SOURCE",
            gate_scope_digest=scope,
            evidence_generation="gate-generation-after",
            receipt_digest="3" * 64,
            passed=True,
            blocker=None,
            exact_green=True,
        )
        return before, after, evidence

    def admit(self, **kw):
        before, after, evidence = self.parts()
        return t.admit_hard_gate_transition(
            before_gate=kw.get("before", before),
            after_gate=kw.get("after", after),
            before_evidence=kw.get("before_evidence", evidence),
            after_evidence=kw.get("after_evidence", evidence),
            unchanged_gates_before=kw.get("other_before", ()),
            unchanged_gates_after=kw.get("other_after", ()),
        )

    def test_exact_gate_closure_recomputes_same_evidence_into_bounded_proposal(self):
        r = self.admit()
        self.assertFalse(r.before_product_feasible)
        self.assertEqual(r.before_disposition, n1.HOLD_HARD_GATE)
        self.assertFalse(r.evidence_policy_evaluated_before)
        self.assertTrue(r.after_product_feasible)
        self.assertEqual(r.after_disposition, n1.ELIGIBLE_BOUNDED_PROPOSAL)
        self.assertTrue(r.evidence_policy_evaluated_after)
        self.assertTrue(r.bounded_proposal_eligible_after)
        self.assertTrue(r.evidence_unchanged)
        self.assertEqual(r.changed_hard_gate_ids, ("source-gate",))

    def test_replaying_same_gate_generation_is_not_closure(self):
        before, after, evidence = self.parts()
        with self.assertRaisesRegex(ValueError, "GATE_EVIDENCE_GENERATION_DID_NOT_ADVANCE"):
            self.admit(after=replace(after, evidence_generation=before.evidence_generation))

    def test_gate_identity_and_scope_cannot_change(self):
        _, after, _ = self.parts()
        with self.assertRaisesRegex(ValueError, "GATE_ID_CHANGED"):
            self.admit(after=replace(after, gate_id="different-gate"))
        with self.assertRaisesRegex(ValueError, "GATE_SCOPE_CHANGED"):
            self.admit(after=replace(after, gate_scope_digest="4" * 64))

    def test_domain_change_rejected(self):
        _, after, _ = self.parts()
        with self.assertRaisesRegex(ValueError, "GATE_DOMAIN_CHANGED"):
            self.admit(after=replace(after, domain="OTHER"))

    def test_closure_must_be_fail_to_pass_and_exact_green(self):
        before, after, _ = self.parts()
        with self.assertRaisesRegex(ValueError, "TRANSITION_MUST_BE_FAIL_TO_PASS"):
            self.admit(before=replace(before, passed=True, blocker=None))
        with self.assertRaisesRegex(ValueError, "CLOSURE_RECEIPT_NOT_EXACT_GREEN_CURRENT"):
            self.admit(after=replace(after, exact_green=False))

    def test_evidence_descriptor_or_generation_change_is_separate_change(self):
        _, _, evidence = self.parts()
        changed_signal = replace(evidence.signal, strength=8)
        with self.assertRaisesRegex(ValueError, "EVIDENCE_DESCRIPTOR_CHANGED_DURING_GATE_CLOSURE"):
            self.admit(after_evidence=replace(evidence, signal=changed_signal))
        with self.assertRaisesRegex(ValueError, "EVIDENCE_GENERATION_CHANGED_DURING_GATE_CLOSURE"):
            self.admit(after_evidence=replace(evidence, generation="evidence-generation-2"))

    def test_unreceipted_second_gate_change_rejected(self):
        b = n1.HardGate(gate_id="other", passed=False, domain="OTHER", blocker="BLOCKED")
        a = n1.HardGate(gate_id="other", passed=True, domain="OTHER", blocker=None)
        with self.assertRaisesRegex(ValueError, "UNRECEIPTED_SECOND_GATE_CHANGE"):
            self.admit(other_before=(b,), other_after=(a,))

    def test_one_gate_closed_does_not_mean_all_gates_closed(self):
        other = n1.HardGate(gate_id="other", passed=False, domain="OTHER", blocker="BLOCKED")
        r = self.admit(other_before=(other,), other_after=(other,))
        self.assertFalse(r.after_product_feasible)
        self.assertEqual(r.after_disposition, n1.HOLD_HARD_GATE)
        self.assertFalse(r.evidence_policy_evaluated_after)
        self.assertFalse(r.bounded_proposal_eligible_after)
        self.assertEqual(r.unchanged_hard_gate_ids, ("other",))

    def test_coordinate_and_authority_crosscasts_are_impossible(self):
        r = self.admit()
        self.assertFalse(r.k27_coordinate_affects_feasibility)
        self.assertFalse(r.proposal_eligibility_grants_execution_authority)
        self.assertFalse(r.gate_closure_grants_tensor_payload_evidence)
        self.assertFalse(r.semantic_truth_minted)
        self.assertFalse(r.effect_authority_granted)
        self.assertFalse(r.native_private_transformer_kv_accessed)
        self.assertFalse(r.gate10_promoted)
        self.assertFalse(r.merge_or_deployment_authorized)

    def test_current_n1_q15_fixture_binds_exact_parents_and_q15_receipt(self):
        r = t.current_n1_q15_fixture()
        self.assertEqual(r.parent_heads, (t.N1_HEAD, t.Q15_HEAD))
        self.assertEqual(r.parent_runs, (t.N1_RUN, t.Q15_RUN))
        self.assertEqual(r.parent_jobs, (t.N1_JOB, t.Q15_JOB))
        self.assertEqual(r.convergence_commit, t.CONVERGENCE)
        self.assertEqual(r.closure_receipt_digest, t.Q15_RECEIPT)
        self.assertEqual(r.after_disposition, n1.ELIGIBLE_BOUNDED_PROPOSAL)
        self.assertTrue(r.bounded_proposal_eligible_after)

    def test_receipt_is_deterministic(self):
        self.assertEqual(self.admit().receipt_digest, self.admit().receipt_digest)


if __name__ == "__main__":
    unittest.main()

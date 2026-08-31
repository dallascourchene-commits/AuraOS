import unittest
from dataclasses import replace

import tools.aura_nav14_progress_bound_hydrated_version_handoff as m

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64


def handoff():
    return m.HydratedVersionHandoffProjectionV1(
        parent_head=m.HANDOFF_HEAD,
        handoff_digest=D1,
        disposition="HANDOFF_READY_CANDIDATE",
        subject_key=D1,
        evidence_generation_key=D2,
        material_digest=D0,
        exact_source_uri="https://example.test/source",
        future_read_axes=m.REQUIRED_FUTURE_READ_AXES,
        eki2_read_axes=m.REQUIRED_EKI2_AXES,
    )


def retrieval(decision=m.RetrievalDecision.ALLOW_INITIAL, *, evidence_digest=D0, purpose=m.REQUIRED_PURPOSE):
    return m._retrieval_fixture(decision, evidence_digest=evidence_digest, purpose=purpose)


class ProgressBoundHydratedVersionHandoffTests(unittest.TestCase):
    def test_initial_retrieval_can_support_candidate_only(self):
        r = m.bind_progress_bound_handoff(handoff=handoff(), retrieval=retrieval())
        self.assertTrue(r.ready)
        self.assertEqual(r.disposition, m.ProgressHandoffDisposition.PROGRESS_BOUND_HANDOFF_CANDIDATE)
        self.assertFalse(r.persistent_write_authorized)
        self.assertFalse(r.evidence_admitted)
        self.assertFalse(r.source_truth_proven)
        self.assertFalse(r.source_currentness_proven)
        self.assertFalse(r.read_currentness_proven)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.semantic_k27_authority)
        self.assertFalse(r.native_private_transformer_kv_accessed)

    def test_independent_provider_state_transition_can_support_candidate(self):
        r = m.bind_progress_bound_handoff(
            handoff=handoff(),
            retrieval=retrieval(m.RetrievalDecision.ALLOW_STATE_TRANSITION),
        )
        self.assertTrue(r.ready)

    def test_fingerprint_axis_change_alone_cannot_mint_handoff_consequence(self):
        r = m.bind_progress_bound_handoff(
            handoff=handoff(),
            retrieval=retrieval(m.RetrievalDecision.ALLOW_CHANGED_AXIS),
        )
        self.assertEqual(r.disposition, m.ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_ONLY)
        self.assertFalse(r.ready)

    def test_first_identical_no_progress_repeat_requires_axis_change(self):
        r = m.bind_progress_bound_handoff(
            handoff=handoff(),
            retrieval=retrieval(m.RetrievalDecision.CHANGE_AXIS_REQUIRED),
        )
        self.assertEqual(
            r.disposition,
            m.ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
        )

    def test_repeated_identical_no_progress_collapses_handoff_cone(self):
        r = m.bind_progress_bound_handoff(
            handoff=handoff(),
            retrieval=retrieval(m.RetrievalDecision.COLLAPSE_CONE),
        )
        self.assertEqual(
            r.disposition,
            m.ProgressHandoffDisposition.HOLD_RETRIEVAL_CONE_COLLAPSED,
        )

    def test_retrieval_evidence_must_bind_exact_hydrated_material(self):
        r = m.bind_progress_bound_handoff(
            handoff=handoff(), retrieval=retrieval(evidence_digest=D1)
        )
        self.assertEqual(
            r.disposition,
            m.ProgressHandoffDisposition.HOLD_EVIDENCE_DIGEST_MISMATCH,
        )

    def test_retrieval_purpose_must_be_exact_handoff_purpose(self):
        r = m.bind_progress_bound_handoff(
            handoff=handoff(), retrieval=retrieval(purpose="generic-hydration")
        )
        self.assertEqual(r.disposition, m.ProgressHandoffDisposition.HOLD_PURPOSE_MISMATCH)

    def test_handoff_must_remain_ready_and_carry_read_debt(self):
        self.assertEqual(
            m.bind_progress_bound_handoff(
                handoff=replace(handoff(), disposition="HOLD_TRANSITION_NOT_READY"),
                retrieval=retrieval(),
            ).disposition,
            m.ProgressHandoffDisposition.HOLD_HANDOFF_NOT_READY,
        )
        self.assertEqual(
            m.bind_progress_bound_handoff(
                handoff=replace(handoff(), future_read_axes=()),
                retrieval=retrieval(),
            ).disposition,
            m.ProgressHandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED,
        )

    def test_parent_generation_mismatch_holds(self):
        r = m.bind_progress_bound_handoff(
            handoff=replace(handoff(), parent_head="f" * 40), retrieval=retrieval()
        )
        self.assertEqual(r.disposition, m.ProgressHandoffDisposition.HOLD_PARENT_GENERATION)

    def test_claim_ceiling_widening_holds(self):
        r = m.bind_progress_bound_handoff(
            handoff=replace(handoff(), evidence_admitted=True), retrieval=retrieval()
        )
        self.assertEqual(r.disposition, m.ProgressHandoffDisposition.HOLD_CLAIM_CEILING)
        r2 = m.bind_progress_bound_handoff(
            handoff=handoff(),
            retrieval=replace(retrieval(), semantic_truth_proven=True),
        )
        self.assertEqual(r2.disposition, m.ProgressHandoffDisposition.HOLD_CLAIM_CEILING)

    def test_parent_retrieval_receipt_identity_is_recomputed(self):
        with self.assertRaisesRegex(ValueError, "RETRIEVAL_RECEIPT_DIGEST_MISMATCH"):
            m.bind_progress_bound_handoff(
                handoff=handoff(), retrieval=replace(retrieval(), receipt_digest=D2)
            )

    def test_parent_retrieval_decision_shape_is_fail_closed(self):
        good = retrieval(m.RetrievalDecision.ALLOW_INITIAL)
        forged = replace(
            good,
            decision=m.RetrievalDecision.CHANGE_AXIS_REQUIRED,
            receipt_digest=D0,
        )
        forged = replace(forged, receipt_digest=m._parent_receipt_digest(forged))
        with self.assertRaisesRegex(ValueError, "RETRIEVAL_DECISION_SHAPE_INVALID"):
            m.bind_progress_bound_handoff(handoff=handoff(), retrieval=forged)

    def test_deterministic_receipt(self):
        a = m.bind_progress_bound_handoff(handoff=handoff(), retrieval=retrieval())
        b = m.bind_progress_bound_handoff(handoff=handoff(), retrieval=retrieval())
        self.assertEqual(a, b)
        self.assertEqual(a.progress_handoff_digest, b.progress_handoff_digest)

    def test_complete_different_j_matrix(self):
        self.assertEqual(m.prove_different_j(), 80)


if __name__ == "__main__":
    unittest.main()

from dataclasses import replace
import unittest

import tools.awj032.glm53_g7_progress_current_admission_handoff as m


class G7ProgressCurrentAdmissionHandoffTests(unittest.TestCase):
    def setUp(self):
        self.progress, self.reuse, self.current = m.fixture()

    def bind(self, progress=None, reuse=None, current=None):
        return m.bind_progress_current_admission_handoff(
            progress=progress or self.progress,
            reuse=reuse or self.reuse,
            current=current or self.current,
        )

    def test_exact_current_pair_yields_candidate_only(self):
        r = self.bind()
        self.assertTrue(r.ready)
        self.assertEqual(
            r.disposition,
            m.G7Disposition.CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE,
        )
        self.assertTrue(r.future_read_currentness_required)
        self.assertFalse(r.future_read_currentness_proven)
        self.assertFalse(r.tensor_payload_bound)
        self.assertFalse(r.evidence_admitted)
        self.assertFalse(r.persistent_write_authorized)
        self.assertFalse(r.execution_authorized)
        self.assertFalse(r.provider_effect_authorized)
        self.assertFalse(r.owner_host_execution_observed)
        self.assertFalse(r.gate10_promoted)
        self.assertFalse(r.semantic_k27_authority)
        self.assertFalse(r.native_private_transformer_kv_accessed)

    def test_nav14_parent_generation_drift_holds(self):
        r = self.bind(progress=replace(self.progress, parent_head="f" * 40))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_PARENT_GENERATION)
        self.assertFalse(r.ready)

    def test_admission_reuse_parent_generation_drift_holds(self):
        r = self.bind(reuse=replace(self.reuse, parent_head="f" * 40))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_PARENT_GENERATION)

    def test_progress_not_ready_holds(self):
        r = self.bind(
            progress=replace(
                self.progress, disposition="HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
            )
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY
        )

    def test_reuse_not_ready_holds(self):
        r = self.bind(
            reuse=replace(self.reuse, disposition="HOLD_SOURCE_GENERATION_CHANGED")
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_ADMISSION_REUSE_NOT_READY
        )

    def test_wrong_admission_family_holds(self):
        r = self.bind(reuse=replace(self.reuse, family="HYDRATION_TRANSACTION"))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_ADMISSION_FAMILY)

    def test_claim_widening_holds(self):
        r = self.bind(progress=replace(self.progress, source_truth_proven=True))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_CLAIM_CEILING)
        r = self.bind(reuse=replace(self.reuse, execution_authorized=True))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_CLAIM_CEILING)

    def test_subject_mismatch_holds(self):
        r = self.bind(
            reuse=replace(
                self.reuse, subject_identity=self.reuse.subject_identity + ":other"
            )
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH
        )

    def test_evidence_generation_mismatch_holds(self):
        r = self.bind(
            reuse=replace(
                self.reuse,
                evidence_generation_key=self.reuse.evidence_generation_key + ":other",
            )
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
        )

    def test_current_progress_receipt_drift_holds(self):
        r = self.bind(
            current=replace(self.current, progress_handoff_digest="4" * 64)
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_PROGRESS_RECEIPT_CHANGED
        )

    def test_current_subject_and_evidence_drift_hold(self):
        r = self.bind(
            current=replace(
                self.current, subject_identity=self.current.subject_identity + ":drift"
            )
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH
        )
        r = self.bind(
            current=replace(
                self.current,
                evidence_generation_key=self.current.evidence_generation_key + ":drift",
            )
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
        )

    def test_material_drift_holds(self):
        r = self.bind(current=replace(self.current, material_digest="5" * 64))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_MATERIAL_CHANGED)

    def test_source_view_drift_holds(self):
        r = self.bind(
            current=replace(
                self.current, exact_source_uri=self.current.exact_source_uri + "#drift"
            )
        )
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_SOURCE_VIEW_CHANGED)

    def test_hold_receipt_suppresses_current_identity(self):
        r = self.bind(current=replace(self.current, material_digest="5" * 64))
        self.assertIsNone(r.subject_identity)
        self.assertIsNone(r.source_generation_key)
        self.assertIsNone(r.evidence_generation_key)
        self.assertIsNone(r.material_digest)
        self.assertIsNone(r.exact_source_uri)
        self.assertIsNone(r.owner_context_key)
        self.assertIsNone(r.decision_context_key)

    def test_receipt_is_deterministic(self):
        self.assertEqual(self.bind().handoff_receipt_digest, self.bind().handoff_receipt_digest)

    def test_bad_digest_shape_rejected(self):
        with self.assertRaises(ValueError):
            self.bind(progress=replace(self.progress, material_digest="not-a-digest"))

    def test_boolean_shape_rejected(self):
        with self.assertRaises(ValueError):
            self.bind(reuse=replace(self.reuse, candidate_only="true"))

    def test_complete_512_state_different_j_lattice(self):
        self.assertEqual(m.prove_different_j(), 512)


if __name__ == "__main__":
    unittest.main()

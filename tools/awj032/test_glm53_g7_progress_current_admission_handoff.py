from dataclasses import replace
import unittest

import tools.awj032.glm53_g7_progress_current_admission_handoff as m


class G7ProgressAdmissionStructuralHandoffTests(unittest.TestCase):
    def setUp(self):
        self.progress, self.reuse, self.presented = m.fixture()

    def bind(self, progress=None, reuse=None, presented=None):
        return m.bind_progress_admission_structural_handoff(
            progress=progress or self.progress,
            reuse=reuse or self.reuse,
            presented=presented or self.presented,
        )

    def recompute_reuse(self, reuse):
        return replace(
            reuse,
            reuse_digest=m._expected_admission_reuse_positive_digest(reuse),
        )

    def test_exact_structural_pair_requires_external_auth(self):
        r = self.bind()
        self.assertTrue(r.structural_candidate)
        self.assertEqual(
            r.disposition,
            m.G7Disposition.STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED,
        )
        self.assertTrue(r.parent_projection_authentication_required)
        self.assertFalse(r.parent_projection_authenticated_by_this_contract)
        self.assertTrue(r.presented_currentness_authentication_required)
        self.assertFalse(r.presented_currentness_authenticated_by_this_contract)
        self.assertTrue(r.future_read_currentness_required)
        self.assertFalse(r.future_read_currentness_proven)
        self.assertFalse(r.reuse_authorized_by_this_contract)
        self.assertFalse(r.tensor_payload_bound)
        self.assertFalse(r.evidence_admitted)
        self.assertFalse(r.persistent_write_authorized)
        self.assertFalse(r.execution_authorized)
        self.assertFalse(r.provider_effect_authorized)
        self.assertFalse(r.owner_host_execution_observed)
        self.assertFalse(r.gate10_promoted)

    def test_progress_positive_receipt_digest_is_recomputed(self):
        with self.assertRaisesRegex(
            ValueError, "NAV14_PROGRESS_RECEIPT_SELF_INTEGRITY_MISMATCH"
        ):
            self.bind(progress=replace(self.progress, progress_handoff_digest="0" * 64))

    def test_reuse_positive_receipt_digest_is_recomputed(self):
        with self.assertRaisesRegex(
            ValueError, "ADMISSION_REUSE_RECEIPT_SELF_INTEGRITY_MISMATCH"
        ):
            self.bind(reuse=replace(self.reuse, reuse_digest="0" * 64))

    def test_nav14_positive_requires_real_positive_retrieval_decision(self):
        bad = replace(self.progress, retrieval_decision="ALLOW_CHANGED_AXIS")
        with self.assertRaisesRegex(
            ValueError, "NAV14_POSITIVE_RETRIEVAL_DECISION_INVALID"
        ):
            self.bind(progress=bad)

    def test_nav14_subject_and_evidence_keep_parent_digest_shape(self):
        with self.assertRaisesRegex(ValueError, "PROGRESS_SUBJECT_DIGEST_REQUIRED"):
            self.bind(progress=replace(self.progress, subject_identity="not-a-digest"))
        with self.assertRaisesRegex(
            ValueError, "PROGRESS_EVIDENCE_GENERATION_DIGEST_REQUIRED"
        ):
            self.bind(
                progress=replace(self.progress, evidence_generation_key="not-a-digest")
            )

    def test_nav14_parent_generation_drift_holds(self):
        r = self.bind(progress=replace(self.progress, parent_head="f" * 40))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_PARENT_GENERATION)

    def test_admission_reuse_parent_generation_drift_holds(self):
        r = self.bind(reuse=replace(self.reuse, parent_head="f" * 40))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_PARENT_GENERATION)

    def test_progress_not_ready_holds(self):
        r = self.bind(
            progress=replace(
                self.progress, disposition="HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
            )
        )
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY)

    def test_reuse_not_ready_holds(self):
        r = self.bind(
            reuse=replace(self.reuse, disposition="HOLD_SOURCE_GENERATION_CHANGED")
        )
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_ADMISSION_REUSE_NOT_READY)

    def test_wrong_admission_family_holds(self):
        reuse = self.recompute_reuse(
            replace(self.reuse, family="HYDRATION_TRANSACTION")
        )
        r = self.bind(reuse=reuse)
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_ADMISSION_FAMILY)

    def test_claim_widening_holds(self):
        r = self.bind(progress=replace(self.progress, source_truth_proven=True))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_CLAIM_CEILING)
        r = self.bind(reuse=replace(self.reuse, execution_authorized=True))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_CLAIM_CEILING)

    def test_subject_mismatch_holds(self):
        reuse = self.recompute_reuse(
            replace(self.reuse, subject_identity="8" * 64)
        )
        r = self.bind(reuse=reuse)
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH)

    def test_evidence_generation_mismatch_holds(self):
        reuse = self.recompute_reuse(
            replace(self.reuse, evidence_generation_key="9" * 64)
        )
        r = self.bind(reuse=reuse)
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
        )

    def test_presented_progress_receipt_drift_holds(self):
        r = self.bind(
            presented=replace(self.presented, progress_handoff_digest="a" * 64)
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_PRESENTED_PROGRESS_RECEIPT_CHANGED
        )

    def test_presented_subject_and_evidence_drift_hold(self):
        r = self.bind(presented=replace(self.presented, subject_identity="8" * 64))
        self.assertEqual(r.disposition, m.G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH)
        r = self.bind(
            presented=replace(self.presented, evidence_generation_key="9" * 64)
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
        )

    def test_material_drift_holds(self):
        r = self.bind(presented=replace(self.presented, material_digest="b" * 64))
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_PRESENTED_MATERIAL_CHANGED
        )

    def test_source_view_drift_holds(self):
        r = self.bind(
            presented=replace(
                self.presented,
                exact_source_uri=self.presented.exact_source_uri + "#drift",
            )
        )
        self.assertEqual(
            r.disposition, m.G7Disposition.HOLD_PRESENTED_SOURCE_VIEW_CHANGED
        )

    def test_hold_receipt_suppresses_identity_bearing_fields(self):
        r = self.bind(presented=replace(self.presented, material_digest="b" * 64))
        self.assertIsNone(r.subject_identity)
        self.assertIsNone(r.source_generation_key)
        self.assertIsNone(r.evidence_generation_key)
        self.assertIsNone(r.material_digest)
        self.assertIsNone(r.exact_source_uri)
        self.assertIsNone(r.owner_context_key)
        self.assertIsNone(r.decision_context_key)

    def test_receipt_is_deterministic(self):
        self.assertEqual(
            self.bind().handoff_receipt_digest,
            self.bind().handoff_receipt_digest,
        )

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

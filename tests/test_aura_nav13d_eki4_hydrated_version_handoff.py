import unittest
from dataclasses import replace

import tools.aura_nav13d_eki4_hydrated_version_handoff as m

D0 = "0" * 64
D1 = "1" * 64


def hydration():
    return m.HydrationCompletionProjectionV1(
        parent_head=m.NAV13D_HEAD,
        completion_digest=D0,
        subject_key=D0,
        evidence_generation_key=D1,
        material_digest=D0,
        exact_source_uri="https://example.test/source",
        hydration_obligation_satisfied=True,
    )


def transition():
    return m.VersionTransitionProjectionV1(
        parent_head=m.EKI4_HEAD,
        envelope_receipt_digest=D1,
        disposition="VERSION_TRANSITION_PLAN_READY",
        current_subject_key=D0,
        current_evidence_generation_key=D1,
        source_content_digest=D0,
        exact_source_uri="https://example.test/source",
        write_currentness_resolved=True,
        read_currentness_debt_carried=True,
        required_future_read_axes=m.REQUIRED_GUARD_AXES,
        required_eki2_read_axes=m.REQUIRED_EKI2_AXES,
    )


class HydratedVersionHandoffTests(unittest.TestCase):
    def test_exact_handoff_ready_but_nonpromoting(self):
        r = m.bind_hydrated_version_handoff(hydration=hydration(), transition=transition())
        self.assertTrue(r.ready)
        self.assertFalse(r.persistent_write_authorized)
        self.assertFalse(r.evidence_admitted)
        self.assertFalse(r.source_truth_proven)
        self.assertFalse(r.read_currentness_proven)
        self.assertFalse(r.native_private_transformer_kv_accessed)

    def test_completion_required(self):
        r = m.bind_hydrated_version_handoff(
            hydration=replace(hydration(), hydration_obligation_satisfied=False),
            transition=transition(),
        )
        self.assertEqual(r.disposition, m.HandoffDisposition.HOLD_COMPLETION_UNSATISFIED)

    def test_transition_ready_required(self):
        r = m.bind_hydrated_version_handoff(
            hydration=hydration(),
            transition=replace(transition(), disposition="WRITE_CURRENTNESS_REQUIRED"),
        )
        self.assertEqual(r.disposition, m.HandoffDisposition.HOLD_TRANSITION_NOT_READY)

    def test_subject_generation_material_and_uri_are_independent_axes(self):
        cases = (
            (replace(transition(), current_subject_key=D1), m.HandoffDisposition.HOLD_SUBJECT_MISMATCH),
            (replace(transition(), current_evidence_generation_key=D0), m.HandoffDisposition.HOLD_EVIDENCE_GENERATION_MISMATCH),
            (replace(transition(), exact_source_uri="https://example.test/other"), m.HandoffDisposition.HOLD_SOURCE_URI_MISMATCH),
            (replace(transition(), source_content_digest=D1), m.HandoffDisposition.HOLD_MATERIAL_DIGEST_MISMATCH),
        )
        for t, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    m.bind_hydrated_version_handoff(hydration=hydration(), transition=t).disposition,
                    expected,
                )

    def test_write_currentness_and_future_read_debt_remain_separate(self):
        self.assertEqual(
            m.bind_hydrated_version_handoff(
                hydration=hydration(),
                transition=replace(transition(), write_currentness_resolved=False),
            ).disposition,
            m.HandoffDisposition.HOLD_WRITE_CURRENTNESS_UNRESOLVED,
        )
        self.assertEqual(
            m.bind_hydrated_version_handoff(
                hydration=hydration(),
                transition=replace(transition(), read_currentness_debt_carried=False),
            ).disposition,
            m.HandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED,
        )

    def test_exact_future_read_axes_required(self):
        r = m.bind_hydrated_version_handoff(
            hydration=hydration(),
            transition=replace(transition(), required_future_read_axes=()),
        )
        self.assertEqual(r.disposition, m.HandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED)

    def test_parent_generation_is_identity_bearing(self):
        r = m.bind_hydrated_version_handoff(
            hydration=replace(hydration(), parent_head="f" * 40),
            transition=transition(),
        )
        self.assertEqual(r.disposition, m.HandoffDisposition.HOLD_PARENT_GENERATION)

    def test_claim_ceiling_fails_closed(self):
        r = m.bind_hydrated_version_handoff(
            hydration=hydration(),
            transition=replace(transition(), write_authority=True),
        )
        self.assertEqual(r.disposition, m.HandoffDisposition.HOLD_CLAIM_CEILING)

    def test_model_prefix_kv_claim_fails_closed(self):
        r = m.bind_hydrated_version_handoff(
            hydration=replace(hydration(), native_private_transformer_kv_accessed=True),
            transition=transition(),
        )
        self.assertEqual(r.disposition, m.HandoffDisposition.HOLD_CLAIM_CEILING)

    def test_deterministic_receipt(self):
        a = m.bind_hydrated_version_handoff(hydration=hydration(), transition=transition())
        b = m.bind_hydrated_version_handoff(hydration=hydration(), transition=transition())
        self.assertEqual(a.handoff_digest, b.handoff_digest)

    def test_different_j_complete_128_state_matrix(self):
        self.assertEqual(m.prove_different_j(), 128)


if __name__ == "__main__":
    unittest.main()

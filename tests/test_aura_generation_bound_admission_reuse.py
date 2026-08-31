from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_generation_bound_admission_reuse import (
    AdmissionFamily,
    AdmissionReceiptProjectionV1,
    CurrentAdmissionUseContextV1,
    EXPECTED_HEAD,
    EXPECTED_POSITIVE_DISPOSITION,
    ReuseDisposition,
    fixture,
    prove_different_j,
    revalidate_admission_reuse,
)


class GenerationBoundAdmissionReuseTests(unittest.TestCase):
    def test_exact_reuse_is_candidate_only_for_both_families(self) -> None:
        for family in AdmissionFamily:
            admission, current = fixture(family)
            receipt = revalidate_admission_reuse(admission=admission, current=current)
            self.assertEqual(receipt.disposition, ReuseDisposition.REUSE_CANDIDATE)
            self.assertTrue(receipt.reusable_candidate)
            self.assertTrue(receipt.candidate_only)
            self.assertFalse(receipt.admission_reused_as_authority)
            self.assertFalse(receipt.execution_authorized)
            self.assertFalse(receipt.effect_authorized)
            self.assertFalse(receipt.source_currentness_proven)
            self.assertFalse(receipt.semantic_truth_proven)
            self.assertFalse(receipt.semantic_k27_authority)
            self.assertFalse(receipt.native_private_transformer_kv_accessed)

    def test_parent_generation_is_pinned(self) -> None:
        for family in AdmissionFamily:
            admission, current = fixture(family)
            forged = replace(admission, producer_head="0" * 40)
            receipt = revalidate_admission_reuse(admission=forged, current=current)
            self.assertEqual(receipt.disposition, ReuseDisposition.HOLD_PARENT_GENERATION)

    def test_positive_disposition_is_required(self) -> None:
        for family in AdmissionFamily:
            admission, current = fixture(family)
            for forged in (
                replace(admission, bounded_admission_positive=False),
                replace(admission, admission_disposition="SOMETHING_ELSE"),
            ):
                receipt = revalidate_admission_reuse(admission=forged, current=current)
                self.assertEqual(receipt.disposition, ReuseDisposition.HOLD_ADMISSION_NOT_POSITIVE)

    def test_claim_ceiling_is_fail_closed(self) -> None:
        for family in AdmissionFamily:
            admission, current = fixture(family)
            mutations = (
                {"candidate_only": False},
                {"source_currentness_proven": True},
                {"semantic_truth_proven": True},
                {"evidence_admitted": True},
                {"execution_authorized": True},
                {"effect_authorized": True},
                {"semantic_k27_authority": True},
                {"native_private_transformer_kv_accessed": True},
            )
            for mutation in mutations:
                receipt = revalidate_admission_reuse(
                    admission=replace(admission, **mutation),
                    current=current,
                )
                self.assertEqual(receipt.disposition, ReuseDisposition.HOLD_CLAIM_CEILING)

    def test_each_identity_bearing_axis_drifts_to_typed_hold(self) -> None:
        expected = (
            ("producer_head", "f" * 40, ReuseDisposition.HOLD_PRODUCER_GENERATION_CHANGED),
            ("subject_identity", "subject:drift", ReuseDisposition.HOLD_SUBJECT_CHANGED),
            ("source_generation_key", "source:drift", ReuseDisposition.HOLD_SOURCE_GENERATION_CHANGED),
            ("evidence_generation_key", "evidence:drift", ReuseDisposition.HOLD_EVIDENCE_GENERATION_CHANGED),
            ("owner_context_key", "owner:drift", ReuseDisposition.HOLD_OWNER_CONTEXT_CHANGED),
            ("decision_context_key", "decision:drift", ReuseDisposition.HOLD_DECISION_CONTEXT_CHANGED),
        )
        for family in AdmissionFamily:
            admission, current = fixture(family)
            for field, value, disposition in expected:
                receipt = revalidate_admission_reuse(
                    admission=admission,
                    current=replace(current, **{field: value}),
                )
                self.assertEqual(receipt.disposition, disposition, (family, field))
                self.assertFalse(receipt.reusable_candidate)

    def test_hold_receipts_do_not_echo_stale_identity_as_current(self) -> None:
        for family in AdmissionFamily:
            admission, current = fixture(family)
            receipt = revalidate_admission_reuse(
                admission=admission,
                current=replace(current, evidence_generation_key="evidence:new"),
            )
            self.assertIsNone(receipt.subject_identity)
            self.assertIsNone(receipt.source_generation_key)
            self.assertIsNone(receipt.evidence_generation_key)
            self.assertIsNone(receipt.owner_context_key)
            self.assertIsNone(receipt.decision_context_key)

    def test_receipt_is_deterministic(self) -> None:
        for family in AdmissionFamily:
            admission, current = fixture(family)
            a = revalidate_admission_reuse(admission=admission, current=current)
            b = revalidate_admission_reuse(admission=admission, current=current)
            self.assertEqual(a, b)
            self.assertEqual(a.reuse_digest, b.reuse_digest)
            self.assertEqual(len(a.reuse_digest), 64)

    def test_complete_two_family_128_state_different_j_lattice(self) -> None:
        self.assertEqual(prove_different_j(), 128)

    def test_family_pins_are_distinct_and_exact(self) -> None:
        self.assertNotEqual(
            EXPECTED_HEAD[AdmissionFamily.HYDRATION_TRANSACTION],
            EXPECTED_HEAD[AdmissionFamily.GLM53_BOUNDED_C2_PROPOSAL],
        )
        self.assertEqual(
            EXPECTED_POSITIVE_DISPOSITION[AdmissionFamily.HYDRATION_TRANSACTION],
            "ADMIT_BOUNDED_TRANSACTION",
        )
        self.assertEqual(
            EXPECTED_POSITIVE_DISPOSITION[AdmissionFamily.GLM53_BOUNDED_C2_PROPOSAL],
            "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE",
        )


if __name__ == "__main__":
    unittest.main()

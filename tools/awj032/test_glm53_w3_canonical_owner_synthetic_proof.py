from dataclasses import replace
import unittest

from tools.awj032.glm53_w3_canonical_owner_composite import compose_canonical_w3_admission
from tools.awj032.glm53_w3_official_producer_admission import evaluate_w3_official_producer_admission
from tools.awj032.glm53_w3_canonical_owner_synthetic_proof import (
    CANONICAL_PR406_NUMERICAL_EVIDENCE,
    CanonicalOwnerSyntheticProofError,
    prove_canonical_native_synthetic_w3,
)
from tools.awj032.test_glm53_w3_official_producer_admission import LowerPlan, metadata, security


class CanonicalOwnerSyntheticProofTests(unittest.TestCase):
    def admission(self):
        w3 = evaluate_w3_official_producer_admission(
            pager_plan=LowerPlan(),
            airllm_security_evidence=security(),
            glm53_metadata_evidence=metadata(),
        )
        return compose_canonical_w3_admission(w3_receipt=w3)

    def assert_code(self, expected, fn):
        with self.assertRaises(CanonicalOwnerSyntheticProofError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_canonical_owner_plus_discriminative_numerical_proof_closes_only_synthetic_w3(self):
        out = prove_canonical_native_synthetic_w3(canonical_owner_admission=self.admission())
        self.assertEqual("PROVEN_NATIVE_SYNTHETIC_W3_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertTrue(out.canonical_owner_admission_proven)
        self.assertTrue(out.native_selected_range_fixture_proven)
        self.assertTrue(out.independent_scale_semantic_oracle_proven)
        self.assertTrue(out.negative_scale_controls_proven)
        self.assertTrue(out.native_synthetic_w3_proven)
        self.assertFalse(out.official_tensor_compatibility_proven)
        self.assertFalse(out.official_tensor_payload_admitted)
        self.assertFalse(out.runtime_mtp_support_proven)
        self.assertFalse(out.runtime_execution_admitted)
        self.assertFalse(out.checkpoint_payload_admitted)
        self.assertFalse(out.quality_proven)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.provider_effect_admitted)
        self.assertFalse(out.authority)

    def test_mapping_cannot_impersonate_canonical_owner_receipt(self):
        self.assert_code(
            "PR427_CANONICAL_OWNER_ADMISSION_REQUIRED",
            lambda: prove_canonical_native_synthetic_w3(
                canonical_owner_admission=self.admission().to_dict()
            ),
        )

    def test_owner_coordinate_substitution_fails(self):
        changed = replace(self.admission(), pr421_report_logical_id="0" * 64)
        self.assert_code(
            "PR427_OWNER_COORDINATE_MISMATCH",
            lambda: prove_canonical_native_synthetic_w3(canonical_owner_admission=changed),
        )

    def test_owner_numerical_widening_fails(self):
        changed = replace(self.admission(), native_synthetic_w3_numerical_proven=True)
        self.assert_code(
            "PR427_EFFECT_CEILING_WIDENED:native_synthetic_w3_numerical_proven",
            lambda: prove_canonical_native_synthetic_w3(canonical_owner_admission=changed),
        )

    def test_pr406_semantic_head_substitution_fails(self):
        changed = replace(CANONICAL_PR406_NUMERICAL_EVIDENCE, semantic_head="0" * 40)
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: prove_canonical_native_synthetic_w3(
                canonical_owner_admission=self.admission(), numerical_evidence=changed
            ),
        )

    def test_pr406_test_blob_substitution_fails(self):
        changed = replace(CANONICAL_PR406_NUMERICAL_EVIDENCE, scale_oracle_test_blob="0" * 40)
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: prove_canonical_native_synthetic_w3(
                canonical_owner_admission=self.admission(), numerical_evidence=changed
            ),
        )

    def test_missing_negative_control_fails(self):
        changed = replace(
            CANONICAL_PR406_NUMERICAL_EVIDENCE,
            negative_controls_detected=CANONICAL_PR406_NUMERICAL_EVIDENCE.negative_controls_detected[:-1],
        )
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: prove_canonical_native_synthetic_w3(
                canonical_owner_admission=self.admission(), numerical_evidence=changed
            ),
        )

    def test_truthy_integer_cannot_impersonate_numerical_proof(self):
        changed = replace(CANONICAL_PR406_NUMERICAL_EVIDENCE, independent_scale_semantic_oracle_passed=1)
        self.assert_code(
            "PR406_REQUIRED_NUMERICAL_PROOF_MISSING:independent_scale_semantic_oracle_passed",
            lambda: prove_canonical_native_synthetic_w3(
                canonical_owner_admission=self.admission(), numerical_evidence=changed
            ),
        )

    def test_numerical_effect_widening_fails(self):
        changed = replace(CANONICAL_PR406_NUMERICAL_EVIDENCE, g2_admitted=True)
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: prove_canonical_native_synthetic_w3(
                canonical_owner_admission=self.admission(), numerical_evidence=changed
            ),
        )

    def test_receipt_is_deterministic(self):
        a = prove_canonical_native_synthetic_w3(canonical_owner_admission=self.admission())
        b = prove_canonical_native_synthetic_w3(canonical_owner_admission=self.admission())
        self.assertEqual(a.logical_id, b.logical_id)
        self.assertEqual(a.pr406_numerical_evidence_digest, b.pr406_numerical_evidence_digest)


if __name__ == "__main__":
    unittest.main()

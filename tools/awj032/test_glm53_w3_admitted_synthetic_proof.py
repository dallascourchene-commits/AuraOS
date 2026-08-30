import copy
import unittest

from tools.awj032.glm53_w3_admitted_synthetic_proof import (
    PR406_SEMANTIC_HEAD,
    PR414_VERIFIED_HEAD,
    W3AdmittedSyntheticProofError,
    compose_admitted_native_synthetic_w3_proof,
    verified_pr406_fixture_evidence,
)
from tools.awj032.glm53_w3_mtp_composite_admission import compose_w3_mtp_admission
from tools.awj032.test_glm53_w3_mtp_composite_admission import W3MTPCompositeAdmissionTests


class W3AdmittedSyntheticProofTests(unittest.TestCase):
    def admission(self):
        helper = W3MTPCompositeAdmissionTests()
        return compose_w3_mtp_admission(
            w3_receipt=helper.w3_receipt(),
            mtp_verified_report=helper.mtp_report(),
        )

    def fixture(self):
        return verified_pr406_fixture_evidence()

    def assert_code(self, expected, fn):
        with self.assertRaises(W3AdmittedSyntheticProofError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_exact_admission_plus_exact_fixture_evidence_proves_only_native_synthetic_w3(self):
        out = compose_admitted_native_synthetic_w3_proof(
            admission_receipt=self.admission(),
            fixture_evidence=self.fixture(),
        )
        self.assertEqual("PROVEN_NATIVE_SYNTHETIC_W3_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertTrue(out.official_w2_producer_proof_consumed)
        self.assertTrue(out.official_mtp_source_provenance_consumed)
        self.assertTrue(out.native_selected_range_fixture_proven)
        self.assertTrue(out.independent_scale_semantic_oracle_proven)
        self.assertTrue(out.negative_scale_controls_proven)
        self.assertTrue(out.native_synthetic_w3_proven)
        self.assertEqual(PR414_VERIFIED_HEAD, out.pr414_verified_head)
        self.assertEqual(PR406_SEMANTIC_HEAD, out.pr406_semantic_head)
        self.assertFalse(out.official_tensor_compatibility_proven)
        self.assertFalse(out.official_tensor_payload_admitted)
        self.assertFalse(out.runtime_mtp_support_proven)
        self.assertFalse(out.runtime_execution_admitted)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.provider_effect_admitted)
        self.assertFalse(out.quality_proven)
        self.assertFalse(out.authority)

    def test_admission_blocker_cannot_be_laundered(self):
        admission = self.admission().to_dict()
        admission["blockers"] = ["OTHER_BLOCKER"]
        self.assert_code(
            "W3_ADMISSION_BLOCKER_REMAINS",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=admission,
                fixture_evidence=self.fixture(),
            ),
        )

    def test_admission_effect_widening_fails(self):
        admission = self.admission().to_dict()
        admission["g2_admitted"] = True
        self.assert_code(
            "W3_EFFECT_CEILING_WIDENED:g2_admitted",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=admission,
                fixture_evidence=self.fixture(),
            ),
        )

    def test_admission_proof_loss_fails(self):
        admission = self.admission().to_dict()
        admission["official_mtp_source_provenance_consumed"] = False
        self.assert_code(
            "W3_REQUIRED_PROOF_MISSING:official_mtp_source_provenance_consumed",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=admission,
                fixture_evidence=self.fixture(),
            ),
        )

    def test_fixture_semantic_generation_substitution_fails(self):
        evidence = self.fixture().to_dict()
        evidence["semantic_head"] = "0" * 40
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=self.admission(),
                fixture_evidence=evidence,
            ),
        )

    def test_fixture_hosted_run_substitution_fails(self):
        evidence = self.fixture().to_dict()
        evidence["hosted_run_ref"] = "github-actions:run:0:job:0"
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=self.admission(),
                fixture_evidence=evidence,
            ),
        )

    def test_missing_discriminative_negative_control_fails(self):
        evidence = self.fixture().to_dict()
        evidence["negative_controls_detected"] = evidence["negative_controls_detected"][:-1]
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=self.admission(),
                fixture_evidence=evidence,
            ),
        )

    def test_fixture_effect_widening_fails(self):
        evidence = self.fixture().to_dict()
        evidence["official_tensor_payload_admitted"] = True
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=self.admission(),
                fixture_evidence=evidence,
            ),
        )

    def test_fixture_boolean_type_widening_fails(self):
        evidence = self.fixture().to_dict()
        evidence["independent_scale_semantic_oracle_passed"] = 1
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_admitted_native_synthetic_w3_proof(
                admission_receipt=self.admission(),
                fixture_evidence=evidence,
            ),
        )

    def test_receipt_is_deterministic(self):
        a = compose_admitted_native_synthetic_w3_proof(
            admission_receipt=self.admission(),
            fixture_evidence=copy.deepcopy(self.fixture().to_dict()),
        )
        b = compose_admitted_native_synthetic_w3_proof(
            admission_receipt=self.admission(),
            fixture_evidence=copy.deepcopy(self.fixture().to_dict()),
        )
        self.assertEqual(a.logical_id, b.logical_id)
        self.assertEqual(a.admission_receipt_digest, b.admission_receipt_digest)
        self.assertEqual(a.fixture_evidence_digest, b.fixture_evidence_digest)


if __name__ == "__main__":
    unittest.main()

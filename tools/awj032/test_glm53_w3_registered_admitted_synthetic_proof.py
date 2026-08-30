import copy
import unittest

from tools.awj032 import glm53_pr340_producer_snapshot_registry as registry
from tools.awj032.glm53_w3_proof_plane_admission_v2 import W3RegisteredAdmissionReceipt
from tools.awj032.glm53_w3_registered_admitted_synthetic_proof import (
    PR406_SEMANTIC_HEAD,
    PR412_REGISTERED_HEAD,
    W3RegisteredSyntheticProofError,
    compose_registered_native_synthetic_w3_proof,
    verified_pr406_fixture_evidence,
)


class W3RegisteredAdmittedSyntheticProofTests(unittest.TestCase):
    def admission(self):
        return W3RegisteredAdmissionReceipt(
            status="ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE",
            blockers=(),
            w2_consumer_receipt_id="1" * 64,
            official_w2_bound_plan_digest="2" * 64,
            pr340_registry_schema=registry.REGISTRY_SCHEMA,
            pr340_producer_execution_head=registry.PRODUCER_EXECUTION_HEAD,
            pr340_producer_run_id=registry.PRODUCER_RUN_ID,
            pr340_producer_job_id=registry.PRODUCER_JOB_ID,
            pr340_final_report_digest=registry.FINAL_REPORT_DIGEST,
            pr340_classification_stage_logical_id=registry.CLASSIFICATION_STAGE_LOGICAL_ID,
            pr340_snapshot_digest=registry.SNAPSHOT_DIGEST,
            official_mtp_source_evidence_id="b0803af6fdb7afd0dcdbf7c5b718605658a02534c960d965cfc1729eb4d9d3a2",
            official_mtp_source_bundle_id=registry.SOURCE_BUNDLE_ID,
        )

    def fixture(self):
        return verified_pr406_fixture_evidence()

    def assert_code(self, expected, fn):
        with self.assertRaises(W3RegisteredSyntheticProofError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_current_registered_admission_plus_discriminative_fixture_proves_only_native_synthetic_w3(self):
        out = compose_registered_native_synthetic_w3_proof(
            admission_receipt=self.admission(), fixture_evidence=self.fixture()
        )
        self.assertEqual("PROVEN_NATIVE_SYNTHETIC_W3_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertEqual(PR412_REGISTERED_HEAD, out.pr412_registered_head)
        self.assertEqual(PR406_SEMANTIC_HEAD, out.pr406_semantic_head)
        self.assertTrue(out.registered_producer_report_proven)
        self.assertTrue(out.registered_pr409_source_appraisal_proven)
        self.assertTrue(out.w2_producer_consumer_boundary_proven)
        self.assertTrue(out.native_selected_range_fixture_proven)
        self.assertTrue(out.independent_scale_semantic_oracle_proven)
        self.assertTrue(out.negative_scale_controls_proven)
        self.assertTrue(out.native_synthetic_w3_proven)
        self.assertFalse(out.official_tensor_compatibility_proven)
        self.assertFalse(out.official_tensor_payload_admitted)
        self.assertFalse(out.runtime_mtp_support_proven)
        self.assertFalse(out.runtime_execution_admitted)
        self.assertFalse(out.checkpoint_payload_admitted)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.provider_effect_admitted)
        self.assertFalse(out.quality_proven)
        self.assertFalse(out.authority)

    def test_pre_registry_composite_schema_is_rejected(self):
        admission = self.admission().to_dict()
        admission["schema"] = "AWJ032GLM53W3CompositeAdmissionV1"
        self.assert_code(
            "W3_REGISTERED_ADMISSION_SCHEMA_MISMATCH",
            lambda: compose_registered_native_synthetic_w3_proof(admission_receipt=admission),
        )

    def test_registered_coordinate_substitution_fails(self):
        admission = self.admission().to_dict()
        admission["pr340_snapshot_digest"] = "0" * 64
        self.assert_code(
            "W3_REGISTERED_COORDINATE_MISMATCH",
            lambda: compose_registered_native_synthetic_w3_proof(admission_receipt=admission),
        )

    def test_registered_proof_loss_fails(self):
        admission = self.admission().to_dict()
        admission["pr340_producer_report_registered"] = False
        self.assert_code(
            "W3_REQUIRED_REGISTERED_PROOF_MISSING:pr340_producer_report_registered",
            lambda: compose_registered_native_synthetic_w3_proof(admission_receipt=admission),
        )

    def test_admission_effect_widening_fails(self):
        admission = self.admission().to_dict()
        admission["runtime_mtp_support_proven"] = True
        self.assert_code(
            "W3_EFFECT_CEILING_WIDENED:runtime_mtp_support_proven",
            lambda: compose_registered_native_synthetic_w3_proof(admission_receipt=admission),
        )

    def test_admission_boolean_type_widening_fails(self):
        admission = self.admission().to_dict()
        admission["synthetic_tiny_fixture_admitted"] = 1
        self.assert_code(
            "W3_REQUIRED_REGISTERED_PROOF_MISSING:synthetic_tiny_fixture_admitted",
            lambda: compose_registered_native_synthetic_w3_proof(admission_receipt=admission),
        )

    def test_extra_admission_field_fails_closed(self):
        admission = self.admission().to_dict()
        admission["caller_expected_pr340_id"] = registry.CLASSIFICATION_STAGE_LOGICAL_ID
        self.assert_code(
            "W3_REGISTERED_ADMISSION_FIELD_SET_MISMATCH",
            lambda: compose_registered_native_synthetic_w3_proof(admission_receipt=admission),
        )

    def test_w2_receipt_identity_must_be_sha256_shaped(self):
        admission = self.admission().to_dict()
        admission["w2_consumer_receipt_id"] = "not-a-digest"
        self.assert_code(
            "W2_CONSUMER_RECEIPT_ID_INVALID",
            lambda: compose_registered_native_synthetic_w3_proof(admission_receipt=admission),
        )

    def test_fixture_semantic_generation_substitution_fails(self):
        evidence = self.fixture().to_dict()
        evidence["semantic_head"] = "0" * 40
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_registered_native_synthetic_w3_proof(
                admission_receipt=self.admission(), fixture_evidence=evidence
            ),
        )

    def test_missing_scale_negative_control_fails(self):
        evidence = self.fixture().to_dict()
        evidence["negative_controls_detected"] = evidence["negative_controls_detected"][:-1]
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_registered_native_synthetic_w3_proof(
                admission_receipt=self.admission(), fixture_evidence=evidence
            ),
        )

    def test_fixture_boolean_type_widening_fails(self):
        evidence = self.fixture().to_dict()
        evidence["independent_scale_semantic_oracle_passed"] = 1
        self.assert_code(
            "PR406_FIXTURE_EVIDENCE_MISMATCH",
            lambda: compose_registered_native_synthetic_w3_proof(
                admission_receipt=self.admission(), fixture_evidence=evidence
            ),
        )

    def test_receipt_is_deterministic(self):
        a = compose_registered_native_synthetic_w3_proof(
            admission_receipt=self.admission(),
            fixture_evidence=copy.deepcopy(self.fixture().to_dict()),
        )
        b = compose_registered_native_synthetic_w3_proof(
            admission_receipt=self.admission(),
            fixture_evidence=copy.deepcopy(self.fixture().to_dict()),
        )
        self.assertEqual(a.logical_id, b.logical_id)
        self.assertEqual(a.registered_admission_receipt_digest, b.registered_admission_receipt_digest)
        self.assertEqual(a.fixture_evidence_digest, b.fixture_evidence_digest)


if __name__ == "__main__":
    unittest.main()

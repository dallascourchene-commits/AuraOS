from dataclasses import replace
import inspect
import unittest

from tools.awj032.glm53_w3_canonical_owner_composite import compose_canonical_w3_admission
from tools.awj032.glm53_w3_live_canonical_owner_synthetic_proof import (
    CANONICAL_PR406_NUMERICAL_EVIDENCE,
    LiveCanonicalOwnerSyntheticProofError,
    _prove_from_admission,
    prove_live_canonical_native_synthetic_w3,
)
from tools.awj032.test_glm53_w3_official_producer_admission import (
    LowerPlan,
    metadata,
    security,
)


class LiveCanonicalOwnerSyntheticProofTests(unittest.TestCase):
    def admission(self):
        return compose_canonical_w3_admission(
            pager_plan=LowerPlan(),
            airllm_security_evidence=security(),
            glm53_metadata_evidence=metadata(),
        )

    def public_proof(self):
        return prove_live_canonical_native_synthetic_w3(
            pager_plan=LowerPlan(),
            airllm_security_evidence=security(),
            glm53_metadata_evidence=metadata(),
        )

    def assert_code(self, expected, fn):
        with self.assertRaises(LiveCanonicalOwnerSyntheticProofError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_public_path_live_traversal_closes_only_native_synthetic_w3(self):
        out = self.public_proof()
        self.assertEqual("PROVEN_NATIVE_SYNTHETIC_W3_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertTrue(out.live_pr410_public_traversal_proven)
        self.assertFalse(out.caller_serialized_pr410_receipt_accepted)
        self.assertFalse(out.caller_canonical_admission_accepted)
        self.assertFalse(out.caller_numerical_evidence_override_accepted)
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

    def test_public_signature_has_no_receipt_registry_or_numerical_override(self):
        params = tuple(inspect.signature(prove_live_canonical_native_synthetic_w3).parameters)
        self.assertEqual(
            ("pager_plan", "airllm_security_evidence", "glm53_metadata_evidence"),
            params,
        )
        for forbidden in (
            "w3_receipt",
            "canonical_owner_admission",
            "registry",
            "numerical_evidence",
        ):
            self.assertNotIn(forbidden, params)

    def test_serialized_or_prebuilt_admission_cannot_enter_public_boundary(self):
        admission = self.admission()
        with self.assertRaises(TypeError):
            prove_live_canonical_native_synthetic_w3(
                canonical_owner_admission=admission,
                pager_plan=LowerPlan(),
                airllm_security_evidence=security(),
                glm53_metadata_evidence=metadata(),
            )
        with self.assertRaises(TypeError):
            prove_live_canonical_native_synthetic_w3(
                w3_receipt=admission.to_dict(),
                pager_plan=LowerPlan(),
                airllm_security_evidence=security(),
                glm53_metadata_evidence=metadata(),
            )

    def test_public_numerical_override_is_not_an_api(self):
        with self.assertRaises(TypeError):
            prove_live_canonical_native_synthetic_w3(
                pager_plan=LowerPlan(),
                airllm_security_evidence=security(),
                glm53_metadata_evidence=metadata(),
                numerical_evidence=CANONICAL_PR406_NUMERICAL_EVIDENCE,
            )

    def test_private_reducer_rejects_mapping_as_canonical_admission(self):
        self.assert_code(
            "PR432_CANONICAL_OWNER_ADMISSION_REQUIRED",
            lambda: _prove_from_admission(
                self.admission().to_dict(), CANONICAL_PR406_NUMERICAL_EVIDENCE
            ),
        )

    def test_owner_coordinate_substitution_fails(self):
        changed = replace(self.admission(), pr421_report_logical_id="0" * 64)
        self.assert_code(
            "PR432_OWNER_COORDINATE_MISMATCH",
            lambda: _prove_from_admission(changed, CANONICAL_PR406_NUMERICAL_EVIDENCE),
        )

    def test_owner_numerical_widening_fails(self):
        changed = replace(self.admission(), native_synthetic_w3_numerical_proven=True)
        self.assert_code(
            "PR432_EFFECT_CEILING_WIDENED:native_synthetic_w3_numerical_proven",
            lambda: _prove_from_admission(changed, CANONICAL_PR406_NUMERICAL_EVIDENCE),
        )

    def test_pr406_semantic_head_substitution_fails(self):
        changed = replace(CANONICAL_PR406_NUMERICAL_EVIDENCE, semantic_head="0" * 40)
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: _prove_from_admission(self.admission(), changed),
        )

    def test_pr406_test_blob_substitution_fails(self):
        changed = replace(
            CANONICAL_PR406_NUMERICAL_EVIDENCE,
            scale_oracle_test_blob="0" * 40,
        )
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: _prove_from_admission(self.admission(), changed),
        )

    def test_missing_negative_control_fails(self):
        changed = replace(
            CANONICAL_PR406_NUMERICAL_EVIDENCE,
            negative_controls_detected=(
                CANONICAL_PR406_NUMERICAL_EVIDENCE.negative_controls_detected[:-1]
            ),
        )
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: _prove_from_admission(self.admission(), changed),
        )

    def test_truthy_integer_cannot_impersonate_numerical_proof(self):
        changed = replace(
            CANONICAL_PR406_NUMERICAL_EVIDENCE,
            independent_scale_semantic_oracle_passed=1,
        )
        self.assert_code(
            "PR406_REQUIRED_NUMERICAL_PROOF_MISSING:independent_scale_semantic_oracle_passed",
            lambda: _prove_from_admission(self.admission(), changed),
        )

    def test_numerical_effect_widening_fails(self):
        changed = replace(CANONICAL_PR406_NUMERICAL_EVIDENCE, g2_admitted=True)
        self.assert_code(
            "PR406_NUMERICAL_EVIDENCE_MISMATCH",
            lambda: _prove_from_admission(self.admission(), changed),
        )

    def test_receipt_is_deterministic(self):
        a = self.public_proof()
        b = self.public_proof()
        self.assertEqual(a.logical_id, b.logical_id)
        self.assertEqual(a.pr406_numerical_evidence_digest, b.pr406_numerical_evidence_digest)


if __name__ == "__main__":
    unittest.main()

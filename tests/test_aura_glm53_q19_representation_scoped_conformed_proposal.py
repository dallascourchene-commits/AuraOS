from __future__ import annotations

from copy import deepcopy
import unittest

from tools.quantization import aura_glm53_q19_representation_scoped_conformed_proposal as q19


def q6_fixture(outcome: str = "E8_WIN") -> dict:
    role_outcome = outcome
    return {
        "schema": q19.Q6_SCHEMA,
        "receipt_digest": q19.Q6_RECEIPT_DIGEST,
        "official_repository": "zai-org/GLM-5.3",
        "official_revision": "7cda81930d6e4cef42f48555de830aa32ecdde28",
        "selected_layer": 3,
        "selected_expert": 0,
        "q14_canary_page_set_digest": "4" * 64,
        "q14_representation_scheme": "AURA_E8_BALL10_16BIT_REF_V1",
        "scalar_scheme": "AURA_OPT_SYMMETRIC_4LEVEL_FP16_V1",
        "scalar_representation_digest": "5" * 64,
        "exact_codec_rate_bpw": 2.25,
        "codec_rate_domain_only": True,
        "container_rate_comparison_claimed": False,
        "aggregate_outcome": outcome,
        "same_official_source_tiles_compared": True,
        "optimized_scalar_control_used": True,
        "official_source_equal_rate_distortion_evidence": True,
        "representative_canary_scope_only": True,
        "geometry_privileged": False,
        "full_role_quantized": False,
        "whole_model_quantized": False,
        "glm_quality_proven": False,
        "runtime_performance_proven": False,
        "semantic_k27_authority": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
        "roles": [
            {
                "tensor_role": "down_proj",
                "equal_codec_rate": True,
                "equal_codec_payload_bytes": True,
                "q14_e8_codec_payload_bytes": 18,
                "scalar_codec_payload_bytes": 18,
                "q14_e8_codec_bits_per_weight": 2.25,
                "scalar_codec_bits_per_weight": 2.25,
                "q14_e8_serialized_bits_per_weight": 42.25,
                "container_rate_comparison_claimed": False,
                "outcome": role_outcome,
            },
            {
                "tensor_role": "gate_up_proj",
                "equal_codec_rate": True,
                "equal_codec_payload_bytes": True,
                "q14_e8_codec_payload_bytes": 18,
                "scalar_codec_payload_bytes": 18,
                "q14_e8_codec_bits_per_weight": 2.25,
                "scalar_codec_bits_per_weight": 2.25,
                "q14_e8_serialized_bits_per_weight": 42.25,
                "container_rate_comparison_claimed": False,
                "outcome": role_outcome,
            },
        ],
    }


class Q19RepresentationScopedProposalTests(unittest.TestCase):
    def admit(self, fixture: dict | None = None, **kwargs):
        return q19.admit_representation_scoped_proposal(
            fixture or q6_fixture(),
            source_gate_passed=kwargs.pop("source_gate_passed", True),
            source_gate_generation=kwargs.pop("source_gate_generation", q19.S1_HEAD),
            require_exact_current=kwargs.pop("require_exact_current", True),
            **kwargs,
        )

    def test_exact_e8_win_and_green_source_gate_is_bounded_proposal_eligible(self):
        result = self.admit()
        self.assertTrue(result.proposal_eligible)
        self.assertEqual(result.generic_disposition, "ELIGIBLE_BOUNDED_PROPOSAL")
        self.assertEqual(result.reason, "REPRESENTATION_SCOPED_BOUNDED_PROPOSAL_ELIGIBLE")
        self.assertIsNotNone(result.proposal_basis_digest)
        self.assertFalse(result.q18_1p25_proposal_mutated)
        self.assertFalse(result.q18_evidence_crosscast_into_q19)

    def test_failed_source_gate_dominates_favorable_q6_evidence(self):
        result = self.admit(
            source_gate_passed=False,
            source_blocker="SOURCE_HEADER_CURRENTNESS_REQUIRED",
        )
        self.assertFalse(result.proposal_eligible)
        self.assertEqual(result.generic_disposition, "HOLD_HARD_GATE")
        self.assertEqual(result.reason, "HOLD_SOURCE_GATE")
        self.assertIsNone(result.proposal_basis_digest)

    def test_scalar_win_maps_to_generic_opposing_evidence(self):
        result = self.admit(q6_fixture("SCALAR_WIN"))
        self.assertFalse(result.proposal_eligible)
        self.assertEqual(result.generic_disposition, "STOP_OPPOSING_EVIDENCE")

    def test_tie_maps_to_generic_no_positive_evidence(self):
        result = self.admit(q6_fixture("TIE"))
        self.assertFalse(result.proposal_eligible)
        self.assertEqual(result.generic_disposition, "STOP_NO_POSITIVE_EVIDENCE")

    def test_container_rate_crosscast_is_rejected(self):
        fixture = q6_fixture()
        fixture["container_rate_comparison_claimed"] = True
        with self.assertRaisesRegex(ValueError, "Q6_CONTAINER_RATE_CROSSCAST"):
            self.admit(fixture)

    def test_nominal_rate_without_codec_domain_is_rejected(self):
        fixture = q6_fixture()
        fixture["codec_rate_domain_only"] = False
        with self.assertRaisesRegex(ValueError, "Q6_CODEC_RATE_DOMAIN_REQUIRED"):
            self.admit(fixture)

    def test_role_payload_rate_drift_is_rejected(self):
        fixture = q6_fixture()
        fixture["roles"][0]["q14_e8_codec_payload_bytes"] = 338
        with self.assertRaisesRegex(ValueError, "Q6_ROLE_EXACT_18_BYTE_CODEC_REQUIRED"):
            self.admit(fixture)

    def test_serialized_container_must_remain_a_distinct_domain(self):
        fixture = q6_fixture()
        fixture["roles"][0]["q14_e8_serialized_bits_per_weight"] = 2.25
        with self.assertRaisesRegex(ValueError, "Q6_ROLE_CONTAINER_DOMAIN_NOT_DISTINCT"):
            self.admit(fixture)

    def test_widened_scientific_claim_is_rejected(self):
        fixture = q6_fixture()
        fixture["glm_quality_proven"] = True
        with self.assertRaisesRegex(ValueError, "Q6_CLAIM_CEILING_WIDENED:glm_quality_proven"):
            self.admit(fixture)

    def test_wrong_q6_receipt_is_rejected_in_exact_mode(self):
        fixture = q6_fixture()
        fixture["receipt_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Q6_RECEIPT_DIGEST_MISMATCH"):
            self.admit(fixture)

    def test_wrong_source_generation_is_rejected_in_exact_mode(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_GATE_GENERATION_NOT_EXACT_S1"):
            self.admit(source_gate_generation="different-generation")

    def test_deterministic_representation_and_proposal_identity(self):
        first = self.admit()
        second = self.admit(deepcopy(q6_fixture()))
        self.assertEqual(first.representation_identity_digest, second.representation_identity_digest)
        self.assertEqual(first.proposal_basis_digest, second.proposal_basis_digest)
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_authority_ceiling_is_fixed_false(self):
        result = self.admit()
        for key in (
            "full_tensor_or_model_scope_granted", "model_quality_proven",
            "runtime_performance_proven", "execution_authority_granted",
            "effect_authority_granted", "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed", "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(result, key), key)


if __name__ == "__main__":
    unittest.main()

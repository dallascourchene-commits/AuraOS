from __future__ import annotations

import math
import unittest

from tools.quantization.aura_glm53_lattice_quantization_feasibility import (
    D4_NSM,
    E8_NSM,
    LEECH24_NSM,
    SCALAR_Z_NSM,
    GLM53_HF_PARAMETER_COUNT,
    build_feasibility_receipt,
    decode_e8,
    doubled_lattice_coordinates,
    indexed_vq_bpw,
    pasted_int8_cast,
    pasted_weight_representation_bpw,
    phase_only_attention_counterexample,
    static_weight_bytes,
)


class LatticeQuantizationFeasibilityTests(unittest.TestCase):
    def test_e8_half_integer_coset_is_real_and_pasted_int8_cast_destroys_it(self):
        point = decode_e8((0.5,) * 8)
        self.assertEqual(point, (0.5,) * 8)
        self.assertEqual(pasted_int8_cast(point), (0,) * 8)
        self.assertNotEqual(tuple(float(v) for v in pasted_int8_cast(point)), point)

    def test_doubled_integer_coordinates_preserve_e8_half_coset(self):
        point = decode_e8((0.5,) * 8)
        doubled = doubled_lattice_coordinates(point)
        self.assertEqual(doubled, (1,) * 8)
        self.assertEqual(tuple(v / 2 for v in doubled), point)

    def test_pasted_representation_is_8_25_bpw_not_two_bit(self):
        self.assertAlmostEqual(pasted_weight_representation_bpw(64, 16), 8.25)
        self.assertGreater(pasted_weight_representation_bpw(64, 16), 8.0)

    def test_real_indexed_vq_must_account_for_index_and_scale_bits(self):
        # Example only: an 18-bit index over each 8-D vector + FP16 scale / 64 weights.
        self.assertAlmostEqual(indexed_vq_bpw(18, 8, 64, 16), 2.5)
        with self.assertRaises(ValueError):
            indexed_vq_bpw(18, 8, 63, 16)

    def test_pasted_e8_normalized_second_moment_is_actually_leech_like(self):
        self.assertGreater(SCALAR_Z_NSM, D4_NSM)
        self.assertGreater(D4_NSM, E8_NSM)
        self.assertGreater(E8_NSM, LEECH24_NSM)
        self.assertFalse(math.isclose(E8_NSM, 0.0658, abs_tol=1e-6))
        self.assertTrue(math.isclose(LEECH24_NSM, 0.0658, abs_tol=5e-5))

    def test_phase_only_kv_normalization_does_not_preserve_attention_logits(self):
        witness = phase_only_attention_counterexample()
        self.assertTrue(witness["original_logits_distinct"])
        self.assertTrue(witness["phase_only_logits_collide"])
        self.assertEqual(witness["original_small_logit"], 1.0)
        self.assertEqual(witness["original_large_logit"], 4.0)
        self.assertEqual(witness["phase_only_small_logit"], 1.0)
        self.assertEqual(witness["phase_only_large_logit"], 1.0)

    def test_glm53_static_storage_arithmetic_precludes_full_model_under_32gb_at_two_bits(self):
        two_bit = static_weight_bytes(GLM53_HF_PARAMETER_COUNT, 2.0)
        self.assertEqual(two_bit, 188_332_475_000)
        self.assertGreater(two_bit, 32_000_000_000)
        self.assertEqual(static_weight_bytes(GLM53_HF_PARAMETER_COUNT, 8.0), 753_329_900_000)

    def test_receipt_preserves_feasible_mechanisms_without_promoting_unearned_claims(self):
        r = build_feasibility_receipt()
        self.assertTrue(r.lattice_vq_mechanism_feasible)
        self.assertTrue(r.practical_sub4bit_requires_finite_index_or_equivalent_coding)
        self.assertFalse(r.practical_sub2bit_glm53_quality_proven)
        self.assertFalse(r.pasted_int8_preserves_half_coset)
        self.assertFalse(r.pasted_e8_nsm_matches_reference)
        self.assertFalse(r.toroidal_phase_only_kv_preserves_attention_logits)
        self.assertTrue(r.magnitude_must_be_preserved_or_accounted_for)
        self.assertTrue(r.rope_aware_kv_quantization_is_viable_research_direction)
        self.assertTrue(r.expert_wise_mixed_precision_is_viable_moe_direction)
        self.assertFalse(r.coordinate_address_is_physical_sector_proof)
        self.assertFalse(r.out_of_core_expert_streaming_proven_on_owner_host)
        self.assertFalse(r.native_private_transformer_kv_accessed)
        self.assertFalse(r.semantic_k27_authority_minted)
        self.assertFalse(r.model_execution_performed)
        self.assertFalse(r.deployment_authorized)
        self.assertEqual(len(r.digest), 64)


if __name__ == "__main__":
    unittest.main()

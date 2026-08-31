from __future__ import annotations

from dataclasses import replace
import unittest

from tools.quantization.aura_glm53_quantization_evidence_transfer import (
    Q4_CODEC_BPW,
    Q4_CODEBOOK_SHA256,
    Q4_INDEX_BITS,
    Q4_SCHEME,
    Q5_EXACT_HEAD,
    Q5_EXACT_RUN,
    SYNTHETIC_DISTORTION_SCOPE,
    QuantizationEvidence,
    classify_evidence_transfer,
    q4_representation_identity,
    q4_synthetic_evidence,
    q4_to_q5_disposition,
    q5_representation_identity,
)


class QuantizationEvidenceTransferTests(unittest.TestCase):
    def test_q4_exact_identity_is_frozen(self):
        q4 = q4_representation_identity()
        self.assertEqual(q4.scheme, Q4_SCHEME)
        self.assertEqual(q4.codebook_digest, Q4_CODEBOOK_SHA256)
        self.assertEqual(q4.index_bits_per_vector, Q4_INDEX_BITS)
        self.assertEqual(q4.codec_bits_per_weight, Q4_CODEC_BPW)
        self.assertEqual(len(q4.identity_digest), 64)

    def test_q5_identity_is_concrete_page_projection(self):
        q5 = q5_representation_identity()
        self.assertTrue(q5.scheme.startswith("AURA_E8_"))
        self.assertEqual(q5.vector_dim, 8)
        self.assertEqual(q5.index_bits_per_vector, 16)
        self.assertAlmostEqual(q5.codec_bits_per_weight, 2.25)
        self.assertEqual(Q5_EXACT_HEAD, "e342b5c1ab1dc51cb0c3d9b79b8fa3b83cae7192")
        self.assertEqual(Q5_EXACT_RUN, 33369222880)

    def test_q4_synthetic_win_does_not_transfer_to_q5(self):
        out = q4_to_q5_disposition()
        self.assertFalse(out.exact_representation_identity_match)
        self.assertTrue(out.geometry_family_label_match)
        self.assertEqual(out.disposition, "DIFFERENT_REPRESENTATION_NO_EVIDENCE_TRANSFER")
        self.assertFalse(out.synthetic_distortion_evidence_transferable)
        self.assertFalse(out.glm53_tensor_gain_inherited)
        self.assertFalse(out.coding_quality_inherited)
        self.assertFalse(out.runtime_performance_inherited)

    def test_exact_q4_self_identity_transfers_only_synthetic_scope(self):
        evidence = q4_synthetic_evidence()
        out = classify_evidence_transfer(source=evidence, target=evidence.representation)
        self.assertTrue(out.exact_representation_identity_match)
        self.assertTrue(out.synthetic_distortion_evidence_transferable)
        self.assertEqual(out.disposition, "SAME_REPRESENTATION_SYNTHETIC_EVIDENCE_ONLY")
        self.assertFalse(out.glm53_tensor_gain_inherited)
        self.assertFalse(out.coding_quality_inherited)
        self.assertFalse(out.runtime_performance_inherited)

    def test_same_scheme_with_codebook_drift_rejects_transfer(self):
        evidence = q4_synthetic_evidence()
        target = replace(evidence.representation, codebook_digest="0" * 64)
        out = classify_evidence_transfer(source=evidence, target=target)
        self.assertFalse(out.exact_representation_identity_match)
        self.assertFalse(out.synthetic_distortion_evidence_transferable)

    def test_same_codebook_with_rate_drift_rejects_transfer(self):
        evidence = q4_synthetic_evidence()
        target = replace(evidence.representation, codec_bits_per_weight=2.25)
        out = classify_evidence_transfer(source=evidence, target=target)
        self.assertFalse(out.exact_representation_identity_match)
        self.assertFalse(out.synthetic_distortion_evidence_transferable)

    def test_same_geometry_family_is_not_same_representation(self):
        out = q4_to_q5_disposition()
        self.assertTrue(out.geometry_family_label_match)
        self.assertNotEqual(out.source_representation_digest, out.target_representation_digest)

    def test_synthetic_evidence_cannot_claim_model_or_runtime_planes(self):
        q4 = q4_representation_identity()
        for kwargs in (
            {"glm53_tensor_evidence": True, "coding_quality_evidence": False, "runtime_evidence": False},
            {"glm53_tensor_evidence": False, "coding_quality_evidence": True, "runtime_evidence": False},
            {"glm53_tensor_evidence": False, "coding_quality_evidence": False, "runtime_evidence": True},
        ):
            bad = QuantizationEvidence(
                representation=q4,
                evidence_scope=SYNTHETIC_DISTORTION_SCOPE,
                evidence_receipt_digest="a" * 64,
                **kwargs,
            )
            with self.assertRaisesRegex(ValueError, "SYNTHETIC_SCOPE_CANNOT_CLAIM_MODEL_OR_RUNTIME_EVIDENCE"):
                bad.validate()

    def test_successful_disposition_remains_nonauthorizing(self):
        out = q4_to_q5_disposition()
        self.assertFalse(out.semantic_k27_authority_minted)
        self.assertFalse(out.gate10_promoted)
        self.assertEqual(len(out.disposition_digest), 64)


if __name__ == "__main__":
    unittest.main()

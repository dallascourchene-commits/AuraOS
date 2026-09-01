from dataclasses import replace
import unittest

from tools.awj032 import glm53_g8_source_revalidation_bound_owner_host_request as g8
from tools.awj032 import test_glm53_g6_gate10_owner_host_evidence_request as g6t


class G8SourceRevalidationBoundOwnerHostRequestProofTests(unittest.TestCase):
    def _bind(self, **changes):
        args = dict(
            reuse=g6t.reuse(),
            provenance=g6t.provenance(),
            source=g6t.source(),
            owner=g6t.owner(),
            evidence=g6t.evidence(),
        )
        args.update(changes)
        return g8.bind_source_revalidation_to_owner_host_request(**args)

    def test_positive_is_source_bound_request_candidate_only(self):
        receipt = self._bind()
        self.assertEqual(receipt.disposition, g8.CANDIDATE)
        self.assertTrue(receipt.g6_request_compiled)
        self.assertTrue(receipt.q20_source_revalidation_candidate_bound)
        self.assertTrue(receipt.request_source_relation_bound)
        self.assertTrue(receipt.q20_exact_observation_generation_bound)
        self.assertTrue(receipt.future_effect_source_revalidation_required)
        for field in (
            "source_currentness_proven_by_this_contract",
            "source_currentness_at_future_effect_proven",
            "tensor_payload_bound",
            "model_execution_observed",
            "owner_host_execution_observed",
            "physical_io_observed",
            "execution_authorized",
            "effect_authorized",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            self.assertFalse(getattr(receipt, field), field)

    def test_receipt_is_deterministic(self):
        self.assertEqual(self._bind().receipt_digest, self._bind().receipt_digest)

    def test_wrong_repository_fails_closed_through_g6(self):
        receipt = self._bind(source=replace(g6t.source(), repository="example/not-glm"))
        self.assertEqual(receipt.disposition, g8.HOLD_G6)
        self.assertFalse(receipt.request_compile_source_revalidation_evidence_bound)

    def test_public_api_does_not_accept_parent_receipts(self):
        self.assertEqual(
            g8.public_api_parameters(),
            ("reuse", "provenance", "source", "owner", "evidence"),
        )

    def test_complete_different_j_lattice(self):
        self.assertEqual(g8.prove_different_j(), 128)

    def test_parent_q20_receipt_is_reconstructed_not_caller_supplied(self):
        receipt = g8._q20_receipt()
        self.assertEqual(receipt["receipt_digest"], g8.Q20_RECEIPT_DIGEST)
        self.assertEqual(receipt["disposition"], g8.q20.CANDIDATE)

    def test_laws_preserve_currentness_and_kv_boundary(self):
        self.assertIn("CompileTimeSourceRevalidation!=EffectTimeSourceCurrentness", g8.LAWS)
        self.assertIn("CoordinateMemory!=MODEL_PREFIX_KV", g8.LAWS)


if __name__ == "__main__":
    unittest.main()

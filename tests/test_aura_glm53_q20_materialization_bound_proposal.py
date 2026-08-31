from __future__ import annotations

from dataclasses import replace
import unittest

from tools.quantization import aura_glm53_q20_materialization_bound_proposal as q20


class Q20MaterializationBoundProposalTests(unittest.TestCase):
    def bind(self, **kwargs):
        params = dict(
            q19=q20.Q19ProposalRef(),
            q15=q20.Q15MaterializationRef(),
            q6_receipt_digest=q20.Q6_RECEIPT_DIGEST,
            q6_page_set_digest=q20.Q15_PAGE_SET_DIGEST,
            accounting_domain=q20.ACCOUNTING_DOMAIN,
            exact_codec_rate_bpw=q20.EXACT_CODEC_RATE_BPW,
        )
        params.update(kwargs)
        return q20.bind_materialization_to_proposal(**params)

    def test_exact_terminal_pair_binds_materialization_to_q19_proposal(self):
        r = self.bind()
        self.assertTrue(r.same_materialized_page_set_bound)
        self.assertTrue(r.execution_qualified_materialization_bound)
        self.assertTrue(r.q19_proposal_basis_preserved)
        self.assertTrue(r.q18_proposal_identity_preserved)
        self.assertEqual(r.reason, "EXECUTION_QUALIFIED_PORTABLE_MATERIALIZATION_BOUND_TO_REPRESENTATION_PROPOSAL_BASIS")

    def test_q6_q15_page_set_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Q6_Q15_PAGE_SET_RELATION_NOT_BOUND"):
            self.bind(q6_page_set_digest="0" * 64)

    def test_wrong_q6_receipt_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Q6_EXACT_RECEIPT_REQUIRED"):
            self.bind(q6_receipt_digest="0" * 64)

    def test_wrong_q19_terminal_generation_fails_closed(self):
        bad = replace(q20.Q19ProposalRef(), head="0" * 40)
        with self.assertRaisesRegex(ValueError, "Q19_EXACT_TERMINAL_GENERATION_REQUIRED"):
            self.bind(q19=bad)

    def test_q19_proposal_basis_tamper_fails_closed(self):
        bad = replace(q20.Q19ProposalRef(), proposal_basis_digest="0" * 64)
        with self.assertRaisesRegex(ValueError, "Q19_EXACT_TERMINAL_GENERATION_REQUIRED"):
            self.bind(q19=bad)

    def test_q15_artifact_substitution_fails_closed(self):
        bad = replace(q20.Q15MaterializationRef(), artifact_digest="sha256:" + "0" * 64)
        with self.assertRaisesRegex(ValueError, "Q15_EXACT_TERMINAL_MATERIALIZATION_GENERATION_REQUIRED"):
            self.bind(q15=bad)

    def test_q15_execution_qualification_must_be_true(self):
        bad = replace(q20.Q15MaterializationRef(), execution_qualified_portable_materialization_evidence=False)
        with self.assertRaisesRegex(ValueError, "Q15_EXECUTION_QUALIFIED_MATERIALIZATION_REQUIRED"):
            self.bind(q15=bad)

    def test_q15_claim_widening_is_rejected(self):
        bad = replace(q20.Q15MaterializationRef(), model_execution_proven=True)
        with self.assertRaisesRegex(ValueError, "Q15_CLAIM_CEILING_WIDENED"):
            self.bind(q15=bad)

    def test_codec_container_crosscast_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Q20_CODEC_ACCOUNTING_DOMAIN_REQUIRED"):
            self.bind(accounting_domain="SERIALIZED_PAGE_CONTAINER")

    def test_rate_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Q20_CODEC_RATE_MISMATCH"):
            self.bind(exact_codec_rate_bpw=1.25)

    def test_q18_mutation_or_crosscast_is_rejected(self):
        for field in ("q18_1p25_proposal_mutated", "q18_evidence_crosscast_into_q19"):
            bad = replace(q20.Q19ProposalRef(), **{field: True})
            with self.assertRaisesRegex(ValueError, "Q19_Q18_COLLISION_BOUNDARY_DRIFT"):
                self.bind(q19=bad)

    def test_provider_execution_never_becomes_proposal_execution_authority(self):
        r = self.bind()
        self.assertFalse(r.q15_provider_execution_is_proposal_execution_authority)
        for field in (
            "model_execution_proven", "inference_proven", "model_quality_or_runtime_proven",
            "execution_authority_granted", "effect_authority_granted", "semantic_k27_authority",
            "native_private_transformer_kv_accessed", "gate10_promoted", "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(r, field), field)

    def test_binding_is_deterministic_and_content_addressed(self):
        a = self.bind()
        b = self.bind()
        self.assertEqual(a.materialization_relation_digest, b.materialization_relation_digest)
        self.assertEqual(a.materialization_bound_proposal_basis_digest, b.materialization_bound_proposal_basis_digest)
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(len(a.materialization_relation_digest), 64)
        self.assertEqual(len(a.materialization_bound_proposal_basis_digest), 64)


if __name__ == "__main__":
    unittest.main()

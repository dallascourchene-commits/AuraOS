from dataclasses import replace
import unittest

import tools.quantization.aura_glm53_q19_q8_producer_evidence_request as m


class Q19ProducerEvidenceRequestTests(unittest.TestCase):
    def q18(self):
        return m.current_q18_receipt()

    def nav14(self):
        return m.nav14_projection_fixture()

    def test_exact_current_parents_issue_request_only(self):
        r = m.issue_q8_producer_evidence_request(q18=self.q18(), nav14=self.nav14())
        self.assertTrue(r.request_ready)
        self.assertEqual(r.disposition, m.RequestDisposition.READY)
        self.assertEqual(r.required_witnesses, m.Q8_REQUIRED_WITNESSES)
        self.assertFalse(r.cross_domain_source_relation_proven)
        self.assertFalse(r.official_source_tensor_payload_observed)
        self.assertFalse(r.exact_official_tensor_to_concrete_source_tensor_set_relation_proven)
        self.assertFalse(r.candidate_page_materialization_owner_receipt_observed)
        self.assertFalse(r.baseline_same_official_source_tensor_set_relation_proven)
        self.assertFalse(r.tensor_payload_bound)
        self.assertFalse(r.real_tensor_quantization_observed)
        self.assertFalse(r.model_execution_observed)
        self.assertFalse(r.execution_authorized)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.semantic_k27_authority_minted)
        self.assertFalse(r.native_private_transformer_kv_accessed)
        self.assertFalse(r.gate10_promoted)

    def test_q18_receipt_tamper_is_rejected_not_held_as_current(self):
        q18 = self.q18()
        q18["receipt_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Q18_RECEIPT_IDENTITY_MISMATCH"):
            m.issue_q8_producer_evidence_request(q18=q18, nav14=self.nav14())

    def test_q18_claim_widening_breaks_exact_semantic_surface(self):
        q18 = self.q18()
        q18["tensor_payload_bound"] = True
        with self.assertRaisesRegex(ValueError, "Q18_EXACT_SEMANTIC_SURFACE_MISMATCH"):
            m.issue_q8_producer_evidence_request(q18=q18, nav14=self.nav14())

    def test_nav14_parent_head_mismatch_holds(self):
        r = m.issue_q8_producer_evidence_request(
            q18=self.q18(), nav14=replace(self.nav14(), parent_head="f" * 40)
        )
        self.assertEqual(r.disposition, m.RequestDisposition.HOLD_NAV14_PARENT)
        self.assertFalse(r.request_ready)

    def test_nav14_proof_coordinate_mismatch_holds(self):
        r = m.issue_q8_producer_evidence_request(
            q18=self.q18(), nav14=replace(self.nav14(), proof_job=m.NAV14_PROOF_JOB + 1)
        )
        self.assertEqual(r.disposition, m.RequestDisposition.HOLD_NAV14_PARENT)

    def test_nav14_nonready_disposition_holds(self):
        r = m.issue_q8_producer_evidence_request(
            q18=self.q18(), nav14=replace(self.nav14(), disposition="HOLD_PURPOSE_MISMATCH")
        )
        self.assertEqual(r.disposition, m.RequestDisposition.HOLD_NAV14_NOT_READY)

    def test_nav14_claim_widening_holds(self):
        r = m.issue_q8_producer_evidence_request(
            q18=self.q18(), nav14=replace(self.nav14(), evidence_admitted=True)
        )
        self.assertEqual(r.disposition, m.RequestDisposition.HOLD_CLAIM_CEILING)
        self.assertFalse(r.request_ready)

    def test_nav14_identity_fields_are_shape_checked(self):
        with self.assertRaisesRegex(ValueError, "NAV14_MATERIAL_DIGEST_INVALID"):
            m.issue_q8_producer_evidence_request(
                q18=self.q18(), nav14=replace(self.nav14(), material_digest="not-a-digest")
            )
        with self.assertRaisesRegex(ValueError, "NAV14_SOURCE_URI_INVALID"):
            m.issue_q8_producer_evidence_request(
                q18=self.q18(), nav14=replace(self.nav14(), exact_source_uri="")
            )

    def test_cross_domain_equality_is_not_required_or_inferred(self):
        q18 = self.q18()
        nav14 = replace(
            self.nav14(),
            material_digest="a" * 64,
            subject_key="b" * 64,
            evidence_generation_key="c" * 64,
            exact_source_uri="https://different.example/material.bin",
        )
        self.assertNotEqual(q18["source_set_digest"], nav14.material_digest)
        r = m.issue_q8_producer_evidence_request(q18=q18, nav14=nav14)
        self.assertTrue(r.request_ready)
        self.assertFalse(r.cross_domain_source_relation_proven)
        self.assertFalse(r.tensor_payload_bound)

    def test_request_identity_changes_with_nav14_domain(self):
        a = m.issue_q8_producer_evidence_request(q18=self.q18(), nav14=self.nav14())
        b = m.issue_q8_producer_evidence_request(
            q18=self.q18(), nav14=replace(self.nav14(), material_digest="e" * 64)
        )
        self.assertNotEqual(a.request_digest, b.request_digest)

    def test_request_is_deterministic(self):
        a = m.issue_q8_producer_evidence_request(q18=self.q18(), nav14=self.nav14())
        b = m.issue_q8_producer_evidence_request(q18=self.q18(), nav14=self.nav14())
        self.assertEqual(a, b)

    def test_q8_witness_contract_is_exact_and_noncollapsible(self):
        self.assertEqual(
            m.Q8_REQUIRED_WITNESSES,
            (
                "OFFICIAL_SOURCE_TENSOR_PAYLOAD_OBSERVATION",
                "EXACT_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION",
                "CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT",
                "BASELINE_SAME_OFFICIAL_SOURCE_TENSOR_SET_RELATION",
            ),
        )
        r = m.issue_q8_producer_evidence_request(q18=self.q18(), nav14=self.nav14())
        self.assertEqual(len(r.required_witnesses), 4)

    def test_complete_different_j_matrix(self):
        self.assertEqual(m.prove_different_j(), 32)


if __name__ == "__main__":
    unittest.main()

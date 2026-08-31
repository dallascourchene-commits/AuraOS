from __future__ import annotations

from copy import deepcopy
import unittest

from tools.quantization import aura_glm53_domain_product_gate_conformance as q17


def q8_fixture(*, outcome="E8_WIN", gate=False):
    if not gate:
        disposition = "SOURCE_ADMISSION_HOLD"
        reason = "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED"
        proposal = False
    elif outcome == "E8_WIN":
        disposition = "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"
        reason = "REPRESENTATIVE_EQUAL_RATE_E8_ADVANTAGE_AND_SOURCE_REQUEST_GATE_GREEN"
        proposal = True
    else:
        disposition = "STOP_E8_ESCALATION_NO_REPRESENTATIVE_ADVANTAGE"
        reason = f"REPRESENTATIVE_{outcome}"
        proposal = False
    return {
        "schema": "AURA_CANARY_RESULT_SOURCE_C2_WORK_ADMISSION_V1",
        "receipt_digest": "a" * 64,
        "exact_other_agent_heads": ["x", "y"],
        "exact_other_agent_runs": [1, 2],
        "q5_receipt_digest": "b" * 64,
        "representative_outcome": outcome,
        "source_bound_c2_request_admissible": gate,
        "disposition": disposition,
        "reason": reason,
        "c2_request_proposal_eligible": proposal,
        "representative_evidence_only": True,
        "source_tensor_payload_bound": False,
        "real_tensor_quantization_eligible": False,
        "execution_authorized": False,
        "owner_host_execution_observed": False,
        "physical_io_attested": False,
        "quality_superiority_proven": False,
        "runtime_superiority_proven": False,
        "full_tensor_superiority_proven": False,
        "whole_model_superiority_proven": False,
        "g2_admitted": False,
        "gate10_promoted": False,
        "semantic_k27_authority": False,
        "native_private_transformer_kv_accessed": False,
    }


class DomainProductGateConformanceTests(unittest.TestCase):
    def test_support_plus_failed_source_gate_maps_to_hold(self):
        r = q17.prove_conformance(q8_fixture(outcome="E8_WIN", gate=False))
        self.assertTrue(r.domain_router_refines_generic_product_gate)
        self.assertEqual(r.n1_disposition, "HOLD_HARD_GATE")
        self.assertFalse(r.q8_proposal_eligible)
        self.assertFalse(r.n1_proposal_eligible)

    def test_support_plus_green_source_gate_maps_to_bounded_proposal(self):
        r = q17.prove_conformance(q8_fixture(outcome="E8_WIN", gate=True))
        self.assertTrue(r.domain_router_refines_generic_product_gate)
        self.assertEqual(r.n1_disposition, "ELIGIBLE_BOUNDED_PROPOSAL")
        self.assertTrue(r.q8_proposal_eligible)
        self.assertTrue(r.n1_proposal_eligible)

    def test_tie_plus_green_source_gate_maps_to_no_positive_evidence_stop(self):
        r = q17.prove_conformance(q8_fixture(outcome="TIE", gate=True))
        self.assertTrue(r.domain_router_refines_generic_product_gate)
        self.assertEqual(r.n1_disposition, "STOP_NO_POSITIVE_EVIDENCE")
        self.assertFalse(r.n1_proposal_eligible)

    def test_control_win_plus_green_source_gate_maps_to_opposing_stop(self):
        r = q17.prove_conformance(q8_fixture(outcome="CONTROL_WIN", gate=True))
        self.assertTrue(r.domain_router_refines_generic_product_gate)
        self.assertEqual(r.n1_disposition, "STOP_OPPOSING_EVIDENCE")
        self.assertFalse(r.n1_proposal_eligible)

    def test_domain_policy_divergence_is_detected(self):
        q = q8_fixture(outcome="E8_WIN", gate=False)
        q["disposition"] = "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"
        q["c2_request_proposal_eligible"] = True
        r = q17.prove_conformance(q)
        self.assertFalse(r.domain_router_refines_generic_product_gate)
        self.assertEqual(r.reason, "DOMAIN_GENERIC_POLICY_DIVERGENCE")

    def test_failed_gate_requires_domain_blocker(self):
        q = q8_fixture(outcome="E8_WIN", gate=False)
        q["reason"] = ""
        with self.assertRaisesRegex(ValueError, "FAILED_SOURCE_GATE_REQUIRES_BLOCKER"):
            q17.prove_conformance(q)

    def test_claim_ceiling_drift_is_rejected(self):
        q = q8_fixture()
        q["execution_authorized"] = True
        with self.assertRaisesRegex(ValueError, "CLAIM_CEILING_WIDENED"):
            q17.prove_conformance(q)

    def test_exact_current_requires_frozen_q8_receipt_identity(self):
        q = q8_fixture()
        with self.assertRaisesRegex(ValueError, "Q8_RECEIPT_DIGEST_MISMATCH"):
            q17.prove_conformance(q, require_exact_current=True)

    def test_noncompensation_ceiling_is_preserved(self):
        r = q17.prove_conformance(q8_fixture())
        for key in (
            "favorable_evidence_can_bypass_failed_source_gate",
            "domain_policy_can_compensate_hard_gate",
            "generic_policy_can_compensate_hard_gate",
            "semantic_truth_minted",
            "effect_authority_granted",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(r, key), key)

    def test_receipt_is_deterministic(self):
        self.assertEqual(
            q17.prove_conformance(q8_fixture()).receipt_digest,
            q17.prove_conformance(q8_fixture()).receipt_digest,
        )


if __name__ == "__main__":
    unittest.main()

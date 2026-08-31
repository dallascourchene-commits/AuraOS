from __future__ import annotations

import unittest

from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.glm53_g2_c2_transfer_plan_attachment import (
    ATTACHED,
    ATTACHED_NOOP,
    C2_OWNER_HEAD,
    G1_PHYSICAL_QUARANTINE_HEAD,
    G2_PREDICTOR_CALIBRATION_HEAD,
    G2_PREDICTOR_CALIBRATION_TEST_BLOB,
    G2_PREDICTOR_CALIBRATION_VERIFICATION_HEAD,
    PHYSICAL_IO_UNKNOWN,
    CalibratedTransferPlanRef,
    attach_calibrated_g2_plan_to_c2_request,
)


def request(**updates):
    base = dict(
        w3_proof_logical_id="1" * 64,
        preflight_receipt_digest="2" * 64,
        airllm_source_revision="airllm:exact-source:v1",
        airllm_security_evidence_digest="3" * 64,
        host_snapshot_digest="4" * 64,
        storage_plan_digest="5" * 64,
        workspace_root="/mnt/c/Users/operator/AuraOS/.aura/c2-canary",
        max_payload_bytes=64_000_000,
        max_wall_seconds=120,
        effect_admission_ref="effect-admission:external-owner-required",
    )
    base.update(updates)
    return OwnerHostC2CanaryRequest(**base)


def plan(**updates):
    base = dict(
        g2_receipt_digest="6" * 64,
        prediction_digest="7" * 64,
        predictor_generation="predictor:g2:v3",
        calibration_generation="calibration:g2:v3",
        policy_generation="policy:g2:v3",
        layer_id="layer:07",
        source_binding_digest="binding:glm53:layer07:official-source",
        admitted_experts=(1, 3),
        admitted_logical_bytes=8_000_000,
    )
    base.update(updates)
    return CalibratedTransferPlanRef(**base)


class G2C2TransferPlanAttachmentTests(unittest.TestCase):
    def test_exact_plan_attaches_without_mutating_c2_or_minting_effects(self):
        req = request()
        before = req.request_digest
        out = attach_calibrated_g2_plan_to_c2_request(request=req, plan_ref=plan())
        self.assertEqual(before, req.request_digest)
        self.assertEqual(before, out.c2_request_digest)
        self.assertEqual(req.storage_plan_digest, out.c2_storage_plan_digest)
        self.assertEqual((1, 3), out.admitted_experts)
        self.assertEqual(ATTACHED, out.disposition)
        self.assertEqual(PHYSICAL_IO_UNKNOWN, out.physical_io_state)
        self.assertTrue(out.source_binding_revalidation_required)
        self.assertTrue(out.owner_host_measurement_required)
        self.assertTrue(out.native_route_remains_authoritative)
        self.assertFalse(out.c2_source_binding_equivalence_proven)
        self.assertFalse(out.physical_io_proven)
        self.assertFalse(out.execution_authorized)
        self.assertFalse(out.transfer_effect_authorized)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.semantic_k27_authority_minted)
        self.assertFalse(out.native_private_transformer_kv_accessed)
        self.assertEqual(64, len(out.attachment_digest))

    def test_empty_calibrated_plan_is_lawful_noop_not_execution_failure(self):
        out = attach_calibrated_g2_plan_to_c2_request(
            request=request(),
            plan_ref=plan(admitted_experts=(), admitted_logical_bytes=0),
        )
        self.assertEqual(ATTACHED_NOOP, out.disposition)
        self.assertEqual((), out.admitted_experts)
        self.assertEqual(0, out.admitted_logical_bytes)
        self.assertFalse(out.execution_authorized)

    def test_foreign_parent_semantics_and_verification_are_distinct_and_exact(self):
        with self.assertRaisesRegex(ValueError, "G1_PHYSICAL_QUARANTINE_HEAD_MISMATCH"):
            plan(g1_physical_quarantine_head="0" * 40).validate()
        with self.assertRaisesRegex(ValueError, "G2_PREDICTOR_CALIBRATION_HEAD_MISMATCH"):
            plan(g2_predictor_calibration_head="f" * 40).validate()
        with self.assertRaisesRegex(ValueError, "G2_PREDICTOR_CALIBRATION_TEST_BLOB_MISMATCH"):
            plan(g2_predictor_calibration_test_blob="a" * 40).validate()
        with self.assertRaisesRegex(ValueError, "G2_PREDICTOR_CALIBRATION_VERIFICATION_HEAD_MISMATCH"):
            plan(g2_predictor_calibration_verification_head="b" * 40).validate()
        self.assertEqual(G1_PHYSICAL_QUARANTINE_HEAD, plan().g1_physical_quarantine_head)
        self.assertEqual(G2_PREDICTOR_CALIBRATION_HEAD, plan().g2_predictor_calibration_head)
        self.assertEqual(G2_PREDICTOR_CALIBRATION_TEST_BLOB, plan().g2_predictor_calibration_test_blob)
        self.assertEqual(
            G2_PREDICTOR_CALIBRATION_VERIFICATION_HEAD,
            plan().g2_predictor_calibration_verification_head,
        )
        self.assertNotEqual(
            plan().g2_predictor_calibration_head,
            plan().g2_predictor_calibration_verification_head,
        )
        self.assertEqual(C2_OWNER_HEAD, attach_calibrated_g2_plan_to_c2_request(request=request(), plan_ref=plan()).c2_owner_head)

    def test_caller_physical_truth_cannot_cross_into_attachment(self):
        with self.assertRaisesRegex(ValueError, "TRANSFER_PLAN_REF_CANNOT_CARRY_PHYSICAL_IO_TRUTH"):
            plan(physical_io_attested=True, physical_prefetch_bytes=1234).validate()
        with self.assertRaisesRegex(ValueError, "TRANSFER_PLAN_REF_CANNOT_CARRY_PHYSICAL_IO_TRUTH"):
            plan(physical_prefetch_bytes=8_000_000).validate()

    def test_logical_bytes_do_not_become_physical_bytes_or_c2_payload_budget(self):
        req = request(max_payload_bytes=1)
        out = attach_calibrated_g2_plan_to_c2_request(request=req, plan_ref=plan(admitted_logical_bytes=8_000_000))
        self.assertEqual(8_000_000, out.admitted_logical_bytes)
        self.assertFalse(out.physical_io_proven)
        self.assertEqual(PHYSICAL_IO_UNKNOWN, out.physical_io_state)
        self.assertEqual(1, req.max_payload_bytes)

    def test_attachment_does_not_claim_source_equivalence_missing_from_c2_schema(self):
        out = attach_calibrated_g2_plan_to_c2_request(request=request(), plan_ref=plan())
        self.assertEqual("binding:glm53:layer07:official-source", out.source_binding_digest)
        self.assertTrue(out.source_binding_revalidation_required)
        self.assertFalse(out.c2_source_binding_equivalence_proven)

    def test_authority_widening_in_plan_ref_fails_closed(self):
        for field in ("transfer_effect_authorized", "g2_admitted", "semantic_k27_authority_minted"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "TRANSFER_PLAN_REF_CANNOT_WIDEN_AUTHORITY"):
                    plan(**{field: True}).validate()

    def test_expert_set_and_logical_byte_identity_is_canonical(self):
        with self.assertRaisesRegex(ValueError, "ATTACHED_EXPERTS_MUST_BE_SORTED_UNIQUE"):
            plan(admitted_experts=(3, 1)).validate()
        with self.assertRaisesRegex(ValueError, "ATTACHED_EXPERTS_MUST_BE_SORTED_UNIQUE"):
            plan(admitted_experts=(1, 1)).validate()
        with self.assertRaisesRegex(ValueError, "NONEMPTY_TRANSFER_PLAN_REQUIRES_POSITIVE_LOGICAL_BYTES"):
            plan(admitted_logical_bytes=0).validate()
        with self.assertRaisesRegex(ValueError, "EMPTY_TRANSFER_PLAN_REQUIRES_ZERO_LOGICAL_BYTES"):
            plan(admitted_experts=(), admitted_logical_bytes=1).validate()

    def test_attachment_digest_changes_with_plan_or_request_identity(self):
        a = attach_calibrated_g2_plan_to_c2_request(request=request(), plan_ref=plan())
        b = attach_calibrated_g2_plan_to_c2_request(request=request(storage_plan_digest="8" * 64), plan_ref=plan())
        c = attach_calibrated_g2_plan_to_c2_request(request=request(), plan_ref=plan(policy_generation="policy:g2:v4"))
        self.assertNotEqual(a.attachment_digest, b.attachment_digest)
        self.assertNotEqual(a.attachment_digest, c.attachment_digest)


if __name__ == "__main__":
    unittest.main()

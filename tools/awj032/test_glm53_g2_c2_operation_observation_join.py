from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g2_c2_transfer_plan_attachment import (
    CalibratedTransferPlanRef,
    attach_calibrated_g2_plan_to_c2_request,
)
from tools.awj032.glm53_owner_host_c2_handoff import (
    OFFICIAL_MODEL_REPO,
    OFFICIAL_MODEL_REVISION,
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    join_owner_host_c2_attempt,
)
from tools.awj032.glm53_g2_c2_operation_observation_join import (
    BOUND,
    HOLD,
    WITNESS_SCHEMA,
    GLM53OperationObservationWitness,
    bind_plan_attempt_operation_observation,
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


def plan_ref(**updates):
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


def attempt(req: OwnerHostC2CanaryRequest, **updates):
    base = dict(
        request_digest=req.request_digest,
        owner_host_observation_id="obs:glm53:c2:001",
        runner_identity="owner-host:runner:a",
        runner_generation="runner-generation:20260831:a",
        started_at_utc="2026-08-31T17:00:00+00:00",
        ended_at_utc="2026-08-31T17:00:02+00:00",
        command_digest="8" * 64,
        environment_digest="9" * 64,
        source_snapshot_digest="a" * 64,
        airllm_source_revision=req.airllm_source_revision,
        model_repo=OFFICIAL_MODEL_REPO,
        model_revision=OFFICIAL_MODEL_REVISION,
        actual_payload_bytes=8_000_000,
        tensor_read_operations=2,
        physical_read_bytes=6_000_000,
        elapsed_seconds=2.0,
        process_exit_code=0,
        generated_token_count=1,
        generated_output_sha256="b" * 64,
        lifecycle_measurement_ref="lifecycle:glm53:c2:001",
        host_measurement_ref="host-measurement:glm53:c2:001",
    )
    base.update(updates)
    return OwnerHostC2CanaryReceipt(**base)


def relation_inputs():
    req = request()
    attachment = attach_calibrated_g2_plan_to_c2_request(request=req, plan_ref=plan_ref())
    att = attempt(req)
    c2_join = join_owner_host_c2_attempt(request=req, receipt=att)
    return req, attachment, att, c2_join


def witness(req, attachment, att, c2_join, **updates):
    base = dict(
        schema=WITNESS_SCHEMA,
        request_digest=req.request_digest,
        attempt_receipt_digest=att.receipt_digest,
        c2_join_logical_id=c2_join.logical_id,
        plan_attachment_digest=attachment.attachment_digest,
        plan_source_binding_digest=attachment.source_binding_digest,
        owner_host_observation_id=att.owner_host_observation_id,
        operation_id="operation:glm53:c2:001",
        runner_identity=att.runner_identity,
        runner_generation=att.runner_generation,
        source_snapshot_digest=att.source_snapshot_digest,
        backend_owner_ref="backend-owner:nvme-observer:v1",
        observer_generation="observer-generation:20260831:v1",
        host_measurement_ref=att.host_measurement_ref,
        lifecycle_measurement_ref=att.lifecycle_measurement_ref,
        physical_io_attestation_ref="physical-io-attestation:operation:001",
        source_binding_revalidation_ref="source-binding-revalidation:operation:001",
        physical_read_bytes=att.physical_read_bytes,
    )
    base.update(updates)
    return GLM53OperationObservationWitness(**base)


class G2C2OperationObservationJoinTests(unittest.TestCase):
    def test_missing_operation_witness_holds_without_manufacturing_measurement(self):
        req, attachment, att, c2_join = relation_inputs()
        out = bind_plan_attempt_operation_observation(
            attachment=attachment, request=req, attempt=att, c2_join=c2_join, witness=None
        )
        self.assertEqual(HOLD, out.disposition)
        self.assertTrue(out.plan_to_request_bound)
        self.assertTrue(out.request_to_attempt_bound)
        self.assertFalse(out.attempt_to_observation_bound)
        self.assertIsNone(out.physical_read_bytes)
        self.assertFalse(out.causal_plan_benefit_proven)

    def test_exact_operation_witness_binds_observation_not_causal_benefit(self):
        req, attachment, att, c2_join = relation_inputs()
        out = bind_plan_attempt_operation_observation(
            attachment=attachment,
            request=req,
            attempt=att,
            c2_join=c2_join,
            witness=witness(req, attachment, att, c2_join),
        )
        self.assertEqual(BOUND, out.disposition)
        self.assertTrue(out.observational_attribution_bound)
        self.assertTrue(out.source_binding_revalidation_bound)
        self.assertEqual(att.physical_read_bytes, out.physical_read_bytes)
        self.assertTrue(out.counterfactual_baseline_required)
        self.assertFalse(out.causal_plan_benefit_proven)
        self.assertFalse(out.bytes_saved_proven)
        self.assertFalse(out.latency_saved_proven)
        self.assertFalse(out.physical_io_avoided_proven)
        self.assertFalse(out.execution_authorized)
        self.assertFalse(out.effect_authority_proven)

    def test_request_attempt_or_join_cross_cast_rejects(self):
        req, attachment, att, c2_join = relation_inputs()
        other = request(storage_plan_digest="c" * 64)
        with self.assertRaisesRegex(ValueError, "PLAN_ATTACHMENT_NOT_FOR_C2_REQUEST"):
            bind_plan_attempt_operation_observation(
                attachment=attachment,
                request=other,
                attempt=att,
                c2_join=c2_join,
                witness=None,
            )
        wrong_attempt = attempt(req, request_digest="d" * 64)
        with self.assertRaisesRegex(ValueError, "C2_ATTEMPT_NOT_FOR_REQUEST"):
            bind_plan_attempt_operation_observation(
                attachment=attachment,
                request=req,
                attempt=wrong_attempt,
                c2_join=c2_join,
                witness=None,
            )
        wrong_join = replace(c2_join, attempt_receipt_digest="e" * 64)
        with self.assertRaisesRegex(ValueError, "C2_JOIN_NOT_FOR_EXACT_ATTEMPT"):
            bind_plan_attempt_operation_observation(
                attachment=attachment,
                request=req,
                attempt=att,
                c2_join=wrong_join,
                witness=None,
            )

    def test_observation_identity_substitutions_reject(self):
        req, attachment, att, c2_join = relation_inputs()
        cases = (
            {"request_digest": "f" * 64},
            {"attempt_receipt_digest": "0" * 64},
            {"c2_join_logical_id": "1" * 64},
            {"plan_attachment_digest": "2" * 64},
            {"plan_source_binding_digest": "binding:other"},
            {"owner_host_observation_id": "obs:other"},
            {"runner_identity": "runner:other"},
            {"runner_generation": "runner-generation:other"},
            {"source_snapshot_digest": "3" * 64},
            {"host_measurement_ref": "host-measurement:other"},
            {"lifecycle_measurement_ref": "lifecycle:other"},
            {"physical_read_bytes": att.physical_read_bytes + 1},
        )
        for updates in cases:
            with self.subTest(updates=updates):
                with self.assertRaisesRegex(ValueError, "PLAN_ATTEMPT_OBSERVATION_IDENTITY_MISMATCH"):
                    bind_plan_attempt_operation_observation(
                        attachment=attachment,
                        request=req,
                        attempt=att,
                        c2_join=c2_join,
                        witness=witness(req, attachment, att, c2_join, **updates),
                    )

    def test_witness_currentness_operation_source_and_domain_are_hard_gates(self):
        req, attachment, att, c2_join = relation_inputs()
        cases = (
            ({"observer_current": False}, "WITNESS_OBSERVER_CURRENTNESS_REQUIRED"),
            ({"exact_operation_bound": False}, "WITNESS_EXACT_OPERATION_BINDING_REQUIRED"),
            ({"source_binding_revalidated": False}, "WITNESS_SOURCE_BINDING_REVALIDATION_REQUIRED"),
            ({"glm53_workload": False}, "WITNESS_MUST_BE_GLM53_NOT_TINY_FIXTURE_CROSSCAST"),
            ({"tiny_fixture_crosscast": True}, "WITNESS_MUST_BE_GLM53_NOT_TINY_FIXTURE_CROSSCAST"),
        )
        for updates, code in cases:
            with self.subTest(updates=updates):
                with self.assertRaisesRegex(ValueError, code):
                    bind_plan_attempt_operation_observation(
                        attachment=attachment,
                        request=req,
                        attempt=att,
                        c2_join=c2_join,
                        witness=witness(req, attachment, att, c2_join, **updates),
                    )

    def test_witness_or_relation_cannot_mint_authority_or_benefit(self):
        req, attachment, att, c2_join = relation_inputs()
        for field in ("execution_authority_granted", "effect_authority_granted", "semantic_k27_authority", "native_private_transformer_kv_accessed"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "WITNESS_CANNOT_WIDEN_AUTHORITY"):
                    witness(req, attachment, att, c2_join, **{field: True}).validate()
        out = bind_plan_attempt_operation_observation(
            attachment=attachment,
            request=req,
            attempt=att,
            c2_join=c2_join,
            witness=witness(req, attachment, att, c2_join),
        )
        for field in ("causal_plan_benefit_proven", "bytes_saved_proven", "latency_saved_proven", "physical_io_avoided_proven", "execution_authorized", "g2_admitted", "semantic_k27_authority_minted"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "PLAN_OPERATION_JOIN_CANNOT_MINT_CAUSAL_BENEFIT_OR_AUTHORITY"):
                    replace(out, **{field: True}).validate_claim_ceiling()

    def test_relation_digest_changes_with_operation_identity(self):
        req, attachment, att, c2_join = relation_inputs()
        a = bind_plan_attempt_operation_observation(
            attachment=attachment, request=req, attempt=att, c2_join=c2_join,
            witness=witness(req, attachment, att, c2_join, operation_id="operation:a"),
        )
        b = bind_plan_attempt_operation_observation(
            attachment=attachment, request=req, attempt=att, c2_join=c2_join,
            witness=witness(req, attachment, att, c2_join, operation_id="operation:b"),
        )
        self.assertNotEqual(a.relation_digest, b.relation_digest)


if __name__ == "__main__":
    unittest.main()

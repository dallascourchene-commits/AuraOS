from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.awj032.glm53_owner_host_c2_handoff import (
    OFFICIAL_MODEL_REPO,
    OFFICIAL_MODEL_REVISION,
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    join_owner_host_c2_attempt,
)
from tools.awj032.glm53_owner_host_lifecycle_return_packet import (
    TARGET_LIFECYCLE_SCHEMA,
    build_owner_host_lifecycle_return_packet,
)
from tools.awj032.glm53_lifecycle_return_evidence_class_boundary import (
    INPUT_EVIDENCE_CLASS,
    TARGET_EVIDENCE_CLASS,
    LifecycleReturnEvidenceClassError,
    preserve_lifecycle_return_evidence_class,
)

D = "ab" * 32
E = "cd" * 32
F = "12" * 32
G = "34" * 32
H = "56" * 32


def request() -> OwnerHostC2CanaryRequest:
    return OwnerHostC2CanaryRequest(
        w3_proof_logical_id=D,
        preflight_receipt_digest=E,
        airllm_source_revision="airllm-reviewed-source@deadbeef",
        airllm_security_evidence_digest=F,
        host_snapshot_digest=G,
        storage_plan_digest=H,
        workspace_root="/mnt/d/aura/awj032/c2-canary",
        max_payload_bytes=256 * 1024 * 1024,
        max_wall_seconds=900,
        effect_admission_ref="owner-effect:awj032:c2:001",
    )


def packet():
    req = request()
    attempt = OwnerHostC2CanaryReceipt(
        request_digest=req.request_digest,
        owner_host_observation_id="thinkpad-wsl:obs:001",
        runner_identity="aura-owner-host-runner",
        runner_generation="v1@001",
        started_at_utc="2026-08-31T05:10:00+00:00",
        ended_at_utc="2026-08-31T05:10:30+00:00",
        command_digest=D,
        environment_digest=E,
        source_snapshot_digest=F,
        airllm_source_revision=req.airllm_source_revision,
        model_repo=OFFICIAL_MODEL_REPO,
        model_revision=OFFICIAL_MODEL_REVISION,
        actual_payload_bytes=64 * 1024 * 1024,
        tensor_read_operations=12,
        physical_read_bytes=48 * 1024 * 1024,
        elapsed_seconds=30.0,
        process_exit_code=0,
        generated_token_count=4,
        generated_output_sha256=G,
        lifecycle_measurement_ref="lifecycle:pending-registry:001",
        host_measurement_ref="host-snapshot:001",
    )
    joined = join_owner_host_c2_attempt(request=req, receipt=attempt)
    return build_owner_host_lifecycle_return_packet(
        request=req,
        receipt=attempt,
        join=joined,
    )


class LifecycleReturnEvidenceClassBoundaryTests(unittest.TestCase):
    def assert_code(self, code: str, fn) -> None:
        with self.assertRaises(LifecycleReturnEvidenceClassError) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)

    def test_exact_return_packet_preserves_attempt_return_class(self) -> None:
        p = packet()
        out = preserve_lifecycle_return_evidence_class(packet=p)
        self.assertEqual(p.packet_digest, out.input_packet_digest)
        self.assertEqual(INPUT_EVIDENCE_CLASS, out.input_evidence_class)
        self.assertEqual(INPUT_EVIDENCE_CLASS, out.output_evidence_class)
        self.assertEqual(TARGET_EVIDENCE_CLASS, out.target_evidence_class)
        self.assertEqual(TARGET_LIFECYCLE_SCHEMA, out.target_lifecycle_schema)
        self.assertNotEqual(out.output_evidence_class, out.target_evidence_class)
        self.assertFalse(out.same_lifecycle_reference_is_type_conversion)
        self.assertFalse(out.cross_cast_to_lifecycle_measurement_receipt_permitted)
        self.assertTrue(out.independent_lifecycle_producer_receipt_required)
        self.assertTrue(out.independent_registry_verification_required)

    def test_attempt_counters_remain_attempt_telemetry(self) -> None:
        p = packet()
        self.assertGreater(p.attempt_reported_physical_read_bytes, 0)
        out = preserve_lifecycle_return_evidence_class(packet=p)
        self.assertFalse(out.attempt_counters_are_lifecycle_metrics)
        self.assertFalse(out.producer_authenticated)
        self.assertFalse(out.lifecycle_registry_verified)
        self.assertFalse(out.real_w4_policy_winner_proven)
        self.assertFalse(out.g2_admitted)

    def test_same_lifecycle_reference_does_not_convert_type(self) -> None:
        p = packet()
        out = preserve_lifecycle_return_evidence_class(packet=p)
        self.assertEqual(p.lifecycle_measurement_ref, out.lifecycle_measurement_ref)
        self.assertFalse(out.same_lifecycle_reference_is_type_conversion)
        self.assertEqual(INPUT_EVIDENCE_CLASS, out.output_evidence_class)

    def test_rejects_parent_ceiling_widening_before_class_reasoning(self) -> None:
        widened = replace(packet(), producer_authenticated_by_this_packet=True)
        self.assert_code(
            "RETURN_PACKET_CEILING_WIDENED",
            lambda: preserve_lifecycle_return_evidence_class(packet=widened),
        )

    def test_rejects_target_schema_drift(self) -> None:
        drifted = replace(packet(), target_lifecycle_schema="OtherLifecycleReceiptV9")
        self.assert_code(
            "TARGET_LIFECYCLE_SCHEMA_DRIFT",
            lambda: preserve_lifecycle_return_evidence_class(packet=drifted),
        )

    def test_mapping_cannot_impersonate_typed_return_packet(self) -> None:
        forged = packet().to_dict()
        self.assert_code(
            "EXACT_C2_RETURN_PACKET_REQUIRED",
            lambda: preserve_lifecycle_return_evidence_class(packet=forged),
        )

    def test_public_boundary_has_no_type_rank_metric_or_trust_overrides(self) -> None:
        params = set(inspect.signature(preserve_lifecycle_return_evidence_class).parameters)
        self.assertEqual({"packet"}, params)
        forbidden = {
            "evidence_class",
            "target_evidence_class",
            "corroboration_count",
            "rank",
            "cache_hit_ratio",
            "energy_joules",
            "peak_resident_bytes",
            "physical_io_attested",
            "producer_authenticated",
            "registry_record",
            "g2_admitted",
            "effect_authority_proven",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_corroboration_and_digest_preservation_do_not_upgrade_class(self) -> None:
        out = preserve_lifecycle_return_evidence_class(packet=packet())
        self.assertFalse(out.corroboration_can_upgrade_evidence_class)
        self.assertFalse(out.digest_preservation_can_upgrade_evidence_class)
        self.assertEqual(INPUT_EVIDENCE_CLASS, out.output_evidence_class)

    def test_receipt_is_deterministic(self) -> None:
        first = preserve_lifecycle_return_evidence_class(packet=packet())
        second = preserve_lifecycle_return_evidence_class(packet=packet())
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertEqual(64, len(first.receipt_digest))


if __name__ == "__main__":
    unittest.main()

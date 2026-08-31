from __future__ import annotations

from dataclasses import fields, replace
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
    PR430_EXACT_HOSTED_HEAD,
    PR430_EXACT_HOSTED_RUN_ID,
    REQUIRED_PRODUCER_LIFECYCLE_METRICS,
    TARGET_LIFECYCLE_SCHEMA,
    OwnerHostLifecycleReturnError,
    OwnerHostLifecycleReturnPacket,
    build_owner_host_lifecycle_return_packet,
)

D = "ab" * 32
E = "cd" * 32
F = "12" * 32
G = "34" * 32
H = "56" * 32


class OwnerHostLifecycleReturnPacketTests(unittest.TestCase):
    def request(self, **changes):
        value = OwnerHostC2CanaryRequest(
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
        return replace(value, **changes) if changes else value

    def receipt(self, request=None, **changes):
        request = request or self.request()
        value = OwnerHostC2CanaryReceipt(
            request_digest=request.request_digest,
            owner_host_observation_id="thinkpad-wsl:obs:001",
            runner_identity="aura-owner-host-runner",
            runner_generation="v1@001",
            started_at_utc="2026-08-31T05:10:00+00:00",
            ended_at_utc="2026-08-31T05:10:30+00:00",
            command_digest=D,
            environment_digest=E,
            source_snapshot_digest=F,
            airllm_source_revision=request.airllm_source_revision,
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
        return replace(value, **changes) if changes else value

    def packet(self, *, request=None, receipt=None):
        request = request or self.request()
        receipt = receipt or self.receipt(request)
        join = join_owner_host_c2_attempt(request=request, receipt=receipt)
        return build_owner_host_lifecycle_return_packet(
            request=request, receipt=receipt, join=join
        )

    def assert_code(self, code, fn):
        with self.assertRaises(OwnerHostLifecycleReturnError) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)

    def test_exact_c2_attempt_binds_to_nonmetric_lifecycle_return_packet(self):
        request = self.request()
        receipt = self.receipt(request)
        join = join_owner_host_c2_attempt(request=request, receipt=receipt)
        packet = build_owner_host_lifecycle_return_packet(
            request=request, receipt=receipt, join=join
        )
        self.assertEqual(request.request_digest, packet.c2_request_digest)
        self.assertEqual(receipt.receipt_digest, packet.c2_attempt_receipt_digest)
        self.assertEqual(join.logical_id, packet.c2_join_logical_id)
        self.assertEqual(receipt.lifecycle_measurement_ref, packet.lifecycle_measurement_ref)
        self.assertEqual(receipt.physical_read_bytes, packet.attempt_reported_physical_read_bytes)
        self.assertTrue(packet.canary_process_succeeded)
        self.assertTrue(packet.generated_output_observed)
        self.assertFalse(packet.lifecycle_metric_vector_supplied_by_this_packet)
        self.assertFalse(packet.physical_io_attested_by_this_packet)
        self.assertFalse(packet.producer_authenticated_by_this_packet)
        self.assertFalse(packet.lifecycle_registry_verified_by_this_packet)
        self.assertFalse(packet.real_w4_policy_winner_proven)
        self.assertFalse(packet.full_model_runtime_proven)
        self.assertFalse(packet.quality_proven)
        self.assertFalse(packet.g2_admitted)
        self.assertFalse(packet.effect_authority_proven)

    def test_target_pr430_schema_and_hosted_generation_are_explicit(self):
        packet = self.packet()
        self.assertEqual(TARGET_LIFECYCLE_SCHEMA, packet.target_lifecycle_schema)
        self.assertEqual(PR430_EXACT_HOSTED_HEAD, packet.target_pr430_exact_hosted_head)
        self.assertEqual(PR430_EXACT_HOSTED_RUN_ID, packet.target_pr430_exact_hosted_run_id)
        self.assertEqual(REQUIRED_PRODUCER_LIFECYCLE_METRICS, packet.required_lifecycle_metric_fields)

    def test_public_builder_has_no_lifecycle_metric_or_registry_override_inputs(self):
        params = set(inspect.signature(build_owner_host_lifecycle_return_packet).parameters)
        self.assertEqual({"request", "receipt", "join"}, params)
        forbidden = {
            "cache_hit_ratio",
            "energy_joules",
            "peak_resident_bytes",
            "warmup_seconds",
            "restart_seconds",
            "revalidation_seconds",
            "control_overhead_seconds",
            "physical_io_attested",
            "correctness_reference_equivalent",
            "source_current",
            "measurement_current",
            "independently_observed",
            "registry",
            "registry_record",
            "producer_authenticated",
            "g2_admitted",
            "effect_authority_proven",
        }
        self.assertTrue(params.isdisjoint(forbidden))

        packet_fields = {field.name for field in fields(OwnerHostLifecycleReturnPacket)}
        metric_value_fields = set(REQUIRED_PRODUCER_LIFECYCLE_METRICS)
        self.assertTrue(packet_fields.isdisjoint(metric_value_fields))

    def test_attempt_counters_are_not_relabelled_as_lifecycle_metrics(self):
        packet = self.packet()
        self.assertEqual(48 * 1024 * 1024, packet.attempt_reported_physical_read_bytes)
        self.assertFalse(packet.physical_io_attested_by_this_packet)
        for name in REQUIRED_PRODUCER_LIFECYCLE_METRICS:
            self.assertFalse(hasattr(packet, name))

    def test_rejects_caller_modified_join(self):
        request = self.request()
        receipt = self.receipt(request)
        join = join_owner_host_c2_attempt(request=request, receipt=receipt)
        foreign = replace(join, lifecycle_measurement_ref="lifecycle:other")
        self.assert_code(
            "C2_JOIN_NOT_EXACT_PARENT_CONSEQUENCE",
            lambda: build_owner_host_lifecycle_return_packet(
                request=request, receipt=receipt, join=foreign
            ),
        )

    def test_rejects_parent_ceiling_widening(self):
        request = self.request()
        receipt = self.receipt(request)
        join = join_owner_host_c2_attempt(request=request, receipt=receipt)
        widened = replace(join, g2_admitted=True)
        self.assert_code(
            "C2_JOIN_NOT_EXACT_PARENT_CONSEQUENCE",
            lambda: build_owner_host_lifecycle_return_packet(
                request=request, receipt=receipt, join=widened
            ),
        )

    def test_failed_attempt_can_return_identity_without_false_success(self):
        request = self.request()
        receipt = self.receipt(
            request,
            process_exit_code=1,
            generated_token_count=0,
            generated_output_sha256=None,
        )
        packet = self.packet(request=request, receipt=receipt)
        self.assertFalse(packet.canary_process_succeeded)
        self.assertFalse(packet.generated_output_observed)
        self.assertFalse(packet.lifecycle_metric_vector_supplied_by_this_packet)
        self.assertFalse(packet.g2_admitted)

    def test_packet_digest_is_deterministic(self):
        self.assertEqual(self.packet().packet_digest, self.packet().packet_digest)


if __name__ == "__main__":
    unittest.main()

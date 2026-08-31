from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_owner_host_c2_handoff import (
    CURRENT_PREFLIGHT_HEAD,
    CURRENT_W3_HEAD,
    OFFICIAL_MODEL_REPO,
    OFFICIAL_MODEL_REVISION,
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    OwnerHostC2HandoffError,
    join_owner_host_c2_attempt,
)


D = "ab" * 32
E = "cd" * 32
F = "12" * 32
G = "34" * 32
H = "56" * 32


class OwnerHostC2HandoffTests(unittest.TestCase):
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
            physical_read_bytes=64 * 1024 * 1024,
            elapsed_seconds=30.0,
            process_exit_code=0,
            generated_token_count=4,
            generated_output_sha256=G,
            lifecycle_measurement_ref="lifecycle:pending-registry:001",
            host_measurement_ref="host-snapshot:001",
        )
        return replace(value, **changes) if changes else value

    def assert_code(self, code, fn):
        with self.assertRaises(OwnerHostC2HandoffError) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)

    def test_exact_upstream_generations_are_bound(self):
        request = self.request()
        self.assertEqual(CURRENT_W3_HEAD, request.w3_head_sha)
        self.assertEqual(CURRENT_PREFLIGHT_HEAD, request.preflight_head_sha)
        self.assertFalse(request.execution_authorized_by_this_contract)
        self.assertFalse(request.g2_admitted)

    def test_request_digest_is_deterministic(self):
        self.assertEqual(self.request().request_digest, self.request().request_digest)

    def test_request_rejects_remote_code_fallback_and_substitution(self):
        self.assert_code(
            "REMOTE_CODE_FORBIDDEN",
            lambda: self.request(trust_remote_code=True),
        )
        self.assert_code(
            "REMOTE_FALLBACK_FORBIDDEN",
            lambda: self.request(allow_remote_fallback=True),
        )
        self.assert_code(
            "MODEL_SUBSTITUTION_FORBIDDEN",
            lambda: self.request(allow_model_substitution=True),
        )

    def test_request_rejects_stale_owner_generations(self):
        self.assert_code(
            "W3_HEAD_NOT_CURRENT_CONTRACT_GENERATION",
            lambda: self.request(w3_head_sha="0" * 40),
        )
        self.assert_code(
            "PREFLIGHT_HEAD_NOT_CURRENT_CONTRACT_GENERATION",
            lambda: self.request(preflight_head_sha="0" * 40),
        )

    def test_request_requires_bounded_workspace(self):
        self.assert_code(
            "WORKSPACE_ROOT_MUST_BE_BOUNDED_ABSOLUTE_PATH",
            lambda: self.request(workspace_root="/"),
        )

    def test_receipt_records_attempt_but_does_not_authenticate_itself(self):
        request = self.request()
        receipt = self.receipt(request)
        joined = join_owner_host_c2_attempt(request=request, receipt=receipt)
        self.assertTrue(joined.host_attempt_integrity_checked)
        self.assertTrue(joined.bounded_payload_respected)
        self.assertTrue(joined.local_only_constraints_respected)
        self.assertTrue(joined.canary_process_succeeded)
        self.assertTrue(joined.generated_output_observed)
        self.assertTrue(joined.producer_authentication_required)
        self.assertTrue(joined.lifecycle_registry_required)
        self.assertFalse(joined.real_w4_policy_winner_proven)
        self.assertFalse(joined.full_model_runtime_proven)
        self.assertFalse(joined.g2_admitted)
        self.assertFalse(joined.effect_authority_proven)

    def test_receipt_must_bind_exact_request(self):
        request = self.request()
        receipt = self.receipt(request)
        foreign = replace(receipt, request_digest="00" * 32)
        self.assert_code(
            "RECEIPT_NOT_FOR_REQUEST",
            lambda: join_owner_host_c2_attempt(request=request, receipt=foreign),
        )

    def test_receipt_rejects_airllm_generation_drift(self):
        request = self.request()
        receipt = self.receipt(request, airllm_source_revision="other-airllm@bad")
        self.assert_code(
            "AIRLLM_GENERATION_DRIFT",
            lambda: join_owner_host_c2_attempt(request=request, receipt=receipt),
        )

    def test_receipt_rejects_payload_and_wall_budget_escape(self):
        request = self.request(max_payload_bytes=1024, max_wall_seconds=20)
        over_payload = self.receipt(request, actual_payload_bytes=1025)
        self.assert_code(
            "C2_PAYLOAD_BUDGET_EXCEEDED",
            lambda: join_owner_host_c2_attempt(request=request, receipt=over_payload),
        )
        over_time = self.receipt(
            request,
            ended_at_utc="2026-08-31T05:10:30+00:00",
            elapsed_seconds=30.0,
            actual_payload_bytes=512,
        )
        self.assert_code(
            "C2_WALL_TIME_BUDGET_EXCEEDED",
            lambda: join_owner_host_c2_attempt(request=request, receipt=over_time),
        )

    def test_receipt_rejects_remote_or_substituted_execution(self):
        self.assert_code(
            "RECEIPT_REMOTE_CODE_FORBIDDEN",
            lambda: self.receipt(trust_remote_code=True),
        )
        self.assert_code(
            "REMOTE_MODEL_EXECUTION_FORBIDDEN",
            lambda: self.receipt(remote_model_execution_observed=True),
        )
        self.assert_code(
            "SMALLER_MODEL_SUBSTITUTION_FORBIDDEN",
            lambda: self.receipt(smaller_model_substitution_observed=True),
        )
        self.assert_code(
            "SYNTHETIC_FIXTURE_SUBSTITUTION_FORBIDDEN",
            lambda: self.receipt(synthetic_fixture_substitution_observed=True),
        )

    def test_c2_receipt_cannot_promote_full_model_or_g2(self):
        self.assert_code(
            "C2_RECEIPT_CANNOT_PROVE_FULL_MODEL_COMPLETENESS",
            lambda: self.receipt(full_model_complete_architecture_proven=True),
        )
        self.assert_code(
            "HANDOFF_CANNOT_AUTHENTICATE_PRODUCER",
            lambda: self.receipt(producer_authenticated_by_this_contract=True),
        )
        self.assert_code(
            "HANDOFF_CANNOT_ADMIT_G2",
            lambda: self.receipt(g2_admitted=True),
        )

    def test_generated_tokens_require_output_digest(self):
        self.assert_code(
            "GENERATED_OUTPUT_DIGEST_REQUIRED",
            lambda: self.receipt(generated_token_count=1, generated_output_sha256=None),
        )

    def test_nonzero_exit_is_recorded_without_false_success(self):
        request = self.request()
        receipt = self.receipt(
            request,
            process_exit_code=1,
            generated_token_count=0,
            generated_output_sha256=None,
        )
        joined = join_owner_host_c2_attempt(request=request, receipt=receipt)
        self.assertFalse(joined.canary_process_succeeded)
        self.assertFalse(joined.generated_output_observed)
        self.assertTrue(joined.producer_authentication_required)


if __name__ == "__main__":
    unittest.main()

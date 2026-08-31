from __future__ import annotations

from dataclasses import replace
import unittest

from airllm_secure_fixture_observation_envelope import (
    AIRLLM_FIXTURE_SCHEMA,
    AIRLLM_SOURCE_HEAD,
    BOUND,
    HOLD,
    PHYSICAL_OBSERVATION_SCHEMA,
    HostPhysicalObservationProjection,
    SecureTinyFixtureProjection,
    bind_secure_fixture_observation,
)


def h(ch: str) -> str:
    return ch * 64


def fixture() -> SecureTinyFixtureProjection:
    return SecureTinyFixtureProjection(
        schema=AIRLLM_FIXTURE_SCHEMA,
        source_head=AIRLLM_SOURCE_HEAD,
        status="PASS",
        model_id="hf-internal-testing/tiny-random-LlamaForCausalLM",
        model_revision="9fb191250dd56d0ba7ec9785a025ed29c03d5998",
        workload_ref="awj032:airllm:tiny-llama:split-generate-reopen:v1",
        device="cpu",
        fixture_manifest_digest=h("1"),
        split_manifest_digest=h("2"),
        runtime_guard_receipt_digest=h("3"),
        first_generated_token_count=1,
        reopen_generated_token_count=1,
        split_manifest_reopen_stable=True,
    )


def observation() -> HostPhysicalObservationProjection:
    f = fixture()
    return HostPhysicalObservationProjection(
        schema=PHYSICAL_OBSERVATION_SCHEMA,
        observer_generation="observer:linux:iostat-plus-backend:v1",
        backend_owner_ref="backend:awj032:fixture-storage:v1",
        operation_id="op:tiny-llama:split-generate-reopen:0001",
        workload_ref=f.workload_ref,
        source_generation=f.source_head,
        fixture_identity_digest=f.fixture_identity_digest,
        fixture_manifest_digest=f.fixture_manifest_digest,
        split_manifest_digest=f.split_manifest_digest,
        physical_io_attestation_ref="attestation:fixture-storage:0001",
        logical_bytes_required=1000,
        physical_demand_bytes=600,
        prefetch_useful_bytes=100,
        prefetch_waste_bytes=50,
        aura_cache_avoided_bytes=200,
        os_cache_avoided_bytes=50,
        other_proven_avoided_bytes=50,
    )


class SecureFixtureObservationEnvelopeTests(unittest.TestCase):
    def test_missing_physical_observation_is_lawful_hold(self):
        result = bind_secure_fixture_observation(fixture=fixture(), observation=None)
        self.assertEqual(result.disposition, HOLD)
        self.assertFalse(result.physical_observation_bound)
        self.assertIsNone(result.relation_id)
        self.assertTrue(result.hard_false_runtime_preserved)
        self.assertFalse(result.glm53_performance_proven)

    def test_exact_operation_bound_observation_binds_deterministically(self):
        a = bind_secure_fixture_observation(fixture=fixture(), observation=observation())
        b = bind_secure_fixture_observation(fixture=fixture(), observation=observation())
        self.assertEqual(a.disposition, BOUND)
        self.assertTrue(a.physical_observation_bound)
        self.assertEqual(a.relation_id, b.relation_id)
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertFalse(a.tiny_fixture_crosscast_to_glm53)
        self.assertFalse(a.model_admission_granted)
        self.assertFalse(a.execution_authority_granted)
        self.assertFalse(a.provider_effect_authority_granted)
        self.assertFalse(a.semantic_k27_authority)
        self.assertFalse(a.native_private_transformer_kv_accessed)
        self.assertFalse(a.gate10_promoted)

    def test_observation_must_bind_exact_fixture_identity(self):
        for field, value in (
            ("workload_ref", "other-workload"),
            ("source_generation", "other-source"),
            ("fixture_identity_digest", h("a")),
            ("fixture_manifest_digest", h("b")),
            ("split_manifest_digest", h("c")),
        ):
            with self.subTest(field=field):
                result = bind_secure_fixture_observation(
                    fixture=fixture(), observation=replace(observation(), **{field: value})
                )
                self.assertEqual(result.disposition, "HOLD_FIXTURE_OBSERVATION_IDENTITY_MISMATCH")
                self.assertFalse(result.physical_observation_bound)

    def test_caller_boolean_without_attestation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "PHYSICAL_IO_ATTESTATION_REQUIRED"):
            bind_secure_fixture_observation(
                fixture=fixture(),
                observation=replace(observation(), physical_io_attested=False),
            )

    def test_exact_operation_binding_and_current_observer_are_required(self):
        for field, value, code in (
            ("exact_operation_bound", False, "EXACT_OPERATION_BOUND_PHYSICAL_RECEIPT_REQUIRED"),
            ("observer_current", False, "PHYSICAL_IO_OBSERVER_CURRENTNESS_REQUIRED"),
            ("avoided_bytes_provenance_complete", False, "AVOIDED_BYTES_PROVENANCE_COMPLETE_REQUIRED"),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, code):
                    bind_secure_fixture_observation(
                        fixture=fixture(), observation=replace(observation(), **{field: value})
                    )

    def test_avoided_byte_accounting_must_close_exactly(self):
        with self.assertRaisesRegex(ValueError, "AVOIDED_BYTE_ACCOUNTING_MUST_CLOSE_EXACTLY"):
            bind_secure_fixture_observation(
                fixture=fixture(),
                observation=replace(observation(), other_proven_avoided_bytes=49),
            )

    def test_tiny_fixture_cannot_be_called_glm53_workload(self):
        with self.assertRaisesRegex(ValueError, "TINY_FIXTURE_CANNOT_BE_CROSSCAST_AS_GLM53_WORKLOAD"):
            bind_secure_fixture_observation(
                fixture=fixture(), observation=replace(observation(), glm53_workload=True)
            )

    def test_fixture_claim_widening_is_rejected(self):
        for field in (
            "remote_code_authorized",
            "large_checkpoint_used",
            "provider_used",
            "glm53_performance_proven",
            "model_admission_granted",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "FIXTURE_CLAIM_CEILING_WIDENED"):
                    bind_secure_fixture_observation(
                        fixture=replace(fixture(), **{field: True}), observation=None
                    )

    def test_observation_authority_widening_is_rejected(self):
        for field in (
            "execution_authority_granted",
            "provider_effect_authority_granted",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "PHYSICAL_OBSERVATION_CLAIM_CEILING_WIDENED"):
                    bind_secure_fixture_observation(
                        fixture=fixture(), observation=replace(observation(), **{field: True})
                    )

    def test_operation_or_observer_drift_changes_relation_identity(self):
        baseline = bind_secure_fixture_observation(fixture=fixture(), observation=observation())
        changed_op = bind_secure_fixture_observation(
            fixture=fixture(), observation=replace(observation(), operation_id="op:tiny:0002")
        )
        changed_observer = bind_secure_fixture_observation(
            fixture=fixture(), observation=replace(observation(), observer_generation="observer:v2")
        )
        self.assertNotEqual(baseline.relation_id, changed_op.relation_id)
        self.assertNotEqual(baseline.relation_id, changed_observer.relation_id)


if __name__ == "__main__":
    unittest.main()

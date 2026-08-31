from __future__ import annotations

from dataclasses import replace
import inspect
from pathlib import Path
import tempfile
import unittest

from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.thinkpad_nvme_residency_plan import (
    ASYNC_NVME_PREFETCH,
    HostStorageProfile,
    ResidencyPolicy,
    TensorSlice,
    build_thinkpad_residency_plan,
)
from tools.awj032.thinkpad_plan_bound_storage_probe import (
    PlanBoundStorageProbeError,
    run_plan_bound_storage_probe,
)

MiB = 1024**2


class ThinkPadPlanBoundStorageProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.payload = bytes(range(256)) * 128
        (self.root / "model.safetensors").write_bytes(self.payload)

        host = HostStorageProfile(
            profile_kind="SYNTHETIC_TEST",
            available_ram_bytes=512 * MiB,
            nvme_sequential_read_bytes_per_second=1024 * MiB,
            page_size_bytes=4096,
            io_uring_supported=True,
            mmap_supported=True,
            direct_io_supported=False,
            source_ref="fixture:o51-host-profile",
        )
        policy = ResidencyPolicy(
            min_ram_reserve_bytes=64 * MiB,
            max_resident_bytes=0,
            max_prefetch_bytes=16 * MiB,
            buffer_count=2,
            max_prefetch_lead_steps=4,
            adjacent_gap_bytes=4096,
        )
        self.plan = build_thinkpad_residency_plan(
            host_profile=host,
            tensors=[
                TensorSlice(
                    tensor_id="layer-0",
                    storage_object_ref="model.safetensors",
                    byte_offset=0,
                    byte_length=8192,
                    first_use_step=3,
                    compute_slack_seconds=1.0,
                    reuse_count=1,
                    role="weight",
                    temperature="COLD",
                )
            ],
            policy=policy,
        )
        self.assertEqual(self.plan.decisions[0].mode, ASYNC_NVME_PREFETCH)
        self.request = OwnerHostC2CanaryRequest(
            w3_proof_logical_id="ab" * 32,
            preflight_receipt_digest="cd" * 32,
            airllm_source_revision="airllm-reviewed-source@deadbeef",
            airllm_security_evidence_digest="12" * 32,
            host_snapshot_digest="34" * 32,
            storage_plan_digest=self.plan.storage_plan_digest,
            workspace_root=str(self.root),
            max_payload_bytes=2 * MiB,
            max_wall_seconds=10,
            effect_admission_ref="owner-effect:awj032:o51-fixture",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_bound(self, *, plan=None, request=None, tensor_id="layer-0"):
        return run_plan_bound_storage_probe(
            plan=plan or self.plan,
            request=request or self.request,
            tensor_id=tensor_id,
            chunk_bytes=4096,
            max_wall_seconds=2.0,
        )

    def assert_code(self, code, fn):
        with self.assertRaises(PlanBoundStorageProbeError) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)

    def test_actual_plan_derives_exact_observed_window(self):
        receipt = self.run_bound()
        decision = self.plan.decisions[0]
        self.assertEqual(receipt.plan_digest, self.plan.storage_plan_digest)
        self.assertEqual(receipt.storage_object_ref, decision.storage_object_ref)
        self.assertEqual(receipt.observation_window_byte_offset, decision.aligned_byte_offset)
        self.assertEqual(receipt.observation_window_bytes, decision.aligned_byte_length)
        self.assertEqual(receipt.logical_bytes_read, decision.aligned_byte_length)
        self.assertTrue(receipt.full_planned_window_observed)
        self.assertTrue(receipt.logical_read_observed)
        self.assertTrue(receipt.plan_identity_bound)

    def test_async_prefetch_plan_mode_is_not_backend_execution(self):
        receipt = self.run_bound()
        self.assertEqual(receipt.planned_mode, ASYNC_NVME_PREFETCH)
        self.assertFalse(receipt.planned_backend_observed)
        self.assertFalse(receipt.planned_backend_executed)
        self.assertFalse(receipt.storage_plan_compliance_proven)
        self.assertFalse(receipt.page_cache_bypass_proven)
        self.assertFalse(receipt.os_page_cache_cold_proven)
        self.assertFalse(receipt.device_cache_cold_proven)
        self.assertFalse(receipt.physical_nvme_io_attested)
        self.assertFalse(receipt.storage_medium_nvme_proven)
        self.assertFalse(receipt.performance_winner_proven)
        self.assertFalse(receipt.w4_admitted)
        self.assertFalse(receipt.g2_admitted)
        self.assertFalse(receipt.effect_authority_proven)

    def test_request_plan_digest_mismatch_fails_before_read(self):
        foreign = replace(self.request, storage_plan_digest="56" * 32)
        self.assert_code(
            "REQUEST_PLAN_DIGEST_MISMATCH",
            lambda: self.run_bound(request=foreign),
        )

    def test_plan_nonauthority_ceiling_cannot_be_widened(self):
        widened = replace(self.plan, physical_io_observed=True)
        self.assert_code(
            "PLAN_NONEXECUTION_CEILING_WIDENED",
            lambda: self.run_bound(plan=widened),
        )

    def test_unknown_tensor_cannot_select_arbitrary_path(self):
        self.assert_code(
            "EXACT_ONE_PLAN_DECISION_REQUIRED",
            lambda: self.run_bound(tensor_id="../../other"),
        )

    def test_short_file_does_not_become_plan_compliance(self):
        (self.root / "model.safetensors").write_bytes(b"short")
        self.assert_code(
            "PLANNED_OBSERVATION_WINDOW_NOT_FULLY_READ",
            self.run_bound,
        )

    def test_plan_change_changes_bound_identity(self):
        changed_plan = build_thinkpad_residency_plan(
            host_profile=self.plan.host_profile,
            tensors=[
                TensorSlice(
                    tensor_id="layer-0",
                    storage_object_ref="model.safetensors",
                    byte_offset=4096,
                    byte_length=4096,
                    first_use_step=3,
                    compute_slack_seconds=1.0,
                    role="weight",
                    temperature="COLD",
                )
            ],
            policy=self.plan.policy,
        )
        changed_request = replace(
            self.request,
            storage_plan_digest=changed_plan.storage_plan_digest,
        )
        original = self.run_bound()
        changed = self.run_bound(plan=changed_plan, request=changed_request)
        self.assertNotEqual(original.plan_digest, changed.plan_digest)
        self.assertNotEqual(
            original.observation_window_byte_offset,
            changed.observation_window_byte_offset,
        )
        self.assertNotEqual(original.receipt_digest, changed.receipt_digest)

    def test_public_boundary_has_no_path_digest_backend_or_authority_override(self):
        params = tuple(inspect.signature(run_plan_bound_storage_probe).parameters)
        self.assertEqual(
            params,
            ("plan", "request", "tensor_id", "chunk_bytes", "max_wall_seconds"),
        )
        forbidden = {
            "relative_path",
            "byte_offset",
            "probe_bytes",
            "storage_plan_digest",
            "planned_backend_executed",
            "physical_nvme_io_attested",
            "page_cache_bypass_proven",
            "w4_admitted",
            "g2_admitted",
            "effect_authority_proven",
        }
        self.assertTrue(forbidden.isdisjoint(params))

    def test_receipt_identity_is_deterministic_except_observation_timing(self):
        a = self.run_bound()
        b = self.run_bound()
        self.assertEqual(a.plan_digest, b.plan_digest)
        self.assertEqual(a.request_digest, b.request_digest)
        self.assertEqual(a.logical_window_sha256, b.logical_window_sha256)
        self.assertEqual(a.logical_bytes_read, b.logical_bytes_read)
        self.assertEqual(a.observation_window_bytes, b.observation_window_bytes)
        # elapsed-derived throughput is observational and intentionally may vary,
        # so the complete receipt digest is not asserted equal across runs.


if __name__ == "__main__":
    unittest.main()

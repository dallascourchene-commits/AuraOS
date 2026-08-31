from __future__ import annotations

import unittest

from tools.awj032.thinkpad_nvme_residency_plan import (
    ASYNC_NVME_PREFETCH,
    MMAP_DEMAND,
    RAM_RESIDENT,
    HostStorageProfile,
    ResidencyPolicy,
    TensorSlice,
    ThinkPadResidencyPlanError,
    build_thinkpad_residency_plan,
)


GiB = 1024**3
MiB = 1024**2


class ThinkPadNVMeResidencyPlanTests(unittest.TestCase):
    def host(self, **updates):
        values = dict(
            profile_kind="SYNTHETIC_TEST",
            available_ram_bytes=16 * GiB,
            nvme_sequential_read_bytes_per_second=3 * GiB,
            page_size_bytes=4096,
            io_uring_supported=True,
            mmap_supported=True,
            direct_io_supported=False,
            source_ref="fixture:thinkpad-storage-profile-v1",
        )
        values.update(updates)
        return HostStorageProfile(**values)

    def policy(self, **updates):
        values = dict(
            min_ram_reserve_bytes=4 * GiB,
            max_resident_bytes=4 * GiB,
            max_prefetch_bytes=256 * MiB,
            buffer_count=2,
            max_prefetch_lead_steps=4,
            adjacent_gap_bytes=4096,
        )
        values.update(updates)
        return ResidencyPolicy(**values)

    def test_hot_reused_slice_is_ram_resident_without_overcommit(self):
        tensors = [
            TensorSlice(
                "router",
                "shard-00001.safetensors",
                1,
                32 * MiB,
                0,
                0.02,
                reuse_count=20,
                role="router",
                temperature="HOT",
            ),
            TensorSlice(
                "expert",
                "shard-00002.safetensors",
                0,
                512 * MiB,
                1,
                0.1,
                reuse_count=1,
                role="expert",
                temperature="WARM",
            ),
        ]
        plan = build_thinkpad_residency_plan(
            host_profile=self.host(),
            tensors=tensors,
            policy=self.policy(max_resident_bytes=64 * MiB),
        )
        modes = {d.tensor_id: d.mode for d in plan.decisions}
        self.assertEqual(modes["router"], RAM_RESIDENT)
        self.assertNotEqual(modes["expert"], RAM_RESIDENT)
        self.assertLessEqual(plan.ram_committed_bytes, plan.ram_budget_bytes)

    def test_io_uring_prefetch_uses_compute_slack_and_double_buffer_slot(self):
        tensor = TensorSlice(
            "layer-7",
            "model-00001.safetensors",
            0,
            96 * MiB,
            7,
            0.02,
            reuse_count=1,
            role="weight",
            temperature="COLD",
        )
        plan = build_thinkpad_residency_plan(
            host_profile=self.host(),
            tensors=[tensor],
            policy=self.policy(),
        )
        decision = plan.decisions[0]
        self.assertEqual(decision.mode, ASYNC_NVME_PREFETCH)
        self.assertEqual(decision.prefetch_lead_steps, 2)
        self.assertEqual(decision.issue_step, 5)
        self.assertEqual(decision.buffer_slot, 1)

    def test_prefetch_falls_back_to_mmap_when_deadline_cannot_be_hidden(self):
        tensor = TensorSlice(
            "oversized",
            "model.safetensors",
            0,
            512 * MiB,
            2,
            0.001,
            role="weight",
            temperature="COLD",
        )
        plan = build_thinkpad_residency_plan(
            host_profile=self.host(),
            tensors=[tensor],
            policy=self.policy(max_prefetch_bytes=128 * MiB),
        )
        self.assertEqual(plan.decisions[0].mode, MMAP_DEMAND)
        self.assertEqual(plan.decisions[0].prefetch_lead_steps, 0)

    def test_adjacent_async_reads_are_coalesced_only_within_same_lane(self):
        tensors = [
            TensorSlice(
                "a", "shard.safetensors", 0, 8 * MiB, 4, 0.02,
                role="expert", temperature="COLD"
            ),
            TensorSlice(
                "b", "shard.safetensors", 8 * MiB, 8 * MiB, 4, 0.02,
                role="expert", temperature="COLD"
            ),
        ]
        plan = build_thinkpad_residency_plan(
            host_profile=self.host(),
            tensors=tensors,
            policy=self.policy(max_prefetch_bytes=64 * MiB),
        )
        self.assertEqual(len(plan.prefetch_batches), 1)
        batch = plan.prefetch_batches[0]
        self.assertEqual(batch.tensor_ids, ("a", "b"))
        self.assertEqual(batch.aligned_byte_length, 16 * MiB)

    def test_page_alignment_is_explicit(self):
        tensor = TensorSlice(
            "unaligned", "shard", 7, 4097, 1, 1.0,
            role="index", temperature="COLD"
        )
        plan = build_thinkpad_residency_plan(
            host_profile=self.host(io_uring_supported=False),
            tensors=[tensor],
            policy=self.policy(),
        )
        decision = plan.decisions[0]
        self.assertEqual(decision.aligned_byte_offset, 0)
        self.assertEqual(decision.aligned_byte_length, 8192)

    def test_no_storage_backend_fails_closed(self):
        tensor = TensorSlice(
            "x", "shard", 0, 4096, 1, 1.0,
            role="weight", temperature="COLD"
        )
        with self.assertRaisesRegex(ThinkPadResidencyPlanError, "NO_SUPPORTED_STORAGE_PATH"):
            build_thinkpad_residency_plan(
                host_profile=self.host(
                    io_uring_supported=False,
                    mmap_supported=False,
                    direct_io_supported=False,
                ),
                tensors=[tensor],
                policy=self.policy(),
            )

    def test_bool_int_confusion_is_rejected(self):
        with self.assertRaisesRegex(ThinkPadResidencyPlanError, "AVAILABLE_RAM_BYTES_INVALID"):
            self.host(available_ram_bytes=True)

    def test_plan_digest_is_deterministic_and_nonauthorizing(self):
        tensors = [
            TensorSlice(
                "x", "shard", 0, 4 * MiB, 3, 0.01,
                reuse_count=2, role="kv", temperature="HOT"
            )
        ]
        a = build_thinkpad_residency_plan(
            host_profile=self.host(), tensors=tensors, policy=self.policy()
        )
        b = build_thinkpad_residency_plan(
            host_profile=self.host(), tensors=list(tensors), policy=self.policy()
        )
        self.assertEqual(a.plan_digest, b.plan_digest)
        self.assertEqual(a.storage_plan_digest, a.plan_digest)
        self.assertFalse(a.physical_io_observed)
        self.assertFalse(a.model_execution_observed)
        self.assertFalse(a.producer_authenticated)
        self.assertFalse(a.performance_claimed)
        self.assertFalse(a.effect_authority_proven)
        self.assertFalse(a.g2_admitted)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.awj032.thinkpad_nvme_residency_plan import (
    HostStorageProfile,
    ResidencyPolicy,
    TensorSlice,
)
from tools.k27_astge_plan_bound_thinkpad_benchmark import (
    PlanBoundBenchmarkRequest,
    admit_plan_bound_benchmark_evidence,
    build_plan_bound_benchmark_request,
)
from tools.k27_astge_thinkpad_owner_host_benchmark import PR477_SAFE_SHA
from tests.test_k27_astge_thinkpad_owner_host_benchmark import D, E, F, samples

GiB = 1024**3
MiB = 1024**2


def host(**updates):
    values = dict(
        profile_kind="SYNTHETIC_TEST",
        available_ram_bytes=16 * GiB,
        nvme_sequential_read_bytes_per_second=3 * GiB,
        page_size_bytes=4096,
        io_uring_supported=True,
        mmap_supported=True,
        direct_io_supported=False,
        source_ref="fixture:o50-thinkpad-storage-profile-v1",
    )
    values.update(updates)
    return HostStorageProfile(**values)


def policy(**updates):
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


def tensors():
    return (
        TensorSlice(
            "router",
            "model-00001.safetensors",
            0,
            32 * MiB,
            0,
            0.02,
            reuse_count=20,
            role="router",
            temperature="HOT",
        ),
        TensorSlice(
            "expert-7",
            "model-00002.safetensors",
            64 * MiB,
            96 * MiB,
            7,
            0.02,
            reuse_count=1,
            role="expert",
            temperature="COLD",
        ),
    )


def binding(**updates):
    values = dict(
        host_profile=host(),
        tensors=tensors(),
        policy=policy(),
        graph_sha256=D,
        source_fixture_sha256=E,
        root_node_ids=(0, 17, 99),
        max_depth=3,
        iterations=10,
        implementation_generation=PR477_SAFE_SHA,
        runner_generation="thinkpad-wsl-runner:v1",
        host_snapshot_digest=F,
    )
    values.update(updates)
    return build_plan_bound_benchmark_request(**values)


class PlanBoundThinkPadBenchmarkTests(unittest.TestCase):
    def test_plan_digest_is_derived_and_bound_to_pr597_request(self) -> None:
        bound = binding()
        self.assertEqual(bound.plan.storage_plan_digest, bound.request.storage_plan_digest)
        self.assertTrue(bound.storage_plan_digest_derived_from_pr599)
        self.assertFalse(bound.storage_plan_execution_observed)
        self.assertFalse(bound.planned_backend_observed)
        self.assertFalse(bound.physical_io_attested)
        self.assertFalse(bound.w4_admitted)

    def test_builder_has_no_storage_plan_or_execution_override(self) -> None:
        params = set(inspect.signature(build_plan_bound_benchmark_request).parameters)
        for forbidden in (
            "storage_plan_digest",
            "storage_plan_execution_observed",
            "planned_backend_observed",
            "physical_io_attested",
            "os_page_cache_cold_required",
            "device_cache_cold_required",
            "performance_winner_claim_requested",
            "effect_authority_requested",
        ):
            self.assertNotIn(forbidden, params)

    def test_host_profile_change_changes_plan_and_binding_identity(self) -> None:
        a = binding()
        b = binding(host_profile=host(io_uring_supported=False))
        self.assertNotEqual(a.plan.storage_plan_digest, b.plan.storage_plan_digest)
        self.assertNotEqual(a.request.request_digest, b.request.request_digest)
        self.assertNotEqual(a.binding_digest, b.binding_digest)
        self.assertFalse(a.host_profile_observed_by_this_membrane)
        self.assertFalse(b.host_profile_observed_by_this_membrane)

    def test_tensor_change_changes_plan_and_binding_identity(self) -> None:
        a = binding()
        changed = list(tensors())
        changed[1] = replace(changed[1], byte_length=128 * MiB)
        b = binding(tensors=tuple(changed))
        self.assertNotEqual(a.plan.storage_plan_digest, b.plan.storage_plan_digest)
        self.assertNotEqual(a.binding_digest, b.binding_digest)

    def test_foreign_storage_plan_digest_is_rejected_at_relation_layer(self) -> None:
        bound = binding()
        foreign_request = replace(bound.request, storage_plan_digest="ff" * 32)
        with self.assertRaisesRegex(ValueError, "STORAGE_PLAN_DIGEST_RELATION_MISMATCH"):
            PlanBoundBenchmarkRequest(plan=bound.plan, request=foreign_request)

    def test_exact_three_phase_benchmark_remains_nonexecuting_for_plan(self) -> None:
        bound = binding()
        out = admit_plan_bound_benchmark_evidence(
            binding=bound,
            samples=samples(bound.request),
            host_observation_id="thinkpad-wsl:o50:001",
            runner_identity="aura-owner-host-benchmark-runner",
        )
        self.assertTrue(out["storage_plan_digest_bound_to_request"])
        self.assertFalse(out["storage_plan_execution_observed"])
        self.assertFalse(out["planned_backend_observed"])
        self.assertFalse(out["benchmark_counters_prove_storage_plan_compliance"])
        self.assertFalse(out["process_cold_proves_os_page_cache_cold"])
        self.assertFalse(out["process_cold_proves_device_cache_cold"])
        self.assertFalse(out["physical_io_attested"])
        self.assertFalse(out["producer_authenticated"])
        self.assertFalse(out["w4_admitted"])
        self.assertFalse(out["real_performance_winner_proven"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(any(out["authority"].values()))

    def test_device_counter_deltas_still_do_not_prove_plan_execution_or_physical_io(self) -> None:
        bound = binding()
        out = admit_plan_bound_benchmark_evidence(
            binding=bound,
            samples=samples(bound.request, with_device=True),
            host_observation_id="thinkpad-wsl:o50:device-counter",
            runner_identity="aura-owner-host-benchmark-runner",
        )
        self.assertFalse(out["storage_plan_execution_observed"])
        self.assertFalse(out["benchmark_counters_prove_storage_plan_compliance"])
        self.assertFalse(out["physical_io_attested"])

    def test_plan_modes_are_not_observed_backend_claims(self) -> None:
        bound = binding()
        self.assertTrue(bound.plan.decisions)
        self.assertTrue(any(decision.mode for decision in bound.plan.decisions))
        self.assertFalse(bound.planned_backend_observed)

    def test_deterministic_binding_and_receipt(self) -> None:
        a = binding()
        b = binding()
        self.assertEqual(a.binding_digest, b.binding_digest)
        first = admit_plan_bound_benchmark_evidence(
            binding=a,
            samples=samples(a.request),
            host_observation_id="thinkpad-wsl:o50:deterministic",
            runner_identity="aura-owner-host-benchmark-runner",
        )
        second = admit_plan_bound_benchmark_evidence(
            binding=b,
            samples=samples(b.request),
            host_observation_id="thinkpad-wsl:o50:deterministic",
            runner_identity="aura-owner-host-benchmark-runner",
        )
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()

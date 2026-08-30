from dataclasses import replace
import math
import unittest

import glm53_backend_io_evidence_guard as guard
import glm53_host_canary_preflight as p


def host(*, free_space=1_000_000_000_000, read_bps=3_000_000_000):
    return p.HostSnapshot(
        observation_id="host-snapshot-001",
        currentness_ref="arena-currentness-gen25",
        cpu_model="ThinkPad CPU fixture",
        cpu_logical_cores=16,
        ram_total_bytes=64_000_000_000,
        ram_available_bytes=40_000_000_000,
        ram_commit_available_bytes=50_000_000_000,
        gpu_present=True,
        gpu_model="fixture-gpu",
        vram_total_bytes=8_000_000_000,
        vram_available_bytes=7_000_000_000,
        gpu_driver="fixture-driver",
        cuda_capability="8.6",
        nvme_model="fixture-nvme",
        filesystem="ext4-wsl",
        free_space_bytes=free_space,
        sequential_read_bytes_per_s=read_bps,
        sequential_write_bytes_per_s=2_000_000_000,
        random_read_iops=100_000,
        thermal_celsius=55.0,
        power_source="AC",
        battery_percent=90.0,
        foreground_load_percent=10.0,
        python_version="3.11",
        torch_version="2.x",
        transformers_version="5.15.0",
        airllm_revision="c92cea691412715a218306acb01fc9c2c681a8f2",
    )


def storage(*, c2=6_000_000_000, representation=756_000_000_000, temporary=20_000_000_000, reserve=10_000_000_000):
    return p.RepresentationStoragePlan(
        model_revision="a" * 40,
        representation_id="GLM53-FP8-source-bound",
        published_source_bytes=756_000_000_000,
        representation_bytes=representation,
        temporary_conversion_bytes=temporary,
        c2_canary_bytes=c2,
        safety_reserve_bytes=reserve,
        source_recoverable=True,
    )


def io_bound():
    return p.ColdExpertIOBound(
        sparse_layers=75,
        routed_experts_per_token=8,
        shared_experts_per_layer=1,
        bytes_per_expert=37_748_736,
    )


class FakeBackend:
    def __init__(self, *, physical_bytes=12_740_198_400, elapsed_ms=5000.0):
        self.physical_bytes = physical_bytes
        self.elapsed_ms = elapsed_ms

    def io_attestation(self, binding_digest):
        return {
            "schema": guard.BACKEND_IO_ATTESTATION_SCHEMA,
            "binding_digest": binding_digest,
            "attestation_id": "thinkpad-w4-fixture",
            "physical_selected_only": True,
            "whole_bank_reads": 0,
            "whole_bank_materialized": False,
            "physical_expert_bytes_read": self.physical_bytes,
            "physical_read_operations": 128,
            "read_elapsed_ms": self.elapsed_ms,
            "page_cache_provenance": "MEASURED_HOST_PAGE_CACHE_STATE",
        }


def w4(*, physical_bytes=12_740_198_400, elapsed_ms=5000.0):
    return guard.validate_backend_evidence(
        FakeBackend(physical_bytes=physical_bytes, elapsed_ms=elapsed_ms),
        binding_digest="pager-binding-001",
    )


class HostCanaryPreflightTests(unittest.TestCase):
    def test_preregistered_cold_expert_floor_matches_work_order(self):
        self.assertEqual(25_480_396_800, io_bound().cold_expert_bytes_per_token)

    def test_complete_measurements_compile_nonpromoting_plan(self):
        bound = io_bound()
        receipt = p.compile_host_canary_preflight(
            host=host(),
            storage=storage(),
            io_bound=bound,
            w4=w4(),
            logical_expert_bytes_required=bound.cold_expert_bytes_per_token,
            targets=(
                p.PerformanceTarget("interactive-candidate", 5.0),
                p.PerformanceTarget("batch-candidate", 10.0),
            ),
        )
        self.assertTrue(math.isclose(receipt.measured_reuse_ratio, 0.5, rel_tol=0, abs_tol=1e-12))
        self.assertTrue(math.isclose(receipt.cold_nvme_floor_seconds_per_token, 8.4934656, rel_tol=0, abs_tol=1e-7))
        self.assertGreater(receipt.target_min_reuse_ratio["interactive-candidate"], 0)
        self.assertEqual(0.0, receipt.target_min_reuse_ratio["batch-candidate"])
        self.assertTrue(receipt.c2_storage_ready)
        self.assertTrue(receipt.c3_storage_ready)
        self.assertTrue(receipt.planning_ready)
        self.assertEqual("C2_EFFECT_ADMISSION_REQUIRED", receipt.next_canary)
        self.assertFalse(receipt.execution_authorized)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.g2_admitted)
        self.assertFalse(receipt.large_checkpoint_admitted)
        self.assertFalse(receipt.runtime_execution_proven)

    def test_storage_shortage_blocks_c2_without_deleting_source(self):
        receipt = p.compile_host_canary_preflight(
            host=host(free_space=5_000_000_000),
            storage=storage(c2=6_000_000_000, reserve=1_000_000_000),
            io_bound=io_bound(),
            w4=w4(),
            logical_expert_bytes_required=io_bound().cold_expert_bytes_per_token,
        )
        self.assertFalse(receipt.c2_storage_ready)
        self.assertFalse(receipt.planning_ready)
        self.assertEqual("BLOCKED_RESOURCE", receipt.next_canary)

    def test_c2_can_fit_while_c3_full_materialization_does_not(self):
        receipt = p.compile_host_canary_preflight(
            host=host(free_space=100_000_000_000),
            storage=storage(),
            io_bound=io_bound(),
            w4=w4(),
            logical_expert_bytes_required=io_bound().cold_expert_bytes_per_token,
        )
        self.assertTrue(receipt.c2_storage_ready)
        self.assertFalse(receipt.c3_storage_ready)
        self.assertTrue(receipt.planning_ready)
        self.assertEqual("C2_EFFECT_ADMISSION_REQUIRED", receipt.next_canary)

    def test_unattested_or_incomplete_w4_is_not_planning_evidence(self):
        unknown = guard.validate_backend_evidence(object(), binding_digest="pager-binding-001")
        with self.assertRaises(p.HostPreflightError) as ctx:
            p.compile_host_canary_preflight(
                host=host(), storage=storage(), io_bound=io_bound(), w4=unknown,
                logical_expert_bytes_required=io_bound().cold_expert_bytes_per_token,
            )
        self.assertEqual("W4_EVIDENCE_NOT_ADMISSIBLE", ctx.exception.code)

    def test_w4_authority_widening_is_rejected(self):
        widened = replace(w4(), g2_admitted=True)
        with self.assertRaises(p.HostPreflightError) as ctx:
            p.compile_host_canary_preflight(
                host=host(), storage=storage(), io_bound=io_bound(), w4=widened,
                logical_expert_bytes_required=io_bound().cold_expert_bytes_per_token,
            )
        self.assertEqual("W4_AUTHORITY_WIDENING", ctx.exception.code)

    def test_physical_io_amplification_clamps_reuse_to_zero(self):
        logical = io_bound().cold_expert_bytes_per_token
        receipt = p.compile_host_canary_preflight(
            host=host(), storage=storage(), io_bound=io_bound(),
            w4=w4(physical_bytes=logical + 1_000_000_000),
            logical_expert_bytes_required=logical,
        )
        self.assertTrue(receipt.physical_io_amplification)
        self.assertEqual(0.0, receipt.measured_reuse_ratio)

    def test_positive_physical_bytes_require_elapsed_time(self):
        with self.assertRaises(p.HostPreflightError) as ctx:
            p.compile_host_canary_preflight(
                host=host(), storage=storage(), io_bound=io_bound(),
                w4=w4(physical_bytes=1, elapsed_ms=0),
                logical_expert_bytes_required=io_bound().cold_expert_bytes_per_token,
            )
        self.assertEqual("POSITIVE_PHYSICAL_BYTES_REQUIRE_ELAPSED_TIME", ctx.exception.code)

    def test_performance_targets_are_policy_inputs_not_invented_thresholds(self):
        with self.assertRaises(p.HostPreflightError) as ctx:
            p.compile_host_canary_preflight(
                host=host(), storage=storage(), io_bound=io_bound(), w4=w4(),
                logical_expert_bytes_required=io_bound().cold_expert_bytes_per_token,
                targets=(p.PerformanceTarget("same", 5.0), p.PerformanceTarget("same", 6.0)),
            )
        self.assertEqual("PERFORMANCE_TARGET_DUPLICATE", ctx.exception.code)

    def test_gpu_absence_is_explicit_not_fabricated(self):
        no_gpu = replace(
            host(),
            gpu_present=False,
            gpu_model=None,
            vram_total_bytes=0,
            vram_available_bytes=0,
            gpu_driver=None,
            cuda_capability=None,
        )
        receipt = p.compile_host_canary_preflight(
            host=no_gpu, storage=storage(), io_bound=io_bound(), w4=w4(),
            logical_expert_bytes_required=io_bound().cold_expert_bytes_per_token,
        )
        self.assertTrue(receipt.host_measurement_complete)
        self.assertFalse(receipt.g2_admitted)


if __name__ == "__main__":
    unittest.main()

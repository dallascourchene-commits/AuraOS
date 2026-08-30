import unittest

from glm53_pager_cache_telemetry import CACHE_SCHEMA, CacheTelemetryReceipt
from glm53_w4_host_preflight import (
    COLD_EXPERT_WEIGHT_BYTES_PER_TOKEN,
    W4CounterSnapshot,
    W4PreflightError,
    evaluate_w4_counters,
    required_avoid_fraction,
    snapshot_from_cache_telemetry,
)


def _cache_receipt(*, physical, attested=True, cache_bytes=0, backend_logical=1000, attestation_id="fixture-attestation"):
    return CacheTelemetryReceipt(
        schema=CACHE_SCHEMA,
        binding_digest="binding",
        layer_id="model.layers.3",
        selected_experts=(1,),
        cache_budget_bytes=4096,
        cache_state_before="COLD",
        cache_state_after="WARM",
        cache_epoch=0,
        cache_hit_entries=0 if cache_bytes == 0 else 6,
        cache_miss_entries=6 if backend_logical else 0,
        cache_bytes_served=cache_bytes,
        logical_backend_bytes_required=backend_logical,
        cache_entries_after=6,
        cache_experts_after=1,
        cache_bytes_after=1000,
        evicted_entries=0,
        eviction_reason=None,
        backend_read_operations=6 if backend_logical else 0,
        logical_source_ranges=(),
        physical_io_attested=attested,
        physical_expert_bytes_read=physical,
        physical_selected_only=True if attested else None,
        whole_bank_reads=0 if attested else None,
        whole_bank_materialized=False if attested else None,
        backend_attestation_id=attestation_id if attested else None,
        page_cache_provenance=None,
        cache_energy_joules=None,
    )


class W4HostPreflightTests(unittest.TestCase):
    def test_required_avoid_fraction_matches_cold_bound_example(self):
        got = required_avoid_fraction(
            logical_expert_bytes_required=COLD_EXPERT_WEIGHT_BYTES_PER_TOKEN,
            effective_bandwidth_bytes_per_s=3_000_000_000,
            exposed_io_budget_seconds=1.0,
        )
        self.assertAlmostEqual(got, 1.0 - 3_000_000_000 / COLD_EXPERT_WEIGHT_BYTES_PER_TOKEN, places=12)

    def test_prefetch_overlap_can_lower_exposed_time_without_avoiding_bytes(self):
        receipt = evaluate_w4_counters(
            W4CounterSnapshot(
                scope_ref="synthetic-prefetch",
                source_generation="g1",
                workload_ref="w1",
                logical_expert_bytes_required=1000,
                physical_demand_expert_bytes=0,
                prefetch_useful_bytes=1000,
                prefetch_waste_bytes=200,
                aura_cache_avoided_bytes=0,
                os_cache_avoided_bytes=0,
                other_proven_avoided_bytes=0,
                effective_bandwidth_bytes_per_s=1000.0,
                overlap_seconds=0.75,
                queue_seconds=0.0,
                exposed_io_budget_seconds=0.5,
            )
        )
        self.assertEqual(0.0, receipt.avoid_fraction)
        self.assertEqual(1200, receipt.physical_total_expert_bytes)
        self.assertAlmostEqual(1.2, receipt.service_seconds)
        self.assertAlmostEqual(0.45, receipt.exposed_seconds)
        self.assertTrue(receipt.expert_io_budget_met)
        self.assertFalse(receipt.end_to_end_usability_proven)
        self.assertFalse(receipt.g2_admitted)

    def test_cache_avoidance_reduces_physical_consumed_bytes(self):
        receipt = evaluate_w4_counters(
            W4CounterSnapshot(
                scope_ref="synthetic-cache",
                source_generation="g1",
                workload_ref="w1",
                logical_expert_bytes_required=1000,
                physical_demand_expert_bytes=400,
                prefetch_useful_bytes=0,
                prefetch_waste_bytes=0,
                aura_cache_avoided_bytes=600,
                os_cache_avoided_bytes=0,
                other_proven_avoided_bytes=0,
                effective_bandwidth_bytes_per_s=1000.0,
                overlap_seconds=0.0,
                queue_seconds=0.0,
            )
        )
        self.assertEqual(600, receipt.avoided_expert_bytes)
        self.assertEqual(400, receipt.physical_total_expert_bytes)
        self.assertAlmostEqual(0.6, receipt.avoid_fraction)
        self.assertAlmostEqual(0.4, receipt.exposed_seconds)

    def test_avoided_bytes_cannot_be_double_counted(self):
        with self.assertRaises(W4PreflightError) as ctx:
            evaluate_w4_counters(
                W4CounterSnapshot(
                    scope_ref="bad-accounting",
                    source_generation="g1",
                    workload_ref="w1",
                    logical_expert_bytes_required=1000,
                    physical_demand_expert_bytes=600,
                    prefetch_useful_bytes=0,
                    prefetch_waste_bytes=0,
                    aura_cache_avoided_bytes=500,
                    os_cache_avoided_bytes=0,
                    other_proven_avoided_bytes=0,
                    effective_bandwidth_bytes_per_s=1000.0,
                    overlap_seconds=0.0,
                    queue_seconds=0.0,
                )
            )
        self.assertEqual("AVOIDED_BYTE_ACCOUNTING_MISMATCH", ctx.exception.code)

    def test_current_cache_owner_unknown_physical_bytes_blocks_w4(self):
        with self.assertRaises(W4PreflightError) as ctx:
            snapshot_from_cache_telemetry(
                _cache_receipt(physical=None, attested=True),
                scope_ref="miss",
                source_generation="g1",
                workload_ref="w1",
                effective_bandwidth_bytes_per_s=1000.0,
            )
        self.assertEqual("PHYSICAL_BYTES_UNOBSERVED", ctx.exception.code)

    def test_cache_only_attested_receipt_can_reduce_operation_scope(self):
        snapshot = snapshot_from_cache_telemetry(
            _cache_receipt(physical=0, attested=True, cache_bytes=1000, backend_logical=0),
            scope_ref="cache-only",
            source_generation="g1",
            workload_ref="w1",
            effective_bandwidth_bytes_per_s=1000.0,
        )
        receipt = evaluate_w4_counters(snapshot)
        self.assertEqual(1.0, receipt.avoid_fraction)
        self.assertEqual(0, receipt.physical_total_expert_bytes)
        self.assertEqual(0.0, receipt.exposed_seconds)
        self.assertTrue(receipt.physical_io_attested)

    def test_unknown_non_aura_avoidance_provenance_blocks_adapter(self):
        with self.assertRaises(W4PreflightError) as ctx:
            snapshot_from_cache_telemetry(
                _cache_receipt(physical=500, attested=True, cache_bytes=400, backend_logical=600),
                scope_ref="mixed",
                source_generation="g1",
                workload_ref="w1",
                effective_bandwidth_bytes_per_s=1000.0,
            )
        self.assertEqual("AVOIDED_BYTES_PROVENANCE_INCOMPLETE", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()

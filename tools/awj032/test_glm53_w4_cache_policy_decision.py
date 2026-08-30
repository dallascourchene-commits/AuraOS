from dataclasses import replace
import unittest

from tools.awj032.glm53_w4_cache_policy_decision import (
    W4CachePolicyDecisionError,
    W4CachePolicyObservation,
    compare_cache_policy_to_baseline,
)
from tools.awj032.glm53_w4_host_preflight import W4CounterSnapshot, evaluate_w4_counters


class W4CachePolicyDecisionTests(unittest.TestCase):
    def preflight(self, *, demand=800, aura_avoided=200, os_avoided=0, other_avoided=0,
                  prefetch_useful=0, prefetch_waste=0, overlap=0.0, queue=0.05,
                  source="glm53-source-generation", workload="trace-A",
                  scope="same-host-fixture", attested=True):
        return evaluate_w4_counters(W4CounterSnapshot(
            scope_ref=scope,
            source_generation=source,
            workload_ref=workload,
            logical_expert_bytes_required=1000,
            physical_demand_expert_bytes=demand,
            prefetch_useful_bytes=prefetch_useful,
            prefetch_waste_bytes=prefetch_waste,
            aura_cache_avoided_bytes=aura_avoided,
            os_cache_avoided_bytes=os_avoided,
            other_proven_avoided_bytes=other_avoided,
            effective_bandwidth_bytes_per_s=1000.0,
            overlap_seconds=overlap,
            queue_seconds=queue,
            exposed_io_budget_seconds=1.0,
            physical_io_attested=attested,
            physical_io_attestation_ref="fixture-attestation" if attested else None,
        ))

    def obs(self, policy_id, *, policy_class="BASELINE", preflight=None,
            campaign="campaign-A", lifecycle_ref=None, lifecycle_attested=True,
            hit=0.2, energy=10.0, memory=1000, warmup=2.0, restart=3.0,
            revalidation=0.5, control=0.1, correctness=True, source_current=True,
            measurement_current=True):
        return W4CachePolicyObservation(
            policy_id=policy_id,
            policy_class=policy_class,
            preflight=preflight or self.preflight(),
            measurement_campaign_ref=campaign,
            lifecycle_measurement_attestation_ref=lifecycle_ref or f"attestation:{policy_id}",
            lifecycle_metrics_attested=lifecycle_attested,
            correctness_reference_equivalent=correctness,
            source_current=source_current,
            measurement_current=measurement_current,
            cache_hit_ratio=hit,
            energy_joules=energy,
            peak_resident_bytes=memory,
            warmup_seconds=warmup,
            restart_seconds=restart,
            revalidation_seconds=revalidation,
            control_overhead_seconds=control,
        )

    def assert_code(self, expected, fn):
        with self.assertRaises(W4CachePolicyDecisionError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_candidate_must_pareto_dominate_before_replacing_baseline(self):
        baseline = self.obs("OS_PAGE_CACHE")
        candidate = self.obs(
            "ADAPTIVE_RECENCY_FREQUENCY", policy_class="ADAPTIVE",
            preflight=self.preflight(demand=600, aura_avoided=400), hit=0.5,
            energy=8.0, memory=900, warmup=1.5, restart=2.5,
            revalidation=0.4, control=0.08,
        )
        out = compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate)
        self.assertEqual("CANDIDATE_PARETO_DOMINATES_BASELINE", out.relation)
        self.assertEqual("ADAPTIVE_RECENCY_FREQUENCY", out.retained_policy_id)
        self.assertEqual("campaign-A", out.measurement_campaign_ref)
        self.assertTrue(out.higher_hit_ratio_not_used_as_authority)
        self.assertFalse(out.k27_or_geometry_privileged)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.runtime_execution_proven)
        self.assertFalse(out.quality_proven)
        self.assertFalse(out.authority)

    def test_k27_higher_hit_rate_does_not_override_lifecycle_tradeoff(self):
        baseline = self.obs("LRU", hit=0.30)
        k27 = self.obs(
            "K27_GEOMETRIC", policy_class="K27_GEOMETRIC",
            preflight=self.preflight(demand=700, aura_avoided=300), hit=0.90,
            energy=14.0, memory=1800, warmup=4.0, restart=5.0,
            revalidation=0.8, control=0.3,
        )
        out = compare_cache_policy_to_baseline(baseline=baseline, candidate=k27)
        self.assertEqual("NONDOMINATED_TRADEOFF_REQUIRES_EXPLICIT_POLICY_PREFERENCE", out.relation)
        self.assertIsNone(out.retained_policy_id)
        self.assertTrue(out.higher_hit_ratio_not_used_as_authority)
        self.assertFalse(out.k27_or_geometry_privileged)
        self.assertIn("physical_total_expert_bytes", out.better_metrics)
        self.assertIn("energy_joules", out.worse_metrics)

    def test_higher_hit_ratio_cannot_save_pareto_regression(self):
        baseline = self.obs("LFU", hit=0.20)
        candidate = self.obs(
            "TEMPORAL_PREDICTIVE_CACHE", policy_class="PREDICTIVE_CACHE", hit=0.95,
            energy=12.0, memory=1400, warmup=3.0, restart=4.0,
            revalidation=0.7, control=0.2,
        )
        out = compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate)
        self.assertEqual("CANDIDATE_PARETO_REGRESSES_BASELINE", out.relation)
        self.assertEqual("LFU", out.retained_policy_id)
        self.assertTrue(out.higher_hit_ratio_not_used_as_authority)

    def test_source_or_workload_substitution_fails(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND", preflight=self.preflight(source="other-source"))
        self.assert_code("SAME_SCOPE_SOURCE_WORKLOAD_REQUIRED",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_measurement_campaign_substitution_fails(self):
        baseline = self.obs("BASE", campaign="campaign-A")
        candidate = self.obs("CAND", campaign="campaign-B")
        self.assert_code("SAME_MEASUREMENT_CAMPAIGN_REQUIRED",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_unattested_lifecycle_metrics_fail(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND", lifecycle_attested=False)
        self.assert_code("CANDIDATE_LIFECYCLE_METRICS_ATTESTATION_REQUIRED",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_prefetch_bytes_cannot_receive_cache_policy_credit(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND", preflight=self.preflight(
            demand=600, aura_avoided=300, prefetch_useful=100))
        self.assert_code("CANDIDATE_PREFETCH_CROSS_CREDIT_FORBIDDEN",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_latency_overlap_cannot_receive_cache_policy_credit(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND", preflight=self.preflight(overlap=0.2))
        self.assert_code("CANDIDATE_OVERLAP_CROSS_CREDIT_FORBIDDEN",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_stale_measurement_fails_closed(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND", measurement_current=False)
        self.assert_code("CANDIDATE_MEASUREMENT_CURRENT_REQUIRED",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_truthy_integer_cannot_impersonate_currentness_boolean(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND", measurement_current=1)
        self.assert_code("CANDIDATE_MEASUREMENT_CURRENT_INVALID",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_truthy_integer_cannot_impersonate_lifecycle_attestation(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND", lifecycle_attested=1)
        self.assert_code("CANDIDATE_LIFECYCLE_METRICS_ATTESTED_INVALID",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_unattested_w4_receipt_fails(self):
        baseline = self.obs("BASE")
        unattested = replace(self.preflight(), physical_io_attested=False, physical_io_attestation_ref=None)
        candidate = self.obs("CAND", preflight=unattested)
        self.assert_code("CANDIDATE_PHYSICAL_IO_ATTESTATION_REQUIRED",
            lambda: compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate))

    def test_equal_candidate_retains_baseline_without_false_improvement(self):
        baseline = self.obs("BASE")
        candidate = self.obs("CAND")
        out = compare_cache_policy_to_baseline(baseline=baseline, candidate=candidate)
        self.assertEqual("CANDIDATE_EQUAL_TO_BASELINE", out.relation)
        self.assertEqual("BASE", out.retained_policy_id)
        self.assertEqual((), out.better_metrics)
        self.assertEqual((), out.worse_metrics)


if __name__ == "__main__":
    unittest.main()

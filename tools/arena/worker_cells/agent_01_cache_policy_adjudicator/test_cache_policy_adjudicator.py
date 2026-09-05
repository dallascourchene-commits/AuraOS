from __future__ import annotations

from dataclasses import replace
import math
import unittest

from cache_policy_adjudicator import AccessEvent, Adjudication, BenchmarkEnvelope, BenchmarkReceipt, TraceBundle, adjudicate, evaluate_policy, generate_trace, hyperscale_campaign


def env(**overrides):
    values = dict(device="synthetic-device", runtime="arena-cache-policy-v1", source_head="7a2c7a16f845752ffb7c16c68636d8d542ecd72e", quantization="synthetic-q4", cache_state="cold", layers=4, experts_per_layer=8, cache_capacity_experts=4, expert_size_bytes=1024, source_bandwidth_bytes_s=1024.0, joules_per_gb=1.0)
    values.update(overrides)
    return BenchmarkEnvelope(**values)


class T(unittest.TestCase):
    def test_01_envelope_root_deterministic(self): self.assertEqual(env().root, env().root)

    def test_02_nonfinite_bandwidth_rejected(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError): env(source_bandwidth_bytes_s=bad).validate()

    def test_03_nonfinite_energy_rejected(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError): env(joules_per_gb=bad).validate()

    def test_04_trace_order_fail_closed(self):
        with self.assertRaises(ValueError): TraceBundle.build((AccessEvent(0, 1, (1,)), AccessEvent(0, 0, (1,))), env())

    def test_05_duplicate_route_expert_rejected(self):
        with self.assertRaises(ValueError): TraceBundle.build((AccessEvent(0, 0, (1, 1)),), env())

    def test_06_trace_envelope_mismatch_rejected(self):
        e = env(); trace = TraceBundle.build((AccessEvent(0, 0, (1,)),), e)
        with self.assertRaises(ValueError): evaluate_policy(trace, replace(e, cache_capacity_experts=3), "LRU")

    def test_07_lru_basic_hits(self):
        e = env(cache_capacity_experts=2)
        trace = TraceBundle.build((AccessEvent(0, 0, (1,)), AccessEvent(0, 1, (1,)), AccessEvent(1, 0, (1,))), e)
        self.assertGreaterEqual(evaluate_policy(trace, e, "LRU").hits, 1)

    def test_08_route_root_policy_invariant(self):
        e = env(cache_capacity_experts=3)
        trace = TraceBundle.build(generate_trace(regime="uniform", seed=3, tokens=4, layers=4, experts_per_layer=8, topk=2), e)
        self.assertEqual(len({evaluate_policy(trace, e, p).route_root for p in ("LRU", "LAYER_CYCLE", "BELADY_ORACLE")}), 1)

    def test_09_oracle_is_ceiling(self):
        e = env(cache_capacity_experts=3)
        trace = TraceBundle.build(generate_trace(regime="uniform", seed=4, tokens=5, layers=4, experts_per_layer=8, topk=2), e)
        lru = evaluate_policy(trace, e, "LRU"); layer = evaluate_policy(trace, e, "LAYER_CYCLE"); oracle = evaluate_policy(trace, e, "BELADY_ORACLE")
        self.assertLessEqual(oracle.misses, min(lru.misses, layer.misses))

    def test_10_transfer_accounting_exact(self):
        e = env(expert_size_bytes=2048, source_bandwidth_bytes_s=1024.0, joules_per_gb=2.0)
        result = evaluate_policy(TraceBundle.build((AccessEvent(0, 0, (1,)),), e), e, "LRU")
        self.assertEqual(result.bytes_loaded, 2048); self.assertEqual(result.transfer_seconds, 2.0); self.assertAlmostEqual(result.energy_j, 2048 / 1e9 * 2.0)

    def test_11_adjudication_nonpromoting(self):
        e = env(); result = adjudicate(TraceBundle.build(generate_trace(regime="uniform", seed=1, tokens=3, layers=4, experts_per_layer=8, topk=2), e), e)
        self.assertFalse(result.effect_authority); self.assertFalse(result.gate10)

    def test_12_receipt_verifies_source_truth(self):
        e = env(); trace = TraceBundle.build(generate_trace(regime="uniform", seed=1, tokens=3, layers=4, experts_per_layer=8, topk=2), e); result = adjudicate(trace, e); receipt = BenchmarkReceipt.build(trace, e, result)
        self.assertTrue(receipt.verify(trace, e, result))

    def test_13_receipt_rejects_source_head_drift(self):
        e = env(); trace = TraceBundle.build(generate_trace(regime="uniform", seed=1, tokens=3, layers=4, experts_per_layer=8, topk=2), e); result = adjudicate(trace, e); receipt = BenchmarkReceipt.build(trace, e, result)
        drift = replace(e, source_head="different-head"); drift_trace = TraceBundle.build(trace.events, drift); self.assertFalse(receipt.verify(drift_trace, drift, adjudicate(drift_trace, drift)))

    def test_14_receipt_rejects_runtime_drift(self):
        e = env(); trace = TraceBundle.build(generate_trace(regime="uniform", seed=1, tokens=3, layers=4, experts_per_layer=8, topk=2), e); result = adjudicate(trace, e); receipt = BenchmarkReceipt.build(trace, e, result)
        drift = replace(e, runtime="other-runtime"); drift_trace = TraceBundle.build(trace.events, drift); self.assertFalse(receipt.verify(drift_trace, drift, adjudicate(drift_trace, drift)))

    def test_15_receipt_rejects_trace_drift(self):
        e = env(); trace = TraceBundle.build(generate_trace(regime="uniform", seed=1, tokens=3, layers=4, experts_per_layer=8, topk=2), e); result = adjudicate(trace, e); receipt = BenchmarkReceipt.build(trace, e, result)
        altered = TraceBundle.build(generate_trace(regime="uniform", seed=2, tokens=3, layers=4, experts_per_layer=8, topk=2), e); self.assertFalse(receipt.verify(altered, e, adjudicate(altered, e)))

    def test_16_receipt_rejects_result_tamper(self):
        e = env(); trace = TraceBundle.build(generate_trace(regime="uniform", seed=1, tokens=3, layers=4, experts_per_layer=8, topk=2), e); result = adjudicate(trace, e); receipt = BenchmarkReceipt.build(trace, e, result)
        tampered = Adjudication(result.state, "LRU", result.lru, result.layer_cycle, result.oracle, result.transfer_time_reduction_vs_lru, result.oracle_regret_ratio)
        self.assertFalse(receipt.verify(trace, e, tampered))

    def test_17_temporal_hot_is_adjudicated_not_assumed(self):
        e = env(cache_capacity_experts=8); trace = TraceBundle.build(generate_trace(regime="temporal_hot", seed=7, tokens=12, layers=4, experts_per_layer=8, topk=2), e)
        self.assertIn(adjudicate(trace, e, minimum_reduction=0.01, maximum_oracle_regret_ratio=2.0).state, {"CANDIDATE_LRU", "NO_MATERIAL_POLICY_ADVANTAGE", "CANDIDATE_LAYER_CYCLE", "HOLD_ORACLE_GAP"})

    def test_18_layer_cyclic_is_measured_not_assumed(self):
        e = env(cache_capacity_experts=5); trace = TraceBundle.build(generate_trace(regime="layer_cyclic", seed=8, tokens=12, layers=4, experts_per_layer=8, topk=2), e); result = adjudicate(trace, e, minimum_reduction=0.0, maximum_oracle_regret_ratio=10.0)
        self.assertGreaterEqual(result.layer_cycle.hit_rate, 0.0); self.assertGreaterEqual(result.lru.hit_rate, 0.0)

    def test_19_unknown_policy_rejected(self):
        e = env(); trace = TraceBundle.build((AccessEvent(0, 0, (1,)),), e)
        with self.assertRaises(ValueError): evaluate_policy(trace, e, "NOPE")

    def test_20_hyperscale_1000_clean(self):
        result = hyperscale_campaign(1000)
        self.assertEqual(result["receipt_failures"], 0); self.assertEqual(result["oracle_violations"], 0); self.assertEqual(result["authority_violations"], 0); self.assertEqual(result["cases"], 1000)


if __name__ == "__main__": unittest.main()

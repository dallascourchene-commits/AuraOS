from __future__ import annotations

import json

from cache_policy_adjudicator import BenchmarkEnvelope, BenchmarkReceipt, TraceBundle, adjudicate, generate_trace, hyperscale_campaign


def run() -> dict[str, object]:
    envelope = BenchmarkEnvelope(
        device="synthetic-device",
        runtime="arena-cache-policy-v1",
        source_head="7a2c7a16f845752ffb7c16c68636d8d542ecd72e",
        quantization="synthetic-q4",
        cache_state="cold",
        layers=16,
        experts_per_layer=32,
        cache_capacity_experts=24,
        expert_size_bytes=8 * 1024 * 1024,
        source_bandwidth_bytes_s=1.2e9,
        joules_per_gb=2.4,
    )
    per_regime: dict[str, object] = {}
    for index, regime in enumerate(("layer_cyclic", "temporal_hot", "uniform")):
        trace = TraceBundle.build(
            generate_trace(regime=regime, seed=620000 + index, tokens=64, layers=envelope.layers, experts_per_layer=envelope.experts_per_layer, topk=4),
            envelope,
        )
        result = adjudicate(trace, envelope, minimum_reduction=0.02, maximum_oracle_regret_ratio=1.25)
        receipt = BenchmarkReceipt.build(trace, envelope, result)
        assert receipt.verify(trace, envelope, result)
        per_regime[regime] = {
            "state": result.state,
            "winner": result.winner,
            "lru_misses": result.lru.misses,
            "layer_cycle_misses": result.layer_cycle.misses,
            "oracle_misses": result.oracle.misses,
            "reduction_vs_lru": result.transfer_time_reduction_vs_lru,
            "oracle_regret_ratio": result.oracle_regret_ratio,
            "receipt_digest": receipt.receipt_digest,
        }
    return {
        "objective": "matched-envelope cache policy adjudication",
        "claim_ceiling": "D0 synthetic only; no physical GLM throughput/energy; no Gate10",
        "envelope_root": envelope.root,
        "regimes": per_regime,
        "hs1000": hyperscale_campaign(1000),
    }


if __name__ == "__main__": print(json.dumps(run(), indent=2, sort_keys=True))

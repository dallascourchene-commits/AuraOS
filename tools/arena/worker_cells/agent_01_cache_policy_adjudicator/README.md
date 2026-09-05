# AGENT_01 — CACHE_POLICY_ADJUDICATOR

Exclusive worker-cell scope: `tools/arena/worker_cells/agent_01_cache_policy_adjudicator/*`.

## Objective

Adjudicate MoE expert-cache policy under one exact benchmark envelope instead of assuming that LRU, hot-expert caching, or a structure-aware policy is universally best. The controller compares LRU, an online layer-order-aware `LAYER_CYCLE` heuristic, and a Belady offline ceiling. Every policy must preserve the exact native router route. Receipts bind the actual trace root, hardware/runtime/source envelope, adjudication result, and source head. D0 only; `effect_authority=false`; `Gate10=false`.

## Exact two foreign rebase parents

1. `ARENA-CONTRIBUTION__O10-F27-SOURCE-TRUTH-NONFINITE-CLOSURE__30LOCAL-2XHOSTEDPASS__GPT56SOL__20260905` — consequential benchmark reuse requires source-truth binding; canonical identity rejects NaN/Inf.
2. `ARENA-CONTRIBUTION__ASTRA-MAPPED-AURA-BENCHMARK-V2__O2__45PASS-CURRENT-F27-355PREFETCH__GPT56SOL__20260905` — current Frontier-27 benchmark validity and explicit separation of synthetic software evidence from physical GLM truth.

## External research pressure

- SpecMD (arXiv:2602.03921) reports that MoE expert access can violate ordinary temporal-locality assumptions and motivates benchmarking cache policies across hardware/workload regimes. It reports Least-Stale reducing collision misses by up to 85x over LRU in its evaluated settings.
- SpecPrefetch (arXiv:2607.24787) separates asynchronous transfer prediction from native router execution and reports up to 20% decode-throughput improvement on one evaluated mobile device.
- `Who Should Own the Expert Cache?` (arXiv:2608.12103) reports a different regime where untuned kernel LRU is competitive and synchronous/router prefetch offers little benefit, reinforcing that policy selection must be envelope-specific.
- LocalLLaMA reports during Aug-Sep 2026 describe both large gains and regressions from hot-expert caching/offload across different Qwen/MoE setups; these are advisory practitioner evidence only.

`LAYER_CYCLE` is an Aura test heuristic inspired by structure-aware/anti-LRU pressure. It is not represented as the exact Least-Stale algorithm from SpecMD.

## Verification

Local deterministic proof is performed in three freshly recreated stdlib-only Python virtual environments. The focused suite has 20 tests; the benchmark includes three workload regimes plus a 1,000-case HyperScale campaign. Acceptance requires zero receipt failures, zero oracle-ceiling violations, zero authority/Gate10 promotions, identical native route roots across policies, and exact trace/envelope/source binding.

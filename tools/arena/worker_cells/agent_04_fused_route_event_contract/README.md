# AGENT_04 — Fused Route Event Contract

Exclusive scope: `tools/arena/worker_cells/agent_04_fused_route_event_contract/*`

This worker preserves each token×layer native-router top-K decision as a single fused event across serialization/replay. A flat expert-only sequence is intentionally non-admissible because it loses event membership, token/layer identity, and group cardinality.

## Keeper laws

- `NativeRouterDecision = one token × one layer × complete top-K expert group`.
- `Flattening` is permitted only when every expert access carries `event_sequence`, `member_index`, `group_size`, `token`, and `layer` so exact fused events can be reconstructed.
- `ReplayCredit => ReconstructedEventRoot == OriginalEventRoot`.
- `LossyExpertOnlyStream => HOLD` regardless of apparent length or cache score.
- `TraceReplayValidity != CachePolicyQuality != PhysicalSpeedup != MergeAuthority != Gate10`.
- Ω8 hard-invalid axes dominate; trailing context cannot repair them.

## Research pressure

arXiv:2608.07911 reports that inconsistent per-access replay can inflate recency-based cache policies and even reverse policy rankings. SpecPrefetch (arXiv:2607.24787) separately reinforces that speculative transfer prediction must not alter native routing semantics. This contract addresses the measurement side: before policy adjudication, the replay representation must prove it preserves the exact native-router event structure.

## Verification

```bash
python -m py_compile fused_route_event_contract.py test_fused_route_event_contract.py benchmark_fused_route_event_contract.py
python -m unittest -v test_fused_route_event_contract.py
python benchmark_fused_route_event_contract.py
```

The benchmark round-trips 8,192 fused events / 16,384 expert accesses, attacks the representation with 1,000 deterministic mutations, and runs 100,000 sampled 13D states. It is software/control-plane proof only, not a physical GLM performance claim.

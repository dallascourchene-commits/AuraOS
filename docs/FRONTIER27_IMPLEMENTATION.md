# Frontier-27 implementation campaign

This branch implements the 27 highest-leverage mechanism families selected by the SOL-AURA1000 1000→27 contraction. It is a D0, stdlib-only reference runtime and benchmark harness. No physical GLM/Qwen throughput, provider execution, owner-host effect, or Gate10 is claimed.

## Implemented mechanisms

1. HardFalseSecurityGate — hard-false runtime security admission.
2. HybridIndexBridge — approximate HDC candidate retrieval bridged to full identity/K27 locality.
3. ExportReceipt — output/dependency/generation-bound export receipts.
4. TypedGraphEdges — relation/provenance/generation-aware graph edges.
5. NativeRouterAuthority — transfer prediction cannot change native execution route.
6. RouterPreservingPrefetch — predictions only schedule allowed transfers.
7. PageCacheStateGate — cold/warm/unknown cache state is explicit.
8. VersionRangeGate — unknown/incompatible generations fail closed.
9. SnapshotRing — bounded deterministic state checkpoints.
10. HotColdCache — hot LRU overlay preserving canonical cold records.
11. StorageTierPlacement — fastest feasible tier under capacity/energy constraints.
12. StateHandleLease — owner/generation/expiry/closed-state typed resource handles.
13. WindowAwareBudget — speculative bytes bounded by measured overlap window.
14. PrefetchWasteGuard — byte-savings gate instead of hit-count optimism.
15. TierEnergyAdmission — typed energy budget per storage transfer.
16. UsefulByteAccounting — useful/wasted/missed bytes separated.
17. ExpertResidencyLRU — deterministic bounded expert residency/eviction.
18. PLEExpertSeparation — separate PLE/n-gram and MoE expert residency classes.
19. P0IdentityGate — exact model/runtime/source/host/generation before effect.
20. MatchedEnvelopeGate — performance claims require comparable device/cache/thermal/clock envelopes.
21. CompositionMembrane — declared interfaces compose without authority union.
22. CollisionBucket — coordinate collisions preserve full identities.
23. HardGatePin — non-compensatory security gates ignore soft score.
24. CapabilityManifest — explicit host powers, default deny.
25. RetrievalReceipt — query/candidate/generation receipt.
26. CurrentnessInvalidator — dependency-indexed selective wake/reproof.
27. HDCSemanticKey — deterministic semantic key for candidate retrieval only.

## Benchmark scope

`benchmarks/benchmark_frontier27.py` compares a simple pre-frontier reference path against the Frontier-27 composition on deterministic synthetic workloads. It measures transfer bytes, modeled transfer latency and energy, cache-hit rate, retrieval candidate examinations and wall time, selective reproof fanout, bounded snapshot retention, and blocked unproven/security cases.

The offload before/after benchmark uses the same SSD source bandwidth and joules/GB on both sides. These are software-level/synthetic efficiency measurements; they do not substitute for owner-host GLM-5.3 profiling or real device throughput/energy measurements.

# Frontier-27 implementation campaign

This branch implements the 27 highest-leverage mechanism families selected by the SOL-AURA1000 1000→27 contraction. It is a D0, stdlib-only reference runtime and benchmark harness. No physical GLM/Qwen throughput, provider execution, owner-host effect, or Gate10 is claimed.

## Implemented mechanisms

1. HardFalseSecurityGate — hard-false runtime security admission.
2. HybridIndexBridge — approximate HDC candidate routing plus an exact lexical backstop so retrieval efficiency cannot drop benchmark-declared relevant records.
3. ExportReceipt — output/dependency/generation-bound export receipts with receipt-digest verification before reuse.
4. TypedGraphEdges — relation/provenance/generation-aware graph edges.
5. NativeRouterAuthority — transfer prediction cannot change native execution route.
6. RouterPreservingPrefetch — predictions only schedule allowed transfers.
7. PageCacheStateGate — cold/warm/unknown cache state is explicit.
8. VersionRangeGate — full-string semantic-version parsing; malformed, unknown and incompatible generations fail closed.
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
23. HardGatePin — exact required non-compensatory security gates; missing, unknown or non-boolean gates fail closed and soft score cannot compensate.
24. CapabilityManifest — explicit host powers, default deny.
25. RetrievalReceipt — query/candidate/generation receipt with self/context verification.
26. CurrentnessInvalidator — dependency-indexed selective wake/reproof, replacement rebinding, and explicit exact-dependency reproof completion.
27. HDCSemanticKey — deterministic semantic key for candidate routing only.

## Benchmark scope

`benchmarks/benchmark_frontier27.py` compares a simple pre-frontier reference path against the Frontier-27 composition on deterministic synthetic workloads. It measures transfer bytes, modeled transfer latency and energy, cache-hit rate, retrieval candidate examinations and wall time, selective reproof fanout, bounded snapshot retention, and blocked unproven/security cases.

The offload before/after benchmark uses the same SSD source bandwidth and joules/GB on both sides. The after path now uses a conservative **serialized-all-transfers** model: every actual prefetch transfer contributes bytes, energy and transfer time. No overlap credit is claimed; physical overlap must be established separately by owner-host profiling.

Retrieval candidate reduction receives efficiency credit only when the full-scan oracle's benchmark-declared relevant set is preserved. The threshold checker therefore requires **recall = 1.0 and zero false negatives** in addition to the candidate-reduction floor.

These are software-level/synthetic efficiency measurements; they do not substitute for owner-host GLM-5.3 profiling or real device throughput/energy measurements.

## Hosted proof identity

The proof workflow pins `actions/checkout`, `actions/setup-python`, and `actions/upload-artifact` to immutable commit SHAs. On pull requests it checks out the exact `pull_request.head.sha` (and `github.sha` on push) and verifies `git rev-parse HEAD` equals that expected identity before compilation, tests or benchmarks run. A hosted PASS is therefore bound to the explicit semantic checkout used by the proof job rather than being inferred from an implicit pull-request merge ref.

Hosted execution still does not grant merge, deployment, model execution, physical-performance truth, effect authority or Gate10.

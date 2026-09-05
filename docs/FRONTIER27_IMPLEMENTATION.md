# Frontier-27 implementation campaign

This branch implements the 27 highest-leverage mechanism families selected by the SOL-AURA1000 1000→27 contraction. It is a D0, stdlib-only reference runtime and benchmark harness. No physical GLM/Qwen throughput, provider execution, owner-host effect, or Gate10 is claimed.

## Implemented mechanisms

1. HardFalseSecurityGate — hard-false runtime security admission.
2. HybridIndexBridge — approximate HDC candidate routing plus an exact lexical backstop so retrieval efficiency cannot drop benchmark-declared relevant records.
3. ExportReceipt — output/dependency/generation-bound export receipts with receipt-digest verification and mandatory candidate-payload rehash before reuse; reuse without source payload fails closed.
4. TypedGraphEdges — relation/provenance/generation-aware graph edges.
5. NativeRouterAuthority — transfer prediction cannot change native execution route.
6. RouterPreservingPrefetch — predictions only schedule allowed transfers.
7. PageCacheStateGate — cold/warm/unknown cache state is explicit.
8. VersionRangeGate — full-string semantic-version parsing; malformed, unknown and incompatible generations fail closed.
9. SnapshotRing — bounded restorable JSON-canonical state checkpoints with digest verification on restore.
10. HotColdCache — hot LRU overlay preserving canonical cold records.
11. StorageTierPlacement — fastest feasible tier under capacity/energy constraints.
12. StateHandleLease — owner/generation/expiry/closed-state typed resource handles.
13. WindowAwareBudget — speculative bytes bounded by measured overlap window.
14. PrefetchWasteGuard — byte-savings gate instead of hit-count optimism.
15. TierEnergyAdmission — typed energy budget per storage transfer; aggregate speculative prefetch must satisfy the configured energy budget before execution.
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

Identity-bearing canonicalization uses strict JSON and rejects non-finite numeric values (`NaN`, positive infinity, negative infinity) rather than hashing non-portable representations.

## Benchmark scope

`benchmarks/benchmark_frontier27.py` compares a simple pre-frontier reference path against the Frontier-27 composition on deterministic synthetic workloads. It measures transfer bytes, modeled transfer latency and energy, cache-hit rate, actual prefetch transfer count, retrieval candidate examinations and wall time, selective reproof fanout, bounded snapshot retention, and security admission outcomes against an independent raw-input validity oracle.

The offload before/after benchmark uses the same SSD source bandwidth and joules/GB on both sides. The after path uses a conservative **serialized-all-transfers** model: every actual prefetch transfer contributes bytes, energy and transfer time. No overlap credit is claimed; physical overlap must be established separately by owner-host profiling.

The synthetic overlap window is 10 ms so at least one 8 MiB expert can be admitted at 1.2 GB/s. The threshold checker requires `prefetch_transfers > 0`; therefore the hosted proof cannot claim a prefetch-path result while exercising only LRU residency. The configured speculative energy budget is independently enforced before a prefetch plan is admitted.

Retrieval candidate reduction receives efficiency credit only when the full-scan oracle's benchmark-declared relevant set is preserved. The threshold checker therefore requires **recall = 1.0 and zero false negatives** in addition to the candidate-reduction floor.

The security campaign defines expected validity directly from the generated source-audit, runtime-hard-false, remote-code-widening and identity inputs, then compares the gates against that independent oracle. The threshold checker requires zero invalid false-admits and zero valid rejections; gate outputs cannot redefine which cases count as invalid.

These are software-level/synthetic efficiency measurements; they do not substitute for owner-host GLM-5.3 profiling or real device throughput/energy measurements.

## Canonical proof receipt

The benchmark emits `AURA-FRONTIER27-PROOF-RECEIPT-v1`. The receipt separates three identities that must not be conflated:

- `source_head` — the exact Git source generation observed by the proof runner.
- `input_root` — a strict-JSON digest of the declared benchmark schema, seed, workload sizes, retrieval parameters, offload envelope, currentness fixture, snapshot fixture, and security-case count.
- `result_root` — a strict-JSON digest of deterministic benchmark consequences only. Environment-sensitive retrieval wall-clock observations are retained in the JSON report but excluded from this root.

`receipt_digest` binds the receipt schema, exact source head, input root, and deterministic result root. Receipt verification also requires the canonical `AURA-FRONTIER27-BENCH-v2` schema and the exact ordered 27-entry Frontier manifest; a self-consistent digest over substituted benchmark identity is rejected. The threshold checker independently recomputes all three roots and resolves the expected source identity against the checked-out Git HEAD. When Git metadata is available, an explicit `FRONTIER27_SOURCE_HEAD` or `FRONTIER27_EXPECTED_SOURCE_HEAD` must equal `git rev-parse HEAD`; a syntactically valid but different SHA fails closed. Git-backed receipt generation also rejects staged or unstaged tracked-file modifications, because a commit SHA alone does not identify dirty executed source. Explicit source identities remain supported for exported/non-Git environments where Git metadata is genuinely unavailable. Numeric threshold and count fields reject JSON booleans rather than accepting Python's `bool`-as-`int` coercion. Missing receipts, source drift, dirty tracked source, benchmark-identity substitution, malformed numeric types, input drift, deterministic-result tampering, receipt tampering, or authority widening fail closed. Wall-clock variation alone does not invalidate a deterministic proof receipt.

The receipt is explicitly `D0_NONPROMOTING`: exact source identity and reproducibility evidence do not grant merge, deployment, model-provider, physical-performance, or Gate10 authority.

## Hosted proof identity

The proof workflow pins `actions/checkout`, `actions/setup-python`, and `actions/upload-artifact` to immutable commit SHAs. On pull requests it checks out the exact `pull_request.head.sha` (and `github.sha` on push) and verifies `git rev-parse HEAD` equals that expected identity before compilation, tests or benchmarks run. A hosted PASS is therefore bound to the explicit semantic checkout used by the proof job rather than being inferred from an implicit pull-request merge ref.

Hosted execution still does not grant merge, deployment, model execution, physical-performance truth, effect authority or Gate10.

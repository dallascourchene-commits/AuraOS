# K27 ThinkPad SIMD Benchmark Evidence V1

Status: DRAFT / D0 / HS1 / NONPROMOTING.

## Exactly two non-self earned artifacts

1. PR #608 exact semantic artifact `bb7d8849112c1c992c64b3078f3df0d84b8ff60b`, dedicated `K27 ThinkPad Portable SIMD Dispatch` run `33365196299` SUCCESS. It owns portable scalar/AVX2/AVX512 1024-bit Hamming execution with CPU + OS extended-state admission and keeps performance, placement, cache and thermal claims false.
2. PR #654 exact proof generation `26e377fe543b8c1906832b8c1e968dfe63480005`, dedicated `Aura HyperScale Work Admission` run `33375530171` SUCCESS. It owns separate EXPLORATION/VERIFICATION value channels and exact bounded minimum-evidence-cover admission.

No fake Git two-parent convergence is claimed. The child is based on current `main`; the workflow revalidates both exact evidence parents and materializes their exact source blobs.

## Residual

`PortableSIMDDispatch + HyperScaleVerificationAdmission != PerformanceEvidenceUntil MatchedWorkload + BackendIdentity + HostIdentity + RepeatedTiming AreBound`.

This is a verification/Evidence Generation Key (EGK) objective, not a new semantic-performance claim. The benchmark does not receive semantic-sibling credit merely because it produces new timing numbers.

## Minimum evidence cone

The PR654 owner is reused directly. For the current hosted-compute question the unresolved leaves are:

- exact PR608 backend identity;
- matched 1024-bit workload identity;
- hosted-runner host identity;
- repeated hosted-runner compute timing.

The exact minimum cover is one observation: `matched-hosted-simd-compute-benchmark`. A broader storage+compute sweep and broad host profiler are deliberately more expensive alternatives and are not selected.

`MinimumEvidenceConeBeforeHyperScaleFanout`.
`VerificationAdmission != VerificationResult`.
`FreshEGK != FreshSemanticSibling`.

## Material benchmark

`tools/k27/thinkpad_simd_benchmark_evidence.cpp` does not own or copy a Hamming algorithm. CI materializes the exact PR608 source blob `96e523682b7d6a0b3e2c3d850bc4d8bafa58b97c` and injects it into the benchmark translation unit.

The workload is deterministic:

- 1024 bits / 16 unsigned 64-bit words per vector;
- one fixed query;
- 4,096 deterministic centroids;
- centroid payload = 524,288 bytes;
- fixed SplitMix64 seed and named workload identity;
- four warmup rounds;
- eleven measured samples;
- 64 full corpus repetitions per sample;
- scalar and selected-backend order alternates by sample;
- every measured sample must preserve an identical semantic checksum.

The runner records the CPU model, uname tuple, runtime-selected PR608 backend, median scalar time, median selected-backend time and a descriptive scalar/selected median ratio.

There is deliberately **no speed threshold**. A slower SIMD result is valid evidence. A faster hosted-runner result is also only hosted-runner evidence.

## Separation from existing owners

PR #598 owns matched ASTGE Read+Seek versus immutable-mmap storage timing. This objective does not benchmark storage, mmap, page faults, NVMe, graph hydration, or snapshot access.

PR #635 owns the architecture-neutral HDV1024 consequence corpus. This objective does not create a competing cross-ISA corpus or representation contract.

PR #631/#638 own RISC-V consequence replay lanes. This objective does not compare x86 and RISC-V performance.

## External Different-J pressure

Current CPU benchmarking methodology emphasizes portable, controlled workloads and multiple microarchitectural profiles rather than one universal speed number. Current CPU inference reports likewise show that SIMD benefit can change with workload phase, cache fit, memory pressure, thread placement and instruction path. Those sources motivate matched repeated measurement; they grant no Aura or ThinkPad performance authority.

Direct task-specific Scholar-native discovery did not yield a stable stronger record in this pass: `SCHOLAR_DIRECT_GAP`.

## 8 crystalline / Triadic / Creation / HyperScale

- W0: exact-green PR608 semantic execution + exact-green PR654 work-admission owner.
- W1: exact owner source -> deterministic matched workload -> alternating repeated timings -> receipt.
- W2: backend/source-generation, workload, host, warmup/cache, order, timing/superiority and effect cross-casts.
- W3: hosted contradiction reopens only compile, owner-materialization, admission, workload or timing harness as indicated by the failing step.
- W4: SIMD semantics, hosted timing, owner-ThinkPad timing, scheduler placement, cache residency, thermal/power, storage I/O and authority remain independent leaves.
- W5: portable SIMD execution × minimum-cone HyperScale admission -> bounded compute benchmark evidence.
- W6/W7/W8: evaluated and unearned. HS1.

Triadic: SIMD execution thesis + sparse verification admission thesis -> challenge `correct SIMD == faster ThinkPad` -> matched nonpromoting hosted-compute evidence synthesis.

Creation: rebind exact parents -> collision scan -> compute minimum evidence cone -> materialize exact owner source -> deterministic workload -> warmup/repeated alternating timing -> semantic checksum reproof -> preserve claim ceiling -> persist receipt -> owner-host reopen only if materially useful.

## Claim ceiling

This child does not prove:

- a physical owner ThinkPad was benchmarked;
- AVX2 or AVX-512 is faster on that ThinkPad;
- AVX-512 is available on that ThinkPad;
- P-core-only placement or affinity;
- cache residency or controlled cache state;
- thermal or power reduction;
- physical NVMe/device effects;
- generalized K27 performance superiority;
- semantic K27 authority;
- native/private transformer KV access;
- Gate-10, merge, deployment, provider, public, financial or human effect authority.

A later owner-host benchmark may reuse this harness only after exact source/workload/currentness binding. Hosted timing never substitutes for owner-host identity.

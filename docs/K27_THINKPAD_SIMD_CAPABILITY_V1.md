# K27 ThinkPad SIMD Capability V1

This surface adapts the useful SIMD portion of the supplied ThinkPad K27 proposal without accepting its CPU, cache, thermal, or latency assumptions as facts.

## Objective

`ComputeProfileIntent + TypedEvidenceAxes != SIMDExecutionEligibleUntil CPUFeatureEvidence + OSExtendedState + CompiledVariant + CacheObservation Are Bound`.

The tool is an observation and safe-dispatch membrane. It is not another Aura host-discovery owner and does not replace `HostDiscoveryV1`.

## Dispatch law

AVX2 execution requires all of:
- x86 CPU;
- CPUID AVX;
- CPUID AVX2;
- CPUID POPCNT because the AVX2 implementation uses scalar POPCNT lanes;
- CPUID OSXSAVE;
- successful XGETBV observation;
- XCR0 XMM and YMM state enabled.

AVX-512 VPOPCNTDQ execution requires all of:
- the AVX prerequisites above except AVX2/POPCNT are not used by that implementation;
- CPUID AVX512F;
- CPUID AVX512_VPOPCNTDQ;
- XCR0 XMM, YMM, opmask, ZMM_hi256, and hi16_ZMM state enabled.

A scalar implementation is always retained as the portability baseline. Optional variants use compiler function targeting; the translation unit is not globally compiled with `-march=native`.

## Cache law

The source proposal's 512 KiB tile is carried only as `proposed_tile_bytes=524288`. Linux sysfs L2 capacity and sharing data are observations. Even if 512 KiB is numerically smaller than observed L2 capacity, the receipt keeps `l2_residency_proven=false`; associativity, competing data, prefetch behavior, sibling sharing, scheduling, and thermal behavior are not inferred from capacity.

## Similarity law

For 1024-bit bipolar vectors encoded as bits, Hamming distance `d` corresponds to bipolar cosine/dot similarity:

`similarity = 1 - 2*d/1024`.

That identity is mathematical representation logic only. It does not make the vectors semantically authoritative K27 coordinates.

## Claim ceiling

The hosted contract does not run on the owner's physical ThinkPad and does not prove:
- 512 KiB L2 residency;
- P-core-only scheduling;
- thermal or power reduction;
- AVX-512 superiority over AVX2;
- any advertised scan latency;
- exact hardware/device identity beyond bounded observations;
- semantic K27 authority;
- model-private/native KV-cache access;
- effect authority.

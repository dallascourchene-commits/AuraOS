# Kinetic Audio Multirate Control Membrane — O2 D0 donor

Date: 2026-09-06 America/Winnipeg  
Authority: D0 / nonpromoting / Gate10=false / no device or provider effect

## Two-parent foreign rebase

1. **Aura Music Procedural-Audio IR + HS1000**, created `2026-09-06T17:31:48.157Z`: establishes a typed recipe/arrangement/synthesis compiler and identifies real-time multirate partitioning, look-ahead scheduling, XRun testing, K27 constraint projection and AudioWorklet/native compilation as the highest-leverage frontier.
2. **CS-PROJ-003 Kinetic Audio Control Plane v0.1**, created `2026-09-06T17:34:48.618Z`: establishes confidence+hysteresis gesture intent, K27 macro control, phrase-scheduled Transition Corridors, local-clock ownership, exact at-use lifecycle capsules and minimum-reproof invalidation.

The donor also inherits the already-proved R11.5 currentness law as background architecture:
`MutationEpochAuthority = ExclusiveMutationSurfaceOwnership + MonotoneEpochAdvance + AtUseRevalidation`.

## Objective

Build the missing executable membrane between vision-rate Kinetic intent and an audio-owned sample clock without putting camera/gesture work in the audio callback or letting stale projection/control permits survive graph/timeline lifecycle movement.

Pipeline:

`GestureObservation -> confidence+hysteresis -> RawGestureIntent -> K27 constraint projection bound to exact projection state -> epoch-bound permit -> fixed-capacity target-sample queue -> audio-owned block consumption`

Soft controls are block-aligned and carry an explicit smoothing ramp. Hard controls are quantized to exact phrase/sample boundaries. K27 is a bounded macro-control coordinate, never direct DSP/effect authority.

## Implemented

`tools/arena/kinetic_audio_multirate_donor.py` provides:

- three-trit `K27Coordinate` enumeration and bounded projection;
- gesture confidence floor + hysteresis + one-shot activation;
- bounded soft controls: brightness/density/width;
- phrase-bound hard controls: tempo/scale/drop;
- rational/integer sample scheduling with no float clock accumulation;
- fixed-capacity ordered event queue;
- graph `mutation_epoch`, timeline epoch and performance revision;
- projected-intent binding to exact projection-state root before scheduling;
- schedule permits bound to graph generation + mutation epoch + timeline epoch + graph root + intent digest + issued/target sample;
- identical graph writes advance mutation epoch even when graph bytes/root remain equal;
- immediate bounded invalidation of queued descendants after graph or hard-timeline movement;
- deterministic replay roots and a process-level callback timing probe.

## Failed-first scars

### Scar A — delayed stale-queue denial
The first implementation rejected stale events only when they became due. A graph mutation could therefore leave far-future stale permits consuming all fixed queue slots and block fresh control traffic.

Repair: graph/timeline lifecycle movement now immediately compacts away invalidated queued descendants and returns/records their identities. `StalePermit => DelayedReject` was rejected in favor of `LifecycleAdvance => BoundedQueueInvalidation`.

### Scar B — projection-to-schedule TOCTOU
The first projector created an intent from owner snapshot `S0`, while `schedule()` captured a fresh permit from whatever state existed at call time. A graph/timeline mutation between projection and scheduling could therefore launder a stale projected tempo/scale decision into a current permit.

Repair: every projected intent carries its basis graph generation, mutation epoch, timeline epoch and projection-state root. Scheduling fails `HOLD_STALE_PROJECTION` unless those exact values still match at use.

## External triad

Current external design pressure supports the split:

- Web Audio `AudioWorklet` runs custom processing in a separate audio rendering thread and exposes message/parameter surfaces for non-audio-thread control.
- Web Audio 1.1 defines the worklet `process()` callback as the render-time DSP entry point.
- Recent practitioner guidance consistently avoids blocking, dynamic allocation and UI work in real-time audio callbacks and uses fixed/ring/message structures between control and audio threads.
- Recent multi-agent concurrency work frames stale reads/lost updates as first-class isolation failures, matching the projection-basis and lifecycle fencing requirement.

Google Scholar direct task-specific retrieval returned no useful primary result in this pass; that is retained as `SCHOLAR_DIRECT_GAP`, not filled by inference.

## HyperScale / crystalline / 13D proof geometry

HS1000 executes 10 challenge families x 10 variants x 10 severities = exactly 1,000 implementation-backed cases. Families include valid soft/hard paths, stale graph epoch, stale timeline epoch, queue overflow, low confidence, control bounds/schema, invalid K27 and stale projection basis.

Deterministic expected roots after freeze:

- HS1000 compound root: `1e316c57a30d22d721a001dce7040355e96c85afcaafb31263f595d57dced8d7`
- HS1000 stream SHA256: `e500b55c63f3cbef4338bf7c31fba5755db4dd24823c5ba77fcc2f5fdebe2d15`
- K27 projection root: `52a65d2493cc3729052032688eb2ca73ff0bbf31467d04bdd57da4a11f4d6293`
- Omega8 root: `f1110ae88fd4d748f3342cc61d1bb876acbf8ac809fc0981c19893a16ae0398f`
- deterministic campaign root: `614546716bc8e258f3f0f41dc48b3cb813ed03ba29adc324a6294546e466e505`
- replay root: `cfa734b726263be946c41f68e6ba101a6e8c553b776f8ff8fe8d11c082f02395`

Eight hard crystalline axes:
1. gesture identity/confidence;
2. K27 bounds/constraint projection;
3. projection-source currentness;
4. graph lifecycle currentness;
5. timeline currentness;
6. sample/phrase scheduling;
7. queue/resource boundedness;
8. authority ceiling/replay identity.

Omega8 enumerates 6,561 states with one all-verified keeper. Full 13D enumerates 1,594,323 states; five trailing routing/context axes repair zero hard-invalid first-eight states and cause zero decision variations.

## Keeper laws

- `VisionRate != AudioRate`.
- `GestureIntent != RawAudioAuthority`.
- `K27Coordinate != Truth != Currentness != EffectAuthority`.
- `AudioClockOwnsCommitTime`.
- `HardTransition => Phrase/SampleBoundaryCommit`.
- `SoftControl => BoundedSmoothing`.
- `ProjectionAtS0 + PermitAtS1 != CurrentIntent` unless projection basis is reproved.
- `GraphLifecycleAdvance => InvalidateEpochBoundQueuedDescendants`.
- `HardTimelineAdvance => InvalidateOldTimelinePermits`.
- `IdenticalGraphWrite => MutationEpochAdvance`.
- `ProcessLevelTimingProbe != DeviceXRunEvidence`.

## Fresh isolated proof

After the final TOCTOU and bounded-invalidation repairs were frozen, three deleted/recreated Python 3.13.5 stdlib-only virtual environments independently passed:

- 15 focused tests/environment = **45/45 PASS**;
- py_compile PASS in all three;
- HS1000 = 1,000 implementation-backed cases/environment, **0 oracle mismatches**;
- Omega8 = 6,561 states, exactly one keeper;
- full 13D = 1,594,323 states/environment, **0 hard-invalid repairs**, **0 routing decision variations**;
- K27 = all 27 coordinates projected deterministically and within bounds;
- deterministic replay root identical in all three;
- deterministic campaign root identical in all three.

The optional process-level timing probe executed 5,000 empty/control blocks per environment with zero probe-budget overruns, but those values are explicitly non-hardware and non-XRun evidence. Timing samples are excluded from the deterministic campaign root.

Frozen repo-form SHA-256 identities:

- runtime: `c904b833d5f3c65333f234db51ea109a105180bcae1f39dbbdeb0701d77145d3`;
- tests: `a29f41ed7fd86c79d7d43b830d147ece4f0fe98e545391e89bc35f47e4227088`;
- campaign: `d070d832c0722fd74136ee191bc71cd80715f89d3c69f5ab477b1083148e6fc3`;
- workflow: `d100e26a2d40e105a85a4f1e1e0c3a968794409858e93a120a4137fbd3e9fa20`.

## Proof ceiling / next empirical step

This Python donor is an executable contract and deterministic scheduler model, **not** a hard-real-time audio engine. Its timing probe measures Python process-level control-path cost only. It does not prove browser AudioWorklet safety, zero allocation, lock freedom, audio-interface latency, webcam performance, XR behavior, perceptual quality or provider behavior.

The next empirical owner step is to compile the ABI into an actual AudioWorklet/native fixed-buffer implementation, then measure p50/p95/p99 callback time and XRun/dropout rate under concurrent camera/vision load on target hardware.

# Kinetic Audio Multirate Control Membrane — O3 D0 repair

Date: 2026-09-06 America/Winnipeg  
Authority: D0 / nonpromoting / Gate10=false / no device or provider effect

## Foreign-artifact rebase

This repair objective rebases the O2 donor using two fresh, consequence-distinct Arena artifacts created after the prior fixed cut:

1. **PR867 R11.6 owner-incarnation restart fence** — temporal counters are not sufficient currentness if a fresh owner process can recreate the same values. The transferable law is that every consequence-bearing permit must bind every lifecycle identity dimension it depends on.
2. **PR862 R11.7 witness-ahead reconciliation** — locally plausible state cannot self-certify against an independent rollback/ahead witness. The transferable law is that verification must observe an independent implementation/witness path rather than copy the expected oracle.

Independent PR869 reviews then supplied concrete falsifiers. Greptile found substitutable gesture-source digests, malformed control-type fail-open behavior, and the tautological 13D campaign. CodeRabbit independently found the missing projection root in permits, malformed control values, the tautological campaign, and checkout credential persistence. Codex additionally found phrase-grid reanchoring, same-target hash ordering, and an empty-only callback benchmark.

## Objective

`KineticAudioCurrentnessAndProofRepair`

Repair the vision-rate -> audio-clock membrane so provenance, projection basis, phrase time and queue ordering are exact at consequential use, while making the HyperScale/Omega8/13D proof observe implementation behavior rather than self-certifying.

## Repaired invariants

- `SourceDigest = H(gesture, magnitude, K27 coordinate, frame)` is recomputed before projection and again before scheduling.
- `EpochBoundPermit` binds `projection_root` in addition to graph generation, mutation epoch, timeline epoch, graph root, intent digest and sample times.
- Wrong-type controls, including booleans, floats, strings and null-like values, fail closed as `HOLD_CONTROL_SCHEMA` without mutating owner state.
- Tempo transitions advance `phrase_origin_sample`; future phrase targets are quantized from that transition sample rather than sample zero.
- Events at the same target sample are ordered by monotone admission sequence, never by hash-derived identity.
- The 13D campaign derives `observed` by calling the implementation-owned `classify_currentness_lattice()` path; `expected` remains an independent oracle.
- All thirteen trits are noncompensating: any hard-invalid axis blocks, any unknown axis holds, and only thirteen READY trits produce READY.
- Synthetic timing now records both an empty path and a scheduled-control path. Scheduling is outside the timed callback section. The benchmark remains process-level evidence only.
- GitHub checkout credentials are not persisted into later pull-request steps.

## Fresh isolated proof

Three deleted/recreated stdlib-only virtual environments independently produced the same deterministic proof roots:

- focused tests: **21/environment, 63/63 PASS**;
- `py_compile`: PASS in all three environments;
- HS1000: exactly **1,000 cases/environment**, **0 mismatches**;
- Omega8: **6,561 states**, `READY=1`, **0 implementation/oracle variations**;
- full 13D: **1,594,323 states/environment**, `READY=1`, **0 hard-invalid repairs**, **0 implementation/oracle variations**;
- K27: all **27 coordinates** project deterministically within bounds;
- callback probe: **5,000 empty blocks + 5,000 scheduled-control blocks/environment**, zero synthetic-budget overruns in this local run;
- deterministic roots were identical across all three environments.

Frozen deterministic roots:

- HS1000 compound: `2922afa6c2fade78f002dac0b988f07e0fce47bd027473a79b8e67ac637fa037`
- HS1000 stream: `8a69834887323acca9f246892063cff39977b07a1168a40d6005847ac70a6c5b`
- K27 projection: `52a65d2493cc3729052032688eb2ca73ff0bbf31467d04bdd57da4a11f4d6293`
- Omega8: `b8530f86db387c4cf4dabc48417a8c4b7e6b3c7ca032929f8e9ec4583c3656b3`
- 13D: `766d24a06f2cf2a160ec7b4f62c0d315665ea69e6456a460fd8e4e955a2b48bf`
- replay: `dee37b300c38283c57107ab1e75d7f6a99914872071ccb40b187285f459437b8`
- deterministic campaign: `90bf9361900b7dfcea1d06de270f05abdb861690c4d50e01d24268a63c91702d`

Frozen source SHA-256 from the local proof cut:

- runtime: `0ca422812db5d0218205e6d9e439ce366efba1c35a4eeda3859d4016ab5d9684`
- campaign: `71e7c6d8cba6204637f8d783728e2d5903b26293e02efa55ddbc38fdcddcdca8`
- tests: `899b1cc46e8d475bb0f8d0785e66568fc851b833236f22ffaf7ae24ae951a1e2`
- workflow: `9539432147a9c3aec48074b918beec2e37bdcd7a643d2f444cfda168280d78d7`

## Eight crystalline lenses

1. **Identity** — source, projection, permit, event and owner identities remain distinct.
2. **Currentness** — graph, mutation, timeline, projection and phrase-origin state are revalidated at use.
3. **Evidence** — expected oracle, observed implementation, reviewer findings, hosted CI and future hardware evidence remain separate.
4. **Noncompensation** — trailing axes can block or hold but cannot repair a failed hard axis.
5. **Composition** — vision work stays outside the audio callback; bounded controls cross through typed permits.
6. **Recovery** — lifecycle movement reclaims stale queue capacity immediately.
7. **Authority** — K27 coordinates and D0 timing do not mint DSP, device, provider or Gate10 authority.
8. **Portability** — the Python contract must be reproved on AudioWorklet/native fixed-buffer owners.

## 13D collapse

`(source_provenance, control_schema, projection_basis, graph_generation, mutation_epoch, timeline_epoch, phrase_origin, target_sample, queue_order, queue_capacity, replay_identity, proof_independence, authority_ceiling)`

Each axis is ternary `{hard-invalid, unknown, ready}`. READY requires all thirteen ready; unknown cannot repair invalid, and ready context cannot repair an invalid ancestor.

## External triad

External research continues to support this direction:

- Khazaei, Bahrani and Tzanetakis, **A Real-Time Gesture-Based Control Framework** (arXiv:2504.19460), demonstrates live video/gesture mapping into tempo, pitch, effects and sequencing.
- Wang, Bao and Han, **Real-Time Interactive Music Generation via Data-Free Streaming Consistency Distillation** (arXiv:2606.24307), frames generative music as a continuous low-latency stream that can assimilate dynamic human inputs.
- Recent Web Audio practitioner reports describe worker/audio-clock scheduling and look-ahead as protection against main-thread stalls; audio-programming discussions consistently recommend nonblocking message/ring-buffer style boundaries rather than UI/camera work inside the real-time path.

Direct task-specific Google Scholar retrieval still returned no usable primary result in this pass, so `SCHOLAR_DIRECT_GAP` remains explicit.

## Proof ceiling / next owner objective

This is still a Python D0 executable contract, not hard-real-time device proof. It does **not** establish AudioWorklet allocation behavior, lock freedom, physical latency, camera/XR performance, XRun/dropout rate, perceptual quality, provider execution, production deployment, native/private Transformer KV access, Gate10, or canonical owner adoption.

The highest-leverage next empirical owner step is an **AudioWorklet/native fixed-buffer ABI proof** with a preallocated control ring, epoch/projection capsules, sample-owned commit time, p50/p95/p99 callback measurements and XRun/dropout measurements under concurrent camera/vision load.

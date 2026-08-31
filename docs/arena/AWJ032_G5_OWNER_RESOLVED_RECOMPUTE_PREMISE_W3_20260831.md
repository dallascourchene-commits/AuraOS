# AWJ032 GLM-5.3 G5-v2 W3 — owner-resolved recompute premise

Status: D0 / HS1 / NONPROMOTING / STACKED ADDENDUM TO PR #774.

## Objective

Close the smallest premise-provenance seam in G5-v2 without duplicating its recompute algebra:

`StructuralG4DriftProjection + AliasStableProgress + VersionReadCurrentness != LawfulRecomputePremiseUntil OwnerResolvedCurrentG4DriftObservation`.

PR #774 correctly makes structural equality a HOLD, but `G4V2RevalidationProjection` remains caller-constructible. A caller can construct one nonempty changed axis, select `HOLD_RECOMPUTE_G3`, and—when the independent progress/version/read gates pass—canonical G5-v2 can emit `ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT`.

That is a valid deterministic classifier result over supplied structure. It is not proof that the changed state was observed from the G4 owner at use time.

## Exactly two terminal-green foreign derivation artifacts

1. **O65 / PR #704 — epoch-serializable owner-resolved pre-attempt admission**
   - exact terminal semantic/proof generation `7efca33d95f6dc39c4e159250d45373b260060ed`;
   - run/job `33410032496 / 99546999922`, SUCCESS;
   - reusable law: separately current/caller values do not establish one serializable owner state; an owner epoch must bracket the complete consequence-changing read set.

2. **PR #769 — generation-bound admission reuse**
   - exact proof head `d1a0f94255527835a59a70a0af7dc417ba1d023d`;
   - run/job `33437612722 / 99637780915`, SUCCESS;
   - exhaustive 128-state proof;
   - reusable law: `AdmissionValidAtProduce != AdmissionReusableAtUse`; current-use generation drift requires revalidation from the appropriate owner.

Neither artifact grants GLM execution authority. Their generic currentness/serializability laws are consumed only as typed derivation pressure.

## Material repair

Adds `tools/awj032/glm53_g5_owner_resolved_recompute_premise.py`.

The strong wrapper first executes canonical G5-v2 unchanged. Every existing G5 HOLD remains a HOLD. If canonical G5-v2 would emit `ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT`, the wrapper refuses to expose that consequence from the raw G4 projection alone.

It requires an injected G4 owner resolver to:
1. return an owner-state epoch before observation;
2. resolve a G4 drift observation bound to the exact G4 receipt digest, canonical changed-axis tuple and source-binding generations;
3. return the owner-state epoch again;
4. preserve one identical observation epoch across the bracket.

Failure, malformed output, binding mismatch or epoch movement fails closed.

The strongest output is only:

`OWNER_RESOLVED_RECOMPUTE_CANDIDATE`.

It deliberately does **not** reissue G5's bounded recompute admission, execute G3, or grant effect authority.

## External trust / ABA ceiling

The injected resolver is a runtime/control-plane trust boundary. This pure contract does not authenticate the resolver producer and does not prove that an epoch is globally change-complete or never reused.

Therefore every receipt permanently keeps:
- `resolver_authenticated_by_this_contract=false`;
- `owner_currentness_truth_proven_by_this_contract=false`;
- `epoch_change_complete_proven_by_this_contract=false`;
- `bounded_g3_recompute_attempt_admitted_by_this_contract=false`.

`StableResolverEpoch != AuthenticatedResolverIdentity`.

`EqualEpochLabels != SnapshotSerializabilityUnlessEpochIsChangeCompleteAndNonreused`.

This is the next explicit Gate-10 trust dependency rather than a hidden assumption.

## HyperDrive

Road transition:

`G4_v2_STRUCTURAL_DRIFT -> G5_v2_RAW_RECOMPUTE_ADMISSION -> W3_PREMISE_PROVENANCE_CONTRADICTION -> OWNER_RESOLVED_EPOCH_BRACKET -> RECOMPUTE_CANDIDATE_ONLY -> FUTURE_AUTHENTICATED_RESOLVER/ATTEMPT_BOUNDARY`.

Laws:
- `StructuralDrift != OwnerObservedDrift`.
- `CallerConstructibleG4Projection != CurrentOwnerState`.
- `RawG5Admission != OwnerResolvedRecomputePremise`.
- `OwnerResolvedCandidate != RecomputeExecutionAuthority`.
- `AdmissionValidAtProduce != AdmissionReusableAtUse`.
- `StableEpoch != ResolverAuthentication != OwnerCurrentnessTruth`.
- `ScaleProofPlaneBeforeWorkerCount`.

## HyperScale

HS1 remains sufficient. G5-v2 already exhausts its bounded control-state lattice. The missing evidence is orthogonal: provenance/serializability of the G4 drift premise.

More workers over the 108 structural states cannot establish who observed the drift.

`FiniteClassifierExhaustion(structure) != ObservationProvenance`.

Scale the proof plane from structural classification to owner observation rather than increasing worker count.

## K27 / persistent external coordinate memory

Coordinate scheme: `AURA-EXT-K27-SHA64x3-MOD27-v1`, where the full canonical URL SHA-256 remains authoritative over coordinate collision.

- Speculating Experts, arXiv:2603.19289 — SHA256 `5d7ebeab6eb71e25e533865b43f3ec45352ec1d3059b234b6144fda51be5853c` — K27 `(10,10,5)`.
- In-depth Analysis on Caching and Pre-fetching in MoE Offloading, arXiv:2511.05814 — SHA256 `fa705de5ab89bd75432ce6cf62d48c5d4b8b02990be1638776e5638db717ec95` — K27 `(20,26,23)`.
- SpecMD, arXiv:2602.03921 — SHA256 `466313fa47d3235d8b5441ce9342aaf6f2b88dbe49a60ba83c32eca41eb835d9` — K27 `(8,16,8)`.
- SpecPrefetch, arXiv:2607.24787 — SHA256 `05fa720414a31c670d7eef9f7bf1707bf7259c3419fb76248225a6e832064cca` — K27 `(12,8,25)`.
- GLM-5.3-Flash TensorSharp/llama.cpp community benchmark — SHA256 `5ceefcc4b3486a573ca145fdb12399dc30f1a4052e8b043008958a68c8673d69` — K27 `(10,18,20)`.

External pressure remains methodological only: expert-prefetch value varies with runtime, cache, hardware, access pattern and engine; prediction and structural labels cannot stand in for runtime observation authority.

Direct task-specific Google-Scholar-native discovery returned no stable stronger source in this pass: `SCHOLAR_DIRECT_GAP`.

`K27Coordinate != SourceIdentity != Currentness != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

Persistent external cache key:

`ExternalObservationKey = H(url_sha || retrieval_generation || source_revision || evidence_digest || currentness_generation || scope)`.

Invalidators: source/revision movement, evidence digest movement, currentness movement, scope movement and collision disposition movement.

## Triadic Process

**Thesis:** G5-v2's finite classifier correctly combines structural G4 drift, alias-stable progress, version transition and read-currentness.

**Antithesis:** the G4 drift input itself can be caller-constructed, so downstream gates can commute perfectly over an unobserved premise.

**Synthesis:** preserve G5-v2's algebra but place its positive drift path behind exact owner-resolved, epoch-stable observation; output only a recompute candidate until the external trust boundary is authenticated.

## Creation Process

Freeze exact G5-v2 cut -> reproduce raw positive path -> collision scan -> select O65 + PR769 foreign laws -> factor structural truth from observation provenance -> introduce owner resolver/epoch bracket -> bind exact receipt/axis/source identities -> attack missing resolver/errors/mismatch/epoch drift -> preserve base HOLDs -> prohibit authority widening -> hosted exact proof -> persist K27/HyperDrive -> recurse only after terminal proof and two fresh foreign artifacts.

## Ω8 crystalline lattice

- **W0 provenance:** exact #774 cut + exact-green O65 + exact-green #769.
- **W1 ordering:** G4 structural receipt -> owner observation -> stable epoch -> G5 base disposition -> W3 candidate/HOLD.
- **W2 substitutions:** caller drift, changed-axis, source-generation, receipt, resolver and epoch substitutions.
- **W3 contradiction:** raw structural drift can reach canonical G5-v2 admission without proving owner observation.
- **W4 factorization:** structural drift / observation provenance / resolver identity / epoch serializability / progress / source currentness / recompute admission / execution/effect stay separate leaves.
- **W5 synthesis:** O65 serializable-owner-state law × #769 generation-bound reuse law.
- **W6 quotient:** #774 remains canonical G5 algebra owner; this child owns only premise provenance and receives zero duplicate G5 consequence mass.
- **W7 temporal:** any G4 receipt, resolver generation or owner epoch movement reopens this premise.
- **W8 effect:** inactive; no execution/effect/Gate-10 authority.

## Claim ceiling

No GLM/model/provider/retrieval execution, G3 recompute execution, provider/network effect, expert-transfer effect, physical I/O observation, native-router mutation, source/currentness truth, resolver authentication, semantic K27 authority, native/private transformer KV access, G2/Gate-10, merge/deploy/spend, causal performance/quality result or public/financial/human effect is claimed.

# Arena Retrieval Progress Guard V1

Status: D0 / HS1 / NONPROMOTING

## Objective

Compile the Aura Drive 2 repeated-retrieval incident into the smallest deterministic scheduling membrane that can distinguish a lawful retry from a no-progress loop without taking ownership of source currentness, K27 semantics, provider effects, or model KV state.

## Exactly two semantic parents

1. Aura Drive 2 `ARENA-INCIDENT__REPEATED-RETRIEVAL-LOOP-GUARD__20260831`: same retrieval fingerprint + no new state requires an axis change or cone collapse.
2. EKI-1 / PR #731: stable external subject identity is separate from evidence generation; currentness is provider/source evidence, not a cached label; change-driven revalidation should reopen only affected hydration levels.

## Residual

`ExactRetrievalFingerprint + ObservedProviderState != ProgressUntil FingerprintDelta OR IndependentStateGenerationDelta OR EvidenceDelta`.

The guard therefore records six fingerprint axes:
- provider;
- tool;
- resource/ref;
- query/pattern;
- page/range;
- semantic purpose.

It separately records `provider_state_generation` and `evidence_digest` so a repeated query cannot impersonate progress merely because it ran again.

## Decisions

- `ALLOW_INITIAL`: first observation only.
- `ALLOW_CHANGED_AXIS`: the retrieval fingerprint changed.
- `ALLOW_STATE_TRANSITION`: provider state generation or evidence digest changed.
- `CHANGE_AXIS_REQUIRED`: first identical no-progress repeat.
- `COLLAPSE_CONE`: subsequent identical no-progress repeat.

## Different-J proof

Two independently shaped classifiers must commute:
- explicit decision tree;
- ordered rule-table formulation.

The focused proof exhausts 24 combinations:
`fingerprint changed × provider state changed × evidence changed × prior no-progress debt {0,1,2}`.

## HyperScale

HS1 is sufficient. This is a finite deterministic membrane; synthetic fanout would add coordination cost without increasing proof coverage.

`ScaleProofCone != ScaleHeadcount`.

## HyperDrive

The scheduling transitions are:

`INITIAL -> RETRIEVED`

`RETRIEVED + SAME_FINGERPRINT + SAME_STATE -> CHANGE_AXIS_REQUIRED`

`CHANGE_AXIS_REQUIRED + SAME_FINGERPRINT + SAME_STATE -> COLLAPSE_CONE`

`ANY + FINGERPRINT_DELTA -> ALLOW_CHANGED_AXIS`

`ANY + PROVIDER_STATE_DELTA_OR_EVIDENCE_DELTA -> ALLOW_STATE_TRANSITION`

These are control-plane transitions only. They do not execute providers or mutate external state.

## K27 / coordinate memory

K27 remains routing/locality metadata only. This guard intentionally does not derive or mint K27 placement. Any persistent cognition record produced from a receipt must retain stable source coordinates and obtain K27 placement from the canonical resolver/owner.

`RetrievalFingerprint != K27Path != SemanticIdentity != Currentness != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## Eight crystalline validation lenses

1. ordered: previous observation -> current observation -> decision;
2. adversarial: same query with changed tool/ref/page vs unchanged replay;
3. contradiction: repeated execution is not progress;
4. factorized: fingerprint/state/evidence/currentness/authority/effect remain separate;
5. synthesis: incident law × EKI generation law;
6. quotient: identical no-progress attempts collapse instead of multiplying work;
7. temporal: provider/evidence generation changes reopen the cone;
8. effect: provider/tool/write/native-KV effects remain unearned.

## Triadic Process

Thesis: repeated retrieval may be necessary to observe a changed external state.

Counterplane: repeating the same retrieval against unchanged state can become an infinite tool loop.

Synthesis: retry only when an independently observable axis or state generation changes; otherwise force axis change, then collapse.

## Creation Process

Freeze the two parents -> collision scan -> isolate deterministic state axes -> implement tree formulation -> implement table formulation -> adversarial substitutions -> exhaustive finite convergence proof -> hosted proof -> persist laws and scars -> recurse only from two new other-Agent artifacts.

## External falsification pressure

- PLACEMEM (arXiv:2607.04089) treats lifelong-agent memory as versioned, provenance-bearing, correction-aware state with invalidation rather than silent stale reuse.
- Is Agent Memory a Database? (arXiv:2605.26252) treats memory correctness as a property of governed state trajectories rather than isolated stored records.
- Current RAG practitioner reports independently describe silent cache staleness and recommend provenance/version-scoped invalidation before semantic reuse.
- Task-specific Google-Scholar-native discovery produced no stable stronger primary result in this pass; record `SCHOLAR_DIRECT_GAP` rather than inventing coverage.

External evidence is methodology/falsification pressure only and grants no Aura authority.

## Claim ceiling

No source currentness is proven by a changed token alone. No semantic truth, semantic identity, K27 authority, read/write/tool/provider authorization, effect authority, native/private transformer KV access, Gate-10, merge/deploy/spend, or public/financial/human effect is granted.

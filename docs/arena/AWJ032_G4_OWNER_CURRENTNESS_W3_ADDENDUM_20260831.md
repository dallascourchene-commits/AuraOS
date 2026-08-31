# AWJ032 GLM-5.3 G4 W3 — Owner-Resolved Currentness Addendum

Date: 2026-08-31  
Status: DRAFT / D0 / HS1 / NONPROMOTING / STACKED ADDENDUM  
Canonical semantic owner preserved: PR #757 / G4 generation-bound plan revalidation.

## Objective

Close one post-authoring W3 residual without taking G4 ownership:

`MatchingCallerConstructedCurrentReuseContext != OwnerResolvedCurrentReuseState`.

PR #757 correctly proves that any drift across prediction, calibration, policy, source binding, runtime, cache, storage geometry or host profile must reopen G3. Its public `revalidate_g3_plan(plan, current)` API, however, accepts `CurrentReuseContext` as a plain caller-constructible value object. Equality across eight caller-supplied strings therefore proves a deterministic structural comparison, but not that the values came from their respective owners or coexisted in one valid use-time state generation.

## Two other-Agent law anchors

1. **O65 / PR #704 — owner-resolved epoch-serializable pre-attempt admission.** Exact terminal head `7efca33d95f6dc39c4e159250d45373b260060ed`; dedicated run `33410032496`, job `99546999922`, SUCCESS. Reusable law: separately plausible current values do not form one lawful state unless the entire consequence-bearing read set is enclosed by one stable owner-state epoch. No caller-supplied currentness/policy/route/concurrency truth is accepted.
2. **G4 / PR #757 — current GLM transfer-plan revalidation owner.** The addendum consumes G4 unchanged and owns only the missing owner-resolution relation. Duplicate G4 semantic mass receives zero additional sibling credit.

Supporting Different-J scar: PR #736 independently demonstrated the broader provenance class `MatchingCallerWitness + UnauthenticatedReceipt != AuthenticatedObservation`. This addendum does not import PR #736 physical-observation semantics; it applies the same anti-self-authentication discipline to use-time currentness.

## Smallest-cone repair

Adds:
- `tools/awj032/glm53_g4_owner_currentness_addendum.py`
- `tools/awj032/test_glm53_g4_owner_currentness_addendum.py`
- `.github/workflows/aura-glm53-g4-owner-currentness-w3.yml`

The W3 public API is intentionally:

`revalidate_g3_plan_owner_resolved(plan, owner_resolver)`

There is no raw `current` argument.

The owner resolver must provide:
- a nonempty state epoch before the read;
- one `OwnerReuseStateObservation` bound to the exact G4 plan identity, the same epoch, a resolver generation, and the eight-axis `CurrentReuseContext`;
- the same state epoch after G4 classification.

Typed outcomes:
- `OWNER_REVALIDATED_UNCHANGED` only when the owner observation exactly matches the plan and the epoch is stable;
- `HOLD_RECOMPUTE_G3_OWNER_RESOLVED` when owner-resolved state is stable but one or more G4 axes drifted;
- `HOLD_OWNER_CURRENTNESS_REQUIRED` when owner state is unavailable, unknown, malformed, exceptional or plan-mismatched;
- `HOLD_OWNER_STATE_EPOCH_CHANGED` when the observation is not from the opened epoch or the epoch changes during revalidation.

## Triadic Process

**Thesis:** G4's eight-axis equality is the correct deterministic reuse comparison.

**Counterplane:** equality of caller-shaped values does not establish their provenance/currentness or that they coexisted.

**Contradiction:** `CurrentReuseContextValuesMatch => CurrentReuseStateProven` is false without an owner boundary.

**Synthesis:** owner-resolved plan-bound observation + optimistic before/after epoch serializability + unchanged G4 classifier.

## Creation Process

1. Freeze current G4 ownership and exact source surface.
2. Collision-scan for an existing owner-currentness repair; none found.
3. Reuse O65's terminal owner-state serializability law rather than inventing a trust root.
4. Preserve G4's eight-axis classifier unchanged.
5. Remove raw current-context input from the addendum public API.
6. Bind observation to exact plan identity + owner epoch + resolver generation.
7. Attack missing/error/malformed/mismatched owner observations.
8. Attack epoch drift before/after the complete read.
9. Reexecute G4 adversarials and add W3 adversarials in hosted proof.
10. Preserve all execution/effect ceilings and return ownership to PR #757.

## Omega-8 crystalline lenses

- **W1 ordered:** plan -> open epoch -> owner observation -> G4 comparison -> close epoch -> disposition.
- **W2 adversarial:** plan ID, observation epoch, resolver generation, each G4 axis, and owner failure substitutions.
- **W3 contradiction:** matching caller strings are not owner-currentness proof.
- **W4 factorization:** plan identity, owner currentness, state epoch, G4 drift, physical observation, execution and effect authority remain independent leaves.
- **W5 synthesis:** current G4 owner × terminal O65 serializability law.
- **W6 quotient:** G4 remains canonical owner; addendum receives only consequence-distinct W3 residue.
- **W7 temporal:** use-time owner epoch is identity-bearing and must remain stable across the read.
- **W8 effect:** unearned; effect-boundary revalidation remains mandatory.

## HyperScale

HS1 remains sufficient. The base eight-axis G4 lattice is finite; the new unresolved dimension is not more worker fanout but provenance/serializability of the observation itself. Same-boundary synthetic workers cannot manufacture owner currentness.

`ScaleUntilOwnerBoundaryResolved; SameObservationFanoutDoesNotIncreaseCurrentnessRank`.

## External Different-J pressure

SpecPrefetch (arXiv `2607.24787`) keeps native routing authoritative and uses prediction only to schedule transfers under runtime cache/bandwidth constraints. Fresh public GLM-5.3 DGX Spark and LocalLLaMA measurements continue to show configuration-sensitive behavior across FP8-KV, MTP/DFlash2, graph caching, offload, concurrency and KV-pool sizing. These sources support keeping runtime/cache/host state use-bound; they do not establish Aura owner currentness or performance.

Google Scholar direct task-specific discovery remains `SCHOLAR_DIRECT_GAP` for this cut.

## K27 / external coordinate memory

No new semantic coordinate is minted. Reuse PR #757's deterministic external-world K27 records for SpecPrefetch, the GLM runtime benchmark, LocalLLaMA and the Scholar gap. This W3 adds an internal reopen edge only:

`K27:AWJ032:G4:PREFETCH_PLAN_REVALIDATION -> W3:OWNER_CURRENTNESS_REQUIRED`.

`K27Coordinate != OwnerCurrentness != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV state is read, written or inferred.

## Laws

`MatchingCallerContext != OwnerResolvedCurrentState`.

`OwnerObservationMustBindExactPlanIdentity`.

`OwnerObservationEpochMustEqualOpenEpoch`.

`OwnerEpochBefore != OwnerEpochAfter => HOLD`.

`OwnerResolverUnavailableOrUnknown => HOLD`.

`OwnerResolvedAxisDrift => HOLD_RECOMPUTE_G3`.

`OwnerResolvedUnchanged != TransferExecutionAuthority`.

`EffectBoundaryRevalidationRemainsMandatory`.

## Claim ceiling

No model/provider execution, transfer effect, physical-I/O proof, native-route mutation, causal performance claim, source truth, semantic K27 authority, native/private transformer KV access, G2/Gate-10 promotion, merge/deploy/spend, or public/financial/human effect is granted.

This addendum is not a new G4 owner and must not receive duplicate G4 successor mass. Closure requires its dedicated exact-head hosted workflow to succeed; integration/disposition remains with the canonical G4 owner.

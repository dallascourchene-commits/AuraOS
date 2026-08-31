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

The injected resolver must provide:
- a nonempty state epoch before the read;
- one `OwnerReuseStateObservation` bound to the exact G4 plan identity, the same epoch, a resolver generation, and the eight-axis `CurrentReuseContext`;
- the same state epoch after G4 classification.

### External trust boundary

The resolver is a trusted integration boundary supplied by the owning runtime/control plane. This pure contract does **not** authenticate the resolver producer and does **not** independently prove source/runtime currentness truth merely because an object satisfies the resolver protocol.

For before/after epoch equality to imply one coherent snapshot, the runtime must additionally guarantee that the epoch token:
- changes for every consequence-bearing mutation relevant to the eight-axis read set; and
- is not reset/reused over the read window.

This is a seqlock/OCC-style integration invariant. PR #764 requires it but cannot prove it from inside the pure membrane.

Receipts therefore permanently carry:
- `owner_resolver_authenticated_by_this_contract=false`;
- `owner_currentness_truth_proven_by_this_contract=false`;
- `owner_epoch_change_complete_required=true`;
- `owner_epoch_change_complete_proven_by_this_contract=false`.

Typed outcomes:
- `OWNER_REVALIDATED_UNCHANGED` only when the resolver observation exactly matches the plan and the returned epoch is stable; this remains a structural/use-boundary result under the external trust assumptions above, not producer authentication;
- `HOLD_RECOMPUTE_G3_OWNER_RESOLVED` when resolver-observed state is stable but one or more G4 axes drifted;
- `HOLD_OWNER_CURRENTNESS_REQUIRED` when state is unavailable, unknown, malformed, exceptional or plan-mismatched;
- `HOLD_OWNER_STATE_EPOCH_CHANGED` when the observation is not from the opened epoch or the epoch changes during revalidation.

## Triadic Process

**Thesis:** G4's eight-axis equality is the correct deterministic reuse comparison.

**Counterplane:** equality of caller-shaped values does not establish provenance/currentness, producer authentication, or that the values coexisted.

**Second counterplane:** equality of opaque epoch labels does not establish snapshot serializability unless the owner epoch is change-complete and non-reused.

**Synthesis:** plan-bound resolver observation + externally guaranteed change-complete/non-reused epoch bracketing + unchanged G4 classifier + explicit non-authentication ceiling.

## Creation Process

1. Freeze current G4 ownership and exact source surface.
2. Collision-scan for an existing owner-currentness repair; none found.
3. Reuse O65's terminal owner-state serializability law rather than inventing a trust root.
4. Preserve G4's eight-axis classifier unchanged.
5. Remove raw current-context input from the addendum public API.
6. Bind observation to exact plan identity + owner epoch + resolver generation.
7. Attack missing/error/malformed/mismatched observations.
8. Attack epoch drift before/after the complete read.
9. Attack resolver self-authentication and ABA/reused-epoch assumptions.
10. Reexecute G4 adversarials, preserve all execution/effect ceilings and return ownership to PR #757.

## Omega-8 crystalline lenses

- **W1 ordered:** plan -> open epoch -> resolver observation -> G4 comparison -> close epoch -> disposition.
- **W2 adversarial:** plan ID, observation epoch, resolver generation, each G4 axis, resolver failure and reused/opaque epoch assumptions.
- **W3 contradiction:** matching caller strings are not owner-currentness proof; equal opaque epoch labels are not serializability proof without change-complete semantics.
- **W4 factorization:** plan identity, resolver provenance, currentness truth, epoch semantics, G4 drift, physical observation, execution and effect authority remain independent leaves.
- **W5 synthesis:** current G4 owner × terminal O65 serializability law.
- **W6 quotient:** G4 remains canonical owner; addendum receives only consequence-distinct W3 residue.
- **W7 temporal:** use-time epoch semantics are identity-bearing integration obligations; effect-time revalidation remains mandatory.
- **W8 effect:** unearned.

## HyperScale

HS1 remains sufficient. The base eight-axis G4 lattice is finite; the new unresolved dimension is an independent owner/trust observation boundary, not more worker fanout. Same-boundary synthetic workers cannot manufacture currentness, resolver authenticity, or epoch change-completeness.

`ScaleUntilOwnerBoundaryResolved; SameObservationFanoutDoesNotIncreaseCurrentnessRank`.

`SameEpochLabelFanout != SerializabilityProof`.

## External Different-J pressure

- SpecPrefetch (arXiv `2607.24787`) keeps native routing authoritative and uses prediction only to schedule transfers under runtime cache/bandwidth constraints.
- CoAgent (arXiv `2606.15376`) treats multi-agent serializability/conflict repair as an explicit runtime coordination problem rather than a local value-label property.
- Seqlock-style readers rely on a sequence/version token whose write semantics make before/after equality meaningful; the comparison syntax alone is insufficient.
- Commit-time authorization (arXiv `2607.10487`) reinforces that even a pre-attempt/current-use result does not replace freshness/rebinding at the durability/effect boundary.
- Current public GLM-5.3 DGX Spark and LocalLLaMA measurements remain configuration-sensitive across FP8-KV, MTP/DFlash2, graph caching, offload, concurrency and KV-pool sizing.

These sources are methodology/falsification pressure only. They do not establish Aura resolver authenticity, currentness, serializability or performance.

Google Scholar direct task-specific discovery remains `SCHOLAR_DIRECT_GAP` for this cut.

## K27 / external coordinate memory

No semantic coordinate is minted. Existing G4 coordinates are reused; the concurrency falsifiers are added only as retrieval/reopen handles:
- SpecPrefetch `arxiv:2607.24787` -> `(16,9,15)`;
- CoAgent `arxiv:2606.15376` -> `(17,23,18)`;
- seqlock reference `github:Amanieu/seqlock` -> `(10,1,19)`;
- commit-time authorization `arxiv:2607.10487` -> `(5,3,9)`;
- explicit Scholar gap remains `(12,12,16)`.

Internal reopen edge:

`K27:AWJ032:G4:PREFETCH_PLAN_REVALIDATION -> W3:OWNER_CURRENTNESS_REQUIRED`.

`K27Coordinate != OwnerCurrentness != ResolverAuthentication != EpochSerializability != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV state is read, written or inferred.

## Laws

`MatchingCallerContext != OwnerResolvedCurrentState`.

`ResolverProjection != ResolverProducerAuthentication != OwnerCurrentnessTruth`.

`OwnerObservationMustBindExactPlanIdentity`.

`OwnerObservationEpochMustEqualOpenEpoch`.

`OwnerEpochBefore != OwnerEpochAfter => HOLD`.

`EqualOpaqueEpochLabels != SnapshotSerializabilityUnlessChangeCompleteNonreusedEpoch`.

`OwnerResolverUnavailableOrUnknown => HOLD`.

`OwnerResolvedAxisDrift => HOLD_RECOMPUTE_G3`.

`OwnerResolvedUnchanged != TransferExecutionAuthority`.

`EffectBoundaryRevalidationRemainsMandatory`.

## Claim ceiling

No resolver producer authentication or independent owner-currentness truth is minted by this contract. No model/provider execution, transfer effect, physical-I/O proof, native-route mutation, causal performance claim, source truth, semantic K27 authority, native/private transformer KV access, G2/Gate-10 promotion, merge/deploy/spend, or public/financial/human effect is granted.

This addendum is not a new G4 owner and must not receive duplicate G4 successor mass. Closure requires its dedicated exact-head hosted workflow to succeed; integration/disposition remains with the canonical G4 owner.

# Alias-Stable Future-Read Currentness Preflight V1

Status: D0 / HS1 / NONPROMOTING / HOSTED-PROOF-REQUIRED

## Exactly two post-PR758 foreign terminal parents

1. PR #759 — scheme-alias-aware retrieval progress.
   - semantic head: `658b3bc651ee39454f6b94039d26ff76d48f73d8`
   - semantic source blob: `1abd821beb2a8a9a96b5ac2f0956195b20a321c7`
   - semantic test blob: `ddc88a73f49d6a09d67b388cf5c4958317e10ae2`
   - proof-only head: `cf6b07e5c498d7c429e6679a8ba5cec5e1e46ca6`
   - hosted proof run/job: `33436588718 / 99634405807`, SUCCESS.
   - reusable consequence: K27/route scheme rotation cannot reset retrieval no-progress debt; alias-aware progress remains separate from currentness/truth/authority.

2. PR #760 — NAV-13D × EKI-4 hydrated version handoff.
   - semantic head: `1a7ab9d884acc917ea28bea2b28bc747222f1aed`
   - source blob: `edac88e89e0659cd6bbf99c7a138e2ae3f516ae8`
   - test blob: `268889ff864c1fd7f80469071d6ec6738e941f36`
   - hosted proof run/job: `33436321891 / 99633531552`, SUCCESS.
   - reusable consequence: exact hydration + version-transition identity may produce only `HANDOFF_READY_CANDIDATE`; future read-currentness debt remains explicitly carried and unresolved.

Both semantic generations were created after PR #758's strict terminal cut `2026-08-31T20:27:47Z` and are consequence-distinct.

## Collision quotient

Bounded repository search found no existing owner for the exact post-handoff relation between alias-quotiented retrieval progress and carried future read-currentness debt.

This contract owns only **admission of a bounded currentness probe candidate**. It does not own source identity, alias-owner authentication, retrieval execution, currentness resolution, evidence admission, persistence, use authorization or effects.

## Residual

`HydratedVersionHandoffReady + AliasAwareRetrievalProgress != LawfulFutureReadCurrentnessProbeUntil ExactReadDebt + HandoffSourceView<->CurrentRouteAliasBinding + NoProgressDebt + Subject/EvidenceGenerationIdentity Commute`.

## Positive disposition

Only:

`FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE`.

This means the required future-read currentness probe is sufficiently bound to be attempted by its actual owner. It does **not** mean the source is current or true, that evidence is admitted, that a retrieval occurred, or that persistence/use/effects are authorized.

## Fail-closed dispositions

- `HOLD_PARENT_GENERATION`
- `HOLD_HANDOFF_NOT_READY`
- `HOLD_READ_DEBT_NOT_CARRIED`
- `HOLD_READ_AXES_MISMATCH`
- `HOLD_SOURCE_BINDING_REQUIRED`
- `HOLD_SOURCE_BINDING_MISMATCH`
- `HOLD_ALIAS_RESOLUTION_REQUIRED`
- `HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED`
- `COLLAPSE_RETRIEVAL_CONE`
- `HOLD_CLAIM_CEILING`

## Temporal law

The parent handoff carries these exact read debts:

- guard axes: `source`
- EKI-2 axes: `SOURCE_GENERATION_CURRENT`, `SOURCE_BODY_CURRENT`

A probe request must ask for those exact axes. Route aliases may change, but a source-route binding projection must tie the handoff subject/evidence/source URI to the current route view. The projection is opaque upstream state: this contract checks internal consistency but does not authenticate its owner or convert it into a currentness witness.

PR #759's alias-aware retrieval disposition then controls the retry surface:

- `ALLOW_INITIAL`, `ALLOW_CHANGED_AXIS`, `ALLOW_STATE_TRANSITION` may reach probe-candidate admission if every other hard gate passes;
- `HOLD_ALIAS_RESOLUTION_REQUIRED` remains HOLD;
- `CHANGE_AXIS_REQUIRED` remains HOLD and must change a genuine retrieval axis;
- `COLLAPSE_CONE` collapses the currentness-probe retrieval cone.

## Core laws

- `HandoffReadyCandidate != PersistentUseReady`.
- `FutureReadDebtCarried != FutureReadDebtResolved`.
- `RouteAliasRotationCannotPayFutureReadCurrentnessDebt`.
- `AliasAwareRetrievalProgress != ReadCurrentnessWitness`.
- `ExactRequestedReadAxesMustEqualCarriedDebtAxes`.
- `HandoffSourceMustBindCurrentRouteBeforeProbeAdmission`.
- `NoProgressDebtSurvivesAliasQuotientIntoFutureReadPreflight`.
- `ProbeAdmission != ReadCurrentness != EvidenceAdmission != UseAuthority`.
- `K27Placement != SemanticIdentity != VersionOrder != Currentness != Authority`.
- `CoordinateMemory != MODEL_PREFIX_KV`.

## Triadic Process

Construct: #760 preserves exact subject/evidence/material identity and carries future read-currentness debt forward.

Challenge: #759 shows that route/scheme movement can be only a projection alias and cannot be counted as retrieval progress. Therefore reopening through another coordinate representation cannot pay temporal read debt.

Invariant/synthesis: preserve the handoff's exact temporal debt and admit only a bounded currentness probe whose source-route binding and alias-aware progress remain consequence-distinct from route movement.

## Creation Process

1. Freeze PR #759 and #760 semantic/proof identities.
2. Collision-scan post-handoff/read-debt owners.
3. Factor handoff identity, exact read axes, source-route binding, alias-aware progress and claim ceiling.
4. Define fail-closed precedence.
5. Implement two differently shaped classifiers.
6. Attack parent generation, handoff readiness, debt axes, subject/evidence/source/view binding, alias resolution and no-progress states.
7. Exhaust the finite 192-state Different-J cross-product.
8. Revalidate parent hosted proofs and exact blobs.
9. Enforce permanent nonpromotion.
10. Persist/rebase only after hosted exact-head SUCCESS.

## Ω8 / eight crystalline validation

- W0 provenance: exact post-cut parent heads/blobs/proofs.
- W1 order: terminal handoff -> exact carried debt -> source/current-route binding -> alias-aware progress -> bounded probe candidate.
- W2 substitutions: parent head, subject, evidence generation, source URI, view digest, debt axes, alias resolution and retry decision.
- W3 contradiction: route projection movement can coexist with zero semantic progress; handoff readiness can coexist with unresolved read currentness.
- W4 factorization: hydration, version transition, route projection, source identity, retrieval progress, currentness, evidence, persistence and effects remain independent leaves.
- W5 exact two-parent synthesis: #759 × #760.
- W6 collision quotient: route aliases and repeated no-progress observations do not create new evidence/semantic mass.
- W7 temporal: future read debt survives handoff; source/evidence/route/proof generations remain reopen invalidators.
- W8 effects: unearned.

HS1 remains sufficient because this is a finite control membrane with a complete 192-state classifier lattice; worker multiplication cannot strengthen identical observation/proof boundaries.

## External Different-J pressure

External sources grant no Aura authority.

- FreshCache, arXiv:2607.04281: semantic cache reuse requires explicit temporal freshness/risk admission rather than similarity/hit alone.
- Grounded Cache Routing, arXiv:2605.27494: safe reuse depends on evidence overlap, source-version validity and support gates rather than cache-key similarity.
- Current production-RAG practitioner reports describe source storage and retrieval/index state diverging across handoffs; provenance, source versions, content hashes and reconciliation are required to diagnose stale-but-plausible retrieval.
- Direct task-specific Google Scholar discovery returned no stronger stable Scholar-native result for this exact relation in this pass: `SCHOLAR_DIRECT_GAP`.

## Claim ceiling

No source owner authentication, source currentness, read currentness, semantic truth, evidence admission, retrieval execution, materialization, persistent store mutation, persistent-use authorization, instruction/tool/provider/model execution, effect authority, semantic K27 authority, native/private transformer KV access, Gate-10, merge/deploy/spend, or public/financial/human effect is granted.

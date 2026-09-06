# Semantic-Domain-Bound Evidence Reproof Bridge — O4R1

## Objective

Repair O4's over-broad generation invalidation without weakening semantic currentness.

The original O4 treated every owner-verifier generation movement as a reproof seed. Foreign successor pressure exposed a narrower lawful distinction:

`OwnerTransition -> {EXACT | REBIND | REPROVE | HOLD}`

- `EXACT`: generation, projection, and semantic-domain roots are unchanged.
- `REBIND`: generation moved while exact projection and semantic-domain roots stayed unchanged. The proof-time witness may only survive as an explicit nonauthorizing rebind obligation bound to the current owner surface.
- `REPROVE`: projection or semantic-domain identity moved; the changed node becomes an exact invalidation seed and only its dependency-closed descendants reopen.
- `HOLD`: required owner identity is malformed, incomplete, or unknown.

## Reproof pressure

O4's original foreign parents remain the lawful creation parents:

- AGENT_12 / PR #838 — dependency-scoped AirLLM security reproof.
- AGENT_08 / PR #831 O2R3 — exact current-owner semantic replay and projection currentness.

O4R1 is a repair/reproof, not a successor mint. It incorporates consequence pressure from:

- AGENT_13 / PR #839 — generation movement must be classified before reuse; generation-only movement can be proof-neutral when the complete semantic/admission/verifier surface is exact.
- AGENT_01 O18 — provider/admission generation movement with exact semantic-domain/projection/source identity is `REBIND_ADMISSION`, while semantic-domain/projection movement is `REPROVE_SECURITY`.

Those pressures do not receive new-parent credit for an O5 successor.

## Keeper laws

`SemanticDomainMoved | SemanticProjectionMoved -> REPROVE -> ExactInvalidationSeed -> DependencyClosedDescendantsToRecompute`.

`GenerationMoved AND ProjectionExact AND SemanticDomainExact -> REBIND`.

`Rebind != DirectReuse`.

`Rebind => ExactProofTimeWitness AND ExactCurrentOwnerSurface AND D0`.

`Malformed | Incomplete | Unknown -> HOLD / fail closed`.

`ExternalReceiptRoot` and `OwnerReplayReceiptRoot` remain opaque upstream proof obligations. This bridge binds them but does not authenticate them.

`ProviderObserved != ProviderAttested != SemanticTruth != EffectAuthority`.

## Why this matters

A verifier generation can move for proof-neutral reasons. Recomputing every node owned by that verifier spends verification work without increasing semantic assurance when the current owner has replayed the same exact projection and semantic-domain identities. Conversely, equal-looking values or self-consistent digests cannot justify reuse when the semantic domain or semantic projection changes.

O4R1 therefore separates semantic invalidation from succession bookkeeping while preserving a fail-closed HOLD state.

## Authority ceiling

D0 control-plane prototype only. No external/provider truth, hosted PASS, model execution, physical performance/energy claim, production deployment, merge authority, effect authority, private/native transformer KV, canonical promotion, or Gate10.

# Arena Successor Admission Gate — falsifier repair cell

This worker cell converts an observed ancestry failure into a deterministic pre-mint gate.

It does **not** claim an Arena successor objective. It exists because the prior O2 implementation was later marked stale/invalid: both of its declared parents were same-actor GPT56SOL artifacts, violating the standing requirement for exactly two fresh consequence-distinct artifacts from other Agents.

## Keeper

`SuccessorMintEligible => ExactlyTwoParents ∧ BothForeignToCurrentActor ∧ DistinctActors ∧ DistinctLineages ∧ StrictlyPostPredecessorCut ∧ NotFutureDated ∧ ArenaSemanticTerminal ∧ NotProjection ∧ DistinctTypedConsequenceRoots ∧ DistinctReceipts ∧ DistinctDerivations`

Corollaries:

- `SameActorCopies != TwoForeignParents`
- `SameLineageFanout != IndependentEvidence`
- `Projection/AppendCandidate != SemanticTerminal`
- `ModifiedAfterCut != CreatedAfterCut`
- `LexicallyDifferentSummary != ConsequenceDistinct`
- `K27Coordinate != Identity != Truth != Currentness != Authority`
- The gate clamps its own authority to D0.

## Typed consequence root

Consequence distinction is computed over structured effect fields (`consequence_axes`, `consequence_action`, `invariant_delta`) rather than titles or prose similarity. This does not prove semantic independence, but it makes simple renaming/projection duplication insufficient.

## 8 crystalline hard lenses

1. foreign actor identity
2. distinct parent actors
3. strict temporal freshness
4. current observation / no future dating
5. semantic-terminal class / no projection
6. distinct lineage/derivation
7. typed consequence distinction
8. exact receipt distinction

Only all-green survives.

## 13D collapse

The 8 hard lenses above are followed by 5 contextual axes. Context never repairs an invalid or unresolved hard ancestry axis.

## HyperScaling

HS1000 is a 1,000-case adversarial campaign (10 mutation families × 100), not a claim of 1,000 breakthroughs. Omega8 exhausts all 3^8 hard-axis states. The 13D tail exhausts all 3^5 context states against invalid and unresolved hard cores.

## External pressure

Recent research on governed shared memory and provenance-aware multi-agent graphs supports explicit lineage, scope, temporal supersession, and action gating. Community reports likewise warn that multiple agreeing agents may collapse to one copied evidence path. These sources are design pressure only; they do not mint Arena parent authority.

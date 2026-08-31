# Aura K27 ASTGE current typed profiled scopes

D0 / NONPROMOTING / HS1.

This bridge makes a profiled Python lexical-scope inventory hydration-current only when three independently owned facts agree:

1. PR495 admits one exact full source body as CURRENT and derives a versioned SyntaxGraph source binding from that receipt;
2. the actual source text independently rebuilds the O7 grammar/profile-bound SyntaxGraph and CPython-conformant lexical-scope inventory;
3. PR490 carries the witnessed body generation as `SourceGenerationV1`, which cannot be confused with snapshot, placement, or graph-serving generation types.

## Contract

`admit_current_typed_profiled_python_scopes(...)` builds the exact pinned Python named-node projection from the supplied source, asks PR495 to admit that projection against the independent CURRENT body receipt, then independently builds the profiled scope graph from the actual source and requires the two complete `SyntaxGraphIdentityV1` values to be equal.

This equality matters: a CURRENT-looking receipt whose body SHA belongs to different source text cannot be pasted onto a profiled scope tree merely because the syntax shape looks plausible.

The positive receipt retains:

- exact SyntaxGraph digest;
- exact source-body witness identity/currentness;
- typed `SourceGenerationV1` + explicit `GenerationDomainV1::Source` coordinate;
- 15-scope CPython-conformant profiled lexical inventory;
- false runtime/call/K27/authority/effect claims.

## Laws

`CurrentBodyReceipt != ActualSourceUnlessSyntaxGraphIdentityMatches`.

`SourceGenerationV1 != PlacementGenerationV1 != SnapshotGenerationV1 != GraphServingGenerationV1`.

`SameNumericGenerationValue != SameGenerationDomain`.

`CurrentProfiledScope != RuntimeNameResolution`.

`CurrentProfiledScope != CallGraph`.

`CurrentProfiledScope != SemanticK27Authority`.

`CurrentSourceBody + ProfiledLexicalScope => CurrentScopeHydrationCandidate`, not runtime truth or effect authority.

## Adversarial contract

- exact CURRENT body + exact source/profile/scope graph passes;
- STALE body cannot admit current scope hydration;
- CURRENT receipt with another body's SHA fails full graph-identity equality;
- witnessed file ID must equal the profiled source file ID;
- equal numeric source and placement generations remain different typed coordinates;
- compile-fail contract proves `PlacementGenerationV1` cannot inhabit a source-generation parameter.

## Claim ceiling

No identifier-use resolution, global/nonlocal semantics, free/cell variables, closure/class lookup semantics, import/reexport/inheritance/attribute resolution, call/dataflow graph, runtime binding winner/value, semantic K27 minting, WorkCapsule integration, merge/deploy/provider/human/public effect, or Gate-10 authority.

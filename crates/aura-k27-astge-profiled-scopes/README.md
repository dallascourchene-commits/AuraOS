# Aura K27 ASTGE profiled nested scopes

D0 / NONPROMOTING / HS1.

This crate composes two independently verified proof planes:

1. the grammar/parser/normalization/source-bound `SyntaxGraphIdentityV1`; and
2. the conservative Python module/function/class lexical-scope inventory verified against CPython `symtable`.

## Proof target

Every non-module scope and every function/class binding must resolve to the exact node in one admitted `python/NAMED_ONLY/v1` SyntaxGraph while preserving:

- exact source file and byte span;
- higher-owner semantic-handle digest;
- lexical owner/child scope relation;
- canonical syntax ordinal inside the profiled graph.

The canonical graph digest binds parser binding version, grammar version/ABI, normalization profile, source-owner reference, source-generation reference, file ID, source SHA-256, ordered syntax projection, and direct parent-child topology.

## Identity boundary

Storage-local AST node IDs and inventory-local scope IDs remain witnesses only. They are not semantic identity. PR486 proves consistent local-node-ID remapping can preserve the same SyntaxGraph digest; this composition therefore anchors scope records to the graph digest plus canonical syntax ordinal instead of promoting local IDs.

## Laws

`ScopeLocalId != SemanticIdentity`.

`AstLocalNodeId != SyntaxGraphIdentity`.

`GrammarVersion + NormalizationProfile + SourceGeneration are SyntaxGraph identity inputs`.

`StatementNesting != LexicalScope`.

`ScopeOwnership != RuntimeNameResolution`.

`CPythonSymtableAgreement != RuntimeValueResolution`.

`ProfiledScopeAnchor != CallGraph`.

`SyntaxGraphIdentity != SemanticK27Authority`.

## Adversarial contract

- exact 15-scope fixture remains bound to the profiled graph;
- consistent local-node-ID remapping leaves SyntaxGraph digest unchanged;
- normalization-profile substitution changes graph identity;
- source-generation substitution changes graph identity;
- grammar-version substitution changes graph identity;
- semantic-handle drift in a scope anchor fails closed.

## Claim ceiling

No identifier-use resolution, `global`/`nonlocal`, free/cell-variable proof, closure semantics, class lookup semantics, lambda/comprehension/type-parameter scopes, imports/reexports, inheritance, attributes, call graph, runtime binding winner/value, semantic K27 minting, WorkCapsule integration, merge/deploy/provider/human/public effect, or Gate-10 authority.

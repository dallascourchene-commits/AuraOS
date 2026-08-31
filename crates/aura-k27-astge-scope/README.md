# Aura K27 ASTGE source-scope verifier

D0 / NONPROMOTING.

This crate closes the Gemini/DeepSeek D6 byte-scope defect without changing the ASTGE storage ABI.

## Proof target

Given:
- exact admitted original source bytes;
- a source-owner generation + SHA-256 binding;
- explicit half-open authorized byte spans;
- explicit original-coordinate replacement operations; and
- the proposed candidate bytes;

the verifier proves only that the candidate is exactly reconstructible by applying those operations and that every operation is wholly inside an authorized span.

This protects the prefix, suffix, and every gap between disjoint authorized spans. Variable-length replacements are supported because the verifier does not infer alignment from a post-hoc line diff.

## Fail-closed details

- stale/wrong original content fails its source binding;
- malformed or overlapping authorization fails;
- out-of-range or overlapping replacement operations fail;
- replacements outside authorization fail even if they are byte-for-byte no-ops;
- a boundary insertion requires an explicit zero-width authorization at that exact byte coordinate;
- empty authorization permits only an identical candidate;
- candidate bytes that cannot be reconstructed from the declared operations fail.

## Separation laws

`DiffLooksSmall != MutationAuthorized`.

`TestsPass != PatchCorrect`.

`AuthorizedByteScope != SemanticCorrectness`.

`K27Coordinate != MutationAuthority`.

`TreeSitterSpan != SourceCurrentnessAuthority`.

`OutsideScopeUnchanged == true` does not grant review, execution, merge, deployment, provider-spend, human, or external-effect authority.

## Intended integration

A higher source/currentness owner supplies the exact source binding and authorized spans. Tree-Sitter/ASTGE may supply candidate source coordinates, but this crate does not trust parser output to mint authority. A later B- semantic verifier may consume the successful byte-scope receipt as one necessary condition, never as sufficient semantic approval.

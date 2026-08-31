# Aura K27 ASTGE source-bound review membrane

D0 / NONPROMOTING / HS1.

This crate composes two independently verified source-side proof planes onto the current ASTGE symbol/storage stack:

1. `file_id -> exact current source` through an admitted `SourceLocatorV1` with source generation, exact length and SHA-256; and
2. fail-closed byte-scope verification from explicit original-coordinate authorized spans and explicit replacement operations.

## Objective

Given one current persisted AST/symbol node record and a higher-owner edit authorization, prove that:

- the record resolves to the exact revalidated current source file through `file_id`, never a hardcoded or guessed filename;
- the stored node span materializes the exact current source bytes;
- the complete original source matches the same source-owner generation/length/digest used by the admitted catalog;
- the candidate source is exactly reconstructible from declared original-coordinate replacements;
- every declared replacement lies wholly inside an explicitly authorized source span;
- prefix, suffix and protected gaps remain unchanged.

The membrane produces only an admission for later semantic review.

## Authority separation

The AST node span, symbol name, semantic-handle digest, K27 coordinate and physical storage location are evidence coordinates only. None automatically becomes an authorized mutation span.

`TreeSitterSpan != MutationAuthority`.

`SymbolAnchor != RuntimeBinding != MutationAuthority`.

`FileId != FilesystemPath`.

`CurrentSourceMaterialized != SemanticCorrectness`.

`OutsideAuthorizedScopeUnchanged != BMinusApproved`.

`BMinusApproved != CommitAuthorized != ExternalEffectAuthorized`.

## Adversarial contract

The focused integration suite covers:

- two duplicate module-level symbols with explicit selection of one physical AST node;
- exact current-source materialization for the selected record;
- one valid explicitly scoped variable edit;
- unauthorized suffix mutation despite an otherwise valid declared symbol edit;
- mutation of the *other* duplicate symbol while only the selected duplicate is authorized;
- source drift after catalog admission.

## Provenance

The convergence history retains the verified current symbol stack plus exact source-materialization and source-scope parents. Their source ownership is reused rather than reimplemented. This crate owns only the composition seam.

## Claim ceiling

No semantic patch correctness, runtime name resolution, call graph, B-minus approval, commit/merge authority, source write, deployment, provider spend, human authority, public effect, Gate-10 promotion, mmap safety/performance, or physical crash durability is claimed.

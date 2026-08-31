# Aura K27 ASTGE source materialization

D0 / NONPROMOTING / HS1.

This crate closes the Gemini D9 demo defect where context hydration ignored `file_id` and hardcoded a filename.

## Contract

A higher source/currentness owner supplies `SourceLocatorV1`:

- `file_id`;
- portable repository-relative path;
- source generation;
- exact byte length;
- SHA-256 of the complete source file.

Catalog admission validates the current file bytes and rejects ambiguous/unsafe locator structure. Materialization looks up the S-plane node's `file_id`, revalidates the exact file, bounds-checks its stored byte span, and returns those bytes with the admitted source generation/hash.

## Path discipline

V1 uses a deliberately narrow portable repo-relative grammar:

- `/` separators only;
- no absolute paths;
- no `.`, `..`, empty components, drive-style `:`, backslash, or control characters;
- every path component is checked with `symlink_metadata`;
- symlinked source paths are rejected rather than followed;
- target must be a regular file.

This avoids turning path normalization heuristics into source authority.

## Laws

`StorageLocalFileId != FilesystemPath`.

`PathExists != SourceCurrent`.

`SourceLocatorBinding = FileId + RelativePath + SourceGeneration + Length + Digest`.

`SourceBytesChanged => RevalidationFails`.

`TreeSitterSpan != SemanticIdentity`.

`MaterializedSourceSlice != ReviewOrEffectAuthority`.

`CODEMAPPath != SourceTruthUnlessAdmittedByCurrentSourceOwner`.

## External pressure

Reproducible-build and software-provenance work emphasizes that source identity needs recoverable, verifiable metadata rather than names alone. Current Rust practitioner discussions also show filesystem path equality/normalization is platform- and filesystem-dependent; V1 therefore uses a narrow path grammar plus content binding instead of path hashing as identity.

## Claim ceiling

No semantic identity, source-authority minting, CODEMAP migration, WorkCapsule integration, cross-platform path equivalence proof, symbol/call graph, merge/deploy/provider/public effect, or Gate-10 promotion.

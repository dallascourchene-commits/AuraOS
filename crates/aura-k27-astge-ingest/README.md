# Aura K27 ASTGE Tree-Sitter ingestion membrane

This crate is an additive consumer of the PR461 physical S-plane contract.

It proves only a narrow syntax-ingestion consequence:

- parse Tree-Sitter Python named syntax nodes;
- assign deterministic storage-local node IDs in preorder;
- preserve exact file ID and byte spans;
- materialize AST parent-to-child edges into PR461 fixed pages;
- require semantic-handle digests to be supplied by a higher semantic/source owner;
- round-trip bounded AST cones through the S-plane reader and compare them with an independent direct adjacency oracle.

It deliberately does **not** derive semantic K27, source truth, symbol identity, call-graph edges, authority, currentness, or effect permission. `node_id` is storage-local. `kind` remains ingestion metadata and does not become a semantic handle by itself. The supplied semantic handle is opaque to this crate.

The first grammar fixture is Python only. Tree-Sitter language expansion is a later typed generation, not an implicit transfer from Python coverage.

## Explicit non-claims

This crate does not prove:

- symbol resolution or call graph correctness;
- semantic K27 assignment or physical locality superiority;
- mmap safety or cold-NVMe performance;
- crash-atomic publication;
- CODEMAP or WorkCapsule integration;
- language-agnostic ingestion;
- merge/deploy/provider/public effect authority.

Current dependency versions are pinned directly in `Cargo.toml`; transitive dependency lockfile admission remains a separate supply-chain/currentness concern.

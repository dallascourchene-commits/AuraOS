# Aura K27 ASTGE — Storage Kernel V0

This crate is the first repository materialization of the Gemini-proposed K27-indexed out-of-core AST graph engine. V0 deliberately narrows the draft to the storage properties that can be made executable and falsifiable before Tree-Sitter ingestion, agent-loop integration, signed receipts, C/Python/Node bindings, or performance claims.

## Different-J repairs from the Gemini draft

1. **Binary layout is encoded, not transmuted.** Node records are exactly 64 bytes and edge blocks exactly 4096 bytes by explicit little-endian byte offsets. No `repr(C)` + `bytemuck::Pod` layout assumption is used.
2. **Record position and `node_id` are the same invariant.** V0 requires dense IDs in record order, preventing preorder-ID/postorder-write aliasing.
3. **Published mmap targets are immutable generations.** A writer creates `gen-N` completely, syncs it, then atomically advances the small `CURRENT` pointer. Existing readers stay pinned to their old generation.
4. **PBNs are generation-local and never reset into an appended mutable file.** Every generation contains its own node table and edge pages.
5. **K27 remains placement metadata.** `coordinate_generation` is bound into every node and the manifest. Changing it invalidates reuse even if the coordinate value is unchanged. V0 explicitly records `k27_physical_ordering_proven=false` because it does not yet reorder blocks by K27 prefix.
6. **Mmap is decoded as bytes.** The reader never creates typed Rust references directly into the file-backed map.
7. **Digest and size checks precede mapping.** `CURRENT` binds the manifest digest; the manifest binds exact file lengths and SHA-256 digests.

## Storage publication law

```text
build immutable generation
-> sync node/edge/manifest files
-> mark generation files read-only on Unix
-> sync generation directory
-> rename temp generation into final generation path
-> sync root directory
-> write + sync temporary CURRENT
-> rename CURRENT
-> sync root directory
```

A crash before `CURRENT` publication can leave an orphan complete generation, but it cannot make a reader select a partially written generation through this API.

## Current query surface

`SnapshotReader::query_affected_cone()` performs a bounded BFS over generation-pinned node records and CSR-style edge pages, with optional K27 prefix filtering and edge-kind filtering. It reports actual edge traversals and unique edge blocks touched; it makes no latency or I/O-amplification superiority claim.

## Explicitly not proved in V0

- Tree-Sitter AST ingestion or stable Source ID policy;
- K27 physical locality superiority or semantic locality;
- incremental/delta updates or LSM compaction;
- arbitrary concurrent writers;
- crash recovery beyond immutable-generation + atomic-current publication;
- external-process protection against malicious mutation of mapped files;
- semantic affected-cone correctness for AuraOS Review/Arena owners;
- Triadic B- source-diff scope verification;
- cryptographic signer identity or signed receipt ledger;
- C FFI, Python, Node-API, MCP, or AuraOS runtime integration;
- throughput, sub-microsecond lookup, TTFT, memory, SSD, or token savings.

Those are successor objectives only after the exact V0 Rust contract passes.

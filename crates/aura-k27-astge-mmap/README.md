# Aura K27 ASTGE mmap generation adapter

This optional sibling extends the safe `aura-k27-astge` S-plane with one narrow OS-backed mmap boundary and immutable-generation publication.

It exists because the canonical parent deliberately proves only `Read+Seek` storage. The mmap adapter does **not** remove `#![forbid(unsafe_code)]` from that parent crate.

## Publication model

Each storage generation is immutable:

```text
node-index.bin + pages.bin
        ↓ write/sync/hash
manifest.txt
        ↓ write/sync
read-only generation directory
        ↓ rename into gen-N
CURRENT.tmp
        ↓ atomic rename
CURRENT
```

A reader resolves `CURRENT`, verifies the manifest digest, verifies exact file sizes and SHA-256 digests, then maps that exact `gen-N`. Publishing `gen-(N+1)` changes only the small `CURRENT` pointer; an already-open reader stays pinned to `gen-N`.

## Unsafe boundary

`memmap2::MmapOptions::map()` is unsafe because a different process can still mutate or truncate the backing file. This crate isolates those map calls in `MappedGenerationV1::open_current()` after digest/length validation. Unix publication also marks generation files read-only.

That is **not** protection against a privileged or hostile external process. Every manifest fixes:

- `external_post_map_mutation_protected=false`
- `k27_physical_locality_proven=false`

The parent byte decoder remains the authority for physical page structure; mmap does not create a new semantic/source/currentness authority plane.

## K27 and locality

The adapter carries the parent's placement generation and placement-scheme digest. It does not derive semantic K27 coordinates from source IDs and does not claim that hash-prefix placement improves locality. PR459's matched reference benchmark is the standing negative control: physical placement must beat contiguous CSR on the same graph before a locality claim can open.

## Explicitly unproved

- zero-copy semantic graph traversal (the parent `PageSource` currently returns an owned 4KB page);
- protection from external post-map mutation or truncation;
- cold-NVMe behavior, SIGBUS immunity, or OS page-cache policy;
- mmap speedup or lower memory use;
- K27 physical locality superiority;
- transactional incremental append/WAL/compaction;
- Tree-Sitter/CODEMAP ingestion;
- semantic affected-cone admission;
- Triadic B- source-diff verification;
- WorkCapsule, KV-prefix, FFI, Python, Node-API, or model runtime integration.

Those remain successor objectives and must use matched evidence rather than inheriting claims from this adapter.

# Aura K27 ASTGE — Storage Kernel V0

Status: **experimental / D0 / nonpromoting**.

This crate is the first executable slice of the Aura K27-indexed out-of-core AST graph-engine mission. It intentionally implements only the persistence/index correctness kernel needed before Tree-Sitter ingestion, `mmap` traversal, AuraOS context hydration, FFI, or performance claims can be trusted.

## Why this starts below the Gemini prototype

The mission transcript proposes Rust `repr(C, align(...))` structs as the persistence format. That makes compiler layout part of the disk ABI and the illustrated CSR structure does not fit the claimed 4096-byte page. It also assigns node IDs before recursive descent but emits node records after descendants, while the reader treats `node_id` as the direct table index. Finally, append examples restart node IDs and physical block numbers from zero.

V0 removes those ambiguities:

- CSR pages are literally `[u8; 4096]` with explicit little-endian field offsets;
- node records are literally 64-byte frames with an explicit schema field and reserved bytes;
- K27 trits reject the reserved `11` encoding and high bits;
- segments sort/validate direct node-ID order before persistence;
- `base_node_id`, `base_pbn`, and `generation` are explicit append coordinates;
- every node must resolve to an existing page/row and its declared out-degree must equal the CSR row;
- the crate forbids `unsafe` code.

## Not proven by V0

V0 does **not** prove:

- SHA-256 SID-to-K27 projection semantics;
- Tree-Sitter AST ingestion or symbol/call/data-flow extraction;
- `mmap` correctness, crash consistency, NVMe locality, or OS page-cache behavior;
- atomic multi-file commits or durable recovery;
- AuraOS affected-cone semantic equivalence;
- token/TTFT reduction;
- latency, memory, IOPS, energy, or performance superiority;
- Prime Directive signature authority;
- C/Python/Node FFI safety.

Those are separate consequence planes and require matched controls plus exact hosted or owner-host evidence.

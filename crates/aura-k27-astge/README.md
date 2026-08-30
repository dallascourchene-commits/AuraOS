# Aura K27 ASTGE — S-Plane Page Contract V1

Status: D0 / experimental / nonpromoting / no external effect.

This crate is the first native storage cell for the Gemini-chat `Aura-K27-ASTGE` mission. It intentionally implements only the **physical storage plane (S)**. It does not decide semantic coordinates, source truth, currentness, authority, reviewer state, or human consequence.

## Upstream AuraOS contract

The storage owner consumes already-admitted higher-layer identity/currentness state. Current Aura affected-cone law separates:

- semantic/source identity from physical retrieval placement;
- coordinate generation from semantic target/source generation;
- coordinate locators from authority/currentness/source truth;
- physical relocalization from semantic reclassification.

A physical placement key must therefore be scheme-qualified by its owner before reaching this crate. The V1 page stores only an opaque `placement_scheme_digest` plus `placement_generation`. The engine never derives a bare K27 coordinate from a semantic SID.

## V1 binary geometry

Exactly one page is 4096 bytes:

- 64-byte header;
- 256 row entries × 4 bytes = 1024 bytes;
- 320 target node IDs × 8 bytes = 2560 bytes;
- 320 edge-kind bytes;
- 128-byte zero-reserved trailer.

`64 + 1024 + 2560 + 320 + 128 = 4096`.

Node-index records are exactly 64 bytes and keep an opaque 32-byte semantic-handle digest separate from physical PBN/row placement.

All V1 parsing is field-by-field little-endian. The crate has `#![forbid(unsafe_code)]`; no byte slice is reinterpreted as an aligned Rust struct.

## Gemini-prototype falsifiers retained as tests/design scars

1. The proposed `K27CSRBlock` with 384 `u64` targets, 384 edge kinds, row offsets and 120 bytes of padding does not fit a 4096-byte `repr(C, align(64))` object. V1 replaces it with explicit offsets whose total is compile-time checked.
2. The prototype assigns `node_id` before recursive child traversal but pushes the node record after the children. A reader that performs `node_table[node_id]` can therefore return the wrong record. V1 builds an explicit ID→record index and tests out-of-order records.
3. A fresh serializer starting `current_pbn=0` cannot safely append to an existing edge file. V1 node records use absolute PBNs within the admitted storage generation; a later writer must allocate them from an owner-controlled generation/allocator.
4. File-backed `mmap` is an unsafe lifetime/mutation boundary in Rust. V1 establishes the byte contract and bounded reader with ordinary `Read+Seek`; a later mmap backend must prove immutable-file/generation lifetime and alignment invariants against the same parser tests.
5. Physical placement generation may change while the higher semantic handle remains unchanged. V1 makes that separation executable.

## What V1 proves

- deterministic 4096-byte physical page serialization/parsing;
- exact 64-byte node-index record serialization/parsing;
- fail-closed malformed page geometry;
- bounded affected-cone physical traversal;
- explicit node-ID lookup independent of record order;
- absolute physical PBN use;
- physical-placement generation is separate from semantic-handle identity.

## What V1 does **not** prove

- Tree-Sitter serialization;
- semantic K27 coordinate assignment;
- mmap safety or performance;
- SSD/NVMe performance;
- crash-atomic append/commit;
- cryptographic tamper evidence;
- B− semantic diff verification;
- AuraOS WorkCapsule integration;
- KV-prefix reuse;
- Node.js/Python/C FFI;
- any review, execution, deployment, Gate-10, or human authority.

Those are separate proof planes and should be earned by later Objectives rather than inferred from this page contract.

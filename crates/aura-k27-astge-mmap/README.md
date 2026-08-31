# Aura K27 ASTGE — Immutable Generation mmap Adapter V1

Status: D0 / experimental / nonpromoting.

This crate is an additive mmap backend for the current `crates/aura-k27-astge` S-plane contract. It does **not** define a second graph format or semantic K27 scheme.

## Lifecycle

1. Receive an already-admitted `StorageGenerationBindingV1` plus exact PR465 node-index/page bytes.
2. Validate the full compact index and every page against the binding before publication.
3. Write a new generation directory, sync files, create a manifest with SHA-256 digests, make generation files read-only, and rename the completed directory into place.
4. Advance a small `CURRENT` pointer to the exact manifest digest.
5. A reader resolves `CURRENT`, verifies the manifest digest, exact file lengths and file digests, then maps the two files read-only.
6. The mmap reader decodes the **same** 64-byte node records and 4096-byte pages used by the safe PR465 reader and rechecks placement PBN/generation/scheme before traversal.
7. A later `CURRENT` update does not retarget an already-open mmap reader.

## Unsafe boundary

Only read-only `memmap2::MmapOptions::map` calls are unsafe. They are isolated in this adapter crate; the core storage crate remains `#![forbid(unsafe_code)]`.

The wrapper's admitted lifecycle forbids this crate from mutating or reusing a published generation. External processes can still violate the lifecycle by truncating or mutating mapped files; file-backed mmap safety under hostile external mutation is **not proved** here.

## Evidence contract

V1 must prove query equivalence against the existing generation-bound Read+Seek reader over the exact same bytes. It may report that an mmap backend exists; it may not claim lower latency, cold-NVMe behavior, physical-read reduction, token/TTFT benefit, or locality superiority.

PR459 is the independent matched-graph benchmark/oracle plane. Its current evidence shows warm mmap correctness but not performance superiority, and hash-prefix placement caused extreme page amplification on its tested graph. Physical layout selection therefore remains a later measured tournament.

## Durability ceiling

The publication path uses file/directory synchronization and rename mechanics, but no crash-injection campaign or filesystem-specific persistence proof has been completed. `CURRENT` publication is therefore not described as crash-atomic durable storage. W8 remains only partially represented by immutable-generation reconstruction.

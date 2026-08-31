# Aura K27 ASTGE ThinkPad warm I/O benchmark

This crate converts the useful part of the supplied Gemini ASTGE proposal into a host-measurement surface for Aura's current verified storage owners.

It **does not** implement another graph store or another K27 scheme. It compares the already-owned Read+Seek and immutable-generation mmap readers on the exact same verified snapshot, query roots, depth, node budget, and iteration count.

The runner deliberately labels cache state as `WARMISH_VERIFICATION_TOUCHED_UNCONTROLLED_OS_PAGE_CACHE`: PR471 verifies and hashes the snapshot before mapping, so this harness cannot truthfully claim a cold cache. Linux `/proc/self/stat` and `/proc/self/io` deltas are recorded as host/kernel counters only. `read_bytes` is not promoted to exact physical NVMe-device bytes.

Typical owner-host ThinkPad/WSL invocation uses separate processes:

```text
cargo run --release --manifest-path crates/aura-k27-astge-thinkpad-bench/Cargo.toml -- readseek <snapshot_root> <node-index.bin> <pages.bin> 0,256,512,768 128 256 25
cargo run --release --manifest-path crates/aura-k27-astge-thinkpad-bench/Cargo.toml -- mmap <snapshot_root> <node-index.bin> <pages.bin> 0,256,512,768 128 256 25
```

Compare only receipts whose snapshot digests, query-corpus digest, and semantic-result digest are identical. A timing ratio is descriptive host evidence; this crate never sets `performance_superiority_proven=true`.

# AWJ032 GLM-5.3 G6 — External K27 Coordinate Delta

Date: 2026-08-31  
Rank: D0 research/falsification routing only  
Namespace: `K27-B3MOD27-XYZ-v1`

Coordinates use successive four-byte SHA-256 limbs of the canonical source ID, interpreted big-endian and reduced mod 27. Full SHA-256 remains the collision discriminator. These coordinates are deterministic reopen/locality indices only.

| Canonical source ID | K27 XYZ | Full SHA-256 | Role |
| --- | --- | --- | --- |
| `hf:zai-org/GLM-5.3` | `(7,2,8)` | `d990c12c60a21a6c8e28dbd54936ee1ff6bf8963c039e098e2e3fe76dbde8c30` | official flagship model identity/currentness pressure |
| `arxiv:2607.24787` | `(16,9,15)` | `8bb9e2903488689ba884b80e269b78cf9b0897974d89a4bcfc7032960ba8af01` | SpecPrefetch: transfer prediction separated from native routing |
| `arxiv:2608.15383` | `(25,19,19)` | `65147b545b635d0f1f8da6b62cb017a47d8a5754b2e0bc86069009f7ff1ef905` | ExactMoE: complete expert availability, unchanged top-k, host-resident expert storage |
| `arxiv:2608.12103` | `(11,25,10)` | `05eb48869fa6e2c2f00f45400f699af7d4321b9462d7b636eacce467f0170ace` | expert-cache ownership and capacity/replay sensitivity |
| `github:tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark:docs/GB10-KV-MEMORY-LADDER.md` | `(4,19,14)` | `d12dd3e524091c7bde98b5146aa3ff23ecc12b087b8a7e287ccfa1c4b8f0236a` | DGX Spark KV/resource-envelope falsifier |
| `reddit:1w0wgad` | `(0,1,4)` | `f7c80321e8d34d757f5fc4a5233bde9eb4e08ce5c559ebec380108a524b7eb80` | community GLM-5.3 runtime/cache/offload falsifier; reused G5 coordinate |
| `scholar:direct-gap:glm53-g6:2026-08-31` | `(7,17,17)` | `346deef71fa71e0be1a6776b3e6ef17d4d788dea622d9852623c3cec9965e5a7` | explicit Google-Scholar-native discovery gap |

## Reopen / invalidation rules

- `hf:zai-org/GLM-5.3`: reopen if an immutable official revision newer than Q18's pinned `7cda81930d6e4cef42f48555de830aa32ecdde28` is resolved, or model architecture/source metadata changes.
- arXiv records: reopen on a material revision changing cache/transfer/routing conclusions relevant to the request envelope.
- DGX Spark record: reopen on a materially different hardware/runtime/KV configuration or a corrected failure envelope.
- Reddit record: advisory only; reopen on independently reproducible configuration/evidence, never on opinion alone.
- Scholar gap: retire only when a stable Scholar-native record is actually resolved.

## External findings retained as pressure, not Aura authority

1. The connected Hugging Face record reports the current `zai-org/GLM-5.3` repository at roughly 753.3B parameters and updated 2026-08-31. The connector did not expose an immutable current revision SHA, so G6 carries `OFFICIAL_SOURCE_REVISION_REVALIDATION` rather than laundering Q18's older pinned revision into "latest".
2. SpecPrefetch predicts experts only for asynchronous transfer while keeping the native top-k router authoritative; transfer optimization therefore cannot become routing authority.
3. ExactMoE keeps complete expert availability and unchanged top-k routing while using host memory plus GPU-resident slots, reinforcing separate source/model identity, storage placement, cache state, and execution evidence axes.
4. Current GLM-5.3-Flash DGX Spark work shows resource envelopes are discontinuous: a KV configuration can allocate on one rank and still fail another rank from memory pressure. Flash results are runtime falsifiers only and cannot substitute for flagship GLM-5.3 owner-host evidence.
5. Current LocalLLaMA reports show warm graph-cache and CPU-MoE choices materially change observed decode behavior; community evidence remains advisory.
6. Direct task-specific Google-Scholar-native discovery returned no stronger stable record for the exact Gate-10 owner-host request seam. Record `SCHOLAR_DIRECT_GAP`; do not fabricate provenance.

## Boundary laws

`K27Coordinate != SemanticIdentity != Currentness != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV state is read, written, inferred, allocated, or represented by this coordinate map.

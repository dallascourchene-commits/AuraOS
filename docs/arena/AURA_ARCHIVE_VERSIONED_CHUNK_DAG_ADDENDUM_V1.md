# Aura Archive Versioned Chunk DAG — Addendum V1

Status: D0 / experimental / nonpromoting.

## Why this addendum exists

`aura_structural_archive_probe.py` owns exact **single-artifact** compression. It tries
opaque and reversible structured representations and keeps the smallest exact
container. This addendum does not compete with that owner.

The missing relation is versioned corpus structure:

`ExactStructuralCodec + LosslessVersionHistory != CompactVersionedArchiveUntil
ContentDefinedChunking + ExactChunkIdentity + OrderedGenerationManifests +
OrthogonalNavigationIndexes + ExactRoundtrip Commute`.

PR #738 independently proved that one stable semantic K plus evolving evidence
generations cannot preserve history losslessly in the v1 unique-K row shape.
PR #735 independently supplies stable subject / evidence-generation separation,
L0-L4 hydration, and routing-only K27 placement. This addendum converts that
pressure into a storage representation without claiming writer authority.

## Two-plane law

```
AuraVersionedArchive = ExactSourcePlane ⊕ NavigationIndexPlane
```

### ExactSourcePlane

Only this plane can reconstruct bytes.

1. Each artifact generation is chunked with deterministic content-defined
   boundaries.
2. Every chunk identity is `SHA256(exact_chunk_bytes)`.
3. Identical exact chunks are stored once across all artifact generations.
4. Every unique chunk is encoded by the existing structural archive owner.
5. Each artifact manifest stores the original ordered chunk-digest sequence plus
   exact source length and SHA-256.
6. Decode must reproduce exact bytes and exact source SHA-256.

`ContentDeduplication != SemanticEquivalence`.

Two semantically equivalent JSON documents with different whitespace remain
different exact byte artifacts unless a future transform supplies a proved
reversible residual.

### NavigationIndexPlane

This plane may contain:
- L0-L3 hydration summaries;
- sector/domain;
- `EVENT_AT`;
- `RECORDED_AT`;
- scale;
- signed Connectome edges;
- 13D ternary projection;
- K27 `(x,y,z)` placement.

It cannot reconstruct source bytes and cannot mint identity, currentness,
causality, truth, authority, or effect permission.

`IndexPlane != ReconstructionAuthority`.

`EVENT_AT != RECORDED_AT`.

`TemporalAdjacency != CausalDependency`.

`K27Placement != ChunkIdentity != ArtifactIdentity`.

`13DProjection != SemanticTruth`.

## Why CDC

Fixed block boundaries shift after insertions. Content-defined boundaries let
unchanged regions tend to recover the same exact chunk identities, so nearby
versions can share storage without treating chronology or semantic similarity as
byte identity.

ARC V1 deliberately uses a simple deterministic Gear-style CDC as a reference,
not a claim that it is the best CDC algorithm.

## Metrics

Keep unlike savings terms separate.

```
R = sum(exact source bytes across artifact generations)
U = sum(raw bytes across unique exact chunks)
S = sum(encoded bytes for unique chunks)
A = total archive bytes including manifest and framing

ExactDedupSavings = 1 - U/R
BackendChunkSavings = 1 - S/U
FinalArchiveSavings = 1 - A/R
```

None of these imply runtime, latency, energy, or universal compression
superiority.

## Reversible semantic transforms

FST, RO3DD/grammar transforms, AST canonicalization and other semantic
representations may become future source-plane transforms only under:

`Decode(Encode(exact_bytes)) == exact_bytes`.

If canonical form loses formatting/order/original bytes, an exact residual is
required. Otherwise the transform belongs only in the NavigationIndexPlane.

## 8-crystalline / HyperScale disposition

- W0: exact structural codec and exact parent evidence baselines.
- W1: source bytes → CDC chunks → structural subarchives → exact reconstruction.
- W2: chunk/index/time/K27/13D/generation substitutions.
- W3: collision with the live structural archive owner caused this work to
  become an addendum rather than a competing codec.
- W4: source identity, version identity, hydration, time, scale, placement,
  currentness, write authority and effects remain separate leaves.
- W5: PR735 × PR738 synthesis.
- W6: identical exact chunks collapse once; semantically similar bytes do not.
- W7: version/time metadata remains explicit and noncausal.
- W8: mutation/effect authority remains unearned.

HS1 is sufficient.

## Claim ceiling

No claim that Aura universally beats ZIP/zstd/lzma/7z. No persistent
coordinate-memory mutation. No source currentness from archive presence. No
semantic K27 authority. No native/private transformer KV access. No model or
provider execution. No Gate-10, merge, deployment, spend, public, financial, or
human effect.

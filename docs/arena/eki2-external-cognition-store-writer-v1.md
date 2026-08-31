# EKI-2 External Cognition Store Writer V1

Status: D0 / HS1 / nonpromoting.

Objective: bridge provider-normalized EKI-1 discovery into the exact `aura-coordinate-memory-kv-v1@1.0.0` snapshot ABI consumed by the independently owned PR #728 reader without collapsing semantic source identity, record generation, physical placement generation, store generation, currentness, or authority.

## Laws

- `SourceGeneration != RecordGeneration != PlacementGeneration != StoreGeneration`.
- `PlacementDrift -> Relocalize`, not re-research, when semantic source/evidence state is unchanged.
- `PersistedCURRENT != CurrentnessWitness`.
- `ExplicitSupersessionEdge != InferredChronology`.
- `CoordinateMemory != TransformerKVCache != SemanticResponseCache`.
- `FoundVerifiedCandidate != InstructionAuthority != WriteAuthority != EffectAuthority`.
- K27/13D/toroidal projections are locality/reopen/scheduling aids only and never semantic identity or source truth.

## Independent owner boundary

The integration proof does not copy PR #728's reader implementation into this branch. Hosted CI fetches the reader from exact green head `9865c42f3ada2520141bd2fe30a439ce160ce2f8`, verifies Git blob `53de9d551c81a0eb495eb180294c0aba5eb359d0`, then executes the EKI-2 snapshot through that exact implementation.

## Provider policy

Direct cheap metadata adapters: arXiv, GitHub, Hugging Face model/dataset/Space. Google Scholar, Reddit, and generic web remain pointer-only in this adapter unless a separately authorized provider integration is supplied. Unknown rights/security facts remain UNKNOWN.

## Crystalline / HyperScale allocation

- W0: exact owner/source baseline.
- W1: writer→snapshot→reader roundtrip.
- W2 Antiprism: stale/unknown currentness, wrong responsibility, relocation/store-generation substitution, supersession.
- W3 Toroid: PowerShell parse repair→exact-host reproof→typed reopen.
- W4 Butterfly: source/record/placement/store/currentness/effect planes remain separately invalidatable.
- W5 Diamond: EKI writer × independent PR #728 reader composition.
- W6/W7/W8: unearned for this tightly coupled residual.
- HyperScale: HS1; no wider physical fanout earned.

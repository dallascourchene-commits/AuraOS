# Canonical ST3GG Contracts — P5.1

P5.1 introduces one domain-neutral contract for ST3GG decisions, savings measurements, pointers, and exact recall. It is additive: existing writers, parsers, public imports, Coding Arena behavior, and provider paths remain unchanged.

## Existing surfaces

Aura currently has four related ST3GG surfaces:

| Surface | Current responsibility | Existing identity |
|---|---|---|
| `aura_st3gg_codec.py` | Python AST/context summarization with profile-specific exact spans | `AURA_ST3GG_CODEC_V1` |
| `aura_st3gg_recall.py` | local exact-original records, aliases, JSON/hash sidecars, visible capsules | `AURA_ST3GG_RECALL_V1` |
| `aura_arena_st3gg_codec.py` | Coding Arena compact egress with recall persistence | `AURA_ARENA_ST3GG_CODEC_V1` |
| `aura_arena_st3gg_egress.py` | report-only symbol substitution and lossy expansion | `AURA_ARENA_ST3GG_EGRESS_V1` |

These surfaces remain supported. P5.1 does not redirect live callers.

## Problems addressed

Before P5.1, the surfaces independently defined:

- different decision dataclasses;
- token-estimate and byte-based savings calculations;
- `ST3GG-L2::...` and `ST3GG_PTR:...` pointer forms;
- exact recall in one path and lossy “decompression” in another;
- different points at which pointer overhead was counted.

The canonical layer makes these distinctions explicit instead of pretending they are interchangeable.

## Canonical contract

`aura_st3gg_contracts.py` adds:

- `ST3GGDecision`;
- `ST3GGSavingsPolicy`;
- `ST3GGMeasurementClass`;
- `ST3GGRestorationMode`;
- `ST3GGExactRecallRecord`;
- `ST3GGPreparedArtifact`;
- deterministic `ST3GG2::<NAMESPACE>:<digest>` pointers;
- deterministic `aura://st3gg/v2/<NAMESPACE>/<sha256>` exact references;
- visible-ASCII and tokenizer-channel sanitation;
- protocol-overhead-aware savings decisions;
- exact-record verification;
- compatibility projections for the three legacy decision shapes.

## Persistence order

The canonical preparation path is intentionally fail-closed:

```text
normalize namespace
→ digest exact original
→ derive deterministic pointer and exact reference
→ sanitize compact candidate
→ add complete protocol metadata
→ count final payload including pointer overhead
→ evaluate the savings policy
→ persist and verify the exact original
→ emit the compact handle
```

If the final handle does not meet the threshold, no exact record is written. If persistence fails, is unconfirmed, or returns a mismatched receipt, no handle is emitted.

## Restoration truth classes

- `EXACT_RECALL`: an exact original is digest-bound, persisted, and receipt-confirmed.
- `LOSSY_ADVISORY`: a compact view may be useful but cannot reconstruct exact bytes.
- `NONE`: no restoration claim is made.

The legacy AST and report adapters are deliberately `LOSSY_ADVISORY`. The legacy Arena adapter remains disabled in canonical V2 until its V1 recall record is explicitly migrated and verified.

## Authority boundary

Every canonical decision is permanently:

```yaml
proposal_only: true
patch_authority: exact_source_spans_and_hashes_only
st3gg_patch_authority: false
```

ST3GG pointers, compact text, fidelity scores, token estimates, and recall records never authorize patches, execution, governance, provider calls, commits, or merges.

## Deferred to P5.2+

P5.1 does not:

- modify current ST3GG writers;
- move existing recall stores;
- dual-write canonical V2 records;
- migrate live Arena, Builder, or emergent-report callers;
- change public CLIs;
- change QDKT;
- delete V1 formats.

A later migration slice can dual-project V1 output into V2 decisions, prove golden compatibility, and only then move one caller at a time.

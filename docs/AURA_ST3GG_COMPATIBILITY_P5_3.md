# Aura ST3GG Cross-Surface Compatibility — P5.3

## Scope

P5.3 completes the remaining additive ST3GG compatibility migrations without redirecting live callers or changing any V1 writer, parser, packet, import, CLI, provider/router path, recall record, or authority boundary.

The opt-in public facade is `aura_st3gg_compatibility.py`; immutable evidence contracts and recall verification are isolated in `aura_st3gg_compatibility_types.py` and `aura_st3gg_compatibility_recall.py`.

```python
from aura_st3gg_compatibility import (
    compress_report_with_v2_facade,
    dual_read_st3gg_recall,
    encode_source_with_v2_facade,
    p5_3_legacy_disposition,
)
```

## Surface truth classes

| Legacy surface | Unchanged V1 owner | Canonical V2 classification |
|---|---|---|
| `aura_st3gg_codec.py` | `AURA_ST3GG_CODEC_V1` | `LOSSY_ADVISORY` when the verified encoded view is smaller; otherwise `NONE` |
| `aura_st3gg_recall.py` | `AURA_ST3GG_RECALL_V1` | `EXACT_RECALL` only after pointer, digest, dash-key, JSON-index, exact-original, content-type, and length agreement |
| `aura_arena_st3gg_egress.py` | `AURA_ARENA_ST3GG_EGRESS_V1` | `LOSSY_ADVISORY` by default; optional `EXACT_RECALL` only after canonical overhead passes and the exact original is persisted and dual-read through V1 recall |

Exact source spans carried by AST PATCH/TEST/VERIFIER frames remain authoritative sidecars. They do not make the compact AST representation reversible and do not grant ST3GG patch authority.

## Fail-closed ordering

Every public facade runs the unchanged V1 operation first. Projection defects cannot alter or suppress its returned value.

### AST/context facade

1. Emit the unchanged `ST3GGFrame`.
2. Recompute source digest, raw units, candidate units, ratio, counts, warnings, and exact spans.
3. Replay the deterministic V1 encoder and require complete frame equality.
4. Classify the encoded view as `LOSSY_ADVISORY` or `NONE`.
5. On any projection error, return the exact V1 frame with a disabled V2 decision.

### Report egress facade

1. Emit the unchanged `(compressed, savings, ST3GG_PTR)` tuple.
2. Recompute byte measurements and verify pointer and visible-ASCII identity.
3. Preserve `LOSSY_ADVISORY` unless exact persistence is explicitly requested.
4. Count the complete canonical V2 metadata suffix before writing recall.
5. Persist through the existing V1 recall owner only when the final V2 artifact still passes policy.
6. Verify the stored exact original independently through the JSON compatibility index and public pointer, digest, and dash-key reads.
7. Emit a canonical V2 exact handle only after all reads agree.
8. On any error, preserve the V1 tuple and downgrade to `LOSSY_ADVISORY` or `NONE`.

## Dual-read invariants

`dual_read_st3gg_recall` rejects:

- stale, missing, malformed, or substituted pointer records;
- digest or dash-key alias disagreement;
- a hash-sidecar success that conflicts with the JSON compatibility index;
- duplicate or conflicting records for the same pointer, digest, or dash key;
- non-canonical record version, pointer, dash key, glyph, holographic header, timestamp, content type, or source hint;
- pointer/header values not derived from the exact original and namespace;
- exact-original digest or byte-length disagreement;
- compact payload disagreement;
- canonical V2 pointer, exact-reference, namespace, or storage-owner disagreement.

A verified record binds:

```text
V1 pointer + V1 digest alias + V1 dash alias + direct JSON record
    == one exact V1 record
    == canonical V2 original digest + exact reference + pointer
```

V1 remains the storage owner. P5.3 does not write a second native V2 store or backfill existing records.

## Authority boundary

All compatibility records remain:

```yaml
execution_mode: OPT_IN_COMPATIBILITY
proposal_only: true
storage_owner: AURA_ST3GG_RECALL_V1
patch_authority: exact_source_spans_and_hashes_only
st3gg_patch_authority: false
```

Compact AST text, report substitutions, pointers, savings, fidelity scores, aliases, and recall bindings cannot authorize code changes, execution, provider calls, governance, commits, or merges.

## Legacy disposition

P5.3 records the machine-readable decision returned by `p5_3_legacy_disposition()`:

```text
RETAIN_V1
```

Deprecation does not begin in this pull request. The evidence proves additive compatibility and exact binding where eligible, but not native V2 storage ownership, existing-record backfill, live-caller redirection, or removal safety. Any deprecation must be opened as a separate reviewable boundary after those blockers are resolved.

## Verification

The focused Python 3.10/3.12 gate includes:

- syntax compilation and fatal/static Ruff checks;
- golden direct-versus-facade V1 equality for AST and report output;
- recomputed AST token measurements and report byte measurements;
- deterministic AST replay and metadata-forgery rejection;
- exact-span sidecar validation without false exact-recall claims;
- optional report exact persistence and pointer/digest/dash/JSON dual reads;
- pointer substitution, alias disagreement, duplicate/conflicting record, malformed metadata, digest/length disagreement, invalid Unicode, empty candidate, persistence failure, and overhead-erased-savings tests;
- deterministic evidence and disposition digests;
- the existing P5.1 contracts, P5.2 Arena shadow, V1 AST codec, and V1 Arena codec tests.

Issue: #114. Epic: #93.

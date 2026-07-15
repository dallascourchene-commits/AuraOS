# Aura QDKT Compatibility Inventory and Dual-Read Evidence — P6.2

## Decision

P6.2 retains `quantum_dag.QuantumMerkleDAG` as the owner of the current legacy `{root, belief}` result and retains `AppendOnlyEventStore` as the owner of canonical observation evidence.

The machine-readable ownership recommendation is:

```text
RETAIN_LEGACY_DUAL_READ
```

It is proposal-only. It does not authorize caller redirection, legacy deletion, storage transfer, historical backfill, patching, routing, execution, verification, or merge.

## Why this boundary exists

`QuantumMerkleDAG.generate_epistemic_system_root()` remains nondeterministic because its result can depend on the working-directory Python snapshot, a random thought identifier, thermal input, and optional HDC state. Re-running it to compare equality would produce a second observation rather than verify the first.

P6.2 therefore accepts an **already-produced** legacy result and compares it with P6.1 event and sidecar evidence. The dual-read path never receives or invokes a generator.

## Deterministic compatibility inventory

`aura_qdkt_inventory.py` parses Python files with `ast` and scans supported documentation/configuration text without importing or executing repository code. It records:

- imports of `quantum_dag` or `QuantumMerkleDAG`;
- constructor calls;
- `generate_epistemic_system_root()` calls;
- root and belief consumers;
- persistence and display uses;
- test surfaces;
- archived `.save`/backup surfaces;
- documentation references;
- the legacy generator definition.

Every entry contains a stable ID, repository-relative file path, enclosing symbol, line, use class, impact, readiness, and detail. Entries are sorted deterministically and the complete report has a stable digest.

Generate the current inventory with:

```bash
python aura_qdkt_inventory.py --root . --output qdkt-p6-2-inventory.json
```

The P6.2 workflow runs this command on Python 3.10 and 3.12 and uploads the exact canonical JSON as a build artifact.

### Readiness classes

| Readiness | Meaning |
|---|---|
| `DUAL_READ_CANDIDATE` | Active use that may be wrapped by a later opt-in caller migration |
| `TEST_ONLY` | Test or validation surface; no production ownership transfer |
| `ARCHIVAL_ONLY` | Saved/backup file; inventory evidence only |
| `DOCUMENTATION_ONLY` | Textual reference; no executable migration |
| `NO_MIGRATION_REQUIRED` | The legacy definition remains the current result owner |

### Current repository disposition

The direct executable result surface remains `quantum_dag.py`. Current direct construction/call coverage is present in `test_aura_functions.py`; historical construction/call surfaces remain in `aura_node.py.save` and `aura_node.py.save.1`. P6.1 supplies the opt-in observation/event facade and focused tests. Documentation, verification metadata, and configuration references are classified separately rather than treated as live consumers.

The inventory is intentionally generated from the checked-out commit rather than maintained as a hand-edited list, preventing drift as files move or new callers appear.

## Dual-read statuses

`compare_qdkt_dual_read()` returns immutable `QDKTDualReadEvidence` containing the unchanged legacy root and belief plus independent canonical evidence.

| Status | Meaning |
|---|---|
| `VERIFIED` | Exactly one clean canonical observation agrees on root, belief, source snapshot digest/count, event identity, sidecar reference/digest, proposal-only metadata, truth class, and optional freshness |
| `ADVISORY_ONLY` | Root and belief agree, but the caller did not supply source-snapshot identity |
| `UNAVAILABLE` | No canonical QDKT event is available |
| `MISMATCHED` | Evidence is missing, duplicate, stale, malformed, substituted, noncanonical, conflicting, or disagrees with the supplied result/snapshot |

The legacy result remains available in every status and is never rewritten from canonical evidence.

## Conflict and history semantics

Multiple historical QDKT observations are allowed. An unrelated observation from a different source snapshot does not invalidate a clean match.

A conflict is narrower: evidence bound to the **same source snapshot digest and count** claims a different root or belief. Multiple exact matches for the same result and snapshot are also rejected because P6.2 cannot select one without a separate ownership policy.

## Integrity checks inherited from P6.1

The comparator relies on the read-only P6.1 projector and sidecar readers for:

- strict finite JSON and duplicate-key rejection;
- canonical JSONL bytes and terminal newline;
- canonical event IDs and envelopes;
- proposal-only and exact authority metadata;
- duplicate/conflicting event IDs;
- parent existence and ordering;
- safe sidecar references;
- sidecar existence, canonical bytes, digest, and reference identity;
- observation identity and event-node agreement.

Any blocking projector finding yields `MISMATCHED`. P6.2 never repairs the store.

## Freshness

Freshness is opt-in. When `max_age_seconds` is supplied, the caller must also supply an explicit `now` value. Evidence dated in the future or older than the permitted window is `MISMATCHED`.

P6.2 does not invent a universal expiry because appropriate freshness depends on the caller and objective.

## Compatibility and authority guarantees

P6.2 does not edit `quantum_dag.py`, `aura_qdkt.py`, the P6.1 observation/event schema, or any current caller. It adds no mutable store and performs no backfill.

All P6.2 records preserve:

```text
proposal_only = true
patch_authority = exact_source_spans_and_hashes_only
vsa_patch_authority = false
qdkt_patch_authority = false
generator_replayed = false
```

## Next evidence gate

A later P6 slice may propose an opt-in wrapper at a specific live caller only after the generated inventory identifies that caller, dual-read evidence is clean, and regression evidence demonstrates unchanged behavior. P6.2 itself makes no such redirection.

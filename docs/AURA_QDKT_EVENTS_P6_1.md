# Aura QDKT Observation Events — P6.1

## Decision

The legacy `QuantumMerkleDAG` is **integrated, not discarded**, but its output is not promoted to deterministic source truth.

`generate_epistemic_system_root()` currently derives its result from a working-directory file snapshot, random thought identifiers, thermal input, and optional HDC state. The exact returned `{root, belief}` pair is therefore useful as an observed cognitive snapshot while remaining nondeterministic advisory evidence.

## Compatibility boundary

P6.1 does not edit `quantum_dag.py` or redirect any caller. Its public class, method name, asynchronous behavior, and result shape remain unchanged.

The additive facade:

1. invokes a supplied legacy generator exactly once;
2. preserves the exact returned `root` and `belief`;
3. binds them to a sanitized source-snapshot digest and source count;
4. declares the complete nondeterministic input classes;
5. stores the immutable observation as an exact sidecar;
6. appends a compact proposal-only `AuraEventEnvelope`;
7. independently revalidates the event log and sidecar through a read-only projector.

## Truth and authority

- Truth class: `LEGACY_NONDETERMINISTIC_ADVISORY`
- Reproducible claim: `false`
- Proposal only: `true`
- Patch authority: `exact_source_spans_and_hashes_only`
- QDKT patch authority: `false`
- VSA patch authority: `false`
- Policy, governance, routing, execution, merge, and verifier authority: none

The observation can reference Planning Board, planning-history, or J2 continuity artifacts, but those references do not become ownership or authority transfers.

## Storage and projection

`AppendOnlyEventStore` remains the canonical event and sidecar owner. P6.1 adds no new mutable database and performs no historical backfill.

The read-only projector verifies:

- strict finite JSON with duplicate-key rejection;
- canonical JSONL event bytes;
- canonical envelope and event identity;
- proposal-only and exact authority metadata;
- duplicate and conflicting event IDs;
- safe canonical sidecar references;
- sidecar existence, canonical bytes, digest, and reference identity;
- canonical `QDKTObservation` identity;
- parent existence and event-log/timestamp ordering;
- separation between a Planning Board reference and the envelope's domain `board_id`.

It never writes, repairs, executes, authorizes, or reorders anything.

## Failure behavior

Malformed roots, boolean beliefs, incomplete nondeterminism declarations, protected/private-reasoning fields, non-finite event or sidecar values, substituted sidecars, invalid references, duplicate records, missing parents, and authority escalation fail closed as blocking projection findings or constructor errors.

The unchanged legacy QDKT result is never rewritten by the compatibility layer.

## Deprecation status

No legacy deprecation begins in P6.1. The next P6 boundary may evaluate live caller inventory and dual-read ownership, but deletion or redirection requires a separate evidence-backed decision.

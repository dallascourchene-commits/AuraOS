# Aura Dual Persistence Fabric

**Status:** staged / nonpromoting / AWJ-018 candidate

Aura's storage target is **two durable physical realizations of each admitted material artifact with one semantic identity and one authority record**.

```text
semantic artifact SID + generation + source owner
                 |
        +--------+--------+
        |                 |
 local realization   cloud realization
        |                 |
        +--------+--------+
                 |
          reconciliation
```

This is not ordinary blind two-way file synchronization.

## Invariants

- `TWO REPLICAS != TWO TRUTH OWNERS`.
- A worker may act only from a current, synchronized generation or from an explicitly scoped source owner allowed by the WorkCapsule.
- One-sided change can propagate after common-base verification.
- Two-sided divergence preserves both sides and opens a review/affected-cone workflow; neither side silently overwrites the other.
- Missing local/cloud replicas are materialization gaps, not new semantic objects.
- Native Google Docs/Sheets/Slides use provider file/revision + canonical export digest; fake byte identity is forbidden.
- Local Aura Drive 2 is the laptop runtime/cache/materialization surface. Cloud Aura Drive 2 is the cross-agent/federation persistence surface. Their roles are distinct even when their admitted artifact content is equivalent.

## Replica record

Every admitted artifact should eventually resolve to:

```text
ArtifactReplicaRecordV1 {
  semantic_sid
  source_owner
  source_generation
  base_digest

  local_path
  local_digest
  local_materialization_generation

  cloud_file_id
  cloud_revision
  cloud_digest_or_canonical_export_digest
  cloud_materialization_generation

  sync_state
  last_reconciled_at
  conflict_ref?
  invalidators[]
}
```

## Sync state

```text
SYNCED
LOCAL_ONLY
CLOUD_ONLY
LOCAL_AHEAD
CLOUD_AHEAD
CONFLICT
STALE_GENERATION
INVALID
```

Only `SYNCED` is universally dispatchable to ordinary Arena workers.

## Event loop

Preferred path:

```text
local/cloud/runtime event
 -> identify semantic SID
 -> validate source generation
 -> hash/canonical-export digest
 -> classify replica state
 -> propagate one-sided lawful delta OR fail closed
 -> verify final digests/currentness
 -> update Sub-Arena + Temporal NOW
 -> emit SyncReceipt
 -> wake affected work only
```

Whole-Drive scans are migration/recovery tools, not the steady-state algorithm.

## K27 and residency

K27 remains a physical/cache partition hint below semantic scope. The complete durable local/cloud replica ledger should not be confused with RAM/hot-cache residency.

Aura may keep:

- HOT shard payloads materialized/indexed;
- WARM shard summaries/metadata;
- COLD shard pointers/digests;
- exact L4 reopen handles.

This changes retrieval cost without changing durable identity or replication guarantees.

## Swarms

Every WorkCapsule should bind a compact currentness token such as:

`<SID>:g<generation>:<digest>`

If the source generation or replica agreement changes after dispatch, the worker's consequence path fails `STALE -> REBASE`.

## Gate-10 acceptance

Do not call the dual-persistence fabric complete until receipts prove:

1. cloud-created canary appears locally;
2. local-created canary appears in the correct cloud root;
3. file/canonical-export digest parity;
4. one-sided updates reconcile correctly both directions;
5. simultaneous divergence produces `CONFLICT` without data loss;
6. stale WorkCapsule cannot act;
7. restart resumes from persisted cursor without duplicate effects;
8. a swarm worker and local resident resolve the same semantic generation;
9. LFM2.5 completes one bounded maintenance job against synchronized state;
10. accepted output is persisted to both realizations and reopened by a fresh worker.

The current `core/aura_dual_persistence.py` is the deterministic reconciliation kernel only. Provider watchers, local filesystem adapters, Google Drive adapters, cursor persistence, and end-to-end host receipts remain separate implementation/acceptance work.

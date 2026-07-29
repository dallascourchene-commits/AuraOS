# Canonical Architecture Addendum — Bilateral Live Repair B11–B15

**Base:** `f1b9d786c4ff30d1ff5b984f5859db80f33446cc`  
**Scope:** final bilateral incident replay, bounded repair, isolated preview/rollback, U7 delegation, and Spatial Foundry projection.

## Ownership statement

The public `aura_bilateral_live_repair_foundry.py` entrypoint and its bounded
`_contracts`, `_capture`, and `_service` companions form one orchestration adapter only.

```yaml
memory_owner: false
truth_owner: false
intent_owner: false
policy_owner: false
routing_owner: false
verification_owner: false
attempt_archive_owner: false
runtime_harness_owner: false
crucible_owner: false
current_reproof_owner: false
rollback_authority: false
construction_truth_owner: false
learning_owner: false
publication_authority: false
production_mutation: false
human_confirmation_required: true
```

## Canonical flow

```text
confirmed bilateral contract from B0–B10
→ explicit bounded incident capture
→ canonical Attempt Archive replay retention
→ Runtime Profile V2 reproduction/proof
→ persistent no-repeat repair attempts
→ Surgeon-local or Council-structural routing
→ isolated preview and exact local rollback receipt
→ canonical U7 P0/P1/current-reproof/disposition path
→ projection-only Spatial Foundry
→ separate human review/promotion decision
```

## Critical invariants

1. The incident marker is not stored only in an evictable rolling buffer.
2. Set normalization is deterministic before sanitization and hashing.
3. Full sanitized replay packets, runtime results, attempts, and preview receipts are retained by `ArenaAttemptArchive`.
4. Runtime execution delegates to Runtime Profile V2 with `allow_dirty=False`.
5. Repair consumes only a digest reference to Runtime Profile V2 proof retained in the Attempt Archive; caller-supplied proof packets and regression booleans have no readiness effect.
6. Missing negative, preservation, fault, adjacent-regression, repository-cleanliness, or independent-verifier evidence blocks readiness.
7. Failed hypotheses cannot repeat across process restarts.
8. Repair attempts are bounded to eight.
9. Local failures route to Surgeon; structural failures route to Council V3.
10. Preview is admitted only in local ephemeral or isolated canary environments.
11. Rollback restoration must equal the exact last verified digest.
12. U7 is delegated to `aura_unified_memory_continuity_learning`; no second reproof or learning lifecycle exists.
13. Foundry visual state is projection only and cannot become Construction or repository truth.

## Plan revision

No standalone canonical production hot-swap owner exists on the B10 head. B13 therefore uses a bounded evidence-only local/canary preview adapter with optional pre-authorized technical rollback. It does not claim production deployment or rollback authority. This changes the implementation path, not the confirmed objective or prohibitions.

## Public entrypoint

`aura_showcase_live_repair_server.py` composes `aura_showcase_server`; it does not replace it. Existing routes and static assets are delegated to the established owner.

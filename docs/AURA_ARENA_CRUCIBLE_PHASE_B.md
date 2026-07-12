# Aura Arena Crucible — Phase B Proposal Pipeline

Status: `DRAFT_REVIEW_REQUIRED`

Phase B introduces the first background-capable Arena Crucible. It mines complete,
sanitized `ArenaExperienceV1` records and may emit a reviewable candidate packet. It
cannot modify active grammar manifests, runtime weights, source code, capability
bindings, leases, or production state.

This implementation is separate from the older `aura_crystallization.py` VSA topology
experiment. The Arena Crucible is an empirical workflow-learning pipeline with a
strict proposal boundary.

## Pipeline

```text
ArenaExperience ledger
  → schema and current-grammar filtering
  → transition-local grouping
  → temporal training/holdout split
  → deterministic candidate calculation
  → holdout validation
  → historical shadow replay
  → CRYSTALLIZATION_PROPOSED store
  → verifier and human review
```

The active grammar is never written during this flow.

## Phase B learning scope

Phase B supports exactly one proposal path:

```text
soft_weight_profile.empirical_uncertainty
```

It can lower or raise the empirical uncertainty assigned to an existing transition
when sufficient diverse experience and validation evidence exists.

Phase B does **not** propose or modify:

- hard guards;
- states or transitions;
- aliases or accepted symbols;
- output symbols;
- requested capabilities;
- verifier requirements;
- approval requirements;
- risk classifications;
- source code;
- active grammar files.

Hard guards continue to remove inadmissible transitions before any soft ranking. The
Crucible therefore cannot make a forbidden transition admissible.

## Candidate admission

Records are grouped by:

```text
arena_id + grammar_version + state_before + selected_transition
```

A record is ignored when its grammar or transition no longer exists. Meta transitions
are excluded. Candidate generation requires configurable minimum support, success,
and objective diversity.

Records are sorted by completion time and divided into disjoint temporal sets. The
newest records form the holdout set. The candidate identity includes the active
manifest digest and a digest of its source experience IDs.

The default policy requires:

```yaml
min_train_records: 8
min_holdout_records: 3
holdout_fraction: 0.25
min_distinct_objectives: 2
min_train_success_rate: 0.70
min_holdout_success_rate: 0.67
min_holdout_wilson_lower: 0.30
min_shadow_records: 1
max_shadow_selection_change_rate: 0.35
minimum_uncertainty_delta: 0.05
max_proposals_per_run: 8
```

These thresholds are prototype defaults, not validated universal constants.

## Validation

A candidate must pass every check:

1. Training and holdout experience IDs are disjoint.
2. The holdout contains enough records.
3. Holdout success meets the declared threshold.
4. The Wilson lower confidence bound meets its threshold.
5. Stored rank projections provide enough historical shadow records.
6. The proposed uncertainty produces no selection change toward greater unresolved
   risk or a larger declared evidence gap.
7. The total historical selection-change rate remains within policy.
8. The candidate targets the single allowed Phase B change path.
9. The proposal is pinned to a repository-local manifest path (relative, no path
   traversal) whose BLAKE2b digest matches the declared digest.

Historical shadow replay operates only over transitions that were already admitted in
the recorded route projection. It does not replay, reinterpret, or bypass hard guards.

## Proposal boundary

Passing output is stored in SQLite WAL at:

```text
Aura_Memory/arena_crucible.db
```

The database enforces this terminal status:

```text
CRYSTALLIZATION_PROPOSED
```

Every proposal requires the next gate:

```text
VERIFIER_AND_HUMAN_REVIEW
```

Typed contracts and the storage layer independently reject packets carrying mutation,
promotion, commit, push, or merge authority. Repeated identical candidates reuse the
existing deterministic proposal rather than generating duplicates.

There is deliberately no apply or promote operation in the service or CLI.

## Pause and resume

Pause state is persistent across processes:

```bash
python -m aura_crucible_cli pause --reason "manual review"
python -m aura_crucible_cli status
python -m aura_crucible_cli resume
```

A paused Crucible fails closed and performs no mining cycle.

## Operation

Run one bounded cycle:

```bash
python -m aura_crucible_cli run-once --arena-id human_agent
```

Run cooperative foreground cycles:

```bash
python -m aura_crucible_cli service \
  --arena-id human_agent \
  --interval 60 \
  --max-cycles 10
```

Inspect proposals:

```bash
python -m aura_crucible_cli proposals --arena-id human_agent
python -m aura_crucible_cli proposal CPROP-...
```

The CLI contains only:

```text
status | pause | resume | run-once | service | proposals | proposal
```

## Authority

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
learned_weight_patch_authority: false
crystallization_patch_authority: false
automatic_grammar_promotion: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

## Deferred work

A later, separately reviewed phase may define a signed proposal-review and controlled
promotion protocol. That protocol is intentionally absent here. Phase B ends when a
validated proposal is available for verifier and human review.

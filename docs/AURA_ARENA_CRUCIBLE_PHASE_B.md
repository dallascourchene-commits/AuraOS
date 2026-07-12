# Aura Arena Crucible — Phase B V2 Proposal Pipeline

Status: `DRAFT_REVIEW_REQUIRED`

Phase B V2 is a proposal-only empirical workflow-learning pipeline. It reads complete,
sanitized `ArenaExperienceV2` records, mines existing-transition uncertainty
candidates, validates them on independent data, replays a separate shadow set, and
stores reviewable packets. It cannot change active grammars, runtime weights, source
code, capability bindings, leases, or production state.

This remains separate from the older `aura_crystallization.py` VSA topology experiment.

## Completed pipeline

```text
Guarded Arena execution
  → ArenaExperienceV2
      grammar_manifest_digest
      OutcomeVector
      every admissible alternative
      every prediction
  → exact current-grammar filtering
  → transition-local grouping
  → temporal TRAIN / VALIDATION / SHADOW split
  → deterministic uncertainty candidate
  → independent OutcomeVector validation
  → independent full-choice shadow replay
  → CRYSTALLIZATION_PROPOSED
  → verifier and human review
```

The active grammar is never written during this flow.

## Learning surface

Phase B supports exactly one proposed field on an existing transition:

```text
soft_weight_profile.empirical_uncertainty
```

It does not propose or modify hard guards, states, transitions, aliases, accepted or
output symbols, capabilities, verifier requirements, approval requirements, risks,
source code, or active grammar manifests. Hard guards remain outside all learned
weights and continue to remove inadmissible transitions before ranking.

## Canonical repository-relative manifest pin

Every candidate is pinned to:

```text
arena_id
grammar_version
repository-relative manifest_path
canonical compiler manifest_digest
```

The manifest validator resolves the path beneath the supplied repository root,
rejects absolute paths and traversal, recompiles the manifest with
`aura_arena_wfst_compiler`, and compares the compiler’s canonical manifest digest.
It also confirms Arena and grammar-version identity.

Raw file-byte hashes are not accepted as grammar manifest digests.

## Eligible experience records

The miner accepts only records that contain:

- an existing Arena and grammar version;
- the exact current compiled `grammar_manifest_digest`;
- an existing state-local selected transition;
- a valid `OutcomeVector`;
- a non-Meta selected transition;
- complete V2 observation fields.

V1 rows remain readable after migration but are marked `legacy_record: true` and are
excluded rather than filled with invented data.

Records are grouped by:

```text
arena_id + grammar_version + grammar_manifest_digest
+ state_before + selected_transition
```

## OutcomeVector rather than binary success

`final_outcome` remains an audit label. The miner does not classify terminal strings
as success or failure. Candidate statistics come from the continuous, nullable
OutcomeVector proposal projection.

The proposal report includes mean score, conservative floor, coverage, dimension
means, observation counts, and terminal-class counts. It explicitly reports:

```text
binary_outcome_used: false
```

## Three independent datasets

Records are sorted by completion time and divided into:

```text
oldest                         newest
TRAIN → VALIDATION → SHADOW
```

- TRAIN computes the candidate value.
- VALIDATION independently measures OutcomeVector evidence.
- SHADOW independently replays recorded routing predictions.

Experience IDs and digests are stored separately for all three sets. Any overlap is a
structural validation failure.

## Complete shadow observations

The guarded runtime evaluates every outgoing state-local transition through hard
guards and capability binding, even when the command has an exact match. Exact
selection still occurs only among admitted exact matches.

Each shadow record therefore preserves every admitted alternative and corresponding
prediction. Replay stores both baseline and proposed ordering, selected transition,
rank vectors, OutcomeVector, and grammar digest. Missing alternatives or predictions
fail structural validation.

Shadow replay never reinterprets blocked transitions and never bypasses hard guards.
It substitutes only the candidate uncertainty inside transitions already admitted in
the recorded observation.

## Structural validation versus proposal thresholds

Structural checks determine whether a packet may be stored as a truthful proposal:

1. TRAIN, VALIDATION, and SHADOW are disjoint.
2. Every referenced record exists and its dataset digest matches.
3. Every record matches the candidate’s Arena, grammar, manifest, state, and transition.
4. Every shadow record preserves all admitted alternatives and predictions.
5. The proposed change path is the single allowed path.
6. The repository-relative manifest pin recompiles and matches canonically.

Thresholds are separate annotations. Every threshold field is named `proposal_*` and
all reports carry:

```text
threshold_scope: PROPOSAL_ONLY
thresholds_have_runtime_authority: false
```

Defaults include proposal-only support, objective-diversity, OutcomeVector coverage
and score, uncertainty-delta, and shadow-change thresholds. Missing a threshold does
not alter runtime behavior and does not turn the threshold into a hard guard. A
structurally valid packet may be stored with:

```text
REVIEW_WITH_THRESHOLD_WARNINGS
```

instead of being silently discarded.

## Persistence and operation

Runtime-local SQLite WAL stores:

```text
Aura_Memory/arena_experience.db
Aura_Memory/arena_crucible.db
```

Pause state persists across processes. A paused service mines nothing.

```bash
python -m aura_crucible_cli pause --reason "manual review"
python -m aura_crucible_cli status
python -m aura_crucible_cli resume
python -m aura_crucible_cli run-once --arena-id human_agent
python -m aura_crucible_cli proposals --arena-id human_agent
```

The CLI contains only:

```text
status | pause | resume | run-once | service | proposals | proposal
```

There is no apply, promote, commit, push, or merge operation.

## CODEMAP and CI

`aura_codemap_verify.py` fails closed unless the generated artifacts report positive
node and edge counts, `compiled_deep_topology`, a nonempty topology file index, the
Phase B files and symbols, Markdown/JSON parity, and no severe regression from the
known-good topology baseline.

GitHub Actions now runs:

- focused contracts on Python 3.10 and 3.12;
- fatal static checks and module compilation;
- the full repository pytest suite;
- deterministic CODEMAP regeneration, topology verification, and generated-artifact
  cleanliness.

## Terminal proposal boundary

Stored output must terminate at:

```text
CRYSTALLIZATION_PROPOSED
```

with the next gate:

```text
VERIFIER_AND_HUMAN_REVIEW
```

Typed contracts and SQLite reconstruction independently reject forged authority.
Repeated identical candidates reuse one deterministic proposal.

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

A signed proposal-review and controlled promotion protocol remains intentionally
absent. It requires a later, separately reviewed phase. Phase B ends with a complete,
structurally verified, human-reviewable proposal.

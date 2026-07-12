# Aura Arena Experience Schema — V2

`ArenaExperienceV2` is the authoritative observable trace format recorded by guarded
Arena workflows and consumed by the proposal-only Phase B Crucible.

It stores what Aura observed, admitted, predicted, selected, executed, and verified.
It does not request or retain hidden chain-of-thought.

## Storage and migration

The SQLite WAL ledger remains runtime-local:

```text
Aura_Memory/arena_experience.db
```

Opening a V1 database performs an additive migration. Historical rows are not given
invented grammar digests, alternatives, predictions, or OutcomeVectors. They remain
readable with:

```text
legacy_record: true
```

The Crucible ignores those incomplete historical rows. New records must satisfy the
full V2 contract.

## Mandatory grammar identity

Every new experience includes:

```text
grammar_version
grammar_manifest_digest
```

`grammar_manifest_digest` is the canonical digest produced by
`aura_arena_wfst_compiler`, not a raw file-byte hash. The Crucible accepts a record
only when its digest exactly matches the currently compiled grammar for that Arena
and grammar version.

This prevents experience produced under one manifest from silently training a
similarly named but structurally different manifest.

## OutcomeVector

A binary success/failure label is insufficient for routing learning. V2 therefore
stores a nullable, observable `OutcomeVector` with dimensions including:

- task progress;
- evidence quality;
- verification quality;
- safety quality;
- human alignment;
- cost efficiency;
- latency efficiency;
- abstention quality;
- recovery quality.

Each dimension is either `null` or a bounded value in `[0, 1]`. Measurement classes
remain attached where available. The terminal string in `final_outcome` is retained
for audit compatibility, but the Phase B miner never converts it into a binary target.

A proposal-only projection may combine observed OutcomeVector dimensions for candidate
analysis. Projection weights and thresholds have no routing, guard, patch, or promotion
authority.

## Complete route observation

Each experience preserves:

```text
selected_transition
admissible_alternatives[]
predictions[]
route_observation_digest
```

`admissible_alternatives` contains every state-local transition that passed hard
guards and capability binding, including rank vectors and evidence declarations.
`predictions` preserves the corresponding ordered selection forecast, next-state
forecast, semantic fit, rank, measurement classes, and selected flag.

Exact text matching still controls which exact transition may be selected. It no
longer removes other admitted transitions from the observable projection. Therefore
an exact blocked command cannot fall through, while the ledger still receives the
complete admitted choice set.

## Other stored classes

A V2 record also includes:

- Arena, runtime, and compiler versions;
- task, workflow, and correlation IDs;
- state before and after;
- repository commit and working-tree digest;
- objective and source-hash collection digests;
- provider/model metadata when applicable;
- cost-run, trace-atom, and raw-evidence references;
- sanitized route, guard, capability, tool, verifier, and result payloads.

It references rather than replaces the Empirical Cost Observatory, symbolic trace
memory, ST3GG recall ledgers, source hashes, verifier records, and ephemeral lifecycle
receipts.

## Privacy and sanitization

The sanitizer removes or redacts API keys, bearer tokens, passwords, secrets,
authorization headers, private-key material, cookies, hidden chain-of-thought,
scratchpads, and private-reasoning fields from payloads, alternatives, and predictions.
Aura stores observable short rationales, decisions, evidence, and outcomes only.

## Idempotency

Repeating an `experience_id` with the same canonical content digest is accepted as an
idempotent replay. Reusing the same ID for different content fails closed with:

```text
experience_id_digest_conflict
```

## Phase B dataset boundary

Eligible records are divided temporally into three disjoint sets:

```text
TRAIN → VALIDATION → SHADOW
```

- TRAIN creates the candidate.
- VALIDATION independently evaluates OutcomeVector evidence.
- SHADOW independently replays every recorded admitted alternative and prediction.

No experience ID may occur in more than one set.

## Proposal-only authority

Phase B may propose only:

```text
soft_weight_profile.empirical_uncertainty
```

Every output terminates at `CRYSTALLIZATION_PROPOSED` and requires
`VERIFIER_AND_HUMAN_REVIEW`. Hard guards, aliases, states, capabilities, risks,
verifier requirements, approval requirements, active grammar files, and source code
remain outside the learning surface.

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
learned_weight_patch_authority: false
crystallization_patch_authority: false
automatic_grammar_promotion: false
```

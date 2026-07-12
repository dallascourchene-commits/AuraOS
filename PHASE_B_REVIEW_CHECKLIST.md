# Phase B V2 Review Checklist

This proposal-only Crucible branch must remain unmerged until Dallas Courchene reviews
it and all applicable checks below are complete.

## Experience V2 integration

- [ ] Confirm every newly recorded experience has a canonical
      `grammar_manifest_digest`.
- [ ] Confirm V1 rows migrate without fabricated digests, OutcomeVectors,
      alternatives, or predictions.
- [ ] Confirm legacy rows are readable but excluded from Crucible mining.
- [ ] Confirm `OutcomeVector` dimensions are nullable, bounded, observable, and
      proposal-only.
- [ ] Confirm `final_outcome` is retained for audit but not converted into a binary
      learning target.
- [ ] Confirm every experience preserves all admitted alternatives and predictions in
      matching order.

## Dataset and validation separation

- [ ] Confirm TRAIN, VALIDATION, and SHADOW experience IDs are pairwise disjoint.
- [ ] Confirm TRAIN alone computes the candidate value.
- [ ] Confirm VALIDATION alone assesses independent OutcomeVector evidence.
- [ ] Confirm SHADOW alone performs routing replay.
- [ ] Confirm dataset ID digests match the stored candidate.
- [ ] Confirm missing shadow alternatives or predictions fail structural validation.
- [ ] Confirm shadow replay cannot introduce greater unresolved risk or evidence gap.

## Manifest pinning

- [ ] Confirm manifest paths are repository-relative.
- [ ] Confirm absolute paths, traversal, and repository escape fail closed.
- [ ] Confirm the manifest is recompiled with `aura_arena_wfst_compiler`.
- [ ] Confirm the canonical compiler digest—not a raw byte hash—matches the experience
      and candidate.
- [ ] Confirm Arena ID and grammar version also match the compiled manifest.

## Proposal-only thresholds

- [ ] Confirm every threshold field is prefixed `proposal_`.
- [ ] Confirm reports state `threshold_scope: PROPOSAL_ONLY`.
- [ ] Confirm thresholds never become guards, routing policy, patch authority, or
      promotion authority.
- [ ] Confirm a structurally valid candidate can be stored with
      `REVIEW_WITH_THRESHOLD_WARNINGS`.
- [ ] Confirm threshold failures remain visible rather than silently deleting the
      candidate.

## Authority and privacy

- [ ] Inspect experience and proposal packets for credentials, cookies, private keys,
      hidden reasoning, scratchpads, or chain-of-thought.
- [ ] Confirm no code path writes active `.aura/arena_routes/*.json` manifests.
- [ ] Confirm no code path updates runtime weights.
- [ ] Confirm no CLI command can apply, promote, commit, push, or merge.
- [ ] Confirm all stored outputs terminate at `CRYSTALLIZATION_PROPOSED`.
- [ ] Confirm every proposal requires `VERIFIER_AND_HUMAN_REVIEW`.
- [ ] Confirm typed contracts and SQLite reconstruction reject forged authority.
- [ ] Confirm `aura_crystallization.py` remains separate and unchanged.

## Operations

- [ ] Verify pause/resume persists across separate processes.
- [ ] Verify a paused service performs no mining cycle.
- [ ] Verify repeated identical cycles reuse one proposal rather than duplicating it.
- [ ] Verify empty, legacy-only, stale-digest, Meta, and unknown-transition ledgers
      complete safely with zero proposals.
- [ ] Run the Crucible against a copied real `arena_experience.db`.
- [ ] Review storage growth and bounded cycle limits.

## CI and repository integration

- [ ] Focused contract jobs pass on Python 3.10 and 3.12.
- [ ] Fatal lint and module-compilation checks pass.
- [ ] The complete repository pytest suite passes or every pre-existing failure is
      explicitly documented and separated from this branch.
- [ ] Aura’s navigator regenerates `.aura/CODEMAP.json` and `.aura/CODEMAP.md`.
- [ ] `python -m aura_codemap_verify` passes.
- [ ] CODEMAP reports positive topology nodes and edges from
      `compiled_deep_topology`.
- [ ] CODEMAP contains the V2 Phase B files and required symbols.
- [ ] CODEMAP Markdown and JSON summary metrics agree.
- [ ] No severe topology regression exists relative to the committed baseline.
- [ ] The temporary branch-only CODEMAP auto-commit workflow is removed before merge.
- [ ] Module manifests, affordances, and other generated architecture metadata are
      reviewed for refresh requirements.
- [ ] CodeRabbit reviews the completed V2 diff and all grounded findings are fixed.
- [ ] Dallas Courchene gives explicit approval before merge.

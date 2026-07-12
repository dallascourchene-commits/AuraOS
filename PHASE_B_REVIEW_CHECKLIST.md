# Phase B Review Checklist

This proposal-only Crucible branch must remain unmerged until every applicable item
is completed from a real AuraOS checkout.

## Validation

- [ ] Run the full repository test suite.
- [ ] Run `pytest -q tests/test_aura_crucible_phase_b.py`.
- [ ] Run static analysis and CodeRabbit review.
- [ ] Exercise the Crucible against a copied real `arena_experience.db` dataset.
- [ ] Confirm incomplete, stale, Meta, and unknown-transition records are ignored.
- [ ] Confirm training and temporal holdout IDs never overlap.
- [ ] Confirm low-support, low-diversity, and failed-holdout candidates are rejected.
- [ ] Confirm shadow replay never changes selection toward greater risk or evidence gap.

## Security and privacy

- [ ] Inspect proposal packets for secrets, credentials, cookies, private keys, hidden
      reasoning, scratchpads, or chain-of-thought.
- [ ] Confirm only sanitized observable experience payloads are consumed.
- [ ] Confirm forged authority flags and non-proposal statuses fail closed.
- [ ] Confirm manifest paths remain repository-local and pinned by digest.

## Authority boundary

- [ ] Confirm no code path writes `.aura/arena_routes/*.json`.
- [ ] Confirm no code path updates runtime weights.
- [ ] Confirm no CLI command can apply, promote, commit, push, or merge.
- [ ] Confirm all stored outputs terminate at `CRYSTALLIZATION_PROPOSED`.
- [ ] Confirm every proposal requires `VERIFIER_AND_HUMAN_REVIEW`.
- [ ] Confirm `aura_crystallization.py` remains separate and unchanged.

## Operations

- [ ] Verify pause/resume persists across separate processes.
- [ ] Verify a paused service performs no mining cycle.
- [ ] Verify repeated identical cycles reuse one proposal rather than duplicating it.
- [ ] Verify an empty or insufficient ledger completes safely with zero proposals.
- [ ] Verify cooperative service shutdown and bounded-cycle behavior.
- [ ] Review storage growth and the 1,000-record per-cycle limit.

## Repository integration

- [ ] Refresh `.aura/CODEMAP.md` and `.aura/CODEMAP.json` with Aura's generator.
- [ ] Refresh module manifests, affordances, and generated topology metadata.
- [ ] Confirm the Crucible database remains runtime-local and ignored by Git.
- [ ] Update user-facing documentation where appropriate.
- [ ] Obtain Dallas Courchene's explicit approval before merge.

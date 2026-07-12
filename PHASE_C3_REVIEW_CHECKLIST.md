# Phase C3 Review Checklist

This branch must remain unmerged until every applicable gate is reviewed.

- [ ] Confirm the branch is based on the merged Phase C2 `main` baseline and contains no code copied from closed PR #73.
- [ ] Confirm C1 capsule compilation and C2 live routing files are not weakened or replaced.
- [ ] Confirm variant generation permits only the seven declared proposal-safe dimensions.
- [ ] Confirm every variant is baseline-equivalent or tighter; expansion fails closed.
- [ ] Confirm capabilities, model policy, verifier contract, output schema and morphology cannot vary.
- [ ] Confirm only the explicit built-in trial executor can run.
- [ ] Confirm unavailable Wasmtime never falls back to arbitrary native execution.
- [ ] Confirm every trial creates and then verifies dissolution of its temporary sandbox.
- [ ] Confirm the independent C3 lease includes `trial:isolated_capsule` and all capsule capabilities.
- [ ] Confirm TRAIN, VALIDATION and SHADOW case IDs and digests are pairwise disjoint.
- [ ] Confirm only TRAIN results choose the winner.
- [ ] Confirm VALIDATION and SHADOW assess but never select a variant.
- [ ] Confirm OutcomeVector, token estimates, wall time, tool calls, model calls and reproducibility are recorded.
- [ ] Confirm procedure induction advances through Agent IR floors without emitting executable source code.
- [ ] Confirm `PURE` requires all validation, shadow, reproducibility, budget and dissolution gates.
- [ ] Confirm the C3 store and CLI expose no apply, activate, install, promote, commit, push or merge operation.
- [ ] Run focused C1, C2, Phase B and C3 tests on Python 3.10 and 3.12.
- [ ] Regenerate `.aura/CODEMAP.json` and `.aura/CODEMAP.md` from the final branch head.
- [ ] Review CodeRabbit findings and apply only grounded fixes.
- [ ] Obtain Dallas Courchene's explicit approval before merge.

## Explicitly deferred to C4+

- generated crystallized source packages;
- benchmark UI and AMD hackathon presentation layer;
- installation or promotion of a winning procedure;
- live runtime replacement;
- automatic commit, push, PR creation or merge.

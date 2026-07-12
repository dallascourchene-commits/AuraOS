# Phase C2 Review Checklist

This branch must remain unmerged until all applicable gates are reviewed.

## Base authority and compatibility

- [ ] Confirm the base guarded Arena WFST runs before any capsule logic.
- [ ] Confirm hard-guard-blocked transitions never reach capsule materialization.
- [ ] Confirm capsule resonance receives only transitions admitted by the base runtime.
- [ ] Confirm feature-disabled routing preserves legacy selection and state behavior.
- [ ] Confirm an exact capsule-bound command cannot fall through when its capsule gate fails.
- [ ] Confirm no existing Human Agent route is activated through C2.

## Capsule compilation and materialization

- [ ] Confirm declarative capsule references compile during manifest registration.
- [ ] Confirm explicit operator attachment validates capsule/transition identity.
- [ ] Confirm all nine C1 component digests are revalidated at materialization time.
- [ ] Confirm a missing capability lease blocks the capsule fail closed.
- [ ] Confirm unbounded repository context is rejected.
- [ ] Confirm file, symbol, line, memory, model and execution budgets are enforced.
- [ ] Confirm measured post-execution budget overruns deny the state transition.
- [ ] Confirm materialization itself performs no tool, model or source execution.

## Polysynthetic and VSA integration

- [ ] Confirm runtime intent packets preserve `DIR, ASP, CLASS, SUBJ, VOICE, STEM` order.
- [ ] Confirm adjunct routing fields remain outside the six-slot core.
- [ ] Confirm VSA profile and capsule digests are pinned in every materialized row.
- [ ] Confirm resonance has no patch, lease, capability or promotion authority.

## Coding Workbench MVP path

- [ ] Confirm the opt-in adapter affects only `CODING.TASK_SCOPED.LOCALIZE_CODE`.
- [ ] Confirm the existing localization implementation remains the executor.
- [ ] Confirm localization output is clamped to the pinned data aperture.
- [ ] Confirm no patch, PR, commit, push or merge is performed.
- [ ] Confirm the original Coding Workbench adapter remains usable unchanged.

## Experience and migration

- [ ] Confirm ArenaExperience V3 preserves the V2 field order and APIs.
- [ ] Confirm complete alternatives and predictions remain recorded.
- [ ] Confirm capsule-aware predictions include resonance and capsule/aperture digests.
- [ ] Confirm actual context, tool, model and budget usage are observable and sanitized.
- [ ] Confirm V2 SQLite databases migrate in place without invented capsule provenance.
- [ ] Confirm `v2_complete_record_count` remains available as a compatibility alias.

## Validation and review

- [ ] Run Phase C2 focused tests on Python 3.10 and 3.12.
- [ ] Run C1, Phase B, Coding Workbench equivalence and Human Agent regression tests.
- [ ] Regenerate and verify CODEMAP from the final PR head.
- [ ] Review CodeRabbit findings and apply only grounded fixes.
- [ ] Obtain Dallas Courchene's explicit approval before merge.

## Explicitly deferred to C3+

- Crucible-generated capsule variations;
- TRAIN / VALIDATION / SHADOW capsule trials;
- procedure induction;
- Agent IR promotion;
- generated crystallized code;
- automatic capsule activation or installation.

# Phase C1 Review Checklist

This branch must remain unmerged until every applicable Phase C1 gate is reviewed.

## Phase C1 contract review

- [ ] Confirm C1 does not alter live Human Agent or Coding Workbench routing.
- [ ] Confirm VSA resonance receives only capsule IDs already admitted by hard guards.
- [x] Confirm BLAKE2-derived vectors are stable across Python processes and hash seeds.
- [x] Confirm bind/unbind recovery and six-slot ordering tests pass.
- [x] Confirm route-capsule references reject absolute paths, traversal and symlinks.
- [x] Confirm all nine component references are pinned by canonical digest.
- [x] Confirm requested capabilities exactly match the grounded tool bundle.
- [x] Confirm capsule manifests reject executable content and promotion authority.
- [x] Confirm the repository localization capsule compiles against real Aura registries.
- [x] Confirm the merged temporary Phase B repair workflow is deleted.
- [x] Run focused Phase A, Phase B and Phase C1 tests on Python 3.10 and 3.12.
- [ ] Commit regenerated `.aura/CODEMAP.json` and `.aura/CODEMAP.md` from the final PR head.
- [ ] Review CodeRabbit findings and apply only grounded fixes.
- [ ] Obtain Dallas Courchene's explicit approval before merge.

## Repository baseline failures observed by the expanded CI matrix

These failures are outside the files and behavior changed by C1. They are recorded for
transparency and should not be silently repaired inside this focused architecture PR:

- `test_aura_icm_workspace.py::test_arena_export_to_icm_creates_workspace` constructs
  the pre-existing `LiquidPlanningArena` signature and is missing four newer required
  fields: `arena_version`, `plan_ref`, `domain_objects`, and `shared_action_queue`.
- `test_pvm_logic.py` reports pre-existing PVM architecture-policy violations.
- `test_aura_substrate.py` contains a stale hard-coded edit-plan line number.

A separate repository-cleanup change or an explicit maintainer decision is required for
those baseline checks. Phase C1 does not modify those modules or fixtures.

## Explicitly deferred to C2+

- live transition schema changes;
- automatic capsule loading;
- data or memory aperture enforcement;
- model routing;
- Crucible capsule trials;
- Agent IR procedure induction;
- generated crystallized code;
- capsule activation or installation.

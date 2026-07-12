# Phase C1 Review Checklist

This branch must remain unmerged until every applicable gate is reviewed.

- [ ] Confirm C1 does not alter live Human Agent or Coding Workbench routing.
- [ ] Confirm VSA resonance receives only capsule IDs already admitted by hard guards.
- [ ] Confirm BLAKE2-derived vectors are stable across Python processes and hash seeds.
- [ ] Confirm bind/unbind recovery and six-slot ordering tests pass.
- [ ] Confirm route-capsule references reject absolute paths, traversal and symlinks.
- [ ] Confirm all nine component references are pinned by canonical digest.
- [ ] Confirm requested capabilities exactly match the grounded tool bundle.
- [ ] Confirm capsule manifests reject executable content and promotion authority.
- [ ] Confirm the repository localization capsule compiles against real Aura registries.
- [ ] Confirm the merged temporary Phase B repair workflow is deleted.
- [ ] Run focused Phase A, Phase B and Phase C1 tests on Python 3.10 and 3.12.
- [ ] Run the complete pytest-native suite.
- [ ] Run all legacy executable validators through their intended entry points.
- [ ] Regenerate and verify CODEMAP topology from the final PR head.
- [ ] Review CodeRabbit findings and apply only grounded fixes.
- [ ] Obtain Dallas Courchene's explicit approval before merge.

## Explicitly deferred to C2+

- live transition schema changes;
- automatic capsule loading;
- data or memory aperture enforcement;
- model routing;
- Crucible capsule trials;
- Agent IR procedure induction;
- generated crystallized code;
- capsule activation or installation.

# Aura Construction G4-G6 Takeover Ledger

**Branch:** `work/construction-arena-g4-g6-20260722`  
**Draft PR:** `#186`  
**Exact base:** `e2c571267108e8b944aa427606d5279019557a99`  
**Policy:** commit every independently useful change immediately; never squash recovery points while implementation is incomplete.

## Completed recovery points

- `82782d7` — immutable G4 fixture contracts and authority boundaries.
- `3287f9e` — deterministic asset-pack-bound G4 fixture builder.
- `f1b4bba` — focused G4 fixture tests.
- `e35f907` — canonical hexadecimal test digests.
- `7642722` — canonical proposal-only G4 runtime packet composition.
- `5a06027` — G5 asset-pack to canonical Spatial foundation.
- `ec5b3d1` — focused G5 Spatial foundation tests.
- `37cd8b3` — pytest-local import correction for the isolated G5 test module.

## Implemented G4 behavior

- Fixture is bound to discovered `ConstructionDemoAssetPack` storey IDs.
- Canonical Construction evidence, claims, events, replayed state, candidates, and adapter runtime are reused.
- All nine required work states and all declared fictional trades are represented.
- Timeline, synthetic CAD projections, inspections, crane/logistics, blocked unsafe work, evidence gates, and human-review-only alternatives are included.
- Mock rules are explicitly `SYNTHETIC_DEMO_RULE` and claim no legal, regulatory, or jurisdiction authority.

## G5 current state

`aura_construction_demo_spatial_assets.py` now projects the admitted asset pack into canonical immutable Spatial frames, assets, building/storey entities, and containment links. Source geometry remains separate from status overlays. The projection contains no person-level data and grants no survey, renderer, or physical authority.

## Next exact slices

1. Run/inspect focused G4/G5 tests and repair exact failures in one-change commits.
2. Add work-package/status overlay records bound to fixture package and storey IDs.
3. Compose Spatial Projection V2 by combining the immutable asset foundation, privacy-minimized canonical Construction projection, and separate status overlays.
4. Add focused G5 privacy, digest, referential-integrity, and authority tests.
5. Implement G6 browser renderer in isolated JavaScript commits: packet decoder; mesh pass; degree-0 Gaussian pass; hybrid composition; floor controls; overlays; cancellation/disposal; accessible fallback; tests.
6. Update this ledger after every completed slice.

## Non-negotiable authority boundary

```yaml
fictional_source: true
proposal_only: true
survey_authority: false
physical_work_authority: false
payment_authority: false
access_authority: false
professional_authority: false
legal_or_regulatory_authority: false
renderer_authority: false
production_mutation: false
automatic_merge: false
human_review_required: true
```

Do not merge PR #186 until G4-G6 verification is complete and Dallas explicitly authorizes merge.

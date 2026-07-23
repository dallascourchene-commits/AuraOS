# Aura Construction Arena — G7–G8 Finalization

## Status

The Construction Arena refactor now spans the complete implementation chain:

```text
G0 architecture/dependency lock
→ G1 source acquisition and immutable asset contracts
→ G2 IFC storey/GLB/SVG compiler
→ G3 deterministic degree-0 Gaussian compiler
→ G4 asset-bound synthetic Construction project fixture
→ G5 immutable Spatial Projection V2
→ G6 local WebGL2 mesh/Gaussian/overlay composition
→ G7 cinematic Construction UI and deterministic director mode
→ G8 proof, review, documentation, and generated navigation synchronization
```

The G7 director does not create a new Construction truth owner. It composes:

```text
ConstructionDemoAssetPack
+ canonical ConstructionProjectState
+ canonical Construction runtime packet
+ G5 SpatialSceneSnapshot
+ G6 ConstructionSceneRenderer
+ presentation-only tour steps
```

## Launch

Generate and inspect the deterministic packet without starting a server:

```bash
python aura_spatial_cli.py \
  --repo-root . \
  construction-video-demo \
  --tour full \
  --output /tmp/aura-construction-demo.packet.json
```

Launch the local video surface:

```bash
python aura_spatial_cli.py \
  --repo-root . \
  construction-video-demo \
  --tour full \
  --serve
```

Open:

```text
http://127.0.0.1:8767/demo/construction?tour=full
```

Use an admitted generated asset pack when available:

```bash
python aura_spatial_cli.py \
  --repo-root . \
  construction-video-demo \
  --asset-pack demo_assets/construction_tuwien/generated/asset-pack.manifest.json \
  --tour full \
  --serve
```

When no pack path is supplied, the director uses a deterministic five-storey local fallback. The fallback preserves the same immutable contracts and uses bounded degree-0 Gaussian presentation data; it is not survey geometry and must not be described as a real construction site.

## Director tours

Supported tour names:

- `full` — complete 18-step recording sequence;
- `blocked-work` — blocked drilling, evidence, unsafe option, and cleanup;
- `alternatives` — unsafe option versus human-review alternative, schedule, cost, and idle deltas;
- `timeline` — exploded storeys, floor plans, timeline replay, and trade history.

The full sequence shows attribution, the hybrid building, orbit and exploded floors, floor-plan overlays, timeline replay, blocked drilling, missing dispositive asbestos evidence, the hard-blocked unsafe option, safe alternate work, trade history, dependencies, synthetic rule and inspection gates, budget/schedule comparison, Observatory evidence, a human decision packet, and exact renderer dissolution.

## UI controls

The local browser surface supports:

```text
orbit · zoom · storey isolation · show all · explode · collapse
mesh · splats · hybrid
floor plans · status · trades · blockers · budgets · inspections
dependencies · synthetic rules · timeline scrub · picking · reset
guided tour · pause · next step · dissolve
```

Exploded transforms are presentation-only. Source coordinates, Construction scope identity, schedule truth, and project state remain unchanged.

## Authority and privacy boundary

Every director packet and tour step preserves:

```yaml
physical_work_authorized: false
payment_released: false
access_controlled: false
professional_certification_claimed: false
legal_or_regulatory_authority_claimed: false
survey_authority_claimed: false
renderer_authority: false
automatic_execution: false
automatic_merge: false
human_review_required: true
```

The surface may recommend an admissible alternative for human review. It may not release work, mutate the Construction ledger, operate equipment, control access, certify a design, issue a permit, release payment, or merge code.

## Attribution

The admitted source contract remains:

> Building geometry adapted from “Custom Test Model for Escape Route Analysis in IFC format,” Fischer, Schranz, Urban, Pfeiffer, and Zdanowicz, TU Wien, DOI 10.48436/a185k-86v39, licensed under CC BY 4.0. Construction activities, schedules, budgets, organizations, hazards, regulations, and project status shown by AuraOS are fictional synthetic demonstration data.

TU Wien does not endorse AuraOS. The model is not survey-authoritative.

## Verification

Focused verification must include:

```bash
python -m py_compile \
  aura_construction_demo_director.py \
  aura_spatial_cli.py

ruff check \
  aura_construction_demo_director.py \
  aura_spatial_cli.py \
  tests/test_aura_construction_demo_director.py

ruff format --check \
  aura_construction_demo_director.py \
  aura_spatial_cli.py \
  tests/test_aura_construction_demo_director.py

pytest -q \
  tests/test_aura_construction_demo_director.py \
  tests/test_aura_construction_demo_fixture.py \
  tests/test_aura_construction_demo_projection.py

node --test \
  tests/js/spatial-construction-demo.test.mjs \
  tests/js/spatial-construction-review-regressions.test.mjs \
  tests/js/spatial-gaussian-covariance.test.mjs
```

Then run the architecture harness, Coding Relationship Compass, Coding Waboose, Crucible, Codex, CodeRabbit, and exact-head checks. Regenerate `.aura/CODEMAP.json`, `.aura/CODEMAP.md`, `topology_map.json`, and `Aura_Memory/live_topology_ast.json` only after source and tests stabilize.

## Recording checklist

```yaml
aspect_ratio: 16:9
external_network_required: false
random_runtime_generation: false
deterministic_camera_and_tour: true
manual_pause_and_override: true
caption_safe_layout: true
accessible_fallback_required: true
source_attribution_visible: true
human_authority_visible: true
renderer_cleanup_visible: true
```

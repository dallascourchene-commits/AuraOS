# Aura Construction Spatial Foundry — PR 3 Decision Lane

## Purpose

PR 3 composes the complete Construction decision lane into the existing Construction/Pascal Spatial Foundry. Aura remains the canonical Construction, evidence, planning, verification, continuity, and authority system. Pascal remains a local, disposable design and floor-plan presentation organ.

## Retained owners

- `ConstructionProjectState` remains Construction truth.
- `ConstructionArenaAdapter` applies hard guards before ranking and emits the canonical runtime evaluation.
- `aura_construction_demo_fixture_builder` supplies the exact offline Construction fixture and exact candidate set.
- `aura_construction_demo_projection` produces the Aura-derived as-built Spatial scene.
- `aura_spatial_render_plan` negotiates the retained Aura WebGL2/Gaussian render plan.
- `aura_pascal_spatial_presentation` owns the pinned Pascal artifact, coordinate receipt, node bindings, bridge messages, and disposable session.
- `aura_spatial_interaction.compile_spatial_interaction` compiles P3 focus and candidate-review actions into the retained six-slot interaction grammar.

## New composition

`ConstructionFoundryDecisionCompiler` produces one exact projection containing:

- current Construction state and runtime packet identities;
- Pascal node-to-Aura target mappings;
- DESIGN, FLOOR_PLAN, AS_BUILT, and COMPARE view state;
- synchronized Pascal storey/node and Aura as-built frame/entity/camera targets;
- work-package, hazard, geofence, inspection, dependency, crew, budget, schedule, staging, and waste/bin projections;
- evidence pins and open obligations;
- exactly three role-distinct `ConstructionCoordinationCandidateArtifact` projections;
- exact closure counts and schedule, budget, and idle-time deltas;
- a `DomainDecisionEnvelope` that stops at `READY_FOR_HUMAN_REVIEW`;
- digest-bound JSON and PDF decision-support exports.

The as-built iframe initializes Aura's existing `ConstructionSceneRenderer`. It validates the exact state and scene digests before applying the selected frame, selected issue entity, timeline, camera focus, and admitted overlay set. The Pascal and Aura renderers remain separate panes; compare mode does not claim survey alignment or same-canvas truth.

## Authority boundary

Every P3 output retains:

- `physical_work_authorized: false`
- `professional_approval: false`
- `payment_released: false`
- `access_granted: false`
- `automatic_execution: false`
- `construction_event_appended: false`
- `survey_authority: false`
- `human_review_required: true`

The JSON/PDF exports are decision support only. They are not a canonical project record, approved change order, professional certification, payment release, access grant, or authorization to perform physical work.

## Failure behavior

P3 fails closed for:

- unknown views or request fields;
- stale Construction state/runtime identities;
- stale Pascal artifact or coordinate receipt;
- stale as-built scene identity;
- stale candidate digest;
- hidden-storey Pascal selection;
- unadmitted issue, storey, node, frame, entity, candidate, overlay, or timeline;
- missing P3 static assets or retained Aura renderer assets.

If P3 cannot initialize, the composed P2 Pascal Foundry remains available. P3 does not alter the pinned P2 Pascal source lock or bridge assets.

## Local command

```bash
python aura_construction_pascal_spatial_foundry_p3_server.py \
  --repo-root . \
  --host 127.0.0.1 \
  --port 8765 \
  --no-auto-start
```

Open `http://127.0.0.1:8765`.

## Focused verification

```bash
python -m py_compile \
  aura_construction_foundry_decision.py \
  aura_construction_pascal_spatial_foundry_p3_server.py

node --check aura_showcase/construction-decision-foundry.js
node --check aura_showcase/construction-decision-as-built-sync.js

pytest -q \
  tests/test_aura_construction_foundry_decision.py \
  tests/test_aura_construction_pascal_spatial_foundry_p3_server.py \
  tests/test_aura_construction_pascal_spatial_foundry_server.py \
  tests/test_aura_construction_spatial_foundry.py
```

Run the broader Construction/Spatial regression workflow before claiming readiness. External reviewer invocation and merge remain separately authorized actions.

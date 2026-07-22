# Aura Construction Arena BIM/Gaussian Demo — Implementation Ledger

```yaml
document_status: ACTIVE_G0
created_date: 2026-07-22
repository: dallascourchene-commits/AuraOS
working_branch: work/construction-arena-bim-gaussian-demo-20260722
stacked_on_harness_pr: 182
harness_head_sha: 1dd81514638372ebf1e6812883dfcf706c5d87c0
source_plan_filename: AURA_CONSTRUCTION_ARENA_BIM_GAUSSIAN_DEMO_CODING_PLAN(1).md
source_plan_sha256: 03f4cab34822b3cc24cf640b41702a23aeaae511e997231a0e2bc5e596703705
source_plan_lines: 1630
chosen_route: TU_WIEN_IFC_TO_PER_FLOOR_GLB_SVG_PLY_SPZ
source_truth: TU_WIEN_FICTIONAL_IFC_MODEL
gaussian_role: PRESENTATION_ONLY
runtime_external_fetch: false
human_review_required: true
automatic_merge: false
```

## Purpose

This ledger is the durable, PR-visible takeover surface for implementing a deterministic,
video-recordable Construction Arena demonstration from the openly licensed TU Wien fictional
IFC model. It records the exact objective, canonical-owner checks, file decisions, commits,
verification evidence, unresolved risks, and next resume command at every bounded checkpoint.

Every source or documentation mutation for this program must be committed to the working branch
as a coherent checkpoint. Generated navigation artifacts are regenerated last after source and
tests stabilize.

## Exact architecture-harness objective

> Build a deterministic, video-recordable, synthetic multi-floor Construction Arena
> demonstration using the TU Wien fictional IFC source. Convert the IFC into per-storey GLB,
> SVG, PLY, and SPZ representations; bind them to the canonical ConstructionProjectState,
> Planning Board, Financial Exact State, Temporal Persistence, Human Agent, Observatory, and
> Spatial Arena; render a hybrid mesh and bounded degree-0 Gaussian interface; preserve exact
> provenance, privacy, accessibility, disposal, and human authority; do not create duplicate
> truth owners or grant physical, payment, professional, legal, regulatory, renderer, patch,
> publication, or production authority.

## Operating rules

1. Read `USER_GUIDE.md`, `README.md`, `.aura/ARCHITECTURE.md`, `.aura/CODEMAP.md`, the Spatial
   S5/S6 Construction documentation, current tests, and exact source slices before mutation.
2. Run the reusable Architecture Harness with Capability Connectome, Relational Index,
   Relationship Atlas, Coding Relationship Compass/Breadboard compatibility, Emergent
   Properties, Architect, Council V3, Planning Board, Coding Waboose, and Crucible surfaces.
3. Default Atlas profile is `MINIMAL`; deeper reasoning is limited to an objective-bounded
   participant neighborhood.
4. At 10 minutes, inspect the watchdog health receipt. At 20 minutes, stop at the retained
   artifact boundary and reassess before explicit resume.
5. The harness, topology, similarity, renderer, and model outputs are advisory/projection
   surfaces. Exact source spans, hashes, schemas, tests, and canonical contracts remain the
   grounding authority.
6. No real workers, real-person tracking, survey coordinates, live site sensors, contractor
   connectors, payments, access control, equipment control, professional certification,
   municipal-law claims, automatic work release, or automatic Construction state mutation.
7. The source IFC may be acquired only through an explicit operator command. Normal Aura startup
   and demo runtime must never fetch it.
8. The base IFC/mesh remains immutable geometry. Work state is emitted as a separate overlay.
9. No special importer bypass is permitted for demo assets.
10. Merge remains a separate explicit human decision.

## Source and licence decision

Use the TU Wien “Custom Test Model for Escape Route Analysis in IFC format” as the single
geometric source.

```yaml
doi: 10.48436/a185k-86v39
source_file: CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc
published_md5: 58a6e009b16bd3808cacd72b11fcf216
license: CC-BY-4.0
model_type: fictional_IFC4_building
coverage: five_storeys_plus_underground_parking
```

The first accepted acquisition run must calculate and pin the observed SHA-256. The published
MD5 is metadata only.

## Required representations

For every discovered storey, generate content-addressed IFC, GLB, sanitized SVG, degree-0
Gaussian PLY, SPZ v4, and a manifest. Also generate full-building GLB/PLY/SPZ, hierarchy,
element index, and an immutable asset-pack manifest.

The initial Gaussian representation is deterministic, bounded, degree 0, and styled as a clean
holographic BIM-derived presentation. It is not a photorealistic camera-trained 3DGS capture.

## Canonical-owner questions for G0

The architecture run must confirm or amend these assumptions before implementation:

- `ConstructionProjectState`, `ConstructionScope`, `ConstructionEvidence`,
  `ConstructionClaim`, and `ConstructionEvent` remain canonical Construction truth owners.
- `ConstructionArenaAdapter` remains the domain adapter; the demo fixture does not create a
  second project-state owner.
- Planning Board owns proposal/dependency planning; Financial Exact State owns financial truth;
  Temporal Persistence owns replay/checkpoint truth.
- Spatial scene modules own immutable projection snapshots only.
- Existing bounded GLB and SPZ importers remain the mandatory admission path.
- Existing Gaussian renderer/device/render-plan/disposal contracts are reused.
- Human Agent and Observatory remain review/explanation surfaces, not execution authority.
- Agent Bridge publication remains exact-head, compare-and-swap, and human-merge-gated.

## Initial candidate file map — pending G0 confirmation

### New source candidates

```text
aura_construction_demo_contracts.py
aura_construction_demo_fixture.py
aura_construction_demo_projection.py
aura_construction_demo_director.py
scripts/aura_fetch_construction_demo_source.py
scripts/aura_ifc_storey_index.py
scripts/aura_mesh_to_gaussian.py
scripts/aura_prepare_construction_demo_assets.py
scripts/aura_verify_construction_demo_assets.py
aura_spatial_web/construction_scene_renderer.js
aura_spatial_web/construction_mesh_pass.js
aura_spatial_web/webgl2_gaussian_pass.js
aura_spatial_web/construction_overlay_pass.js
aura_spatial_web/construction_demo.html
aura_spatial_web/construction_demo_app.js
aura_spatial_web/construction_demo.css
```

### Existing integration candidates

```text
aura_spatial_server.py
aura_spatial_cli.py
aura_spatial_agent_bridge.py
existing Construction contracts/state/adapter modules
existing GLB and SPZ importer modules
existing renderer/device/render-plan/disposal modules
existing Planning Board, Financial Exact State, Temporal Persistence, Human Agent, Observatory
```

### Asset/tooling/documentation candidates

```text
demo_assets/construction_tuwien/README.md
demo_assets/construction_tuwien/ATTRIBUTION.md
demo_assets/construction_tuwien/LICENSE-CC-BY-4.0.txt
demo_assets/construction_tuwien/source/source-manifest.json
tools/construction_demo_assets/README.md
tools/construction_demo_assets/requirements.txt
docs/AURA_CONSTRUCTION_ARENA_BIM_GAUSSIAN_DEMO_IMPLEMENTATION_LEDGER.md
```

### Test candidates

```text
tests/test_aura_construction_demo_assets.py
tests/test_aura_construction_demo_projection.py
tests/test_aura_construction_demo_cli.py
tests/js/construction-demo-renderer.test.mjs
tests/js/construction-demo-tour.test.mjs
```

No candidate path is approved merely by appearing here. G0 must identify existing owners,
name collisions, import boundaries, and safer integration points.

## Implementation gates

### G0 — Architecture and dependency lock

Deliver the harness run, objective-scoped Compass packet, exact owner map, dependency decision,
source/licence decision, Change Graph, risk register, and amended file list. No code mutation.

### G1 — Source acquisition and immutable asset contracts

Deliver operator-only source acquisition, source manifest/attribution, immutable asset contracts,
and source-verification tests.

### G2 — IFC compiler

Deliver deterministic hierarchy/indexing, storey split, GLB/SVG conversion, build receipts,
timeouts, sanitization, and focused tests.

### G3 — Gaussian compiler

Deliver deterministic mesh sampling, degree-0 PLY, SPZ v4, explicit coordinate bindings,
representation digests, importer validation, and allocation/GPU/frame-budget tests.

### G4 — Synthetic Construction fixture

Deliver storey/zone-bound scopes, trades, work history, hazards, blockers, inspections,
synthetic rules, schedule, budget, crane/logistics, alternative work, and verified canonical state.

### G5 — Spatial projection V2

Deliver frames, asset instances, domain entities/links, status/timeline/budget/rule projections,
and privacy/authority tests.

### G6 — Browser renderer

Deliver GLB, bounded degree-0 splat, hybrid composition, floor isolation/explosion, overlays,
picking, cancellation, device-loss handling, disposal, and accessible fallback.

### G7 — Cinematic UI and director mode

Deliver Construction Arena UI, bounded intent filters, inspector, timeline, scenario comparison,
deterministic tour, local launch route, and recording checklist.

### G8 — Final proof and publication

Run focused and regression verification, architecture harness, Waboose, Crucible, external review,
then regenerate CODEMAP/topology from the final source tree. Prepare merge evidence only; do not
merge without explicit human authorization.

## Commit protocol

Each commit must be small enough to review and resume independently. Preferred checkpoints:

```text
G0.1 ledger and objective pin
G0.2 architecture-harness evidence and owner map
G0.3 dependency/file lock and Change Graph
G1.1 attribution and source manifest contracts
G1.2 operator-only acquisition path
G1.3 source verification tests
G2.1 IFC hierarchy/index contracts
G2.2 storey split and conversion orchestration
G2.3 GLB/SVG validation and receipts
G3.1 deterministic mesh sampler
G3.2 Gaussian PLY/SPZ compilation
G3.3 Aura importer/budget verification
```

Later gates follow the same contract-first, implementation, focused-test cadence.

## Current checkpoint

```yaml
checkpoint: G0.1
status: committed
code_mutation_started: false
architecture_export_requested: true
architecture_run_completed: false
owner_map_locked: false
dependency_list_locked: false
change_graph_locked: false
next_action: obtain AI-safe repository export, run harness, and commit G0 evidence
```

## Handoff instructions

A replacement agent should:

1. inspect this ledger and the draft PR;
2. verify the exact branch head before writing;
3. obtain or regenerate the AI-safe harness export;
4. run the objective above with the uploaded source plan bound by SHA-256;
5. update this ledger with exact outputs and unresolved questions;
6. commit the G0 evidence before writing implementation code;
7. never skip the current canonical owner/importer/disposal checks;
8. stop and reassess at the harness watchdog pause boundary rather than silently restarting.

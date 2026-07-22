# Aura Construction Arena BIM/Gaussian Demo — G0 Change Graph

```yaml
document_status: G0_CHANGE_GRAPH_LOCKED
source_main_sha: 489baef6fc9c0363d5b71c4080efcb7c234e5a39
source_plan_sha256: 03f4cab34822b3cc24cf640b41702a23aeaae511e997231a0e2bc5e596703705
architecture_run_digest: 70228d5abc14b84e0ba14c89a68ed2cc
construction_compass_digest: 5bda692957d889912eb4e1d573aa82599757da11b60aa545
spatial_compass_digest: 901aec5279c7cb1906fd77cbabfcc05c10931714138b1d0a
supporting_owner_compass_digest: 46fc1df71124c6cd368128287606d53d90ca470e41829d83
proposal_only: true
safe_to_patch: false
human_review_required: true
```

## Compass and Coding Breadboard result

The Construction objective was compiled through three resource-bounded Compass packets. Each
packet retained a maximum of 96 participants and produced a grounded Coding Breadboard, Planning
Board projection, four continuity phases, ten act capsules, Agent IR, an exact Change Graph, and a
Council V3 route.

| Packet | Participants | Relations | Required tests | Primary grounded target | Result |
|---|---:|---:|---:|---|---|
| Construction truth/runtime | 96 | 148 | 47 | `aura_construction_runtime_binding.py#require_canonical_construction_runtime_packet` | Grounded; 7 prohibitions carried; `safe_to_patch=false` |
| Spatial/assets/render | 96 | 154 | 54 | `aura_spatial_construction.py#project_construction_state_to_scene` | Grounded; exact render-plan, GLB, SPZ, Agent Bridge, and runtime-validator targets present |
| Supporting owners | 96 | 129 | 31 | Architect/Change Graph meta-surfaces | Grounded architecture evidence, but not used as patch authority for financial/planning/temporal owners |

The first two packets localized to the expected canonical implementation boundaries. The third
packet localized to the architecture planning machinery rather than to the requested supporting
owners; therefore its Change Graph is retained only as architecture-routing evidence. Planning,
Financial Exact State, and Temporal Persistence remain locked by direct exact-source inspection
and tests, not by that packet's recommended patch targets.

## File-list amendments from G0

### Add

```text
aura_construction_demo_contracts.py
scripts/aura_fetch_construction_demo_source.py
scripts/aura_ifc_storey_index.py
scripts/aura_mesh_to_gaussian.py
scripts/aura_prepare_construction_demo_assets.py
scripts/aura_verify_construction_demo_assets.py
aura_construction_demo_fixture.py
aura_construction_demo_director.py
aura_spatial_web/construction_scene_renderer.js
aura_spatial_web/construction_mesh_pass.js
aura_spatial_web/webgl2_gaussian_pass.js
aura_spatial_web/construction_overlay_pass.js
aura_spatial_web/construction_demo.html
aura_spatial_web/construction_demo_app.js
aura_spatial_web/construction_demo.css
```

### Amend the original candidate `aura_construction_demo_projection.py`

Do not create a second canonical Construction→Spatial projector. Use one of these bounded forms:

1. extend `aura_spatial_construction.py` with a V2 composer that accepts the immutable asset pack
   and synthetic projection inputs; or
2. add a thin `aura_construction_demo_projection.py` composer whose only authority is to call the
   canonical `project_construction_state_to_scene` path and then append validated presentation
   assets/entities through existing immutable scene contracts.

The thin composer must not own Construction state, event replay, project decisions, renderer
state, financial truth, temporal truth, or authority routing.

### Extend existing owners

```text
aura_spatial_construction.py
aura_spatial_render_plan.py
aura_spatial_server.py
aura_spatial_cli.py
aura_spatial_agent_bridge.py
aura_spatial_web/gaussian_renderer.js
existing renderer/device/telemetry/disposal modules
existing Construction adapter/runtime/Human Agent/Observatory integrations
```

### Generated navigation artifacts

Regenerate only after source and tests stabilize:

```text
.aura/CODEMAP.json
.aura/CODEMAP.md
topology_map.json
Aura_Memory/live_topology_ast.json
```

They are never patch authority and must not be hand-edited as implementation source.

## Ordered implementation graph

### G0 — Architecture and dependency lock

**Inputs**

- exact `main` snapshot;
- pinned Construction coding plan;
- USER_GUIDE, README, Architecture, CODEMAP/topology, and Construction/Spatial evidence;
- Architecture Harness, Connectome, Relational Index, Atlas, Emergent Properties, Architect,
  Council V3, Coding Breadboard, Planning Board, Waboose/Crucible evidence paths.

**Outputs**

- canonical owner map;
- dependency/source/licence lock;
- Compass packets and Change Graph;
- tested resolver patch artifact;
- PR-visible implementation ledger.

**Exit gate**

No source implementation begins until the owner map and authority prohibitions are durable in the
PR. This gate is satisfied for G1.

---

### G1 — Source acquisition and immutable asset contracts

**Depends on:** G0

**New files**

```text
aura_construction_demo_contracts.py
demo_assets/construction_tuwien/README.md
demo_assets/construction_tuwien/ATTRIBUTION.md
demo_assets/construction_tuwien/LICENSE-CC-BY-4.0.txt
demo_assets/construction_tuwien/source/source-manifest.json
scripts/aura_fetch_construction_demo_source.py
tools/construction_demo_assets/README.md
tools/construction_demo_assets/requirements.txt
tests/test_aura_construction_demo_assets.py
```

**Contracts**

- `ConstructionDemoSourceManifest` owns source identity/licence only;
- `ConstructionDemoStorey` owns deterministic storey identity only;
- `ConstructionDemoAssetBinding` owns immutable representation identity/provenance only;
- `ConstructionDemoAssetPack` owns the content-addressed pack identity only.

**Hard guards**

- explicit operator-only network acquisition;
- approved TU Wien host/file only;
- redirect refusal, byte ceiling, temporary download, MD5 metadata check, SHA-256 pin, atomic move;
- no startup/runtime fetch;
- fictional source, no person-level data, no survey authority;
- no Construction, schedule, financial, regulatory, professional, renderer, or physical authority.

**Verification**

- contract invariants and canonical serialization/digests;
- source-manifest schema/round trip;
- attribution present;
- wrong filename/host/size/hash fail closed;
- no runtime import path invokes the fetcher.

---

### G2 — Deterministic IFC compiler

**Depends on:** G1

**Files**

```text
scripts/aura_ifc_storey_index.py
scripts/aura_prepare_construction_demo_assets.py
scripts/aura_verify_construction_demo_assets.py
tests/test_aura_construction_demo_assets.py
```

**Actions**

- inspect one project/building and enumerate storeys/spaces/elements;
- reject duplicate GlobalIds, non-finite values, absent storeys, or unbounded indexes;
- derive Aura storey IDs from source SHA-256 + IFC GlobalId + canonical name/elevation;
- split by `IfcBuildingStorey`;
- invoke IfcConvert with bounded workers and timeout;
- validate GLB header/resources/units/bounds through Aura's importer;
- sanitize SVG and reject scripts, external hrefs, and data URLs;
- write content-addressed receipts after every phase.

**Rollback**

Delete only the incomplete staging directory. Never mutate source IFC or Construction state.

---

### G3 — Deterministic degree-0 Gaussian compiler

**Depends on:** G2

**Files**

```text
scripts/aura_mesh_to_gaussian.py
scripts/aura_prepare_construction_demo_assets.py
scripts/aura_verify_construction_demo_assets.py
tests/test_aura_construction_demo_assets.py
```

**Actions**

- load validated GLB triangles;
- reject degenerate/non-finite geometry;
- fixed-seed, area-proportional barycentric sampling;
- normalized quaternion, positive bounded anisotropic scale, bounded opacity;
- deterministic semantic IFC-class palette;
- stable element/sample ordering;
- Gaussian PLY and Niantic SPZ v4 with explicit coordinate conversion;
- exact representation/source/output digests;
- validate every output through Aura's current SPZ importer and render-plan budgets.

**Important amendment**

The plan's `LOW`, `STANDARD`, and `VIDEO` splat counts are requested ceilings. Admission is
controlled by current source limits and device/render-plan preflight. Asset generation must lower
the effective count deterministically or fail closed; it may not bypass importer or GPU budgets.

---

### G4 — Synthetic Construction project fixture

**Depends on:** G1, G2, G3

**Files**

```text
aura_construction_demo_fixture.py
tests/test_aura_construction_demo_projection.py
```

**Actions**

- construct canonical `ConstructionScope`, `ConstructionEvidence`, `ConstructionClaim`, and
  `ConstructionEvent` records using discovered storey/zone IDs;
- replay them into `ConstructionProjectState`;
- route proposals through `ConstructionArenaAdapter` and canonical runtime packet registry;
- project schedule dependencies through Planning Board;
- project synthetic cost values without becoming Financial Exact State;
- use Temporal Persistence for deterministic checkpoint/replay references;
- label all mock rules `SYNTHETIC_DEMO_RULE` with no jurisdiction or authority.

**Required scenario**

Blocked upper-floor drilling, dispositive asbestos evidence gap, another floor released for safe
preparation, professionally evidenced electrical isolation, a crane window, labour cost/idle
tradeoff, an unsafe hard-blocked option, and a safe resequencing proposal for human review only.

---

### G5 — Construction Spatial projection V2

**Depends on:** G3, G4

**Files**

```text
aura_spatial_construction.py
optional thin aura_construction_demo_projection.py
tests/test_aura_construction_demo_projection.py
```

**Actions**

- call the canonical Construction runtime/state validator;
- bind immutable building/storey GLB, SVG, PLY/SPZ assets to actual discovered frames;
- project zones, work packages, hazards, inspections, synthetic rules, schedule tasks, budget
  lines, crew/trade activity classes, logistics, and proposal options;
- keep base geometry immutable and status separate;
- preserve privacy hashes, non-survey precision, no person identities, and proposal-only state;
- compile an immutable `SpatialSceneSnapshot` through existing scene contracts.

---

### G6 — Browser renderer

**Depends on:** G5

**Files**

```text
aura_spatial_web/construction_scene_renderer.js
aura_spatial_web/construction_mesh_pass.js
aura_spatial_web/webgl2_gaussian_pass.js
aura_spatial_web/construction_overlay_pass.js
aura_spatial_web/gaussian_renderer.js
tests/js/construction-demo-renderer.test.mjs
```

**Actions**

- preserve existing renderer/device/render-plan ownership;
- GLB mesh pass + bounded degree-0 Gaussian pass + overlay/dependency/label passes;
- mesh, splat, and hybrid modes;
- floor isolate/show-all/explode/collapse presentation transforms;
- timeline filters and picking;
- cancellation, device loss, exact disposal handles, accessibility fallback;
- no iframe, hosted viewer, remote shader/resource fetch, or higher-order SH requirement.

---

### G7 — Cinematic UI and director mode

**Depends on:** G5, G6

**Files**

```text
aura_spatial_web/construction_demo.html
aura_spatial_web/construction_demo_app.js
aura_spatial_web/construction_demo.css
aura_construction_demo_director.py
aura_spatial_server.py
aura_spatial_cli.py
aura_spatial_agent_bridge.py
tests/test_aura_construction_demo_cli.py
tests/js/construction-demo-tour.test.mjs
```

**Actions**

- bounded natural-language intent → filters, selection, camera, timeline query, comparison;
- deterministic guided tour with manual pause/override;
- inspector, evidence, mock-rule, budget, schedule, and proposal comparison panels;
- Human Agent and Observatory review surfaces;
- decision packet only; no automatic project mutation;
- deterministic Arena dissolution and cleanup proof.

---

### G8 — Final proof, navigation regeneration, and publication preparation

**Depends on:** G1-G7

**Verification order**

1. Python compilation and Ruff;
2. contract/schema tests;
3. focused Python and JavaScript tests;
4. Construction/Spatial security and authority regressions;
5. deterministic asset rebuild/digest proof;
6. lifecycle/disposal/zero-session proof;
7. Architecture Harness and objective-scoped Compass rerun;
8. Waboose and Crucible;
9. Codex and CodeRabbit review;
10. exact patches and rerun until clear;
11. regenerate CODEMAP/topology from final source;
12. exact-head verification and human merge packet.

Merge remains outside this graph and requires explicit human authorization.

## Commit sequence

```text
G0.1 implementation ledger and source-plan pin
G0.2 architecture evidence and owner lock
G0.3 tested harness defect patch artifact
G0.4 Change Graph and exact implementation file lock
G1.1 immutable source/asset contracts
G1.2 attribution, source manifest, and tool dependency lock
G1.3 operator-only source acquisition
G1.4 focused source and contract verification
G2.1 deterministic IFC hierarchy/index
G2.2 storey split + GLB/SVG orchestration
G2.3 receipts, sanitizer, importer validation
G3.1 deterministic mesh sampler
G3.2 PLY/SPZ v4 compilation
G3.3 importer/device/render budget verification
```

Every later gate follows contract → implementation → focused tests → durable checkpoint. Large
binary/generated assets are not committed until measured; Strategy A is attempted first, with a
versioned release bundle only when repository size evidence requires Strategy B.

## Takeover checkpoint

```yaml
completed:
  - exact repository export and virtual environment
  - Architecture Harness run
  - canonical owner map
  - Council V3 route
  - three bounded Compass/Coding Breadboard packets
  - source/licence/dependency decision
  - G0 file and Change Graph lock
next:
  - implement G1 immutable contracts and attribution
  - apply the tested resolver patch to canonical source when the branch write path permits
blocked: []
merge_authorized: false
```

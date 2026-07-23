# Aura Construction Arena BIM/Gaussian Demo — G0 Architecture Evidence

```yaml
document_status: G0_EVIDENCE_RECORDED
source_repository: dallascourchene-commits/AuraOS
source_main_sha: 489baef6fc9c0363d5b71c4080efcb7c234e5a39
source_plan_sha256: 03f4cab34822b3cc24cf640b41702a23aeaae511e997231a0e2bc5e596703705
architecture_harness_version: AURA_ARCHITECTURE_HARNESS_V1
architecture_run_digest: 70228d5abc14b84e0ba14c89a68ed2cc
architecture_request_digest: 00b63477bd2507f967340522039437c7
patch_authority: exact_source_spans_and_hashes_only
production_mutation: false
human_review_required: true
```

## Objective

Build a deterministic, video-recordable, synthetic multi-floor Construction Arena demonstration
using the TU Wien fictional IFC source. Convert the IFC into per-storey GLB, SVG, PLY, and SPZ
representations; bind them to the canonical ConstructionProjectState, Planning Board, Financial
Exact State, Temporal Persistence, Human Agent, Observatory, and Spatial Arena; render a hybrid
mesh and bounded degree-0 Gaussian interface; preserve exact provenance, privacy, accessibility,
disposal, and human authority; do not create duplicate truth owners or grant physical, payment,
professional, legal, regulatory, renderer, patch, publication, or production authority.

## Reproducible environment

The architecture run used the exact GitHub `main` snapshot at
`489baef6fc9c0363d5b71c4080efcb7c234e5a39`, exported by the AI-safe Architecture Harness
workflow. The snapshot contained 1,312 tracked files and was bound to a synthetic local Git
identity whose `aura.harnessSourceSha` points to the exact GitHub source SHA. The isolated virtual
environment resolved all eight required architecture imports and the working tree remained clean
before and after the run.

The export workflow was also corrected and proven before this run:

1. the request commit's harness script is extracted and compiled before checking out exact `main`;
2. the full forensic ZIP, manifests, and request harness are written outside the checkout;
3. the exact full repository artifact is uploaded before lightweight handoff generation;
4. the AI-first handoff and full snapshot were both produced successfully in workflow run
   `29908682929`.

## Harness results

| Surface | Result |
|---|---|
| Capability Connectome | 24 nodes, 76 edges, digest `8ce50643fa9de0e554009b842d1f973b` |
| Relational Index | 14,347 participants, 30,035 relations, 22 groups, index `relindex_6dea4f422c8d170215a5c1b2` |
| Relationship Atlas | `MINIMAL`, 30,035 assessments, 7 missing configurations, 7 prohibitions |
| Atlas snapshot | `1f0ee8a09abfeafec3fe1c6e5e2291d0aa810e36b8da136cf443434c155d4520` |
| Emergent Properties | 7,232 abilities scanned; one candidate remains `NEEDS_GROUNDING`; zero future-patchable findings |
| Architect | intensity 1; Shadow gate `ALLOW_BUILDER`; `ready_for_incubator=false`; `safe_to_patch=false` |
| Repository boundary | clean before and after; no production mutation |

`ALLOW_BUILDER` means the bounded implementation program may proceed through explicit source and
test work. It does not grant patch, commit, push, pull-request, merge, publication, or production
authority.

## Council V3 routing

The G0-G8 plan profiles as a `PROGRAM`:

```yaml
task_count: 9
distinct_file_count: 28
dependency_edge_count: 18
sequential_depth_estimate: 9
large_task_count: 9
council_recommended: true
selected_critic_lanes:
  - scope
  - tests
  - sequence
  - continuity
  - rollback
  - cost
```

Exact local resolver/assertion failures route to Surgeon with `tests` and `scope` lanes.
Cross-boundary interface, dependency, authority, prohibition, invariant, or sequence failures route
to Council V3. Both routes remain proposal-only.

## Canonical owner lock

| Concern | Canonical owner and exact source evidence | G0 decision |
|---|---|---|
| Construction records/contracts | `aura_construction_contracts.py`: `ConstructionScope` L202-L247, `ConstructionEvidence` L251-L431, `ConstructionClaim` L435-L608, `ConstructionEvent` L615-L855; file SHA-256 `8998c140d40177b8343545ce4e977c9e4365940e45008bbfef9fe9843dcc2d98` | Reuse; demo contracts may own asset provenance only, never project truth. |
| Construction truth and replay | `aura_construction_state.py`: `ConstructionProjectState` L249-L352; file SHA-256 `1dd3d13f255b5f46335320a7864ffcba872ab6bb0c722eed40de4df7c4dbd01f` | Sole Construction truth owner. No demo state replica. |
| Proposal filtering and authority routing | `aura_construction_adapter.py`: `ConstructionArenaAdapter` L945-L1246; SHA-256 `fdfb6fa80f8ae635a5811232158720f78552c6b64d914889056ef73138a40dae` | Reuse exact adapter/runtime packet boundary. |
| Runtime packet registry | `aura_construction_runtime_binding.py`: `require_canonical_construction_runtime_packet` L47-L64; SHA-256 `d449c4835bbdbfb9ae687a7469cb31dff904630767a3ec085688af1d337cd040` | Use existing registration/validation path; do not add JSON caller-constructed state. |
| Human Agent review | `aura_construction_human_agent.py`: profile builder L333-L427 and `ConstructionHumanAgentProfileService` L430-L539; SHA-256 `c2c92c1a713fcc419cd92efc31ffc0af5b1db96dc18b68f8fb67786b61ca4070` | Review/explanation only; no execution authority. |
| Spatial Construction projection | `aura_spatial_construction.py`: `project_construction_state_to_scene` L43-L272; SHA-256 `085b817bd75a8701bac7bbd901678642acaf2ae3f3244da4e8ec6420c235cfbd` | Extend this path or call it from a thin demo composer; do not create a second canonical projector. |
| Immutable scene/assets/disposal | `aura_spatial_contracts.py`: `SpatialAssetManifest` L591-L652, `SpatialSceneSnapshot` L810-L923, `SpatialDissolutionReceipt` L1434-L1552; SHA-256 `5db03f674d2104bd98c3e6efe641dd1704f7fd656f98477b58ca369cb68a182c` | Reuse exact immutable and disposal contracts. |
| Spatial lifecycle | `aura_spatial_arena.py`: `SpatialArena` L105-L1011; SHA-256 `60279b855e9071e2561bf4ecc03df342101f1bae802f902a75f77cf5016c0809` | Preserve FRAME→GROUND→COMPILE_SCENE→PLAN_RENDER→PRESENT→INTERACT→PROVE→DECIDE→DISSOLVE. |
| Render planning | `aura_spatial_render_plan.py`: `negotiate_spatial_render_plan` and `compile_gaussian_representation_budget`; SHA-256 `f25e8ad0bd14de47313249b9e8ea460f73c1949fcfc4e3f31ddaeb98fae0769c` | Existing render-plan/device budgets remain authoritative. |
| Typed Spatial Agent Bridge | `aura_spatial_agent_bridge.py`: `AuraSpatialAgentBridge` L27-L235; SHA-256 `03d16e77cfd42826068455412bf8d8160d362ad643ecf023f2e714bb2b081d33` | Add bounded demo operations only; preparation remains typed. |
| GLB admission | `aura_spatial_importers/gltf.py`: `import_gltf_bytes` L324-L452; SHA-256 `aeaa7352de271437e80b8864bebfb7aa5f55850c70de14c32f3556dd4d9c6c08` | Mandatory admission path; no demo bypass. |
| SPZ admission | `aura_spatial_importers/spz.py`: `inspect_spz_v4_bytes` L89-L151 and `import_spz_bytes` L206-L315; SHA-256 `39627b18ace3a64f54e909c60d4f0cc486823dac068042eb0e2d768b3a20e6bf` | Mandatory v4 admission path; explicit coordinate conversion. |
| Planning | `aura_planning_board.py`: `PlanningBoard` L392-L427; SHA-256 `79a372091c1c3c10d76c243992c5a7de719deea30213496dfc38481f68d01f46` | Owns proposal/dependency planning; demo emits bounded proposals. |
| Financial exact state | `aura_financial_contracts.py`: `FinancialLedgerSnapshot` L711-L919; SHA-256 `039645bf1fafbead20a323a40634cbb209684f79d9fd49e79dba07642cd9c674` | Owns financial truth; demo budget data is explicitly synthetic projection. |
| Temporal persistence | `aura_temporal_persistence.py`: `TemporalCheckpointRegistry` L260-L744; SHA-256 `626129fb843e18ed47bdb4af866b33c91a54c045975ed0d74d3e5b27ba99e973` | Owns checkpoints/replay; restore remains assessment-only and never auto-resumes. |

## Dependency lock

### Existing runtime dependencies to reuse

- Aura's strict GLB importer and existing spatial import receipt contracts;
- Aura's strict SPZ v4 importer and Gaussian representation digest;
- existing Gaussian renderer, device profile, render-plan, telemetry, cancellation, and disposal
  contracts;
- Planning Board, Financial Exact State, Temporal Persistence, Human Agent, Observatory, and
  Attempt Archive owners.

### Build-time dependencies admitted for the asset compiler

- IfcOpenShell / IfcPatch for IFC inspection and storey splitting;
- IfcConvert for IFC→GLB and IFC→sanitized SVG;
- Python `numpy` and `trimesh` for deterministic bounded mesh sampling;
- Niantic SPZ for explicit SPZ v4 compilation.

These dependencies are build-time only. The finished demo must run from already-generated,
content-addressed local assets and must not fetch geometry or viewers during runtime.

### Importer budget consequences

The implementation must measure generated assets against current Aura admission limits before
selecting a committed publication strategy. Current source enforces bounded GLB and SPZ decode,
primitive, point, allocation, and frame budgets. Therefore `LOW`, `STANDARD`, and `VIDEO`
profiles are ceilings subject to importer acceptance—not promises that every proposed count will
be admitted.

## Architecture defects found during G0

### 1. Unqualified method source-reference compatibility

The Compass evidence spine emitted an exact source reference such as
`aura_agent_arena_bridge.py#aura_find_affordances`, while the current Relational Index stores the
qualified participant symbol `AuraAgentArenaBridge.aura_find_affordances`. The fallback resolver
still required exact symbol equality, so the source reference resolved zero participants despite
matching file, line span, symbol hash, and file hash.

A narrow patch was prepared and regression-tested:

- permit an unqualified symbol to match `Class.method` only when the requested symbol itself is
  unqualified;
- continue requiring exact file, line start/end, source hash, optional file hash, and a unique
  final resolution;
- apply the same rule to the legacy compatibility resolver;
- add canonical and legacy regression tests.

Verification: 89 relational-index/Compass/finalization tests passed. The patch is recorded as a
separate PR-visible artifact until it is applied to canonical source.

### 2. Emergent input projection pressure

A Construction-wide Compass neighborhood can satisfy node/edge/pair bounds but exceed the
Emergent scanner's 512 KiB canonical input ceiling because full participant metadata is passed to
a scanner that needs only identities, roles, exact evidence refs/hashes/tests, relation endpoints,
and Atlas dispositions.

For G0 analysis, the Construction Compass is partitioned into three owner-bounded packets and a
read-only compatibility projection removes unrelated metadata before Emergent discovery. The
full neighborhood remains intact for Atlas, Change Graph, and verification. This is evidence for
a future general harness hardening patch; it is not treated as canonical runtime behavior.

## Prohibitions carried forward

- no duplicate Construction ledger, project-state owner, renderer, event store, checkpoint
  engine, Observatory, Agent Bridge, or authority path;
- no survey-authoritative geometry or coordinates;
- no real-person identity, worker tracking, raw sensor payload, or vulnerability data;
- no physical-work, payment, access, equipment, professional, legal, engineering, regulatory, or
  production authority;
- no external hosted viewer, runtime asset fetch, iframe, or unrestricted WebXR activation;
- no importer bypass;
- no automatic restore, automatic commit, automatic merge, or automatic release;
- status remains a separate overlay and never mutates base geometry;
- `DECIDE` emits a human/domain decision packet and never applies it;
- `DISSOLVE` requires exact renderer-bound cleanup evidence.

## G0 disposition

```yaml
architecture_harness_complete: true
canonical_owner_map_locked: true
dependency_classes_locked: true
source_and_license_route_locked: true
council_v3_route_locked: true
compass_resolver_patch_prepared: true
compass_bundle_status: IN_PROGRESS_AT_DOCUMENT_CREATION
code_mutation_authorized_by_harness: false
implementation_may_proceed_under_human_instruction: true
next_gate: G1_SOURCE_AND_IMMUTABLE_ASSET_CONTRACTS
```

# AuraOS Intent-Native Spatial Workspace — PR1

## Contracts and frozen Coding Spatial Workspace vertical slice

**Base:** `879b5fb056b70d150b1646e082223330a36c2912`  
**Allowed-path-set digest:** `903d3ac371968dfff15ff57eb406bf960fd9bb483660cd983ce25c87c2652d81`  
**Terminal state:** `READY_FOR_HUMAN_REVIEW`

## Decision

PR1 adds a single contract-only compatibility module. It does **not** modify the existing Ephemeral Organ V1 manifest, Spatial contracts, Compass, Forge, Unified Memory and Continuity, Waboose, Runtime Harness, renderer, or domain owners.

The new layer compiles and validates immutable references. It does not activate a workspace, call an adapter, invoke a renderer or model, write a project store, mutate source/domain state, publish, or merge.

## Exact objective

Establish deterministic, versioned compatibility contracts for an intent-compiled ephemeral spatial workspace and freeze the `CODING_SPATIAL_WORKSPACE_V1` demonstration recipe without operational behavior.

## Canonical-owner matrix

| Concern | Canonical owner preserved | PR1 action |
|---|---|---|
| Existing temporary-organ manifest | `aura_ephemeral_manifest` | Wrap by exact reference and digest; never modify V1 |
| Temporary activation and dissolution | `aura_ephemeral_runtime` | Reference only; no activation API in PR1 |
| Project evidence and continuity | Existing repository/domain owners and Unified Memory/Continuity | Compile a minimum-sufficient reference projection |
| Spatial scene and interaction truth | Existing Spatial contracts and Arena | Bind exact scene/session/entity digests only |
| Code intelligence | Coding Relationship Compass | Declare a capability/adaptor reference only |
| Code candidate lifecycle | Forge | Prepare-handoff capability only; no direct edit capability |
| Semantic review | Coding Waboose | Commit a bounded review request |
| Runtime proof | Runtime Refactor Harness | Declare a required gate only; no runtime execution in the contract module |

## New immutable contracts

### `ProjectContextProjection`

A read-only, projection-only record containing repository identity plus exact canonical references for artifacts/evidence, decisions, rejected alternatives, unresolved questions, assumptions, capabilities, relationships, blockers, and next actions. It creates no project database and copies no canonical truth.

### `EphemeralWorkspaceRecipe`

A versioned wrapper over an exact V1 organ-manifest reference. It binds the canonical intent digest, project projection digest, capability dependency graph, adapter/evidence identities, owner handoff map, bounded resources, renderer/device requirements, allowed interaction actions, verification gates, TTL, and mandatory dissolution policy.

### `SpatialReferentBinding`

An exact scene/session/entity candidate binding with confidence, evidence reference, input sources, and its own deterministic digest.

### `MultimodalSpatialObservation`

A privacy-minimized normalized event that may identify voice, hand, gaze, ray, touch, keyboard, and controller sources. Raw camera, audio, joint, gaze-stream, room-scan, and related payload aliases are rejected. The record has no authority.

### `AuthorityEnvelope`

Every mutation, renderer, sensor, model, execution, persistence, deployment, physical-work, payment, professional, patch, VSA patch, commit, push, pull-request, merge, resume, persistence, and promotion authority remains false. Projection-only, review-only, and human-review-required remain true.

## Frozen `CODING_SPATIAL_WORKSPACE_V1`

The demonstration recipe declares only bounded capabilities:

- compile an existing Compass packet;
- fetch a bounded exact neighborhood;
- open exact source slices;
- display tests and schemas;
- compile candidate Change Graphs;
- prepare a governed Forge handoff;
- read verification status;
- display admitted Attempt Archive evidence;
- dissolve the workspace.

No direct edit or write capability is present. Consequential code work remains owned by Forge and exact-source verification lanes.

## Frozen Change Graph

```text
EphemeralOrganManifest V1
  --wrapped_by_reference--> EphemeralWorkspaceRecipe V1

canonical repository/domain/continuity records
  --minimum-sufficient references--> ProjectContextProjection V1

normalized multimodal provider events
  --privacy-minimized binding--> MultimodalSpatialObservation V1

exact scene + session + entity identity
  --digest binding--> SpatialReferentBinding V1

CODING_SPATIAL_WORKSPACE_V1
  --handoff only--> Compass / Forge / Waboose / Runtime Harness
```

Prohibited relationships include direct source mutation, direct domain mutation, rendered-state authority, raw-sensor retention, automatic persistence/resume/promotion, arbitrary native/browser execution, and any second truth/routing/planning/verification/persistence/policy/authority plane.

## Validation and stale-identity behavior

Every contract has exact-key parsing, deterministic canonical JSON, and BLAKE2b-256 identity. Binding checks fail closed for stale or mismatched:

- repository and source-tree identities;
- project reference and projection digest;
- base V1 manifest digest;
- canonical intent digest;
- adapter and evidence reference sets/digests;
- scene, session, and entity identities;
- freshness classes;
- capability dependency cycles.

Draft 2020-12 schemas mirror the Python contract and make the no-authority envelope executable at schema validation time.

## Focused verification

The focused suite covers:

1. exact V1 object, canonical JSON, and `compute_digest()` compatibility after wrapping;
2. exact project, recipe, referent, and observation round-trips;
3. nested authority-alias rejection;
4. raw-sensor-payload rejection;
5. all required stale identity classes;
6. dependency-cycle rejection;
7. schema validation and authority-tamper rejection;
8. AST proof that the contract module imports only stdlib and invokes no operational or persistence APIs.

## Harness evidence disclosure

The work was bound to the exact GitHub main commit and current canonical source blobs through the connected repository interface. The execution environment could not materialize the full repository checkout, so it could not honestly claim a completed local `prepare`, `doctor`, Harness run, Compass packet, Council receipt, Waboose execution, or full repository regression suite. The frozen owner matrix and Change Graph therefore remain exact-source-guided implementation evidence, not a fabricated Harness-runtime receipt. Repository CI and the requested current-head external deep reviews are retained as separate evidence.

## Allowed paths

```text
aura_ephemeral_workspace_contracts.py
schemas/aura_project_context_projection.schema.json
schemas/aura_ephemeral_workspace_recipe.schema.json
schemas/aura_multimodal_spatial_observation.schema.json
tests/test_aura_ephemeral_workspace_contracts.py
docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md
.aura/refactor_objectives/intent_native_spatial_workspace_pr1.v1.json
.aura/waboose_requests/intent_native_spatial_workspace_pr1.v1.json
```

No CODEMAP, topology, runtime-memory, existing V1 source, operational UI, renderer, or lifecycle source is changed.

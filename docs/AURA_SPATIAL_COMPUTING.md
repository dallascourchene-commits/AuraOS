# Aura Spatial Computing Substrate — S0–S2

Status: **implementation slice on `feature/aura-spatial-s0-s2`**  
Authority: **projection-only; no patch, execution, commit, push, merge, or promotion authority**

## Purpose

Aura's spatial layer is an additive, representation-independent projection substrate. It lets existing Aura domains expose bounded scenes without creating a second truth system.

```text
canonical domain truth
  → bounded domain adapter
  → immutable SpatialSceneSnapshot
  → replaceable renderer/device adapter
  → human or agent interaction
  → six-slot review-only Aura intent
  → existing domain Arena / Forge / Gate / human review
```

The spatial substrate owns scene snapshots, coordinate frames, content-addressed asset manifests, projected entities and links, renderer hints, and interaction receipts. It does **not** own code truth, civic truth, construction truth, identity, governance, source mutation, or promotion.

## Coding Circuit and Council V3 basis

The implementation follows the Coding Waboose breadboard architecture introduced in July 2026:

- typed component inputs and outputs;
- exact connected evidence references;
- explicit mocks for unavailable renderer, Gaussian-splat runtime, and device signals;
- forward consequence paths;
- backward proof requirements;
- BC0–BC5 continuity;
- human authorization separated from planning and verification.

`aura_spatial_breadboard.py` compiles the S0–S2 work into a proposal-only Planning Board. It also replays Council V3's deterministic critic routing over the plan profile. The plan has ten tasks, explicit dependencies, two large components, rollback conditions, and a risk map, so Council V3 selects all six lanes:

```text
scope → tests → sequence → continuity → rollback → cost
```

The route replay does not claim that native model calls occurred. It records the exact critic lanes and requirements applied during implementation.

## Canonical modules

| Module | Responsibility | Explicit non-responsibility |
|---|---|---|
| `aura_spatial_contracts.py` | Immutable scene, frame, asset, entity, link, and interaction contracts | Rendering, scanning, mutation |
| `aura_spatial_coordinate_frames.py` | Rooted frame-graph validation and deterministic transform resolution | SLAM, tracking, sensor fusion |
| `aura_spatial_asset_registry.py` | Content-addressed manifest validation | Network fetch, decode, training, rendering |
| `aura_spatial_scene.py` | Deterministic scene compilation and referential-integrity verification | Domain truth ownership |
| `aura_spatial_projection.py` | Coding Arena and showcase compatibility projection | Second topology scanner |
| `aura_spatial_interaction.py` | Six-slot review-only intent compilation and hotswap guard | Direct hotswap or patch execution |
| `aura_spatial_breadboard.py` | Council V3 route replay and typed S0–S2 implementation circuit | Patch or merge authority |

## Truth classes

Every spatial record declares one of four truth classes:

- `EXACT` — direct domain evidence, such as an exact source reference;
- `DERIVED` — deterministic transformation of canonical records;
- `PRESENTATION` — layout or renderer-facing state;
- `HYPOTHESIS` — unverified spatial suggestion.

A truth class does not grant authority. Even an `EXACT` source reference inside a scene remains read-only until the canonical domain owner and its governance path authorize action.

## Coordinate frames

`CoordinateFrame` records declare:

- stable frame identity and optional parent;
- handedness and up axis;
- meters-per-unit scale;
- translation, normalized quaternion, and positive scale;
- exact source references and truth class;
- `projection_only=true`.

Validation fails closed on:

- duplicate frame IDs;
- any attempt to set `projection_only=false`;
- missing parents;
- cycles;
- roots with parents;
- frames not connected to the declared root;
- non-finite values;
- zero quaternions;
- non-positive scale or unit conversion.

## Assets

`SpatialAssetManifest` is content-addressed and immutable. S0–S2 supports manifest types for topology graphs, meshes, point clouds, Gaussian splats, voxels, signed-distance fields, planes, and annotations. This does not mean every representation has a renderer yet.

The registry:

- validates `sha256` or `blake2b-256` digests;
- validates byte length when bytes are supplied;
- blocks remote HTTPS assets unless an explicit fetch policy admits them;
- rejects unsafe relative paths and unsupported URI schemes;
- never fetches, decodes, trains, or renders an asset.

## Scene snapshots

`SpatialSceneSnapshot` is deterministic across equivalent input order. Compilation sorts frames, assets, entities, and links by stable identity and then verifies:

- rooted frame continuity;
- asset-frame references;
- entity-frame and entity-asset references;
- link endpoints;
- duplicate identifiers;
- fixed authority fields.

Metadata is sanitized through Aura's canonical event sanitizer: secret-shaped fields are redacted and private-reasoning fields are rejected before scene hashing.

Metadata is sanitized through Aura's canonical event sanitizer: secret-shaped fields are redacted and private-reasoning fields are rejected before scene hashing.

Every snapshot carries:

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
execution_authority: false
```

## Coding Arena adapter

`project_coding_topology_to_scene()` calls the existing `aura_coding_arena_3d.select_micro_arena()` owner. It does not scan the repository or build an alternative call graph.

The adapter:

- keeps the existing bounded depth and token budget;
- preserves exact topology/source references in entity metadata;
- converts coordinates into presentation-only frame state;
- creates a content-addressed topology-graph asset manifest from the same bounded node/link projection, never the unbounded pre-truncation neighborhood;
- records pre-bound source counts and explicit truncation without serializing discarded topology into the asset evidence;
- prioritizes exact selected nodes before applying the bounded node cap;
- preserves only links whose endpoints remain inside the bounded node closure;
- marks every entity `projection_only=true` and `patch_authority=false`;
- requires a 2D accessible fallback through renderer hints.

`project_showcase_workspace_to_scene()` is a compatibility adapter over successful `aura_showcase_spatial` workspace packets.

## Interaction and legacy hotswap boundary

Spatial UI actions compile into exact six-slot Aura intents:

```text
DIR · ASP · CLASS · SUBJ · VOICE · STEM
```

Selection, focus, expansion, contraction, and source navigation remain review-only. A request to change code compiles as `PREPARE_REPAIR_REQUEST` and requires Aura Forge.

`compile_hotswap_request_guard()` deliberately returns:

```yaml
ok: false
status: REQUIRES_GOVERNED_REPAIR_HANDOFF
queued: false
success: false
next_owner: aura_forge
```

It never reports that a hotswap was queued merely because a WebSocket message was accepted. The legacy AR bridge now calls the guard against its current bounded shape state, returns `HOTSWAP_REVIEW_REQUIRED` only to the requesting session, retains only a redacted proposal digest, and does not broadcast success or refresh topology as though a mutation occurred.

## Explicitly deferred work

These are explicit breadboard mocks, not implementation claims:

- WebXR/OpenXR renderer and session adapter;
- Gaussian-splat import/render runtime;
- device anchors, gaze, gesture, controller, and sensor adapters;
- OpenUSD scene interchange;
- Gaussian-splat training or capture;
- civic, construction, observatory, and life-OS domain adapters beyond the Coding Arena compatibility slice.

They belong in S3–S7 after the core contracts are verified.

## Verification

Focused tests cover:

- finite transforms and quaternion normalization;
- cycles, missing parents, and unrooted frames;
- transform composition;
- asset digest, length, path, and remote-policy validation;
- deterministic scene digests;
- dangling frame, asset, entity, and link references;
- spatial patch-authority rejection;
- Coding Arena micro-topology reuse and bounded closure;
- exact six-slot interaction compilation;
- fail-closed hotswap semantics;
- Council V3 all-lane routing;
- BC4 unpowered and BC5 verifier-bound breadboard continuity.

Run:

```bash
pytest -q tests/test_aura_spatial_substrate.py
python -m py_compile \
  aura_spatial_contracts.py \
  aura_spatial_coordinate_frames.py \
  aura_spatial_asset_registry.py \
  aura_spatial_scene.py \
  aura_spatial_projection.py \
  aura_spatial_interaction.py \
  aura_spatial_breadboard.py
```

## Implementation boundary for this pull request

The first pull request should remain S0–S2:

1. canonical contracts;
2. coordinate-frame validator;
3. asset registry;
4. immutable scene compiler;
5. Coding Arena/showcase adapters;
6. interaction compiler and hotswap guard;
7. Coding Circuit/Council V3 receipt;
8. adversarial tests and schema;
9. bounded bridge integration;
10. generated CODEMAP/topology refresh only after source tests pass.

Renderer selection and advanced spatial representations are intentionally excluded from this merge.

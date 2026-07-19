# Aura Spatial Computing Substrate — S0–S2

Status: **implementation slice on `feature/aura-spatial-s0-s2`**  
Authority: **projection-only; no patch, execution, commit, push, pull-request, merge, or promotion authority**

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

The implementation follows the Coding Waboose breadboard architecture:

- typed component inputs and outputs;
- exact connected evidence references;
- explicit mocks for unavailable renderer, Gaussian-splat runtime, and device signals;
- forward consequence paths;
- backward proof requirements;
- BC0–BC5 continuity;
- human authorization separated from planning and verification.

`aura_spatial_breadboard.py` compiles the S0–S2 work into a proposal-only Planning Board and replays Council V3's deterministic critic routing over the plan profile. The route replay selects scope, tests, sequence, continuity, rollback, and cost. It does not claim native Council model calls occurred.

A breadboard BC5 state is a circuit-continuity representation, not independent proof that repository tests ran. Repository-native verifier evidence must remain externally attributable to exact commands, commits, and outputs.

## Canonical modules

| Module | Responsibility | Explicit non-responsibility |
|---|---|---|
| `aura_spatial_contracts.py` | Immutable scene, frame, asset, entity, link, and interaction contracts | Rendering, scanning, mutation |
| `aura_spatial_coordinate_frames.py` | Rooted frame-graph validation and deterministic transform resolution | SLAM, tracking, sensor fusion |
| `aura_spatial_asset_registry.py` | Content-addressed manifest validation | Network fetch, decode, training, rendering |
| `aura_spatial_scene.py` | Deterministic scene compilation and referential-integrity verification | Domain truth ownership |
| `aura_spatial_projection.py` | Coding Arena and showcase compatibility projection | Second topology scanner |
| `aura_spatial_interaction.py` | Six-slot review-only intent compilation and hotswap guard | Direct hotswap or patch execution |
| `aura_spatial_ws_guard.py` | Bounded, requesting-session-only legacy bridge handoff | Executing or retaining proposed code |
| `aura_spatial_breadboard.py` | Council V3 route replay and typed S0–S2 implementation circuit | Patch or merge authority |

## Truth classes

Every spatial record declares one of four truth classes:

- `EXACT` — direct domain evidence, such as an exact source reference;
- `DERIVED` — deterministic transformation of canonical records;
- `PRESENTATION` — layout or renderer-facing state;
- `HYPOTHESIS` — unverified spatial suggestion.

A truth class does not grant authority. Even an `EXACT` source reference inside a scene remains read-only until the canonical domain owner and its governance path authorize action.

## Coordinate frames

`CoordinateFrame` records declare stable identity, optional parent, handedness, up axis, meters-per-unit, translation, normalized quaternion, positive scale, source references, truth class, and `projection_only=true`.

Validation fails closed on duplicate IDs, missing parents, cycles, roots with parents, unrooted frames, non-finite values, zero quaternions, non-positive scale or unit conversion, and implicit handedness/up-axis changes. A basis change requires an explicit future conversion transform rather than silent reinterpretation. World-transform resolution applies each frame's `unit_scale_meters` before composing parent scale and rotation.

## Assets

`SpatialAssetManifest` is content-addressed and immutable. S0–S2 defines manifest types for topology graphs, meshes, point clouds, Gaussian splats, voxels, signed-distance fields, planes, and annotations. Defining a type does not claim that a renderer exists.

The registry:

- validates `sha256` or `blake2b-256` digests and byte length when bytes are supplied;
- uses constant-time digest comparison;
- blocks remote HTTPS assets unless explicitly admitted;
- rejects credentials, parameters, queries, fragments, control characters, backslashes, encoded traversal, unsafe authorities, and unsupported schemes;
- never fetches, decodes, trains, or renders an asset.

## Scene snapshots

`SpatialSceneSnapshot` compilation canonicalizes set-like source references and asset references, sorts frames/assets/entities/links by stable identity, and verifies rooted frame continuity, asset and entity references, link endpoints, duplicate identifiers, and fixed authority fields.

Metadata is sanitized through Aura's canonical event sanitizer: secret-shaped fields are redacted and private-reasoning fields are rejected before scene hashing. Affirmative authority claims embedded in entity, asset, link, or renderer metadata fail closed.

Every snapshot carries:

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
execution_authority: false
```

The `patch_authority` string is a policy boundary: only exact source spans and hashes can participate in a later governed patch workflow. It does not grant the spatial scene patch authority.

## Coding Arena adapter

`project_coding_topology_to_scene()` calls the existing `aura_coding_arena_3d.select_micro_arena()` owner. It does not scan the repository or build an alternative graph.

The adapter:

- bounds depth, token budget, selected nodes, retained nodes, retained links, field lengths, and canonical serialized evidence;
- keeps a maximum 128 nodes, 320 links, and 1 MiB canonical projection payload;
- allowlists retained topology fields before hashing, so arbitrary node/link metadata cannot enter bounded evidence;
- preserves selected nodes before the node cap;
- sorts eligible links deterministically before the link cap;
- creates a content-addressed topology asset from exactly the retained bounded projection;
- records source counts and truncation without serializing discarded payloads;
- marks entities projection-only with no patch authority;
- requires a 2D accessible renderer fallback.

`project_showcase_workspace_to_scene()` remains a compatibility adapter over successful `aura_showcase_spatial` workspace packets.

## Interaction and legacy hotswap boundary

Spatial actions compile into exactly six Aura slots:

```text
DIR · ASP · CLASS · SUBJ · VOICE · STEM
```

Selection, focus, expansion, contraction, and source navigation remain review-only. A code-change request compiles as `PREPARE_REPAIR_REQUEST` and requires Aura Forge. Caller metadata cannot override protected authority fields, actor references are bounded, and set-like targets and evidence references are canonicalized before digesting.

`compile_hotswap_request_guard()` deliberately returns `ok=false`, `queued=false`, `success=false`, and `next_owner=aura_forge`. The legacy AR bridge returns `HOTSWAP_REVIEW_REQUIRED` only to the requesting session and does not broadcast success or refresh topology as though a mutation occurred.

The WebSocket handoff sanitizes the proposal, retains only a digest, applies a 256 KiB canonical payload limit, bounds identifiers and labels, rejects unsafe source paths, and never executes the proposed function.

## Schema and verification boundary

The JSON schema is Draft 2020-12. The focused workflow is required to:

- check the schema against the Draft 2020-12 meta-schema;
- validate a compiled canonical scene;
- confirm that an authority-bearing negative fixture is rejected;
- compile and lint all spatial modules and focused regression files;
- run focused spatial, bridge, bounded-payload, and showcase compatibility tests.

Historical verifier results belong to the exact commit on which they ran. Source changes after that commit require fresh evidence before the PR may claim those results apply to the new head.

## Explicitly deferred work

These remain explicit mocks, not implementation claims:

- WebXR/OpenXR renderer and session adapter;
- Gaussian-splat import, rendering, training, or capture;
- device anchors, gaze, gesture, controller, and sensor adapters;
- OpenUSD scene interchange;
- civic, construction, observatory, and life-OS adapters beyond the Coding compatibility slice.

They belong in S3–S7 after the core contracts and evidence boundary are accepted.

## S0–S2 implementation boundary

1. canonical contracts;
2. coordinate-frame validator;
3. asset registry;
4. immutable scene compiler;
5. Coding Arena/showcase adapters;
6. interaction compiler and hotswap guard;
7. Coding Circuit/Council V3 receipt;
8. adversarial tests and Draft 2020-12 schema;
9. bounded bridge integration;
10. generated CODEMAP/topology refresh only after source verification.

Renderer selection and advanced spatial representations remain outside this slice.

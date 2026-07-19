# Aura Spatial Computing Substrate — S0–S4-A

Status: **S0–S4-A implementation with browser projection and bounded interchange**
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

- native OpenXR and persistent WebXR anchor adapters;
- Gaussian-splat import, rendering, training, or capture;
- gaze, gesture, controller, camera, and unrestricted sensor adapters;
- compressed glTF extensions such as Draco, meshopt, and KTX2;
- OpenUSD scene interchange;
- civic, construction, observatory, and life-OS adapters beyond the Coding compatibility slice.

They belong in later independently reviewable stages after the browser and core-interchange evidence boundaries are accepted.

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

## S3-A renderer-independent continuation

S3-A adds negotiation and lifecycle contracts without implementing a browser renderer. The retained scene snapshot remains the source-bound projection record; device, render-plan, session, and receipt packets only describe how that immutable scene may be presented within explicit budgets.

### Device profiles and render plans

`SpatialDeviceProfile` records a bounded, non-fingerprinting capability summary. It admits only canonical renderer identifiers and always requires `ACCESSIBLE_2D`. Raw sensor data, user-agent strings, hardware serials, stable cross-session identifiers, and unrestricted device metadata are outside the contract.

`negotiate_spatial_render_plan()` deterministically intersects the scene, device profile, caller preference, and request budget. It:

- binds the exact scene and device-profile digests;
- applies the lower of device and request ceilings for entity, link, asset, asset-byte, CPU, GPU, and network budgets;
- selects only an admitted renderer;
- retains `ACCESSIBLE_2D` as a mandatory fallback;
- admits `WEBXR` only when XR was explicitly requested and user activation was observed;
- emits reasons for rejected or unavailable choices;
- never fetches assets, allocates a renderer, starts an XR session, or grants execution authority.

The render plan is deterministic interchange evidence. Renderer order, fallback order, counts, budgets, reasons, and source references are canonicalized before its digest is computed.

### Projection sessions and receipts

`SpatialProjectionSessionManager` owns bounded in-memory session lifecycle state. A session is bound to one exact scene digest, one exact device-profile digest, and one exact render-plan digest. It is ephemeral, carries no raw sensor data, and cannot outlive explicit cancellation, failure, or dissolution.

Render outcomes are recorded as immutable `SpatialRenderReceipt` packets with explicit evidence classes: measured, derived, estimated, or unavailable. A receipt may describe presentation evidence, but it cannot prove domain truth or authorize a mutation. `SpatialDissolutionReceipt` records terminal state, lease release, zero raw-sensor retention, and `renderer_disposed=false` until a future client-acknowledgement contract can bind renderer cleanup evidence to the session. Dissolution removes the active server session without overclaiming browser disposal.

### Bounded HTTP surface

`aura_spatial_server.py` exposes a renderer-independent API surface:

```text
GET  /api/spatial/capabilities
POST /api/spatial/scenes
GET  /api/spatial/scenes/{scene_id}
POST /api/spatial/render-plans
POST /api/spatial/sessions
GET  /api/spatial/sessions/{session_id}
GET  /api/spatial/projections/{session_id}
POST /api/spatial/interactions
POST /api/spatial/telemetry
POST /api/spatial/sessions/{session_id}/renders
POST /api/spatial/sessions/{session_id}/cancel
POST /api/spatial/sessions/{session_id}/dissolve
```

Requests are bounded before expensive processing. Responses are also byte-bounded and use `Cache-Control: no-store`, a restrictive Content Security Policy, same-origin resource policy, no-referrer, and MIME sniffing protection. API responses disable camera, microphone, geolocation, motion sensors, and XR spatial tracking. The allowlisted `/spatial` browser surface serves only local static assets and permits same-origin WebXR solely for the explicit-gesture capability path; it never serves remote assets.

### Aura-native continuation harness

`scripts/aura_spatial_continuation_architect_harness.py` runs the S3-A circuit through retained Aura owners:

1. Coding Arena and Agent Bridge preparation;
2. Capability Connectome and atomic-function inventory;
3. Emergent Properties evidence;
4. all justified Council V3 critic lanes;
5. proposal-only Surgeon control;
6. Coding Waboose exact-range review;
7. Crucible replay of learned review lessons;
8. scene-to-plan-to-session-to-dissolution lifecycle proof;
9. browser renderer/accessibility/telemetry proof;
10. bounded glTF/GLB and PLY interchange proof.

The receipt binds the observed repository head and distinguishes current execution from workflow configuration. A workflow file is not evidence that a check passed until GitHub reports a completed run against that exact head.

### S3-A authority boundary

Every public S3-A device profile, render plan, render receipt, and session summary preserves the following boundary:

```yaml
renderer_authority: false
execution_authority: false
patch_authority: false
```

`SpatialDissolutionReceipt` additionally fixes `production_mutation: false` and `automatic_merge: false`. S4-A import receipts carry the broader review-only evidence envelope, including `human_review_required: true` and `patch_authority: exact_source_spans_and_hashes_only`.
Device-profile metadata and render-receipt metrics are capped at four nested containers and 128 entries per container, matching their public schemas.

Device capabilities, renderer selection, session state, visual selection, measured frame data, and dissolution receipts cannot become domain truth, patch authority, execution authority, merge authority, promotion authority, or production authority.

## S3-B browser vertical slice

S3-B consumes the S3-A scene, device, render-plan, session, and receipt contracts without creating a second scene owner. The browser implementation is replaceable and renderer-neutral at its boundary:

- `renderer_adapter.js` validates immutable scene and render-plan packets and preserves a fixed no-authority envelope;
- `headless_renderer.js` supplies deterministic CI and fallback behavior;
- `accessibility.js` generates keyboard-first, screen-reader-compatible 2D parity from the same scene entities and interactions;
- `webgl2_renderer.js` provides the active browser canvas path with bounded point/link buffers, picking, camera state, and deterministic disposal;
- `webgpu_renderer.js` remains a shadow adapter and cannot self-promote after success or device recovery;
- `webxr_session.js` exposes capability-only immersive entry and rejects every request lacking an observed explicit user activation;
- `interaction_adapter.js` compiles browser selection and navigation into the retained six-slot review-only intent contract;
- `telemetry.js` accepts only measured, calculated, estimated, or unavailable evidence bound to exact scene, device, renderer, and browser-fixture digests;
- `bootstrap.js` loads one exact active projection session, sends review-only interactions, records bounded telemetry, and exposes WebXR only through a direct user gesture.

The browser server surface is allowlisted and content-bound through the capability packet's `browser_fixture_digest`. Traversal, symlinks, oversized files, arbitrary directory reads, remote scripts, and remote assets are rejected. Renderer disposal clears retained GPU/session resources; WebXR does not retain raw sensor frames or create stable cross-session device identifiers.

## S4-A bounded core interchange

S4-A introduces import contracts and two local-only importers. Imported data is a derived projection asset, never source provenance or renderer authority.

### glTF 2.0 and GLB

`aura_spatial_importers.gltf` accepts bounded static triangle meshes with float32 `POSITION` data and bounded unsigned indices. It accepts only embedded canonical buffer data or the declared GLB BIN chunk. It rejects remote or path-based URIs, duplicate JSON keys, required extensions, animation, skins, cameras, images, scripts, executable extras, sparse accessors, unsupported strides, and out-of-range buffer views.

The glTF basis is explicitly converted from right-handed Y-up meters into Aura's canonical right-handed Y-up meter frame. No network fetch, shader execution, decompression plugin, or training path exists.

### PLY point clouds

`aura_spatial_importers.ply` accepts bounded ASCII, little-endian binary, and big-endian binary vertex-only point clouds. The caller must provide an explicit source handedness, up axis, and meters-per-unit conversion. Faces, list properties, undeclared properties, non-finite coordinates, mismatched payload sizes, symlinks, and files outside the admitted local root fail closed.

### Import receipts

Every successful import emits a strict Draft 2020-12 `SpatialImportReceipt` containing source digest, decoded byte count, primitive bounds/counts, coordinate-conversion matrix, provenance references, warnings, and a derived asset digest. Runtime reconstruction must reproduce the exact canonical payload. The receipt fixes all of the following boundaries:

```yaml
local_only: true
scripts_executed: false
shaders_executed: false
network_fetch_performed: false
training_invoked: false
projection_only: true
provenance_authority: false
renderer_authority: false
execution_authority: false
patch_authority: false
production_mutation: false
automatic_merge: false
human_review_required: true
```

## Still deferred after S4-A

The following remain outside the implemented boundary:

- native OpenXR, persistent anchors, gaze, gesture, controller, camera, and unrestricted sensor adapters;
- KTX2, Draco, meshopt, arbitrary glTF extensions, and external buffer/image resolution;
- Gaussian-splat, voxel, SDF, reconstruction, capture, and training pipelines;
- Spatial Arena and Agent Bridge public tool registration;
- civic, construction, observatory, life-OS, and other domain adapters;
- OpenUSD interchange.

Later stages must consume the retained scene, plan, session, receipt, renderer, and import contracts rather than replacing their truth or authority boundaries.

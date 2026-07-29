# Aura Pascal Spatial Presentation — PR 2

## Purpose

PR 2 adds a pinned, local, disposable Pascal presentation organ beneath Aura's existing Construction and Spatial owners. It does **not** create a second Construction truth store, renderer authority, routing engine, evidence ledger, approval plane, persistence plane, or learning path.

The PR extends the PR 1 composed Construction Spatial Foundry. When the Pascal compatibility assets are absent or invalid, the PR 1 server, APIs, and browser surface remain available and Pascal fails closed as unavailable.

## Exact Pascal identity

The compatibility boundary is pinned to:

- repository: `pascalorg/editor`
- commit: `42ac4be1ce5f3fee74806aa093267b6fee77d47d`
- license: MIT, Copyright (c) 2026 Pascal Group Inc.
- `@pascal-app/core`: `0.9.2`
- `@pascal-app/viewer`: `0.9.2`
- `@pascal-app/editor`: `0.9.2`
- `@pascal-app/nodes`: `0.1.1`

`third_party/pascal/pascal-lock.json` binds each approved upstream `package.json` by its exact Git blob SHA-1, and binds every committed local compatibility asset and package-identity summary by SHA-256. The retained MIT notice is at `third_party/pascal/LICENSE`.

Pascal's public editor surface is React/Next based and its viewer can resolve CDN assets. The recordable Aura MVP requires a vanilla, no-external-network, same-origin child surface. PR 2 therefore keeps the upstream source identity exact while placing a narrow local compatibility renderer behind contracts that can later receive an exact prebuilt Pascal package bundle without changing Aura's ownership, bridge, session, or receipt semantics.

## Canonical ownership

Aura continues to own:

- bilateral intent and confirmation;
- Construction project state, events, claims, evidence, conflicts, and authority routing;
- Spatial scenes, render plans, interaction compilation, proof, and dissolution;
- guarded transition admission;
- exact repository/runtime identity;
- Attempt Archive, reproof, and human/community disposition.

The Pascal organ owns only one ephemeral browser working copy:

- local fixture geometry;
- current 2D or 3D presentation;
- selected storey and node;
- dimensions visibility;
- disposable canvas and browser listeners.

All authority fields remain false. Visual alignment is not survey truth. `READY_FOR_HUMAN_REVIEW` is not approval.

## Contracts

### `PascalSourceLock`

Binds the approved repository, commit, package versions, package metadata blob identities, license, local asset hashes, and no-network/no-canonical-storage policy.

### `PascalSceneArtifactManifest`

Binds one scene fixture to the source lock, raw scene bytes, storeys, one-to-one Pascal node/Aura entity mappings, and working-copy-only lifecycle constraints.

### `AuraPascalCoordinateReceipt`

Binds the artifact to one canonical Spatial compatibility scene, coordinate frames, identity transform, units, and deterministic node mapping. It is explicitly visual-alignment-only and grants neither survey nor Construction authority.

### `AuraPascalPresentationBridgeV1`

Every message binds:

- exact session;
- monotonic direction-specific sequence;
- one-time nonce;
- Spatial scene digest;
- render-plan digest;
- Pascal artifact digest;
- coordinate receipt digest;
- guarded presentation-state digest;
- exact UTC send timestamp;
- direction, action, bounded payload, and message digest.

The bridge rejects wrong origin, wrong session, stale identity, sequence gaps, replayed nonces, digest tampering, unknown actions, oversized/deep payloads, hidden-storey selection, unsupported authority fields, missing child receipts, and all post-dissolution messages.

Explicit false authority boundaries may cross the bridge so the child can display and preserve them; positive authority claims fail closed.

## Guarded lifecycle

```text
CREATED
  -> child READY receipt
READY
  -> server-issued LOAD_ARTIFACT
  -> exact child LOAD_RECEIPT
ACTIVE
  -> server-issued view/storey/selection/dimensions/reset command
  -> exact VIEW_STATE or SELECTION_CHANGED receipt
  -> exact RENDER_RECEIPT
ACTIVE
  -> server-issued DISSOLVE
  -> exact child DISSOLUTION_RECEIPT
DISSOLVED
  -> same-origin parent removes iframe
  -> retained parent cleanup observation
```

Only one parent command can be pending. Its exact digest must appear in the corresponding child receipt. The server does not move to `ACTIVE` or `DISSOLVED` merely because it issued a command.

## Six-slot routing

Every accepted parent command and child receipt is compiled through `aura_spatial_interaction.compile_spatial_interaction`. The result must contain exactly:

```text
DIR -> ASP -> CLASS -> SUBJ -> VOICE -> STEM
```

The PR 2 session grammar is a bounded lifecycle extension. It names the existing Spatial interaction compiler as its base owner and grants no state, execution, patch, Construction, or approval authority.

## Browser boundary

The parent is the existing Showcase-composed Spatial Foundry. It mounts:

```text
sandbox="allow-scripts allow-same-origin"
```

The child accepts messages only from its exact loopback `location.origin` and exact parent window. The child contains no remote script, stylesheet, model, texture, plugin, or font URL. `fetch`, `XMLHttpRequest`, and `WebSocket` are blocked inside the workbench and counted as external-request violations.

The deterministic local fixture supports:

- floor-plan 2D;
- isometric 3D;
- two storeys with isolation;
- deterministic room selection;
- dimension visibility;
- reset;
- child renderer/listener/timer/buffer/IndexedDB dissolution;
- parent iframe removal and relaunch.

## Run

```bash
python aura_construction_pascal_spatial_foundry_server.py \
  --repo-root . \
  --host 127.0.0.1 \
  --port 8000
```

Open the exact loopback URL printed by the server. Using a different hostname intentionally fails the same-origin session binding.

## Verification

Focused verification:

```bash
python -m py_compile \
  aura_pascal_spatial_presentation.py \
  aura_construction_pascal_spatial_foundry_server.py

pytest -q tests/test_aura_pascal_spatial_presentation.py

node --check aura_showcase/pascal-construction-foundry.js
node --check aura_showcase/pascal-workbench/pascal-workbench.js
```

The tests cover exact source identity, JSON schemas, scene/coordinate tampering, malformed lock rows, current-state admission, same-origin validation, six-slot compilation, pending-command binding, sequence and nonce replay, message tampering, storey/selection behavior, authority rejection, exact dissolution, post-dissolution rejection, relaunch, and absence of remote dependencies.

## Deliberate limits

- This is presentation-only and synthetic-fixture-only.
- No Pascal MCP mutation is enabled.
- No Construction event is appended.
- No design, safety, survey, code, payment, access, or physical-work decision is approved.
- No external model or internet connection is required.
- The local compatibility renderer is not canonical geometry truth.
- A future exact Pascal package build can replace the child rendering implementation only if the source lock, contracts, bridge, lifecycle, no-network policy, deterministic mapping, and receipts continue to pass unchanged.

# Aura Pascal Spatial Presentation — PR 2

## Purpose

PR 2 adds a pinned, local, disposable Pascal presentation organ beneath Aura's existing Construction and Spatial owners. It does **not** create a second Construction truth store, renderer authority, routing engine, evidence ledger, approval plane, persistence plane, or learning path.

The Pascal organ is optional. If any lock, package identity, asset, manifest, coordinate receipt, or retained static byte fails validation, the Pascal routes and browser injection remain unavailable while the PR 1 Construction Spatial Foundry continues to operate.

## Exact Pascal identity

- repository: `pascalorg/editor`
- commit: `42ac4be1ce5f3fee74806aa093267b6fee77d47d`
- license: MIT, Copyright (c) 2026 Pascal Group Inc.
- `@pascal-app/core`: `0.9.2` / blob `ada4f58be5494e031675a40663471a24afdfc3f0`
- `@pascal-app/viewer`: `0.9.2` / blob `86565ea117ff1fe666f1b7e93d3c40d105f502df`
- `@pascal-app/editor`: `0.9.2` / blob `73d5899ffe7d80342e06f37b9cda877ffb51a768`
- `@pascal-app/nodes`: `0.1.1` / blob `a9eb033b1ad277cd6d0d8712bb696f01a132d487`

Trusted local identities after review repair:

- source-lock digest: `672611b98aca61e3ad7a4ebcb32f278916d09d876e663452bb654610562d2e87`
- scene-artifact digest: `3a007f69349cbb78966d8deedb43326a2c236112066298b59b245435a950cbbe`
- canonical Spatial scene digest: `56824f5cf1e38a1ed82591448c111859a79a277d396df8f030730ef8031f510c`
- coordinate-receipt digest: `4dd3767ab948b3627dc0674c5f02d5ac8ee3f9745b052d1864fb44f7589b084a`

`PascalSourceLock` compares the parsed package set, local-asset path set, and computed lock digest against code-owned approved constants. A self-consistent but unapproved lock file therefore fails closed.

## Canonical ownership

Aura continues to own bilateral intent, Construction state and evidence, Spatial scenes and interaction compilation, guarded transition admission, exact repository/runtime identity, reproof, and human/community disposition.

Pascal owns only an ephemeral browser working copy:

- local fixture geometry;
- current 2D or isometric 3D presentation;
- selected storey and node;
- visible dimensions;
- disposable canvas, listeners, network guards, and IndexedDB namespace.

All Construction, survey, professional, payment, access, execution, patch, deployment, learning, and merge authority remains false.

## Exact bridge protocol

Every bridge message binds:

- exact session identity;
- direction-specific sequence;
- one-time nonce retained for the full bounded session;
- Spatial scene, render-plan, Pascal artifact, coordinate receipt, and state digests;
- UTC timestamp, direction, action, bounded payload, and message digest.

The server validates actual HTTP Host and Origin headers out-of-band. Sequence, nonce, and digest belong to the bridge message envelope; callers cannot override these server-owned identity fields outside the validated message structure.

Python and JavaScript use the same type-tagged bridge encoding. Safe integers are decimal tagged values; non-integer numbers use their exact big-endian IEEE-754 bytes. This avoids JSON exponent, negative-zero, and formatting differences between runtimes.

Only one parent command may be pending. Issuing a command does **not** increment the parent sequence and does not acknowledge the command. Parent sequence advances only after:

1. the exact expected child receipt;
2. the exact command digest;
3. action-specific postconditions matching the issued payload.

Examples:

- `SET_VIEW_2D` cannot be acknowledged as `3D`;
- `SET_STOREY L2` cannot be acknowledged as `L1`;
- selection and dimensions receipts must match the issued node/boolean;
- load receipt must match the exact manifest, initial view, storey, root selection, dimensions, and node count.

A child error marked `validated_command=false` clears the pending delivery attempt without consuming the parent sequence, allowing exact retry. A command-bound error marked `validated_command=true` consumes the sequence and is retained against that exact command digest.

## Request and static-asset boundary

Pascal API requests validate the actual HTTP `Host` and `Origin` headers. Server-owned origin, digest, sequence, nonce, and state identity cannot be supplied in request bodies.

User-controlled route strings are never joined into filesystem paths. Exact routes select fixed paths, and static bytes are retained only after the source lock and all dependent contracts validate. Pascal markup, scripts, styles, and workbench assets are not served or injected when validation fails.

The strict no-network Content Security Policy is scoped only to `/pascal-workbench/*`. PR 1 retains its existing map/network behavior.

IPv4 loopback uses `HTTPServer`; `::1` uses an IPv6 server family.

## Guarded lifecycle

```text
CREATED
  -> child READY
READY
  -> server issues LOAD_ARTIFACT (pending only)
  -> exact LOAD_RECEIPT
ACTIVE
  -> server issues one view/storey/selection/dimensions/reset command
  -> exact action-specific receipt
  -> optional exact RENDER_RECEIPT
ACTIVE
  -> server issues DISSOLVE
  -> child removes listeners, restores network guards, clears renderer/buffers,
     deletes session IndexedDB, then emits DISSOLUTION_RECEIPT
DISSOLVED
  -> same-origin parent removes iframe
  -> server retains parent cleanup observation
```

A registry slot is reusable only after both the child dissolution receipt and parent iframe-removal observation exist. Active or incompletely dissolved sessions are never evicted.

## Deterministic presentation

The local fixture supports:

- floor-plan 2D;
- isometric 3D;
- storey isolation;
- bounded selectable nodes;
- dimensions that alter both 2D and 3D pixels;
- reset;
- zero external requests;
- exact cleanup and relaunch.

Every accepted command and child event compiles through `aura_spatial_interaction.compile_spatial_interaction` and must return exactly:

```text
DIR -> ASP -> CLASS -> SUBJ -> VOICE -> STEM
```

## Verification

```bash
python -m py_compile \
  aura_pascal_spatial_presentation.py \
  aura_pascal_spatial_presentation_part1.py \
  aura_pascal_spatial_presentation_part2.py \
  aura_pascal_spatial_presentation_part3.py \
  aura_pascal_spatial_presentation_part4.py \
  aura_pascal_spatial_presentation_part5.py \
  aura_construction_pascal_spatial_foundry_server.py \
  tests/test_aura_pascal_spatial_presentation.py \
  tests/test_aura_construction_pascal_spatial_foundry_server.py

pytest -q \
  tests/test_aura_pascal_spatial_presentation.py \
  tests/test_aura_construction_pascal_spatial_foundry_server.py

node --check aura_showcase/pascal-construction-foundry.js
node --check aura_showcase/pascal-workbench/pascal-workbench.js
```

The repaired focused suite covers 34 contract/server cases, including payload size/depth/type limits, exact package pins, cross-runtime number hashing, actual Host/Origin checks, contradictory receipts, sequence recovery, nonce/session ceilings, incomplete-dissolution retention, conditional asset serving, route-scoped CSP, IPv6 selection, full launch/load/dissolution, and PR 1 fallback.

## Deliberate limits

- presentation-only and synthetic-fixture-only;
- no Pascal MCP mutation;
- no Construction event append;
- no external model, plugin, asset, or internet dependency;
- no canonical browser persistence;
- visual alignment is not canonical geometry or survey truth;
- merge and deployment remain human-controlled.

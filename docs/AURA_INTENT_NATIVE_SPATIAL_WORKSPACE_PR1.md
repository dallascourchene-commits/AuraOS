# AuraOS Intent-Native Spatial Workspace — PR1

## Contracts and frozen Coding Spatial Workspace vertical slice

**Base:** `879b5fb056b70d150b1646e082223330a36c2912`  
**Allowed-path-set digest:** `903d3ac371968dfff15ff57eb406bf960fd9bb483660cd983ce25c87c2652d81`  
**Terminal state:** `READY_FOR_HUMAN_REVIEW`

## Decision

PR1 adds one contract-only compatibility module. It does **not** modify or replace the existing Ephemeral Organ V1 manifest, Spatial contracts, Compass, Forge, Unified Memory and Continuity, Waboose, Runtime Harness, renderer, or domain owners.

The new layer compiles and verifies immutable references. It does not activate a workspace, call an adapter, invoke a renderer or model, create a project store, mutate source or domain state, publish, deploy, or merge.

## Canonical-owner matrix

| Concern | Canonical owner preserved | PR1 action |
|---|---|---|
| Temporary-organ manifest | `aura_ephemeral_manifest` | Wrap an exact verified V1 snapshot by reference; never modify V1 |
| Activation and dissolution | `aura_ephemeral_runtime` | Reference only; PR1 exposes no activation API |
| Project evidence and continuity | Existing repository/domain owners and Unified Memory/Continuity | Compile minimum-sufficient references, never copied truth |
| Spatial scene and interaction truth | Existing Spatial contracts and Arena | Bind exact scene, session, entity, and evidence identities |
| Code intelligence | Coding Relationship Compass | Declare a capability/adapter reference only |
| Code candidate lifecycle | Forge | Prepare a governed handoff only; no direct edit capability |
| Semantic review | Coding Waboose | Commit a bounded review request |
| Runtime proof | Runtime Refactor Harness | Declare a required gate only; no runtime execution in this module |

## Immutable contracts

### `ProjectContextProjection`

A read-only project projection containing exact repository identity and complete canonical-reference sets for artifacts/evidence, decisions, rejected alternatives, unresolved questions, assumptions, capabilities, relationships, blockers, and next actions. Its privacy profile is fixed to `MINIMUM_SUFFICIENT`; egress is fixed to `LOCAL_ONLY`.

Binding validation requires the complete expected reference-ID set. Partial maps, stale projection-level freshness, stale references, duplicate IDs, and changed digests fail closed.

### `EphemeralWorkspaceRecipe`

A versioned wrapper over an exact V1 manifest snapshot. It binds the complete canonical intent, project projection, capability graph, adapters, evidence, owner handoffs, budgets, interaction actions, verification gates, TTL, and dissolution policy.

For `CODING_SPATIAL_WORKSPACE_V1`, capability IDs, dependency edges, owners, renderer/device requirements, actions, verification gates, lifecycle policy, and dissolution policy are exact constants. Serialized recipes cannot substitute `shell`, redirect a canonical owner, remove a gate, make dissolution optional, or add automatic persistence or promotion.

The effective recipe TTL is capped by the V1 manifest TTL. Its wall-time budget cannot exceed that effective TTL. The public recipe ID is derived from every behavior-defining recipe field.

### `SpatialReferentBinding`

An exact scene/session/entity candidate bound to current canonical evidence. Evidence with `STALE` or `UNKNOWN` freshness is rejected before a binding can be constructed.

### `MultimodalSpatialObservation`

A privacy-minimized normalized event for voice, hand, gaze, ray, touch, keyboard, and controller input. Raw sensor payloads are not representable in the closed metadata contract. Temporal windows are ordered and limited to 60 seconds, speech is bound to its exact transcript digest, input sources are normalized before uniqueness checks, and every target is rebound to complete current entity and evidence sets.

### `AuthorityEnvelope`

Every source/domain/production mutation, renderer, sensor, model, execution, persistence, deployment, physical-work, payment, professional, patch, VSA patch, commit, push, pull-request, merge, automatic persistence, automatic resume, and automatic promotion authority remains false. Projection-only, review-only, and human-review-required remain true.

## Canonicalization and integrity

Canonical JSON accepts only unambiguous JSON values:

- object keys must already be strings;
- sets and non-JSON objects are rejected;
- text and probability fields are never coerced from malformed types;
- non-finite numbers are rejected;
- all new record digests are exact 64-character BLAKE2b-256 identities;
- repository commits require complete 40-character SHA-1 or 64-character SHA-256 object IDs;
- deserialization requires the original non-empty record digest and verifies it against canonical bytes.

The existing Ephemeral Organ V1 digest remains its canonical 32-character BLAKE2b-128 identity. PR1 recomputes that digest from a serialized V1 snapshot and then derives a 64-character wrapper digest. It never trusts `phase_hash` without recomputation.

## Closed metadata contract

Canonical-reference metadata is a bounded flat scalar object. Only explicitly approved navigation and evidence fields are accepted:

- bounded text such as `source_path`, `source_span`, `symbol`, `relation`, `media_type`, and `description`;
- bounded integers such as line numbers and byte length;
- exact digests;
- `manifest_version`, the retained V1 manifest digest, and `wrapped_not_replaced: true` for the V1 wrapper.

Unknown keys, nested arrays/objects, authority aliases, raw camera/audio/joint/gaze/room payload families, and non-string keys fail closed. This removes both key-alias and nested-value alias bypasses.

## Frozen `CODING_SPATIAL_WORKSPACE_V1`

The recipe exposes only bounded review capabilities:

- compile an existing Compass packet;
- fetch a bounded exact neighborhood;
- open exact source slices;
- display tests and schemas;
- compile candidate Change Graphs;
- prepare a governed Forge handoff;
- read verification status;
- display admitted Attempt Archive evidence;
- dissolve the workspace.

No direct source-write or execution capability is present. Consequential code work remains owned by Forge and exact-source verification lanes.

## Schema and semantic validation boundary

The three Draft 2020-12 schemas enforce exact record shape, fixed authority and policy constants, closed metadata, exact digest formats, bounded arrays/numbers, and structural types.

Some invariants cannot be expressed portably in standard Draft 2020-12 JSON Schema, including:

- membership of dependency-edge endpoints in a sibling `capability_ids` array;
- graph cycle detection;
- uniqueness of reference IDs across separate arrays;
- arithmetic relationships between timestamps;
- equality of transcript text and its digest;
- scene/session equality between a parent observation and nested targets.

Each schema therefore names a mandatory executable semantic validator through `x-aura-semantic-validator`:

- `validate_project_semantics`
- `validate_recipe_semantics`
- `validate_observation_semantics`

A consumer must run both Draft 2020-12 validation and the named semantic validator. The documentation no longer claims that JSON Schema alone proves cross-field graph or identity invariants.

## Review-repair verification

The focused suite now contains 25 tests covering:

1. exact V1 object and serialized-snapshot compatibility;
2. manifest-version, body, and legacy-digest tampering;
3. strict non-coercive canonicalization;
4. closed, detached metadata;
5. mandatory serialized record digests;
6. complete project rebinding and projection freshness;
7. self, dangling, duplicate, cyclic, and oversized dependency graphs;
8. exact frozen capabilities, owners, gates, and lifecycle policies;
9. deterministic reference ordering and global recipe-reference uniqueness;
10. manifest/recipe TTL and wall-time budget consistency;
11. temporal, transcript, normalized-input, target, and evidence binding;
12. Draft 2020-12 structural safety plus mandatory semantic validators;
13. docstring coverage and proof of no operational or persistence calls.

Local focused verification completed:

- Python compilation: passed;
- focused tests: **25 passed**;
- all JSON documents parsed successfully;
- all three schemas passed Draft 2020-12 meta-validation;
- the contract module imports only Python standard-library modules and contains no operational or persistence invocation.

## Review-finding disposition

All substantive CodeRabbit and Codex findings were consolidated into the strict contract rewrite and regression suite. Sourcery's self-dependency, temporal-window, and TTL test requests are covered. Kilo's CODEMAP/topology scope finding is addressed by restoring those generated artifacts to the exact base tree. The test's import of `aura_ephemeral_manifest.create_manifest` is intentional: it is the compatibility boundary under test, not a hidden new dependency or replacement owner.

## Harness evidence disclosure

The implementation is bound to the exact GitHub base and canonical source blobs. This execution environment still cannot honestly claim a completed full-repository Harness `prepare`/`doctor` run, Compass packet, Council receipt, Waboose execution, or full repository regression suite. The owner matrix and Change Graph are exact-source-guided evidence, not fabricated runtime receipts. Repository CI and current-head external reviews remain separate evidence.

## Exact substantive scope

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

`.aura/CODEMAP.json`, `.aura/CODEMAP.md`, `topology_map.json`, and runtime-memory artifacts must remain identical to the exact base in this substantive PR.

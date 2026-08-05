# AuraOS Intent-Native Spatial Workspace — PR1

## Structural contract repair and frozen Coding Spatial Workspace vertical slice

**Base:** `879b5fb056b70d150b1646e082223330a36c2912`  
**Allowed-path-set digest:** `903d3ac371968dfff15ff57eb406bf960fd9bb483660cd983ce25c87c2652d81`  
**Digest derivation:** lexicographically sort the eight allowed paths, join them with `\n`, append one trailing `\n`, encode as UTF-8, and compute SHA-256.  
**Terminal state:** `READY_FOR_HUMAN_REVIEW`

## Structural decision

PR1 remains a non-operational compatibility layer. It does not activate an organ, invoke a renderer or model, persist project truth, mutate source, publish, deploy, or merge.

The repair separates three previously blurred trust states:

1. **Parse:** bounded structure, canonical spelling, and self-integrity are verified.
2. **Bind:** the complete record is compared with independently trusted canonical expectations.
3. **Admit:** only a successfully bound compiled record may be treated as the workspace recipe.

A digest proves that a body is internally self-consistent. It does not prove that the body came from a canonical owner or matches an approved lifecycle/resource contract. `validate_project_semantics()`, `validate_recipe_semantics()`, and `validate_observation_semantics()` therefore require independently trusted complete-record expectations; parsing alone is never admission. The compiler likewise requires `expected_project_projection` before it can emit a recipe.

## Canonical-owner matrix

| Concern | Canonical owner preserved | PR1 action |
|---|---|---|
| Source V1 manifest | `aura_ephemeral_manifest` | Export once, verify the complete V1 body and legacy digest, then derive a sanitized projection reference |
| Activation and dissolution | `aura_ephemeral_runtime` | Reference only; no activation API is exposed |
| Repository secret-path policy | `aura_ephemeral_path_policy` | Reuse its forbidden patterns; do not maintain a second local denylist |
| Project evidence and continuity | `aura_unified_memory_continuity` | Require this exact owner during project parsing and binding |
| Spatial scene and interaction truth | Existing Spatial contracts and Arena | Bind exact scene, session, entity, observation, and evidence identities |
| Code intelligence | Coding Relationship Compass | Declare exact adapter references only |
| Code candidate lifecycle | Forge | Prepare a governed handoff only; no direct edit capability |
| Semantic review | Coding Waboose | Publish a bounded review request only |
| Runtime proof | Runtime Refactor Harness | Declare a required gate; no runtime execution in this module |

## Single-snapshot hostile-input boundary

Mappings, nested mappings, nested sequences, dataclasses, enums, and live manifest exports are recursively detached exactly once before validation. The canonicalizer:

- rechecks observed breadth after iteration rather than trusting a custom `len()`, and normalizes hostile sequence iteration, mapping export/iteration, and pair length/index protocols to `ValueError`;
- recursively validates enum values;
- walks dataclass fields without unbounded `asdict()` recursion;
- detects recursive/cyclic values and normalizes failures to `ValueError`;
- bounds depth, breadth, scalar bytes, and numeric magnitude;
- rejects sets, non-string object keys, invalid Unicode scalars, and non-JSON values.

This closes the repeated A/B/A snapshot, lying-container, enum bypass, and recursive-dataclass findings at one shared boundary.

## Sanitized V1 manifest projection

The source `AURA_EPHEMERAL_ORGAN_V1` record remains canonical and unchanged. PR1 verifies its full shape, legacy 32-character digest, timestamps, safe policy, closed grant profile, arena lease, verifier gates, resource ceilings, and non-executable UI.

The recipe does **not** treat that complete legacy body as workspace authority. It derives a deterministic projection containing only:

- source manifest version and organ identity;
- source snapshot digest and retained legacy digest;
- the exact minimal read-only capability basis needed by PR1;
- empty effective UI capability;
- effective bounded resource ceilings, with positive legacy `cost_usd` rejected rather than clamped into a zero-cost projection;
- explicit authority non-escalation.

The resulting `base_manifest_ref` is named `organ-manifest-projection:<digest-prefix>` and carries `source_digest`, `legacy_manifest_digest`, `manifest_version`, and `wrapped_not_replaced: true` metadata. Legacy renderer, audit, telemetry, or other broader V1 grants cannot silently become PR1 authority.

## Immutable contracts

### `ProjectContextProjection`

A minimum-sufficient read-only projection containing exact repository identity and complete reference sets for artifacts/evidence, decisions, rejected alternatives, unresolved questions, assumptions, capabilities, relationships, blockers, and next actions.

`canonical_owner` is fixed to `aura_unified_memory_continuity`; privacy is fixed to `MINIMUM_SUFFICIENT`; egress is fixed to `LOCAL_ONLY`. Hypothesis/presentation references, stale references, duplicate IDs, redirected owners, and incomplete rebinding fail closed.

### `EphemeralWorkspaceRecipe`

The frozen `CODING_SPATIAL_WORKSPACE_V1` recipe binds the manifest projection, canonical intent, project projection, capability graph, adapters, evidence, handoff owners, budgets, interactions, verification gates, TTL, and dissolution policy.

The behavior-derived `recipe_id` is enforced during direct construction, `dataclasses.replace()`, and deserialization. A caller cannot create a live forged identity and have the constructor sign it.

Serialized adapter/evidence references are structurally exact and current, but their external ownership is authenticated only when the mandatory semantic admission path receives the independently trusted expected recipe. Documentation does not claim otherwise.

### `SpatialReferentBinding` and `MultimodalSpatialObservation`

Referents and observations bind complete scene, session, entity, evidence, target, parent-event, modality, transcript, and temporal identities. Target binding IDs, entity IDs, and evidence-reference IDs must each be unique before an observation digest is signed. Raw sensor payloads are not representable in the metadata contract. Temporal windows are ordered and limited to 60 seconds.

### `AuthorityEnvelope`

Every mutation, renderer, sensor, model, execution, persistence, deployment, physical-work, payment, professional, patch, commit, push, pull-request, merge, and automatic-promotion authority remains false. Projection-only, review-only, and human-review-required remain true.

## Closed metadata and source paths

Canonical-reference metadata is a bounded flat scalar object. Accepted bounded text fields are:

- `source_path`, `source_span`, `symbol`, `relation`, `evidence_class`, `media_type`, `description`, and `note`;
- bounded line/byte integers;
- exact content/source/artifact digests;
- V1 projection metadata fields.

Unknown keys, nested structures, authority aliases, raw camera/audio/joint/gaze/room payloads, and non-string keys fail closed.

`source_path` must be repository-relative POSIX syntax and is checked against the exact forbidden patterns owned by `aura_ephemeral_path_policy`. PR1 intentionally does not invent additional unrelated path policy.

## Schema and semantic boundary

The three Draft 2020-12 schemas enforce exact local shape, fixed authority and owner constants, closed metadata, exact digest formats, bounded arrays/numbers, no surrounding whitespace in bounded text, source-path restrictions, and frozen recipe constants.

Cross-record identity, graph, digest equality, timestamp arithmetic, transcript equality, freshness admission, reference-ID uniqueness, manifest digest-prefix identity, target identity uniqueness, canonical serialized array ordering, Unicode scalar validity, and complete admission require executable semantic validation. All three schemas declare `x-aura-semantic-requires-independent-binding: true`. Each non-structural rejection is named in `x-aura-semantic-delegations`; UTF-8 byte ceilings, Unicode scalar validity, source-span ordering (`line_start <= line_end`), cross-record uniqueness/equality, freshness, digest-prefix identity, and canonical ordering are enforced by the named mandatory semantic validator rather than falsely claimed as Draft 2020-12 structure.

Consumers must run both schema validation and the named validator:

- `validate_project_semantics(..., expected_projection=<trusted continuity projection>)`
- `validate_recipe_semantics(..., expected_recipe=<trusted compiled recipe>)`
- `validate_observation_semantics(..., expected_observation=<trusted observation>)`

## Focused verification

The focused suite contains **37 tests** covering the original review waves plus the structural repair:

- exact V1 object and serialized compatibility;
- recursive single-snapshot live/custom mapping and nested-sequence behavior;
- strict bounded canonicalization and recursion handling;
- closed metadata and canonical path-policy delegation;
- mandatory serialized digests;
- exact continuity ownership;
- frozen capability/owner/gate/lifecycle profiles;
- complete graph/reference/observation bindings;
- sanitized manifest-projection identity;
- manifest/recipe TTL and budget ceilings;
- schema parity, canonical path-policy equivalence, and explicit semantic delegation;
- explicit parse-bind-admit separation.

Verification completed in the exact-head focused workspace:

- Python compilation: passed;
- focused tests: **33 passed**;
- all JSON documents parse successfully;
- all three schemas pass Draft 2020-12 meta-validation;
- no operational or persistence invocation is introduced.

## Scope

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

`.aura/CODEMAP.json`, `.aura/CODEMAP.md`, `topology_map.json`, and `Aura_Memory/live_topology_ast.json` remain untouched.

# Aura Spatial S5 and S6 Construction Integration

## Scope

This slice completes the governed Spatial Arena lifecycle from Phase S5 and adds only the Construction Arena adapter from Phase S6. It extends existing owners rather than creating a second renderer, Construction ledger, event store, Agent Bridge, checkpoint engine, Observatory, or authority path.

```text
ConstructionProjectState + ConstructionArenaAdapter packet
  → privacy-minimized Construction spatial projector
  → immutable SpatialSceneSnapshot
  → governed SpatialArena lifecycle
  → bounded renderer/device plan
  → review-only interaction
  → evidence receipt + Attempt Archive + assessment-only checkpoint
  → Observatory projection
  → human/domain decision packet
  → exact renderer cleanup evidence
  → lease/session dissolution
```

## Canonical owners

| Concern | Owner |
|---|---|
| Construction truth and event replay | `aura_construction_state.py` |
| Construction proposal filtering and authority routing | `aura_construction_adapter.py` |
| Immutable spatial contracts | `aura_spatial_contracts.py` |
| Scene compilation and referential integrity | `aura_spatial_scene.py` |
| Render planning | `aura_spatial_render_plan.py` |
| Ephemeral projection sessions | `aura_spatial_session.py` |
| S5 lifecycle orchestration | `aura_spatial_arena.py` |
| Construction-only S6 projection | `aura_spatial_construction.py` |
| Typed Agent Bridge facade | `aura_spatial_agent_bridge.py` |
| Persistent Agent Bridge registration | `aura_agent_arena_persistence_bridge.py` |
| MCP registration | `aura_agent_arena_mcp.py` and `aura_spatial_mcp.py` |
| Checkpoints and restore assessment | `aura_arena_persistence_adapters.py` |
| Route grammar | `.aura/arena_routes/spatial.v1.json` |

## S5 lifecycle

The route is exact and finite:

```text
FRAME → GROUND → COMPILE_SCENE → PLAN_RENDER → PRESENT
      → INTERACT → PROVE → DECIDE → DISSOLVE
```

`SpatialArena` binds each run to:

- one normalized objective and purpose digest;
- one privacy class and egress policy;
- one canonical external domain owner and state digest;
- one immutable scene digest;
- one device profile and render-plan digest;
- one ephemeral session;
- one read-only Action Capsule, Boundary Contract, and Arena Lease;
- bounded interactions, render receipts, checkpoints, archive records, and cost receipts.

Every lifecycle action remains proposal or presentation only. `DECIDE` compiles a packet for an authorized person or domain owner; it does not apply the decision. `DISSOLVE` requires a client-reported renderer-boundary receipt bound to the exact session, scene, and render plan. Allocated renderers report `DISPOSED`; headless and synthetic paths report `NOT_ALLOCATED`. Aura preserves the evidence class and never converts that client report into an independently verified cleanup claim.

Emergency `close()` does not fabricate renderer disposal. A run without observed cleanup evidence is cancelled and dissolved as abandoned, with `renderer_cleanup_observed=false`, `renderer_resources_released=false`, and `renderer_resource_boundary_satisfied=false`.

Generic Agent/MCP proof calls are labelled `DERIVED` by default and cannot claim `MEASURED` evidence. Measured browser evidence is admitted only through the exact scene/render-plan/device-bound browser telemetry validator; failed pre-presentation preparation releases its lease without inventing a renderer session.

## Privacy and egress

Spatial privacy classes are `PUBLIC`, `PROJECT`, `RESTRICTED`, and `SENSITIVE`. Egress is either `LOCAL_ONLY` or `ADMITTED_RENDER_WORKER`.

Restricted and sensitive runs are always local-only. External egress requires an explicit worker allowlist, a pre-admitted capability digest for every worker, and a network-enabled device profile with a positive byte budget. After planning, the Arena may emit a bounded admission baton containing only the selected worker identity/capability binding, admitted manifest fields, exact scene/plan/domain digests, lease identity, and non-authority flags. It never includes asset URIs, metadata, source references, entity/link payloads, raw domain state, or raw sensor data. Emission count and calculated bytes are recorded in the cost receipt; observed transport bytes remain `0` until measured by an external transport owner.

## Checkpoints, archive, and Observatory

The Spatial Arena uses the retained temporal persistence and Attempt Archive owners. Checkpoints contain invariant projections only: run, phase, purpose, privacy, egress, domain owner/state digest, scene/render-plan digests, interaction/proof identifiers, admitted asset identifiers/source references, `restore_mode=ASSESSMENT_ONLY`, and `automatic_resume=false`. They contain no raw domain state or sensor payload.

Repeated proofs form a parent-linked checkpoint chain. Restore calls return an assessment packet and never mutate or automatically resume a run. Observatory output is read-only and includes calculated usage/cost evidence without payloads.

## Construction-only S6 adapter

`project_construction_state_to_scene()` accepts an exact `ConstructionProjectState` and a validated Construction Arena runtime packet. The adapter verifies the nested Action Capsule, Boundary Contract, Arena Lease, evaluation digest, and all proposal/human-release boundaries before projecting anything.

The scene contains state and final-chain digests, abstract project/scope references, aggregate event/conflict counts, blocked/admissible proposal summaries, uncertainty classes, evaluation/projection digests, and local explicitly non-survey floor-plan manifests when privacy permits.

It excludes Construction event records, evidence payloads, raw sensor values, actor/claimant/worker/person identity or vulnerability data, consent records, source/survey-authoritative coordinates, and physical-work, payment, access, equipment, certification, or production authority.

Public projections hash project, scope, and candidate identifiers. Restricted and sensitive projections are abstract and reject floor-plan geometry. Project-level floor plans must be local or Aura-addressed, privacy-compatible, explicitly `survey_authority=false`, and explicitly `person_level_data_included=false`.

## Agent Bridge, MCP, and CLI

Construction preparation remains Python-typed through `aura_spatial_prepare_construction`; it requires an exact `ConstructionProjectState`. It is intentionally absent from the JSON MCP tool list so untyped payloads cannot impersonate canonical Construction state.

MCP exposes only post-preparation status, review-only interaction, proof/checkpoint, decision packet, Observatory, restore assessment, and exact-evidence dissolution. The CLI supports route validation and a synthetic Construction demo using a temporary state root, no private data, no production connectors, and no persistent demo state.

## Verification workflow

`.github/workflows/aura-spatial-s5-s6-construction.yml` verifies the exact pull-request head and runs compile/Ruff/route checks, new and retained Spatial/Construction/persistence/Agent Bridge/browser regressions, structural architecture proof, and full Agent Bridge/Connectome/Emergent/Council-Surgeon/Waboose/Crucible proof. Timeouts fail closed with diagnostic receipts instead of hanging CI. CODEMAP remains deferred until the final pre-merge operation.

## Non-authority guarantees

This slice adds no mutable Construction replica; physical work, payment, access, equipment, professional/legal/engineering/regulatory/survey authority; renderer authority; raw sensor retention; automatic checkpoint restore; or automatic execution, commit, push, pull request, merge, or production promotion.

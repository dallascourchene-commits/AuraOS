# Temporary S5/S6 implementation contract

Implement the complete S5 Spatial Arena and only the Construction adapter slice of S6 on PR #169. This is a bounded coding handoff; delete this temporary file after source is materialized.

## Required permanent files

Modify canonical owners:
- `.aura/ARCHITECTURE.md`
- `README.md`
- `USER_GUIDE.md`
- `aura_agent_arena_mcp.py`
- `aura_agent_arena_persistence_bridge.py`
- `aura_arena_persistence_adapters.py`

Add:
- `.aura/arena_routes/spatial.v1.json`
- `.github/workflows/aura-spatial-s5-s6-construction.yml`
- `aura_spatial_agent_bridge.py`
- `aura_spatial_arena.py`
- `aura_spatial_cli.py`
- `aura_spatial_construction.py`
- `aura_spatial_mcp.py`
- `docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md`
- `scripts/aura_spatial_s5_s6_construction_architect_harness.py`
- `tests/test_aura_spatial_agent_bridge_mcp.py`
- `tests/test_aura_spatial_cli.py`
- `tests/test_aura_spatial_s5_arena.py`
- `tests/test_aura_spatial_s5_s6_harness.py`
- `tests/test_aura_spatial_s6_construction.py`

## S5 lifecycle

Implement exact governed states:
`FRAME → GROUND → COMPILE_SCENE → PLAN_RENDER → PRESENT → INTERACT → PROVE → DECIDE → DISSOLVE`.

Reuse existing canonical owners: `SpatialProjectionSessionManager`, spatial contracts/render plans, Attempt Archive, temporal persistence, Observatory projections, Action Capsules, Boundary Contracts, read-only Arena Leases, existing renderer adapters, and Agent Bridge/MCP patterns.

Requirements:
- purpose, privacy, lease, egress, capability and digest checks fail closed;
- interactions compile review-only intent and cannot mutate source or domain truth;
- external workers receive only admitted assets/state and digest-bound capability packets;
- proof creates bounded non-authoritative receipts, empirical cost/usage evidence, Attempt Archive entry, and payload-minimized assessment-only checkpoint;
- repeated proof checkpoints form a parent-linked chain;
- restore is assessment-only and never auto-resumes;
- Observatory is read-only;
- DECIDE emits a human/domain decision packet and does not execute the decision;
- dissolution releases the Arena lease and requires an exact renderer-boundary receipt;
- client-reported `DISPOSED` is required when a renderer was allocated; `NOT_ALLOCATED` is required for headless/synthetic paths;
- cleanup evidence binds session ID, scene digest and render-plan digest and remains labelled client-reported, not independently verified;
- emergency close records cleanup as unobserved and must not fabricate disposal;
- no raw private sensor payload is stored.

## Construction-only S6 adapter

`ConstructionProjectState` remains the sole mutable Construction truth owner. Validate the exact state and existing Construction runtime packet, including nested action capsule, boundary contract, lease and evaluation digests. Emit an immutable privacy-minimized scene containing only abstract project/scope/proposal views and digest references.

Must reject or exclude:
- Construction events and evidence payloads;
- people, consent records or person-level vulnerability fields;
- source coordinates or precise restricted/community layout;
- private production fixtures;
- survey-authoritative geometry;
- incompatible privacy classes or stale/mismatched digests.

Public identifiers are hashed. Restricted/sensitive scenes reject floor-plan geometry. Admitted assets must be local, privacy-compatible, non-survey and free of person-level data. Blocked/admissible proposals remain advisory. Never authorize physical work, payment, access, equipment, safety release, engineering/professional/legal/regulatory certification, source mutation, execution or merge.

## Bridge, MCP and CLI

- Add typed Python-only Construction preparation to `PersistentAuraAgentArenaBridge`.
- Deliberately omit Construction preparation from JSON MCP so untyped JSON cannot impersonate canonical Construction state.
- MCP exposes only post-prepare status, interaction, proof, decision, Observatory, restore assessment and cleanup-bound dissolution.
- CLI supports route validation and a synthetic Construction demo using a temporary state root, no private data, no production connector and no persistent demo state.

## Persistence and harness

- Add `spatial_arena` to canonical persistence and a `checkpoint_spatial` assessment-only projection that rejects raw domain/sensor state and automatic resume.
- Add a structural proof and a full Aura-native proof using Agent Bridge, Connectome/affordance routing, Emergent evidence, Council/Surgeon proposal boundaries, Coding Waboose and Crucible.
- Run the full architecture analysis in a separately killable process group with a unique run token; total/component timeouts fail closed and still write a diagnostic receipt; kill token-marked descendants to prevent hangs.
- Architecture analysis must restore CODEMAP and leave tracked source unchanged.

## Required verification

- Python compile, Ruff check/format and route validation.
- All `tests/test_aura_spatial*.py`.
- Canonical Construction tests: adapter, adapter hardening, authority, benchmark, contracts, fixtures, grammar and state.
- persistence/Agent Bridge/MCP tests.
- `npm run test:spatial`.
- structural architecture receipt with every invariant passing.

## Authority and workflow

No automatic execution, code mutation from Spatial interactions, automatic merge, production promotion or CodeRabbit Autofix. Keep PR draft. Do not regenerate CODEMAP yet; CODEMAP regeneration is the final operation immediately before a human-authorized merge decision.

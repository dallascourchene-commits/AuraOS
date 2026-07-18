# Aura Spatial S0–S2 — Council V3 and Coding Circuit Receipt

Date: 2026-07-19  
Base head: `f302811ec4c84f194f232e6f475cbd0e64bf94c8`  
Branch: `feature/aura-spatial-s0-s2`  
Mode: deterministic Council V3 route replay + implementation synthesis  
Native Council model calls claimed: **no**

## Evidence lineage

This implementation uses the architecture introduced by the recent Planning Board and Coding Waboose work:

```text
Planning Board IR
  → typed proposal-only actions
  → BC0–BC5 continuity
  → Coding Arena Planning Board shadow
  → Coding Waboose diagnostic breadboard
  → Council V3 selective critics
  → Aura Spatial S0–S2 Coding Circuit
```

The important transfer is structural, not cosmetic. Spatial work is represented as components with typed ports, connected evidence, explicit mocks, forward paths, backward proof requirements, verifier receipts, rollback conditions, and separated authority.

## Council V3 routing

The bounded implementation plan contains:

- 10 ACT tasks;
- explicit dependency edges;
- a sequential chain deeper than three tasks;
- 2 large tasks;
- risk map and rollback conditions;
- 30 estimated maximum model turns under the Council profile.

Therefore the deterministic Council V3 selector admits:

```yaml
selected_lanes:
  - scope
  - tests
  - sequence
  - continuity
  - rollback
  - cost
skipped_lanes: []
```

## Lane findings applied

### Scope

- Create a new spatial substrate; do not refactor Council V3, Coding Waboose, Planning Board, Agent Bridge, or Coding Arena algorithms.
- Reuse `select_micro_arena()` as the coding topology owner.
- Keep S0–S2 representation-independent and renderer-free.
- Treat existing AR/WebSocket surfaces as compatibility projections, not canonical state.

### Tests

- Require contract and adversarial tests before bridge integration.
- Test authority fields directly, not only output shape.
- Test missing references, cycles, non-finite transforms, digest mismatches, unsafe paths, self-links, projection-only enforcement, selected-node cap survival, and metadata sanitization.
- Test deterministic Council routing and BC4/BC5 circuit states.
- Preserve existing Coding Arena and showcase tests.

### Sequence

```text
contracts
  → frame and asset validation
  → scene compiler
  → Coding Arena projection
  → interaction compiler
  → hotswap guard
  → bridge integration
  → docs/schema/tests
  → architecture anchor
  → CODEMAP regeneration
```

Bridge integration is intentionally after the interaction contract so it cannot invent its own authority semantics.

### Continuity

Every component emits:

- a stable component output reference;
- a verification packet reference;
- exact source references;
- dependency output references;
- two verifier IDs;
- an idempotency key;
- a reversible proposal-only action.

Context handoffs can be reconstructed from the Planning Board and do not depend on private chain-of-thought.

### Rollback

- Additive contract modules can be reverted independently.
- Bridge integration is a separate, narrow change.
- Any second topology scanner, renderer authority, unstable digest, selected-node truncation, or false hotswap success triggers rollback.
- Generated maps are refreshed only after tests pass, preventing generated evidence from masking a broken source state.

### Cost

- Core uses Python standard library plus existing Aura contracts.
- Topology projection is bounded to 128 nodes and 320 links.
- Network fetch, asset decoding, renderer runtime, OpenXR/WebXR, and Gaussian-splat execution are deferred.
- No new runtime dependency is introduced in S0–S2.

## Coding Circuit

Components:

```text
S0_CONTRACTS
  ├─→ S1_FRAMES
  └─→ S1_ASSETS
        ↓
      S1_SCENE
      ├─→ S2_CODING_PROJECTION
      └─→ S2_INTERACTIONS
              ↓
      S2_HOTSWAP_GUARD
              ↓
      S2_BREADBOARD
              ↓
      S2_TESTS_DOCS
              ↓
      S2_REGENERATE_MAPS
```

Each component begins as `CONNECTED_GROUNDED_UNPOWERED / BC4_AUTHORIZED`. It may reach `BC5_VERIFIED` only after its declared contract and authority verifier receipts are bound. BC5 is still not execution or merge authority.

## Explicit mocks

```yaml
- mock:renderer:webxr_or_openxr_adapter
- mock:asset:gaussian_splat_runtime
- mock:device:anchors_gaze_gesture_sensors
```

Mocks are declared, ungrounded, and non-authoritative. They are excluded from the S0–S2 completion claim.

## Authority receipt

```yaml
planning_proposes: true
verification_proves: true
human_authorizes: true
execution_authority: false
patch_authority: false
renderer_authority: false
vsa_patch_authority: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
```

## Repository-native implementation evidence

The source circuit at commit `670e7cdb9e52290b88f6a427307be2924be97249` completed the self-cleaning repository-native finalization workflow:

```yaml
python_compile: pass
fatal_lint: pass
json_schema_syntax: pass
focused_and_compatibility_tests:
  python: "3.12"
  passed: 27
  failed: 0
authority_invariants: pass
codemap_regeneration_and_compare: pass
canonical_codemap:
  file_count: 1159
  topology_nodes: 9561
  topology_edges: 21788
  topology_source: compiled_deep_topology
temporary_finalization_machinery_removed: true
```

Before the final three adversarial cases were added, the same repository-native focused circuit passed 24 tests on both Python 3.10 and Python 3.12. The final source is being rechecked by the permanent matrix workflow after this receipt-only update.

This evidence verifies the bounded S0–S2 source, bridge, schema, architecture anchor, and generated navigation artifacts. It does not grant merge, execution, renderer, or production-mutation authority.

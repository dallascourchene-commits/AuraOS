# Aura Spatial S0–S2 — Council V3 and Coding Circuit Receipt

Date: 2026-07-19  
Base head: `f302811ec4c84f194f232e6f475cbd0e64bf94c8`  
Branch: `feature/aura-spatial-s0-s2`  
Mode: deterministic Council V3 route replay + implementation synthesis  
Native Council model calls claimed: **no**

## Evidence lineage

```text
Planning Board IR
  → typed proposal-only actions
  → BC0–BC5 continuity
  → Coding Arena Planning Board shadow
  → Coding Waboose diagnostic breadboard
  → Council V3 selective critics
  → Aura Spatial S0–S2 Coding Circuit
```

The transfer is structural: typed ports, connected evidence, explicit mocks, forward paths, backward proof requirements, rollback conditions, and separated authority.

## Council V3 routing

The bounded plan contains ten ACT tasks, explicit dependencies, two large tasks, a deep sequential chain, rollback conditions, and a risk map. The deterministic selector therefore applies all six lanes:

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

### Scope

- Add a spatial substrate without refactoring Council V3, Coding Waboose, Planning Board, Agent Bridge, or Coding Arena algorithms.
- Reuse `select_micro_arena()` as the coding topology owner.
- Keep S0–S2 representation-independent and renderer-free.
- Treat AR/WebSocket surfaces as compatibility projections, not canonical state.

### Tests

- Test authority fields directly.
- Test missing references, cycles, non-finite transforms, unit conversion, implicit basis changes, digest mismatches, URI/path attacks, self-links, projection-only enforcement, selected-node survival, metadata sanitization, authority overrides, retained-payload bounds, and schema/code compatibility.
- Preserve existing Coding Arena and showcase compatibility behavior.

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
  → CODEMAP regeneration after source verification
```

### Continuity

Each component retains a stable output reference, exact source references, dependency references, verifier requirements, an idempotency key, and a reversible proposal-only action. Context handoffs must be reconstructible without private chain-of-thought.

A breadboard BC5 state represents continuity of the planned circuit. It is not independent evidence that repository commands ran. Repository-native verification must be tied to exact commands, outputs, and the exact commit tested.

### Rollback

Rollback triggers include a second topology scanner, renderer authority, unstable digest, selected-node truncation, unbounded retained payloads, affirmative authority metadata, false hotswap success, or generated evidence that obscures an unverified source state.

### Cost

- Core runtime remains standard-library plus existing Aura contracts.
- Projection is bounded to 128 nodes, 320 links, and 1 MiB of canonical retained evidence.
- WebSocket proposal handoff is bounded to 256 KiB and retains no raw proposal.
- Network fetch, decoding, renderer runtime, OpenXR/WebXR, and Gaussian-splat execution remain deferred.
- `jsonschema` is focused verification tooling, not a runtime dependency.

## Coding Circuit

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

Components begin `CONNECTED_GROUNDED_UNPOWERED / BC4_AUTHORIZED`. BC5 still grants no execution, patch, commit, pull-request, merge, renderer, or production authority.

## Explicit mocks

```yaml
- mock:renderer:webxr_or_openxr_adapter
- mock:asset:gaussian_splat_runtime
- mock:device:anchors_gaze_gesture_sensors
```

Mocks remain ungrounded and non-authoritative. They are excluded from S0–S2 implementation claims.

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

## Evidence status

Historical repository-native evidence at commit `670e7cdb9e52290b88f6a427307be2924be97249` recorded Python compilation, fatal lint, 27 focused tests on Python 3.12, authority invariants, and CODEMAP regeneration/compare as passing. That evidence remains historical and does not automatically verify later source changes.

The subsequent manual review:

- posted `@codex review` on PR #164, but no Codex response had been observed when this receipt was updated;
- reviewed the scoped source, bridge, tests, schema, workflow, documentation, and receipts while excluding generated CODEMAP/topology artifacts;
- corrected authority metadata overrides, URI/path validation, scene canonicalization, coordinate units and basis handling, WebSocket payload bounds, retained topology payload bounds, deterministic link selection, and Draft 2020-12 schema verification;
- added focused regression files for the manual findings;
- performed local Python compilation and full Ruff analysis on the rewritten Python files;
- did **not** trigger or rerun CI, by user instruction.

Fresh repository-native execution evidence is therefore still required before the updated PR head may claim passing runtime tests. This receipt grants no merge or execution authority.

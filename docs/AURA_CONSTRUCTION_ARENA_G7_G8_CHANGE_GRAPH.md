# Aura Construction Arena G7–G8 Change Graph

## Objective

Finish the Construction Arena refactor by composing the admitted G4 fixture, G5 Spatial Projection V2, and G6 renderer into a deterministic cinematic UI/director flow, then close the G8 proof and publication boundary.

## Canonical owners retained

| Concern | Canonical owner | G7–G8 relationship |
|---|---|---|
| Construction state | `aura_construction_state.py` | Read-only input |
| Construction runtime filtering | `aura_construction_adapter.py` | Canonical runtime packet |
| Demo asset identity | `aura_construction_demo_contracts.py` | Immutable admitted pack |
| Synthetic demo fixture | `aura_construction_demo_fixture.py` and builder | G4 owner retained |
| Spatial scene | `aura_construction_demo_projection.py` | G5 projection retained |
| Renderer lifecycle | `aura_spatial_web/construction_scene_renderer.js` | G6 owner retained |
| Cinematic sequence | `aura_construction_demo_director.py` | New presentation-only owner |
| Browser controls | `aura_spatial_web/construction_demo_*` | Local presentation surface |
| CLI launch | `aura_spatial_cli.py` | Bounded operator entrypoint |

## Added edges

```text
ConstructionDemoAssetPack
  → build_construction_demo_project_fixture
  → build_construction_demo_runtime_packet
  → project_construction_demo_to_scene
  → negotiate_spatial_render_plan
  → compile_construction_demo_packet
  → ConstructionSceneRenderer
  → deterministic tour steps
  → renderer disposal
```

## Prohibited edges

```text
director → Construction ledger mutation
browser button → physical work release
recommended alternative → automatic execution
renderer → payment/access/professional authority
fallback asset pack → survey truth
Observatory display → decision authority
CI or review bot → automatic merge
```

## Verification edges

```text
G7 source
  → Python compilation
  → Ruff
  → Node syntax checks
  → focused director tests
  → retained G4/G5 tests
  → retained G6 renderer tests
  → Gaussian covariance regression
  → deterministic CLI packet proof
  → authority envelope assertions
  → Coding Relationship Compass
  → Council V3 failure routing
  → architecture-harness doctor
  → CODEMAP freshness
  → Codex
  → CodeRabbit
  → exact-head merge
```

## Merge boundary

The final PR targets `main` because the G0–G6 integration branch is ahead of `main` and contains the complete refactor stack. The merge must preserve exact-head compare-and-swap and must occur only after the user-authorized final review cycle.

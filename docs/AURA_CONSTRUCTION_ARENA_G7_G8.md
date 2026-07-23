# Aura Construction Arena — G7–G8 Finalization

## Status

The complete chain is implemented from source/provenance contracts through deterministic director tours, evidence review, and exact renderer dissolution.

```text
G0 architecture/dependency lock
→ G1 source acquisition and immutable asset contracts
→ G2 IFC storey/GLB/SVG compiler
→ G3 deterministic degree-0 Gaussian compiler
→ G4 asset-bound synthetic Construction fixture
→ G5 immutable Spatial Projection V2
→ G6 local WebGL2 Gaussian/graph/overlay composition with fail-closed mesh contracts
→ G7 cinematic Construction UI and deterministic director
→ G8 stress tests, Waboose review, documentation, navigation, and exact-head merge
```

The browser recording client implements the deterministic Gaussian fallback. Browser GLB/SPZ decoding and a real mesh draw pass remain intentionally unavailable; mesh/hybrid controls are disabled rather than overstated.

## Launch

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --serve
```

Open `http://127.0.0.1:8767/demo/construction?tour=full`.

Compile without serving:

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --output /tmp/aura-construction-demo.packet.json
```

Full instructions: [`AURA_CONSTRUCTION_DEMO_OPERATOR_GUIDE.md`](AURA_CONSTRUCTION_DEMO_OPERATOR_GUIDE.md).

## Tours and controls

Tours: `full`, `blocked-work`, `alternatives`, and `timeline`.

Implemented controls:

```text
orbit · zoom · storey isolation · show all · explode · collapse
splats · floor plans · status · trades · blockers · budgets · inspections
dependencies · synthetic rules · timeline · picking · reset
play · pause · next step · dissolve
```

## Real-pack boundary

An admitted generated asset pack may be compiled and validated into a deterministic packet. The browser refuses it until repository-owned GLB/SPZ browser decoders and a real mesh draw pass exist. It never substitutes fallback geometry for admitted real digests.

## Authority boundary

```yaml
physical_work_authorized: false
payment_released: false
access_controlled: false
professional_certification_claimed: false
legal_or_regulatory_authority_claimed: false
survey_authority_claimed: false
renderer_authority: false
automatic_execution: false
automatic_merge: false
human_review_required: true
```

## Verification

```bash
python -m py_compile aura_construction_demo_director.py aura_spatial_cli.py
pytest -q tests/test_aura_construction_demo_director.py tests/test_aura_construction_demo_fixture.py tests/test_aura_construction_demo_projection.py
node --test tests/js/spatial-webgl2.test.mjs tests/js/spatial-webgl2-failure-injection.test.mjs tests/js/spatial-construction-demo.test.mjs tests/js/spatial-construction-review-regressions.test.mjs tests/js/spatial-gaussian-covariance.test.mjs
```

Run Coding Waboose and the Architecture Harness after focused tests. Regenerate CODEMAP/topology from the final tree, then merge only the exact reviewed head.

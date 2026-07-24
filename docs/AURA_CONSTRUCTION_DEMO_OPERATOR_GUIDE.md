# Aura Construction Arena Demo — Operator and AI-Agent Guide

## Purpose

This guide explains how to compile, launch, record, verify, troubleshoot, and safely modify AuraOS's deterministic Construction Arena demonstration.

The demo is a local, synthetic, presentation-only surface. It does not control a real project, release work, approve a contractor, operate equipment, certify a design, issue a permit, release payment, or mutate canonical Construction truth.

## What is implemented

The G0–G8 chain provides:

```text
source/provenance contracts
  → deterministic IFC storey, GLB, and SVG compilation
  → bounded degree-0 Gaussian assets
  → synthetic Construction project fixture
  → immutable Spatial Projection V2
  → WebGL2 Gaussian, graph, and overlay presentation
  → deterministic director tours
  → Observatory evidence and a human decision packet
  → exact renderer dissolution
```

The browser recording client renders the deterministic Gaussian fallback, a deterministic bounds-derived wireframe mesh presentation, and graph/overlay context. Mesh, Splats, and Hybrid are available for the synthetic fallback. The wireframe remains presentation-derived and does not claim that browser GLB decoding exists.

## Prerequisites

- Python 3.10 or newer;
- Node.js 22 for JavaScript verification;
- a clean AuraOS checkout;
- loopback access to `127.0.0.1`;
- no external network is required at runtime.

## Fastest launch

```bash
python aura_spatial_cli.py \
  --repo-root . \
  construction-video-demo \
  --tour full \
  --serve
```

Open:

```text
http://127.0.0.1:8767/demo/construction?tour=full
```

The server accepts loopback hosts only. Do not expose it through `0.0.0.0`, a public interface, or a reverse proxy without a separate security review.

## Compile a packet without serving

```bash
python aura_spatial_cli.py \
  --repo-root . \
  construction-video-demo \
  --tour full \
  --output /tmp/aura-construction-demo.packet.json
```

Inspect the packet before recording:

```bash
python -m json.tool /tmp/aura-construction-demo.packet.json | less
```

Expected authority fields remain false, while `human_review_required` remains true.

## Tour modes

- `full` — complete 18-step recording sequence;
- `blocked-work` — blocked drilling, evidence, unsafe option, and cleanup;
- `alternatives` — blocked option, admissible alternative, time/cost/idle comparison, and human review;
- `timeline` — storey separation, floor plans, progress replay, and trade history.

Change the tour in the command or URL:

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour alternatives --serve
```

```text
http://127.0.0.1:8767/demo/construction?tour=alternatives
```

## Recording controls

The implemented recording surface supports:

```text
orbit · zoom · storey isolation · show all · explode · collapse
mesh · splats · hybrid · floor plans · work status · trades · blockers · budgets
inspections · dependencies · synthetic rules · timeline scrub
picking · reset · play · pause · next step · dissolve
```

Mesh uses the admitted storey bounds to draw a deterministic wireframe fallback. Hybrid combines that wireframe with the verified Gaussian fallback. These modes are recording aids, not decoded BIM truth or physical authority.

For a clean recording:

1. use a 16:9 browser window;
2. open the full tour URL;
3. wait for `Fallback pack ready`;
4. verify attribution is visible;
5. start screen recording;
6. use Play, Pause, and Next Step as needed;
7. finish on Dissolve and confirm zero active presentation resources.

## Fallback pack versus admitted generated pack

Omit `--asset-pack` for the deterministic five-storey Gaussian recording fallback.

An admitted generated pack may be compiled and contract-validated:

```bash
python aura_spatial_cli.py \
  --repo-root . \
  construction-video-demo \
  --asset-pack demo_assets/construction_tuwien/generated/asset-pack.manifest.json \
  --tour full \
  --output /tmp/aura-construction-real-pack.packet.json
```

The browser intentionally refuses admitted real-pack rendering until repository-owned GLB/SPZ browser decoders exist. The bounds-derived wireframe applies only to the deterministic fallback and never substitutes fabricated fallback geometry for admitted real digests.

## Security boundary

The local server serves only:

- `aura_spatial_web/` files required by the interface;
- generated Construction demo assets under the admitted directory;
- the deterministic `/api/construction-demo` packet.

It rejects traversal, encoded traversal, backslash paths, NUL paths, unrelated repository files, non-loopback hosts, and invalid ports. Responses use no-store caching, content-type hardening, no-referrer policy, and a restrictive Content Security Policy.

## Focused verification

```bash
python -m py_compile aura_construction_demo_director.py aura_spatial_cli.py

ruff check \
  aura_construction_demo_director.py \
  aura_spatial_cli.py \
  tests/test_aura_construction_demo_director.py

pytest -q \
  tests/test_aura_construction_demo_director.py \
  tests/test_aura_construction_demo_fixture.py \
  tests/test_aura_construction_demo_projection.py

node --test \
  tests/js/spatial-webgl2.test.mjs \
  tests/js/spatial-webgl2-failure-injection.test.mjs \
  tests/js/spatial-construction-demo.test.mjs \
  tests/js/spatial-construction-review-regressions.test.mjs \
  tests/js/spatial-gaussian-covariance.test.mjs
```

## Use Aura's own review and architecture tools

Read `.aura/CODEMAP.md` first, then use the Architecture Harness for a reproducible repository view:

```bash
python scripts/aura_architecture_harness.py --repo-root . doctor
```

Prepare an AI-safe source handoff outside the checkout:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  handoff \
  --output-dir ../AuraOS-ai-handoff
```

Run Waboose on the focused Construction surface:

```bash
python aura_coding_waboose_cli.py --repo-root . run --request waboose_request.json
```

Waboose is review-only. It does not patch, commit, push, approve, or merge. Use exact findings as inputs to a separate repair and verification pass.

## Runtime Refactor Harness

Run the complete local server and browser path through Aura's Architecture Harness:

```bash
mkdir -p /tmp/aura-playwright
cd /tmp/aura-playwright
npm init -y
npm install --no-audit --no-fund playwright@1.55.0
npx playwright install chromium
cd -

NODE_PATH=/tmp/aura-playwright/node_modules \
python scripts/aura_architecture_harness.py \
  --repo-root . \
  runtime \
  --profile .aura/runtime_profiles/construction_demo.v1.json \
  --output-dir /tmp/aura-construction-runtime \
  --venv /tmp/aura-construction-venv \
  --install-requirements
```

A healthy receipt reports `RUNTIME_VERIFIED`; a successful run bound to a failed baseline reports `REPAIRED_AND_VERIFIED`. Inspect `browser-evidence.json`, `initial.png`, `after-tour.png`, readiness and command receipts, server logs, artifact hashes, and the source-identity comparison.

The runtime incident that motivated this harness was a real first-frame WebGL warm-up exceeding the normal Gaussian frame budget. Performance evidence had been misclassified as an integrity failure, causing renderer dissolution. The current renderer preserves invalid timing as fatal while reporting a valid slow frame as measured degraded performance and continuing safely.

## Troubleshooting

### `WebGL2 unavailable`

Confirm the browser exposes WebGL2 and that hardware acceleration is enabled. The renderer fails closed instead of silently changing evidence class.

### The browser rejects an admitted real pack

This is intentional. Use the fallback for recording or implement and review repository-owned GLB/SPZ decoders and a real mesh pass.

### A renderer enters `LOST`

Inspect the original error and any cleanup errors. The renderer attempts all releases, loses the WebGL context when available, retains unresolved handles when release cannot be proven, and permits a bounded disposal retry.

### Generated maps are stale

Regenerate only after source and tests stabilize:

```bash
python aura_codebase_navigator.py
python -m aura_codemap_verify --compare-json .aura/CODEMAP.json
```

## Authority receipt

```yaml
physical_work_authorized: false
payment_released: false
access_controlled: false
professional_certification_claimed: false
legal_or_regulatory_authority_claimed: false
survey_authority_claimed: false
renderer_authority: false
automatic_execution: false
automatic_commit: false
automatic_push: false
automatic_merge: false
human_review_required: true
```

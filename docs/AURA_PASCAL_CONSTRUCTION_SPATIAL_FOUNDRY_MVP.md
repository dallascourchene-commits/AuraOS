# Aura Construction + Pascal Spatial Foundry MVP

## Status and purpose

The PR1–PR5 Construction + Pascal Spatial Foundry MVP is merged through PR #252. This document is the canonical integration narrative for the local, deterministic, video-recordable system.

The operational entry points are:

- [`AURA_CONSTRUCTION_FOUNDRY_OPERATOR_GUIDE.md`](AURA_CONSTRUCTION_FOUNDRY_OPERATOR_GUIDE.md) — setup, rehearsal, manual presentation, full proof, reset, and troubleshooting;
- [`AURA_CONSTRUCTION_FOUNDRY_VIDEO_SCRIPT.md`](AURA_CONSTRUCTION_FOUNDRY_VIDEO_SCRIPT.md) — narrated shot list, timing, edit points, and authority-safe wording;
- [`AURA_CONSTRUCTION_FOUNDRY_EVIDENCE_GUIDE.md`](AURA_CONSTRUCTION_FOUNDRY_EVIDENCE_GUIDE.md) — artifact review, verdict, archival, failure classification, and publication handling.

The architecture keeps a strict ownership split:

```text
AuraOS
  = bilateral intent
  + canonical Construction state and runtime packet
  + evidence, obligations, candidates, authority, verification, archive, reproof, and dissolution

Pascal
  = pinned local 2D/3D building presentation organ
  + storey, node, dimensions, selection, and disposable visual working copy
```

Pascal is not a Construction truth store, approval system, evidence ledger, runtime owner, archive, verifier, rollback authority, or learning plane.

## Merged implementation sequence

- **PR #241 / PR1:** backward-compatible Construction Spatial Foundry projection, exact arena binding, trusted identity handle, guarded-WFST evidence, and candidate separation.
- **PR #247 / PR2:** pinned Pascal source/package/asset identity, local 2D/3D workbench, same-origin bridge, exact coordinate receipt, bounded session, and two-party dissolution.
- **PR #249 / PR3:** Construction decision lane, synchronized Design/Floor-plan/As-built/Compare views, obligations, overlays, three role-distinct candidates, and digest-bound JSON/PDF decision support.
- **PR #250 / PR4:** deterministic fifteen-chapter Director, bounded incident capture, retained replay, Runtime Profile V2 repair proof, isolated preview/rollback, governed U7 current reproof, and terminal dissolution.
- **PR #252 / PR5:** exact Pascal identity-chain repair, complete-MVP Runtime V1/V2 profiles, real-Chromium tour evidence, packaging, operator/video/evidence guides, Waboose review, atomic evidence-directory ownership, executable browser-proof contract, concurrency tests, and final CODEMAP/topology synchronization.

## Complete Director tour

The Director executes exactly fifteen admitted chapters:

1. Frame the Construction objective.
2. Open the exact floor plan.
3. Project the Aura-derived as-built state.
4. Compare design and as-built.
5. Review bounded Construction alternatives.
6. Start explicit `AURA, WATCH THIS` capture.
7. Mark the deterministic presentation-interface incident.
8. Finalize capture and retain replay.
9. Run exact Runtime Profile V2 reproduction.
10. Derive the repair route and retain the attempt.
11. Demonstrate degraded isolated preview and exact rollback.
12. Demonstrate successful isolated preview.
13. Run P0, P1, current reproof, and human disposition.
14. Return to Construction without changing Construction truth.
15. Dissolve the presentation session.

Restart is available only after dissolution and proves a fresh session/relaunch. It is not a sixteenth Director chapter.

The browser evidence profile captures seventeen named screenshots because it also records the opening bilateral-intent state and three separate detail views during the candidate-review chapter.

The browser may navigate only through the Director controls and the retained P3 synchronization protocol. Consequential chapters cannot be skipped by presentation navigation.

## Operational modes

### Manual presenter mode

Run:

```bash
python aura_construction_pascal_spatial_foundry_p4_server.py \
  --repo-root . \
  --host 127.0.0.1 \
  --port 8768
```

Open `http://127.0.0.1:8768/` and use **Next** for a narrated recording. This mode exposes the complete UI and still executes the consequential Runtime Profile V2 chapter through the canonical owner.

### Full bilateral proof mode

Run with a fresh external output directory that does not already exist:

```bash
python scripts/aura_construction_pascal_spatial_foundry_pr5_runtime.py \
  --repo-root . \
  --venv ../.AuraOS-pr5-runtime-venv \
  --output-dir ../AuraOS-pr5-runtime-evidence/<run-id> \
  --install-requirements
```

The wrapper compiles the external canonical bilateral confirmation, runs Runtime Profile V2, drives real Chromium through all fifteen chapters, captures current-run evidence, runs focused verification, checks CODEMAP and source-tree preservation, terminates the server, runs bilateral Waboose, and stops at human review.

## Runtime proof owners

```text
.aura/runtime_profiles/construction_pascal_spatial_foundry.v1.json
.aura/runtime_profiles/construction_pascal_spatial_foundry_bilateral.v2.json
scripts/aura_construction_pascal_spatial_foundry_pr5_runtime.py
tests/runtime/construction_pascal_spatial_foundry_browser_probe.cjs
tests/runtime/construction_pascal_spatial_foundry_probe_contract.cjs
```

The V1 profile boots the P4 loopback server, drives real Chromium, captures seventeen named screenshots plus exact JSON evidence, runs focused tests, regenerates/verifies CODEMAP, terminates the server, and proves the repository did not change. The V2 adapter runs bilateral Waboose after V1 succeeds and verifies that Waboose did not change the retained V1 artifacts.

The V2 profile consumes an external canonical bilateral confirmation compiled against the exact clean profile and current source tree. It independently evaluates positive, negative, preservation, and fault obligations. The wrapper compiles that confirmation outside the checkout and delegates to the existing Runtime Profile V2 adapter.

The runtime output directory is single-run evidence. It must be newly and exclusively claimed so concurrent or stale runs cannot mix artifacts.

## Evidence package

The required screenshot sequence is `00-bilateral-intent.png` through `16-dissolved.png`.

The required domain/runtime JSON includes:

```text
browser-evidence.json
construction-foundry-projection.json
incident-replay-packet.json
runtime-profile-v2-proof.json
repair-attempt.json
preview-rollback-receipt.json
u7-current-reproof.json
attempt-archive-index.json
cleanup-receipt.json
```

The Runtime Harness separately emits readiness, probe, server-output, server-termination, verification-command, artifact, and runtime-harness receipts. The V2 layer emits the bilateral-Waboose receipt.

A complete package must show exact chapter order, terminal dissolution, successful relaunch, no unexpected request origin, no browser/page failure, false authority, unchanged source identity, and terminal server cleanup.

## Trust model

The MVP preserves PR4 **Trust Model A**. Aura’s same-origin local browser is the trusted presentation agent. The P3 protocol proves ordered, one-time `PREPARED → PROJECTED → RENDER_CONFIRMED → ACKNOWLEDGED` transitions and unpredictable server-bound receipts. It does not claim hostile-browser pixel attestation.

The runtime probe does provide real browser, DOM, WebGL, server, request, screenshot, and receipt evidence. An environment that administratively blocks browser navigation to loopback must report that limitation; it may not substitute a passing claim.

## Authority boundary

Every runtime, projection, receipt, export, and decision surface retains false authority for:

- Construction truth mutation;
- survey or professional approval;
- physical work;
- payment release;
- access or equipment operation;
- automatic patch, commit, push, pull request, merge, deployment, or publication;
- automatic learning promotion.

`READY_FOR_HUMAN_REVIEW` is not approval. Merge and all domain decisions remain separate trusted-human actions.

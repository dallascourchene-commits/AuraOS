# Aura Bilateral Live-Repair Foundry

Status: proposal and evidence adapter only.

This final B11-B15 slice composes Aura's existing Attempt Archive, Runtime Harness, Behavioral Crucible, exact-head transport, and U7 current-reproof lifecycle. It does not create a new archive, runtime, truth, verification, learning, publication, or authority plane.

## B11 — bounded incident capture

`BoundedIncidentCapture` keeps at most 256 sanitized events in memory. An explicit incident marker is mandatory. Finalization binds the replay packet to the confirmed intent, confirmation, Semantic Ledger, guardrails, intent revision, repository head, source tree, runtime profile, release, and environment. Secret-like keys and token patterns are redacted. Finalization dissolves the active capture.

## B12 — bounded repair Foundry

`BoundedRepairFoundry` records evidence produced by the canonical execution and verification owners. It does not execute or apply patches. Each candidate must independently satisfy positive, negative, preservation, and adjacent-regression obligations. Repeated hypothesis digests are rejected and the attempt budget is bounded to eight.

Failed and successful candidate records are suitable for the existing `ArenaAttemptArchive`; storage never verifies them or promotes them to truth.

## B13 — preview and rollback

`build_preview_receipt` binds a candidate to the retained last verified version and before/after health evidence. A rollback receipt requires an explicit reason. Preview remains local/canary evidence, production mutation remains false, and human promotion remains mandatory.

## B14 — current reproof and governed learning

`build_current_reproof` requires P0 positive and negative predictions, independent P1 guardrail and preservation observations, an independent verifier identity, current bilateral/source identity, explicit human or community disposition, and a Relationship Experience reference before durable learning can be authorized. QDKT eligibility is false unless all of those gates pass. Eligibility does not crystallize or promote learning automatically.

## B15 — Spatial Foundry projection

`build_spatial_foundry_projection` produces a digest-bound projection of intent, negative intent, guardrails, plan, code targets, runtime incident, failed attempts, preview, current reproof, and human disposition. It explicitly has no visual-truth, patch, commit, push, PR, merge, deployment, production, professional, physical-work, or learning-promotion authority.

## Verification

Focused tests cover redaction, marker requirements, dissolution, no-repeat attempts, attempt budgets, negative/preservation proof, retained rollback state, P0/P1 and human/community disposition, QDKT non-crystallization, and non-authoritative projection.

Run:

```bash
python -m pytest -q tests/test_aura_bilateral_live_repair_foundry.py
```

The initial isolated run completed with 9 passing tests. Repository CI, Waboose, retained regressions, and external review remain required before merge.

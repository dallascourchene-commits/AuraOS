# Aura Construction + Pascal Spatial Foundry P4

## Purpose

P4 adds one deterministic, offline Foundry Director over the merged P3 Construction decision experience. It coordinates the Construction lane and the existing B11–B15 software self-repair lane without creating a new truth, evidence, repair, rollback, or learning owner.

P3 remains the fallback and composition owner. When P4 cannot establish a clean exact Git head, current runtime-profile identity, exact verifier hash, retained static assets, or a valid manifest, the P3 Foundry remains available and P4 reports the failure explicitly.

## Tour

The exact manifest contains fifteen ordered chapters:

1. Frame the Construction objective.
2. Show the exact Pascal floor plan.
3. Show the Aura-derived as-built projection.
4. Compare the two representations.
5. Review bounded Construction coordination candidates.
6. Start explicit `AURA, WATCH THIS` capture.
7. Mark one deterministic Pascal-selection synchronization fault.
8. Dissolve capture and retain an exact replay packet with required assets.
9. Run the existing bilateral Runtime Profile V2.
10. Record and route the bounded repair attempt.
11. Demonstrate a deliberately degraded isolated preview and exact rollback.
12. Demonstrate a successful isolated preview.
13. Run canonical P0, independent P1, current reproof, and human disposition through the existing U7 delegate.
14. Return to the Construction comparison without changing Construction truth.
15. Dissolve the presentation session.

Each chapter carries an exact six-slot packet, evidence gates, presenter notes, a digest-bound transition, and a receipt that records the unchanged Construction state digest.

## Controls

The browser exposes Play, Pause, Previous, Next, Restart, and chapter selection. All requests share one serialized queue. Previous and chapter jump are presentation navigation only; they cannot execute or skip an unproven chapter. Restart is admitted only after dissolution and creates a fresh server-owned confirmation, bilateral identity, and Director session.

## Browser synchronization contract

The Director bundle contains a testable synchronization contract that waits for P3 to retain both the selected view button receipt and the synchronized `presentationMode`; it fails closed on timeout, always re-renders the server-updated Director session in a `finally` path, and applies pacing only to non-consequential presentation chapters. A test-only early branch exposes these exact helpers before DOM initialization, while production exposes no test hooks. Node behavior tests exercise successful retention, timeout, render-on-failure reconciliation, and pacing without depending on source-string spelling.

## Trust model (Trust Model A — trusted local browser)

The P3 presentation synchronization protocol (prepare → project → confirm → acknowledge) provides:

- **Ordering**: state transitions PREPARED → PROJECTED → RENDER_CONFIRMED → ACKNOWLEDGED in strict sequence.
- **Anti-replay**: one-time nonce consumption and one-time state transitions prevent reuse.
- **Receipt unpredictability**: the server-owned `render_capability` secret is included in the `receipt_digest` but never returned to any caller, preventing offline receipt forgery.

It does **not** provide cryptographic proof that a human observed rendered pixels. Under Trust Model A, Aura's same-origin browser agent is trusted: `waitForP3View()` is the presentation-owner observation, and direct same-origin API use is not treated as an adversarial bypass. The `render_capability` prevents offline forgery but cannot prevent the trusted browser from asking the signing endpoint to sign the claim — because that browser IS the trusted agent.

This is the correct and final trust model for this offline local demo. Achieving Trust Model B (hostile-browser attestation) would require a separate trusted renderer boundary and is out of scope for this PR.

## Exact identity

The browser never declares itself current. The P4 server compiles a canonical bilateral confirmation against the current clean Git head and source tree, the exact existing Runtime Profile V2, the exact independent verifier source, the current CODEMAP digest, and the profile’s exact allowed paths. The full confirmation and runtime output remain outside the source checkout. The browser receives only a bounded identity handle and must also supply all five exact P3 identities for every stateful Director request.

## Canonical delegation

P4 reuses:

- `ArenaBoundBilateralLiveRepairService` for Construction-bound capture, replay retention, Runtime V2 proof, repair attempts, preview, rollback, and Attempt Archive records;
- the existing Runtime Profile V2 adapter and independent browser verifier;
- `compile_bridge_execution_binding` and `run_governed_u7` for P0, P1, current reproof, mandatory human disposition, and proposal-only learning assessment;
- the P3 compiler and server for Construction/Pascal identities, views, candidate projection, and P3 fallback.

The deterministic repair fixture is a software presentation-interface fault. It is not a Construction coordination candidate and cannot approve design, safety, payment, access, equipment operation, professional release, or physical work.

## Runtime V2 to B11 identity compatibility

The canonical bilateral compiler and Semantic Ledger use their existing 32-character BLAKE2 stable identities, while the B11 live-repair envelope historically admits 40–64-character hexadecimal identities. P4 does not replace either owner. It validates the exact canonical Runtime V2 contract against the external confirmation packet, retains that original contract and proof digest, and derives namespaced SHA-256 compatibility handles only for the three affected canonical IDs. The projected B11 proof is written beside the canonical proof outside the checkout, carries every exact P4 required-asset trace, records that the verification owner did not change, and remains human-review-only.

## Runtime and storage

Each Runtime V2 confirmation and trace run uses a unique process-temporary directory outside the source checkout. The Director removes those external roots during terminal dissolution. Canonical governed U7 records continue to use Aura’s existing repository-confined, ignored `Aura_Memory/p4_foundry_runtime` owner paths. The tracked source checkout remains Git-clean throughout the recording path.

## Verification

Focused tests cover the manifest chain, evidence gates, blocked chapter skipping, exact transition receipts, complete tour, restart, P3 fallback status, idempotent static injection, exact-head confirmation, external runtime paths, canonical U7 execution binding, proposal-only disposition contracts, exact P3 presentation retention, fail-closed synchronization timeout, render-on-failure reconciliation, and bounded presentation pacing. Before merge, run the existing P3 regressions and a real loopback P4 browser walkthrough through Aura’s Runtime Refactor Harness.

## Authority boundary

P4 is presentation and proof coordination only. It grants no Construction truth, professional authority, physical-work authority, patch authority, deployment authority, merge authority, or automatic learning promotion. The final Director state is `DISSOLVED`; the retained U7 disposition remains `NOT_REVIEWED`, and any approval or merge remains a separate trusted-human action.

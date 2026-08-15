# Live Bounty Harvest — 2026-08-15

Work order: `WO-LIVE-BOUNTY-HARVESTER-001`

## Triad assignment
- Triad 1 (W1–W3): live scan, exact-source issue/repo analysis, reproduction/contract extraction, AST key parsing.
- Triad 2 (W4–W6): patch construction and isolated static/schema verification.
- Triad 3 (W7–W9): PR draft/evidence review, hash verification, Merkle receipt.

## Promoted to READY_FOR_PR
1. `mergeos-bounties/Loru#19` — 25 MRG documentation patch.
2. `mergeos-bounties/PlantGuide#10` — 50 MRG JSON Schema + TypeScript SDK contract patch.

## Ingested but not promoted
- Algora public bounty index: zero public open bounties at scan time.
- Opire TypeORM #3357: $590 available/open, but broad migration/schema behavior with many active solvers; no clean-room patch attempted in this bounded harvest.
- Opire qtop Challenge #6: Opire still lists $220, but GitHub issue #433 is CLOSED/completed; stale listing rejected.
- Opire/docs French bounty: Opire landing still lists funding, but GitHub issues #2/#27 are CLOSED; stale listing rejected.
- Autokey Wayland: Opire has available rewards but issue status is CLOSED; rejected.

No third-party claim comments, branches, PRs, or repository mutations were performed.

---

# Algora scan

Disposition: `NO_OPEN_PUBLIC_BOUNTIES` at scan time. No worker assignment minted.

---

# Opire / TypeORM #3357

- Repo: `typeorm/typeorm`
- Issue: #3357 — Migration generation drops and creates columns instead of altering resulting in data loss
- GitHub state: OPEN
- Opire funding: $590 available across 12 rewards at scan time
- Language/domain: TypeScript; migrations/schema/Postgres
- Reproduction: changing varchar length 50→51 generates DROP+ADD instead of ALTER COLUMN, risking data loss.
- Disposition: `INGESTED_NOT_READY`; broad cross-driver migration semantics and heavy concurrent solver activity make a bounded patch irresponsible without full upstream checkout/integration matrix.

---

# Opire / qtop Challenge #6 — stale listing scar

Opire listed $220 for qtop/qtop Challenge #6 during the live scan. Exact GitHub issue #433 is CLOSED with state reason `completed`.

Disposition: `REJECT_STALE_FUNDING_LISTING`; no assignment or patch.

---

# Opire/docs French bounty — stale listing scar

Opire landing listed the French docs bounty during the live scan. Exact GitHub issues `Opire/docs#2` and bounty wrapper `#27` are CLOSED.

Disposition: `REJECT_STALE_FUNDING_LISTING`; no assignment or patch.

---

# GitHub native bounty — Loru #19

Funding: 25 MRG (MergeOS ledger credit; not represented as USD).
Acceptance: add `CONTRIBUTING.md` with setup/test/PR checklist/claim flow and link it from README.
Parent: `a2d332c790ea88bb2139c386d913195e7c8dce9e`.
Disposition: `READY_FOR_PR_STAGED`; external claim/PR not submitted.

---

# GitHub native bounty — PlantGuide #10

Funding: 50 MRG (MergeOS ledger credit; not represented as USD).
Acceptance: publish schemas and optional TypeScript contracts; schema must match Python payload; README integration section.
Parent: `2b9ed0e3169026e5c809bf563c1e3c71f1afc30e`.
Exact contract owner: `src/plantguide/integrations/sdk.py` (`plantguide.sdk.v1`).
Disposition: `READY_FOR_PR_STAGED`; external claim/PR not submitted.

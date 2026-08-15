# WO-LIVE-BOUNTY-HARVESTER-001 — Harvest Index

- Coordinate: `AD:BOUNTY:HARVEST-EXECUTE:001`
- Lead: W1
- Fleet: W1-W9
- State: STAGED / HUMAN-DISPATCHED / NO EXTERNAL CLAIMS OR PRS SUBMITTED
- AuraOS staging branch: `staging/wo-live-bounty-harvester-001`
- Base main observed: `c4f0cdf875d1b1aba221cf4e34c6bd1ce3879ab9`

## Triad routing

### Triad 1 — W1/W2/W3: source + reproduction + structural diff
- W1: funding/currentness verification and source-owner resolution.
- W2: repo constraints, acceptance criteria, and deterministic reproduction design.
- W3: structural/AST/diff surface analysis; no code claim unless exact source is resolved.

### Triad 2 — W4/W5/W6: patch + isolated verification
- W4: patch implementation.
- W5: adversarial/negative tests.
- W6: clean-room rerun and acceptance-matrix check.

### Triad 3 — W7/W8/W9: PR packet + validation + receipt
- W7: PR narrative and exact evidence boundaries.
- W8: independent pass/fail review against issue acceptance criteria.
- W9: artifact hashes and Merkle receipt.

## Harvest disposition

### READY_FOR_PR after external claim prerequisites
1. `mergeos-bounties/Loru#19` — 25 MRG documentation bounty.
   - Open GitHub issue with `bounty` and `reward:25-mrg` labels.
   - Patch produced: `CONTRIBUTING.md` plus README backlink hunk.
   - Structural verification PASS.
   - **External claim prerequisites remain pending**: stars/comments required by source policy before opening a payout-eligible PR.

### Provider-funded ANALYZE queue — no PR-ready claim minted
- `typeorm/typeorm#3357` — TypeScript migration/schema data-loss issue; Opire currently lists $590 and command available. High contention/deep migration test matrix.
- `strapi/strapi#11998` — TypeScript core-database nested-filter `deleteMany`; Opire currently reports Status Open with 3 available rewards totaling $70 and 0 paid rewards.
- `storybookjs/storybook#12641` — TypeScript controls/select issue; Opire currently lists $263 and command available.
- `qtop/qtop#433` — Python CI/testing challenge; Opire currently lists $220 and command available; broad acceptance surface, Python 3.6 compatibility and GitHub/GitLab parity requirements.

### TECHNICALLY_VERIFIED but funding-provider unresolved
- `claude-builders-bounty/claude-builders-bounty#3` — destructive Bash PreToolUse hook.
  - GitHub issue/board declares `$100` and “powered by Opire”, but bounded live Opire lookup did not resolve a current reward page for this exact issue.
  - Implementation and isolated tests PASS; artifact is staged outside funded READY_FOR_PR until provider funding resolves.

### EXCLUDED / BLOCKED
- AgentShield $1,000 rules-engine challenge: source explicitly says human contributors only and AI-generated/automated submissions are rejected. Ineligible for this worker fleet.
- Tenstorrent T3K model bring-up: hardware-required; no T3K execution environment here.
- Thrixel Roblox $2,000: requires Developer Program registration, two finished games, playable links and videos; external human/platform prerequisites unresolved.
- SecureBanana-style `/bounty` declarations without a source-resolved current funding record: funding unresolved; not promoted.
- Algora: bounded live scan found open bounties, but the currently visible ProjectDiscovery examples were Go/CI work rather than the requested Python/TypeScript/AST/SQLite/documentation execution lanes; no Algora item was promoted in this run.

## Source anchors

- Opire home: https://app.opire.dev/home
- Strapi Opire issue: https://app.opire.dev/issues/01HWT2MKE4GWPJXDPMAFEAHHHE
- GitHub Loru #19: https://github.com/mergeos-bounties/Loru/issues/19
- Loru bounty policy: https://github.com/mergeos-bounties/Loru/blob/master/docs/BOUNTY.md
- Claude-builders #3: https://github.com/claude-builders-bounty/claude-builders-bounty/issues/3
- Algora ProjectDiscovery open board: https://algora.io/projectdiscovery/bounties?status=open

## Negative-space law

A bounty title, label, issue body, solver claim, passing local test, or PR-ready patch is **not payment evidence**. No claim comments, wallet signatures, external PRs, merges, or payout assertions were made by this work order.

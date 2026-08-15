# Live Bounty Harvest — 2026-08-15

Work order: `WO-LIVE-BOUNTY-HARVESTER-001`  
Coordinate: `AD:BOUNTY:HARVEST-EXECUTE:001`  
Execution mode: source-current, fail-closed, no external claims or wallet actions.

## Selection law

An issue enters the execution lane only when (a) it is currently open, (b) a reward/funding mechanism is visible from the platform or issue source, (c) its repository and constraints can be source-bound, and (d) the requested work can be tested without pretending unavailable infrastructure exists. `bounty` labels are discovery metadata, not payment proof.

## Scan summary

| Lane | Candidate | Funding/currentness | Fit | Disposition |
|---|---|---|---|---|
| Opire/GitHub | `claude-builders-bounty/claude-builders-bounty#3` destructive Bash PreToolUse hook | Open; issue advertises **$100 powered by Opire**, payment on merge; very high competition | Python / security / docs | **PATCH_STAGED_VERIFIED** |
| GitHub/MergeOS | `mergeos-bounties/PlantGuide#10` JSON Schema + TypeScript contracts | Open; **50 MRG** ledger credit after review/merge | Python payloads / TypeScript / docs | **PATCH_STAGED_VERIFIED** |
| GitHub/MergeOS | `mergeos-bounties/Loru#19` CONTRIBUTING + good-first path | Open; **25 MRG** ledger credit after review/merge | Documentation / Python project | **PATCH_STAGED_VERIFIED** |
| Opire | `typeorm/typeorm#3357` migration column recreation/data-loss issue | Opire shows open **$590** reward; crowded and deep migration surface | TypeScript / database | INTAKE_ONLY_HIGH_COMPLEXITY |
| Opire | `aueangpanit/electron-template#1` context-menu issue | Opire shows open **$100** reward | TypeScript | BLOCKED_SOURCE_MATERIALIZATION (GitHub source unavailable through connected repo plane) |
| Opire | `qtop/qtop` issue #207 | Opire lists **$117** open reward | Python / HPC | INTAKE_ONLY_ENVIRONMENT_HEAVY |
| Algora | `CapSoftware/Cap#1540` deeplinks + Raycast extension | Algora project page shows one open bounty at **$0.10**, while issue prose says **$200** | TypeScript/Raycast | INTAKE_ONLY_FUNDING_DISCREPANCY_HIGH_COMPETITION |
| GitHub | AgentShield mirrored bounty | Open mirror advertises USD bounty but source states **human contributors only / AI submissions rejected** | Python/security | EXCLUDED_POLICY |

## Triad allocation

### Triad 1 — W1/W2/W3: analysis, reproduction, structural diff
- W1: source/currentness and funding gate; candidate ranking.
- W2: target-tree hydration and minimal reproduction surfaces.
- W3: structural/AST-style diff review: identify changed interfaces, commands, schemas, and negative space before implementation.

### Triad 2 — W4/W5/W6: patch + isolated verification
- W4: Claude Code destructive-command hook and regression matrix.
- W5: PlantGuide JSON Schema + TypeScript contracts and isolated schema/TypeScript checks.
- W6: Loru CONTRIBUTING/README documentation patch and source-command verification.

### Triad 3 — W7/W8/W9: PR packaging, pass validation, Merkle evidence
- W7: package unified patches and PR notes.
- W8: re-check pass evidence and fail-closed residues.
- W9: compute SHA-256 leaves and Merkle root; bind receipt.

## Negative space

- No `/opire try`, `/claim`, star/follow, wallet signature, bond, or bounty reservation was submitted.
- No third-party repository was mutated and no PR was opened.
- MRG is recorded as MRG ledger credit, not converted to USD.
- Advertised bounty value is not settlement proof; payout remains governed by each platform/repository.
- Human-only bounty programs were excluded from autonomous execution.

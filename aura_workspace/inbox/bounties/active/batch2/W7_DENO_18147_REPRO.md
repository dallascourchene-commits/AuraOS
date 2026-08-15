# W7 — Batch 2 Reproduction Harness: denoland/deno#18147

WORK_ORDER: WO-FLEET-PHASE3-DEPLOY-001
COORDINATE: AD:FLEET:PHASE3:001
WORKER: W7
STATE: ACTIVE_REPRODUCTION_CANDIDATE / NO_CLAIM / NO_PR
SOURCE_CLASS: PRIMARY_NEAR_MATCH

## Source binding
- Successor Batch-2 source: `BATCH2_BOUNTY_TARGET_SCAN__WC-03__2026-08-15.md`
- Source Drive ID: `1cfauvRQjXoHly6bXi74sYh2ndx5BtyGICXKMZk2Id0Q`
- Target: `denoland/deno#18147` — `feat: view test coverage in editor`
- Current owner state rechecked 2026-08-15: OPEN / state_reason=REOPENED / assignees=[] / labels include `feat`, `lsp`, `testing`
- Last upstream update observed: 2026-08-09T05:39:03Z

## Fit boundary
This is the strongest source-current Rust developer-tooling/LSP/testing target in the resolved Batch-2 scan. It is **not** relabeled as an exact Rust CLI/parser bounty.

## Isolated reproduction objective
Determine the smallest current Deno LSP/testing surface needed to reproduce the requested editor-visible test-coverage behavior without modifying upstream. Produce only a bounded evidence package:
1. identify current coverage-producing command/data path;
2. identify current LSP/editor capability surface that could carry coverage ranges;
3. identify existing tests/fixtures nearest the requested behavior;
4. produce a failing or missing-capability reproduction if source-resolvable;
5. record exact upstream commit before any implementation proposal.

## Mutation boundary
- NO `/opire try`
- NO issue comment
- NO fork/branch/PR
- NO payment/wallet action
- NO implementation claim until exact current upstream source is hydrated
- RECHECK issue state and competition immediately before any later claim or PR transition

## Acceptance
`REPRO_READY` only when exact source locations, current upstream head, reproduction command, observed output, and minimal implicated test surface are recorded. Otherwise emit `SOURCE_GAP` or `NOT_REPRODUCED`.

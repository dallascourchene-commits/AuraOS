# BATCH 2 BOUNTY TARGET SCAN — PYTHON AST + RUST CLI

**War Capsule:** WC-03 / Triad 3  
**Coordinate:** `AD:BOUNTY:UPSTREAM-DISBURSEMENT:002`  
**Scan date:** 2026-08-15  
**State:** `LIVE_SCAN_COMPLETE / EXACT_FIT_EMPTY / WATCHLIST_OPEN`

## 0. Selection law

A target is `READY_TO_CLAIM` only if all are true:

1. funding/reward is currently source-visible,
2. upstream issue is open/current,
3. language/domain fits the requested lane,
4. issue scope is reproducible without hidden infrastructure,
5. claim terms do not conflict with Aura's human-authority boundary.

Near matches remain `WATCH_NEAR_MATCH`; anomalous reward displays remain `BLOCK_FUNDING_ANOMALY`.

## 1. Opire live feed snapshot

Source: `https://app.opire.dev/home`  
Observed on 2026-08-15:

- paid bounties: 44
- available bounties: 330
- paid out: `$4,975.87`
- displayed open value: `$1,914,294.22`

### Python lane

#### O-PY-01 — MisakaNet: `[Test] Windows Voice hook verification`
- language: Python / JavaScript / Shell
- displayed reward: `$1,500`
- visible solvers: 1
- fit: tooling/hook verification
- AST-specific: **NO**
- disposition: `WATCH_NEAR_MATCH_PYTHON_TOOLING_NOT_AST`
- reason: attractive reward and low visible contention, but the surfaced scope is hook verification, not Python AST/parser work.

#### O-PY-02 — qtop Challenge #6: improve testing and CI/CD cycles
- language: Python
- displayed reward: `$220`
- visible solvers: 6
- fit: code-management/tooling
- AST-specific: **NO**
- disposition: `WATCH_NEAR_MATCH_PYTHON_TOOLING_NOT_AST`
- reason: Python engineering work, but no source-visible AST/parser acceptance surface in the feed listing.

#### O-PY-03 — qtop differential-debugging cluster task
- language: Python
- displayed reward: `$117`
- visible solvers: 6
- fit: debugging / HPC execution
- AST-specific: **NO**
- disposition: `DEFER_INFRASTRUCTURE_DEPENDENCY`
- reason: requires execution across two HPC clusters; not a clean local AST lane.

### Rust lane

#### O-RS-01 — Zed: `Helix keymap`
- language: Rust
- displayed reward: `$395`
- source issue status: OPEN
- visible solvers: 6
- available reward detail was visible on Opire
- CLI-specific: **NO**
- disposition: `WATCH_NEAR_MATCH_RUST_EDITOR_NOT_CLI`
- reason: serious Rust codebase and source-visible reward, but the issue is editor keymap behavior rather than a CLI tool.

#### O-RS-02 — Deno: `feat: view test coverage in editor`
- language: Rust
- displayed reward: `$70`
- source issue status: OPEN
- visible reward count: 1
- CLI-specific: **NO**
- disposition: `WATCH_NEAR_MATCH_RUST_RUNTIME_LSP_NOT_CLI`
- reason: Deno is a Rust-based runtime/CLI ecosystem, but this issue's acceptance surface is editor/LSP coverage.

#### O-RS-03 — esp-hal: Ethernet peripheral support
- language: Rust
- displayed live-feed reward: `$120`
- visible solvers: 2
- CLI-specific: **NO**
- disposition: `EXCLUDE_EMBEDDED_HAL`
- reason: embedded hardware abstraction layer work, not CLI tooling.

#### O-RS-04 — `zeroeye` deterministic data seed
- languages shown: TypeScript / Rust / Python
- title contains `($50)`
- live feed displayed aggregate value: `$100,100`
- visible solvers: 7
- disposition: `BLOCK_FUNDING_ANOMALY`
- reason: title/reward display materially conflict; no claim until reward-level provenance is reconciled.

## 2. Algora scan

Source-verified open Algora pages surfaced during this run included:

### A-01 — ProjectDiscovery / nuclei
- open bounties: 2
- reward: `$100` each
- visible scopes:
  - panic → error handling in template loader
  - typos tool integration into CI
- language/domain: Go
- disposition: `EXCLUDED_LANGUAGE`

### A-02 — Cap
- open bounties: 1
- displayed reward: `$0.10`
- scope: Deeplinks + Raycast Extension
- visible claims: 35
- disposition: `EXCLUDED_FIT_AND_VALUE`

### A-03 — Kyo
- open page surfaced gRPC-support reward entries
- fit to requested Python-AST/Rust-CLI lanes: not established
- disposition: `DEFER_DOMAIN_MISMATCH`

## 3. Exact-fit result

No source-verified **exact Python-AST** or **exact Rust-CLI** bounty was found in the accessible live/indexed Algora + Opire feed surfaces during this scan.

That is not equivalent to “none exist anywhere.” It means:

`EXACT_FIT_READY_TO_CLAIM = 0`

The scan refuses to relabel generic Python tooling as AST work or generic Rust work as CLI work.

## 4. Batch 2 watch order

Priority for the next hydration pass:

1. Search terms: `AST`, `parser`, `syntax tree`, `tree-sitter`, `linter`, `codegen`, `formatter`.
2. Rust terms: `CLI`, `command-line`, `terminal`, `subcommand`, `clap`, `arg parser`.
3. Re-check Opire O-PY-01 and O-RS-01 for newly narrowed child issues that fit the exact lanes.
4. Reconcile O-RS-04 reward anomaly before any engineering time is spent.
5. Keep Algora exact-fit scan active; do not substitute nonmatching language bounties merely to fill the batch.

## 5. Current Batch 2 disposition

`SCAN_COMPLETE / 0 EXACT-FIT CLAIMS / 4 WATCH_NEAR_MATCH_OR_RECHECK / 1 FUNDING_ANOMALY / NO_EXTERNAL_CLAIMS`

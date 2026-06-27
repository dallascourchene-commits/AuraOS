# Aura ICM Workspace — Human-Readable Control Surface

## Overview

The **ICM (Interoperable Control Module) workspace** is a human-readable filesystem layer for Aura Arena runs. It provides an audit, edit, and review surface without replacing any live subsystem.

> **Design rule:** ICM folders are references, reports, and audit artifacts. Exact truth remains in sidecars: prices, transactions, posts, timestamps, balances, source snapshots, code files, and tests.

---

## Layer Mapping

| Layer | Content | Physical Location |
|-------|---------|-------------------|
| **Layer 0** | Aura identity / domain axioms | `AURA.md` |
| **Layer 1** | Arena workspace routing | `CONTEXT.md` |
| **Layer 2** | Stage ActionCapsule + BoundaryContract | `stages/NN_name/CONTEXT.md` |
| **Layer 3** | Stable references / schemas / policies / CODEMAP / sidecar schemas | `stages/NN_name/references/` |
| **Layer 4** | Per-run artifacts, outputs, deltas, verifier results | `stages/NN_name/output/` |

---

## Folder Layout

```
<workspace_root>/
└── 001_arena_run_objective/
    ├── AURA.md                  # Layer 0 — identity and axioms
    ├── CONTEXT.md               # Layer 1 — routing overview
    ├── boundary_contracts.jsonl # All contracts from the transaction
    ├── verifier_report.json     # Verifier outcomes per stage
    ├── qdkt_events.jsonl        # QDKT observations (export + human edits)
    ├── dream_scores.jsonl       # DREAM-lite training rows
    ├── metadata.json            # Workspace metadata snapshot
    └── stages/
        ├── 01_stage_name/
        │   ├── CONTEXT.md        # Layer 2 — capsule + contracts
        │   ├── references/       # Layer 3 — stable refs
        │   │   ├── codemap.json
        │   │   └── schema.json
        │   └── output/           # Layer 4 — per-run artifacts
        │       ├── diff.json
        │       └── human_edit_tester_20240101_120000.md
        └── 02_next_stage/
            ├── CONTEXT.md
            ├── references/
            └── output/
```

---

## File Reference

### `AURA.md` (Layer 0)
- ICM version and workspace ID
- Arena ID, version, domain
- Exported timestamp
- Five axioms that govern the workspace boundary
- Explicit layer mapping table

### `CONTEXT.md` (Layer 1)
- Arena routing summary
- Stage table with inputs, outputs, verifier gates, review status
- Invariants (e.g., "No stage may skip verifier gates")

### `stages/NN_name/CONTEXT.md` (Layer 2)
Every stage must declare:
- **Inputs** — explicit required inputs
- **Process** — what the stage does
- **Outputs** — promised outputs
- **Allowed Actions** — permitted operations
- **Forbidden Actions** — blocked operations
- **Verifier Gates** — names of verifier checks
- **Human Review Status** — `pending`, `approved`, or `rejected`
- **ActionCapsule** — full capsule JSON
- **BoundaryContracts** — all contracts scoped to this stage

### `stages/NN_name/references/` (Layer 3)
Stable JSON references, schemas, and policies stored as individual `.json` files. Examples:
- `codemap.json` — CODEMAP snapshot
- `sidecar_schema.json` — sidecar schema reference
- `policy.json` — domain policy reference

### `stages/NN_name/output/` (Layer 4)
Per-run artifacts and deltas stored as individual `.json` files, plus human edit diffs as `.md` files. Examples:
- `diff.json` — code diff artifact
- `report.json` — verifier report snippet
- `human_edit_<editor>_<timestamp>.md` — human edit diff with before/after

### `boundary_contracts.jsonl`
Newline-delimited JSON of all boundary contracts in the transaction, one per line. Deterministic truth lives in the Arena lease ledger; this file is a materialized reference copy.

### `verifier_report.json`
Structured verifier outcomes per stage or globally. May contain `approved`, `blockers`, `warnings`, and `requires_live_recheck_before_booking` flags.

### `qdkt_events.jsonl`
Newline-delimited JSON of QDKT observations. Includes:
- `icm_workspace_export` event (written at export time)
- `human_edit` events (written when a human edits stage output)

### `dream_scores.jsonl`
Newline-delimited JSON of DREAM-lite training rows. Each row contains:
- `candidate_id`, `candidate_type`, `query`
- `usefulness_score`, `semantic_score`
- `verifier_result`, `failure_reason`

### `metadata.json`
Workspace-level metadata snapshot including:
- `icm_version`, `workspace_id`, `folder_name`, `txn_id`
- `exported_at`, `domain`, `arena_id`, `stage_count`


---

## Human Review Workflow

1. **Export** — The Arena or CLI exports a transaction into a numbered workspace.
2. **Review** — A human opens `AURA.md` and `CONTEXT.md` to understand the run.
3. **Inspect Stage** — Navigate to `stages/NN_name/CONTEXT.md` to see allowed/forbidden actions, verifier gates, and review status.
4. **Edit** — If a human edits a stage output, call `record_human_edit(...)` (or use the CLI). This writes a diff to `output/` and records a QDKT observation.
5. **Import** — Use `import_workspace(...)` to reconstruct the workspace for validation or replay.

---

## CLI Usage

```bash
# Export a transaction JSON to an ICM workspace
python aura_icm_cli.py export txn.json ./icm_workspaces --domain code --arena-id ARENA-1

# Import a workspace back to JSON
python aura_icm_cli.py import ./icm_workspaces/001_arena_run --out workspace.json

# List all workspaces under a root
python aura_icm_cli.py list ./icm_workspaces
```

---

## Integration with Arena Subsystems

- **Liquid Planning Arena** — `LiquidPlanningArena.export_arena_to_icm(...)` converts an arena run into an ICM workspace.
- **Travel Package Arena** — `TravelPackageArena.export_candidate_to_icm(...)` exports a single verified candidate.
- **UnifiedQDKT** — Human edits and exports are recorded as QDKT observations.
- **DREAM-lite** — Context candidates and verifier outcomes are emitted as DREAM-lite training rows.

---

## Invariants

1. Exact truth remains in sidecars.
2. ICM folders are an audit/edit/review layer, not the source of deterministic truth.
3. ICM does not replace live routing, multi-agent orchestration, or any Arena subsystem.
4. Every stage must declare explicit inputs, process, outputs, allowed actions, forbidden actions, verifier gates, and human review status.
5. No stage may skip verifier gates or human review before production mutation.


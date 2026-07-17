# SCO Construction Arena — Phase 4 E9–E12 Temporal Persistence Verification

```yaml
document_status: VERIFIED_PENDING_PINNED_MERGE
document_version: 2.0.0
date: 2026-07-17
baseline_main: c77e6d6558b2ee4f4c7f7c9160eff16e8ec0e4c5
verified_implementation_head: d37fbffcebb84527fd4343c4babc70b938395421
branch: refactor/sco-construction-persistence-e9-e12
pull_request: 150
phase_scope:
  - E9_HUMAN_AGENT_CONSTRUCTION_PROFILE
  - E12_TEMPORAL_PERSISTENCE
  - CODING_ARENA_PERSISTENCE
  - HUMAN_AGENT_ARENA_PERSISTENCE
  - AGENT_BRIDGE_ARENA_PERSISTENCE
  - CONSTRUCTION_ARENA_PERSISTENCE
coderabbit_explicit_invocations: 1
coderabbit_result: CHECK_SUCCESS_NO_SUBMITTED_REVIEW_OR_INLINE_THREADS
automatic_restore: false
automatic_hotswap: false
automatic_commit: false
automatic_push: false
automatic_merge: false
physical_work_authority: false
payment_release_authority: false
access_control_authority: false
professional_certification_authority: false
legal_immutability_claimed: false
court_admissibility_claimed: false
```

## Council decision

`RefactorStateLedger V3` already preserves compact intra-session execution state, and Crucible preserves governed learning across sessions. The verified gap was durable, content-addressed continuation shared by Aura's Arenas.

The implemented solution is a generic Temporal Persistence Engine beneath the Arenas, not a second Construction truth store.

```text
existing arena state owner
  → narrow canonical projection
  → content-addressed TemporalCheckpoint
  → append-only parent/fork registry
  → exact HEAD and invariant assessment
  → DIRECT_RESUME_REVIEW_REQUIRED
     | MITOSIS_REQUIRED
     | RESTORATION_COUNCIL_REQUIRED
  → existing Arena guards and verifier
  → human review
```

## Canonical ownership

| Capability | Owner | Verified disposition |
|---|---|---|
| Intra-session refactor continuity | `aura_refactor_state_ledger_core.py` | `REUSED` |
| Stable normalization and identity | `aura_refactor_state_identity.py` | `REUSED` |
| Durable checkpoint and registry | `aura_temporal_persistence.py` | `NEW_GENERIC_OWNER` |
| Requested registry surface | `aura_persistence_registry.py` | `COMPATIBILITY_FACADE` |
| Restoration decision capsule | `aura_restoration_commander.py` | `REVIEW_GATED` |
| Temporal WFST guard | `aura_wfst_temporal_adapter.py` | `NARROW_ADAPTER`; no active grammar mutation |
| Cross-arena projections | `aura_arena_persistence_adapters.py` | `GENERIC_ADAPTER_OWNER` |
| Agent Bridge integration | `aura_agent_arena_persistence_bridge.py`, `aura_agent_arena_mcp.py` | `INTEGRATED` |
| Human Agent integration | `aura_human_agent_arena_server.py` | `INTEGRATED` |
| Coding Workbench integration | `aura_coding_workbench_wfst_adapter.py` | `INTEGRATED` |
| Construction state | `aura_construction_state.py` | `REUSED`; checkpoint projection only |
| Observatory | checkpoint metadata projection | `READ_ONLY`; payload omitted |
| Automatic model replan | none | `FORBIDDEN_IN_THIS_SLICE` |
| Automatic live-state application | none | `FORBIDDEN` |

## Persistence semantics

Checkpoint identity binds Arena/session identity, exact repository HEAD, parent checkpoint, branch name, sequence number, canonical payload digest, invariant digests, source kind, and authority boundaries. Wall-clock creation metadata is excluded from checkpoint identity so identical replay remains idempotent, but it is included in the full record digest.

Registry entries are append-only and digest chained. Verification now validates both the registry chain and every referenced checkpoint file, including duplicated registry metadata. Checkpoint paths are repository confined and written atomically under `Aura_Memory/checkpoints/`.

File locking fails closed and supports POSIX `fcntl` and Windows `msvcrt`. An unsupported or failed lock backend cannot silently disable serialization.

## Temporal WFST semantics

`TEMP` is guard evidence, not active grammar mutation:

- `TEMP:CURRENT`
- `TEMP:STALE`
- `TEMP:FUTURE`
- `TEMP:BRANCH_OFFSET`
- `TEMP:UNKNOWN`

Stale, future, unknown, and branch-offset state cannot bypass existing direction, aspect, evidence, authority, consent, lease, or verifier guards.

## Arena integration

### Coding Workbench

The guarded session exposes checkpoint, restore-assessment, restoration-packet, and checkpoint-list methods. Restore never changes `WorkbenchState` automatically.

### Human Agent Arena

The local server exposes checkpoint creation, metadata listing, read-only checkpoint projection, restore assessment, restoration packets, and cross-Arena handoff. Observatory projection excludes checkpoint payloads.

### Agent Bridge Arena

The MCP surface exposes:

```text
aura_checkpoint_session
aura_list_checkpoints
aura_restore_checkpoint
aura_fork_checkpoint
aura_handoff_checkpoint
```

These tools cannot stage a patch, promote a hotswap, commit, push, open a pull request, or merge.

### Construction Arena

`ConstructionProjectState` projects into the generic registry while retaining the project state digest, event-chain digest, proposal-only flag, and physical-authority boundary.

## Verified evidence

Exact pre-CodeRabbit audit run `29602039592`, artifact `8415408411`:

- Python 3.11 compile: PASS;
- fatal Ruff selection: PASS;
- focused temporal-persistence tests: `25/25` PASS in `1.27s`;
- selected canonical-owner regressions: `95/95` PASS in `1.80s`;
- aggregate coverage across the five persistence owners: `84%`;
- `aura_temporal_persistence.py`: `85%`;
- `aura_wfst_temporal_adapter.py`: `91%`;
- `aura_arena_persistence_adapters.py`: `83%`;
- `aura_agent_arena_persistence_bridge.py`: `71%`;
- `aura_restoration_commander.py`: `67%`;
- registry/CLI/MCP boundary gate: PASS;
- CODEMAP and topology generation: PASS.

The complete machine-readable record is `docs/evidence/AURA_SCO_PHASE4_E9_E12_TEMPORAL_PERSISTENCE.json`.

## Manual adversarial hardening

The final sweep repaired registry verification that previously checked only JSONL, registry/file metadata divergence, explicit empty fork payload loss, non-finite timestamp acceptance, incomplete record-digest binding, silent lock degradation, two dead Coding Workbench imports, missing committed seed fixtures in the audit checkout, and map-only branch-write races.

## CodeRabbit result

CodeRabbit was invoked exactly once with command comment `5006045090`. Invocation `18886d52-813b-4e14-a514-b75398f22a3f` completed with a successful commit check. It submitted no review and created no inline threads, so there were no CodeRabbit-suggested code changes to apply. It will not be invoked again for this phase.

## Claim boundaries

This phase does not establish real-project deployment, field safety effectiveness, provider token/cost savings, automatic Restoration Council calls, automatic MITOSIS execution, automatic state application, legal immutability, court admissibility, or production readiness.

All restoration paths remain proposal/review paths. Human review is mandatory, patch authority remains `exact_source_spans_and_hashes_only`, and VSA patch authority remains false.

## Final sequence

```text
verified implementation and manual hardening
  → one CodeRabbit invocation and completed clean result
  → synchronized README / ARCHITECTURE / USER_GUIDE / evidence
  → regenerated CODEMAP and topology
  → final exact-head audit
  → mark PR ready
  → pinned-head merge
  → post-merge verification
```

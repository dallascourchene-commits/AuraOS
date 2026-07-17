# SCO Construction Arena — Phase 4 E9–E12 Temporal Persistence Plan

```yaml
document_status: IMPLEMENTING
document_version: 1.0.0
date: 2026-07-17
baseline_main: c77e6d6558b2ee4f4c7f7c9160eff16e8ec0e4c5
branch: refactor/sco-construction-persistence-e9-e12
phase_scope:
  - E9_HUMAN_AGENT_CONSTRUCTION_PROFILE
  - E12_TEMPORAL_PERSISTENCE
  - CODING_ARENA_PERSISTENCE
  - HUMAN_AGENT_ARENA_PERSISTENCE
  - AGENT_BRIDGE_ARENA_PERSISTENCE
  - CONSTRUCTION_ARENA_PERSISTENCE
coderabbit_policy: TRIGGER_ONCE_AFTER_MANUAL_AND_EXECUTABLE_GATES
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

The persistence proposal identifies a real architectural gap: `RefactorStateLedger V3` preserves compact execution state inside a session, and Crucible preserves verified learning across sessions, but there is no generic content-addressed checkpoint and restoration gate shared by Aura's Arenas.

The solution is a new generic persistence owner beneath the Arenas, not a second Construction truth store.

```text
existing arena state owner
  → narrow canonical projection
  → TemporalCheckpointRegistry
  → parent/fork DAG
  → restoration assessment
  → existing Arena guards
  → verifier
  → human review
```

## Canonical ownership

| Capability | Owner | Decision |
|---|---|---|
| Intra-session refactor continuity | `aura_refactor_state_ledger_core.py` | `REUSE` |
| Stable normalization and identity | `aura_refactor_state_identity.py` | `REUSE` |
| Durable checkpoint and registry | `aura_temporal_persistence.py` | `NEW_GENERIC_OWNER` |
| Requested registry facade | `aura_persistence_registry.py` | `COMPATIBILITY_FACADE` |
| Restoration decision capsule | `aura_restoration_commander.py` | `NEW_REVIEW_GATED_COMMANDER` |
| Temporal WFST guard | `aura_wfst_temporal_adapter.py` | `NEW_NARROW_ADAPTER` |
| Cross-arena projections | `aura_arena_persistence_adapters.py` | `NEW_GENERIC_ADAPTER_OWNER` |
| Agent Bridge integration | `aura_agent_arena_persistence_bridge.py`, `aura_agent_arena_mcp.py` | `INTEGRATE` |
| Human Agent integration | `aura_human_agent_arena_server.py` | `INTEGRATE` |
| Coding Workbench integration | `aura_coding_workbench_wfst_adapter.py` | `INTEGRATE` |
| Construction state | `aura_construction_state.py` | `REUSE`; checkpoint projection only |
| Observatory | checkpoint metadata projection | `READ_ONLY` |
| Automatic model replan | none | `DEFERRED_AND_FORBIDDEN_IN_THIS_SLICE` |
| Automatic live-state application | none | `FORBIDDEN` |

## Persistence semantics

Checkpoint identity binds:

- Arena and session identity;
- exact repository HEAD;
- parent checkpoint and branch name;
- sequence number;
- canonical payload digest;
- invariant digests;
- source-kind and authority boundaries.

Wall-clock creation metadata is excluded from checkpoint identity so identical replay remains idempotent.

Registry entries are append-only and digest chained. Checkpoint files are atomically written under `Aura_Memory/checkpoints/` and must remain confined to the repository persistence root.

## Restoration decisions

```text
HEAD + invariants match
  → DIRECT_RESUME_REVIEW_REQUIRED

remaining work > 75% of declared Surgeon context
  → MITOSIS_REQUIRED

HEAD or invariant changed
  → RESTORATION_COUNCIL_REQUIRED
```

No decision applies state. The Restoration Commander returns a capsule for the existing verifier and human-review path.

## Temporal WFST semantics

`TEMP` is projected as guard evidence rather than mutating the active grammar:

- `TEMP:CURRENT`
- `TEMP:STALE`
- `TEMP:FUTURE`
- `TEMP:BRANCH_OFFSET`
- `TEMP:UNKNOWN`

Stale, future, and branch-offset state fail closed. Existing direction, aspect, evidence, authority, consent, lease, and verifier guards remain authoritative.

## Arena integration

### Coding Workbench

The guarded Coding Workbench session gains checkpoint, assessment, restoration-packet, and list methods. Restore never changes `WorkbenchState` automatically.

### Human Agent Arena

The local server gains checkpoint metadata, checkpoint creation, restore assessment, restoration packet, and cross-Arena handoff endpoints. Observatory projection excludes payloads.

### Agent Bridge Arena

The MCP server uses a persistence-enabled bridge and exposes checkpoint, list, restore, fork, and handoff tools. These tools cannot stage or promote a patch.

### Construction Arena

`ConstructionProjectState` is projected into the generic registry while preserving its exact event chain, state digest, proposal-only flag, and physical-authority boundary.

## Claim boundaries

This phase does not establish:

- real-project deployment;
- field safety effectiveness;
- provider token or cost savings;
- automatic premium-model Restoration Council calls;
- automatic MITOSIS execution;
- automatic state application;
- legal immutability;
- court admissibility;
- production readiness.

## Required gates

1. exact Python 3.11 compile;
2. fatal Ruff checks;
3. focused persistence and cross-Arena tests;
4. persistence-module statement coverage;
5. State Ledger, Human Agent, Coding Workbench, Agent Bridge, and Construction owner regressions;
6. registry tamper and path-confinement tests;
7. stale/future/branch-offset WFST tests;
8. README, ARCHITECTURE, USER_GUIDE, Agent Bridge docs, and handoff-log synchronization;
9. regenerated CODEMAP and topology validation;
10. manual CodeRabbit-style adversarial sweep;
11. one CodeRabbit invocation;
12. wait for CodeRabbit response, apply findings, rerun gates;
13. pinned-head merge and post-merge verification.

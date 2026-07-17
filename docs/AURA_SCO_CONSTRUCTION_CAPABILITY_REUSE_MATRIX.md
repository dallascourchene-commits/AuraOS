# SCO Construction Arena — Capability Reuse Matrix

```yaml
document_status: E0_E14_COMPLETION_IN_PROGRESS
document_version: 2.0.0
date: 2026-07-17
baseline_main: 62b967be2fc1150c3d52e1624d4d2b6af234d05a
branch: refactor/sco-construction-e9-e14-completion
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

## Decision rule

```text
existing canonical owner
  | narrow domain adapter/profile
  | exact capability gap
  | explicit policy deferral
```

| Capability | Canonical owner | Decision | Current Construction disposition |
|---|---|---|---|
| Event identity and measurement | `aura_event_contracts.py` | `REUSE` | Construction records project to canonical Aura event semantics |
| Immutable-contract patterns | `aura_civic_planning_types.py` | `REUSE_PATTERN` | strict normalized immutable domain records |
| Capsules, contracts, leases, adapter lifecycle | `aura_liquid_planning_arena.py` | `REUSE` | `ConstructionArenaAdapter` composes the canonical planner |
| Grants, attestations, quorum, decisions | `aura_relational_authority.py` | `REUSE` | exact Construction action/project/evidence binding |
| Chained receipts and checkpoints | `aura_relational_authority.py`, `aura_temporal_persistence.py` | `REUSE` | continuity/content verification; actor authenticity and consequential authority remain external |
| Construction claims/evidence/events | `aura_construction_contracts.py` | `TRUE_DOMAIN_GAP` | minimal E4 owner, merged |
| Construction replay/conflict/query | `aura_construction_state.py` | `TRUE_DOMAIN_GAP` | minimal E5 owner, deterministic `ZERO_MODEL`, merged |
| Construction authority binding | `aura_construction_authority.py` | `ADD_NARROW_ADAPTER` | minimal E6 adapter, merged |
| Payment/dependency/alternative/hazard advisory | `aura_construction_adapter.py` | `ADD_NARROW_ADAPTER` | E7 proposal-only hard-filter-before-ranking lanes, merged |
| Construction Arena lifecycle | `ConstructionArenaAdapter` | `ADD_NARROW_ADAPTER` | E8 synthetic/shadow/owner-read-only adapter, merged |
| Human Agent Construction profile | `aura_construction_human_agent.py` | `ADD_NARROW_PROFILE` | E9 purpose-limited read-only review packet, active branch |
| Human Agent API/UI | `aura_human_agent_arena_server.py`, `aura_human_agent_arena/` | `EXTEND_CANONICAL_OWNER` | E9 Construction surface, active branch |
| Observatory | `ConstructionHumanAgentProfile.observatory_projection()` | `ADD_READ_ONLY_PROJECTION` | IDs, digests, statuses and gates only; no raw records or execution methods |
| Experience/Crucible | `aura_construction_learning.py` plus canonical Experience/Crucible owners | `REUSE` | E10 verified synthetic/shadow episodes; proposal-only crystallization |
| Deterministic benchmark | `aura_construction_benchmark.py` | `TRUE_TEST_GAP` | E11 zero-model candidate-order invariance arm |
| Temporal persistence | `aura_temporal_persistence.py`, `aura_arena_persistence_adapters.py` | `REUSE` | E12 checkpoints, restoration assessment, forks and payload-free handoff |
| Completion/handoff validation | `aura_construction_refactor_completion.py` | `TRUE_GOVERNANCE_GAP` | E13 machine-enforced owner/marker reconciliation |
| Final external review and merge | GitHub PR, CodeRabbit, exact-head CI | `PROCESS_GATE` | E14 pinned reviewed merge only |
| Real project connectors or consequential control | none | `DEFER_BY_POLICY` | separate future program; not an E0–E14 completion requirement |

## Gap proof

Construction-specific ownership remains intentionally small:

- E4 owns Construction scope, claim/evidence separation, evidence classes, privacy/consent/freshness, and project event semantics.
- E5 owns deterministic replay, structural conflicts, supersession, and queries.
- E6 binds those records to existing relational governance and receipts.
- E7–E8 add only the domain advisory/lifecycle adapter.
- E9 adds only a purpose-limited Human Agent/Observatory profile; it does not duplicate Construction state.
- E13 adds only a repository completion audit; it does not grant runtime authority.

## Explicit policy deferrals

Real connectors, physical control, payments, access control, professional certification, legal/regulatory decisions, and automatic restore/hotswap/commit/push/PR/merge remain outside this refactor. Their absence does not make the E0–E14 software architecture incomplete.

## Completion gate

```bash
python3 -m aura_construction_refactor_completion --repo-root .
```

The final branch must return `runtime_complete: true` and `e14_release_status: READY_FOR_PINNED_MERGE`, pass focused and inherited tests, survive independent review, and regenerate CODEMAP/topology.

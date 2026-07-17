# SCO Construction Arena — Phase 5 E9–E14 Completion Plan

```yaml
document_status: IMPLEMENTING
document_version: 1.0.0
date: 2026-07-17
baseline_main: 62b967be2fc1150c3d52e1624d4d2b6af234d05a
branch: refactor/sco-construction-e9-e14-completion
scope:
  - E9_CONSTRUCTION_HUMAN_AGENT_PROFILE
  - E9_READ_ONLY_OBSERVATORY_PROJECTION
  - E13_MACHINE_ENFORCED_HANDOFF_RECONCILIATION
  - E13_CANONICAL_DOCUMENTATION_SYNC
  - E14_PINNED_REVIEW_AND_MERGE
physical_work_authority: false
payment_release_authority: false
access_control_authority: false
professional_certification_authority: false
automatic_merge: false
```

## Tracker reconciliation

The repository tracker contains one open draft PR and two open Financial Arena issues:

- PR #130 is an old read-only analysis scaffold based on pre-Construction `main`. Its own description says it is not intended for merge.
- Issue #126 is the parent Financial Arena epic; F1.1 already merged through PR #128.
- Issue #129 is the active Financial Planning Board projection slice.

None of those items tracks the remaining SCO Construction refactor. Construction completion must therefore be derived from the original E0–E14 skeleton, merged phase evidence, canonical source, tests, and the handoff debt register.

## Actual remaining work

Merged phases already provide:

- E0–E3 reuse grounding, revisioned skeletons, and exact Action Capsules;
- E4–E6 Construction contracts, deterministic state, governance, and receipts;
- E7–E8 advisory lanes and the synthetic/shadow `ConstructionArenaAdapter`;
- E10–E11 Experience/Crucible projection and deterministic benchmark;
- E12 generic temporal persistence across Coding, Human Agent, Agent Bridge, and Construction.

The true remaining bounded gap is:

1. a Construction-specific Human Agent review profile;
2. a purpose-limited read-only Observatory projection;
3. Human Agent HTTP and browser wiring for that profile;
4. a machine-enforced completion audit that rejects stale or missing cross-Arena wires;
5. synchronized plan, reuse-matrix, handoff, README, ARCHITECTURE, USER_GUIDE, CODEMAP, and topology evidence;
6. independent final review and pinned merge.

## Architecture

```text
ConstructionProjectState
  + ConstructionCoordinationEvaluation
  → ConstructionHumanAgentProfile
      → bounded candidate summaries
      → hard blockers remain visible
      → human authority route remains external
      → no raw evidence export
  → Construction Observatory projection
      → IDs, digests, status counts, and gates only
      → no narratives, amounts, records, or execution methods
  → payload-free cross-Arena baton
  → optional review-gated TemporalCheckpoint
```

## Canonical owners

| Capability | Owner | Decision |
|---|---|---|
| Construction truth | `aura_construction_contracts.py`, `aura_construction_state.py` | `REUSE`; never duplicated |
| Proposal evaluation | `aura_construction_adapter.py` | `REUSE` |
| Human Agent profile | `aura_construction_human_agent.py` | `NEW_NARROW_PROFILE` |
| Human Agent API | `aura_human_agent_arena_server.py` | `INTEGRATE` |
| Human Agent UI | `aura_human_agent_arena/index.html`, `construction.js`, `construction.css` | `INTEGRATE` |
| Observatory | `ConstructionHumanAgentProfile.observatory_projection()` | `READ_ONLY` |
| Persistence | `aura_arena_persistence_adapters.py` | `REUSE` |
| Completion/handoff validation | `aura_construction_refactor_completion.py` | `NEW_MACHINE_GATE` |

## Explicit policy deferrals

The following are not unfinished implementation and must remain outside this refactor:

- real owner, contractor, payment, access, sensor, safety, or professional connectors;
- physical construction or equipment control;
- payment release or fund transfer;
- safety, engineering, inspection, legal, or regulatory certification;
- automatic state restoration, hotswap, commit, push, PR, or merge;
- commercial field-performance claims.

## Required gates

1. Python 3.11 compile and fatal Ruff checks;
2. focused Human Agent/Observatory and completion-validator tests;
3. all Construction adapter, state, authority, fixture, benchmark, learning, persistence, and Human Agent server regressions;
4. focused statement coverage;
5. browser-surface marker and endpoint validation;
6. `python -m aura_construction_refactor_completion --repo-root .` returns `READY_FOR_PINNED_MERGE`;
7. manual adversarial review;
8. one CodeRabbit invocation after all prior gates;
9. actionable findings repaired and regressions rerun;
10. regenerated CODEMAP/topology;
11. pinned-head merge and post-merge verification.

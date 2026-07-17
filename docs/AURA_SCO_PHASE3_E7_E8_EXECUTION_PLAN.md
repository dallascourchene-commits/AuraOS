# SCO Construction Arena — Phase 3 E7–E8 Execution Plan

```yaml
document_status: EXECUTING_BOUNDED_VERTICAL_SLICE
document_version: 1.1.2
date: 2026-07-17
baseline_main: 7edd80484629378af0658bfca0d7d4e351361831
branch: refactor/sco-construction-e7-e8
finalizer_trigger: pull_request_synchronize
phase_scope:
  - E7_ADVISORY_LANES
  - E8_SYNTHETIC_SHADOW_ADAPTER
  - E11_ZERO_MODEL_BENCHMARK_ARM
coderabbit_policy: TRIGGER_ONCE_AT_FINAL_REVIEW_GATE
coderabbit_triggered: false
production_connectors: FORBIDDEN_IN_THIS_PHASE
private_project_data: FORBIDDEN_IN_THIS_PHASE
physical_work_authority: false
payment_release_authority: false
access_control_authority: false
```

## Council determination

The current main branch already has canonical owners for immutable Construction claims and evidence, append-only state replay, supersession, conflict preservation, evidence readiness, relational governance, and chained receipt continuity. This phase does not redesign those owners.

The exact missing wire is a narrow Construction `BaseArenaAdapter` that composes:

```text
ConstructionProjectState
  -> deterministic claim readiness
  -> hard candidate filtering
  -> advisory probabilistic signal
  -> deterministic state-local ranking
  -> Liquid Planning ActionCapsule / BoundaryContract / ArenaLease
  -> proposal-only coordination packet
  -> authorized human review
```

## Capability reuse decisions

| Capability | Canonical owner | Phase 3 decision |
|---|---|---|
| Construction truth and event chain | `aura_construction_contracts.py`, `aura_construction_state.py` | `REUSE`; no duplicate store |
| Human authority and receipt continuity | `aura_construction_authority.py`, `aura_relational_authority.py` | `REUSE`; no physical release |
| Capsules, boundaries, leases | `aura_liquid_planning_arena.py` | `ADD_NARROW_ADAPTER` |
| Hard filtering and rank-vector pattern | `aura_arena_wfst_runtime.py`, `aura_arena_wfst_types.py` | `REUSE_PATTERN`; hard blockers precede ranking |
| Probabilistic progress/ranking signal | no Construction owner | `TRUE_ADVISORY_GAP`; proposal-only record |
| Synthetic demo state and scenarios | no Construction fixture owner | `TRUE_TEST_GAP`; fictional deterministic fixture |
| Executable benchmark | standard Aura evidence hierarchy | `ADD_DOMAIN_BENCHMARK`; zero-model only initially |

## Surgeon capsules

### E7.1 — Coordination contracts and ranking

Targets:
- `aura_construction_adapter.py`
- `tests/test_aura_construction_adapter.py`

Acceptance:
- exact Construction state is revalidated;
- missing, expired, conflicting, sensor-only, or explicitly blocked routes are removed before ranking;
- probabilistic signals cannot rescue blocked candidates;
- no packet can authorize work, payment, access, safety, engineering, or legal status.

### E8.1 — Synthetic runtime fixture

Targets:
- `aura_construction_fixtures.py`
- `tests/test_aura_construction_fixtures.py`

Acceptance:
- deterministic fictional data only;
- no real SCO, PCL, worker, owner, building, or bid data;
- one deliberately high-scoring unsafe route remains blocked;
- at least three materially different admissible alternatives remain visible.

### E11.1 — Zero-model benchmark

Targets:
- `aura_construction_benchmark.py`
- `tests/test_aura_construction_benchmark.py`

Acceptance:
- 250 candidate-order permutations produce one exact evaluation digest and recommendation;
- unsafe high-score route is blocked in every run;
- non-executed comparison arms remain `NOT_MEASURED`;
- provider tokens, provider cost, real-project savings, and production readiness are not invented.

## Aura architecture benchmark ledger

These measurements describe the refactoring method and synthetic software fixture, not a real construction project.

```yaml
baseline_repository_files: 1032
initial_bounded_changed_files_before_generated_topology: 8
structural_file_scope_reduction: 99.22_percent
measurement_class: STRUCTURAL_CONTEXT_PROXY
canonical_reuse_rows: 7
parallel_truth_stores_added: 0
production_connectors_added: 0
initial_py_compile: PASS
initial_fatal_ruff: PASS
initial_focused_tests_collected: 40
initial_focused_tests_passed: 39
initial_focused_tests_failed: 1
manual_council_surgeon_findings:
  - distinct-option backfill missing after role deduplication
  - next-authority route over-escalated from unrelated alternatives
manual_findings_repaired: 2
coderabbit_invocations: 0
provider_tokens: NOT_MEASURED
provider_cost: NOT_MEASURED
real_project_savings: NOT_MEASURED
production_readiness: NOT_CLAIMED
```

The first failing test was valuable architectural evidence: cheapest, fastest, balanced, and safest selectors can collapse onto the same candidate. The repair preserves role-based choices first, then backfills distinct admissible routes to keep the decision surface materially plural. The manual Council/Surgeon sweep separately found that the next-authority field must follow the recommended candidate, while each alternative retains its own authority route.

## Deferred by design

- Human Agent server/API and UI wiring (E9)
- Observatory projection (E9/E12)
- ArenaExperience and Crucible eligibility (E10)
- real owner/contractor integrations
- production sensor, location, access, payment, payroll, or safety systems
- external model calls and multi-provider Council benchmark arms
- commercial claims based on synthetic savings

## Final gate sequence

```text
manual syntax/lint/logic sweep
  -> branch CI and focused coverage
  -> deterministic benchmark and prior-owner regressions
  -> exact topology regeneration
  -> manual CodeRabbit-equivalent diff audit
  -> one CodeRabbit invocation
  -> bounded repairs, if any
  -> README / ARCHITECTURE / USER_GUIDE / handoff / evidence sync
  -> regenerated CODEMAP
  -> pinned-head final CI
  -> merge
  -> post-merge verification
```

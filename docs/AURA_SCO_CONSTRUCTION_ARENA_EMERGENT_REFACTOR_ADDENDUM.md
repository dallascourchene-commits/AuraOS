# AuraOS SCO Construction Arena — Emergent Refactor Addendum

```yaml
document_status: PHASE_TWO_E4_E6_COMPLETE_AWAITING_USER_DIRECTION
document_version: 1.2.0
prepared_date: 2026-07-17
repository: dallascourchene-commits/AuraOS
baseline_main: 77e83f5686250530b00d40ef0d99e60f098681e5
branch: refactor/sco-construction-e4-e6
completed_phases: E0_E6
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
coderabbit_triggered: false
pull_request_opened: false
merged: false
cross_arena_handoff: docs/AURA_CROSS_ARENA_CHANGE_HANDOFF_LOG.md
```

## Architecture decision

The SCO Construction Arena remains a narrow domain layer over Aura's governed spine. It is not a parallel planner, evidence store, authority system, bridge, learning system, or autonomous construction controller.

```text
human objective
  -> Human Agent emergent evidence
  -> Capability Resolver and CODEMAP grounding
  -> exact canonical owners and missing domain gaps
  -> revisioned refactor skeleton
  -> bounded implementation
  -> deterministic replay and queries
  -> canonical relational governance
  -> digest-bound human decision
```

## Authority boundary

Aura may represent claims, evidence, conflict, dependencies, missing approvals, and digital coordination readiness. It may not:

- authorize physical work;
- certify safety, engineering, inspection, or professional conclusions;
- release payment or transfer funds;
- control access or equipment;
- discipline workers;
- treat sensors or location as dispositive proof;
- replace owner, consultant, community, contractual, legal, or regulatory authority.

The invariant is:

```text
EVIDENCE_READY != GOVERNANCE_AUTHORIZED != PHYSICAL_RELEASED
```

Physical release remains false and human-controlled.

## Phase 1 — E0–E3 foundation

Phase 1 introduced the general revisioned `RefactorSkeleton`, exact source-hash/span capsule authority, capability reuse grounding, Construction plan adapter, persistent handoff, and generated topology. It merged as:

```text
77e83f5686250530b00d40ef0d99e60f098681e5
```

## Phase 2 — E4 minimal contracts

`aura_construction_contracts.py` adds the minimum domain gap while reusing `aura_event_contracts.py`:

- immutable Construction scopes;
- claims and evidence as separate records;
- evidence, measurement, confidence, authority, privacy, consent, freshness, and expiry separation;
- project-bound append-only Construction events;
- exact sequence, parent, supersession, event, and chain identity;
- canonical Aura event-envelope projection.

## Phase 2 — E5 deterministic state and queries

`aura_construction_state.py` adds a zero-model reducer and query layer:

- deterministic replay;
- explicit supersession;
- conflict preservation;
- deletion, reordering, duplicate, foreign-parent, cross-key, and backward-time rejection;
- claim-readiness and project-conflict queries;
- sensor/location-only evidence blocked as non-dispositive;
- privacy and consent propagation enforcement.

## Phase 2 — E6 authority and receipts

`aura_construction_authority.py` is a narrow adapter over `aura_relational_authority.py`:

- no custom cryptography;
- no injectable evaluator;
- exact risk/quorum binding;
- exact project policy and Construction capability scope;
- canonical grant, attestation, quorum, and governance evaluation;
- separate governance-authorized and evidence-ready values;
- digitally-ready only when both pass;
- chained receipt and external-reference binding to the exact request, state, decision, and result;
- physical work remains unauthorized.

## Original ten emergent properties in E4–E6

| # | Emergent property | E4–E6 application |
|---:|---|---|
| 1 | Grounded intent -> capsules | Exact canonical owners and narrow domain gaps defined the slice |
| 2 | Topology -> route | Runtime queries use `ZERO_MODEL`; authority escalates to canonical human governance |
| 3 | Localization before broad prompts | Four principal owner files selected from 1,022 repository files |
| 4 | Verified memory -> compact context | Append-only state digest replaces broad history replay |
| 5 | Plans -> persistent skeletons | Phase state and unresolved wires remain in the handoff log |
| 6 | Failures -> bounded repair | Twenty-four review findings were repaired locally with regressions |
| 7 | Attempts -> governed procedures | Still deferred until verified Experience episodes exist |
| 8 | Findings -> ghost plan | Deferred integrations remain explicit wiring debts |
| 9 | Reuse before invention | Event and authority owners were reused; only proven Construction gaps were added |
| 10 | Verified component -> promotion proposal | Phase stops before PR, CodeRabbit, merge, or activation |

## Manual equivalent review

CodeRabbit was not triggered by user instruction. The equivalent review produced:

```yaml
py_compile: PASS
compileall: PASS
focused_adversarial_tests: 89_passed
focused_statement_coverage: 90_percent
manual_fatal_lint: PASS
randomized_replay_probe: 250_histories_passed
manual_findings_repaired: 24
```

Full evidence is recorded in `docs/AURA_SCO_PHASE2_E4_E6_REVIEW_EVIDENCE.md`.

## Context-efficiency evidence

```yaml
repository_file_count: 1022
selected_principal_owner_files: 4
structural_file_selection_reduction: 99.61_percent
measurement_class: STRUCTURAL_CONTEXT_PROXY
provider_tokens_and_cost: NOT_MEASURED
runtime_model_route: ZERO_MODEL
```

This is a structural context-selection result, not a provider billing claim.

## Generated topology policy

The following artifacts must be regenerated from the final branch tree and never hand-merged:

```text
.aura/CODEMAP.json
.aura/CODEMAP.md
topology_map.json
```

## Deferred work

- Construction `BaseArenaAdapter`;
- Human Agent Construction profile and UI;
- Observatory projection;
- verified Experience and Crucible projection;
- payment-readiness lane;
- hazard/location advisory lane;
- live connectors;
- physical control or autonomous procedure activation.

> Build the Construction Arena by extending Aura's governed spine. Preserve unknowns, conflict, dissent, privacy, missing authority, and human release.

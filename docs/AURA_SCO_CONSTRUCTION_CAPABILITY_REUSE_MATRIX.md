# SCO Construction Arena — Capability Reuse Matrix

```yaml
document_status: PHASE_TWO_E4_E6_GROUNDED_IMPLEMENTATION
date: 2026-07-17
baseline_main: 77e83f5686250530b00d40ef0d99e60f098681e5
branch: refactor/sco-construction-e4-e6
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
coderabbit_triggered: false
pull_request_opened: false
merged: false
```

## Decision rule

```text
existing canonical owner
  | narrow domain adapter
  | exact capability gap
  | defer
```

A caller-supplied filename, generic capability path, or unrelated symbol is not grounding. Current source, exact symbols, tests, hashes, and CODEMAP topology remain authoritative.

## Grounded owner decisions

| Capability | Canonical owner | Decision | E4–E6 disposition |
|---|---|---|---|
| Canonical event envelope, measurement classes, stable IDs and digests | `aura_event_contracts.py` | `REUSE` | Construction events project into the existing envelope without schema mutation |
| Civic privacy, consent, governance-blocker, and immutable-contract precedents | `aura_civic_planning_types.py` | `REUSE_PATTERN` | Construction adds only proven domain fields and stricter project scope |
| Action Capsules, Boundary Contracts, leases, deltas, adapter lifecycle | `aura_liquid_planning_arena.py` | `DEFER_ADAPTER` | No `BaseArenaAdapter` is added in E4–E6; runtime adapter remains a later wire |
| Relational authority grants, attestations, quorum, decisions, receipts, checkpoints | `aura_relational_authority.py` | `ADD_NARROW_ADAPTER` | Construction binds exact digital readiness to existing governance contracts |
| Construction claim/evidence/event contracts | `aura_construction_contracts.py` | `TRUE_DOMAIN_GAP` | New narrow owner; proposal-only and no physical authority |
| Construction replay, conflict, supersession, readiness queries | `aura_construction_state.py` | `TRUE_DOMAIN_GAP` | New deterministic zero-model owner |
| Construction authority and receipt binding | `aura_construction_authority.py` | `ADD_NARROW_ADAPTER` | Reuses canonical authority; no custom crypto or injectable evaluator |
| Human Agent emergent evidence workspace | `aura_emergent_refactor_workspace.py` | `DEFER_ADAPTER` | No second evidence store; runtime profile not added in this phase |
| Experience and Crucible projection | existing Experience/Crucible owners | `DEFER` | Requires verified synthetic/shadow episodes first |
| Observatory projection | existing Observatory owners | `DEFER` | Read-only route/context/gate records remain future work |

## E4 minimal gap proof

Existing owners provide generic event identity, measurement classes, civic planning patterns, and proposal-only boundaries. They do not provide Construction-specific separation of:

- claim versus evidence;
- project/zone/work-package scope;
- evidence class and non-dispositive sensor/location treatment;
- Construction privacy and consent propagation;
- record freshness and expiry;
- Construction event supersession and chain identity.

The gap is therefore implemented as `aura_construction_contracts.py`, not by changing the canonical event schema.

## E5 minimal gap proof

Existing planning and civic surfaces do not own a Construction-specific deterministic reducer that preserves contradictory active claims/evidence and explicit supersession. `aura_construction_state.py` owns only that domain projection and deterministic query layer.

## E6 minimal gap proof

`aura_relational_authority.py` already owns grants, attestations, quorum, governance decisions, receipt chains, checkpoints, and trusted-reference boundaries. Construction therefore does not duplicate them. `aura_construction_authority.py` only binds those objects to exact Construction requests, evidence-readiness reports, project state, and receipt records.

## Deferred capabilities

- Construction `BaseArenaAdapter`;
- Human Agent Construction profile/API/UI;
- Observatory projection;
- Experience and Crucible projection;
- payment-readiness lane;
- hazard and location advisory lane;
- live owner or contractor connectors;
- physical access, equipment, or work control;
- professional, safety, regulatory, or legal certification;
- autonomous procedure activation.

## Phase evidence

```yaml
focused_adversarial_tests: 89_passed
focused_statement_coverage: 90_percent
manual_fatal_lint: PASS
randomized_replay_histories: 250
runtime_model_calls: 0
structural_context_proxy:
  repository_files: 1022
  principal_owner_files: 4
  reduction: 99.61_percent
provider_tokens_and_cost: NOT_MEASURED
```

## Future module gate

No later Construction module may proceed without:

1. an updated row in this matrix;
2. an exact canonical-owner decision;
3. a cross-Arena disposition;
4. an authority and privacy boundary;
5. focused adversarial tests;
6. a handoff-log entry for every missing wire;
7. regenerated topology after the final source tree is stable.

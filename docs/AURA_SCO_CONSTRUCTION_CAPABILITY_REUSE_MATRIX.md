# SCO Construction Arena — Capability Reuse Matrix

```yaml
document_status: PHASE_ONE_GROUNDED_INVENTORY
date: 2026-07-16
baseline_main: 52f07f3b8bc5f932b6a1c950f0c3081500f189db
branch: refactor/sco-construction-arena
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

## Decision rule

```text
existing canonical owner
  | narrow domain adapter
  | exact capability gap
  | defer
```

A filename supplied by the caller is not grounding. A generic capability path is not grounding. A function in the same file is not grounding unless it is one of the exact requested owner symbols. Current source, symbols, tests, hashes, and topology remain authoritative.

## Grounding inventory

| Capability | Candidate canonical owner | Decision | Construction disposition |
|---|---|---|---|
| Append-only event and evidence semantics | `aura_event_contracts.py`, `aura_civic_planning_types.py` | `EXTEND_CANONICAL_OWNER` | Reuse core truth/measurement semantics; add only proven domain fields |
| Action Capsules, Boundary Contracts, leases, deltas, adapter lifecycle | `aura_liquid_planning_arena.py` | `ADD_NARROW_ADAPTER` | Construction becomes a domain adapter, not another planner |
| Capability discovery and reuse | `aura_capability_resolver_v2.py`, `aura_capability_resolver.py`, `aura_capability_connectome.py` | `REUSE` | Mandatory before any new module |
| Human Agent emergent reports, findings, research, strict packets | `aura_emergent_refactor_workspace.py` | `EXTEND_CANONICAL_OWNER` | No second evidence store |
| Revisioned refactor skeleton | `aura_refactor_skeleton.py` | `TRUE_NEW_CAPABILITY` | General owner; Construction is the first adapter |
| Staging, verification, repair, rollback, hotswap proposal | `aura_architect_loop.py`, `aura_agent_arena_bridge.py` | `REUSE` | Bridge remains unchanged until an exact interface gap is proven |
| Verified attempt experience | `aura_arena_experience.py`, `aura_arena_experience_ledger.py` | `REUSE` | Deferred until complete verified Construction episodes exist |
| Executable refactor quality records | `aura_refactor_output_record.py` | `REUSE` | Construction results cannot inherit evidence from unrelated fixtures |

## Implemented Phase 1 owner

`aura_refactor_skeleton.py` is the only approved new canonical owner in E0-E3. It exists because the repository had surrounding plan, capsule, evidence, staging, experience, and quality owners but lacked a general human-editable, digest-bound revision skeleton.

## Required owner-proof fields

Every capability row compiled by `build_construction_capability_reuse_matrix()` records:

```yaml
capability_id:
objective:
expected_owner:
reuse_decision:
candidate_files:
candidate_symbols:
exact_hits:
capability_ids:
capability_path:
tests:
truth_boundaries:
risks:
codemap_digest:
capability_graph_digest:
capability_path_digest:
status:
```

`GROUNDED_REUSE_CANDIDATE` requires:

- a healthy resolver/topology response;
- an exact requested symbol;
- the symbol appearing in a declared candidate file;
- an exact grounding class;
- no file-only or unresolved placeholder.

## Explicitly deferred capabilities

The following are not approved by Phase 1:

- Construction runtime contracts;
- project-state reducer and query engine;
- authority, attestation, and receipt runtime;
- payment-readiness lane;
- hazard or location lane;
- live owner/contractor connectors;
- physical access or equipment control;
- Human Agent Construction UI/profile;
- Observatory Construction projection;
- Experience or Crucible projection;
- autonomous procedure activation.

## Exact next grounding tasks

```text
E4:
  inspect current event and civic contracts
  prove the minimal Construction-only schema gap
  retain evidence, confidence, authority, privacy, consent, and supersession separation

E5:
  inspect current reducers and deterministic project queries
  implement append-only replay, explicit supersession, and conflict preservation

E6:
  inspect existing verifier/signature/attestation protocols
  add no custom cryptography
  validate role, project, zone, scope, freshness, revocation, and human release
```

## Merge boundary

No new Construction module may enter a later PR without:

1. a row in this matrix or its successor;
2. an exact canonical-owner decision;
3. cross-Arena integration dispositions;
4. source hashes and spans for executable capsules;
5. focused tests and an explicit authority boundary;
6. a handoff-log entry for any missing integration.

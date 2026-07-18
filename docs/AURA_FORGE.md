# Aura Forge — Verified Engineering OS

## Status

Aura Forge V1 is a bounded product façade over Aura's existing Coding Arena,
Architect, Controlled Refactor Session, external-LLM slice leasing, staging,
verification, output-vault, and human-review owners.

It does **not** introduce a second planner, patch store, verifier, experience
ledger, or promotion path.

## Product objective

Aura Forge lets a team use a local or hosted coding model as a replaceable
worker without giving that worker ambient repository or release authority.

```text
human engineering objective
  → CODEMAP and topology grounding
  → frozen Architect/Coding Arena plan
  → Arena Evidence Contract
  → bounded source/test slice lease
  → external worker unified diff
  → canonical staging and verification
  → bounded repair or Council replan
  → READY_FOR_HUMAN_REVIEW
  → separate authorized promotion decision
```

## Canonical implementation

- `aura_forge.py` — product contract and runtime façade;
- `schemas/aura_forge_arena_evidence_contract.schema.json` — stable contract;
- `aura_agent_arena_bridge.py` — repository digest, grounding, staging, tests,
  repair packets, and hotswap evidence;
- `aura_controlled_refactor_session.py` — frozen-plan Council/Surgeon controls;
- `aura_external_llm_session_safe.py` — bounded slices and safe evidence export;
- `aura_refactor_output_record.py` and output vault owners — quality evidence;
- `tests/test_aura_forge.py` — fail-closed product-contract tests.

## Arena Evidence Contract

Every Forge run compiles `AURA_FORGE_ARENA_EVIDENCE_CONTRACT_V1` before a
worker session opens. The contract binds:

- the normalized objective and request digest;
- repository/CODEMAP/topology identity;
- frozen plan-phase identity;
- Act Capsules and exact micro-context references;
- source line ranges, dependencies, tests, and route decisions;
- acceptance criteria and risk map;
- allowed files and mandatory verification gates;
- model/provider budgets;
- authority and lifecycle invariants.

The contract is evidence and authority scope. It is not permission to promote a
patch.

## Python use

```python
from aura_forge import AuraForgeRuntime

forge = AuraForgeRuntime(repo_root=".")
opened = forge.start(
    {
        "objective": "Refactor failure routing while preserving public APIs",
        "target_file": "pkg/router.py",
        "target_symbol": "route_failure",
        "acceptance_criteria": [
            "visible, hidden, and regression tests pass",
            "public APIs remain compatible",
        ],
        "risk_map": ["interface drift", "scope expansion"],
        "provider": "external",
        "model": "provider-model",
    }
)
```

The first turn contains only the leased Act Capsule, exact source/test slices,
failure evidence when repairing, and the unified-diff output contract.

Submit a worker response through the runtime:

```python
result = forge.submit(
    run_id=opened["run_id"],
    turn_id=opened["turn"]["turn_id"],
    response=worker_unified_diff,
    provider_usage={"input_tokens": 1000, "output_tokens": 400},
)
```

Forge may return another worker or repair turn. Completion stops at
`READY_FOR_HUMAN_REVIEW`. The review packet never commits, pushes, opens a pull
request, merges, or mutates production.

## Aura Gate Phase 2 binding

Aura Gate wraps Forge without becoming a second planner, staging store, verifier, or
worker runtime. The integration seam is deliberately two-step:

```text
AuraGateRuntime.prepare
  → AuraForgeRuntime.prepare
  → retain contract ID + full contract digest
  → issue exact Gate authority envelope and Arena lease

AuraGateRuntime.start
  → reauthorize identity, policy, audit, lease, capability, and expiry
  → append PRE_ACTION evidence
  → AuraForgeRuntime.start_prepared(
       run_id,
       expected_contract_id=...,
       expected_contract_digest=...,
     )
```

`start_prepared` is one-shot and revalidates the retained internal contract, repository
HEAD, CODEMAP digest, and allowed-file source hashes before the controlled worker session
opens. The Gate wrapper then compiles any outbound turn into exact canonical bytes under
the envelope's purpose, destination, model, data, retention, field, payload, and token
limits.

OIDC verification, static Gate policy, operational lease state, governed egress, MCP/A2A
translation, comparisons, audit receipts, SIEM projection, and private serving remain
owned by the `aura_gate*.py` modules. Forge retains preparation, bounded worker execution,
staging, verification, repair, and `READY_FOR_HUMAN_REVIEW` ownership.

The Gate envelope never upgrades a Forge review packet into commit, push, pull-request,
merge, release, policy-promotion, or production authority. See
[`docs/AURA_GATE.md`](AURA_GATE.md).

## Fail-closed conditions

Forge refuses to start when:

- CODEMAP/repository digest is unavailable;
- Architect preparation fails;
- blockers remain;
- the Builder route is not authorized;
- no Act Capsule is produced;
- an exact task micro-context cannot be built;
- the target path is absolute or traverses outside the repository;
- context, output, turn, repair, or Council budgets are invalid;
- the controlled external-worker session cannot open.

## Authority invariants

```yaml
planning_proposes: true
verification_proves: true
human_authorizes: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
production_mutation: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

## V1 boundary

V1 proves the canonical contract and frozen-plan worker path. It does not yet
claim:

- independent multi-provider superiority;
- production deployment readiness;
- automatic release management;
- enterprise identity or policy integration inside Forge itself (the separate Gate Phase
  2 proof supplies a narrow OIDC/static-policy wrapper);
- a hosted control plane;
- broad language/ecosystem coverage.

Those require real-repository pilots and provider-reported measurements.

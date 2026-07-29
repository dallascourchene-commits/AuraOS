# Aura Construction Spatial Foundry — PR 1

**Base:** `211b5c76138667861d0b789f7e863a658ff16676`  
**Scope:** backward-compatible domain projection and exact Construction arena binding.

## Ownership

PR 1 adds adapters only. It does not replace the merged B15 service, Attempt
Archive, Runtime Profile V2, U7/current-reproof, Showcase, Spatial, or
Construction truth owners.

## Additive surfaces

- `aura_spatial_foundry_projection.py`
  - validates readable V1 projections;
  - wraps them as `AURA_SPATIAL_FOUNDRY_PROJECTION_V2`;
  - retains `code_targets`;
  - adds `domain_targets`, `domain_artifacts`, presentation, Construction
    evidence, Construction candidates, domain decision, and guarded-WFST
    projections;
  - keeps all domain authority false.
- `aura_construction_spatial_foundry.py`
  - supplies exact arena attribution over the canonical Attempt Archive;
  - projects the canonical
    `aura_construction_adapter.ConstructionCoordinationCandidate` through a
    state-bound `ConstructionCoordinationCandidateArtifact`;
  - keeps canonical Construction candidates separate from
    `RepairCandidateResult`;
  - supplies a server-side trusted bilateral identity handle.
- `aura_construction_spatial_foundry_server.py`
  - composes all existing Showcase/B15 routes;
  - adds `/api/showcase/live-repair/identity/current`;
  - transforms a server-issued identity handle into the full in-process identity;
  - never accepts raw request claims of currency;
  - routes V2 Construction projections through the arena-bound service.
- `aura_showcase/construction-spatial-foundry.js`
  - preserves the legacy Foundry script;
  - obtains trusted identity from the composed server;
  - preserves the legacy B15 identity flow when no trusted provider is
    configured;
  - adds required-asset path/SHA-256 intake;
  - requests the V2 Construction projection.

## Exact arena binding

The generic projection contract recognizes `coding`, `construction`, and
`spatial`, but PR 1's composed server selects only the `construction` arena. The
adapter binds that Construction arena to the bounded capture and replay
workflow. Every subsequent runtime replay, repair attempt, preview, and archive
call is corrected to that immutable packet binding. This specifically prevents
the generic B15 preview default from labeling Construction evidence as Coding.

## Candidate semantics

A Construction coordination candidate is parsed and identity-checked by the
existing `aura_construction_adapter` owner. The Foundry artifact adds only the
exact `base_state_digest` projection binding. It has no `promotion_ready`,
runtime proof, failure class, or Surgeon/Council route fields. A domain decision
must match exactly one projected canonical candidate and remains limited to a
closed, non-authoritative status set. Software repair candidates retain their
existing B12 meaning.

Identity handles pin the exact identity present at issuance. Resolution returns
that retained identity only while the current trusted owner still matches it;
an identity change expires the handle rather than retargeting it.

## Guarded-WFST projection

The PR exposes deterministic admitted, blocked, and recommended transitions.
The transition packet is a projection only:

```yaml
execution_authority: false
state_mutation: false
human_review_required: true
```

No browser transition dispatches a physical, professional, payment, access,
repository, deployment, or learning action.

## Verification

Focused tests prove:

1. V1 remains readable and `code_targets` remain present.
2. V2 adds domain fields and a fresh exact projection digest.
3. Candidate types fail closed across the Construction/software boundary.
4. Required assets survive incident finalization.
5. Construction preview/archive records remain `arena_id=construction`.
6. Server identity summaries omit the full bilateral identity.
7. Raw request currency claims fail closed.
8. Guarded-WFST output grants no execution authority.

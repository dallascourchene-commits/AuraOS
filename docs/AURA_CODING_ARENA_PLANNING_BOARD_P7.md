# P7 Coding Arena Planning Board Shadow Adapter

## Disposition

P7 adds an **additive, proposal-only shadow adapter** over records already produced by Aura's Coding/Architect Arena. The existing Architect loop, Refactor Arena, Liquid Planning Arena, routes, leases, patch queue, verifier, hotswap gate, merge path, stores, CLIs, and servers remain unchanged and retain their current ownership.

No caller is redirected in P7. The adapter is suitable for observation and empirical parity testing only. Any live migration remains a separately staged decision.

## Inputs

The strict projector consumes four already-produced legacy values:

1. `FractalPlanCapsule`
2. ordered `GroundingEvidence` records
3. `ShadowReport`
4. `RefactorArenaTransaction`

The projector accepts mappings, dataclasses, or `to_dict()` records and snapshots them through Aura canonical JSON. It reads the supplied records again before returning a board. Any inconsistency fails closed; when projection reaches the final comparison, a changed input is reported as `LEGACY_MUTATION_DETECTED`. An earlier exact-integrity contradiction may reject the record first with the more specific mismatch code.

It does not invoke the Architect loop, providers, models, routers, CODEMAP refresh, test runners, lease creation, patch staging, verification, hotswap, or merge.

## Exact compatibility requirements

Projection succeeds only when all of the following remain exact:

- plan and arena phase hash;
- task identity, count, and order;
- full Act Capsule value in both plan and arena;
- one grounding, route, lease, and boundary contract per task;
- target file and symbol across every surface;
- declared file scope and exact lease read/write/symbol regions;
- shadow report identity and independently verified legacy phase hash;
- affected-file projection;
- Liquid Arena version, intent, plan reference, code domain, domain objects, adapter invariant, initial ledger, action count, task identity, and order;
- independently reconstructed Liquid Action, Boundary, Lease, Arena ID, and Arena phase hash;
- top-level enriched boundaries and leases matching their Liquid Arena sources;
- `ready_for_incubator` agreeing with the unchanged shadow result, grounding, and routes;
- strict booleans, canonical strings, exact schemas, and repository-relative normalized paths.

Missing, duplicate, reordered, substituted, stale, malformed, noncanonical, unsafe, conflicting, or independently unverifiable evidence never produces a Planning Board.

The deep integrity layer intentionally mirrors the current legacy `CodeArenaAdapter` construction contracts. A future legitimate legacy schema change must update this compatibility layer in a separately reviewed change; unknown drift is not accepted silently.

## Compatibility states

- `VERIFIED_SHADOW`: exact mapping succeeded and the legacy record is not blocked.
- `BLOCKED_LEGACY`: exact mapping succeeded, but the unchanged legacy Shadow or route remains blocked.
- `MISMATCHED`: evidence exists but violates an exact compatibility invariant.
- `UNAVAILABLE`: a required legacy record is absent, cannot be snapshotted, or is not a supported concrete record.

`BLOCKED_LEGACY` is not upgraded by the adapter. The board can describe blocked work while preserving its blocked legacy disposition.

## Planning Board authority boundary

Every projected action is:

- `proposal_only = true`;
- `authority_requirement = HUMAN`;
- reversible and bound to one deterministic idempotency key;
- constrained by exact legacy digest references;
- grounded only when the legacy file, CODEMAP, and symbol facts all agree;
- assigned declared verifier IDs but no fabricated verifier receipts;
- assigned no authority-decision IDs.

A normally grounded fixture therefore reaches BC3 (`GROUNDED`) but not BC4 (`AUTHORIZED`) or BC5 (`VERIFIED`). A blocked missing-file fixture reaches BC2 (`CONSTRAINED`). Planning proposes; governance authorizes; verification proves.

## Deterministic empirical benchmark

`aura_coding_arena_planning_benchmark.py` independently reconstructs exact legacy-format fixture records and runs five committed cases:

1. grounded single-file patch;
2. grounded multi-act patch;
3. inspect-only route;
4. warning with no nearby test;
5. blocked missing-file work.

The gate requires:

- 100% task-to-action coverage;
- exact task-order preservation;
- deterministic board and inspection digests across repeated projections;
- 100% verifier declaration coverage;
- zero legacy mutation drift;
- zero authority drift;
- zero board/action identifier collisions;
- the exact expected compatibility status for every case.

The report records exact canonical UTF-8 byte sizes and a deterministic four-bytes-per-token proxy. Size overhead is reported honestly. The benchmark does **not** claim lower latency, improved provider/model quality, successful code execution, general token savings, or general efficiency improvement.

## Manual CodeRabbit-style review

Before requesting external review, P7 was red-teamed against substitution, aliasing, malformed-schema, authority, mutation, and time-of-check/time-of-use surfaces. The manual review added or strengthened:

- independent legacy Action, Boundary, Lease, and Liquid Arena reconstruction;
- exact ID and phase-hash verification;
- top-level/Liquid copy equivalence;
- symbol-region and unknown-region rejection;
- strict task, route, boundary, path, and boolean typing;
- snapshot exception containment;
- readiness coherence;
- exact benchmark fixtures rather than abbreviated stand-ins;
- adversarial regression coverage for every discovered gap.

The manual review does not replace external CodeRabbit review; both are required before merge.

## Non-goals

P7 does not:

- replace `CodeArenaAdapter` or `build_refactor_arena`;
- change public return values or imports;
- execute or re-run legacy work;
- stage or apply a patch;
- run a test or create a verifier receipt;
- grant a capability, human approval, governance decision, or merge authority;
- mutate production, hotswap, or merge;
- begin the P8 Civic Commons adapter.

## Ownership decision

**Retain legacy Coding Arena ownership.** The Planning Board adapter remains a verified shadow until a separately reviewed migration demonstrates caller compatibility, operational value, and unchanged human/exact-source authority boundaries.

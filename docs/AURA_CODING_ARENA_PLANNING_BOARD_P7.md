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

The projector accepts mappings, dataclasses, or `to_dict()` records, snapshots them through Aura canonical JSON, and then re-reads them after projection. A change between reads fails closed as `LEGACY_MUTATION_DETECTED`.

It does not invoke the Architect loop, providers, models, routers, CODEMAP refresh, test runners, lease creation, patch staging, verification, hotswap, or merge.

## Exact compatibility requirements

Projection succeeds only when all of the following remain exact:

- plan and arena phase hash;
- task identity, count, and order;
- full Act Capsule value in both plan and arena;
- one grounding, route, lease, and boundary contract per task;
- target file and symbol across every surface;
- declared file scope and lease write scope;
- lease read scope restricted to grounded neighbour files;
- shadow report identity and independently verified legacy phase hash;
- affected-file projection;
- Liquid Arena plan reference, code domain, action count, task identity, and order;
- strict booleans, canonical strings, and repository-relative normalized paths.

Missing, duplicate, reordered, substituted, stale, malformed, noncanonical, unsafe, or conflicting evidence never produces a Planning Board.

## Compatibility states

- `VERIFIED_SHADOW`: exact mapping succeeded and the legacy record is not blocked.
- `BLOCKED_LEGACY`: exact mapping succeeded, but the unchanged legacy Shadow or route remains blocked.
- `MISMATCHED`: evidence exists but violates an exact compatibility invariant.
- `UNAVAILABLE`: a required legacy record is absent or is not a supported concrete record.

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

`aura_coding_arena_planning_benchmark.py` runs five committed fixtures:

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

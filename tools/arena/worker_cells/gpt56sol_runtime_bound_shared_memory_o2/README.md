# Runtime-Bound Shared-Memory Admission — O2

D0/nonpromoting Arena worker cell.

## Objective
Bind shared-memory eligibility to the exact producer process-isolation receipt, producer implementation/owner generation, semantic domain/projection, and subject generation/state **before** K27 route scoring.

## Keeper laws

- `HistoricalProducerReceipt != CurrentMemoryAdmission`
- `Provenance/Recency != Subject-State Authenticity`
- `MemoryReuseCandidate => MemoryValid AND SemanticCurrent AND SubjectStateCurrent AND ProducerProcessIsolated AND ExactProducerReceipt AND ExactProducerImplementationGeneration AND ExactProducerOwnerGeneration AND D0`
- `K27Coordinate != Identity != Truth != Currentness != Authority`
- Routing economics never repair semantic/currentness/runtime proof debt.

## Exact parents

1. O10 Isolation Receipt -> Currentness DAG Bridge (Drive `12NODg-AoUVKk7kzb3PSisiHgL1GLUPUmPQb_6xR5RTg`).
2. PR #847 / Process-Global Patch Isolation Membrane (Drive `1jjp-a7QwaJ7p-NQdVi-joxkY7nVscgKvJkiVmVVlAzo`).

## Local proof

Three freshly recreated stdlib-only Python virtual environments on exact final bytes:

- 21 focused tests/environment = **63/63 PASS**; `py_compile` PASS.
- HS1000: 1,000 adversarial cases/environment, **0 false admissions**.
- Independent oracle: 100,000 decisions/environment = **300,000 total**, **0 mismatches**.
- Omega8: all **6,561** ternary hard-axis states, exactly **1** keeper.
- 13D: all **243** context5 tails, **0** repairs of a hard-invalid producer/runtime core.
- Producer invalidation cone is dependency-closed and preserves the unrelated source branch.
- Deterministic receipt root across all three environments: `27a38acec39c3c7fa794eafc2ba0aabf19ca28476fb83fd9c631b06542998172`.

Frozen SHA-256:

- `runtime_bound_memory.py` `b806d0c965aed578f3965795d754c268890f6cd55ff47aba56a507a57a195981`
- `campaign.py` `205e72f2488f1a46d398799a8766e400c96282acbc090214ab1a11cd110bc9cd`
- `tests/test_runtime_bound_memory.py` `d71d2430abb65412d95a5b0fd01918b968fd6af1e04d40b3c44db7eaad4378bc`
- `README.md` `e1a0a5fdb8dafc5c03ef4e4d3a14ddf9c59652e77d6d5c01dcc68e1464a9cf48`

## Authority ceiling

D0 control-plane proof only. No source truth, provider truth, hosted/model execution, physical latency/throughput/energy, native/private transformer KV, merge/deploy authority, effect authority, canonical promotion, or Gate10.

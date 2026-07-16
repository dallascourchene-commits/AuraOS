# Aura Real Refactor Trial V1

## Purpose

Benchmark Four uses a real AuraOS hardening refactor as the benchmark task itself.
It carries forward the prior Selective Council V3 evidence, compares three bounded
plans, selects one through the shared Council V3 connector, executes the selected
plan on the repository branch, and records executable tests plus engineering gates.

The independent review that triggered this trial found two concrete defects:

1. a compact fixture ledger hashed only the last event, so two different histories
   with the same length and final event could collide;
2. malformed `repair_attempt` values such as `"bad"` or `NaN` could raise instead
   of producing a bounded fail-closed route.

## Candidate plans

- **Plan A:** patch only the two defects.
- **Plan B:** patch the defects and strengthen the adversarial benchmark.
- **Plan C:** do both, then expose the selected architecture through Coding/Human
  Agent Arena MCP and HTTP connector surfaces, package it as an OCI container,
  route native model use through the Model Cognome, and retain the trial evidence.

The plan source is `benchmarks/real_refactor_trial/plans.json`. The selected plan
must be `PLAN-C-INTEGRATED-ARENA-ARCHITECTURE` before review.

## Production hardening

### Strict failure evidence

`aura_cognitive_labor_router.route_failure()` now parses counters and graph flags
without Python truthiness shortcuts. Unknown encodings, negative counts, booleans
used as integers, NaN, infinity, mappings, and sequences fail closed to a Council
replan. They do not raise.

### State Ledger V2

`AURA_REFACTOR_STATE_LEDGER_V2` carries:

- complete event count;
- chained history-root digest;
- last-event digest;
- plan and objective identities;
- task frontier and dependency map;
- latest stage and verifier digests;
- repair and Council-replan state;
- immutable authority invariants.

The history root commits to every event, its order, the session identity, and the
previous digest. Earlier-event mutation therefore changes the root even when the
final event and event count are unchanged.

## Shared Arena connector

`AuraArenaArchitectConnector` is the common application service for:

- Coding Arena clients;
- Human Agent Arena clients;
- MCP clients;
- HTTP/container clients.

It compares candidate plans, records Council V3 selective critic lanes, prepares
the selected plan through `AuraAgentArenaBridge`, and keeps promotion authority
outside the connector.

The unified MCP entrypoint is:

```bash
python aura_agent_arena_mcp_architect.py
```

It includes the existing repository/slice/session tools plus:

- `aura_architect_compare_plans`
- `aura_architect_prepare`
- `aura_native_model_route`
- `aura_native_model_execute`

## Native model routing

`AuraNativeModelGateway` always enters through `AdaptiveModelRouter`. With no human
override, Aura queries the Model Cognome candidate set and selects the policy mode
that best fits verified success, cost, latency, repair burden, scope violations,
drift, risk, and current capability-path evidence.

Possible routes are:

- `ZERO_MODEL`
- `DIRECT`
- `CASCADE`
- `PANEL`

A `CASCADE` advances only after provider failure or verifier rejection. Live
execution remains authorization-gated, and verified telemetry is persisted by the
existing adaptive executor for future model selection.

## Container use

The OCI image contains the AuraOS runtime, so an operator can pull and run the
connector without cloning the GitHub repository:

```bash
docker compose -f docker-compose.arena-connector.yml up
```

HTTP endpoints include:

- `GET /health`
- `GET /v1/capabilities`
- `POST /v1/architect/compare`
- `POST /v1/coding-arena/architect/prepare`
- `POST /v1/human-agent/architect/prepare`
- `POST /v1/models/route`
- `POST /v1/models/execute`

`/v1/models/execute` defaults to `SHADOW`; `PAIRED_LIVE` requires an explicit
content-addressed authorization.

## Benchmark evidence

The workflow `.github/workflows/architect-real-refactor-trial.yml` records:

- exact plan candidates and selected plan;
- prior Benchmark Three evidence;
- focused JUnit counts;
- property-based routing and history tests;
- compilation;
- fatal static analysis;
- Bandit security checks;
- container compose validation and image build;
- changed-file inventory;
- final disposition before CodeRabbit/manual review.

This is a real repository refactor trial, but it is not yet an independent
provider-generation trial. The plan candidates were prepared in the same assisted
development process. External reproduction, independent hidden tests, exact
provider billing, repeated trials, mutation testing, and cross-repository tasks
remain the next evidence tier.

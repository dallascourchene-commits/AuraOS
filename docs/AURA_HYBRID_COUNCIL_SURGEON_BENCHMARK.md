# Aura Council–Surgeon Hybrid Refactor Benchmark

**Planning benchmark:** `AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V2`  
**Execution benchmark:** `AURA_HYBRID_COUNCIL_SURGEON_BENCHMARK_V1`  
**Status:** reproducible fixture and synthetic-control-flow evidence; no production mutation  
**Model fixture:** GPT-5.6 Thinking, single-session assisted planning fixture

## Research question

Does Aura perform best when cognitive labor is divided by scope?

- A multi-agent **Council** handles architectural design, cross-domain dependency mapping, sequencing, trade-offs, interface contracts, invariants, and graph-level rollback.
- A single sliced **Surgeon** handles exact-file implementation, compile-ready patches, focused verification, and bounded local repair.

The hybrid hypothesis is:

```text
Council once → long execution graph
Surgeon → each bounded Act Capsule
local failure → Surgeon repair
interface/dependency/invariant failure → Council replan → Surgeon resumes
```

This benchmark measures planning quality, total planning tokens, step-level execution tokens, context preservation, full-history avoidance, local repair, graph escalation, and Council-cost amortization.

It does **not** measure real multi-step patch quality because the execution bridge and patch responses are deterministic fixtures.

## Exact benchmark prompt

### Objective

> Scan the AuraOS repository and produce a grounded, staged refactor skeleton that consolidates memory, skill, capability, and agentic functions to improve the Human Agent Arena. Reuse existing Aura architecture, preserve compatibility through explicit adapters, retain plans and verifier evidence, and require human approval before mutation or promotion.

### Shared plan contract

> Return JSON only. Produce a bounded Aura Architect refactor plan with fields: architecture_decision, target_file, target_symbol, act_tasks, acceptance_criteria, rollback_conditions, risk_map, constraints. Each act task must include task_id, objective, target_file, target_symbol, related_files, allowed_scope, acceptance, expected_output=UNIFIED_DIFF, and size. Use only repository facts present in the context. Prefer existing modules and explicit adapters over a new giant abstraction. The plan must persist in the Human Agent Arena, preserve verifier evidence, stage all changes, and require human approval before mutation or promotion.

The generated `prompt_manifest.json` preserves 20 exact prompt entries: two single-planner prompts and 18 Council-role prompts.

## Division of cognitive labor

| Vector | Single sliced planner — Surgeon | Multi-agent Council — Board |
|---|---|---|
| Optimal scope | Local implementation, single-module refactoring, pure code synthesis | Architecture, cross-domain dependency mapping, trade-off analysis, graph repair |
| Context profile | Hyper-narrow source/test slices plus compact State Ledger | System indexes, dependency trees, plan history, interface contracts, invariants |
| Primary output | Compile-ready bounded patch capsule | Execution sequence, interface specifications, safety invariants, rollback conditions |
| Failure mode | Tunnel vision; misses global impacts | Consensus drift; boilerplate; token and latency tax |

## Planning results

| Arm | Calls | Estimated input | Estimated output | Estimated total | Grounded-plan quality | Normalized cost* |
|---|---:|---:|---:|---:|---:|---:|
| Broad-context single planner | 1 | 130,485 | 1,169 | 131,654 | 0.9550 | $0.133992 |
| Aura-slice single planner | 1 | 13,201 | 1,667 | 14,868 | 0.9607 | $0.018202 |
| Length-aware Council V2 | 18 | 154,226 | 4,319 | 158,545 | 0.9625 | $0.167183 |

\*Normalized comparison cost uses a declared $1/M input and $3/M output rate card. It is not a provider invoice.

Council V2 produced the strongest planning score:

- **+0.0075** versus broad context;
- **+0.0018** versus the sliced planner.

However, it used:

- **20.43% more total token proxy** than broad context;
- approximately **10.66×** the total token proxy of the sliced planner.

The sliced planner therefore remained the strongest single-call quality-per-token arm.

### Council role costs

| Role | Calls | Estimated input | Estimated output |
|---|---:|---:|---:|
| Planner | 1 | 395 | 2,011 |
| Alternate planner | 1 | 396 | 1,546 |
| Shadow critics | 15 | 127,473 | 687 |
| Judge | 1 | 25,962 | 75 |

Shadow review consumed approximately **82.6%** of Council input-token proxy. Selective critic routing is therefore the largest obvious Council optimization.

## Refactor length profile

The selected plan was classified `LONG`:

- 8 Act Capsules;
- 17 distinct files;
- estimated minimum 8 model turns;
- estimated maximum 24 model turns;
- Council planning recommended because the work is cross-module and multi-step.

Council V2 preserved the plan-level fields dropped by V1:

- acceptance criteria;
- rollback conditions;
- risk map;
- constraints;
- escalation rules.

## Multi-step execution scaling

The execution benchmark used deterministic sliced workers and one forced local repair in the 4-, 8-, and 10-step cases.

| Steps | Turns | Estimated input | Estimated output | Fixture-reported input | Fixture-reported output | Estimated tokens per completed step |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 602 | 51 | 452 | 51 | 653.0 |
| 4 | 5 | 3,287 | 255 | 2,513 | 255 | 885.5 |
| 8 | 9 | 5,984 | 459 | 4,611 | 459 | 805.4 |
| 10 | 11 | 7,405 | 562 | 5,730 | 562 | 796.7 |

All scenarios reached `READY_FOR_HUMAN_REVIEW` without production mutation.

## State preservation and context drift

Aura passed a compact State Ledger instead of replaying all preceding turns, patches, and verifier records.

The ledger records:

- plan phase identity;
- completed and current tasks;
- dependency map;
- safety invariants;
- latest stage and verification digests;
- repair attempts;
- Council replan count;
- execution status.

### Ten-step local-repair case

| Point | State Ledger proxy | Full-history proxy | Avoided history | Ledger/history ratio | State preservation | Context drift |
|---|---:|---:|---:|---:|---:|---:|
| Step 3 | 227 | 1,670 | 1,443 | 13.59% | 1.0000 | 0.0000 |
| Step 7 | 234 | 6,140 | 5,906 | 3.81% | 1.0000 | 0.0000 |

At step 7, the State Ledger was approximately **96.19% smaller** than replaying recorded history. Deterministic fact matching found no state loss in the synthetic test.

### Ten-step graph-replan case

The graph-replan case also recorded:

- minimum state preservation: **1.0000**;
- maximum context drift: **0.0000**;
- step-7 State Ledger: **237** token proxy;
- step-7 full history: **6,032** token proxy;
- avoided history: **5,795** token proxy.

These are deterministic state-consistency measurements, not semantic-model cognition measurements.

## Token amortization

The initial Council planning cost was 158,545 total token proxy.

| Ten-step scenario | Initial Council | Surgeon execution | Bounded Council replan | Hybrid total | Initial Council amortized per step |
|---|---:|---:|---:|---:|---:|
| Local assertion failure | 158,545 | 8,147 | 0 | 166,692 | 15,854.5 |
| Graph/interface/invariant failure | 158,545 | 8,115 | 2,039 | 168,699 | 15,854.5 |

A hypothetical full Council run at every step would cost:

```text
158,545 × 10 = 1,585,450 token proxy
```

Compared with that clearly labeled extrapolation:

- local-repair hybrid avoided **1,426,905** tokens, or **90.00%**;
- graph-replan hybrid avoided **1,424,866** tokens, or **89.87%**.

This validates the accounting mechanism: a strategic Council can be amortized over many bounded Surgeon steps. It does not prove that the initial Council is necessary or quality-improving for every ten-step refactor.

## Rollback and recovery routing

Two failures were injected at step 4.

### Local failure

Evidence:

```text
focused unit-test assertion failure
one task
one file
no downstream invalidation
no interface, dependency, or invariant breach
```

Route:

```text
SURGEON_LOCAL_REPAIR
```

Outcome:

- one repair turn;
- zero Council replans;
- all ten steps completed;
- terminal state `READY_FOR_HUMAN_REVIEW`.

### Graph-level failure

Evidence:

```text
interface contract invalidated
dependency graph invalidated
downstream tasks invalidated
invariant breach
multi-file and multi-task blast radius
```

Route:

```text
ESCALATE_TO_COUNCIL_REPLAN
```

Outcome:

- zero local repair turns;
- one bounded Council replan;
- replan token proxy: 2,039;
- Surgeon resumed from preserved completed work;
- all ten steps completed;
- terminal state `READY_FOR_HUMAN_REVIEW`.

The router also escalates when the configured local-repair budget is exhausted.

## Persistent evidence and learning

Each recorded refactor can preserve:

- objective and plan phase hash;
- prompt and response digests;
- redacted content-addressed prompt and response evidence;
- estimated input and output tokens;
- provider-reported input and output tokens when supplied;
- provider-reported cost when supplied;
- Act Capsule, staging, verification, repair, and replan events;
- State Ledger snapshots and drift metrics;
- final outcome and human-review boundary;
- learning notes;
- ArenaExperience V3 projection.

Default paths:

```text
Aura_Memory/refactor_chronicle.jsonl
Aura_Memory/refactor_evidence/
Aura_Memory/benchmarks/benchmark_registry.jsonl
```

Workflow evidence uses artifact-local paths so each benchmark package remains independently replayable.

## Measurement labels

- Repository files, bytes, lines, call counts, task transitions, routes, and terminal states: **MEASURED**.
- Token counts without provider usage: **ESTIMATED_CHAR4_PROXY**.
- Synthetic worker provider fields: **DETERMINISTIC_FIXTURE_REPORTED**.
- Quality and normalized costs: **DERIVED**.
- State preservation: **DERIVED_DETERMINISTIC_FACT_MATCH**.
- Council-every-step comparison: **DERIVED_EXTRAPOLATION**.
- Real patch quality: **NOT MEASURED** by the synthetic execution benchmark.
- Provider billing: **UNAVAILABLE** in the fixture run.

## Limitations and next experiment

The benchmark supports the hybrid control-flow and accounting hypothesis, but not yet the real-code-quality hypothesis.

The next publication-grade experiment must use:

1. a temporary worktree;
2. a real ten-step repository refactor;
3. independently generated provider responses;
4. exact tokenizer usage and billed cost;
5. blinded acceptance tests;
6. at least three orchestration arms:
   - sliced Surgeon only;
   - Council once plus Surgeons;
   - Council at every gate or an adaptive Council;
7. measured compilation, tests, regressions, repairs, blast radius, and human-review time.

Only that experiment can determine where Council strategic quality actually outweighs its token tax.

## Reproduce

```bash
python aura_codebase_navigator.py

python aura_architect_consolidation_benchmark_v2.py prepare \
  --repo-root . \
  --output-dir benchmark-output

python benchmarks/architect_consolidation/generate_gpt56_pilot_fixture.py \
  --output benchmark-output/responses.gpt-5.6-thinking.json

python aura_architect_consolidation_benchmark_v2.py score \
  --repo-root . \
  --output-dir benchmark-output \
  --responses benchmark-output/responses.gpt-5.6-thinking.json \
  --input-rate 1.0 \
  --output-rate 3.0

python aura_multistep_refactor_benchmark.py \
  --repo-root . \
  --output-dir benchmark-output/multistep \
  --lengths 1,4,8,10

python aura_hybrid_refactor_benchmark.py \
  --repo-root . \
  --output-dir benchmark-output/hybrid \
  --planning-report benchmark-output/architect_consolidation_benchmark.json
```

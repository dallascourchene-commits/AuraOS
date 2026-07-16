# Aura Architect Consolidation Benchmark

**Benchmark:** `AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V1`  
**Status:** reproducible single-session pilot; plan-only; no production mutation  
**Model fixture:** GPT-5.6 Thinking (single-session assisted pilot)

## Objective

> Scan the AuraOS repository and produce a grounded, staged refactor skeleton that consolidates memory, skill, capability, and agentic functions to improve the Human Agent Arena. Reuse existing Aura architecture, preserve compatibility through explicit adapters, retain plans and verifier evidence, and require human approval before mutation or promotion.

All three arms use the same repository commit, objective, JSON plan contract, and deterministic grounding rubric.

## First measured results

| Arm | Model calls | Input token proxy | Output token proxy | Total token proxy | Grounded-plan quality | Normalized cost* |
|---|---:|---:|---:|---:|---:|---:|
| Broad-context single planner | 1 | 130,485 | 1,169 | 131,654 | 0.9550 | $0.133992 |
| Aura-slice single planner | 1 | 13,201 | 1,667 | 14,868 | 0.9607 | $0.018202 |
| Aura Architect Council | 12 | 90,020 | 4,121 | 94,141 | 0.9458 | $0.102383 |

\*Normalized cost uses a declared **$1 per million input-token proxy** and **$3 per million output-token proxy** rate card. It is derived for comparison and is **not** a provider invoice or current market price.

### Measured and derived deltas

- Aura slices reduced input-token proxy by **89.88%** versus broad context.
- Aura slices reduced total-token proxy by **88.71%** and normalized cost by **86.42%**.
- The sliced plan's deterministic quality changed by **+0.0057** versus broad context.
- The 12-call Council remained **28.49%** below the broad-context total-token proxy and **23.59%** below its normalized cost.
- The Council quality changed by **-0.0092** versus broad context and did **not** outperform the single sliced planner.
- The tested repository inventory was 860 source/config/document files, 52,671,947 bytes, 1,538,107 lines, and a 13,167,987 char/4 token proxy.
- The Aura-slice input was **99.90%** below that full-repository token proxy. The broad-context arm was **99.01%** below it because the baseline used a relevance-ranked 520,000-character cap rather than transmitting every repository byte.

## What this first pilot supports

The first run supports three narrow claims:

1. Aura can replace a broad repository handoff with a much smaller, exact-slice planning packet.
2. In this task, the sliced packet preserved and slightly improved the deterministic grounded-plan score.
3. Aura can drive a real multi-role Architect Council while measuring aggregate planner, critic, and Judge consumption rather than hiding extra calls.

It does **not** yet support claims of general quality superiority, Council superiority, production refactor success, provider-billed cost savings, consciousness, or a conclusively revolutionary architecture.

## Defects discovered by the benchmark

### 1. Generic localization displaced the intended subsystem

The first prompt-preparation run returned `LOCALIZE_FIRST` with fallback files from civic, AMD, and server surfaces before reaching the Architect/Human-Agent spine. The refined benchmark adapter now ranks:

1. exact source spans;
2. selected capability-lane modules;
3. grounded affordances;
4. objective-core Architect/Human-Agent files;
5. generic fallback candidates.

This correction is recorded as benchmark behavior, not silently hidden.

### 2. Council normalization lost plan-level contracts

The submitted planner candidate contained:

- `acceptance_criteria`;
- `rollback_conditions`;
- `risk_map`;
- `constraints`.

The current `ArchitectFusionCouncil._normalize_plan_spec()` output did not preserve those plan-level fields. The Act Capsule fields survived, but the selected plan lost part of its governance envelope. This must be repaired before the Council result becomes the canonical persistent skeleton.

### 3. A scope keyword produced a false repo-wide route

The experience-capture task referenced “repository and source digests” in its acceptance text. The current scope heuristic interpreted the word `repository` as repo-wide edit authority and routed the task `PLAN_ONLY` with `scope_too_broad_for_act_capsule`, despite its exact target file and symbol.

The heuristic should distinguish **evidence about a repository** from **authority to edit a repository**.

### 4. One experience target lacked a nearby test mapping

`aura_arena_experience.py::build_arena_experience` was exact and blocker-free, but the Architect grounding step found no nearby test file under its current naming heuristic. The generated skeleton therefore remains a human-review proposal and is not marked refactor-ready.

## Generated refactor skeleton

The Council-selected skeleton contains eight bounded Act Capsules covering:

1. persistent Human Agent plan workspace;
2. capability-lane, affordance, and SkillWeaver consolidation;
3. Architect-to-Planning-Board projection;
4. governed Architect experience capture;
5. canonical Agent Arena MCP slice sessions;
6. explicit SkillWeaver adapter input;
7. Human Agent Arena plan/revision visualization;
8. Arena experience-ledger and Crucible handoff.

The skeleton is intentionally marked:

```text
next_gate = HUMAN_REVIEW_BEFORE_REFACTOR
production_mutation = false
patch_authority = exact_source_spans_and_hashes_only
vsa_patch_authority = false
```

## Reproduce

```bash
python aura_codebase_navigator.py

python aura_architect_consolidation_benchmark_refined.py prepare \
  --repo-root . \
  --output-dir benchmark-output

python benchmarks/architect_consolidation/generate_gpt56_pilot_fixture.py \
  --output benchmark-output/responses.gpt-5.6-thinking.json

python aura_architect_consolidation_benchmark_refined.py score \
  --repo-root . \
  --output-dir benchmark-output \
  --responses benchmark-output/responses.gpt-5.6-thinking.json \
  --input-rate 1.0 \
  --output-rate 3.0

python aura_architect_benchmark_report.py \
  --report benchmark-output/architect_consolidation_benchmark.json \
  --responses benchmark-output/responses.gpt-5.6-thinking.json \
  --skeleton benchmark-output/architect_consolidation_skeleton.json
```

## Measurement labels and limitations

- Repository bytes, lines, file counts, CODEMAP size, and model-call count are **MEASURED** from the tested commit.
- Token values are **ESTIMATED** using a deterministic four-bytes-per-token proxy.
- Quality scores and normalized costs are **DERIVED**.
- Provider-reported tokens and billed costs are **UNAVAILABLE** in this fixture run.
- The model responses were authored in one GPT-5.6 Thinking session, so the pilot is not blinded and cross-arm contamination cannot be ruled out.
- The broad baseline used relevance-ranked complete files with a global cap, not every repository byte.
- The quality rubric measures grounding, exact targets, tests, boundedness, domain coverage, governance, Shadow findings, and Arena routing. It does not prove the long-term success of the future refactor.

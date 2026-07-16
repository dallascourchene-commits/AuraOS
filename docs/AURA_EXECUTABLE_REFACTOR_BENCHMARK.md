# Aura Executable Refactor Code-Quality Benchmark

**Benchmark:** `AURA_EXECUTABLE_REFACTOR_CODE_QUALITY_V1`  
**Council ablation:** `AURA_ARCHITECT_COUNCIL_CALLING_ABLATION_V1`  
**Record schema:** `AURA_REFACTOR_OUTPUT_RECORD_V1`  
**Workflow run:** `29475732851`  
**Tested head:** `d12cbabaf6408ddf59613d0d6d51e01e1e33cf0d`  
**Artifact digest:** `sha256:19788b0a303cf6a4674d6ce67716acf30e6681991c4afa38487b14d3a4a9505a`

## Why this benchmark exists

The earlier Aura benchmarks measured planning quality, grounding, context reduction, token usage, State Ledger continuity, and repair routing. They did not measure the engineering quality of actual generated patches.

This benchmark adds an isolated executable comparison. Every method receives the same cross-module task, starting fixture, allowed files, visible tests, hidden tests, regression tests, API contract, security scan, static analysis, and maintainability measurement.

Every result is retained even when a mandatory gate fails. Working behavior and acceptance are separate:

- `ACCEPTED` — all required gates passed;
- `WORKED_BUT_NOT_ACCEPTABLE` — functional behavior passed but another required gate failed;
- `PARTIAL` — some measured functional behavior passed and some failed;
- `FAILED` — the patch did not apply, compile, or pass measured functionality;
- `CODE_QUALITY_UNAVAILABLE` — no executable patch was produced.

## Controlled task

> Refactor the failure router and compact State Ledger so false graph-breach fields stay with local repair, true graph/interface/invariant breaches escalate to a Council replan, exhausted local repair budget escalates, and compact state preserves identity without replaying raw history. Preserve public APIs and edit only `router.py` and `state.py`.

The fixture contains:

- five starting source/package files;
- two authorized source files;
- three visible tests;
- three held-out tests not included in the patch prompt;
- two regression tests;
- public API signature checks;
- scope checks;
- Bandit security checks;
- Ruff static analysis;
- before/after maintainability measurements.

The fixture is executable and cross-module, but smaller than a production AuraOS refactor. Patch fixtures were authored in one assisted session; this is not a blinded independent-provider trial.

## Executable code-quality results

| Refactoring method | Calls | Input proxy | Output proxy | Total proxy | Visible | Hidden | Regression | API | Scope | Security | Working status | Disposition | Observed score | Benchmark score |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---:|
| Broad-context single implementer | 1 | 130,485 | 1,169 | 131,654 | 3/3 | 1/3 | 2/2 | PASS | PASS | PASS | `PARTIALLY_WORKING` | `PARTIAL` | 80.34 | 78.33 |
| Aura-slice single Surgeon | 1 | 13,201 | 1,667 | 14,868 | 3/3 | 2/3 | 2/2 | PASS | PASS | PASS | `PARTIALLY_WORKING` | `PARTIAL` | 88.89 | 86.67 |
| Council V2 plan + Surgeon | 18 | 154,226 | 4,319 | 158,545 | 3/3 | 3/3 | 2/2 | PASS | PASS | PASS | `WORKING` | `ACCEPTED` | 100.00 | 97.50 |
| Selective Council V3 plan + Surgeon | 12 | 102,436 | 4,058 | 106,494 | 3/3 | 3/3 | 2/2 | PASS | PASS | PASS | `WORKING` | `ACCEPTED` | 100.00 | 97.50 |

Performance and portability were not measured, so measurement completeness was **97.5%** for every arm. The benchmark score treats unmeasured weighted dimensions as zero; the observed score normalizes only measured dimensions.

### Partial results remain visible

The broad-context patch applied, compiled, passed all visible tests, passed both regression tests, preserved APIs, stayed within scope, and passed the security scan. It failed two of three hidden tests, so it is `PARTIAL`, not discarded.

The sliced Surgeon patch applied, compiled, passed all visible tests, passed two of three hidden tests, passed both regression tests, preserved APIs, stayed within scope, and passed the security scan. It therefore scored higher than the broad-context patch while using **88.71% fewer total token proxy**, but remained `PARTIAL` because one held-out case failed.

Both Council-guided patches passed every required gate. They also passed Ruff, while the broad and sliced patches retained a static-analysis failure as recorded evidence. Static analysis was measured but was not a mandatory acceptance gate in this fixture.

## Selective Council V3 calling ablation

Council V2 called every long-refactor critic lane uniformly. Council V3 selects critic lanes from measurable plan structure and risk evidence.

| Council policy | Calls | Critic reports | Input proxy | Output proxy | Total proxy | Planning quality |
|---|---:|---:|---:|---:|---:|---:|
| Council V2, uniform critics | 18 | 15 | 154,226 | 4,319 | 158,545 | 0.9625 |
| Council V3, selective critics | 12 | 9 | 102,436 | 4,058 | 106,494 | 0.9625 |

Measured V3 changes:

- **33.33% fewer total model calls**;
- **40.00% fewer critic reports**;
- **33.58% lower input-token proxy**;
- **32.83% lower total-token proxy**;
- **0.0000 planning-quality delta**;
- the same substantive selected plan after excluding version-only metadata;
- the same executable patch digest as V2;
- the same `ACCEPTED` disposition;
- the same 100.00 observed and 97.50 benchmark code-quality scores.

On this frozen fixture, Selective Council V3 is therefore more quality-adjusted efficient than Council V2.

### Critic routes selected by V3

- deterministic one-task local candidate: `scope`, `tests`;
- eight-task long planner candidate: `scope`, `tests`, `continuity`, `rollback`;
- seven-task long alternate candidate: `scope`, `tests`, `rollback`.

V3 skipped `cost` and `sequence` where the candidate evidence did not justify them. This is a first positive ablation, not proof that these lanes are unnecessary in general.

## Standard evidence record

Every executable arm emits a JSON record validated by:

```text
schemas/aura_refactor_output_record.schema.json
```

The record preserves:

- repository/task/arm identity;
- prompt, response, and patch digests;
- estimated and provider-reported input/output tokens separately;
- patch size and files touched;
- exact visible, hidden, and regression test counts;
- failing test identifiers and JUnit report digests;
- build/compile evidence;
- API compatibility;
- authorized scope and blast radius;
- security and static-analysis evidence;
- maintainability before/after/delta;
- observed and benchmark quality scores;
- measurement completeness;
- every failed required gate;
- working status and final disposition.

Append-only summaries are stored under:

```text
Aura_Memory/benchmarks/refactor_output_records.jsonl
```

Artifact-local registries make each benchmark package independently replayable.

## Industry-reference mapping

Aura uses the following as reference frameworks, not as a claim of formal certification:

- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) for product-quality characteristics and acceptance-oriented quality evaluation;
- [ISO/IEC 5055:2021](https://www.iso.org/standard/80623.html) for automated source-code quality measures and structural-risk evidence;
- [NIST SP 800-218 SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) for repeatable secure-development evidence and vulnerability-risk reduction;
- [OWASP SAMM](https://owasp.org/www-project-samm/) for measurable, risk-driven software-security assurance;
- [SWE-bench](https://www.swebench.com/) for isolated repository-task evaluation, held-out tests, resolved outcomes, and cost-aware comparison.

Aura's evaluator is an industry-aligned evidence layer. It is not an ISO certification, a NIST compliance claim, an OWASP endorsement, or an official SWE-bench result.

## Reproduce

```bash
python -m pytest -q \
  tests/test_aura_refactor_output_quality.py \
  tests/test_aura_architect_council_v3.py

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

python aura_architect_council_calling_benchmark.py \
  --repo-root . \
  --responses benchmark-output/responses.gpt-5.6-thinking.json \
  --output-dir benchmark-output/council-calling

python benchmarks/refactor_code_quality/generate_fixture.py \
  --output-dir benchmark-output/executable-fixture \
  --planning-report benchmark-output/architect_consolidation_benchmark.json \
  --calling-ablation benchmark-output/council-calling/council_calling_ablation.json

python aura_executable_refactor_benchmark.py \
  --fixture-dir benchmark-output/executable-fixture \
  --output-dir benchmark-output/executable-quality
```

## What remains to prove

The next benchmark tier should use:

- independent provider calls rather than one assisted fixture;
- tokenizer-exact and provider-billed usage;
- multiple independent trials per arm;
- local, cross-module, and long-horizon task suites;
- real AuraOS tasks in isolated worktrees;
- hidden tests written independently of the generated patches;
- mutation testing, coverage, type checking, dependency scanning, and performance thresholds where relevant;
- blinded human review of maintainability and architectural fit;
- outcome variance and confidence intervals.

The present result supports a narrower claim:

> On this executable controlled fixture, Council guidance produced more complete held-out behavior than either single method, and selective Council V3 preserved V2 planning and code quality while reducing its token and call cost by roughly one third.

## 4A. Refactor Code-Quality Benchmarking

Use this workflow when comparing engineering quality from broad context, Aura slices, Council-guided execution, or another refactoring method.

### Interpret the result

Aura records **working behavior** separately from **acceptance**:

| Disposition | Meaning |
|---|---|
| `ACCEPTED` | Every required gate passed |
| `WORKED_BUT_NOT_ACCEPTABLE` | Functional behavior passed, but scope, API, security, regression, or another required gate failed |
| `PARTIAL` | Some measured functional behavior passed and some failed |
| `FAILED` | Patch application, compilation, or measured functionality failed completely |
| `CODE_QUALITY_UNAVAILABLE` | The arm produced only a plan or synthetic control-flow result |

Do not discard a rejected patch's passing evidence. Inspect `failed_required_gates`, exact test counts, and per-gate evidence.

### Run focused tests

```bash
python -m pytest -q \
  tests/test_aura_refactor_output_quality.py \
  tests/test_aura_architect_council_v3.py
```

### Reproduce the executable comparison

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

### Read the records

```text
benchmark-output/executable-quality/executable_refactor_benchmark.json
benchmark-output/executable-quality/*.refactor-output.json
benchmark-output/executable-quality/refactor_output_records.jsonl
```

Persistent summaries default to:

```text
Aura_Memory/benchmarks/refactor_output_records.jsonl
```

Each record stores estimated and provider-reported input/output tokens separately. Provider fields remain null when the provider did not report them.

### Required engineering evidence

A serious executable comparison should include:

1. clean patch application;
2. compilation or repository-native build;
3. visible tests;
4. hidden tests unavailable to the coding method;
5. regression tests;
6. public API compatibility unless change is authorized;
7. authorized-file scope and blast radius;
8. security checks;
9. maintainability and repository-native static analysis;
10. performance, portability, coverage, mutation, type, and dependency checks when relevant.

### Selective Council V3

Council V3 always reviews scope and tests. It adds sequence, continuity, rollback, and cost critics only when plan length, dependency edges, large tasks, risk, or rollback evidence justify them.

The first controlled result retained Council V2's accepted patch and 100.00 observed code-quality score while reducing Council calls from 18 to 12 and total token proxy from 158,545 to 106,494.

See:

- `docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`
- `docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`
- `schemas/aura_refactor_output_record.schema.json`

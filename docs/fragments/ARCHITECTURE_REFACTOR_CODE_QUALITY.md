## 1B. Refactor Engineering Evidence and Selective Council Architecture

Aura treats **planning quality**, **orchestration quality**, and **executable code-output quality** as separate evidence classes.

```text
objective
→ Council or single-planner strategy
→ bounded Surgeon patch
→ isolated patch application
→ compile/build
→ visible tests
→ held-out tests
→ regression tests
→ API and scope checks
→ security and static analysis
→ maintainability delta
→ standardized output record
→ human review and acceptance
```

A high planning score cannot be relabelled as code quality. A synthetic State Ledger or rollback test cannot be relabelled as patch correctness. Code-output quality remains unavailable until an executable patch is evaluated.

### Council–Surgeon cognitive labor

```text
Selective Council V3
  → architecture, dependencies, interfaces, invariants, sequence, rollback
  → only critic lanes justified by candidate evidence

Sliced Surgeon
  → exact-file implementation
  → focused verification
  → bounded local repairs

Escalation
  → interface/dependency/invariant invalidation
  → broad downstream change
  → exhausted local-repair budget
```

Universal critic lanes are `scope` and `tests`. Sequence, continuity, rollback, and cost lanes are admitted from measured plan structure and risk rather than called uniformly.

### Canonical output record

`AURA_REFACTOR_OUTPUT_RECORD_V1` records:

- task, repository, model, provider, and arm identity;
- prompt, response, and patch digests;
- estimated and provider-reported input/output tokens separately;
- patch size and files touched;
- exact visible, hidden, and regression test counts;
- build, API, scope, security, static-analysis, maintainability, performance, and portability evidence where measured;
- observed score, benchmark score, and measurement completeness;
- failed required gates;
- `WORKING`, `PARTIALLY_WORKING`, `NOT_WORKING`, or `UNDETERMINED` status;
- `ACCEPTED`, `WORKED_BUT_NOT_ACCEPTABLE`, `PARTIAL`, `FAILED`, or `CODE_QUALITY_UNAVAILABLE` disposition.

All measured quality is preserved when a gate fails. Functional success does not erase a security, scope, API, or regression failure; a failed gate does not erase passing tests or useful partial behavior. No aggregate score overrides mandatory gates.

Primary modules and contracts:

- `aura_architect_council_v3.py`
- `aura_refactor_output_record.py`
- `aura_refactor_patch_evaluator.py`
- `aura_refactor_patch_evaluator_v2.py`
- `aura_code_quality_registry.py`
- `aura_executable_refactor_benchmark.py`
- `schemas/aura_refactor_output_record.schema.json`
- `docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`

Append-only summaries default to:

```text
Aura_Memory/benchmarks/refactor_output_records.jsonl
```

The evidence vocabulary is aligned by reference—not certification—to ISO/IEC 25010:2023, ISO/IEC 5055:2021, NIST SSDF 1.1, OWASP SAMM, and SWE-bench-style isolated patch evaluation.

### First executable result

On the controlled cross-module fixture, Council V2 and Selective Council V3 passed 3/3 visible tests, 3/3 hidden tests, 2/2 regression tests, API, scope, security, compilation, static analysis, and maintainability gates. V3 retained the same substantive plan, executable patch digest, and quality scores while reducing total token proxy by **32.83%** and model calls by **33.33%**.

This supports selective critic routing for the tested case. General superiority still requires independent-provider, multi-trial, real-worktree benchmarks.

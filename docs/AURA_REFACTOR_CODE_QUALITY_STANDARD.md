# Aura Refactor Code-Output Quality Standard

**Record:** `AURA_REFACTOR_OUTPUT_RECORD_V1`  
**Quality standard:** `AURA_REFACTOR_CODE_QUALITY_STANDARD_V1`  
**Schema:** [`schemas/aura_refactor_output_record.schema.json`](../schemas/aura_refactor_output_record.schema.json)

## Purpose

Aura's earlier benchmarks measure planning quality, grounding, context reduction, token usage, state preservation, and repair routing. Those measurements are useful, but they are not measurements of the engineering quality of generated code.

This standard gives every real refactor output the same evidence record. It preserves all measured quality—even when a mandatory gate fails.

A patch can therefore be:

- `ACCEPTED`;
- `WORKED_BUT_NOT_ACCEPTABLE`;
- `PARTIAL`;
- `FAILED`;
- `UNDETERMINED`;
- `CODE_QUALITY_UNAVAILABLE` when no executable patch was produced.

A passing functional test does not erase a scope, compatibility, security, or regression failure. A failed gate does not erase passing tests, complexity measurements, token usage, or useful partial behavior.

## Industry alignment

Aura uses the following standards and benchmark practices as reference models. This is an evidence mapping, not a claim that AuraOS or a generated patch is formally certified.

### ISO/IEC 25010:2023

The product-quality model supplies the high-level vocabulary used for:

- functional suitability;
- reliability;
- performance efficiency;
- compatibility;
- security;
- maintainability;
- portability.

Reference: [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html).

### ISO/IEC 5055:2021

The automated-source-code quality standard motivates automated evidence for:

- reliability;
- performance efficiency;
- security;
- maintainability.

Reference: [ISO/IEC 5055:2021](https://www.iso.org/standard/80623.html).

### NIST SP 800-218 SSDF 1.1

The Secure Software Development Framework motivates repeatable security evidence, provenance, reviewability, and prevention of recurring vulnerabilities throughout the software lifecycle.

Reference: [NIST SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final).

### OWASP SAMM

OWASP SAMM motivates measurable, risk-driven security assurance across the software lifecycle rather than treating one scanner result as complete security proof.

Reference: [OWASP SAMM](https://owasp.org/www-project-samm/).

### SWE-bench-style evaluation

SWE-bench established the practical pattern of evaluating a patch against a fixed repository snapshot and tests for a real issue. Aura adopts the useful parts of this approach:

- clean isolated workspace;
- fixed task and repository snapshot;
- unified-diff output;
- patch-application check;
- execution against tests;
- held-out tests not present in the model prompt;
- Pass@1 as a primary outcome;
- retained trajectory, cost, and evidence.

Long-refactor suites should additionally use multi-file, long-horizon tasks, human-verified resolvability, and held-out evaluation in the spirit of long-horizon software-engineering benchmarks.

## Required record identity

Every arm and trial receives a unique record containing:

```text
benchmark_id
run_id
case_id
arm_id
method
repository_commit_sha
objective
model and provider
prompt digest
response digest
patch digest
```

The record also retains estimated and provider-reported input/output tokens separately.

## Executable gates

### Patch integrity

- unified diff parses;
- patch applies cleanly to the declared repository snapshot;
- touched files are recorded;
- additions and deletions are recorded.

### Compilation or build

For Python, Aura runs `python -m compileall`. Other language adapters should run the repository-native build or compiler.

### Visible tests

Tests visible to the coding method measure direct requirement satisfaction and repair responsiveness.

### Hidden tests

Held-out tests are excluded from model context and measure generalization beyond visible examples. Hidden-test exposure must be recorded explicitly.

### Regression tests

The unchanged repository test suite or a declared regression subset must still pass.

### API compatibility

Unless the task explicitly authorizes an API change, Aura compares public function, method, and class signatures before and after the patch.

### Scope and blast radius

Touched files must remain inside the Act Capsule's authorized file set. Out-of-scope edits are retained as evidence and fail the scope gate even when all tests pass.

### Security

Security evidence should include repository-native SAST or dependency tooling. The initial Python adapter supports Bandit as a fixed tool. Production suites should add the repository's existing security checks and record all results.

### Maintainability

Aura records before/after and delta measurements for:

- maximum and mean cyclomatic-complexity proxy;
- functions above a complexity threshold;
- maximum function length;
- functions above a length threshold;
- patch size and files touched;
- repository-native lint and type checks when enabled.

### Performance and portability

Performance and platform matrices are task-specific. They remain `NOT_MEASURED` unless the task declares a reproducible threshold and evidence source.

## Scoring without evidence loss

Aura stores two scores:

### Observed quality score

Normalizes only the quality dimensions actually measured. This answers:

> How good was the patch on the evidence we collected?

### Benchmark quality score

Treats unmeasured dimensions as zero for cross-run comparability. This prevents a lightly measured patch from appearing superior to a comprehensively measured patch.

### Measurement completeness

The percentage of the weighted quality model that was actually measured.

None of these scores overrides mandatory gates.

## Working status versus acceptance

### `WORKING`

The patch applies, compiles, and passes all measured functional-test groups.

### `PARTIALLY_WORKING`

The patch applies and compiles, and at least one measured functional group passes while another fails.

### `NOT_WORKING`

The patch does not apply, does not compile, or passes no measured functional group.

### `WORKED_BUT_NOT_ACCEPTABLE`

The code works functionally, but one or more mandatory non-functional or governance gates fail. Examples:

- all functional tests pass, but an unauthorized file was edited;
- tests pass, but the public API changed without authorization;
- tests pass, but a security scanner finds a new issue;
- tests pass, but regression tests fail.

This distinction implements the rule: **record all code quality, then state which gates prevented acceptance.**

## Fair comparison protocol

Every refactoring method must receive:

- the same task wording and acceptance contract;
- the same starting commit;
- the same allowed files and tool permissions;
- the same model where the benchmark isolates orchestration effects;
- the same temperature or deterministic settings;
- the same time, turn, and cost budgets;
- the same visible tests;
- the same inaccessible hidden tests;
- the same regression suite;
- the same evaluator version.

Required arms for Aura's first executable comparison:

1. broad-context single planner/implementer;
2. Aura-slice single Surgeon;
3. Council plan followed by sliced Surgeon execution;
4. Council-per-step ablation for a bounded subset;
5. optional human reference patch.

Each arm should run multiple independent trials. Report Pass@1, trial count, variance, token and cost distribution, repair count, elapsed time, and every `AURA_REFACTOR_OUTPUT_RECORD_V1` result.

## Task suites

A serious benchmark should contain at least three length classes:

### Local

- one or two files;
- shallow dependency graph;
- focused refactor or bug fix.

### Cross-module

- three to seven files;
- interface and compatibility constraints;
- meaningful regression risk.

### Long-horizon

- eight or more bounded steps;
- multiple modules and dependency edges;
- at least one planned migration or compatibility adapter;
- local-repair and graph-replan opportunities;
- hidden tests for downstream effects.

Tasks should be human-verified as resolvable and should not be authored from the exact patch shown to the evaluated model.

## Current Aura assessment

The current benchmark arms are recorded honestly:

| Existing arm | Output kind | Code-output quality |
|---|---|---|
| Broad-context planner | `PLAN_ONLY` | `CODE_QUALITY_UNAVAILABLE` |
| Aura-slice planner | `PLAN_ONLY` | `CODE_QUALITY_UNAVAILABLE` |
| Length-aware Council V2 | `PLAN_ONLY` | `CODE_QUALITY_UNAVAILABLE` |
| Hybrid local-repair simulation | `SYNTHETIC_CONTROL_FLOW` | `CODE_QUALITY_UNAVAILABLE` |
| Hybrid graph-replan simulation | `SYNTHETIC_CONTROL_FLOW` | `CODE_QUALITY_UNAVAILABLE` |

Their existing planning, token, state, and routing findings remain valid. They do not yet establish generated-patch engineering quality.

## Files and storage

```text
aura_refactor_output_record.py
aura_refactor_patch_evaluator.py
aura_current_code_quality_assessment.py
aura_code_quality_registry.py
schemas/aura_refactor_output_record.schema.json
Aura_Memory/benchmarks/refactor_output_records.jsonl
```

Workflow artifacts use an artifact-local registry so each benchmark package remains independently replayable.

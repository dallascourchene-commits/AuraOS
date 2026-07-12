# Aura Phase C3 — Isolated Capsule Trials and Agent IR Procedure Induction

Status: `DRAFT_REVIEW_REQUIRED`

Phase C3 connects the merged C2 live route-capsule runtime to Aura's existing proposal-only Crucible and Agent IR floors. It does not modify the live C2 selection path. It creates bounded variants, executes trusted deterministic trial adapters in Aura's ephemeral sandbox lifecycle, measures them, and emits a review-only procedure proposal.

## Execution model

```text
pinned C2 ExecutableRouteCapsule
  -> baseline plus single-axis tightening variants
  -> explicit C3 feature flag and independent trial lease
  -> bounded TRAIN trials in ephemeral temporary sandboxes
  -> TRAIN-only deterministic winner selection
  -> independent VALIDATION comparison against baseline
  -> independent SHADOW comparison against baseline
  -> typed Agent IR induction
  -> PROCEDURE_INDUCTION_PROPOSED
  -> verifier and human review
```

## Proposal-safe dimensions

Only these limits may vary, and only toward a value less than or equal to the pinned C2 baseline:

```text
data_aperture.maximum_files
data_aperture.maximum_symbols
data_aperture.maximum_lines
execution_budget.input_tokens
execution_budget.output_tokens
execution_budget.tool_calls
execution_budget.wall_seconds
```

A variant cannot alter morphology, VSA profile, requested capabilities, tool bundle, model policy, verifier contract, output schema, component digests or transition identity.

## Isolation contract

C3 reuses `aura_ephemeral_sandbox.py` rather than inventing a second sandbox. The initial trial executor is a repository-owned, allowlisted deterministic localization adapter. When Wasmtime is unavailable, Aura remains in built-in-only mode. C3 never describes Python subprocesses or AST filtering as secure arbitrary-code isolation and never silently falls back to native execution.

Every trial records:

- sandbox mode and receipt;
- exact context items and BLAKE2 source hashes;
- deterministic output digest;
- input/output token estimates;
- tool and model calls;
- wall-clock duration;
- requested and consumed budgets;
- OutcomeVector and proposal projection;
- capability revocation, temporary-directory removal and dissolution verification.

## Dataset separation

The versioned case manifest declares disjoint `TRAIN`, `VALIDATION` and `SHADOW` cases. TRAIN alone ranks variants. VALIDATION and SHADOW are run only after the winner is fixed and compare it with the pinned baseline. Their results cannot influence selection.

## Agent IR induction

Successful repeated traces advance only when evidence supports each floor:

```text
TEXT  raw observed expression
TYPED typed trial and output records
SPEC  explicit bounds, digests and preconditions
STUB  stable input/output contract
SHIM  one allowlisted executor bridge
PURE  reproducible deterministic procedure with all independent gates passed
```

`PURE` means a verified deterministic Agent IR procedure proposal. C3 does not emit source code. C4 may later package a reviewed procedure as crystallized code.

## New modules

- `aura_capsule_trial_types.py`
- `aura_capsule_variant_generator.py`
- `aura_capsule_trial_runner.py`
- `aura_agent_ir_induction.py`
- `aura_capsule_trial_store.py`
- `aura_phase_c3_trial_crucible.py`
- `aura_capsule_trial_cli.py`

Versioned inputs:

- `.aura/capsule_trial_policies/coding_localize.v1.json`
- `.aura/capsule_trial_cases/coding_localize.v1.json`

## CLI

```bash
python -m aura_capsule_trial_cli status

python -m aura_capsule_trial_cli run-once \
  --enable-trials \
  --lease-capability trial:isolated_capsule \
  --lease-capability tool:topology_inspector

python -m aura_capsule_trial_cli procedures
python -m aura_capsule_trial_cli procedure CPROC-...
```

There is no `apply`, `activate`, `install`, `promote`, `commit`, `push` or `merge` command.

## Authority boundary

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
capsule_trial_selection_authority: train_only_offline
validation_shadow_authority: assessment_only
arbitrary_code_execution: false
active_capsule_mutation: false
automatic_capsule_activation: false
automatic_grammar_promotion: false
executable_code_generated: false
automatic_code_installation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

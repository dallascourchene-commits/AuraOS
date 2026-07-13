# Human Agent Arena — Guided Showcase Workspace

## Purpose

The Human Agent Arena remains a fully usable guarded workspace. The suggested demo is an optional navigation layer over the real workflow, not a second implementation and not a scripted simulation.

```text
INTAKE → FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

A user may exit the tour or display the complete workspace at any time.

## Suggested demo path

### 1. INTAKE

Choose one of the bounded CODEMAP tasks, receive a Civic issue, or open an Aura Observatory handoff.

The starter task provides:

- an ordinary-language objective;
- six intent slots;
- exact seed files and symbols;
- acceptance criteria;
- prohibited operations;
- a bounded topology projection.

Loading a task does not grant patch authority.

### 2. FRAME

The tour calls the existing guarded `set_objective` workflow action.

Changing the objective clears stale evidence in the established `HumanAgentWorkflow`; no independent demo state is treated as workflow evidence.

### 3. GROUND

The tour calls `ground_context`, which uses Aura's existing topology inspector to localize:

- exact files;
- symbols and source spans;
- connected tests;
- callers and dependencies;
- risks and grounding evidence;
- sandbox or dissolution receipts where produced.

The 3D topology remains an orientation and selection surface. Exact source spans and hashes remain authoritative.

### 4. PLAN

The tour calls `prepare_capsule` with the selected task's acceptance criteria.

The real Agent Arena bridge prepares:

- a plan-phase hash;
- Action Capsules;
- target files and symbols;
- leases and constraints;
- focused tests;
- a bounded worker handoff.

### 5. ACT

The user may paste a worker-generated unified diff. The tour calls the existing `stage_patch` action with the exact affected files and symbols already grounded by Aura.

The patch is staged through the Arena boundary. Production source is not mutated directly.

### 6. PROVE

The tour calls the existing actions in order:

```text
run_tests → verify_patch
```

Focused tests run through the ephemeral test lab and measured evidence is preserved for the independent verifier.

### 7. DECIDE

The tour calls the established review-only actions:

```text
check_hotswap → human_review → export_handoff
```

The default demonstration review records `approved: false`. No commit, push, merge, production promotion, or grammar promotion is performed.

## Free workspace mode

The rail does not replace the original Arena surfaces. Users can:

- exit the tour;
- display every panel together;
- select any topology task;
- rotate and expand topology manually;
- invoke any currently admitted WFST transition;
- inspect blocked transitions and missing evidence;
- ask the grounded guide about the current gate;
- paste a candidate diff;
- inspect exact guarded results;
- open the Learning Arena / Crucible.

## Observatory navigation repair

The Observatory Next control now has one user-facing navigation authority. From the first view it can:

```text
ordinary intention
→ Compile and show lexical addresses
→ routing tags
→ six-slot packet
→ FST hard gate
→ bounded handoff
```

The repair uses capture-phase event delegation so the control survives the Observatory's dynamic toolbar and button replacement. It also updates its enabled state as the user types.

## Authority invariants

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
visual_topology_patch_authority: false
worker_output_authority: proposal_only
production_mutation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
automatic_grammar_promotion: false
human_review_required: true
```

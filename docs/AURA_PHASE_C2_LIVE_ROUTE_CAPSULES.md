# Aura Phase C2 — Live Guarded Route Capsules

## Purpose

Phase C2 connects the Phase C1 polysynthetic bind/bundle and Executable Route Capsule contracts to Aura's live guarded Arena WFST without transferring authority to VSA resonance.

```text
input
→ state-local transitions
→ hard guards
→ existing capability grounding
→ compile/materialize declared capsule
→ advisory resonance among already-admitted transitions
→ bounded action execution
→ ArenaExperience V3
```

## First live use case

`CODING.TASK_SCOPED.LOCALIZE_CODE` is bound through the independently digestible overlay:

`.aura/arena_capsule_bindings/coding_workbench.v1.json`

The overlay avoids rewriting the compact one-line Coding Workbench grammar and is validated against the exact arena and grammar version. Unknown transitions, mismatched versions, duplicate bindings, stale components, and failed capability grounding fail closed.

## Feature flag

Live materialization is enabled only when either:

- runtime policy contains `route_capsules_enabled: true`; or
- `AURA_ROUTE_CAPSULES_ENABLED=1`.

When disabled, the guarded transition behaves as before and the capsule is reported as disabled. There is no automatic activation mechanism.

## Materialized aperture

After admission, the selected capsule supplies bounded copies of:

- data aperture;
- memory aperture;
- grounded tool bundle;
- model policy;
- execution budget;
- verifier contract;
- output schema.

The localization action enforces the pinned maximum file, symbol, and line budgets before downstream model reasoning. It records actual context items, tool calls, model use, and consumed retrieval counts.

## Experience V3

Every capsule-backed execution can record:

- capsule and capsule-manifest digests;
- polysynthetic intent packet digest;
- VSA profile digest;
- all component digests;
- resonance;
- requested budget;
- actual context items;
- actual tools and model;
- consumed budget.

All admissible alternatives and predictions remain preserved. The ledger migrates V2 databases in place using SQLite WAL.

## Authority boundary

```yaml
hard_guards_before_capsules: true
capability_grounding_before_capsules: true
vsa_routing_authority: advisory_after_hard_guards
vsa_patch_authority: false
automatic_capsule_activation: false
automatic_grammar_promotion: false
automatic_code_installation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

Phase C2 does not run Crucible trials, induce procedures, generate code, or install crystallized implementations. Those remain Phase C3 and C4 work.

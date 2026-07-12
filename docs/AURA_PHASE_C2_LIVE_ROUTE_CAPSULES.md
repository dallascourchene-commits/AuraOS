# Aura Phase C2 — Live Guarded Route Capsules

## Status

Phase C2 connects the deterministic polysynthetic and route-capsule contracts from C1 to Aura's live guarded Arena WFST path.

It is deliberately opt-in. The existing `ArenaWFSTRuntime` and `CodingWorkbenchWFSTSession` remain available and retain their prior behavior.

## Authority order

```text
state-local transitions
→ exact/semantic input projection
→ hard guards and evidence gates
→ existing capability binding
→ declared or operator-attached route capsule
→ component-digest revalidation
→ explicit capability lease
→ bounded aperture materialization
→ advisory VSA resonance
→ deterministic selection
→ existing action implementation
→ measured usage and OutcomeVector
```

Hard guards, policy, lifecycle, evidence and leases remain authoritative. Capsule resonance can only rank transitions already admitted by the base runtime. It cannot add an inadmissible transition, grant a capability, mutate a grammar or install code.

## Transition contract

`ArenaTransition` now supports three optional declarative fields:

```yaml
morphology_profile_ref: .aura/morphology_profiles/six_slot.v1.json
route_capsule_ref: .aura/route_capsules/coding_localize.v1.json
capsule_feature_flag: c2_coding_localization_enabled
```

`CapsuleAwareArenaWFSTRuntime.register_manifest()` compiles any declared references during grammar registration. A failed declared attachment makes the registration report fail closed.

The first Coding Workbench MVP path also uses an explicit operator-owned attachment so C2 can be reviewed without rewriting the compact production grammar manifest.

## Feature and lease gates

Two independent conditions are required:

1. the runtime is constructed with `route_capsules_enabled=True`;
2. the route policy contains `route_capsules_enabled: true` and the transition-specific feature flag.

A materialized capsule must also receive every requested capability through `context.lease_capabilities`.

Feature disabled:

- legacy route selection is preserved;
- the capsule is reported as configured but disabled;
- no aperture is materialized.

Feature enabled but lease or digest invalid:

- the transition is removed from the admitted set;
- an exact command abstains with `exact_transition_blocked_by_capsule`;
- the runtime does not fall through to a different action.

## Runtime intent packet

C2 derives an observable `PolysyntheticIntentPacket` from the command, state, explicit context and policy:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

Risk, grounding, context class, model class and resource budget remain orthogonal adjuncts. No hidden reasoning or chain-of-thought is stored.

## Aperture materialization

`aura_route_capsule_materializer.py` reloads and verifies every pinned C1 component before producing a non-executing aperture:

- data aperture;
- memory aperture;
- grounded tool bundle;
- model policy;
- execution budget;
- verifier contract;
- output schema.

It rejects:

- stale component digests;
- unbounded repository context;
- missing capability leases;
- disallowed models;
- path traversal in observed context;
- budget overruns.

Materialization does not execute a tool or retrieve source code. It only describes and bounds what the existing action is allowed to use.

## Coding Workbench MVP path

`CapsuleCodingWorkbenchWFSTSession` is an opt-in subclass of the existing 18-state adapter. The first live capsule targets:

```text
TASK_SCOPED
→ CODING.TASK_SCOPED.LOCALIZE_CODE
→ CODE_LOCALIZED
```

The action still calls Aura's existing `aura_code_region_ranker.rank_code_regions` implementation. C2 clamps the returned files, symbols and line ranges to the pinned data aperture and records measured token estimates, tool calls, model usage and elapsed time.

Measured post-execution budget overruns deny the state transition. Localization is read-only, so a denial does not leave a patch or production mutation behind.

Example construction:

```python
from aura_coding_workbench_capsule_adapter import CapsuleCodingWorkbenchWFSTSession

session = CapsuleCodingWorkbenchWFSTSession(
    repo_root=".",
    route_capsules_enabled=True,
    capsule_lease_capabilities=["tool:topology_inspector"],
    requested_model="no_model",
)
```

No capability is granted by that constructor. The supplied lease must come from Aura's existing authority path.

## ArenaExperience V3

Every capsule-aware experience may record:

- `intent_packet_digest`;
- `vsa_profile_digest`;
- `route_capsule_digest`;
- `aperture_digest`;
- `actual_context_digest`;
- `actual_tool_calls`;
- `actual_model`;
- `budget_requested`;
- `budget_consumed`.

The SQLite ledger migrates V2 databases in place, adds a capsule/aperture index and does not invent capsule provenance for historical rows. The existing `v2_complete_record_count` status field remains as a compatibility alias.

Complete admissible alternatives and predictions remain preserved. Predictions now include capsule resonance and capsule/aperture digests where present.

## Safety boundary

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
capsule_ranking_authority: advisory_after_hard_guards
automatic_capsule_activation: false
automatic_grammar_promotion: false
automatic_code_installation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

## Deferred to C3

C2 does not:

- generate capsule variants;
- run Crucible TRAIN/VALIDATION/SHADOW trials;
- infer reusable procedures;
- promote Agent IR maturity;
- generate crystallized code;
- install a winning capsule automatically.

Those operations belong to Phase C3 and must consume the measured C2 experience records through proposal-only review gates.

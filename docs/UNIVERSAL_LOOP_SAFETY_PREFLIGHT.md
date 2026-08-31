# Universal Loop-Safety Preflight

Status: global, cross-project, fail-closed.

This contract prevents three recurring classes of failure:

1. repeated identical retrievals that acquire no new provider state;
2. repeated/no-op mutations used as event pressure; and
3. action-selection mismatch, where the intended mutation differs from the tool action actually selected.

## Required execution envelope

Before a read, bind:

`R = (provider/tool, resource/ref, query/pattern, page/range, semantic purpose)`

If the same `R` is proposed again without an independently observed provider state transition, do not execute it. Change retrieval axis or collapse the cone.

Before a write, bind:

`A = (action class, target object, allowed fields, expected state delta, repair route)`

If the selected action, target, or fields do not match `A`, stop before mutation. If a mismatched primitive executes once, freeze that primitive for the objective.

## No-op history rule

`SameBlob + NewCommit != NewEvidence`

One no-op mutation is sufficient to diagnose event behavior. A no-op mutation that fails to produce the intended external transition blocks repeating the same write key.

## Mutation stop

Any unintended semantic mutation raises `MUTATION_STOP`. Freeze writes, record the exact before/after identities, and repair only through a different verified primitive.

## Poll/event rule

Do not re-poll an unchanged terminal state. Re-poll only after a new run/job/head/revision/provider retry condition, or through a genuinely different evidence axis.

Provider events must be produced by provider-native control surfaces. Do not manufacture `synchronize`, `reopened`, webhook, or similar events through repeated identical file writes.

## Scope and authority

The guard is process control only. It grants no semantic, effect, provider, K27, coordinate-memory, model-state, or native/private transformer-KV authority.

Canonical laws:

- `SameRetrievalFingerprint + NoNewState => CHANGE_AXIS_OR_COLLAPSE`
- `IntendedAction != SelectedAction => STOP_PRIMITIVE`
- `SameBlob + NewCommit != NewEvidence`
- `NoOpHistoryDrift != ProofProgress`
- `UnintendedSemanticMutation => FREEZE_WRITES + RECORD + REPAIR_VIA_DIFFERENT_PRIMITIVE`
- `ToolLoop != ArenaStop`

# Creator Studio Continuation WorkGraph — staged reference

This is the bounded G2 / `CS-WG-RUNTIME-001` realization for the Creator Studio Always-On Arena Continuation Harness.

## Contract

`aura_arena_workgraph.py` projects machine-readable Creator Studio/Arena workers, work cells and coordination claims into a deterministic WorkGraph. It provides:

- dependency-aware OPEN / CLAIMED / BLOCKED / COMPLETE projection;
- canonical orientation / board revision / currentness / route-policy binding;
- worker capability and D0 effect-ceiling selection gates;
- fail-closed duplicate active-claim collision handling;
- compare-and-swap CLAIM / RELEASE / COMPLETE / BLOCK / REOPEN / ADD_CELL transitions;
- receipt-bound execution-state transitions;
- safe stale-claim recovery only when `execution_state=NOT_STARTED`;
- `RECONCILE_EFFECT_STATE_REQUIRED` when a stale/released claim may have started an effect;
- evidence-required completion and append-only completed history;
- deterministic priority ordering;
- changed-state wake intent;
- `NO_CHANGE_NO_MODEL` when only wall time moves and no consequence state changes.

## Reality boundary

A WorkGraph claim is coordination state, not runtime liveness. A wake intent is not a delivered ChatGPT turn. The module never calls a provider, never claims a browser window can wake itself, and never grants authority. A production AuraOS/Arena/Resident adapter must persist accepted compare-and-swap transitions and deliver a real authorized turn when `delivery_required=true`.

An expired lease is not proof that retry is safe. If effect state is anything other than provably `NOT_STARTED`, the projection blocks automatic reassignment until the effect state is reconciled from receipts.

## Relationship to the continuation harness

The sibling H-B replenisher on draft PR #312 owns finish -> release -> scan -> claim and residual -> successor-objective policy. This module supplies the machine projection, eligibility and transition primitives H-B/H-G can consume without duplicating scheduler state.

The branches currently have different substrates: PR #312 was authored from `main`, while this G2 reference is stacked on the staged Arena architecture branch `paperx-rev41-joinable-cognition-places-20260829`. Integration must resolve that substrate/currentness difference rather than silently treating them as one head.

The other harness lanes (entry admission, cost/swarm routing, adversarial Gate-10 testing and live scheduler/wake integration) remain independently owned work.

## Constructor / adversarial evidence

The focused isolated battery now passes **22/22** tests. It covers dependency/capability eligibility, collision prevention, safe stale-claim recovery, ambiguous-effect replay refusal, evidence-bound completion, dependency wake, currentness, compare-and-swap basis rejection, successor-cell admission, D1 exclusion, no-change/no-model behavior, lease-expiry digest transition, receipt-bound execution transitions, effect-started release refusal, append-only completed history, typed block/reopen behavior and UNKNOWN execution exclusion.

The stronger stale/effect and completion rules were added after applying the C0 harness sidecar acceptance contract (`01_C0-SUPPORT__CS-HARNESS-001__CONTINUATION-STATE-MACHINE-ACCEPTANCE-BATTERY__20260830`).

This is reference evidence only. It is not owner-host runtime proof, independent approval, Gate 8 or Gate 10, and it does not prove an external wake bridge is deployed.

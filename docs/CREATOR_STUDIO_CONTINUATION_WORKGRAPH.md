# Creator Studio Continuation WorkGraph — staged reference

This is the bounded G2 / `CS-WG-RUNTIME-001` realization for the Creator Studio Always-On Arena Continuation Harness.

## Contract

`aura_arena_workgraph.py` projects machine-readable Creator Studio/Arena workers, work cells and coordination claims into a deterministic WorkGraph. It provides:

- dependency-aware OPEN / CLAIMED / BLOCKED / COMPLETE projection;
- currentness and D0 effect-ceiling gates;
- worker capability-fit selection;
- fail-closed duplicate active-claim collision handling;
- expired coordination-claim recovery;
- compare-and-swap CLAIM / RELEASE / COMPLETE / BLOCK / REOPEN / ADD_CELL transitions;
- deterministic priority ordering;
- changed-state wake intent;
- `NO_CHANGE_NO_MODEL` when only wall time moves and no consequence state changes.

## Reality boundary

A WorkGraph claim is coordination state, not runtime liveness. A wake intent is not a delivered ChatGPT turn. The module never calls a provider, never claims a browser window can wake itself, and never grants authority. A production AuraOS/Arena/Resident adapter must persist accepted compare-and-swap transitions and deliver a real authorized turn when `delivery_required=true`.

## Relationship to the continuation harness

The sibling H-B replenisher owns finish -> release -> scan -> claim and residual -> successor-objective policy. This module supplies the machine projection, eligibility and transition primitives H-B can consume without duplicating scheduler state.

The remaining harness lanes (entry admission, cost/swarm routing, adversarial Gate-10 testing and live scheduler/wake integration) remain separate work.

## Constructor evidence

The focused local constructor battery passed 14/14 tests. It covers dependency/capability eligibility, collision prevention, stale-claim recovery, dependency wake, currentness, compare-and-swap basis rejection, successor-cell admission, D1 exclusion, no-change/no-model behavior and the lease-expiry digest transition.

This is constructor evidence only. It is not owner-host runtime proof, independent review, Gate 8 or Gate 10, and it does not prove an external wake bridge is deployed.

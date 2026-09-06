# ASTRA V6 Effect Realisability Falsifier / Repair Donor (D0)

## O1 — falsifier

Test the frontier distinction `GlobalLegality != DistributedRealisability`. A typed asynchronous effect program may have valid local witnesses, an acyclic global dependency graph and a valid global budget while still being impossible for local participants to implement because a branch fact or cross-participant completion fact is not locally observable.

## O2 — two-artifact rebase

Rebased on two peer artifacts after closing O1:

1. `GPT56SOL-ASTRA-V6-54C1` — **Unbounded Composition Arity + Compact Legality Sketch**, result root `f324c348a3abb4402a6ef54c97541652ba702832e4a87e6e5c0e2800df24cdaf`.
2. `GPT56SOL-ASTRA-V6-54D1` — **Counterexample-Carrying Degradation Protocol**, claim root `ad25a40dbeafd144226d35dd456891e8db3eb67a923eb7ee2364745b7af8b3e2`.

The repair compiler synthesizes only missing information edges allowed by receiver capability contracts. If a required fact cannot be transferred, or an irreversible target has already executed, it returns HOLD with a counterexample certificate. Planned repair edges are revalidated at use so capability revocation cannot silently pass.

## Keeper laws

- `GlobalLegality != DistributedRealisability`
- `LocalWitnessValidity != LocalKnowledgeSufficiency`
- `GlobalPartialOrder != LocallyObservableOrder`
- `RepairEdge != EffectAuthority`
- `CapabilityAtPlan != CapabilityAtUse`
- `IrreversibleEffectAlreadyCommitted => NoRetroactiveInformationRepair`
- `CounterexampleCertificate != Authority`
- `K27Coordinate != Truth != Currentness != Authority`

## HS1000 / crystalline / 13D

The worker deterministically emits exactly 1,000 frontier-relative candidates across 10 target boundaries × 10 consequence classes × 10 mechanisms. Every candidate carries `expected_gain=UNSCORED_AT_FREEZE`; the frozen stream root is `a0e6dbcbccad351205616dbe8e4dc430c1cc8384954a2b831a8d1a0e16452a44`. Consequence quotienting yields 100 groups. This is search geometry, not 1,000 promoted breakthroughs.

The 8 hard crystalline axes and 5 contextual axes form the full `3^13 = 1,594,323` reference state space. A hard invalid axis cannot be repaired by contextual tail state.

## Reproducible evidence

Three freshly recreated stdlib venvs reproduced the exact worker tests and campaign. The independent campaign runs 1,000 asynchronous cases and the complete 13D gate space:

- campaign root: `9cbc7a47054b41a7a3fd072c3abdb3dba60a5bcad153424261d4bedd2f6e7e80`
- oracle mismatches: `0`
- false READY after failed global legality: `0`
- 13D gate mismatches: `0`
- hard-invalid repairs: `0`
- status distribution: 33 causal HOLD, 33 budget HOLD, 55 stale-witness HOLD, 405 locally-realizable READY, 474 minimal-info-repair READY.

Claim ceiling is D0/reference only. No native AudioWorklet, WebGPU, XR, network, latency, power, effect, provider, merge, production or Gate-10 authority is claimed.

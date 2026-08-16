# D0 EGMMS Benchmark Harness

This directory implements the first concrete D0 harness for the Evidence-Gated
Memory-Mode Selection (EGMMS) contract.

## Governing law

> PROVE THE MODE SAFE; MEASURE ITS COST; SELECT LOCALLY; FALL BACK TO CURRENT OWNERS.

The harness is bound to EGMMS synthesis bundle SHA-256:

`c9f6c13f23decb0b53d1a567dd4f9b72fd01d24b67db115472ae760e4ddc21f6`

## Important status

The included FST-routing and mobile-kernel workload envelopes are **deterministic
reference fixtures**, not measurements of production execution paths. They exist
to test D0's admission, selection, receipt, restart, invalidation, and fallback
contracts while the live Aura code-map/filesystem seam is being reconciled.

A production adapter should replace only the fixture measurements and canonical
owner adapter. It must not weaken the admission gates.

## Memory modes

- `FULL_CONTEXT_FULL_PROOF`
- `CONVENTIONAL_VERSIONED_MEMOIZATION`
- `PERSISTENT_REACTIVATION_KERNEL`
- `DERIVATIVE_RECONSTRUCTION`
- `OWNER_GATED_NEAR_STATELESS`

## Safety admission

Cost is ignored unless a mode passes every hard gate:

1. zero stale source/PASS escape;
2. exact current J56/V30 receipt compatibility for every reused receipt;
3. no UNKNOWN laundering;
4. live authority/provenance/repair duties preserved and current permission
   independently verified;
5. equivalent lawful result after generated-state deletion/restart;
6. complete invalidation fanout;
7. reconstruction before the consequence deadline or behind an enforceable fence.

A failed mode receives infinite selector cost and cannot win.

## Receipts

`runD0Benchmark()` emits `aura.d0.mode-selection.v1`.

The receipt is:
- advisory only;
- bound to the exact EGMMS bundle digest;
- deterministic/digest-addressed;
- explicit about canonical source/authority generations;
- explicit about each V30 receipt check and safety gate;
- always equipped with a `CURRENT_OWNER` fresh-read fallback.

`verifyModeSelectionReceipt()` re-reads the canonical owner state and current
permission; it does not trust the selector receipt as authority.

## Run

From the repository root:

```bash
node --test tests/js/d0-egmms-benchmark.test.mjs
```

The harness deliberately uses only Node built-ins.

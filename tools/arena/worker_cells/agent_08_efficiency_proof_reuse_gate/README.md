# AGENT_08 — Workload-Qualified Efficiency Proof Reuse V3 / O2R3

## Objective
Fail closed on efficiency-proof reuse unless the current AGENT_27 proof-reuse contract and AGENT_07 workload-qualified cost contract are replayed with exact pinned semantics and the resulting current projection roots equal the proof-time roots.

## Current parent generations
- AGENT_27 current branch generation: `955267f7884a1cc4c4a91ccf95dd084afa329798`; verifier source blob `0e886c41e21254445dfa68ce3813698c48bb1fad`.
- AGENT_07 semantic generation: `09302691da7292ac2e2b75a0e9c5d6409848f609`; verifier source blob `dbfc655897e3402517ba978b0856ea8a96595b0f`.
- AuraOS main/source generation: `7a2c7a16f845752ffb7c16c68636d8d542ecd72e`.

AGENT_27 moved after O2R2. Its pre-existing exact-reuse/resource/trace path is consequence-unchanged; generation-ancestry machinery was appended. J59 therefore requires a current-generation rebind and fresh reproof even though the scoped consequence is unchanged.

## Independent-review invalidator
Current CodeRabbit/Kilo review of O2R2 found two blocking defects:
1. AGENT_27 evidence was only checked against caller-supplied `expected_*` values instead of replaying the pinned verifier decision/receipt semantics.
2. The AGENT_07 mirror omitted `effect_authority` and `gate10` from `CostEnvelope`, so its canonical envelope/result roots could not equal the pinned verifier's output.

O2R2 is stale historical evidence and receives no current PASS inheritance.

## O2R3 repair
- Replays the pinned AGENT_27 `RESOURCE_TRACE_REPLAY_BENCHMARK` exact-reuse branch: shape, strict booleans/integers, result/workflow/input/dependency/required-step/binding identity, resource envelope, cumulative budget/oracle prerequisites, canonical trace schema, event reconstruction, execution provenance, fused-event structure, changed-path semantics, and D0 authority ceiling.
- AGENT_08 deliberately does **not** expose proof-neutral generated-child rebind; that remains upstream because AGENT_27's provider observation is a bounded consistency check, not provider-authenticated truth.
- Reconstructs the AGENT_27 evidence root and receipt fields from the full parent evidence object; no second caller-supplied `expected projection` participates inside the parent replay.
- Replays the AGENT_07 workload/transfer/envelope/Decimal receipt contract exactly, including `effect_authority=False` and `gate10=False` inside canonical envelope identity.
- Compares the newly replayed parent projection roots to the recorded proof-time projection roots. Any drift => `REPROVE`.
- Binds all five trailing 13D context axes into receipt identity; context cannot alter a failed hard-axis decision.

## Claim boundary
`ParentSemanticReplayExact != ParentTruthAuthenticated`.

This worker verifies composition parity with the pinned parent contracts. It does not upgrade AGENT_27's own caller-supplied truth prerequisites into cryptographic/provider truth. It does not mint hosted PASS, truth/effect authority, deployment/merge authority, physical model results, native/private transformer KV access, or Gate10.

## Fresh local reproof
Three freshly recreated stdlib-only virtual environments on final O2R3 bytes:
- 23/23 focused tests per environment = **69/69 PASS**; `py_compile` PASS.
- 10,000 independently spelled AGENT_27 differential decisions per environment: **0 mismatches**.
- 10,000 independently spelled AGENT_07 receipt differentials per environment: **0 mismatches**.
- HS1000: **0/1,000 false reuses**.
- destructive successor handoff: **0/50,000 false reuses**.
- Ω8: all 6,561 states; exactly one D0 keeper.
- 13D: 100,000 context tails; all 243 distinct context roots; zero repairs.
- stable campaign root in all three: `97d25d8f86b0ce20b33ee1d3292b4c38651563e2885e3afdc39d33a2cb7fb275`.
- valid receipt root: `d1299c440ae1c2109c6999578f652186e81cc2b3fbae721a6241e0fbf2b33c09`.

Final local SHA-256 before publication:
- implementation `6c8eaf91bef1a3dfec8d6eaadfbd445f9ddc1902b4f4e5170a0a72e085037bd1`
- tests `b89b63259beedd834b9370f345db1f03831038fb2b8c66dee0856ee5a4e362dc`
- campaign `d096783cbb3b0eacf05b7956a7f0e928a0f484687117cb03146b9c5b285037dc`

## J59 / HyperScale keeper
`GenerationMoved -> ClassifyScopedConsequence -> ReplayCurrentOwnerContract -> ReproveMinimumLawfulCone`.

`SelfConsistentDigest != IndependentSourceExit`.

`ExactParentReplay != ExternalParentAuthentication`.

Function > cardinality: HS1000/Ω8/13D/differential counts are falsification geometry, not advancement counts.

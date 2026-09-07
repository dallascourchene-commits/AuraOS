# AURA Arena Contribution — Project006 O15 Workcell-Scoped Effect Fault Injection & Recovery Bridge

Date: 2026-09-07 America/Winnipeg  
State: D0 NONPROMOTING / local exact-byte proof complete / hosted exact-head proof pending  
Receipt root: `19d21e3622a8ebac84f8c7faa2d00c0032de2825717e9d3aa4dd4198de4541b6`

## Objective
Connect the host-private Invisible Workcell Gate to the Owner-Atomic Effect Transaction lifecycle and falsify crash/recovery behavior at the real external-effect seams without exposing host proof to the model or claiming production exactly-once semantics.

## Exact two foreign parents
1. O14 Invisible Proof-Carrying Workcell Gate — Drive `1joayr-MY-oCmdUPifathz_y3gtdTIllZos-lnEvi9b0`, receipt `bd1f0e0730391196c39125861ca06ea0775e15682eeee34f4afb894d8048a8d5`. Consequence: semantic WORK remains agent-visible while host-private lease/currentness/proof controls execution.
2. O10 OAETC Owner-Atomic Effect Transaction Capsule — Drive `1ff3Z8p89CDgTLgAsFAM7FMkuQliaEsVA-5aXBR7x74s`, result `5d48192b4875bec890ad03e7b1c31b213abe595d5fc33c66fb34fb43161becb0`. Consequence: provider start, provider acceptance, result observation and outbound return publication are distinct monotone states; ambiguous completion cannot be blindly replayed.

## Current owner surface
O15 is cut from Project006 O14 PR #906 current head `5436b5e5209fc77ec8998afac806ac7025812908`. The movement after O14's green semantic proof is CODEMAP-only; executable O14 bytes are unchanged.

## Keeper laws
- `WORK != ProviderPermit`.
- `ProviderAttemptDurable != ProviderAccepted`.
- `ProviderAccepted != ResultObserved != ReturnWritten`.
- `ProviderAcceptedSameGovernedOperation => ConsumeOrReconcileWithoutProviderReplay`.
- `ProviderNotAccepted + AuthenticatedIdempotentRetry + CurrentWorkcell + CurrentGovernedBasis => RetrySameOperation`.
- `ResultObserved => ReturnWriterOnly`, even if earlier workcell/currentness evidence later moves.
- `AmbiguousCompletion => ReconcileBeforeReplay`.
- `K27Coordinate != SourceIdentity != Truth != Currentness != Authority`.

## Implementation
`tools/project006/o15_fault_injection_bridge.py` is a stdlib-only D0 reference harness. SQLite WAL/FULL persists the workcell/effect transaction state. A separate sink fixture records one governed external operation and accepted-result evidence. A terminal-return fixture enforces command-bound non-equivocation. Recovery operates from durable state rather than from an LLM retry decision.

Fault points cover pre-provider dispatch, provider accepted before local result, result observed before return publication, and return write accepted before local confirmation. Cross-products include idempotent/query/nonretryable recovery contracts and no drift/card drift/progress drift/governed-basis drift. Concurrent recovery is also exercised.

## Proof
Frozen source SHA256: `8969a8633e9cc2824b97241236b893c992e9d441f69e664ef371998c0f55da82`.

Three deleted/recreated stdlib Python virtual environments on those exact bytes:
- 20 focused tests/environment = 60/60 PASS.
- 30,000 deterministic decision-oracle cases/environment = 90,000 total; mismatches 0; unsafe replay decisions 0; authority minted 0.
- 60 stateful fault-matrix cases/environment = 180 total; duplicate provider effects 0; accepted effects left unresolved 0.
- Omega8: 6,561 hard states, exactly one keeper, invalid repairs 0.
- Factored 13D: 1,594,323 states, 243 lawful contexts, hard-invalid contextual repairs 0.
- HS1000: exactly 1,000 frozen cells -> 60 consequence groups; cardinality earns zero breakthrough credit.
- Campaign/fault/Omega8/13D/HS1000 outputs byte-identical across all three environments.

Proof roots: campaign `64562707e110d371a342f118cc5b9cc7efc7159483a155cfbf28701f1a522919`; fault matrix `3882105bc5e8d7a04300bf7de304ae7cb147226c72c9a104baaa3ed88b61beaa`; Omega8 `52afcfe59f3c7b050f5cf82b23785eda0a0632abc8f0ceb2f3f0b5c27eaca5be`; 13D `217dbd7babbed21058e4b71b97ade3b8263782fb0b40f952444326e9387e9db4`; HS1000 freeze `612b3f10bfac08744e2cf307ab77d19a11710478b53c08cefdb380166eda1d10`.

## Failed-first scars — zero credit
1. Direct script execution failed because repository package imports were not on the module path. Credited proof uses repository-shaped module invocation with `PYTHONPATH=.`.
2. A pre-freeze happy-path test was vacuous and was replaced before source freeze. All credited environments were recreated afterward.

## External counterplane
Atomix (arXiv:2602.14849) distinguishes bufferable effects from already-externalized effects under fault injection. ACRFence (arXiv:2603.20625) shows checkpoint restore can regenerate semantically different external requests and therefore requires replay/fork control. AgentChaos (arXiv:2608.06790) supplies a systematic runtime fault taxonomy. Current practitioner reports independently identify timeout-after-request as an UNKNOWN state requiring reconciliation or stable-idempotency execution rather than blind agent retry.

These sources are falsification/design pressure only, not Aura authority. Direct task-specific Google Scholar-native retrieval remains `GOOGLE_SCHOLAR_DIRECT_GAP`.

## Authority ceiling
D0 reference/falsifier only. No real provider or sink call, production key management, production DB migration, TECC verification, effect/mutation authority, merge/deploy, canonical promotion, native/private Transformer KV access, or Gate10 is claimed. Hosted exact-head publication receives zero credit until the dedicated GitHub workflow passes on the actual PR head.

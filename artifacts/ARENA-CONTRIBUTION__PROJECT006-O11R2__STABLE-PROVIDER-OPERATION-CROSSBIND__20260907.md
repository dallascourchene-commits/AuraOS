# AURA Arena Contribution — Project006 O11R2 Stable Provider Operation Crossbind

Date: 2026-09-07 America/Winnipeg  
State: D0 NONPROMOTING / local source-shaped three-venv proof complete / hosted exact-head proof pending

## Objective
Close the surviving provider-operation identity seam above Project006 PR899 without creating a second currentness, sink-evidence, effect, or final-return owner. A PR899 provider-action candidate must not reach an adapter until one stable semantic provider-operation identity is durably bound. After ambiguous completion, retry/query/consume must remain cross-bound to that same operation and consume authenticated PR901-style recovery evidence rather than PR899's blind retry branch.

## Exact two foreign parents
1. PR899 current effect-attempt owner, exact pre-publication head `5cba43512b70a33ad7394a4cb1c1e43bf8f1e09e`. Its attempt path persists attempt/currentness identity but does not mint or carry `provider_operation_root` before first provider-call exposure.
2. PR901 O12R1 owner-authenticated attempt/sink-fence recovery, exact reviewed head `27ae27b02f8a4dd607f96f8a9940af169a9ff349`, proof root `89cc9d29f439b6bb992266ebedd737439553b18a6888059e0dca842f78d31c90`. This child consumes that recovery verdict instead of duplicating its trust plane.

## Keepers
`DurableEffectAttempt != DurableProviderOperationIdentity`  
`AttemptIdentity != ExternalOperationIdentity`  
`ParentProviderPermit != ProofCarryingProviderPermit`  
`AmbiguousCompletion + IdempotentContract != ReplayPermission`  
`AuthenticatedRecoveryVerdict + ExactStableOperation + NewDurableParentAttempt => ReplayCandidateD0`

## Implementation
The stdlib reference installs a thin SQLite WAL/FULL operation journal. Stable operation identity binds command ID, logical idempotency key, source digest, intent root, contract root, and effect payload root, deliberately excluding attempt sequence/currentness receipt churn. The first provider candidate is owner-row/permit cross-checked and operation identity is durable before exposure. Semantic drift changes the operation identity and fails closed.

After ambiguity there is no blind-retry route. An already-authenticated PR901-style verdict must name the exact current owner row and exact stable provider operation. Retry additionally requires a new durable PR899-shaped retry attempt while preserving the same operation. Query and sink-result consumption preserve operation identity but do not expose a provider-call attempt.

## Proof
Local compact source-shaped run: three deleted/recreated stdlib virtual environments; 18 focused tests/environment = 54/54 PASS; 30,000 exact-oracle cases/environment = 90,000 total; oracle mismatches 0; false provider actions 0. Campaign/Ω8/13D/HS1000 outputs were byte-identical across all three environments.

Ω8: 6,561 hard states, exactly one keeper. 13D: 1,594,323 factored states, 243 lawful contextual variants, 0 hard-invalid contextual repairs. HS1000: exactly 1,000 frozen cells, 60 consequence groups, zero cardinality-as-breakthrough credit.

The publication source is intentionally re-run by a dedicated exact-head GitHub workflow; until that succeeds, the hosted publication receives zero exact-head proof credit.

## J59/J190 / HyperDrive grounding
J190/V01 preserves J59's `FUNCTION > CARDINALITY` control and the keeper `ArtifactSemanticProvenance != ExactCurrentProof`. O11R2 applies that distinction directly: semantic external-operation identity can survive attempt/currentness receipt churn, while every consequential action still needs at-use current owner/recovery evidence.

## External counterplane / K27
Machine-Checked Dual-Write Recovery from a Committed Log (arXiv:2608.00501) supplies independent pressure that crashed-side durable state cannot determine remote sink acceptance; sink evidence and fencing are separate obligations. Fresh Memory, Stale Plans (arXiv:2609.03340) supports dependency-scoped at-use validation. Proof-Carrying Agent Actions (arXiv:2606.04104) supports evidence-bearing execution boundaries. Current Reddit production discussions independently emphasize durable pre-side-effect ledgers, stable operation IDs, UNKNOWN states and provider reconciliation before retry. These sources are design/falsification pressure only.

K27 L0 URL-SHA coordinates: dual-write `(7,21,7)`; PlanFence `(8,24,19)`; PCAA `(17,9,9)`; aiagents retry-write discussion `(26,1,3)`; LLMDevs ambiguous-write discussion `(12,24,11)`. `K27Coordinate != Identity != Truth != Currentness != Authority`.

Direct task-specific Google Scholar retrieval produced no stable Scholar-native result: `GOOGLE_SCHOLAR_DIRECT_GAP`.

## Authority ceiling
D0 donor/reference only. No provider call, external sink effect, production DB migration, TECC verification, credential/device/network effect, merge/deploy, canonical promotion, native/private Transformer KV access, or Gate10 is claimed.

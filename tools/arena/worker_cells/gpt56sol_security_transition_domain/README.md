# Security Transition Domain Compiler — D0

## Objective

Rebase two current, consequence-distinct AuraOS artifacts with a third security law:

1. **AGENT_13 / PR #839**, current head `1a66ff9162abd69dc0223842e672f38f271a686f`: generation movement is classified by consequence and only the dependency-closed cone is reproved.
2. **GPT56SOL / PR #845**, current head `423a437a10e8252130cc1e74f0c2693c80284c34`: local semantic exactness and external authentication are noncompensatory, and composable parents require an exact cross-plane binding.
3. **2026-09-08 transition-domain campaign**: signed/newer/positive-looking values do not establish currentness unless the value domain, causal order, and lifecycle transition are exact.

PR #843 is not an active parent because it is currently marked `STALE / REPROVE REQUIRED`; it remains provenance pressure only.

## Keeper

```text
LocalTransitionExact =
    GenerationCurrent
  ∧ SemanticDomainCurrent
  ∧ SemanticProjectionCurrent
  ∧ CrossPlaneBindingCurrent
  ∧ ValueDomainValid
  ∧ CausalOrderValid
  ∧ LifecycleTransitionValid
  ∧ EvidenceCurrent
  ∧ Reproducible

LocalTransitionExact
  -> ExternalAuthenticationComplete
  -> AuthorityCeilingIntact
  -> ELIGIBLE_FOR_FRESH_READJUDICATION
```

Any local failure suppresses external-auth optimization and returns `REPROVE_LOCAL_FIRST`. Changed semantic dimensions are expanded only through their deterministic descendant cone.

## Typed transition laws

- `SignedValue != TypedDomainValidValue`
- `PositiveComparisonPass != FinitePositiveDuration`
- `AuthenticatedTimestampTuple != CausallyOrderedEvidence`
- `NewerReceipt != LawfulLifecycleTransition`
- `COMPLETED -> retryable state` is forbidden within one durable attempt.
- Python `bool` is not accepted as an integer identity/time/count.
- Context cannot compensate for a failed hard security axis.

## Empirical source of the third leg

The detector family produced five narrow repair children: #940 (terminal lifecycle), #941 and #942 (finite durations), #943 (causal time order), and #944 (exact millisecond domains). Each repair has a dedicated focused hosted PASS. Frozen parent-generation hash workflows are not counted as semantic failures when a child intentionally changes those bytes.

## Campaign

`campaign.py` is stdlib-only and deterministic:

- exhaustive `3^13 = 1,594,323` transition-domain membrane states;
- all 24 strict orderings of observation / issuance / effect-time / expiry;
- 1,000,000 random IEEE-754 bit patterns;
- exhaustive lifecycle sequences through length 7.

It requires exactly 243 valid contextual variants, zero hard-invalid repairs, one lawful causal ordering, zero non-finite admissions under the fixed duration domain, and zero post-completion retries.

## Authority ceiling

D0 defensive compiler only. It schedules local reproof and external readjudication; it does not authenticate providers, run third-party targets, create source truth, merge/deploy, mutate host processes, grant effect authority, or Gate10.

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

Any local failure suppresses external-auth optimization and returns `REPROVE_LOCAL_FIRST`. The reproof seed is the union of caller-declared changes and all observed failed local axes; that union is then expanded only through the deterministic descendant cone. A caller therefore cannot hide a failed invariant by supplying a narrower change list.

## Typed transition laws

- `SignedValue != TypedDomainValidValue`
- `PositiveComparisonPass != FinitePositiveDuration`
- `AuthenticatedTimestampTuple != CausallyOrderedEvidence`
- `NewerReceipt != LawfulLifecycleTransition`
- `COMPLETED -> retryable state` is forbidden within one durable attempt.
- Python `bool` is not accepted as an integer identity/time/count.
- Float-conversion overflow is a typed domain rejection, not an uncontrolled exception surface.
- Context cannot compensate for a failed hard security axis.

## Empirical source of the third leg

The detector family produced five narrow repair children: #940 (terminal lifecycle), #941 and #942 (finite durations), #943 (causal time order), and #944 (exact millisecond domains). Each repair has a dedicated focused hosted PASS. Frozen parent-generation hash workflows are not counted as semantic failures when a child intentionally changes those bytes.

## Campaign

`campaign.py` is stdlib-only and deterministic. It separates conceptual search geometry from implementation-facing proof:

- conceptual `3^13 = 1,594,323` lattice, with an 8-hard/5-context membrane retained as falsification geometry only;
- actual implementation truth table across all `2^11 = 2,048` evidence states: exactly one all-green state may be eligible and no unsafe state may be eligible;
- `9 × 2^9 = 4,608` failed-local-axis × declared-change-subset cases: every observed failed axis must remain in the compiled reproof cone;
- all 24 strict orderings of observation / issuance / effect-time / expiry;
- 1,000,000 random IEEE-754 bit patterns;
- exhaustive lifecycle sequences through length 7.

Current deterministic keeper results:

- 13D contextual variants: 243; conceptual hard-invalid repairs: 0;
- evidence truth table: 2,048 states, exactly 1 eligible, 0 unsafe eligible;
- reproof-union campaign: 4,608 cases, 0 misses;
- temporal orderings: legacy-shaped predicate accepts 4, only 1 is lawful, fixed predicate accepts 1;
- IEEE-754: positivity-only admits 498 non-finite values, finite-positive domain admits 0;
- lifecycle: legacy permits 2,778 post-completion retry sequences through length 7, fixed transition law permits 0;
- campaign root: `07805a91bf3d9dce038d41cabad879ff43b685412a1922e94959f5b5e4239bce`.

## Authority ceiling

D0 defensive compiler only. It schedules local reproof and external readjudication; it does not authenticate providers, run third-party targets, create source truth, merge/deploy, mutate host processes, grant effect authority, or Gate10.

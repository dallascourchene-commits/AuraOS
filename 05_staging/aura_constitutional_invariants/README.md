# Aura Executable Constitutional Invariant Checker — O6 D0

A bounded T2 structural/symbolic checker for the highest-value cross-project Aura invariants. It is not a theorem prover, source of truth, currentness owner, effect authority, or Gate10 actor.

## Exact two rebase parents
1. Ambiguity Escalation / Precision Budget Controller V1 O3 — Drive `1s0wStpFLBiwPd_tkjnIrY3-b7mRK9JF7EF9c6lmxhSI`.
2. Federal Act 0001 — Drive `1mPYOYJAsUmcuQ1ng-xpgOueXUEwT7vMMfZ7IgHNPLbw`.

## Checked laws
1. Evidence domain A cannot pay domain B.
2. Projection cannot widen owner/effect authority.
3. Provider-only movement cannot mint semantic movement.
4. Supersession graphs fail closed on cycles.
5. Cold/retired work cannot self-wake without a matching declared invalidator.
6. Cross-jurisdiction transfer cannot widen authority and destination authority requires destination-local revalidation.
7. Gate10 crossings require a HUMAN actor.
8. Incomplete dependency coverage cannot claim selective revalidation; local wider validation stays nonauthorizing, while owner/physical revalidation requires owner authority or HOLD.

## Integration fixtures
The suite includes normalized fixtures corresponding to the current SourceCursor3D (#798), lifecycle/supersession (#800), Cross-City Bridge ABI (#802), and PR311 G1 source-security boundaries.

## Claim ceiling
D0 structural verifier only. Passing this checker is necessary evidence for these encoded invariants, not proof of whole-system correctness or authorization for any effect.
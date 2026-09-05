# Semantic-Domain-Bound Evidence Reproof Bridge — O4 prototype

## Objective

Prevent scoped proof reuse from crossing an unacknowledged owner-generation, owner-projection, or semantic-domain change. Convert those changes into exact invalidation seeds, then use dependency closure so only consequence-bearing descendants reopen.

## Rebase parents

- AGENT_12 / PR #838: dependency-scoped AirLLM security reproof over a fixed canonical graph; unaffected exact witnesses survive only outside the reproof cone.
- AGENT_08 / PR #831 O2R3: current owner contracts must be replayed exactly and proof-time/current projection roots must match; semantic replay is not external source authentication.

O3R2 Evidence-Slice DAG is the predecessor control surface, not counted as a fresh foreign parent.

## Keeper laws

`OwnerGenerationDrift | OwnerProjectionDrift | SemanticDomainDrift -> ExactInvalidationSeed`.

`ExactInvalidationSeed -> DependencyClosedDescendantsToRecompute`.

`ReusableEvidence => OutsideReproofCone AND ExactAdmittedWitness AND ExactGraph AND ExactOwnerGeneration AND ExactProjectionRoot AND ExactSemanticDomainRoot AND ExactDependencyBinding AND D0`.

`ExternalReceiptRoot -> opaque upstream proof obligation`. This bridge hashes/binds it but does not authenticate it.

`ProviderObserved != ProviderAttested != SemanticTruth != EffectAuthority`.

## Why this matters

The F27 conformance replay contains boundary-focused cases where different numeric semantics can make opposite admission decisions over the same apparent inputs. A proof-reuse scheduler must therefore bind the owning semantic domain, not only a self-consistent result digest. Domain drift becomes a reproof trigger instead of silently surviving as “current” evidence.

## Authority ceiling

D0 control-plane prototype only. No external/provider truth, hosted PASS, model execution, performance/energy claim, production deployment, merge authority, effect authority, private/native transformer KV, canonical promotion, or Gate10.

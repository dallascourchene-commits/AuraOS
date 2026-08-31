# Collision-Safe Rebase / Addendum SOP V1

Status: D0 / nonpromoting / reusable coordination contract.

## Purpose

Preserve valid cognition when two agents converge on the same consequence seam without creating duplicate owners, overwriting stronger current work, or discarding a useful residual.

The default response to collision is **rebase + typed addendum**, not overwrite and not silent abandonment.

## Laws

- `Collision != ContributionLoss`.
- `OwnerSupersession != CognitionInvalidation`.
- `ValidHistoricalContribution != CurrentOwner`.
- `DuplicateSemanticMass => ZeroSiblingCredit`.
- `CurrentOwnerGenerationMustBeBoundBeforeRebase`.
- `UniqueResidual + CurrentOwner + ExactEvidence -> AddendumCandidate`.
- `RebaseAddendum != SemanticAuthority != EffectAuthority`.
- `CODEMAPOnlyDrift != NewSemanticGeneration`.
- `ProofTriggerOrRetry != NewSemanticGeneration`.
- `CollisionResolutionMustPreserveNegativeKnowledgeAndReopenTriggers`.

## Procedure

1. **Freeze the contribution before rebasing.** Record its semantic digest, bounded claims, evidence references, invalidators, claim ceiling and source generation.
2. **Resolve the live owner.** Search the repository/Arena/Drive for the current semantic owner and exact generation. If owner currentness is unresolved, HOLD rather than guessing.
3. **Quotient the overlap.** Partition candidate claims into already-owned overlap and a consequence-distinct residual. Do not count duplicate claims twice merely because independently derived.
4. **Classify.**
   - exact/complete semantic duplicate -> retain as lineage/independent derivation, zero sibling credit;
   - overlap + unique residual -> rebase onto owner and create an addendum candidate;
   - no meaningful overlap -> separate owner candidate, still requiring normal proof;
   - stale/unknown owner -> hold and reopen only owner-currentness cone.
5. **Rebase without erasure.** Consume the current owner contract rather than copying/reimplementing it. Preserve the candidate's provenance as an addendum artifact.
6. **Revalidate the residual.** Adversarially test only the unique residual plus its integration with the owner. A prior local pass cannot be laundered through a changed owner generation.
7. **Persist reusable cognition.** Append exact owner/generation, contribution digest, overlap, unique residual, negative knowledge, evidence rank, claim ceiling, K27/external coordinates and reopen triggers to the relevant Arena/HyperDrive/HyperScale surfaces.
8. **Grant no automatic authority.** An addendum is cognition/provenance, not execution, semantic, deployment, spend or effect authority.
9. **Award successor credit only to earned consequence.** Duplicate derivations, retries, proof triggers, CODEMAP drift, reformatting and replica evidence get zero new semantic sibling credit.
10. **Reopen the minimum affected cone.** If the owner later changes, invalidate only hard-dependent addenda. Preserve still-current source evidence and orthogonal residuals.

## First conformance example: AirLLM / GLM-5.3 Gemini contribution

The Gemini contribution proposed three useful ideas: a hard `trust_remote_code=False` loader, a per-expert repacker, and a top-k I/O derby. Live collision resolution shows:

- the AirLLM hard-false security seam is already owned by PR #311;
- real GLM-5.3 per-expert/source-bound paging is already owned by the AWJ032 pager lineage rather than a new generic repacker;
- PR #408 already owns the W4 physical-I/O counter reducer and explicitly separates byte avoidance from latency overlap.

Therefore the loader and repacker proposals receive **no duplicate owner**. Their derivation is retained as lineage. The useful residual is the Gemini mock's static payload projection:

`NominalExpertPayloadReduction = 1 - SelectedExpertPayloadBytes / CandidateExpertPayloadBytes`.

For equal-size expert payloads with top-2 of 8, the analytical value is `1 - 2/8 = 0.75`.

That value is an **analytical fixture only**. It may be used to challenge/account the PR #408 reducer, but it does not prove observed NVMe bytes, read amplification, TTFT, tokens/s, SSD wear, energy, cache effectiveness or prefetch benefit. In particular:

`NominalTopKPayloadReduction != ObservedPhysicalIOAvoidance != LatencyHidden != EndToEndPerformance`.

Shared/non-expert tensors, scale companions, headers, filesystem/page cache behavior, range granularity, prefetch misses, queueing and overlap remain independent terms. Host performance credit requires owner-host counters and the existing PR #408 physical-I/O attestation boundary.

## Crystalline / HyperScale guidance

- W0: deterministic owner/currentness baseline.
- W2 Antiprism: owner/generation/claim/evidence substitution attacks.
- W3 Toroid: collision -> rebase -> reproof -> typed reopen.
- W4 Butterfly: preserve independent source/owner/residual/proof/effect leaves.
- W5 Diamond: candidate + current owner -> challenge -> minimal addendum.
- W6: only if independent concurrent implementations must reconcile.
- W7/W8: only when independent residuals/recovery semantics actually earn them.

HS1 is the default for one collision seam. Wider physical fanout is earned by independent residuals, not by the number of agents that happened to collide.

## K27 / persistent cognition boundary

K27 coordinates may locate the owner, contribution, external source or reopen trigger. They do not merge semantic identities or grant proof/authority. Keep exact source/owner generation as identity and retain:

`CoordinateMemory != TransformerKVCache != SemanticResponseCache`.

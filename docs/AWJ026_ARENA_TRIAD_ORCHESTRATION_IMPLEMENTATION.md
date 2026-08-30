# AWJ-026 — Arena Triad Orchestration Implementation

Status: implementation branch / nonpromoting / no merge authority

## Purpose

Add the smallest provider-neutral orchestration layer needed to let AuraOS compile an Arena work order into evidence-preserving Triadic model calls without creating another provider, Drive, authority, currentness, memory, or execution plane.

This layer sits above the existing Project-006 / PR #306 admitted DeepSeek egress. It must not call DeepSeek directly in production and must not replace `aura_llm_egress.ExternalLLM`.

## Current proven substrate

The live host already proved:

`Drive command -> persisted ingest -> dedup/currentness -> WorkCapsule admission -> Dispatcher/lease/fence -> ACK before provider effect -> ExternalLLM DeepSeek -> RESULT or typed ERROR -> terminal WAL -> consumed cursor -> outbound bus`

The existing C81 lattice already supports identity-distinct A+ Construct, B- Challenge, C0 Verify, reciprocal BASE_TRIAD synthesis, and FINAL dimensional rebase.

Therefore AWJ-026 should reuse those owners rather than build a second swarm runtime.

## Required orchestration modes

### INDEPENDENT_RECIPROCAL — default for verification/security/Gate-10

Per independent work cell:

1. A+ Construct from the same source-bound common WorkCapsule.
2. B- Challenge independently from the same source-bound common WorkCapsule.
3. C0 Verify independently from the same source-bound common WorkCapsule.
4. A-view BASE_TRIAD receives A/B/C leaves.
5. B-view BASE_TRIAD receives A/B/C leaves.
6. C-view BASE_TRIAD receives A/B/C leaves.
7. FINAL_DIMENSIONAL_REBASE receives the three reciprocal syntheses.

Seven provider effects per cell. First-pass independence is preserved.

### STAGGERED_EFFICIENT — only when independent first-pass views are not required

Per independent work cell:

`A Construct -> B Challenge(A) -> C Verify(A,B) -> A Rebase(B,C)`

Four provider effects per cell. This saves compute but is not equivalent evidence to the seven-call independent mode.

## HyperScale law

Parallelize independent work cells, not duplicate opinions. `worker_count != evidence_independence`.

Start with zero workers when exact closure already exists; one cell for one unresolved consequence; multiple cells only when the unresolved frontier is genuinely decomposable. Do not use 9/27/81 merely because the provider or C81 runtime can.

## Leaf-first persistence

Every provider leaf must be persisted before a dependent synthesis call is admitted. Each leaf gets:

- parent command ID;
- parent idempotency key;
- derived child idempotency key;
- Arena head/generation;
- cell ID;
- phase/role/sequence;
- provider/model/attempt metadata when observed;
- usage/cache/cost observations when observed;
- exact output body or content-addressed body reference;
- digest;
- source/currentness/authority bindings;
- residuals/dissent/reopen handles.

The final outbound RESULT must carry compact leaf refs/digests rather than concatenating all leaf bodies. This closes the observed ~6.5 KB final-result truncation without throwing away cognition.

## Provider/cache efficiency

The common WorkCapsule serialization should be byte-stable and precede the role-specific suffix. DeepSeek's context cache is prefix-based and automatic; keeping the source/currentness prefix stable lets later role/synthesis calls reuse cached input when the provider can match it.

Do not force a new direct HTTP client into AuraOS. Production leaf effects must flow through the existing canonical egress/admission path.

## Machine command separation

A human-readable work-order document is not the same thing as an executable Drive command. The compiler must emit an exact machine envelope accepted by Project-006, currently `AuraCommandEnvelopeV1-candidate`, with current Arena binding and host-owned effect admission.

Never infer execution from a work-order or queue file existing.

## Gemini

Expose AuraOS/Arena as one remote Streamable-HTTP MCP server, not a Gemini-specific second control plane. Use current MCP Tasks for long-running Arena runs. Gemini becomes another authenticated client that calls AuraOS tools and receives Aura task/run handles.

## ChatGPT endpoint wake

ChatGPT windows are endpoint workers, not schedulers. AuraOS may maintain an external wake/recommission broker that delivers a real new turn to an addressable ChatGPT endpoint when the product/runtime supports it; otherwise create/recommission a successor from the last SuccessorFrame. A sleeping chat cannot self-wake.

The 30/60-second check convention belongs only to the external AuraOS-side ChatGPT endpoint broker and is a latency policy, never execution authority.

## AR/VR

The spatial UI is a projection/control surface over the Arena event graph. It may show humans, ChatGPT/Gemini windows, DeepSeek workers, WorkCapsules, leases, receipts, Sub-Arenas, dependencies, currentness and work state. Voice/gesture actions compile into ordinary AuraOS commands and remain subject to the same authority/effect gates. UI presence never grants authority.

## Acceptance gates

1. stale Arena head refuses before any model/provider effect;
2. replay of a terminal command produces zero duplicate provider effects;
3. every child call has a unique deterministic idempotency key;
4. leaf artifact is durable before dependent synthesis;
5. final RESULT can be reconstructed from leaf refs without relying on a large bus payload;
6. independent mode proves A/B/C first-pass isolation;
7. staggered mode is explicitly marked non-independent;
8. max-call/concurrency/cost budgets fail closed;
9. no command may select credentials, endpoint, provider fallback, lease, fence or currentness;
10. all DeepSeek effects use canonical Project-006/ExternalLLM admission;
11. no implicit paid fallback;
12. `UNKNOWN cost != zero`;
13. source/mirror/identity/certification/lease/effect distinctions remain separate;
14. newer Arena head invalidates stale WorkCapsules and triggers rebase;
15. ChatGPT cannot self-wake in tests;
16. Gemini calls AuraOS through one MCP tool plane rather than spawning an independent truth/runtime plane;
17. AR/VR commands compile to the same typed AuraOS commands as CLI/MCP;
18. automatic work stops at Gate 10.

## OpenCode integration instruction

Do not rediscover the architecture. Inspect the current host/repo state, cherry-pick or otherwise preserve the exact PR #306 egress seam where appropriate, implement the provider-neutral scheduler around existing C81/Project-006 owners, run focused and adjacent regression rings, and return exact receipts/digests. Do not merge PR #307 or any AWJ-026 branch automatically.

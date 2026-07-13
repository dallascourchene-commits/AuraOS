# Aura Observatory ↔ Human Agent ↔ Learning Arena Handoff

## Four distinct surfaces

| Surface | Purpose |
|---|---|
| Civic Arena | Governed community coordination and decision support |
| Human Agent Arena | Ground, plan, stage, test, verify, and prepare work for human review |
| Aura Observatory | Explain how Aura parsed, routed, localized, and bounded an intention |
| Learning Arena / Crucible | Mine complete verified experiences and propose reviewable learning |

## End-to-end lineage

```text
ordinary human intention
  → Aura Observatory
  → bounded Human Agent task
  → governed execution
  → verifier evidence
  → OutcomeVector
  → ArenaExperience V3
  → Learning Arena / Crucible
  → TRAIN / VALIDATION / SHADOW
  → CRYSTALLIZATION_PROPOSED
  → VERIFIER_AND_HUMAN_REVIEW
```

## Observatory to Human Agent

Endpoint:

```text
POST /api/showcase/observatory/handoff/human
```

The adapter imports only bounded observable data:

- objective;
- exact localized files and symbols where present;
- source spans and source hashes where present;
- focused tests where present;
- six-slot intent packet;
- machine-route decision;
- compressed worker context;
- bounded topology counts and selected node IDs.

A new Observatory handoff clears stale showcase workflow evidence before framing the new
objective. It does not stage a diff, run a worker, mutate production, commit, push, open a
pull request, or merge.

## Observatory to Learning Arena

Endpoint:

```text
POST /api/showcase/observatory/handoff/learning
```

The resulting packet is deliberately pre-experience:

```yaml
status: AWAITING_VERIFIED_EXPERIENCE
eligible_for_crucible: false
```

It preserves intent lineage but cannot enter the Crucible dataset until a governed Arena
execution creates a complete `ArenaExperience` with verifier evidence and an
`OutcomeVector`.

## Learning Arena API

```text
GET  /api/showcase/learning/status
POST /api/showcase/learning/run
POST /api/showcase/learning/pause
POST /api/showcase/learning/resume
```

The showcase facade calls the real `ArenaCrucibleService`. It does not implement a second
learning engine.

A proposal cycle:

1. reads sanitized complete experience records;
2. pins each record to the current compiled grammar digest;
3. separates TRAIN, VALIDATION, and SHADOW records;
4. mines candidate empirical-uncertainty changes;
5. validates the candidate structurally and against independent evidence;
6. replays SHADOW alternatives and predictions;
7. stores only `CRYSTALLIZATION_PROPOSED` packets.

## Allowed learning surface

The Crucible may propose only:

```text
soft_weight_profile.empirical_uncertainty
```

It cannot change:

- hard guards;
- states or transitions;
- capabilities;
- risk classes;
- verifier or approval requirements;
- source code;
- active grammar manifests.

Every proposal terminates at:

```text
CRYSTALLIZATION_PROPOSED
→ VERIFIER_AND_HUMAN_REVIEW
```

## Egress policy used by downstream workers

Aura's external egress priority is:

```text
1. Fireworks AI
2. Direct DeepSeek API
3. Anthropic
4. Mistral
5. SambaNova
6. Groq
7. Cerebras
8. OpenRouter
9. GitHub Models
10. OpenAI
11. Gemini
```

Fireworks model roles:

```text
primary / premium / reasoner / coding
  accounts/fireworks/models/glm-5p2

cheap / budget / fast / flash / shadow / summarizer
  accounts/fireworks/models/deepseek-v4-flash
```

Direct DeepSeek fallback roles:

```text
default / cheap
  deepseek-v4-flash

premium / reasoner / coding
  deepseek-v4-pro
```

No provider receives authority to expand scope, bypass the verifier, or promote a Crucible
proposal.

## Authority invariants

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
visual_topology_patch_authority: false
learned_weight_patch_authority: false
crystallization_patch_authority: false
active_grammar_mutation: false
automatic_grammar_promotion: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
```

# Human Agent Arena — Six-Slot Manual-Free Guidance

## Purpose

The Human Agent Arena should teach people how to operate it from inside the workflow. A person should be able to ask:

- What can I do?
- What should I do next?
- Why is this action blocked?
- What evidence do we have?
- What does this gate mean?

The answer must come from the current guarded state, not from an LLM guessing about the interface.

## Gate grammar

Every Human Agent gate is projected through Aura's six-slot software grammar:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

For example, the `PLAN` gate is represented as:

```text
DIR: bounded_change_space
ASP: pre_action
CLASS: arena_planning
SUBJ: human_guided_worker
VOICE: proposal_only
STEM: prepare
```

The slots teach both the human and an optional model:

- **DIR** — where or toward what domain the step operates;
- **ASP** — the lifecycle state, timing, or duration;
- **CLASS** — the kind of work permitted;
- **SUBJ** — the actor or authority permitted to act;
- **VOICE** — advisory, measured, proposed, staged, or human-authorized;
- **STEM** — the core operation.

## Guidance packet

`aura_human_agent_guidance.py` builds a machine-readable packet from the real guarded WFST projection:

```text
current gate
+ gate purpose and rules
+ six-slot gate packet
+ admitted transitions
+ exact rank vectors
+ required and produced evidence
+ requested capabilities
+ blocked transitions
+ failed hard guards
+ missing evidence and remediation
+ AI may / may-not instructions
```

The guide may explain, compare admitted options, identify missing evidence, and suggest the safest admitted next step.

It may not:

- grant capabilities;
- bypass hard guards;
- invent unavailable actions;
- treat a rank as model confidence;
- mutate production;
- commit;
- push;
- merge.

## Deterministic help today, optional LLM later

The showcase answers common onboarding questions deterministically through:

```text
GET  /api/human-agent/guide
POST /api/human-agent/guide/ask
```

This makes the demo reliable without a model or network connection.

A future local LLM may receive the same guidance packet as its directional context. The model can make the explanation conversational, adapt it to the user's experience level, and ask clarifying questions, but it must remain downstream of the guarded state projection.

The correct order is:

```text
hard guards
→ admitted state-local transitions
→ exact WFST ranking
→ six-slot teaching packet
→ deterministic or model-assisted explanation
→ human choice
```

The incorrect order is:

```text
LLM guess
→ fabricated option
→ attempted action
```

## Showcase use

After opening the Civic-to-Coding handoff:

1. Read the current six-slot gate packet.
2. Select **What can I do?** to list admitted actions.
3. Select **What should I do next?** to explain the safest admitted transition.
4. Select **Why is it blocked?** to expose failed guards and missing evidence.
5. Select **Explain this gate** to translate the six slots into plain language.
6. Run the chosen guarded action.
7. Observe the guide update automatically for the new phase.

This allows a first-time user to learn the workflow by using it instead of reading a separate manual.

## Authority invariant

The guidance layer is educational and advisory only:

```text
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

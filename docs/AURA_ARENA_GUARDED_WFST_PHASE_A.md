# Aura Arena Guarded-WFST Fabric — Phase A

Status: `RESEARCH_PROTOTYPE`

Phase A adds a shared, stdlib-first Arena routing substrate. It does **not** add the
background crystallization Crucible and it does not automatically promote learned
weights or grammar changes.

## Core rule

```text
hard guards → admissible transitions → deterministic ranking → capability binding
```

A failed guard removes a transition before ranking. Cost, latency, semantic fit,
VSA similarity, user preference, or historical success can never compensate for a
failed guard.

## Three separate layers

1. The six-slot morphology keeps the canonical order
   `DIR → ASP → CLASS → SUBJ → VOICE → STEM`.
2. The machine routing frame carries intent, artifact, action, scope, risk,
   grounding, tests, quality, cost, route, and verifier state.
3. The Arena state records workflow position such as `FRAME`, `PROVE`, or
   `DECIDE`.

These layers cooperate but are not interchangeable.

## Added components

- `aura_arena_wfst_types.py` — typed manifest, transition, guard, and rank contracts.
- `aura_arena_wfst_compiler.py` — deterministic manifest validation and compilation.
- `aura_arena_wfst_registry.py` — one registry for compiled Arena grammars.
- `aura_arena_wfst_runtime.py` — state-local guard evaluation and ranking.
- `aura_capability_binding.py` — adapter over existing tools, affordances, lanes,
  and plugins. It is not a second capability registry.
- `aura_arena_state_packet.py` — advisory J1 Arena continuity packet; J0 remains
  parseable through the existing JSpace codec.
- `aura_human_agent_wfst_adapter.py` — composition adapter over the existing
  `HumanAgentWorkflow` API.
- `aura_arena_wfst_cli.py` — standalone inspection and validation commands.

## Initial grammars

- `.aura/arena_routes/human_agent.v1.json`
- `.aura/arena_routes/meta.v1.json`

The Human Agent grammar mirrors the current actions:

```text
FRAME  → set_objective
GROUND → ground_context
PLAN   → prepare_capsule
ACT    → stage_patch
PROVE  → run_tests | verify_patch
DECIDE → check_hotswap | human_review | export_handoff
```

The Meta grammar provides state-preserving help, status, what-next, why-blocked,
show-evidence, and cancel transitions. Meta transitions are self-loops and cannot
advance the workflow.

## Runtime behavior

For each request the runtime:

1. loads only outgoing transitions from the active state;
2. adds reusable Meta transitions;
3. resolves exact symbols and state-local aliases;
4. evaluates all named hard guards;
5. moves failed transitions to the blocked projection;
6. resolves requested capabilities through existing registries;
7. lexicographically ranks only admitted transitions;
8. emits recommended, available, blocked, and selected projections;
9. emits a J1 continuity packet;
10. leaves execution to the existing workflow/tool/lease/sandbox/verifier systems.

Unknown guards, capabilities, states, and grammar constructs fail closed.

## CLI

```bash
python -m aura_arena_wfst_cli compile \
  --manifest .aura/arena_routes/human_agent.v1.json

python -m aura_arena_wfst_cli project-human \
  --state PROVE \
  --input "run tests" \
  --evidence-json '{"test_targets":["tests/test_example.py"]}'

python -m aura_arena_wfst_cli experience-status
```

## Authority

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
jspace_patch_authority: false
learned_weight_patch_authority: false
crystallization_patch_authority: false
automatic_grammar_promotion: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

The FST remains an admission grammar, not a sandbox.

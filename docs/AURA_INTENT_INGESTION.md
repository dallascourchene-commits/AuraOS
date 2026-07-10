# Aura Intent Ingestion

## What This Is

Aura Intent Ingestion parses Aura-native Markdown intent documents (`.aura/intents/*.aura.md`) and compiles them into `IntentPacket`s that route through Aura's architecture.

## Intent Document Format

Files in `.aura/intents/` with the `.aura.md` extension. Each document may contain YAML frontmatter plus structured sections:

```markdown
---
aura_doc_type: refactor_intent
intent_id: my_task
created_by: human
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
---

[AURA_INTENT]
OBJECTIVE: Refactor Fireworks egress to support multiple providers.

[AURA_POLYSYNTHETIC_PACKET]
[OP:IMPROVE][DOMAIN:LLM_EGRESS][TARGET:EGRESS][ENV:PYTHON][CONSTRAINT:TOKEN_SPARING][OUTPUT:PATCH]

[AURA_LEXC_ROUTE]
DIR: +SYS
ASP: +SYS_ROUTE
CLASS: +POLY
SUBJ: +SHAPE:OCTA
VOICE: _VALIDATE
STEM: _MERGE

[AURA_CAPABILITIES]
USE: Context Crusher
USE: Agent Arena Bridge

[AURA_GATES]
GATE_1: Human approves objective.
GATE_2: Aura validates LEXC/FST route.
...

[AURA_HANDOFF]
agent: hermes
mode: pr

[AURA_TOKEN_BUDGET]
raw_estimate: 50000
aura_target: 5000
```

Unstructured Markdown is also accepted — the parser degrades gracefully and extracts an objective from the first line.

## Supported Sections

| Section | Purpose |
|---------|---------|
| `AURA_INTENT` | Objective and why |
| `AURA_CONTEXT` | Background context |
| `AURA_POLYSYNTHETIC_PACKET` | Pre-authored polysynthetic packet |
| `AURA_LEXC_ROUTE` | Six-slot LEXC route (DIR, ASP, CLASS, SUBJ, VOICE, STEM) |
| `AURA_CAPABILITIES` | Which Aura capabilities to use |
| `AURA_ROUTE_HINTS` | Routing frame hints (intent, action, scope, etc.) |
| `AURA_CONSTRAINTS` | Task constraints |
| `AURA_GATES` | Human checkpoint gates |
| `AURA_HANDOFF` | Agent handoff configuration |
| `AURA_ACCEPTANCE` | Acceptance criteria |
| `AURA_RISKS` | Known risks |
| `AURA_TOKEN_BUDGET` | Token budget targets |
| `AURA_MEMORY_FEEDBACK` | Memory/QDKT feedback instructions |

## IntentPacket Output

The `compile_intent_packet()` function returns a packet with:

- `objective` — extracted objective string
- `raw_objective_tokens_est` — char/4 estimate of raw objective
- `compressed_objective` — polysynthetic packet
- `compressed_tokens_est` — char/4 estimate of compressed
- `polysynthetic_packet` — the bracketed packet string
- `lexc_symbols` — parsed LEXC symbols
- `lexc_valid` — whether the six-slot route is valid
- `lexc_route_packet` — validated route packet
- `routing_frame` — intent/artifact/action/scope/risk/grounding/tests/quality/cost
- `route_decision` — route/reason/model/verifier_required/next_state
- `recommended_affordances` — from Affordance Directory
- `concept_workspace_summary` — from Concept Workspace
- `likely_files` — from CODEMAP
- `likely_symbols` — from CODEMAP
- `suggested_searches` — CODEMAP search commands
- `suggested_read_slices` — read-slice commands
- `dream_ranked_candidates` — DREAM-lite reranked candidates
- `qdkt_fast_path` — QDKT crystallized pattern if available
- `context_crush_summary` — Context Crusher result
- `st3gg_decision` — ST3GG egress decision
- `checkpoint_plan` — from AURA_GATES section
- `handoff_mode` — agent name
- `token_budget` — from AURA_TOKEN_BUDGET section
- `patch_authority` — `"exact_source_spans_and_hashes_only"`
- `vsa_patch_authority` — `false`

## API

```python
from aura_intent_ingestion import (
    parse_intent_document,
    compile_intent_packet,
    compress_intent_for_agent,
    route_intent_to_lexc,
    route_intent_to_fst,
    route_intent_to_affordances,
    route_intent_to_concept_workspace,
    intent_to_agent_handoff,
    write_intent_capsule,
)
```

## CLI

```powershell
python -m aura_agent_arena_cli ingest-intent --file .aura/intents/example.aura.md
python -m aura_agent_arena_cli validate-lexc-route --file .aura/intents/example.aura.md
python -m aura_agent_arena_cli prepare-native-handoff --intent-file .aura/intents/example.aura.md --agent hermes
```

## Safety

- Patch authority remains exact source spans and hashes only.
- LEXC validation is advisory — an invalid route blocks patching but does not authorize patches.
- DREAM-lite reranking is advisory and cannot override exact lookup.
- QDKT fast-path is advisory and does not fail if the DB is unavailable.

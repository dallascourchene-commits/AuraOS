# Aura Affordance Directory / Internal Capability Oracle

> **Intelligence Layer V1.2** — Tells Aura and coding agents which internal Aura tools should be reused before inventing generic solutions.

## Overview

The Affordance Directory is an Aura-native capability oracle. When a coding agent (or Aura itself) is about to plan or implement a change, it can ask the Affordance Directory: *"What internal Aura tools should I consider before implementing this?"*

The directory returns ranked, grounded affordance cards with:
- **when_to_use** / **when_not_to_use** guidance
- **implemented_by** (source files)
- **symbols** (key functions/classes)
- **tests** (test files)
- **safety** constraints
- **prompt_card** (compact guidance for agents)

## Core Invariant

Affordance cards are **advisory only**. They tell agents what to consider — they are **never patch authority**. Patch authority remains exact source spans, hashes, CODEMAP facts, tests, boundary contracts, verifier gates, and human approval.

```
patch_authority: "exact_source_spans_and_hashes_only"
vsa_patch_authority: false
```

## Architecture

### Files

| File | Role |
|------|------|
| `aura_affordance_directory.py` | Core module — `AuraAffordance` dataclass, `find_affordances()`, `load_affordance_directory()` |
| `.aura/AFFORDANCE_MAP.json` | Optional seed map for additional affordances |
| `docs/AURA_AFFORDANCE_DIRECTORY.md` | This document |
| `tests/test_aura_affordance_directory.py` | Tests |

### Seeded Affordances (17)

| ID | Name |
|----|------|
| `aura.concept_workspace` | Concept Workspace Engine |
| `aura.node_inspector` | Node Intelligence Inspector |
| `aura.coding_arena.topology` | Coding Arena Topology |
| `aura.coding_arena.capsule_compiler` | Coding Arena Capsule Compiler |
| `aura.agent_arena.bridge` | Agent Arena Bridge |
| `aura.jspace.advisory_state` | JSpace Advisory State |
| `aura.fst.intent_routing` | FST Intent Routing |
| `aura.st3gg.egress` | ST3GG Egress Codec |
| `aura.context_crusher` | Context Crusher |
| `aura.understand_graph` | Understand Graph Bridge |
| `aura.emergent_potential.audit` | Emergent Potential Audit |
| `aura.dream.reranking` | DREAM Reranking |
| `aura.qdkt.memory` | QDKT Memory |
| `aura.llm_egress` | LLM Egress |
| `aura.tokenizer_guard` | Tokenizer Guard |
| `aura.patch_quality_gate` | Patch Quality Gate |
| `aura.architect_loop` | Architect Loop |
| `aura.research_arxiv_memory` | Research / ArXiv Memory |

Each affordance is grounded against CODEMAP at load time:
- **grounded** — all listed files/symbols/tests exist in CODEMAP
- **partial** — some exist
- **NEEDS_GROUNDING** — none found

## API

### `find_affordances(objective, target_files=None, target_symbols=None, selected_node_ids=None, current_workspace=None, repo_root=".", top_k=7)`

Returns a compact packet:
```json
{
  "objective": "...",
  "route_frame": { "intent": "...", "action": "...", ... },
  "recommended_affordances": [],
  "prompt_cards": [],
  "do_not_reinvent": [],
  "grounding": "grounded|partial|NEEDS_GROUNDING",
  "patch_authority": "exact_source_spans_and_hashes_only",
  "vsa_patch_authority": false
}
```

Ranking uses:
- Objective/tag match
- Target file overlap
- Symbol overlap
- Concept profile overlap from `aura_human_agent_concepts.py`
- Related affordance expansion
- Tests available
- Risk/safety penalty

### `explain_affordance(affordance_id)`

Returns full details for a single affordance.

### `affordance_prompt_cards(objective, top_k=7)`

Returns compact prompt card strings for the top matching affordances.

### `route_objective_to_affordances(objective)`

Same as `find_affordances` with a focus on the route frame for agent handoff.

## Integration Points

### Human Agent Arena Commands

| Command | Behavior |
|---------|----------|
| `what Aura tools can help here` | Returns ranked affordances for current selection/workspace |
| `show affordances for selected` | Same as above |
| `what am I not seeing` | Affordance Directory + Node Inspector + Concept Workspace |
| `before refactor, show internal tools` | Returns affordances before planning a refactor |
| `show native tools for this workspace` | Returns affordances for the current workspace |

### Agent Arena Bridge

The bridge exposes `aura_find_affordances` as Tool 11:
```python
bridge.aura_find_affordances(
    objective="refactor coding arena",
    target_files=["aura_coding_arena_3d.py"],
    top_k=5,
)
```

Also available via:
- **MCP**: `aura_find_affordances` tool
- **CLI**: `python -m aura_agent_arena_cli find-affordances --objective "..."`

### Node Inspector

`inspect_node()` calls `find_affordances()` for the selected node and includes `recommended_affordances` in the NodeIntelligencePacket.

### Concept Workspace

`_show_concept_workspace()` includes a `recommended_affordances` field in its response.

### Handoff Packets

`prepare agent task` includes top affordance cards and prompt cards in the `handoff_packet`.

## How Coding Agents Use Affordance Preflight

1. Agent receives a coding objective
2. Agent calls `aura_find_affordances` with the objective
3. Directory returns top 3–7 affordance cards with `when_to_use`, `when_not_to_use`, `implemented_by`, `safety`
4. Agent reads `do_not_reinvent` notes
5. Agent plans using existing Aura tools instead of inventing generic solutions
6. Affordance cards never become patch authority — they are advisory only

## Constraints

- **No external provider calls** — fully deterministic, stdlib-only
- **No heavy dependencies** — uses only `dataclasses`, `hashlib`, `json`, `pathlib`, `re`, `typing`
- **No production mutation** — read-only CODEMAP grounding
- **Top 3–7 only** — never expose every affordance

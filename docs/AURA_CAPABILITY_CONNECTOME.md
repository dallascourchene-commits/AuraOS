# Aura Capability Connectome

## What This Is

The **Capability Connectome** is a living graph of Aura's internal capabilities. Each node represents an Aura-native tool (from the Affordance Directory) with metadata about purpose, when to use, token savings role, truth boundary, future potentials, and risks. Edges connect related capabilities.

## Why It Exists

External agents (Hermes, Codex) and the Native Cockpit need to understand:
- **What** each capability is for
- **Why** it exists
- **When** to use it (and when not to)
- **How** it saves tokens
- **What** it connects to
- **What** future potentials it unlocks

## Capability Node Fields

| Field | Description |
|-------|-------------|
| `id` | Unique capability ID |
| `name` | Human-readable name |
| `purpose` | What it does |
| `when_to_use` | When to use it |
| `when_not_to_use` | When not to use it |
| `implemented_by` | Python modules |
| `symbols` | Key symbols/functions |
| `tests` | Test files |
| `docs` | Documentation files |
| `related_capabilities` | Connected capability IDs |
| `lexc_slots_if_known` | LEXC slots this capability maps to |
| `routing_frame_examples` | Example routing frame |
| `token_savings_role` | compression/localization/routing/verification/grounding/safety/advisory/context_reduction |
| `truth_boundary` | exact_source or advisory |
| `future_potentials` | What this capability could unlock |
| `risks` | Risk description |
| `patch_authority` | `"exact_source_spans_and_hashes_only"` |
| `vsa_patch_authority` | `false` |

## Token Savings Roles

| Role | Capabilities |
|------|-------------|
| `compression` | Context Crusher, ST3GG Egress, LLM Egress |
| `localization` | Concept Workspace, Node Inspector, AI Router, Understand Graph |
| `routing` | FST Intent Routing, JSpace Advisory State |
| `verification` | Patch Quality Gate, Tokenizer Guard |
| `grounding` | Agent Arena Bridge, Architect Loop, Coding Arena Topology |
| `safety` | Tokenizer Guard |
| `advisory` | DREAM Reranking, QDKT Memory, Emergent Potential Audit, Research/ArXiv |
| `context_reduction` | LLM Egress |

## API

```python
from aura_capability_connectome import (
    build_capability_connectome,
    find_capability_path,
    explain_capability,
    future_potentials_for_capability,
    token_savings_for_capability,
    capability_graph_packet,
)
```

## CLI

```powershell
python -m aura_agent_arena_cli capability-connectome
python -m aura_agent_arena_cli capability-path --objective "Refactor Fireworks egress"
```

## Safety

- The connectome is advisory/orientation only — never patch authority.
- `truth_boundary: "exact_source"` for grounding/verification capabilities.
- `truth_boundary: "advisory"` for routing/compression/advisory capabilities.
- Capabilities with `truth_boundary: "advisory"` cannot authorize patches.

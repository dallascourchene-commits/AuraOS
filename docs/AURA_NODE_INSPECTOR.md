# Aura Node Inspector

> **Intelligence Layer V1.2** — Produces grounded NodeIntelligencePackets for any node in the Human Agent Arena.

## Overview

The Node Inspector is the primary tool for understanding individual nodes in the arena topology. When you click a node or run `inspect selected`, the Node Inspector produces a `NodeIntelligencePacket` that answers:

- **Why is this node here?** (grounding path)
- **What source grounds it?** (file path, symbol, line range, digest, signature hash)
- **What does it connect to?** (contains, calls, called_by, neighbors, tests, docs, commands)
- **What tests/docs relate to it?**
- **What risks does it carry?** (missing tests, high fan-in, hub file, large file)
- **What next actions are available?**
- **What Aura tools can help?** (recommended affordances)

## Core Invariant

Node Intelligence is **advisory only**. Visual topology, JSpace, VSA, ST3GG, screenshots, summaries, fuzzy matches, CODEMAP projections, and ghost edges are advisory/orientation layers. **Patch authority remains exact source spans, hashes, CODEMAP facts, tests, boundary contracts, verifier gates, and human approval.**

```
patch_authority: "exact_source_spans_and_hashes_only"
vsa_patch_authority: false
```

## Grounded Node Ontology

The Node Inspector identifies one of five node origins:

| Origin | Description |
|--------|-------------|
| `exact_topology_node` | Already present in loaded arena topology. Highest visual confidence. |
| `codemap_projected_node` | Real file/symbol from `.aura/CODEMAP.json` projected into the current visual workspace. Visual projection only — the file/symbol itself is real (`entity_exists: true`). |
| `inferred_relationship_edge` | Relationship inferred from CODEMAP topology neighbors, naming, tests, docs, imports, or concept profiles. States inference source. |
| `ghost_hypothesis_edge` | Human-created hypothesis edge. Never patch authority. Not grounded unless later verified. |
| `unresolved_candidate` | Query/node/relationship could not be grounded. Shows `NEEDS_GROUNDING`. |

### CODEMAP-Projected Node Metadata

```json
{
  "node_origin": "codemap_projected_node",
  "projected_from_codemap": true,
  "grounding_source": ".aura/CODEMAP.json",
  "visual_projection_only": true,
  "entity_exists": true,
  "patch_authority": false
}
```

CODEMAP-projected nodes are **real CODEMAP-grounded entities**, not fake or synthetic nodes.

## Architecture

### File

| File | Role |
|------|------|
| `aura_node_inspector.py` | Core module — `NodeIntelligencePacket`, `inspect_node()`, `expand_node()`, `route_node_command()`, `why_is_node_here()` |
| `docs/AURA_NODE_INSPECTOR.md` | This document |
| `tests/test_aura_node_inspector.py` | Tests |

### NodeIntelligencePacket Fields

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | str | Unique node identifier |
| `node_origin` | str | One of the 5 origin types |
| `why_here` | str | Human-readable grounding path |
| `grounding_source` | str | `.aura/CODEMAP.json` or empty |
| `file_path` | str | Source file path |
| `symbol` | str | Symbol name if applicable |
| `kind` | str | file, function, class, method, test, doc |
| `line_range` | list[int] | [start_line, end_line] |
| `digest8` | str | 8-byte blake2b digest |
| `semantic_id` | str | CODEMAP semantic ID |
| `signature_hash` | str | CODEMAP signature hash |
| `entity_exists` | bool | True if file/symbol exists in CODEMAP |
| `patch_authority` | bool | Always False (advisory only) |
| `vsa_patch_authority` | bool | Always False |
| `relationships` | dict | contains, calls, called_by, neighbors, tests, docs, commands, related_concepts |
| `risk` | dict | missing_tests, high_fan_in, high_fan_out, missing_grounding, large_file, hub_file, severity |
| `jspace_state` | dict | Advisory JSpace state (advisory only) |
| `fst_route` | dict | FST route frame (advisory only) |
| `recommended_affordances` | list | Top Aura tools to consider |
| `next_actions` | list[str] | Safe next actions |
| `confidence` | float | 0.0–1.0 grounding confidence |
| `notes` | list[str] | Additional notes |

## API

### `inspect_node(node_id, repo_root=".", current_workspace=None, topology=None) -> NodeIntelligencePacket`

Resolves the node against current topology, then CODEMAP file paths and symbol_index. Identifies origin, pulls grounding facts, finds relationships, assesses risks, and produces `why_here` + safe next actions.

### `expand_node(node_id, expansion_mode="balanced", depth=1, repo_root=".", current_workspace=None, topology=None)`

Lazy expansion modes:

| Mode | Returns |
|------|---------|
| `children` | Contained functions/classes/methods |
| `callers` | Incoming callers/neighbor files |
| `callees` | Outgoing dependencies |
| `tests` | Related tests |
| `docs` | Related docs |
| `risks` | Verifier/risk facts |
| `full` | All available grounded rings |
| `balanced` | Readable mixed subset (default) |

Returns: `additional_nodes`, `additional_links`, `truth_packet`, `node_intelligence`, `visual_update`, `next_actions`.

Does **not** dump full source files. For exact source, returns file path, symbol, line range, digest/signature hash, and recommended `aura_read_slice` command.

### `route_node_command(command, selected_node_ids, current_workspace=None, repo_root=".")`

Maps broad commands into an FST/JSpace route frame:

```json
{
  "intent": "explain|localize|code_refactor|verify|repair|test_generate|research_rank",
  "artifact": "python_module|test_file|codemap|manifest|patch|documentation",
  "action": "inspect|create|modify|rank|verify|repair|rollback|promote",
  "scope": "symbol|file|capsule|subsystem|repo",
  "risk": "low|medium|high|live",
  "grounding": "none|file_exists|symbol_exists|tests_exist|manifest_owner|codemap_grounded|full",
  "tests": "none|existing|generated|required",
  "quality": "fast|balanced|accuracy_first|verifier_required",
  "cost": "no_model|local_first|cheap_first|premium_allowed|premium_required",
  "route": "LOCALIZE_FIRST|PLAN_ONLY|VERIFY_ONLY|TEST_GAP_FILL|BUILDER_PATCH|BLOCKED_WITH_REASON",
  "next_state": "..."
}
```

JSpace/FST remain **advisory only** and never become patch authority.

### `why_is_node_here(node_id, repo_root=".", current_workspace=None, topology=None)`

Explains the grounding path: matched alias, seed file, CODEMAP file path match, symbol match, topology neighbor, test relation, doc relation, human ghost edge, or unresolved candidate.

## Human Agent Arena Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `inspect selected` | `_cmd_inspect_selected` | Produce NodeIntelligencePacket |
| `explain selected` | `_cmd_inspect_selected` | Same as inspect |
| `why is this node here` | `_cmd_why_is_node_here` | Grounding path explanation |
| `show exact source for selected` | `_cmd_show_exact_source` | File/symbol/lines/hash (no full dump) |
| `expand selected` | `_cmd_expand_selected` | Lazy expansion (balanced) |
| `expand projected node` | `_cmd_expand_selected` | Expand a CODEMAP-projected node |
| `show callers` | `_cmd_show_callers` | Incoming callers |
| `show callees` | `_cmd_show_callees` | Outgoing dependencies |
| `show tests for selected` | `_cmd_show_tests_for_selected` | Related tests |
| `show docs for selected` | `_cmd_show_docs_for_selected` | Related docs |
| `show risks` | `_cmd_show_risks` | Risk assessment |
| `what would break if this changed` | `_cmd_what_would_break` | Impact analysis |
| `focus selected` | `_cmd_focus_selected` | Hide all unselected |
| `collapse unselected` | `_cmd_collapse_unselected` | Show selected + neighbors only |

## Frontend Integration

The Node Inspector panel appears when a node is clicked or inspected. It shows:

- Node ID
- Origin badge (color-coded)
- File/symbol
- Line range
- Digest/signature hash
- `why_here` explanation
- Relationship counts
- Risk badges
- Recommended Aura tools
- Next action buttons

### Click Behavior

| Action | Behavior |
|--------|----------|
| Single-click | Select + auto-inspect |
| Double-click | Inspect + expand balanced |
| Shift-click | Focus selected |
| Alt-click | Collapse unrelated nodes |

## Constraints

- **No external provider calls** — fully deterministic, stdlib-only
- **No heavy dependencies** — uses only `dataclasses`, `hashlib`, `json`, `pathlib`, `re`, `typing`
- **No production mutation** — read-only CODEMAP inspection
- **No full source dumps** — returns file path, symbol, line range, hash, and read-slice command

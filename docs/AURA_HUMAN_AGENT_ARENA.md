# Aura Human Agent Arena

## Three-Surface Model

Aura now has three additive, non-overlapping surfaces. None replaces the others.

| Surface | Role | Who Drives | Production Mutation? |
|---------|------|-----------|---------------------|
| **CLI / 3D Coding Arena** (`aura_coding_arena_server.py`, `aura_coding_arena_3d.py`) | Automatic/internal topology selection, capsule compilation, route simulation | Aura internals / human click | No (read-only topology + advisory capsules) |
| **Agent Arena Bridge** (`aura_agent_arena_bridge.py`, `aura_agent_arena_cli.py`) | Machine-agent interface — external coding agents drive through Aura | External agents (Codex, Cursor, OpenHands, Fireworks workers) | No (patches staged + verified only) |
| **Human Agent Arena** (`aura_human_agent_arena.py`, `aura_human_agent_arena_server.py`) | Collaborative human/Aura/agent command center — Jarvis-style topology cockpit | Human (type or speak) | No (ghost edges, diagnostics, prepared handoff only) |

The existing CLI Coding Arena remains **automatic/internal**. The Agent Arena Bridge remains the **machine-agent interface**. The Human Agent Arena is the **collaborative human/Aura/agent command center**.

## What Problem This Solves

The Human Agent Arena gives a human operator a Jarvis-style cockpit to:

- **Type or speak commands** to manipulate the visible code topology
- **Isolate micro-arenas** around selected nodes
- **Ask diagnostics** (wiring faults, missing tests, high fan-in/out)
- **Create ghost/hypothesis edges** without writing code
- **Prepare an agent task** and hand it off to the existing Agent Arena Bridge

It is a **third additive surface** — it does not replace, rename, or break the CLI Coding Arena, the 3D Coding Arena, or the Agent Arena Bridge.

## Quickstart

```bash
# Run the Human Agent Arena server locally (stdlib HTTP, no new dependencies)
python aura_human_agent_arena_server.py --demo

# Or with the real CODEMAP topology:
python aura_human_agent_arena_server.py --repo-root .

# Then open:
# http://127.0.0.1:8090
```

No model/provider APIs are called. No WebSockets are used. The frontend polls `/api/human-agent/state` every 800 ms.

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/api/human-agent/state` | Return current live state + topology |
| `GET` | `/api/human-agent/events?since=N` | Return events since index N |
| `POST` | `/api/human-agent/command` | Route a command and return result |
| `GET` | `/api/human-agent/topology` | Return the underlying read-only topology |

### Command Endpoint

```json
// Request
{
  "command": "show ST3GG",
  "selected_node_ids": ["aura_arena_st3gg_codec.py::encode_arena_capsule_for_egress"],
  "mode": "explore"
}

// Response
{
  "ok": true,
  "answer": "Highlighted 3 node(s) matching ST3GG.",
  "visual_update": {
    "highlighted_node_ids": ["..."],
    "hidden_node_ids": ["..."],
    "selected_node_ids": ["..."],
    "ghost_edges": [],
    "labels": {"...": "ST3GG"},
    "ui_hints": ["st3gg_filter_active"]
  },
  "truth_packet": {
    "files": ["aura_arena_st3gg_codec.py"],
    "symbols": ["encode_arena_capsule_for_egress"],
    "line_ranges": [{"node_id": "...", "file_path": "...", "symbol": "...", "line_range": [10, 50]}],
    "tests": [],
    "source_hashes": [],
    "patch_authority": "exact_source_spans_and_hashes_only",
    "vsa_patch_authority": false,
    "grounding": "grounded"
  },
  "next_actions": ["isolate selected", "diagnose selection", "show dependencies", "prepare agent task"]
}
```

## Supported Commands

| Command | Behavior |
|---------|----------|
| `show ST3GG` | Filter/highlight nodes/files/symbols containing `ST3GG` or `st3gg` |
| `show JSpace` | Filter/highlight JSpace-related nodes |
| `show Agent Arena Bridge` | Filter/highlight `aura_agent_arena_*` nodes and docs |
| `show tests` | Highlight known test files connected to current selection |
| `show dependencies` | Show dependency neighbors of current selection |
| `isolate selected` | Isolate a micro-arena around the current selection |
| `expand depth 2` | Expand selection to depth 2 in the topology |
| `show unwired connections here` | Call read-only emergent potential audit (scoped to selection if possible); MVP fallback with `NEEDS_GROUNDING` if unavailable |
| `what if connect source to target` | Create a ghost edge only — no code written |
| `hypothesize connection` | Create a ghost edge only — no code written |
| `diagnose selection` | Run wiring fault diagnostics on current selection |
| `prepare agent task` | Call `AuraAgentArenaBridge.aura_prepare_arena` after building objective from command/selection; return plan phase hash, act capsules, grounding evidence, shadow findings, routing decisions, blockers/warnings |

## Safety Model

- **No production code is mutated** from voice or graph commands.
- **Ghost edges** are stored only in live state (`HumanAgentArenaState.ghost_edges`). They are never written to topology, files, or patch authority.
- **VSA, JSpace, ST3GG, screenshots, summaries, and fuzzy similarity are advisory only.** Patch authority is exact source spans, hashes, CODEMAP facts, tests, boundary contracts, verifier gates, and human approval.
- Every command response includes `patch_authority: "exact_source_spans_and_hashes_only"` and `vsa_patch_authority: false`.
- If exact truth is missing, the truth packet is marked `NEEDS_GROUNDING` rather than guessing.
- The Agent Arena Bridge is used **only** for prepared handoff (`prepare agent task`), never for direct mutation.
- No new dependencies are required. No WebSockets. No provider APIs.
- Broad hub file reads are not introduced — the Human Agent Arena reuses `load_arena_topology` from `aura_coding_arena_3d` read-only.

## Visual Update vs Truth Packet

Every command response separates `visual_update` from `truth_packet`:

- **`visual_update`**: highlighted nodes, hidden nodes, ghost edges, labels, UI hints. This is advisory/orientation only.
- **`truth_packet`**: exact files, symbols, line ranges where known, tests where known, source hashes if available, patch authority policy, `vsa_patch_authority: false`, and grounding status. This is authoritative.

## Live State Fields

```python
{
  "visible_node_ids": [...],
  "hidden_node_ids": [...],
  "selected_node_ids": [...],
  "active_filter": "st3gg",
  "micro_arena": {...},
  "ghost_edges": [...],
  "diagnostics": [...],
  "hypotheses": [...],
  "agent_tasks": [...],
  "human_notes": [...],
  "event_log": [...]
}
```

## AMD Hackathon Demo Script

1. **Open the arena:**
   ```bash
   python aura_human_agent_arena_server.py --demo
   # Open http://127.0.0.1:8090
   ```

2. **Say or type "show ST3GG":**
   - Graph prunes to ST3GG-related nodes
   - Truth packet shows exact files/symbols
   - Next actions appear as buttons

3. **Prune the graph:**
   - Click a node to select it
   - Type "isolate selected" — micro-arena isolates around selection
   - Non-matching nodes are hidden

4. **Ask "what happens if ST3GG connects to Agent Arena Bridge micro-context":**
   - Type: `what if ST3GG connects to Agent Arena Bridge`
   - A **ghost edge** (dashed purple line) appears
   - Truth packet says `NEEDS_GROUNDING` — no code written

5. **Draw ghost edge:**
   - Type: `hypothesize connection`
   - Ghost edge stored in live state only
   - Never treated as patch authority

6. **Run diagnose selection:**
   - Type: `diagnose selection` (or switch mode to `diagnose`)
   - Diagnostics panel shows wiring faults (missing tests, high fan-in, etc.)
   - Truth packet includes exact line ranges and test files

7. **Prepare agent task:**
   - Type: `prepare agent task` (or switch mode to `prepare`)
   - Agent Arena Bridge `aura_prepare_arena` is called
   - Truth packet shows plan phase hash, act capsules, grounding evidence, shadow findings, routing decisions, blockers/warnings
   - **No production files mutated** — handoff is ready for Agent Arena Bridge

8. **Show token savings / grounding:**
   - Truth packet shows exact files/symbols/line_ranges
   - Compare topology node count vs micro-arena node count
   - Show `vsa_patch_authority: false` and `patch_authority: exact_source_spans_and_hashes_only`

9. **Stop before production mutation:**
   - The demo ends here. No patches are staged. No files are written.
   - The prepared task can be handed to the Agent Arena Bridge for actual execution.

## Concept Workspace Engine (V1.1)

The V1.1 upgrade replaces simple keyword filtering with a real concept-workspace engine.
Commands like `show Agent Arena Bridge` or `show Coding Arena` now work even when those files
are not present in the projected visual topology (e.g. because they were outside the node limit).

### How it works

| Step | Detail |
|------|--------|
| **1. CODEMAP search** | Searches the full `.aura/CODEMAP.json` — `files`, `symbol_index`, `command_index`, topology `neighbor_files` |
| **2. Concept profiles** | 13 built-in profiles map human phrases to seed files, seed symbols, and related concepts |
| **3. Neighbor expansion** | Topology `neighbor_files` are expanded to depth 1 by default |
| **4. Synthetic nodes** | Files found in CODEMAP but not in the projected topology are synthesised as `ArenaNode`-compatible dicts tagged `projected_from_codemap: true`, `visual_only: true`, `patch_authority: false` |
| **5. Visual injection** | Synthetic nodes are injected into the live session (never persisted); displayed with a dashed purple badge ring in the canvas |
| **6. Truth packet** | The truth_packet carries exact CODEMAP file paths, symbols, line ranges (from projected nodes). Synthetic nodes appear only in the visual graph |

### Concept Profiles (13 built-in)

| Key | Display Name | Example Aliases |
|-----|-------------|----------------|
| `st3gg` | ST3GG | `st3gg`, `arena_st3gg`, `st3gg_egress` |
| `jspace` | JSpace | `jspace`, `j_space`, `jspace_codec` |
| `agent_arena_bridge` | Agent Arena Bridge | `agent arena`, `agent bridge`, `aura_prepare_arena` |
| `human_agent_arena` | Human Agent Arena | `human agent arena`, `jarvis`, `route_command` |
| `coding_arena` | Coding Arena | `coding arena`, `load_arena_topology`, `select_micro_arena` |
| `architect` | Architect | `architect`, `aura_architect_loop`, `ArchitectFusionLoop` |
| `dream` | DREAM | `dream`, `dream_engine`, `DreamCandidate` |
| `qdkt` | QDKT | `qdkt`, `get_qdkt` |
| `emergent_potential` | Emergent Potential | `emergent potential`, `audit_emergent_potential` |
| `context_crusher` | Context Crusher | `context crusher`, `apply_context_crush_to_prompt` |
| `llm_egress` | LLM Egress | `llm egress`, `aura_llm_egress` |
| `verifier` | Verifier | `verifier`, `patch_quality_gate` |
| `research_arxiv` | Research / ArXiv | `research`, `arxiv`, `ArXivForager` |

### New Commands

| Command | Behavior |
|---------|----------|
| `show Coding Arena` | Full concept workspace: files, symbols, tests, docs for Coding Arena |
| `show Agent Arena Bridge` | Searches CODEMAP — finds bridge files even if not in projected topology |
| `show all functions related to <concept>` | Returns function/symbol nodes in `functions` mode |
| `show everything connected to <concept>` | Full mode: files + symbols + neighbors + docs + tests |
| `refactor <concept>` / `I want to refactor the <concept>` | Concept workspace in prepare mode + 4 refactor next_actions |
| `export handoff packet` | Exports concept workspace + prepared tasks as JSON; optionally writes to `Aura_Memory/human_agent_arena/handoff_<id>.json` |

### Concept Workspace Summary Panel

After any concept command, a **Concept Workspace Summary Panel** appears in the UI with:
- Files count, symbols count, tests count, docs count, neighbors count
- CODEMAP-projected node count (real, visual projection only)
- Workspace action buttons: `show all functions`, `show neighbors`, `show tests`, `show docs`, `show agent handoff`, `prepare refactor plan`, `what Aura tools can help here`

### CODEMAP-Projected Nodes Visual Legend

| Style | Meaning |
|-------|---------|
| Dashed purple ring `⬤ ···` | CODEMAP-projected node (real CODEMAP-grounded entity, visual projection only) |
| Purple label prefix `[CODEMAP]` | Same node in label text |
| Normal filled dot | Existing projected topology node |

### Safety Invariants (unchanged)

- Synthetic nodes are **session-local only** — they are never written to CODEMAP, topology, or any file.
- The `truth_packet` remains authoritative: exact CODEMAP facts for projected nodes; `NEEDS_GROUNDING` for synthetic matches unless line ranges are available.
- `patch_authority: "exact_source_spans_and_hashes_only"` and `vsa_patch_authority: false` on every response.

### State Fields (new in V1.1)

```python
{
  "concept_workspace": {
    "concept": "Agent Arena Bridge",
    "profile_key": "agent_arena_bridge",
    "workspace_id": "a1b2c3d4",
    "files": ["aura_agent_arena_bridge.py", ...],
    "symbols": ["AuraAgentArenaBridge", ...],
    "docs": ["docs/AURA_AGENT_ARENA_BRIDGE.md"],
    "tests": ["tests/test_aura_agent_arena_bridge.py"],
    "commands": ["!show Agent Arena Bridge"],
    "neighbors": [...],
    "token_estimates": {...},
    "grounding": "grounded"
  },
  "prepared_handoff_packets": [
    {
      "objective": "...",
      "plan_phase_hash": "...",
      "workspace_id": "a1b2c3d4",
      "recommended_next_cli_commands": [...],
      "note": "..."
    }
  ]
}
```

## Files


| File | Purpose |
|------|---------|
| `aura_human_agent_arena.py` | Live state + deterministic command router |
| `aura_human_agent_arena_server.py` | Stdlib HTTP server with polling endpoints |
| `aura_human_agent_concepts.py` | Concept Workspace Engine — CODEMAP search, 13 concept profiles, `build_concept_workspace`, `resolve_node_ref` |
| `aura_node_inspector.py` | Node Intelligence — `NodeIntelligencePacket`, `inspect_node`, `expand_node`, `route_node_command` |
| `aura_affordance_directory.py` | Affordance Directory / Internal Capability Oracle |
| `aura_human_agent_arena/index.html` | Frontend HTML |
| `aura_human_agent_arena/main.js` | Frontend JS (graph, polling, command, mic, concept workspace, node inspector, layout controls) |
| `aura_human_agent_arena/arena.css` | Frontend CSS |
| `tests/test_aura_human_agent_arena.py` | Deterministic tests (existing) |
| `tests/test_aura_human_agent_concepts.py` | Concept Workspace Engine acceptance criteria tests |
| `tests/test_aura_node_inspector.py` | Node Intelligence tests |
| `tests/test_aura_affordance_directory.py` | Affordance Directory tests |
| `docs/AURA_HUMAN_AGENT_ARENA.md` | This document |
| `docs/AURA_NODE_INSPECTOR.md` | Node Inspector documentation |
| `docs/AURA_AFFORDANCE_DIRECTORY.md` | Affordance Directory documentation |


## Testing

```bash
# Run Human Agent Arena tests
python -m pytest tests/test_aura_human_agent_arena.py -v

# Run Node Inspector tests
python -m pytest tests/test_aura_node_inspector.py -v

# Run Affordance Directory tests
python -m pytest tests/test_aura_affordance_directory.py -v

# Run existing Coding Arena tests (must still pass)
python -m pytest tests/test_aura_coding_arena_3d.py -v

# Run all tests
python -m pytest tests/ -v
```

---

## Intelligence Layer V1.2

The Human Agent Arena now includes three integrated intelligence systems that work together as one coherent layer:

### 1. Grounded Node Ontology

Nodes in the Concept Workspace are now classified by origin:

| Origin | Description |
|--------|-------------|
| `exact_topology_node` | Present in loaded arena topology |
| `codemap_projected_node` | Real file/symbol from `.aura/CODEMAP.json` projected into the visual workspace |
| `inferred_relationship_edge` | Relationship inferred from CODEMAP neighbors, naming, tests, docs |
| `ghost_hypothesis_edge` | Human-created hypothesis edge — never patch authority |
| `unresolved_candidate` | Could not be grounded — shows `NEEDS_GROUNDING` |

CODEMAP-projected nodes are **real CODEMAP-grounded entities** (`entity_exists: true`), not fake or synthetic nodes. The projection is UI-only, but the file/symbol itself is real.

### 2. Node Intelligence (Node Inspector)

Clicking a node produces a `NodeIntelligencePacket` that answers:
- Why it is here (grounding path)
- What source grounds it (file, symbol, line range, digest, hash)
- What it connects to (contains, calls, called_by, neighbors, tests, docs)
- What risks it carries (missing tests, high fan-in, hub file, large file)
- What Aura tools can help (recommended affordances)
- What next actions are available

See [docs/AURA_NODE_INSPECTOR.md](AURA_NODE_INSPECTOR.md) for full details.

### 3. Affordance Directory / Internal Capability Oracle

Tells Aura and coding agents which existing internal Aura tools should be reused before inventing generic solutions. 17 seed affordances, grounded against CODEMAP, ranked by relevance.

See [docs/AURA_AFFORDANCE_DIRECTORY.md](AURA_AFFORDANCE_DIRECTORY.md) for full details.

### Three Surfaces Working Together

| Surface | Role | Key Commands |
|---------|------|-------------|
| **Concept Workspace** | Broad concept search across full CODEMAP | `show Coding Arena`, `show all functions related to Coding Arena`, `show ST3GG` |
| **Node Inspector** | Per-node intelligence and lazy expansion | `inspect selected`, `why is this node here`, `expand selected`, `show callers` |
| **Affordance Directory** | Internal capability oracle | `what Aura tools can help here`, `what am I not seeing`, `before refactor, show internal tools` |

### Example Commands

```
show Coding Arena
show all functions related to Coding Arena
show Agent Arena Bridge
why is this node here
what Aura tools can help here
what am I not seeing
expand selected
inspect selected
show callers
show callees
show tests for selected
show risks
what would break if this changed
prepare agent task
export handoff packet
before refactor, show internal tools
focus selected
collapse unselected
```

### Frontend Improvements (V1.2)

- **Layout controls**: spacing slider (1.0–6.0), zoom slider (0.4–8.0), label mode (selected/highlighted/all/off)
- **Reset View**, **Focus Selected**, **Collapse Unselected** buttons
- **Node Inspector panel**: origin badge, file/symbol/line range/digest/hash, why_here, relationship counts, risk badges, recommended affordances, next action buttons
- **Click behavior**: single-click = select + inspect, double-click = inspect + expand, shift-click = focus, alt-click = collapse
- **Label readability**: background boxes, zoom-based truncation, subsystem/file labels at low zoom, functions/classes at high zoom
- **`layoutSpread`**: adjustable node spacing (default 2.8) applied in projection

### Handoff Packets (V1.2)

`prepare agent task` now includes:
- `recommended_affordances` — top 5 Aura tools to consider
- `prompt_cards` — compact guidance for agents
- `recommended_next_cli_commands` — including `find-affordances`

`export handoff packet` writes to `Aura_Memory/human_agent_arena/handoff_<workspace_id>.json`.

### Core Invariant (Unchanged)

Visual topology, JSpace, VSA, ST3GG, screenshots, summaries, fuzzy matches, CODEMAP projections, and ghost edges are **advisory/orientation layers only**. Patch authority remains exact source spans, hashes, CODEMAP facts, tests, boundary contracts, verifier gates, and human approval.

```
patch_authority: "exact_source_spans_and_hashes_only"
vsa_patch_authority: false
```
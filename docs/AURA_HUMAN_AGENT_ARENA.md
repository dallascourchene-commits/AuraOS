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

## Files

| File | Purpose |
|------|---------|
| `aura_human_agent_arena.py` | Live state + deterministic command router |
| `aura_human_agent_arena_server.py` | Stdlib HTTP server with polling endpoints |
| `aura_human_agent_arena/index.html` | Frontend HTML |
| `aura_human_agent_arena/main.js` | Frontend JS (graph, polling, command, mic) |
| `aura_human_agent_arena/arena.css` | Frontend CSS |
| `tests/test_aura_human_agent_arena.py` | Deterministic tests |
| `docs/AURA_HUMAN_AGENT_ARENA.md` | This document |

## Testing

```bash
# Run Human Agent Arena tests
python -m pytest tests/test_aura_human_agent_arena.py -v

# Run existing Coding Arena tests (must still pass)
python -m pytest tests/test_aura_coding_arena_3d.py -v

# Run all tests
python -m pytest tests/ -v
```
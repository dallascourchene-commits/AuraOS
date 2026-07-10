# Aura Swarm + MCP Cockpit

## Swarm Plan

The Mesh/Swarm lane plans multi-agent execution across Hermes/Codex/Fireworks/local workers. **No worker executes automatically.** Human approval required before each handoff.

### Functions
- `build_swarm_plan(objective, agents)` — build multi-agent plan
- `assign_agent_roles(objective, agents)` — assign roles to agents
- `agent_lane_compatibility(agent)` — check lane compatibility
- `swarm_plan_to_agent_handoffs(swarm_plan)` — convert to individual handoff packets

### Supported Workers
| Worker | Type |
|--------|------|
| Hermes | External coding agent |
| Codex | External coding agent |
| Fireworks | Model worker |
| Local | Deterministic Aura lane |
| MCP Agent | MCP-capable agent |

## MCP Gateway

The MCP Gateway lane exposes cockpit operations as MCP-compatible tools.

### Functions
- `list_capability_lanes()` — list lanes as MCP tools
- `cockpit_mcp_tool_list()` — full MCP tool definitions
- `register_cockpit_mcp_tools()` — register with AuraMCPGateway

## CLI

```powershell
python -m aura_agent_arena_cli swarm-plan --objective "..." --agents hermes,codex
```

## Safety
- No worker executes automatically. Human approval required.
- Each worker receives only a compact capsule.
- Workers must return patches through Agent Arena staging.
- `patch_authority: "exact_source_spans_and_hashes_only"`

# Aura Capability Lanes

## What This Is

**Capability Lanes** are formal, cockpit-routable capability channels that connect Aura's existing underused architecture into the Native Cockpit as first-class routed lanes. Each lane is advisory/routing/planning unless it has exact source spans, hashes, tests, verifier gates, and human approval.

## 17 Seed Lanes

| Lane ID | Name | Token Savings Role | Advisory |
|---------|------|-------------------|----------|
| `music_coding_lane` | MUSIC Coding Arena | routing | ✅ |
| `mitosis_decomposition_lane` | Mitosis Decomposition | context_reduction | ✅ |
| `research_arxiv_lane` | Research / arXiv | localization | ✅ |
| `skillweaver_lane` | SkillWeaver Discovery | localization | ✅ |
| `mesh_swarm_lane` | Mesh / Multi-Agent Swarm | routing | ✅ |
| `mcp_gateway_lane` | MCP Gateway | advisory | ✅ |
| `plugin_registry_lane` | Plugin Registry | advisory | ✅ |
| `goap_planner_lane` | GOAP Planner | routing | ✅ |
| `live_architect_lane` | Live Architect Patch Lifecycle | verification | ✅ |
| `associative_core_lane` | Associative Core Recall | advisory | ✅ |
| `phase_capsule_lane` | Phase Capsule State | context_reduction | ✅ |
| `audit_staking_lane` | Audit / Memory Staking | safety | ✅ |
| `federation_lane` | Federation | advisory | ✅ |
| `empirical_lab_lane` | Empirical Software Lab | verification | ✅ |
| `resonant_test_oracle_lane` | Resonant Test Oracle | verification | ✅ |
| `symbolic_trace_memory_lane` | Symbolic Trace Memory | advisory | ✅ |
| `module_manifest_lane` | Module Manifest | localization | ✅ |

## CLI

```powershell
python -m aura_agent_arena_cli capability-lanes
python -m aura_agent_arena_cli route-lanes --objective "research this approach before refactor"
```

## Safety

- All lanes are advisory only — no lane can patch without exact source spans.
- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`

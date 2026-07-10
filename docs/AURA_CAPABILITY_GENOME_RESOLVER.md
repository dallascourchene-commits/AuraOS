# Aura Capability Genome Resolver

## What This Is

The Capability Genome Resolver composes Aura's existing substrate to answer: **what already exists for this objective?** before any new code is proposed. It is a facade/aggregator, not another registry.

## Sources Composed

1. CODEMAP files and symbol index
2. CODEMAP command index
3. Topology neighbors
4. Module Manifest
5. Affordance Directory
6. Capability Connectome
7. Capability Lane Registry
8. Plugin Registry
9. Concept Workspace
10. Node Inspector
11. Agent Arena Bridge tools

## Ranking Order

1. Exact requested file/symbol
2. Exact symbol/file keyword match
3. Callers/callees/import neighbors
4. Tests
5. Docs
6. Command exposure
7. Declared affordance implementation
8. Capability lane ownership
9. Plugin ownership
10. Semantic/VSA/DREAM as advisory tie-break only

## Output: CapabilityResolutionPacket

- `exact_matches` — files/symbols with CODEMAP grounding
- `related_functions` — keyword-matched functions with line ranges
- `existing_affordances` — from Affordance Directory
- `capability_lanes` — from Lane Registry
- `plugin_organs` — from Plugin Registry
- `agent_tools` — from Workbench Interface
- `commands` — from CODEMAP command index
- `tests` — test files covering matched symbols
- `reuse_plan` — what to reuse
- `do_not_reinvent` — explicit reuse guidance
- `missing_capabilities` — what's genuinely missing
- `read_slice_commands` — bounded read-slice commands
- `confidence` — 0.0 to 1.0
- `truth_boundary` — exact vs advisory distinction

## CLI

```powershell
python -m aura_agent_arena_cli resolve-capabilities --objective "sandboxed ephemeral application runtime"
python -m aura_agent_arena_cli resolve-capabilities --objective "..." --target-files aura_llm_egress.py --target-symbols AuraLexc
```

## Stabilization Status

```powershell
python -m aura_agent_arena_cli stabilization-status
```

Reports: git commit, CODEMAP health, LEXC validity, affordance grounding, capability lanes, workbench status, Cost Observatory availability, blocking findings, recommended next gate.

## Safety

- Never invents symbols — all matches have CODEMAP grounding
- Stale topology is explicitly marked
- Token budget enforced
- Secrets stripped
- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`

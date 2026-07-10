# Aura MUSIC + Mitosis Cockpit Integration

## MUSIC Coding Arena Lane

The MUSIC Coding Arena lane provides advisory ranking of candidate code routes and inverse-search coding topology. MUSIC output is **advisory only** — never patch from MUSIC alone.

### Functions
- `music_rank_cockpit_candidates(objective, candidates)` — rank candidates by MUSIC scoring
- `music_invert_code_route(objective, target_file)` — inverse-search coding topology

## Mitosis Decomposition Lane

The Mitosis lane splits large objectives into child act-capsules, reducing context by decomposition. Each child capsule includes: child_id, objective, parent_objective, target_files, target_symbols, required_evidence, suggested_tests, token_budget, workflow_gate_start, patch_authority, vsa_patch_authority.

### Functions
- `mitosis_split_objective(objective, max_children=5)` — split into child capsules
- `mitosis_to_phase_capsules(children)` — convert to phase capsules
- `mitosis_to_agent_act_capsules(children)` — convert to agent act capsules

## CLI

```powershell
python -m aura_agent_arena_cli music-rank --objective "Refactor routing"
python -m aura_agent_arena_cli mitosis-split --objective "Split this huge refactor into smaller PRs"
```

## Safety
- MUSIC output is advisory only. Never patch from MUSIC alone.
- Mitosis output is plan/capsule only. No direct code mutation.
- `patch_authority: "exact_source_spans_and_hashes_only"`

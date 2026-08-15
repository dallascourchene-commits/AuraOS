# Aura Source Anchors

**Version:** `AURA_SOURCE_ANCHOR_MAP_V1`  
**Generated from:** `.aura/CODEMAP.json` + `.aura/source_anchor_manifest.v1.json`  
**Authority:** navigation projection only; exact current source/tests/contracts remain authoritative.

> **Do not use line numbers or symbol-index display keys as durable identity.** CODEMAP `semantic_id` + `signature_hash` identify the selected symbol; `Lstart-Lend` is regenerated whenever navigation state is refreshed.

| Mechanism | Symbol | Current source span | Semantic identity | Signature | Why it matters |
|---|---|---|---|---|---|
| CODEMAP semantic symbol extraction | `_python_symbol_records` | [aura_codebase_navigator.py:L149-L189](../aura_codebase_navigator.py#L149-L189) | `aura_codebase_navigator.py#function:_python_symbol_records:6f1a917545f1ee1f` | `f28fd69c5857289f` | Regenerates semantic_id, signature_hash, and current source spans from AST. |
| CODEMAP incremental refresh | `refresh_index_for_paths` | [aura_codebase_navigator.py:L475-L530](../aura_codebase_navigator.py#L475-L530) | `aura_codebase_navigator.py#function:refresh_index_for_paths:30af08a11685d859` | `1045b2d21cf78d9b` | Reparses touched files and regenerates symbol identities and line ranges after writes. |
| Guarded WFST admission/runtime | `ArenaWFSTRuntime.route` | [aura_arena_wfst_runtime.py:L56-L172](../aura_arena_wfst_runtime.py#L56-L172) | `aura_arena_wfst_runtime.py#method:ArenaWFSTRuntime.route:f8226eb2633bed5c` | `f4d06789c5596872` | Evaluates hard guards, capability bindings, ranking, abstention, and bounded state packets. |
| Capability Connectome | `build_capability_connectome` | [aura_capability_connectome.py:L312-L375](../aura_capability_connectome.py#L312-L375) | `aura_capability_connectome.py#function:build_capability_connectome:18fb5f3bb4b701e8` | `09894f0b3dbc9c67` | Builds the capability graph and grounds implementation references against CODEMAP. |
| Capability path resolution | `find_capability_path` | [aura_capability_connectome.py:L378-L425](../aura_capability_connectome.py#L378-L425) | `aura_capability_connectome.py#function:find_capability_path:f65b05d9bd302f9d` | `5da750287b6d81d9` | Finds objective-relevant capability paths before reinvention. |
| Relational Synthesis | `compile_relational_shadow_capsule` | [aura_relational_synthesis.py:L1573-L1591](../aura_relational_synthesis.py#L1573-L1591) | `aura_relational_synthesis.py#function:compile_relational_shadow_capsule:8cd22eb187491ec8` | `1f547728a0bfda00` | Compiles exact evidence into a read-only relational synthesis capsule. |
| Relationship Atlas | `build_relationship_atlas` | [aura_relationship_atlas.py:L609-L1151](../aura_relationship_atlas.py#L609-L1151) | `aura_relationship_atlas.py#function:build_relationship_atlas:318f86e88f5df5af` | `893a1b4c719a042f` | Classifies explicit, overlapping, auxiliary, and candidate relationships without becoming source truth. |
| Selective Council V3 | `select_critic_lanes` | [aura_architect_council_v3.py:L36-L67](../aura_architect_council_v3.py#L36-L67) | `aura_architect_council_v3.py#function:select_critic_lanes:5af4851a0738b68b` | `a8011e96c7d2261f` | Selects critic lanes from plan structure, dependencies, continuity, rollback, and cost pressure. |
| Architecture Harness | `run_architecture` | [scripts/aura_architecture_harness.py:L116-L124](../scripts/aura_architecture_harness.py#L116-L124) | `scripts/aura_architecture_harness.py#function:run_architecture:cb2ae15fe72c73a9` | `25d9a167ea20dd21` | Runs repository architecture analysis while preserving the Harness compatibility/authority boundary. |

## Refresh contract

```text
source changes
→ refresh CODEMAP touched branches
→ semantic IDs / signatures / line ranges regenerate
→ regenerate SOURCE_ANCHORS.md
→ stale/missing/ambiguous anchors fail closed
```

Use `python scripts/aura_navigation_refresh.py` to sync current commit/working-tree changes, or pass `--refresh <paths...>` for an explicit bounded refresh. Use `--all` only for an intentional full source-card refresh.

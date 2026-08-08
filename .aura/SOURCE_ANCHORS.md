# Aura Source Anchors

**Version:** `AURA_SOURCE_ANCHOR_MAP_V1`  
**Bootstrap HEAD:** `1e509b76315b1a461a2d35db6b772688236c0e4a`  
**Authority:** navigation projection only; exact current source/tests/contracts remain authoritative.

> **Stable identity is not the line number.** These current source spans are bootstrap navigation anchors. `scripts/aura_navigation_refresh.py` regenerates this file from CODEMAP `semantic_id` + `signature_hash` whenever navigation state is refreshed.

| Mechanism | Symbol | Current bootstrap source span | Why it matters |
|---|---|---|---|
| CODEMAP semantic symbol extraction | `_python_symbol_records` | [`aura_codebase_navigator.py:L149-L192`](../aura_codebase_navigator.py#L149-L192) | Extracts AST symbols and regenerates semantic identity/signature/current spans. |
| CODEMAP incremental refresh | `refresh_index_for_paths` | [`aura_codebase_navigator.py:L482-L571`](../aura_codebase_navigator.py#L482-L571) | Reparses touched branches after successful writes; line ranges move here rather than becoming stale documentation. |
| Guarded WFST routing | `ArenaWFSTRuntime.route` | [`aura_arena_wfst_runtime.py:L56-L172`](../aura_arena_wfst_runtime.py#L56-L172) | Hard guards, capability binding, ranking, abstention, state packet, and non-authority boundaries. |
| Capability Connectome | `build_capability_connectome` | [`aura_capability_connectome.py:L312-L375`](../aura_capability_connectome.py#L312-L375) | Builds capability graph and checks implementation references against CODEMAP. |
| Capability resolution | `find_capability_path` | [`aura_capability_connectome.py:L378-L425`](../aura_capability_connectome.py#L378-L425) | Finds objective-relevant existing capabilities before invention. |
| Relational Synthesis | `compile_relational_shadow_capsule` | [`aura_relational_synthesis.py:L1574-L1592`](../aura_relational_synthesis.py#L1574-L1592) | Public read-only compiler from exact evidence into relational synthesis. |
| Relationship Atlas | `build_relationship_atlas` | [`aura_relationship_atlas.py:L609`](../aura_relationship_atlas.py#L609) | Starts the compiled relationship classification pass; generated refresh records its complete current span. |
| Selective Council V3 | `select_critic_lanes` | [`aura_architect_council_v3.py:L36-L67`](../aura_architect_council_v3.py#L36-L67) | Selects critic lanes from actual plan/dependency/risk evidence instead of invoking every critic. |
| Architecture Harness | `run_architecture` | [`scripts/aura_architecture_harness.py:L116-L124`](../scripts/aura_architecture_harness.py#L116-L124) | Runs architecture analysis while preserving the Harness compatibility and authority boundary. |

## Refresh contract

```text
source changes
→ CODEMAP incremental/full refresh
→ semantic_id + signature_hash + current line/end_line regenerate
→ SOURCE_ANCHORS.md regenerates from the curated manifest
→ missing / ambiguous anchors fail closed
```

Canonical command:

```bash
python scripts/aura_navigation_refresh.py --refresh path/to/changed.py
python scripts/aura_source_anchor_map.py --check
```

A line shift alone must never require a human to edit README prose.

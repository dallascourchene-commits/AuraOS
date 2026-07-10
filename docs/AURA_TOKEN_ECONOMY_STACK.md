# Aura Token Economy Stack

## What This Is

The **Token Economy Stack** makes Aura's token savings visible, measurable, and native to the cockpit. It compares raw prompt/file/repo context baselines against Aura's compressed packet/context/slice/ST3GG/CCR path.

## How It Works

```
Raw baseline:                    Aura path:
  raw_prompt_tokens (obj/4)        aura_packet_tokens (polysynthetic)
  raw_file_tokens (file chars/4)   codemap_search_tokens (search results)
  raw_repo_tokens (CODEMAP est.)   read_slice_tokens (120 lines)
                                   context_crush_tokens (CCR)
                                   st3gg_tokens (ST3GG egress)
                                   hermes_contract_tokens (contract)

  estimated_tokens_saved = raw_total - total_aura
  estimated_percent_saved = saved / raw_total * 100
  estimated_cost_saved_usd = saved / 1M * price_per_m
```

## Savings Sources

| Source | How it saves |
|--------|-------------|
| `polysynthetic_packet` | Compresses verbose objective into bracketed packet |
| `codemap_localization` | Search CODEMAP instead of reading full files |
| `ai_router_context` | Minimal function context instead of broad file reads |
| `read_slice` | 120-line bounded slice instead of full file |
| `context_crusher` | Compress prompts while preserving system prefix |
| `st3gg_recall_pointer` | Compact pointer instead of full capsule egress |
| `dream_rerank` | Better retrieval ranking reduces irrelevant context |
| `qdkt_fast_path` | Crystallized patterns avoid re-derivation |
| `hermes_contract` | Structured contract instead of unstructured prompt |

## Modules

| Module | Role |
|--------|------|
| `aura_token_economy_orchestrator.py` | Cockpit-level token/cost deltas |
| `aura_token_economics.py` | Per-call financial accounting with pricing tables |
| `aura_context_crusher.py` | Context compression with ledger |
| `aura_arena_st3gg_codec.py` | ST3GG egress with savings threshold |

## API

```python
from aura_token_economy_orchestrator import (
    compute_token_economy,
    compute_savings_sources,
    estimate_cost_saved_usd,
    token_economy_markdown,
)
```

## CLI

```powershell
python -m aura_agent_arena_cli token-economy --objective "Refactor Fireworks egress" --files aura_llm_egress.py,aura_agent_arena_bridge.py
```

## Important Note

All estimates use `chars / 4` as a local approximation. This is **NOT provider billing telemetry**. Actual token usage depends on the model tokenizer and prompt structure.

## Safety

- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`
- Token economy reports are advisory measurements — they do not authorize anything.

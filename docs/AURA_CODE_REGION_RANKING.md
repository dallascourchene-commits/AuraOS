# Aura Code Region Ranking

## What This Is

Ranks files, symbols, classes, functions, and line ranges relevant to an objective under a fixed token/line budget.

## Metrics

- `top_k_files`, `top_k_symbols`, `total_lines_selected`, `total_tokens_est`
- `context_efficiency_ratio`, `localization_confidence`, `needs_more_context`
- `coverage_estimate`, `confidence`

## CLI

```powershell
python -m aura_agent_arena_cli rank-code-regions --objective "..." --max-lines 400
```

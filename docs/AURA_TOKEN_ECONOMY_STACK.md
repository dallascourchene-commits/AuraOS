# Aura Token Economy Stack (Updated)

## What This Is

The Token Economy Stack makes Aura's token savings visible, measurable, and native to the cockpit. The **Empirical Cost Observatory** (PR #60) adds measured vs estimated distinction, versioned pricing, persistent ledger, and quality-normalized metrics.

## Architecture (Updated)

| Module | Role |
|--------|------|
| `aura_token_economy_orchestrator.py` | Cockpit-level token/cost deltas (from PR #57) |
| `aura_token_economics.py` | Per-call financial accounting with pricing tables |
| `aura_usage_normalizer.py` | **NEW**: Normalize provider usage into common schema |
| `aura_pricing_registry.py` | **NEW**: Versioned pricing with snapshot preservation |
| `aura_empirical_cost_ledger.py` | **NEW**: SQLite persistent ledger with migrations |
| `aura_cost_attribution.py` | **NEW**: Exclusive per-stage attribution waterfall |
| `aura_cost_experiment_runner.py` | **NEW**: Paired experiments (replay/shadow/live) |
| `aura_cost_telemetry_events.py` | **NEW**: Real-time event stream for UI |
| `aura_cost_observatory_mcp.py` | **NEW**: MCP tools for cost queries |
| `aura_context_crusher.py` | Context compression with ledger |
| `aura_arena_st3gg_codec.py` | ST3GG egress with savings threshold |

## Measurement Classes

| Class | Meaning |
|-------|---------|
| `MEASURED` | Provider reported exact usage |
| `TOKENIZER_EXACT` | Local tokenizer counted exact tokens |
| `DERIVED` | Derived from known fields |
| `ESTIMATED` | chars/4 fallback |
| `UNAVAILABLE` | No usage data |

## Measurement Precedence

1. Provider-billed cost is authoritative when available
2. Registry price calculation is secondary
3. Unknown pricing produces `COST_UNKNOWN` — never substitutes
4. Tokenizer count is secondary to provider usage
5. `chars / 4` is a last-resort estimate

## Quality-Normalized Economics

The principal success metric is `cost_per_verified_success`, not just `tokens_saved`. Aura must never celebrate a cheaper run that failed verification.

## Savings Status

- `SAVINGS_VERIFIED` — cheaper + verified + quality not worse
- `SAVINGS_PROVISIONAL` — cheaper but not yet verified
- `SAVINGS_INVALIDATED_BY_QUALITY` — cheaper but failed
- `SAVINGS_INCONCLUSIVE` — not cheaper
- `NO_COMPARABLE_BASELINE` — no baseline

## CLI Commands

```powershell
python -m aura_agent_arena_cli cost-status
python -m aura_agent_arena_cli cost-run --objective "..." --mode aura
python -m aura_agent_arena_cli cost-baseline --objective "..." --mode shadow
python -m aura_agent_arena_cli cost-compare --comparison-id <id>
python -m aura_agent_arena_cli cost-report --comparison-id <id> --format markdown
python -m aura_agent_arena_cli cost-attribution --run-id <id>
python -m aura_agent_arena_cli cost-history --limit 20
```

## Human Agent Arena Integration

The Arena server now exposes:
- `GET /api/human-agent/cost-telemetry` — panel data with events, runs, visual states
- `GET /api/human-agent/cost-events?since=<timestamp>` — event stream for polling

## MCP Tools

- `aura_cost_run_status` — current status
- `aura_get_cost_comparison` — paired comparison
- `aura_get_cost_attribution` — attribution waterfall
- `aura_get_quality_normalized_cost` — quality-normalized metrics

## Safety

- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`
- No production mutation from measurement
- No secrets in ledger
- All savings claims measured or labelled
- Quality-gating enforced

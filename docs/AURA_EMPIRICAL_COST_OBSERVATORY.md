# Aura Empirical Cost Observatory

## What This Is

The **Empirical Cost Observatory** measures the real operational economics of coding tasks executed through Aura's pipeline. It distinguishes measured, tokenizer-exact, derived, estimated, and unavailable values — no report may present an estimated value as an exact saving.

## Measurement Classes

| Class | Meaning |
|-------|---------|
| `MEASURED` | Provider reported exact usage |
| `TOKENIZER_EXACT` | Local tokenizer counted exact tokens |
| `DERIVED` | Derived from known fields (e.g., total = input + output) |
| `ESTIMATED` | chars/4 fallback |
| `UNAVAILABLE` | No usage data |

## Measurement Precedence

1. **Provider-billed cost** is authoritative when explicitly returned (`COST_MEASURED`)
2. **Registry price calculation** is secondary (`COST_CALCULATED`)
3. **Unknown pricing** produces `COST_UNKNOWN` — never substitutes another model's price
4. **Tokenizer count** is secondary to provider usage
5. **chars / 4** is a last-resort estimate

## Savings Status

| Status | Meaning |
|--------|---------|
| `SAVINGS_VERIFIED` | Aura cheaper + verified + quality not worse |
| `SAVINGS_PROVISIONAL` | Aura cheaper but not yet verified |
| `SAVINGS_INVALIDATED_BY_QUALITY` | Aura cheaper but failed verification or regressed quality |
| `SAVINGS_INCONCLUSIVE` | Aura not cheaper |
| `NO_COMPARABLE_BASELINE` | No raw baseline to compare |

## Quality-Normalized Metrics

- `cost_per_verified_success` — cost / verified_success
- `tokens_per_verified_success`
- `latency_per_verified_success`
- `repair_cost`
- `context_lines_per_success`
- `scope_violations_per_run`

## Experiment Modes

| Mode | Description |
|------|-------------|
| `REPLAY` | Stored provider fixtures, deterministic |
| `SHADOW` | Counterfactual estimate, no paid call |
| `PAIRED_LIVE` | Both paths through same provider (requires approval) |

## Attribution

Savings are calculated as **exclusive per-stage deltas** — each stage saves relative to its input. DREAM/QDKT are credited only when their decision changed retrieval. Protocol overhead (contracts, metadata, verification) is visible.

## CLI Commands

```powershell
python -m aura_agent_arena_cli cost-status
python -m aura_agent_arena_cli cost-run --objective "..." --mode aura
python -m aura_agent_arena_cli cost-baseline --objective "..." --mode shadow
python -m aura_agent_arena_cli cost-compare --comparison-id <id>
python -m aura_agent_arena_cli cost-report --comparison-id <id>
python -m aura_agent_arena_cli cost-attribution --run-id <id>
python -m aura_agent_arena_cli cost-history --limit 20
```

## Safety

- No production code mutated by measurement tools
- No secrets or unrestricted prompts written to ledger
- All savings claims are either measured or labelled as estimates
- Quality-gating enforced — cheaper failed runs cannot claim verified savings
- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`

## Limitations

- Pricing table is maintained manually; provider prices change frequently
- Shadow baselines are counterfactual estimates, not measured values
- Paired live mode incurs duplicate provider cost and requires explicit approval
- Local models may report energy/runtime but zero API cost

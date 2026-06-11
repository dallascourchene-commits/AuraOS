# AURA_ROUTER — Self-Optimising Provider/Protocol Router

`aura_router.py` is the self-learning routing layer that sits on top of the Aura substrate. It benchmarks every (model × packet-style × output-mode) combination, remembers the cheapest highest-quality route for each task type, and automatically sends future work through the optimal path — with zero internal LLM calls.

---

## Architecture overview

```
User task
   │
   ▼
CalibrationLedger  ←─ run_matrix() (aura_matrix_benchmark)
   │  (JSONL, newest wins)
   ▼
AutoRouter.route()
   │  best_candidates() → ordered list of (provider, style, mode)
   │
   ▼
AuraSubstrate.compile()   ← LLM-free: compress + validate
   │  (produces a polysynthetic packet)
   │
   ▼
ExternalLLM.generate()    ← only this step touches a paid model
   │
   ▼
QualityScorer + expand    ← LLM-free: validate + diff the output
   │
   ▼
ExecutionLog.append()     ← records actual tokens, cost, quality
```

**Aura's internal core never calls a local or in-process model.** Only the external egress step in `aura_llm_egress.py` touches a paid API.

---

## What calibration means

Calibration runs the full model/protocol matrix (every provider × packet style × output mode) against a representative task and records which combination yields the highest `overall_score` for each task type.

```
overall_score = 0.55·q_aura + 0.15·Δq + 0.15·latency_score + 0.15·cost_score
```

Results are appended to `Aura_Memory/aura_calibration.jsonl` (append-only, newest record per key supersedes older ones). The ledger is never committed — it is gitignored so accidental commits are impossible.

Run calibration offline with mock data (no API calls):

```bash
python3 aura_router.py calibrate --mock
```

Run with real providers (requires API keys in `aura_secrets.json`):

```bash
python3 aura_router.py calibrate --task mesh_offload
```

---

## How auto-routing chooses provider / style / output mode

`AutoRouter.best_candidates()` returns an ordered list of candidates for a given task type:

1. **If a provider has calibration data** for the task type, it is sorted by `overall_score` (highest first).
2. **Forced model** (via `--model`) is always placed first, regardless of score.
3. **Providers with no calibration data yet** fall back to the cold-start defaults (`bracket` style + `json_edit_plan` output mode) and are appended after calibrated providers.

The router tries each candidate in order. If one fails (network error, rate limit, bad key), it falls back to the next automatically.

---

## Cold-start defaults

Before any calibration data exists for a task type, the router uses:

| Field | Default |
|---|---|
| Packet style | `bracket` |
| Output mode | `json_edit_plan` |

These defaults were chosen from observed real runs: bracket packets + the output-token-efficient edit plan mode consistently produced the highest quality on the `mesh_offload` task.

---

## How forced model override works

Pass `--model <provider>` to force a specific provider to the front of the queue:

```bash
python3 aura_router.py route --task mesh_offload --model sambanova
```

The forced provider is tried first. If it fails, the router automatically falls back to the next best calibrated provider. The `forced_model` field in the execution log records which model was forced for auditing.

---

## How savings are calculated

### Actual savings (from `ExecutionLog`)

Every successful route appends a record with:
- `aura_input_tokens` — tokens in the compact Aura packet
- `aura_output_tokens` — tokens in the compact model output
- `aura_total_cost_usd` — actual cost of the Aura call
- `raw_input_tokens` — what the raw (no-Aura) prompt would have cost (measured deterministically)
- `est_raw_output_tokens` — estimated raw output size from calibration averages
- `est_raw_total_cost_usd` — estimated raw cost from calibration averages

The `savings` command sums these across all logged executions:

```
input_tokens_saved  = Σ (raw_input_tokens - aura_input_tokens)
output_tokens_saved = Σ (est_raw_output_tokens - aura_output_tokens)
est_cost_saved_usd  = Σ (est_raw_total_cost_usd - aura_total_cost_usd)
```

### Projected savings (from `CalibrationLedger`)

For each task type, the ledger's best-calibrated row is used to project what savings would look like if every future task were routed optimally:

```
input_reduction_pct  = token_reduction_amortized_pct  (guardrails treated as cached)
output_reduction_pct = output_token_reduction_pct
cost_saving_per_task = cost_saving_usd
```

```bash
python3 aura_router.py savings
```

---

## Running in mock mode (no API keys needed)

All router commands support `--mock` for fully offline operation:

```bash
# Calibrate with synthetic results
python3 aura_router.py calibrate --mock

# Route a task with the mock egress
python3 aura_router.py route --task mesh_offload --mock

# Check status after mock calibration
python3 aura_router.py status

# View savings from the mock route
python3 aura_router.py savings
```

Mock mode uses `MockEgress` from `aura_matrix_benchmark.py`, which returns a deterministic valid JSON edit plan. This is safe to run in CI or during development without incurring any API costs.

---

## Running with real providers (after updating API keys)

1. Add your API keys to `aura_secrets.json`:

```json
{
  "MISTRAL_API_KEY": "your-key-here",
  "SAMBANOVA_API_KEY": "your-key-here",
  "GROQ_API_KEY": "your-key-here"
}
```

2. Verify keys are detected:

```bash
python3 aura_router.py list-providers
# working: mistral, sambanova
# configured: groq
# placeholders: openrouter, github, openai, anthropic
```

3. Run calibration against all working providers:

```bash
python3 aura_router.py calibrate --task mesh_offload
```

4. Check the leaderboard:

```bash
python3 aura_router.py status
```

5. Route real tasks:

```bash
python3 aura_router.py route --task mesh_offload
# or force a specific model:
python3 aura_router.py route --task mesh_offload --model mistral
```

6. Check cumulative savings:

```bash
python3 aura_router.py savings
```

---

## Runtime files (never committed)

The following files are created at runtime and are listed in `.gitignore`:

| File | Contents |
|---|---|
| `Aura_Memory/aura_calibration.jsonl` | Append-only calibration ledger (newest record per key supersedes) |
| `Aura_Memory/aura_executions.jsonl` | Execution log for savings accounting |

These files grow over time. Delete them to reset calibration state.

---

## Current measured benchmark

**Best observed route: Mistral + bracket packet + JSON_EDIT_PLAN**

| Metric | RAW | AURA | Delta |
|---|---|---|---|
| Input tokens (direct) | 2695 | 2175 | 19.3% reduction |
| Input tokens (amortized) | 2695 | 539 | **80.0% reduction** |
| Output tokens | 1474 | 59 | **96.0% reduction** |
| Est. cost (USD) | ~$0.001423 | ~$0.000470 | **~66.9% savings** |
| Latency | 4.39s | 0.737s | **~7× faster** |
| Exposed source lines | 240 | 25 | **89.6% leakage reduction** |
| Quality score | 0.333 | 1.0 | **+0.667 improvement** |

Task: `mesh_offload` — Provider: Mistral — Provider discovery: mistral and sambanova verified working.

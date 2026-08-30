# DeepSeek cost, cache, and verified-output economics — through 2026-08-29

**Status:** measured provider accounting + bounded output/receipt review. Causal quality superiority still requires matched controls.

This report summarizes the owner-supplied DeepSeek usage export `usage_data_2026-07-31_2026-08-29 (1).zip`. The export filename spans July 31–August 29, but billing rows are present only for August 21, 22, 23, 26, 27, 28, and 29. Raw account-level export files are intentionally not committed here.

## Aggregate measured usage

| Metric | Measured value |
|---|---:|
| Requests | 11,670 |
| Logical/model tokens* | 1,321,646,285 |
| Input tokens | 1,311,343,042 |
| Cache-hit input tokens | 1,277,497,600 |
| Cache-miss input tokens | 33,845,442 |
| Output tokens | 10,303,243 |
| Input cache-hit share | 97.4190245% |
| Actual billed cost | $27.068077 |
| Billed/request | ~$0.00231946 |
| Billed / 1M logical/model tokens | ~$0.0204806 |

`* logical/model tokens = cache-hit input + cache-miss input + output. Cached logical tokens did not disappear; provider cache means reused input was billed/processed under a lower cache-hit path.`

## Conservative cache-billing counterfactual

For each day+model cell, cache-hit input was repriced at the **lowest observed cache-miss input-token rate in that same day+model cell**. This is deliberately conservative when multiple rate generations occur.

- Actual billed: **$27.068077**
- Additional cache-miss charge avoided: **>= $271.515493**
- Conservative all-miss-equivalent bill: **>= $298.583570**
- Conservative billed-cost reduction: **>= 90.9345%**
- Conservative all-miss-equivalent / actual bill ratio: **>= 11.03x**

This is a provider-pricing counterfactual. It does **not** establish that Aura uniquely caused provider cacheability.

## Flash vs Pro

| Metric | DeepSeek V4 Flash | DeepSeek V4 Pro |
|---|---:|---:|
| Requests | 11,206 | 464 |
| Cache-hit input | 1,277,475,456 | 22,144 |
| Cache-miss input | 32,049,023 | 1,796,419 |
| Output | 9,557,231 | 746,012 |
| Input cache-hit share | 97.5526213% | 1.2176647% |
| Billed | $24.384589 | $2.683488 |
| Billed/request | ~$0.00217603 | ~$0.00578338 |
| Effective input cost / 1M input tokens under actual cache mix | ~$0.013394 | ~$0.656326 |
| Conservative cache-billing savings | >= $271.501365 | >= $0.014128 |

Observed corresponding token-rate rows place Pro at approximately **3x Flash** across like token categories/rate generations. Task difficulty and output quality are not controlled by the export, so this is a price observation, not a quality comparison.

### August 29 routing witness

| Model | Requests | Logical/model tokens | Input cache-hit share | Billed | Billed / 1M logical/model tokens |
|---|---:|---:|---:|---:|---:|
| V4 Flash | 343 | 109,281,723 | 94.1092% | $2.443945 | ~$0.022364 |
| V4 Pro | 307 | 1,956,723 | 0% | $2.089129 | ~$1.067667 |

Under the actual August 29 workload/cache mix, Pro was about **47.74x more expensive per logical/model token** than Flash. That is a routing-economic witness, **not** evidence that Flash was 47.74x better in quality-adjusted terms.

## Routing law: Pro is escalation-only

DeepSeek V4 Pro is not the default remote lane.

```text
REUSE / HYPERDRIVE COLLAPSE
→ NO_MODEL / AURAOS DETERMINISTIC
→ active authorized high-reasoning interactive endpoint where appropriate
→ admitted LOCAL route when adequate
→ DEEPSEEK V4 FLASH / STANDARD lower-cost residual
→ DEEPSEEK V4 PRO only when earned
→ another frontier provider only with explicit current authority
```

A Pro escalation is earned only when lower-cost routes fail declared adequacy/success criteria, or when measured/preregistered expected quality, correctness, repair, verification, latency, or reusable-cognition value is sufficient to justify the incremental lifecycle cost.

A compact decision rule is:

```text
EscalateToPro(a) only if
E[Δ VerifiedValue(a)] > Δ LifecycleCost(a) + RiskMargin(a)
```

subject to source/currentness, authority, privacy, budget, and consequence constraints.

## Every consequential action gets a cost/outcome receipt

Token cost alone is not enough. Every consequential execution path should produce or extend `CognitiveEfficiencyReceiptV1` with action/command/capsule identity, route, provider/model/version/rate generation, cache-hit/cache-miss/output tokens, billed provider dollars, observable local compute/I/O/network/latency/energy, verification/rework, success criteria, final disposition, reusable artifacts/cognition, and invalidators/reopen triggers.

```text
C_action =
    C_provider
  + C_compute
  + C_IO
  + C_network
  + C_latency
  + C_coordination
  + C_verification
  + C_rework
```

Reuse/reconstruction avoided should be reported as a separately evidenced counterfactual rather than silently subtracted. `UNKNOWN COST != ZERO COST.` A no-model action may have $0 provider spend while still consuming local resources.

Future matched benchmarks should report at minimum:

- provider cost per verified outcome;
- lifecycle cost per verified outcome;
- time to verified result;
- success/acceptance rate;
- challenged correctness and defects surviving verification;
- repair/rework count and cost per repaired defect;
- cost per reusable verified artifact;
- cache savings per action;
- recomputation avoided per action;
- reusable cognition created;
- quality delta versus matched control.

## Output/quality evidence boundary

Current bounded evidence is meaningful but not universal:

- **HSC-196:** a real cold provider task consumed 43,743 prompt + 763 completion tokens; the accepted typed consequence was then reused from Coordinate Memory with `COORDINATE_HIT` and **0 provider tokens** on the scoped repeat.
- **HSC-198:** cold 27-objective wave produced 27/27 receipts but only 10 PASS / 17 TIMEOUT and failed its preregistered timeout criterion. The cold wave still observed **95.9% provider cache-read**; the scoped same-objective warm rerun produced **27/27 coordinate hits, 0 API tokens, and 31,816,596 prompt tokens avoided**. A WorkCapsule prompt-content defect prevents using that cold wave as a clean semantic-quality superiority result.
- **AWJ-023:** later governed DeepSeek dispatch evidence records a real canary, ACK-before-effect, zero-duplicate replay, stale-revision refusal before effect, restart absorption, dispatcher **21/21**, and an identity-distinct three-worker successor triad, reaching `GATE10_READY / READY_FOR_OWNER_PROMOTION / NONPROMOTING`.
- **AWJ-025:** later work returned `GATE10_PARTIAL / READY_FOR_OWNER_DISPOSITION` rather than being mislabeled complete. Preserving partial and negative results is part of the quality discipline.

The historical provider export is aggregated by day/model, so exact historical dollars cannot be assigned to an individual AWJ command or WorkCapsule. Action-linked receipts are required going forward.

## Present claim ceiling

Current bounded evidence supports the claim that Aura can **substantially reduce provider cost in scoped workloads through provider-cache exploitation plus source-bound semantic/result reuse while preserving explicit challenge, verification, stale-state, replay, restart, and Gate-10 controls**. Several scoped witnesses return already-accepted consequences with zero additional provider tokens.

It does **not yet** prove universal causal savings, universal superior output quality, or universal energy/lifecycle savings. Those require matched non-Aura controls with action-linked cost and quality telemetry.

The falsifiable systems hypothesis is:

> For matched consequence-complete workloads, Aura should achieve **equal-or-better challenged correctness at lower verified lifecycle cost** by combining deterministic resolution, minimum hydration, provider-cache reuse, semantic/result reuse, bounded model routing, Construct/Challenge/Verify, and persistent reusable cognition.

That is the benchmark target—not an assumption.

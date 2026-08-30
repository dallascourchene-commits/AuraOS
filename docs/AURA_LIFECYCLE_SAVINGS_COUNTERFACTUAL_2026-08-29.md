# Aura lifecycle-savings counterfactual — through 2026-08-29

**Status:** MODELLED / SENSITIVITY ANALYSIS. This document combines measured provider accounting and bounded Aura work-output/repair evidence with explicit counterfactual assumptions. It is not a randomized or matched-control causal estimate.

## Why token price is not the economic unit

The relevant economic unit is **cost to reach the same verified consequence**, not cost of the first model response.

A no-Aura path may incur costs that do not appear in a token-only comparison:

- re-reading/re-hydrating source and project state;
- rediscovering already-known failures;
- duplicate model work and duplicate effects;
- stale-context work that later has to be discarded;
- bugs that escape first-pass generation and require later rewrite;
- challenge/verification deferred until after dependent work has accumulated;
- repeated provider calls for a consequence Aura can reopen or reuse directly;
- human/tooling time spent diagnosing context, provenance, replay, or repair failures.

Aura itself also has costs: deterministic preprocessing, indexing, coordination, challenge, verification, receipts, repair, local compute, I/O, and latency. Therefore the falsifiable target is **lower lifecycle cost per verified outcome**, not "every Aura action is cheaper."

## Measured anchors

From the owner-supplied DeepSeek export through August 29:

- actual billed provider cost: **$27.068077**;
- requests: **11,670**;
- logical/model tokens: **1,321,646,285**;
- input cache-hit share: **97.4190245%**;
- conservative additional cache-miss charge avoided by provider caching: **>= $271.515493**;
- conservative all-miss-equivalent bill: **>= $298.583570**.

The provider-cache counterfactual is measured from observed prices, but the fraction of provider cacheability caused by Aura is unknown. It must therefore be a sensitivity parameter rather than silently treated as 100% Aura savings.

## Direct semantic/result-reuse witness beyond provider cache

HSC-198's clean cold wave used **31,816,596 prompt tokens + 317,459 completion tokens** and billed **$0.709600**. The scoped same-objective warm rerun then returned **27/27 `COORDINATE_HIT` with 0 API tokens**.

Using the lowest observed August 27 Flash rates from the supplied export, regenerating that same prompt/output without Aura-level result reuse would cost approximately:

- **$0.432239** even if every repeated input token received the cheapest observed provider cache-hit rate;
- **$7.209174** if the repeated input were billed at the cheapest observed cache-miss rate.

Aura's warm coordinate reuse cost **$0 provider** for that scoped repeat. This is a direct witness that semantic/result reuse can avoid a provider call even when provider-side prefix caching would make the repeated call cheap.

HSC-198 is not a clean semantic-quality benchmark: its cold run also exposed a WorkCapsule objective-plumbing defect and failed its preregistered timeout criterion. Those failures remain part of the evidence instead of being rewritten as success.

## Observed defect/rework containment

Bounded Aura records show concrete work that a token-only metric misses:

- an independent A3 Challenge identified **9/9 real defects**; after repair the target passed **17/17 tests plus 13/13 controller checks**;
- a separate repair fold verified **6/6 claimed repairs** while still preserving **four additional precision residuals** rather than declaring false completeness;
- HSC-198 exposed a timeout-kill defect that left a child DeepSeek process alive and holding a concurrency slot for roughly **137–416 seconds beyond timeout**; the executor was repaired to terminate the process group;
- HSC-198 also caught that the WorkCapsule objective was not reaching the model, preventing a schema/gate demonstration from being promoted into a semantic-quality claim;
- later governed dispatch evidence records ACK-before-effect, replay absorption with zero duplicate effect, stale-revision refusal before provider work, restart absorption, and a 21/21 dispatcher suite.

These are lifecycle-quality mechanisms. The historical aggregate usage export cannot assign exact dollars to each repair, so their monetary value should not be invented.

## Provider/rework sensitivity model

Let:

- `C_A = 27.068077` = actual billed provider cost;
- `S_C = 271.515493` = conservative provider-cache charge avoided;
- `f` = fraction of that provider-cache opportunity that would be lost in a no-Aura workflow;
- `r` = additional model/provider rework fraction needed by a no-Aura workflow to reach the same verified final state.

Then a deliberately simple provider-side counterfactual is:

```text
C_noAura_provider(f,r) = (C_A + f*S_C) * (1 + r)
Savings_provider = C_noAura_provider - C_A
```

The result is a sensitivity surface, not a causal estimate:

| Scenario | Cache opportunity attributed to Aura (`f`) | Extra quality-equivalent rework (`r`) | Modelled no-Aura provider cost | Modelled saving vs $27.068 actual | Modelled saving share | No-Aura / Aura ratio |
|---|---:|---:|---:|---:|---:|---:|
| Attribution-zero reference | 0% | 10% | $29.77 | $2.71 | 9.1% | 1.10x |
| Conservative | 25% | 10% | **$104.44** | **$77.37** | **74.1%** | **3.86x** |
| Central sensitivity | 50% | 25% | **$203.53** | **$176.46** | **86.7%** | **7.52x** |
| Strong | 75% | 40% | **$322.99** | **$295.92** | **91.6%** | **11.93x** |
| Stress / full-attribution | 100% | 50% | $447.88 | $420.81 | 94.0% | 16.55x |

The **central sensitivity point is not a measured headline**. It says: *if* Aura is responsible for half of the provider-cache opportunity and *if* a no-Aura path needs 25% more model/provider work to reach the same verified state, the observed $27.07 window corresponds to about $203.53 in provider-side quality-equivalent work without Aura.

The conservative 25%/10% point still produces a modelled **$104.44 vs $27.07**, or about **74% lower provider-side cost**. The attribution-zero row shows why causal attribution matters: if Aura caused none of the provider-cache advantage and avoided only 10% rework, the model gives only about 9.1% savings.

## Defect-escape / engineering-time sensitivity

Provider dollars are not the whole rework bill. For a sampled set of observed issues, keep labor in **hours** until an actual labor rate is supplied.

For `D` observed defects/residuals, probability `p_escape` that an issue would have escaped without Aura's challenge/verification, and downstream repair burden `h` hours per escaped issue:

```text
ExpectedAvoidedRepairHours = D * p_escape * h
DollarValue = ExpectedAvoidedRepairHours * actual_loaded_hourly_cost
```

Using only the **13 issues** visible in the two sampled A3/repair review records (9 upheld defects + 4 precision residuals) as an illustrative sensitivity set:

| Assumption | Expected avoided engineering hours |
|---|---:|
| 25% would escape; 0.5 h each | 1.625 h |
| 50% would escape; 2 h each | 13.0 h |
| 75% would escape; 4 h each | 39.0 h |

This does **not** claim all 13 issues would have escaped, that the records are statistically representative, or that every residual required the same remediation. It shows how downstream rewrite cost should be priced once action-linked repair time becomes observable.

## What the current model still excludes

The provider sensitivity table intentionally excludes several potentially material terms because the current historical records do not price them reliably:

```text
C_noAura_total =
    C_noAura_provider
  + C_rehydration
  + C_rediscovery
  + C_duplicate_effects
  + C_stale_work
  + C_defect_escape
  + C_human_repair
  + C_local_compute
  + C_IO_network
  + C_coordination
  + C_verification
  + C_downstream_blast_radius
```

Some of these terms can be negative for Aura on a particular action because challenge, verification, indexing, or coordination costs money. That is why Aura should not claim it saves money on literally every action. A verification run may cost more **locally** while reducing the expected cost of later failure.

## Measurement law going forward

`CognitiveEfficiencyReceiptV1` should make this model increasingly empirical. Each consequential action should bind:

- actual provider/model/version and rate generation;
- cache-hit, cache-miss, output and reasoning-token counts where exposed;
- provider dollars;
- local compute/I/O/network/latency/energy where observable;
- deterministic and provider calls avoided;
- reuse/coordinate hits and the exact counterfactual method;
- defects found, severity, repair attempts, regression scope, and surviving residuals;
- stale/replay/duplicate effects prevented;
- verification outcome and Gate disposition;
- reusable verified artifacts produced;
- human repair/review time when available;
- invalidators and reopen conditions.

For matched Aura/control runs, the primary economic score should be:

```text
VerifiedLifecycleEfficiency =
    VerifiedConsequenceValue / TotalLifecycleCost
```

with the denominator and quality dimensions also reported separately so a single score cannot hide regressions.

## Current claim ceiling

The evidence now supports more than a token-cache story:

> **Measured records show large provider-cache savings, direct zero-provider semantic/result reuse on scoped repeats, and repeated examples of defects, stale work, replay risk, and false-completeness being caught before promotion. A sensitivity model that attributes only part of the cache advantage to Aura and charges no-Aura workflows for additional quality-equivalent rework produces materially higher counterfactual lifecycle costs. The exact causal savings percentage remains unmeasured until matched controls and action-linked receipts are available.**

The correct target is therefore not `minimum tokens` and not `cheapest first response`. It is **maximum verified reusable consequence per unit of lifecycle cost**.

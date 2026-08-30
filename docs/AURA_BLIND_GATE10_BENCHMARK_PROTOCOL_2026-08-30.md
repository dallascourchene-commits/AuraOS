# Aura vs No-Aura Blind Gate-10 Benchmark Protocol — 2026-08-30

**Status:** PREREGISTERED CAMPAIGN DESIGN / NONPROMOTING UNTIL GATE 10  
**Arena campaign:** AWJ-028  
**Current issuance head:** AWJ-001 GEN24, `tp://arena/AURA-DRIVE2/workflow/AWJ-001-LIVE-WORKFLOW-FABRIC?g=24&head=3aeb8f3db921201f`  
**Paper X working successor:** Rev.4.4 — lifecycle efficiency + blind benchmark amendment

## Objective

Measure whether AuraOS/Arena improves **verified lifecycle efficiency**, correctness, hallucination containment, provenance/currentness fidelity, code quality, rework, replay safety, latency and provider cost versus genuinely blind no-Aura controls.

The economic unit is not first-response tokens. It is the cost required to reach the **same verified reusable consequence**:

```text
C_lifecycle =
    C_provider
  + C_compute
  + C_IO
  + C_network
  + C_latency
  + C_coordination
  + C_verification
  + C_rework
  + C_stale_work
  + C_duplicate_work_effects
  + C_rehydration
  + C_rediscovery
  + C_defect_escape
  + C_downstream_blast_radius
```

Primary economic score:

```text
VerifiedLifecycleEfficiency = VerifiedConsequenceValue / TotalLifecycleCost
```

The denominator and quality dimensions must also be reported separately; one scalar must never hide a correctness, currentness, safety or cost regression.

## Existing measured anchors

From the owner-supplied DeepSeek export through 2026-08-29:

- 11,670 requests;
- 1,321,646,285 logical/model tokens;
- 1,277,497,600 cache-hit input tokens;
- 97.4190245% input cache-hit share;
- $27.068077 actual billed provider cost;
- >= $271.515493 conservative cache-miss charge avoided;
- >= $298.583570 conservative all-miss-equivalent bill;
- >= 90.9345% conservative provider-billing reduction.

This provider-cache counterfactual is measured from observed pricing but is **not** proof that Aura caused every cache hit.

HSC-198 separately demonstrates semantic/result reuse beyond provider prefix caching: a cold 27-objective wave consumed 31,816,596 prompt + 317,459 completion tokens and billed $0.709600; the scoped same-objective warm rerun produced 27/27 `COORDINATE_HIT` with **0 API tokens**. Using the cheapest observed August 27 Flash rates, reconstructing that same work would still have cost about $0.432239 even with the cheapest observed cache-hit rate, or about $7.209174 with the cheapest observed miss rate.

## Lifecycle counterfactual sensitivity

Let:

```text
C_A = 27.068077
S_C = 271.515493
f   = fraction of provider-cache opportunity attributable to Aura-enabled workload structure
r   = additional model/provider rework required without Aura to reach equal verified quality

C_noAura_provider(f,r) = (C_A + f*S_C) * (1 + r)
```

| Scenario | f | r | No-Aura provider/rework equivalent | Saving vs actual | Saving share | Ratio |
|---|---:|---:|---:|---:|---:|---:|
| Attribution-zero reference | 0% | 10% | $29.77 | $2.71 | 9.1% | 1.10x |
| Conservative | 25% | 10% | **$104.44** | **$77.37** | **74.1%** | **3.86x** |
| Central sensitivity | 50% | 25% | **$203.53** | **$176.46** | **86.7%** | **7.52x** |
| Strong | 75% | 40% | **$322.99** | **$295.92** | **91.6%** | **11.93x** |
| Stress/full attribution | 100% | 50% | $447.88 | $420.81 | 94.0% | 16.55x |

These are **modelled sensitivity points**, not matched-control measurements. AWJ-028 exists to replace `f` and `r` with empirical estimates.

## Blinding law

### CONTROL arm

Receives the benchmark task, source corpus, allowed control tools, model/version, time/output budget and success criteria. It receives **none** of:

- Aura Drive / Aura Drive 2 orientation;
- Coordinate Memory or Coordinate-result hits;
- Aura WorkCapsules or HydrationTrees;
- HyperDrive / HyperScale conclusions;
- prior Aura answers, Gate receipts or treatment traces;
- treatment-specific source hints or compressed successor state.

### AURA arm

Must:

- enter through current Front Door/Arena;
- re-resolve current AWJ-001 head before consequence-bearing work;
- use bounded WorkCapsule/HydrationTree;
- use deterministic AuraOS tools before model reasoning where sufficient;
- reuse verified current cognition before recompute;
- preserve exact source/reopen handles and currentness;
- use independent Construct / Challenge / Verify when earned;
- persist independent first-pass leaves before reciprocal synthesis.

### Evaluator

Does not see treatment labels until semantic scoring is frozen. Ground truth is reconstructed independently from immutable sources, deterministic generators and executable tests.

## 3×3 adversarial benchmark lattice

### Cell 01 — 27-bit / 27-cell sharding and exact reconstruction

Adversarial binary/ternary payloads with reorder, duplication, omission, corruption, aliases, boundary values, misleading near-matches and insufficient-information cases. Score exact reconstruction, bit/trit error, fabricated completion, typed UNKNOWN, provenance and lifecycle cost.

### Cell 02 — semantic currentness and stale-state traps

Mixed-generation corpus with superseded records, same-name files, stale summaries, contradictory newer evidence, invalidated coordinates and partially valid old results. Score current-source selection, stale answers, false/correct reuse, exact reopen and hydration/cost.

### Cell 03 — code generation and repair cascade

Seed interacting race conditions, exception-contract mismatch, replay/idempotency faults, process/resource leaks, stale fixtures, tests that bless wrong behavior, documentation drift, hidden cross-module dependencies and a tempting structurally wrong rewrite. Score initial and surviving defects, repair attempts, regressions, unnecessary rewrite, hidden tests, time and lifecycle cost.

### Cell 04 — hallucination / citation / provenance stress

Plausible decoys, near-identical titles, deliberately absent facts, internally inconsistent passages, mixed dates/generations and UNKNOWN cases.

Hallucination classes are scored separately:

```text
H_source      unsupported or source-contradicted claim
H_citation    fabricated or incorrect source attribution
H_currentness once-true but stale/wrong for the current objective
H_inference   conclusion not justified by evidence/execution
```

Initial hallucinations and hallucinations surviving final Challenge/Verify are reported separately.

### Cell 05 — long context and minimum hydration

Corpus larger than useful model context with decisive sparse evidence distributed across distant files/generations and high-similarity distractors. Score decisive-source precision/recall, omissions, irrelevant hydration, tokens/bytes, cache/reuse, latency, cost and challenged correctness.

### Cell 06 — replay, idempotency and restart safety

Duplicate/reordered commands, stale revisions, worker/process restart, partial receipts, lease/fence turnover and adversarial retry timing. Score duplicate provider calls/effects, stale effects, ACK-before-effect violations, replay absorption, restart recovery, terminal consistency and wasted provider cost.

### Cell 07 — multi-agent independence and dissent

Compare independent first-pass A+/B-/C0 leaves, broadcast-first correlated debate and majority voting under comparable budgets. Score hypothesis diversity, unique falsifiers/defects, correlated errors, false consensus, majority-pressure reversals, dissent survival, final correctness and cost per unique useful discovery.

### Cell 08 — routing economics and escalation

Matched tasks across verified reuse/no-model, deterministic tooling, local model where admitted, lower-cost remote/Flash-class route and Pro-class escalation only when earned. Report routing advantage separately from Aura semantic/currentness advantage.

### Cell 09 — end-to-end adversarial composite

One principal Gate-10 torture test combining 27-bit reconstruction, currentness, code repair, ambiguous evidence, deliberate misinformation, restart/replay, long-context retrieval, exact mathematics, cost-aware routing and a final auditable decision. Neither arm gets the answer key.

## Execution topology

Baseline campaign = **20 logical triad swarms**:

- 9 blind CONTROL triads;
- 9 AURA triads;
- 1 blind evaluator triad;
- 1 final Gate-10 synthesis triad.

For evidence-bearing triads, the preferred topology is independent A+ Construct / B- Challenge / C0 Verify first-pass leaves, followed only then by reciprocal synthesis and final rebase. Expansion `3 -> 9 -> 27 -> 81` is permitted only on decomposed unresolved independent frontier and under current provider authorization/budget. Identical duplicate prompts are never counted as independent evidence.

## Metrics

Every run should emit enough data to calculate:

- success / acceptance;
- exact and challenged correctness;
- all four hallucination classes;
- citation/provenance error;
- stale-state answer rate;
- UNKNOWN abstention precision/recall;
- initial and surviving defects;
- repairs and regressions;
- duplicate/stale effects;
- input cache-hit/cache-miss/output/reasoning tokens where exposed;
- logical/model tokens;
- provider dollars;
- wall time / time to accepted consequence;
- source bytes/tokens hydrated;
- irrelevant hydration ratio;
- Coordinate/result hits and provider calls avoided;
- local compute/I/O/network/energy where observable;
- human repair/review time where observable;
- reusable verified artifacts;
- downstream work invalidated by corrections;
- total lifecycle cost per verified consequence.

## Gate-10 acceptance

A result does not pass Gate 10 merely because Aura wins an average. Required:

1. frozen benchmark manifest, seeds, condition mapping, source hashes, answer/test hashes and scoring code before results;
2. genuine treatment isolation and evaluator blinding;
3. repeated seeds where practical;
4. identical consequence criteria;
5. retention of FAIL/TIMEOUT/PARTIAL/UNKNOWN;
6. exact run-to-cost/token/receipt linkage;
7. independent reproduction of ground truth and scoring;
8. effect sizes/uncertainty where sample size permits;
9. cell-level heterogeneity before aggregate claims;
10. provider-cache benefit separated from Aura semantic/result reuse;
11. model-route advantage separated from substrate advantage;
12. verification overhead separated from avoided downstream repair;
13. explicit residuals and bounded claim ceiling.

Valid terminal dispositions are `GATE10_READY`, `GATE10_PARTIAL`, `FAILED_TO_VERIFY`, or `REPAIR_REQUIRED`. `GATE10_READY` remains `READY_FOR_OWNER_PROMOTION / NONPROMOTING`; the campaign does not self-promote claims or merge them into publication authority.

## Issued Drive work orders

- Master campaign: `1cmiUn4Au1BZyjFu3_S7HvC5V4UeNNIaiasM6bpb4x4s`
- Cell 01 sharding: `1DRLx6koEBGznJ_ETaToDki8PMPTUhjQK1Wo0hvGc_MM`
- Cell 02 currentness: `10K4nEk8xVVmryqzmXbbUREBmA_OndgHQwSrfVI-E-TE`
- Cell 03 code repair: `1A5kPlozpi6MplDN61Sk2Ew849Nk9Alti23YJb9P0LaE`
- Cell 04 hallucination/provenance: `1P1a0jyDnygC8eoT8kdpreYGtMQJRN1Bt2a80jk5-_cI`
- Cell 05 long context: `1NYDNa6cjtDzez08hd8AMSCW4Msfv-ULRWIWJjERc2js`
- Cell 06 replay/restart: `14k8zEUgW1MOnwIBm41k56ftXtk7f65YXJ2DZ_QMtarw`
- Cell 07 independence/dissent: `1GGLS-WcDAxxncfdzfL5jfxNSvRSddsa76UvBf4wHQjs`
- Cell 08 routing economics: `15MRBty0pMOacfeO3baXKBdezeW321ciou_rY2c82sUo`
- Cell 09 composite: `1tojLWreGpbd7F7vrSrD-JGcedaNPg7nWC6tZ6N8GZVg`
- Blind evaluator: `1hHkgF9LytpZ55I8RAXPfXLyzo7NxJl_RrSnmRi02N8Y`
- Gate-10 synthesis: `1fNLePVW0dvIigDRqF-27hM3odqp9aqriDsWEQc7H7DE`

## Claim ceiling before results

Current evidence supports high provider-cache reuse, direct zero-provider semantic/result reuse on scoped repeats, and concrete containment of defects, stale work, replay risk and false completeness. The present 74–92% conservative-to-strong lifecycle/provider savings band is a **sensitivity model**, not a causal result. Hallucination reduction, coding-quality improvement and total lifecycle advantage must be earned by the blinded campaign above.

# Aura Evidence Map

**Status:** active evidence and orientation document  
**Updated:** 2026-08-08  
**Scope:** current benchmark-backed Aura claims, mechanism/evidence crosswalk, independent comparable benchmarks, and explicit non-claims

---

## 1. Why this document exists

Aura is large enough that reading one file, one benchmark, one paper, or one historical design note produces a distorted picture.

This map is the bridge between:

```text
claim
→ Aura mechanism
→ current Aura evidence
→ authoritative artifact
→ external comparable evidence
→ limitation / next falsification test
```

It is deliberately stricter than a vision document. The purpose is not to collect every impressive number ever associated with Aura. The purpose is to make it hard to confuse:

- a measured Aura result with a projection;
- a token proxy with provider billing;
- an external paper's benchmark with an Aura benchmark;
- a mechanism that exists with a mechanism whose performance has been established;
- historical architecture with current authority;
- research convergence with proof of Aura's integration.

A smaller claim that can be reproduced is more useful than a large claim whose boundary conditions disappeared.

---

## 2. Evidence classes

| Class | Definition | Allowed use |
|---|---|---|
| **Aura measured** | Directly observed in a named Aura benchmark, test, executable gate, or inspected repository artifact. | May be stated as an Aura result with the benchmark/fixture boundary attached. |
| **Aura estimated / derived** | Calculated from measured artifacts or an explicit proxy. | Must be labeled as estimated/derived; never silently upgraded to provider telemetry. |
| **External comparable benchmark** | A result reported by another research project on a related architectural subproblem. | May establish that a pressure is independently measurable; may not be presented as Aura's result. |
| **Design thesis** | An architectural hypothesis, intended mechanism, roadmap item, or integration argument not yet established by the canonical Aura benchmarks. | May explain direction; must not be presented as measured performance. |
| **Historical context** | Origin, chronology, superseded experiment, influence, or older exploratory benchmark. | May explain why a mechanism exists; not current headline performance evidence. |

---

## 3. Canonical quantitative policy

For current public quantitative claims about **Aura itself**, use these two documents:

1. [`AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)
2. [`AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)

Everything else falls into one of three categories:

- qualitative architectural evidence;
- historical/supplementary experiment;
- external comparable evidence.

This policy intentionally retires large scenario arithmetic from the active evidence chain. It also prevents a convenient external paper from becoming an unearned Aura score.

### Rule for future numbers

A new Aura performance number should not enter the README until its benchmark record identifies:

- benchmark ID;
- tested commit/head;
- exact fixture/objective;
- evaluation gates;
- measurement class for every metric;
- reproduction command or artifact where available;
- negative findings;
- limitations;
- the next experiment capable of falsifying the claim.

---

# Part I — Aura's own benchmark evidence

## 4. Benchmark A — Architect consolidation / context localization

**Benchmark ID:** `AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V1`  
**Authority:** [`AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)  
**Study class:** reproducible single-session pilot; plan-only; no production mutation

The study compares three planning arms under the same repository, objective, JSON plan contract, and deterministic grounding rubric:

1. broad-context single planner;
2. Aura-sliced single planner;
3. Aura Architect Council.

### 4.1 Controlled results

| Arm | Calls | Input token proxy | Output token proxy | Total token proxy | Deterministic quality | Normalized cost |
|---|---:|---:|---:|---:|---:|---:|
| Broad-context single planner | 1 | 130,485 | 1,169 | 131,654 | 0.9550 | $0.133992 |
| Aura-slice single planner | 1 | 13,201 | 1,667 | 14,868 | 0.9607 | $0.018202 |
| Aura Architect Council | 12 | 90,020 | 4,121 | 94,141 | 0.9458 | $0.102383 |

### 4.2 Supported deltas

**Aura slice vs broad-context baseline:**

- input token proxy: **89.88% lower**;
- total token proxy: **88.71% lower**;
- normalized cost: **86.42% lower**;
- deterministic quality: **+0.0057**.

**Council vs broad-context baseline:**

- total token proxy: **28.49% lower**;
- normalized cost: **23.59% lower**;
- deterministic quality: **-0.0092**.

### 4.3 Important negative result

The Council did **not** beat the sliced single planner on this fixture. The sliced single planner was both cheaper and slightly higher on the deterministic quality rubric.

That is not an embarrassment to hide. It is evidence that multi-agent deliberation has an overhead and should be **selective**, which later becomes directly relevant to the Council V2→V3 ablation.

### 4.4 Measurement boundary

The benchmark records repository inventory and call counts as measured, while token counts use a documented four-bytes-per-token proxy. The normalized cost and quality scores are derived. Provider token telemetry and provider billing were unavailable.

The study does **not** establish:

- universal superiority of sliced context;
- Council superiority;
- production refactor success;
- exact provider-billed savings;
- general performance across models/providers/repos;
- any claim about consciousness, AGI, or ASI.

---

## 5. Benchmark B — executable refactor and Selective Council V3

**Benchmark IDs:**

- `AURA_EXECUTABLE_REFACTOR_CODE_QUALITY_V1`
- `AURA_ARCHITECT_COUNCIL_CALLING_ABLATION_V1`

**Authority:** [`AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)  
**Record schema:** `AURA_REFACTOR_OUTPUT_RECORD_V1`  
**Workflow run:** `29475732851`  
**Tested head:** `d12cbabaf6408ddf59613d0d6d51e01e1e33cf0d`  
**Artifact digest:** `sha256:19788b0a303cf6a4674d6ce67716acf30e6681991c4afa38487b14d3a4a9505a`

This benchmark extends the first study from planning into executable behavior. It evaluates visible tests, hidden tests, regression checks, API/scope/security gates, static analysis, and maintainability.

### 5.1 Executable results

| Method | Calls | Total token proxy | Visible | Hidden | Regression | API / scope / security | Disposition | Benchmark score |
|---|---:|---:|---:|---:|---:|---|---|---:|
| Broad-context single implementer | 1 | 131,654 | 3/3 | 1/3 | 2/2 | PASS | PARTIAL | **78.33** |
| Aura-slice single Surgeon | 1 | 14,868 | 3/3 | 2/3 | 2/2 | PASS | PARTIAL | **86.67** |
| Council V2 + Surgeon | 18 | 158,545 | 3/3 | 3/3 | 2/2 | PASS | ACCEPTED | **97.50** |
| Selective Council V3 + Surgeon | 12 | 106,494 | 3/3 | 3/3 | 2/2 | PASS | ACCEPTED | **97.50** |

### 5.2 Council V2→V3 ablation

| Metric | V2 | V3 | Difference |
|---|---:|---:|---:|
| Model calls | 18 | 12 | **33.33% fewer** |
| Critic reports | 15 | 9 | **40.00% fewer** |
| Input token proxy | 154,226 | 102,436 | **33.58% lower** |
| Output token proxy | 4,319 | 4,058 | lower |
| Total token proxy | 158,545 | 106,494 | **32.83% lower** |
| Plan quality | 0.9625 | 0.9625 | **0 delta** |
| Benchmark score | 97.50 | 97.50 | **0 delta** |

Within this controlled fixture, V2 and V3 produced:

- the same selected plan apart from metadata;
- the same executable patch digest;
- the same accepted disposition;
- the same observed quality;
- the same benchmark score.

V3 reached that accepted result with one-third fewer model calls and roughly one-third less total token proxy.

### 5.3 What this establishes — and what it does not

This is stronger evidence than the plan-only pilot because the artifact is executable and held-out behavior distinguishes the methods.

It still does **not** establish universal performance. The benchmark is smaller than a production refactor; the fixture patches were authored in one assisted evaluation program; evaluation was not blinded or independent-provider; performance and portability were not measured.

The next stronger study should add:

- multiple providers/models;
- exact provider token and billing telemetry;
- repeated trials;
- larger real Aura refactors;
- independently authored hidden tests;
- mutation/coverage/typechecking where relevant;
- blinded review and independent CI adjudication.

---

# Part II — Mechanism-to-evidence crosswalk

## 6. What is currently measured, what merely exists, and what remains a thesis

| Architectural pressure | Aura mechanism family | Canonical Aura evidence | Current evidence status | Closest independent benchmark family |
|---|---|---|---|---|
| Large-repository context overload | CODEMAP/topology discovery, bounded slices, Sliced Surgeon, exact hydration | Benchmark A + Benchmark B | **Measured on controlled fixtures** | Repository-level context compression |
| Multi-agent overhead / when to deliberate | Council V2, Selective Council V3 | Benchmark B ablation | **Measured on controlled fixture** | Multi-agent coordination; harness optimization |
| Executable patch completeness | Surgeon + Council planning + verification gates | Benchmark B | **Measured on controlled fixture** | Coding-agent coordination / harness evaluation |
| Strong-vs-cheap/local worker selection | Model Cognome, Fusion/Architect routing | No dedicated canonical Aura routing benchmark yet | **Mechanism exists; performance claim remains thesis** | RouteLLM; QEIL |
| Proof-bearing authorization and execution | Gate, Forge, receipts, provenance / Verified DAG | Benchmark B includes API/scope/security/test gates but is not a whole governance benchmark | **Partially exercised; system-wide performance claim not established** | Proof-Carrying Agent Actions |
| Bounded current memory vs stale history | State Ledger, Continuity, exact-current-state preference | Not one of the two canonical quantitative benchmarks | **Mechanism exists; current headline quantitative claim withheld** | Verifiable Memory; When History Lies |
| Failure memory / causal diagnosis | Attempt Archive, ArenaExperience, Crucible/Waboose learning pressure | Not one of the two canonical quantitative benchmarks | **Mechanism exists; performance claim not established** | TRAJDEBUG |
| Reusable capability selection/composition | Capability Genome Resolver, recipes, Capability Commons | Not directly benchmarked by the two canonical studies | **Design direction / partial implementation depending on component** | SkillComposer; skill-admission gating |
| Proof before reusable knowledge enters future context | verification/gating + governed promotion | No canonical admission benchmark yet | **Design thesis supported by architecture and external pressure** | When Self-Evolution Backfires |
| Long-refactor continuity and architectural chain completion | Architecture Harness / ARCH | Not a canonical quantitative Aura benchmark yet | **Operational architecture; dedicated benchmark still needed** | HarnessOpt-Bench |
| Local/heterogeneous execution | Model Cognome / local-first routing direction | No canonical energy/latency benchmark | **Design thesis until measured on Aura** | QEIL |

This table is intentionally asymmetric. The existence of a source file or mechanism does not automatically authorize a performance adjective.

---

## 7. Context localization: strongest current Aura evidence

### Aura mechanism

Aura separates **discovery** from **authority**:

```text
compressed index / topology / relationship hints
→ identify a bounded region
→ hydrate exact current source / contracts / tests
→ act only on authoritative evidence
```

The relevant mechanism family includes CODEMAP/topology discovery, relationship localization, bounded slices, and the Sliced Surgeon execution pattern.

### Aura evidence

Both canonical benchmarks support the same bounded conclusion:

- the planning pilot reduced the total token proxy from 131,654 to 14,868 while slightly increasing its deterministic planning-quality score;
- the executable benchmark preserved that low-context arm and improved the benchmark score from 78.33 to 86.67 compared with the broad-context implementer.

### Independent comparable evidence

**On the Effectiveness of Context Compression for Repository-Level Tasks — arXiv:2604.13725** systematically evaluates repository-level context compression. At 4× compression, some continuous methods outperform full context by up to **28.3% BLEU**, and high compression produces up to **50% end-to-end latency reduction**.

This does not reproduce Aura's slicing mechanism. It independently supports the narrower premise that repository context can contain enough noise that **less, better-selected context can improve both efficiency and task performance**.

---

## 8. Selective Council: deliberation should earn its cost

### Aura mechanism

Council is not intended to mean “always call more models.” Selective Council V3 exists because Benchmark A exposed the cost of broad deliberation.

The desired question is:

> **Which uncertainty or architectural boundary actually benefits from another critic?**

### Aura evidence

Benchmark B directly compares V2 and V3 while holding the accepted result constant:

- 33.33% fewer model calls;
- 40% fewer critic reports;
- 33.58% lower input token proxy;
- 32.83% lower total token proxy;
- no plan-quality loss;
- same executable patch digest and accepted disposition.

### Independent comparable evidence

**AgentRadio — arXiv:2607.28430** reports that four asynchronously coordinated coding agents resolve **62.1%** of SWE-Atlas tasks versus **32.3%** for its stated single-agent Claude Code baseline. It supports the proposition that multi-agent coordination can materially help long-horizon code understanding when interdependent findings must propagate during work.

Aura does not use AgentRadio's protocol. The overlap is the architectural pressure: collaboration can help, but orchestration is itself part of the system being optimized.

**HarnessOpt-Bench — arXiv:2608.06301** evaluates five frontier models, four downstream tasks, and 111 scored runs, showing that harness effects are measurable, task-dependent, and far from exhausted. This is especially relevant to Aura's decision to treat selection, prompts, tools, memory, orchestration, and verification as architecture rather than invisible glue.

---

## 9. Model routing: plausible architecture, not yet an Aura benchmark claim

### Aura mechanism

Aura's model layer evolved from provider failover into Model Cognome / Architect routing: use stronger reasoning where the uncertainty warrants it and bounded cheaper/local workers where constraints and verification make that safe.

### Current Aura evidence boundary

Neither canonical benchmark isolates model-routing policy as its independent variable. Therefore claims that Model Cognome itself produces a specific cost, latency, or quality gain remain **unmeasured by the canonical evidence set**.

### Independent comparable evidence

**RouteLLM — arXiv:2406.18665** reports more than **2× cost reduction in some evaluated cases without compromising response quality** by dynamically routing between stronger and weaker LLMs.

**QEIL — arXiv:2602.06057** evaluates heterogeneous CPU/GPU/NPU inference across five model families and reports **35.6–78.2% energy reduction, 68% average-power reduction, 15.8% latency improvement, and zero accuracy loss** under its setup.

These papers support the pressure behind differentiated routing. They are not Aura performance results. Aura needs a dedicated routing ablation before assigning a number to Model Cognome or local-first execution.

---

## 10. Verified memory and current-state authority

### Aura mechanism

Aura treats current exact state as authoritative over stale summaries, old chat history, generated topology, embeddings, or remembered plans. State Ledger / Continuity and exact-head materialization in the refactor workflow exist to keep execution tied to the state that is actually current.

### Current Aura evidence boundary

Older Aura experiments may contain continuity metrics, but they are not part of the two canonical quantitative documents selected for the current public evidence chain. Therefore no continuity percentage is promoted here as a current headline Aura claim.

### Independent comparable evidence

**Verifiable Memory — arXiv:2608.03137** unifies long-term memory, active context, and episodic history under a memory-operation policy with local and global verifiers. Across five benchmarks and two backbones it reports the best result on the vast majority of metrics and the strongest efficiency-performance frontier under controlled online-token budgets on three interactive benchmarks.

**When History Lies — arXiv:2608.06057** isolates stale/misleading interaction history as a tool-use failure mode. In its Qwen3-1.7B baseline, polluted history flips **32.1%** of decisions that were correct under the original trajectory. Its proposed method reaches **87.0% Balanced Tool-Use Accuracy** and scales higher in larger teacher/student configurations.

The relevance to Aura is precise: **history is evidence only while it remains authoritative for the current state**.

---

## 11. Capability reuse: useful knowledge needs admission control

### Aura mechanism

Capability Commons, recipes, Capability Genome resolution, verification, provenance, and governed promotion are designed around a simple idea: useful work should become reusable without allowing bad work to become permanent reference material.

### Current Aura evidence boundary

The canonical Aura benchmarks evaluate context/planning/executable refactor behavior. They do not yet isolate a growing capability library or measure skill-pool contamination, retrieval/composition accuracy, long-run reuse rate, or admission quality.

### Independent comparable evidence

**Generative Skill Composition for LLM Agents — arXiv:2606.32025** treats skill selection as a structured composition problem over subset, count, and order. SkillComposer reports **+23.1 and +18.2 percentage-point pass-rate gains** over no-skill baselines on two production-grade coding agents while matching the stated gold-skill upper bound at lower prompt-token cost.

**When Self-Evolution Backfires — arXiv:2608.05810** shows the other side of reuse: unconditional skill accumulation eventually degrades as defective skills contaminate later distillation. Its pre-commit Verifier-as-Gatekeeper reaches **72% pass@1** on Terminal-Bench 2 with a skill pool roughly **5× smaller**, while the ungated pool gives back much of its gain as it grows.

That result is unusually close to Aura's governance thesis: **verification after contamination is weaker than admission control before reusable knowledge becomes future context**.

---

## 12. Proof-bearing actions and authority boundaries

### Aura mechanism

Gate, Forge, receipts, provenance, and human/community disposition enforce a distinction between recommendation, authorization, execution, and proof.

```text
planning proposes
→ governance authorizes
→ execution acts
→ verification proves
→ provenance records
```

### Current Aura evidence boundary

Benchmark B exercises API, scope, security, visible/hidden/regression, static-analysis, and maintainability gates. It therefore provides executable evidence that gated evaluation matters in the tested refactor fixture.

It is **not** a full benchmark of every Aura governance path, community authority rule, runtime lease, or production action.

### Independent comparable evidence

**Proof-Carrying Agent Actions — arXiv:2606.04104** defines portable certificate-bearing actions across heterogeneous runtimes. Its protected benchmark expands 24 executable seeds to **96 traces across four runtime families**, preserving route quality while ablations expose distinct failure modes.

The architectural convergence is the separation of action intent, authorization, runtime execution, and replayable evidence.

---

## 13. Failure memory needs causal attribution, not just logging

### Aura mechanism

Attempt Archive, ArenaExperience, Crucible, Waboose, and related learning paths exist so failed work can become structured evidence rather than disappear or be blindly repeated.

### Current Aura evidence boundary

The two canonical benchmarks preserve negative results and held-out failures, but do not independently benchmark Aura's causal error-attribution quality. Therefore “Aura learns from failure better” is not yet a canonical measured claim.

### Independent comparable evidence

**TRAJDEBUG — arXiv:2608.06346** introduces TrajErrBench with **486 manually annotated failed trajectories** from tool-use and coding benchmarks. Its framework tracks error lifecycle, resolution status, and terminal impact to identify the earliest failure responsible for the final outcome, and reports the best overall performance over evaluated baselines.

This supports a key pressure behind Attempt Archive: in long trajectories, the last visible error is not necessarily the causal error worth learning from.

---

## 14. The harness is part of the intelligence system

### Aura mechanism

Architecture Harness / ARCH exists because long, multi-agent refactors exposed failures that model capability alone did not solve:

- stale or wrong-head edits;
- lost continuity;
- repeated failed approaches;
- local patches that violate an architectural invariant elsewhere;
- handoff drift between agents;
- completion claims made before the architecture chain is actually complete.

### Current Aura evidence boundary

ARCH is operational architecture, but it does not yet have a dedicated canonical Aura harness benchmark in the two-document evidence set. Historical “before/after” experience is useful provenance, not sufficient quantitative proof.

### Independent comparable evidence

**HarnessOpt-Bench — arXiv:2608.06301** explicitly treats the harness — prompts, tools, control flow, memory, and orchestration — as an optimization object. Across five frontier models, four tasks, and 111 scored runs, the study finds measurable, task-dependent harness effects and substantial room for optimization.

The appropriate Aura claim is therefore modest:

> **Harness design is a real measurable variable; Aura's particular harness still needs its own controlled ablation.**

---

# Part III — Independent comparable benchmark index

## 15. Primary-source arXiv benchmark table

These results belong to the cited papers, not to Aura.

| Paper | arXiv | Related Aura pressure | Benchmark result relevant to the comparison |
|---|---|---|---|
| RouteLLM: Learning to Route LLMs with Preference Data | [`2406.18665`](https://arxiv.org/abs/2406.18665) | strong/weak model routing | More than **2× cost reduction in certain evaluated cases** without response-quality loss. |
| On the Effectiveness of Context Compression for Repository-Level Tasks | [`2604.13725`](https://arxiv.org/abs/2604.13725) | bounded repository context | At 4× compression, some continuous methods beat full-context BLEU by up to **28.3%**; up to **50%** end-to-end latency reduction at high ratios. |
| Proof-Carrying Agent Actions | [`2606.04104`](https://arxiv.org/abs/2606.04104) | governed, evidence-bearing actions | Protected benchmark expanded from **24 executable seeds to 96 traces across four runtime families**; ablations expose distinct failures. |
| Generative Skill Composition for LLM Agents | [`2606.32025`](https://arxiv.org/abs/2606.32025) | capability composition | **+23.1 / +18.2 percentage-point** pass-rate gains over no-skill baselines on two coding agents. |
| AgentRadio | [`2607.28430`](https://arxiv.org/abs/2607.28430) | multi-agent codebase coordination | Four coordinated agents resolve **62.1%** of SWE-Atlas tasks vs **32.3%** stated single-agent baseline. |
| Quantifying Energy-Efficient Edge Intelligence (QEIL) | [`2602.06057`](https://arxiv.org/abs/2602.06057) | heterogeneous local execution | Reports **35.6–78.2% energy reduction**, **68% average-power reduction**, **15.8% latency improvement**, zero accuracy loss. |
| Verifiable Memory | [`2608.03137`](https://arxiv.org/abs/2608.03137) | bounded active context + verified memory | Across five benchmarks/two backbones, best on vast majority of metrics; strongest efficiency-performance frontier under controlled online-token budgets on three interactive benchmarks. |
| When Self-Evolution Backfires | [`2608.05810`](https://arxiv.org/abs/2608.05810) | verification before reuse | **72% pass@1** on Terminal-Bench 2 with a skill pool roughly **5× smaller**; ungated accumulation eventually degrades. |
| When History Lies | [`2608.06057`](https://arxiv.org/abs/2608.06057) | current-state authority over stale history | Polluted history flips **32.1%** of otherwise-correct baseline decisions; proposed method reaches **87.0% Balanced Tool-Use Accuracy**. |
| HarnessOpt-Bench | [`2608.06301`](https://arxiv.org/abs/2608.06301) | harness quality / orchestration | **5 frontier models × 4 tasks, 111 scored runs**; measurable task-dependent harness effects. |
| TRAJDEBUG | [`2608.06346`](https://arxiv.org/abs/2608.06346) | causal failure attribution | Benchmark of **486 manually annotated failed trajectories**; best overall performance over evaluated critical-error baselines. |

### Interpretation rule

These papers can support statements such as:

> Independent work finds that selective routing, context compression, skill composition, verified memory, admission gating, stale-history resistance, failure attribution, governed actions, multi-agent communication, and harness design are measurable system-level problems.

They cannot support:

> Therefore Aura obtains the paper's benchmark score.

or:

> Therefore the paper validates Aura as a whole.

The strongest responsible phrasing is:

> **The field is independently converging on many of the pressures Aura was built to solve. Aura's own benchmarks must establish whether her particular integration solves them effectively.**

---

# Part IV — Retired and withheld claims

## 16. Claims intentionally removed from the active public evidence chain

The following categories may remain in historical planning material, but should not be used as current README evidence unless new benchmark work independently re-establishes them:

### 16.1 Giant generalized multipliers

Retire generic claims such as “10,000×” or similar large architecture-wide multipliers unless a named reproducible benchmark defines exactly what quantity improved, against what baseline, on what fixture, and with what measurement method.

### 16.2 Adoption arithmetic

Do not treat hypothetical developer/user adoption multiplied by per-user reuse as evidence of current Aura impact. That is scenario analysis, not benchmark data.

### 16.3 Absolute energy / data-center savings scenarios

External energy baselines can motivate resource-aware architecture, but multiplying a global TWh forecast by hypothetical Aura adoption and hypothetical savings does not measure Aura.

Aura currently has **no canonical energy benchmark**. QEIL is useful external comparable evidence; its gains remain QEIL's gains.

### 16.4 Counterfactual Council amortization headlines

The older hybrid Council/Surgeon benchmark contains useful historical analysis, but its very large Council-amortization savings are explicitly counterfactual/synthetic rather than an observed end-to-end model run. Do not promote them over the measured V2→V3 ablation.

### 16.5 Older standalone continuity percentages

Historical State Ledger/continuity experiments can remain in their original records. They are not part of the two-document canonical quantitative policy and therefore should not be used as the current top-level continuity claim without a new integrated benchmark.

### 16.6 External benchmark inheritance

No external paper's accuracy, pass rate, token saving, cost saving, latency saving, or energy saving is an Aura result merely because Aura contains a related mechanism.

---

## 17. Why negative results remain in the evidence map

Aura's evidence should preserve where the architecture **did not** win:

- Benchmark A's Council was worse than the sliced single planner on cost and slightly worse on deterministic planning quality.
- Benchmark B's broad implementer still passed visible tests and several gates; it was not useless, just less complete on hidden behavior.
- The sliced Surgeon improved on broad context but still missed one hidden case.
- Council's extra deliberation became worthwhile on the executable fixture only when held-out completeness demanded it.

These observations are architectural information. They argue against universal policies such as “always use Council,” “always minimize context,” or “always use the strongest model.”

The recurring Aura strategy is conditional composition under evidence.

---

# Part V — What the next benchmark should test

## 18. Priority benchmark ladder

### Tier 1 — replicate the two canonical results

- exact provider token telemetry;
- exact provider billing where available;
- repeated trials;
- multiple model families/providers;
- confidence intervals / variance;
- independently authored hidden tests.

### Tier 2 — real production-sized refactors

Compare:

1. broad single agent;
2. bounded single Surgeon;
3. Council V2 + Surgeon;
4. Selective Council V3 + Surgeon;
5. ARCH-enabled end-to-end refactor.

Measure:

- accepted patch rate;
- hidden/regression failures;
- scope violations;
- security findings;
- rework loops;
- wall-clock time;
- exact tokens/cost;
- architectural invariant breakage;
- human review burden.

### Tier 3 — dedicated mechanism ablations

Run independent tests for:

- Model Cognome routing;
- State Ledger / current-state reliability;
- Attempt Archive / causal failure reuse;
- Capability Genome selection/composition;
- pre-commit capability admission;
- ARCH exact-head/continuity behavior;
- local/heterogeneous execution energy and latency.

### Tier 4 — longitudinal Capability Commons study

Measure whether reuse actually changes the work curve over time:

- verified reuse hit rate;
- novel-work fraction;
- failed-reinvention rate;
- capability-selection precision;
- stale/superseded capability rejection;
- adaptation cost;
- re-verification cost;
- contribution/provenance correctness;
- absolute compute/energy rather than only per-task efficiency.

This is where the Capability Commons thesis either becomes a measured systems advantage or fails honestly.

---

# Part VI — Source and provenance index

## 19. Primary Aura evidence documents

- [`AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md) — canonical planning/context benchmark.
- [`AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](AURA_EXECUTABLE_REFACTOR_BENCHMARK.md) — canonical executable refactor and Council V2→V3 ablation.

## 20. Architecture / chronology documents

- [`AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md) — causal architecture evolution and acknowledged influences.
- [`AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md`](AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md) — origin and continuity thesis.

## 21. Research comparison documents

- [`AURA_RESEARCH_ALIGNMENT_CATALOG.md`](AURA_RESEARCH_ALIGNMENT_CATALOG.md) — broader research-alignment catalog.
- [`AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md) — independent convergence analysis.

## 22. Economic / capability direction

- [`AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md`](AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md) — Extension Economy, Capability Commons, attribution, and cultural/philosophical horizon.

## 23. Deprecated scenario material

- [`AURA_METRICS_AND_SCALE_SCENARIOS.md`](AURA_METRICS_AND_SCALE_SCENARIOS.md) — deprecated as active benchmark evidence; retained only as a historical pointer after 2026-08-08.
- [`AURA_HYBRID_COUNCIL_SURGEON_BENCHMARK.md`](AURA_HYBRID_COUNCIL_SURGEON_BENCHMARK.md) — useful historical/supplementary experiment; its projected shared-grounding amortization is not one of the two canonical current benchmark claims.

---

## 24. The compact evidence rule

For a human or AI evaluating Aura:

```text
Aura number?
→ find it in one of the two canonical Aura benchmark documents

External number?
→ keep it attached to the paper that measured it

Mechanism exists but has no canonical benchmark?
→ call it implemented architecture or a design thesis, not proven performance

Historical projection?
→ keep it historical
```

That leaves Aura with a smaller argument, but a stronger one:

> **The architecture has controlled benchmark evidence for context localization and selective Council execution. Independent research shows that many adjacent pressures are real and measurable. The remaining integration claims are a benchmark agenda, not a substitute for one.**

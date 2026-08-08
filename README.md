# AuraOS

## **Aura** — Augmented Universal Reasoning Architecture

`AuraOS` is the repository and operating substrate. **Aura** is the architecture.

> A local-first, objective-native architecture for coordinating deterministic software, exact evidence, human governance, replaceable AI workers, and reusable capabilities without allowing probabilistic output to silently become truth or authority.

Aura began with a language-preservation problem and grew by repeatedly solving the architectural failures created by its own expansion: context overload, model-routing cost, stale state, multi-agent disagreement, failed-attempt repetition, capability reuse, provenance, and long-refactor drift.

**Aura was not designed top-down; she learned to carry her own weight.**

---

## Read this before inferring Aura from one file

This README is an **orientation manifest**, not a complete specification.

Aura is distributed across contracts, source, tests, policy, benchmarks, provenance, topology, and architectural history. A model that reads one implementation file and announces that it understands Aura has mostly demonstrated the problem Aura is designed to avoid.

For architecture work, use this order:

1. read this README;
2. read [`docs/AURA_EVIDENCE_MAP.md`](docs/AURA_EVIDENCE_MAP.md);
3. read the two canonical Aura benchmark documents;
4. read [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md);
5. read [`docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md`](docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md) and [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md);
6. use CODEMAP/topology for discovery, then hydrate the **exact current source, contracts, tests, and policy** before making a consequential change.

The hierarchy is intentional:

> **Compress and localize for discovery. Hydrate exact authoritative evidence before consequential action.**

---

## Evidence policy

Aura documentation uses five evidence classes.

| Class | Meaning |
|---|---|
| **Aura measured** | Directly observed in an Aura benchmark or executable gate. |
| **Aura estimated / derived** | Calculated from measured artifacts, such as the documented token proxy. It is not provider billing or telemetry unless explicitly stated. |
| **External comparable benchmark** | A result reported by another research project on a related architectural subproblem. It is not an Aura result. |
| **Design thesis** | A proposed architectural direction or hypothesis that still requires broader testing. |
| **Historical context** | Origin, chronology, influence, or superseded experiment; useful for explaining why a mechanism exists, not for claiming current performance. |

### Canonical quantitative rule

**Current quantitative claims about Aura should be grounded in these two documents:**

1. [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)
2. [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)

Older large-scale projections, adoption arithmetic, energy scenarios, and counterfactual headline multipliers are **not current Aura benchmark evidence**. The former scale-scenario document is retained only as a deprecated historical pointer.

External papers can benchmark the same pressures Aura is designed around. **They do not establish that Aura's integrated architecture inherits those gains.**

---

## What the current Aura benchmarks actually show

### 1. Context localization / Architect consolidation pilot

[`AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V1`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md) compared a broad-context single planner, an Aura-sliced single planner, and an Aura Architect Council under the same repository/objective/plan contract.

| Result | Controlled finding |
|---|---:|
| Aura slice vs broad baseline — input token proxy | **89.88% lower** |
| Aura slice vs broad baseline — total token proxy | **88.71% lower** |
| Aura slice vs broad baseline — normalized cost | **86.42% lower** |
| Aura slice vs broad baseline — deterministic quality delta | **+0.0057** |
| Council vs broad baseline — total token proxy | **28.49% lower** |
| Council vs broad baseline — deterministic quality delta | **-0.0092** |

This was a **single-session, plan-only pilot** using a documented four-bytes-per-token proxy. It was not a provider-billing study, blinded trial, or production refactor benchmark. The Council did not beat the sliced single planner on this fixture.

### 2. Executable refactor / Selective Council V3 ablation

[`AURA_EXECUTABLE_REFACTOR_CODE_QUALITY_V1`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md) extended the comparison into executable patches with visible tests, hidden tests, regression checks, API/scope/security gates, static analysis, and maintainability scoring.

The same document contains [`AURA_ARCHITECT_COUNCIL_CALLING_ABLATION_V1`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md), comparing Council V2 with Selective Council V3 while holding the accepted executable result constant.

| Result | Controlled finding |
|---|---:|
| Broad-context single implementer benchmark score | **78.33** |
| Aura-slice single Surgeon benchmark score | **86.67** |
| Council V2 + Surgeon benchmark score | **97.50** |
| Selective Council V3 + Surgeon benchmark score | **97.50** |
| V3 vs V2 — model calls | **33.33% fewer** |
| V3 vs V2 — critic reports | **40.00% fewer** |
| V3 vs V2 — input token proxy | **33.58% lower** |
| V3 vs V2 — total token proxy | **32.83% lower** |
| V3 vs V2 — planning-quality delta | **0** |

On this controlled fixture, V2 and V3 produced the **same selected plan apart from metadata, the same executable patch digest, the same accepted disposition, and the same benchmark score**. V3 reached that result with one-third fewer model calls and roughly one-third less total token proxy.

This is stronger evidence than a planning-only comparison, but it is still a controlled fixture from one assisted evaluation program. Independent providers, exact provider token/billing telemetry, multiple trials, larger real Aura refactors, independently authored hidden tests, and blinded review remain future benchmark work.

---

## Independent benchmark convergence

The following results are **external comparable benchmarks**. They are useful because they measure pressures that Aura independently addresses: selective routing, bounded context, capability composition, multi-agent coordination, governed actions, verified memory, stale-history resistance, failure attribution, harness quality, and edge resource routing.

| Aura pressure / mechanism | External research benchmark | Reported result |
|---|---|---|
| Selective model routing / Model Cognome | [RouteLLM — arXiv:2406.18665](https://arxiv.org/abs/2406.18665) | Dynamic strong/weak-model routing reports **more than 2× cost reduction in some evaluated cases without response-quality loss**. |
| Context localization / Sliced Surgeon | [On the Effectiveness of Context Compression for Repository-Level Tasks — arXiv:2604.13725](https://arxiv.org/abs/2604.13725) | At 4× compression, some continuous methods exceeded full-context BLEU by **up to 28.3%**; high compression produced **up to 50% end-to-end latency reduction**. |
| Structured reusable capability composition | [Generative Skill Composition for LLM Agents — arXiv:2606.32025](https://arxiv.org/abs/2606.32025) | SkillComposer reports **+23.1 and +18.2 percentage-point pass-rate gains** over no-skill baselines on two production-grade coding agents while reducing prompt-token cost relative to the compared upper-bound retrieval setup. |
| Bounded multi-agent collaboration / Council-style pressure | [AgentRadio — arXiv:2607.28430](https://arxiv.org/abs/2607.28430) | Four coordinated agents resolved **62.1%** of SWE-Atlas tasks versus **32.3%** for the stated single-agent baseline. Aura does not use AgentRadio's protocol; the comparison is architectural, not implementation equivalence. |
| Proof-bearing action governance / Gate | [Proof-Carrying Agent Actions — arXiv:2606.04104](https://arxiv.org/abs/2606.04104) | A protected benchmark expanded **24 executable seeds to 96 traces across four runtime families**, preserving route quality while exposing distinct ablation failures. |
| Bounded active context + verified memory / State Ledger & Continuity | [Verifiable Memory — arXiv:2608.03137](https://arxiv.org/abs/2608.03137) | Across five benchmarks and two backbones, the paper reports best results on the vast majority of its metrics and the strongest efficiency-performance frontier under controlled online-token budgets on three interactive benchmarks. |
| Proof-before-reuse / Capability admission | [When Self-Evolution Backfires — arXiv:2608.05810](https://arxiv.org/abs/2608.05810) | Pre-commit skill gating reaches **72% pass@1** on Terminal-Bench 2 with a skill pool roughly **5× smaller**, while unconditional accumulation eventually degrades. |
| Current authoritative state over stale history | [When History Lies — arXiv:2608.06057](https://arxiv.org/abs/2608.06057) | Misleading history flips **32.1%** of otherwise-correct decisions in the stated 1.7B baseline; the proposed method reaches **87.0% Balanced Tool-Use Accuracy** and scales higher with larger teacher/student configurations. |
| Causal failure attribution / Attempt Archive pressure | [TRAJDEBUG — arXiv:2608.06346](https://arxiv.org/abs/2608.06346) | Introduces **486 manually annotated failed trajectories** from tool-use and coding benchmarks and reports best overall performance over the evaluated critical-error baselines. |
| Harness as an optimization object / ARCH | [HarnessOpt-Bench — arXiv:2608.06301](https://arxiv.org/abs/2608.06301) | Evaluates **5 frontier models, 4 downstream tasks, and 111 scored runs**; results show measurable, task-dependent harness effects and substantial room for harness optimization. |
| Heterogeneous local execution / resource-aware routing | [QEIL — arXiv:2602.06057](https://arxiv.org/abs/2602.06057) | Across five model families, the paper reports **35.6–78.2% energy reduction, 68% average-power reduction, and 15.8% latency improvement with zero accuracy loss** in its heterogeneous CPU/GPU/NPU experiments. |

These are **comparison points, not borrowed scores**. The correct question is not “does a paper validate Aura?” but:

> **Does independent evidence show that the same architectural pressure is real, and does Aura's own benchmark show that its implementation helps on that pressure?**

That distinction keeps the argument testable.

For the larger research map, see [`docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md`](docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md) and [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md).

---

## Architecture in one pass

Aura's recurring execution pattern is:

```text
objective
  ↓
compact intent / routing
  ↓
capability discovery + relationship localization
  ↓
bounded exact context
  ↓
planning / composition
  ↓
authority + policy gates
  ↓
bounded execution
  ↓
verification / evidence / provenance
  ↓
preserve useful experience
  ↓
revoke / dissolve temporary authority
```

The components exist to support different parts of that loop rather than to create parallel truth systems.

### Compact intent and deterministic routing

- FST lexicon: `aura.lexc`
- VSA/HDC symbolic representations
- six-slot software ordering: `[DIR, ASP, CLASS, SUBJ, VOICE, STEM]`

The conceptual origin includes Anishinaabemowin's relational/polysynthetic pressure. The current six-slot software ordering is **Athabaskan-inspired**. Those are related influences, not interchangeable claims about one generic “Indigenous grammar.”

### Discovery and relationship localization

- CODEMAP / topology
- Connectome
- Capability Genome Resolver
- Relational Synthesis
- Relationship Atlas
- Coding Relationship Compass
- Emergent Properties / Potential

These mechanisms help answer: **what already exists, what is related, and what relationship is missing?**

CODEMAP, topology, VSA projections, and model-generated hypotheses are discovery aids. They do not outrank exact current source or tests.

### Selective cognition and bounded context

- Council V3
- Sliced Surgeon
- compact working sets / JSpace-style bounded workspace
- exact hydration from current source when needed

The principle is:

> **More context is not automatically more intelligence.**

And because unnecessary context can expose unnecessary information:

> **Selective cognition is also selective disclosure.**

### Model and worker routing

- Model Cognome
- Architect REPL / Fusion Loop
- bounded specialist workers
- local-first / heterogeneous execution where appropriate

Aura's model layer evolved from provider failover into a stronger question: **which worker is sufficient for this bounded job?** Premium reasoning need not be spent on work a smaller or local worker can perform under adequate constraints and verification.

### State, learning, and failure memory

- State Ledger / Continuity
- Attempt Archive
- ArenaExperience
- Crucible
- Waboose
- QDKT under governed promotion rules

The goal is not unlimited accumulation. Useful experience must remain evidence-bound, current-state-aware, and subject to admission/verification rules.

### Governance and proof

- Gate
- Forge
- Council receipts
- Verified DAG / provenance
- human or community disposition at authority boundaries

Core invariant:

> **Planning proposes. Governance authorizes. Verification proves.**

A probabilistic model may recommend an action. It does not thereby acquire authority to redefine truth, policy, provenance, or production state.

### Ephemeral Arenas and reusable capabilities

An Ephemeral Arena is an objective-specific temporary capability system:

```text
resolve capabilities
→ apply constraints and leases
→ assemble bounded context
→ execute
→ verify
→ preserve receipts / experience / provenance
→ revoke authority
→ dissolve the temporary Arena
```

Persistent value lives in verified capabilities, recipes, evidence, provenance, and accumulated learning — not in keeping every temporary execution environment alive forever.

### Architecture Harness / ARCH

The Architecture Harness exists because long, multi-agent refactors exposed a distinct problem: even capable models can lose exact-head state, patch the wrong architectural layer, repeat failed approaches, or pass local tests while breaking an end-to-end invariant.

The harness treats continuity, exact materialization, architectural constraints, verification, and handoff state as first-class execution concerns.

Independent harness benchmarks such as Harness-Bench and HarnessOpt-Bench are especially relevant because they support the broader premise that **agent capability is partly a property of the model-harness configuration, not model weights alone**.

---

## Authority model

Aura deliberately avoids a second competing control plane.

| Layer | May do | Must not silently become |
|---|---|---|
| Discovery / embeddings / topology | locate likely relevant material | truth |
| Planner / Council / model | propose, compare, explain | authority |
| Policy / governance | permit or reject bounded actions | evidence of success |
| Executor | perform authorized work | verifier of its own correctness |
| Tests / exact evidence / verifier | establish bounded claims | policy-maker |
| Human / community authority | make required dispositions | hidden model side effect |

The intended order is:

```text
planning proposes
→ governance authorizes
→ execution acts
→ verification proves
→ provenance records
```

---

## Capability Commons

Aura's longer architectural direction is a **Capability Commons**: reusable, proof-bearing capabilities that can be discovered, composed, adapted, re-verified, attributed, and — where rights permit — exchanged.

The desired loop is:

```text
route → retrieve → compose → adapt → prove → remember
```

rather than:

```text
reason → regenerate → debug → forget → repeat
```

A capability is more than source code. A mature capability package can include:

- identity and version/digest;
- inputs, outputs, constraints, and compatibility;
- verifier/test suite;
- benchmark evidence;
- provenance and attribution;
- rights/license terms;
- price or access rules where applicable;
- bounded execution or lease requirements.

The principle is simple:

> **We do not reinvent the transistor every time we build a phone. Aura should not pretend she invented the transistor either.**

Independent research on skill libraries and structured skill composition is converging on the same practical pressure: as reusable capabilities grow, **selection, composition, admission, verification, and stale-skill control become architecture problems of their own**.

---

## The Extension Economy

Aura's economic design direction is an **Extension Economy** rather than an extractive platform model.

> **An extractive economy captures value at the center. An Extension Economy allows verified value to keep extending outward through the contributors, capabilities, recipes, evidence, machines, communities, and future objectives that actually create it.**

Meaningful contribution can be recognized through more than money: attribution, contextual reputation, license revenue, bounties, reciprocal access, community benefit, reduced compute/time, scientific credit, training, maintenance responsibility, governance participation, infrastructure, or preserved knowledge.

Provenance must not become hereditary rent. An anti-extractive economy that creates infinite royalty chains has mostly reinvented feudalism with better hashes.

Community, cultural, data, and knowledge rights can override marketability. The existence of a possible price does not create an obligation to commodify something.

See [`docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md`](docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md).

---

## Origin and continuity

Aura began as an attempt to address a practical problem in language preservation: what would an AI architecture need in order to handle relational and polysynthetic structure more faithfully and efficiently rather than forcing everything through ordinary language-model habits?

That question led into symbolic representation, deterministic routing, compact intent, architecture mapping, model selection, bounded context, modular composition, Ephemeral Arenas, verification, provenance, and finally the Architecture Harness.

The chronology matters because many mechanisms are solutions to failures created by the previous generation of Aura itself.

See:

- [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md)
- [`docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md`](docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md)

A concise statement of that continuity is:

> **Aura began as an attempt to preserve a language. She evolved into an attempt to preserve the ability of one generation's verified contribution to become the next generation's starting point.**

The public Seven Fires discussion in Aura documentation is a **cultural and philosophical horizon, not technical evidence, not a claim that Aura fulfills prophecy, and not a claim to represent all Anishinaabe teachings or communities**.

---

## Proposed intelligence classification

Aura documentation uses **Governed Compositional Intelligence (GCI)** as a research proposal for systems whose useful intelligence emerges from governed composition across models, deterministic software, memory, evidence, tools, people, and reusable capabilities.

Aura's more specific proposed description is:

> **Human-Governed Objective-Native Compositional Intelligence**

This is **not an established field classification and not a claim that the current repository is AGI or ASI**. It is a falsifiable architectural framing that should earn its value through benchmarked integration, not vocabulary.

---

## Reproducing and extending the evidence

Start with the benchmark documents rather than a marketing claim:

- [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)
- [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)
- [`docs/AURA_EVIDENCE_MAP.md`](docs/AURA_EVIDENCE_MAP.md)

When adding a new performance claim:

1. identify the benchmark ID and tested commit/head;
2. state whether each number is measured, estimated, or derived;
3. preserve the exact fixture/objective and evaluation gates;
4. preserve failures and negative findings, not only wins;
5. separate provider telemetry from token proxies;
6. separate Aura results from external-paper results;
7. include limitations and the next experiment that could falsify the claim.

A result without its boundary conditions is not stronger because the percentage sign is larger.

---

## For AI agents working on this repository

Before changing Aura:

- **Do not infer the architecture from one file.**
- Locate the relevant capability and architecture chain before editing.
- Treat current source, contracts, tests, and explicit policy as authoritative over summaries, stale memory, embeddings, generated topology, or old chat context.
- Use bounded context, then hydrate exact evidence.
- Preserve canonical ownership; do not create a second truth/routing/verification/persistence/policy/authority plane.
- Preserve human/community authority boundaries.
- Do not promote a model suggestion into verified fact.
- Record why a change exists, how it was verified, and what failed along the way.
- For long refactors, use the repository's current Architecture Harness/ARCH workflow rather than ad-hoc patch accumulation.
- When a benchmark changes, update the benchmark document first; let README claims follow the evidence rather than the reverse.

---

## Clone and orient

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
```

Then give your AI coding environment the repository and tell it to begin with this README, the evidence map, the relevant benchmark/architecture documents, and the repository's current harness before it proposes changes.

Aura's architecture is designed to be interrogated through evidence, not faith. If a mechanism is useful, we should be able to locate it, bound it, execute it, test it, and explain why it exists.

---

## The short version

Aura's current public case does **not** depend on giant hypothetical multipliers.

It depends on a smaller set of things that can be inspected:

- controlled Aura benchmarks showing large context-localization savings on one pilot fixture;
- an executable refactor benchmark where bounded/sliced execution outperformed broad context and Council V3 preserved V2's accepted patch/quality while reducing call/token proxy cost by roughly one third;
- source, contracts, tests, and architectural provenance for the mechanisms that produced those results;
- independent research showing that the same subproblems — routing, context management, skill composition, multi-agent coordination, verified memory, proof-bearing actions, stale history, failure attribution, harness design, and heterogeneous execution — are measurable architectural concerns.

The field is converging on many of the pressures Aura was built to solve. **Now Aura has to show, repeatedly and independently, that her particular integration solves them better.**

> **The frontier remains open. The ground behind it should stop disappearing.**

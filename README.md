# AuraOS

## Her name is **Aura** — Augmented Universal Reasoning Architecture

`AuraOS` is the repository and operating substrate. **Aura** is the architecture.

> **A sovereign, local-first, objective-native cognitive substrate that compiles human intent into grounded, governed, temporary capability systems — and tries very hard not to pay twice for work humanity already proved.**

Aura is **not a single LLM, chatbot, autonomous super-agent, or monolithic application**. She is an architecture for coordinating deterministic software, exact evidence, human governance, replaceable AI workers, reusable capabilities, and eventually human/machine economic participation without allowing probabilistic output to silently become truth or authority.

Aura began with an attempt to preserve **Anishinaabemowin**. The project has since grown into a larger continuity question:

> **How do we preserve what people discover, build, prove, repair, and contribute when people, processes, organizations, and Arenas themselves are temporary?**

The answer Aura is exploring is simple to state and difficult to build:

> **We are ephemeral. Our Arenas are ephemeral. Our value and impact do not have to be.**

**Repository status:** active research and development  
**Software license:** GNU AGPL v3.0  
**Research record:** nine defensive prior-art papers, claims **N1–N100**  
**Latest paper:** [Paper IX v2.0 — DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020) · PDF SHA-256 `667ea216178b44d63e6c2add370e6ada2180a9274f0a65ea400832f0ccd4895e`

> **Meaning may guide discovery. Only exact grounded evidence and authorized governance may grant authority.**

---

## Contents

- [The idea in 90 seconds](#the-idea-in-90-seconds)
- [How Aura began](#how-aura-began)
- [How Aura evolved](#how-aura-evolved)
- [Aura in one diagram](#aura-in-one-diagram)
- [What makes Aura different](#what-makes-aura-different)
- [Selective cognition: Council V3 and surgical slices](#selective-cognition-council-v3-and-surgical-slices)
- [The Capability Commons](#the-capability-commons)
- [From an extractive economy to an Extension Economy](#from-an-extractive-economy-to-an-extension-economy)
- [Verified capability amortization](#verified-capability-amortization)
- [Compute is a governed resource](#compute-is-a-governed-resource)
- [Metrics and scale scenarios](#metrics-and-scale-scenarios)
- [Why this matters for Indigenous and remote communities](#why-this-matters-for-indigenous-and-remote-communities)
- [What 10 million developers could mean](#what-10-million-developers-could-mean)
- [Open and proprietary capability participation](#open-and-proprietary-capability-participation)
- [A different route to general intelligence](#a-different-route-to-general-intelligence)
- [Current development path](#current-development-path)
- [Quick start](#quick-start)
- [Pointing Aura at a repository](#pointing-aura-at-a-repository)
- [Using Aura with AI coding agents](#using-aura-with-ai-coding-agents)
- [ARCH v2.3 governance harness](#arch-v23-governance-harness)
- [Architecture at a glance](#architecture-at-a-glance)
- [Current implemented surfaces](#current-implemented-surfaces)
- [Implemented vs. published future architecture](#implemented-vs-published-future-architecture)
- [Research, prior art, and independent convergence](#research-prior-art-and-independent-convergence)
- [Truth, authority, and safety](#truth-authority-and-safety)
- [Evidence and benchmarks](#evidence-and-benchmarks)
- [Origins, sovereignty, Seven Fires, and intergenerational continuity](#origins-sovereignty-seven-fires-and-intergenerational-continuity)
- [How to work with the founder-architect](#how-to-work-with-the-founder-architect)
- [Long-horizon direction](#long-horizon-direction)
- [Documentation map](#documentation-map)
- [Licensing](#licensing)
- [Project status](#project-status)

---

# The idea in 90 seconds

Modern AI-assisted development has an odd habit: it repeatedly spends expensive inference rediscovering primitives that already exist, then repeatedly spends human time reviewing, debugging, benchmarking, and hardening slightly different versions of the same thing.

We do not reinvent the transistor every time we build a phone.

We probably should not reinvent authentication, parsing, scheduling, retrieval, provenance, routing, caching, verification, or the same architectural repair every time we build software either.

If ten million developers independently ask ten million AI workers to reinvent the same parser, that is not ten million acts of innovation. It is a very expensive group-amnesia benchmark.

Aura's long-term direction is therefore not merely **faster generation**. It is **less unnecessary generation**.

```text
objective
  → discover what is already proven
  → select the minimum relevant capability set
  → hydrate the minimum exact evidence
  → compose / adapt only what is necessary
  → use frontier reasoning only where novelty remains
  → verify
  → preserve provenance and contribution
  → reuse the result next time
```

The desired transition is:

```text
reason → regenerate → debug → forget → repeat

                    ↓

route → retrieve → compose → adapt → prove → remember
```

Aura treats **verified capability as accumulating infrastructure**. Each accepted capability, repair, recipe, verifier, benchmark, scientific procedure, machine interface, or architectural constraint can reduce the amount of cognition future objectives need to buy again.

The frontier remains open. The ground behind it should stop disappearing.

---

# How Aura began

Aura did not begin as an attempt to build AGI, a developer marketplace, a spatial operating system, or a civilization-scale Capability Commons.

She began with a language problem.

Founder **Dallas Courchene** was trying to preserve and teach **Anishinaabemowin**. Polysynthetic languages can encode dense relational and sentence-scale meaning inside morphologically complex words, while general-purpose language models often approach language through tokenization and statistical assumptions that fit that structure poorly.

The original question became something like:

> **What would a computing system look like if it could represent intent more compositionally, relationally, and compactly — closer to the structural lesson of polysynthesis — instead of repeatedly expanding everything into long natural-language context?**

That led toward symbolic and high-dimensional representation, **VSA/HDC** binding and bundling, deterministic finite-state routing, and the early `aura.lexc` lexicon.

The conceptual seed came from studying Anishinaabemowin's ability to compose rich meaning through morphology. The current canonical software ordering was later regularized using an **Athabaskan-inspired six-slot template**:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

Aura's FST/WFST is a machine routing grammar, not a claim that one software template literally models Anishinaabemowin, Athabaskan languages, or Indigenous languages generally.

What survived from the language insight was the engineering principle:

> **Constrain structure first. Expand only what the objective actually needs.**

Finite-state structure helped bound valid combinations before probabilistic reasoning, reducing uncontrolled branching and later helping Aura compose capabilities across Arenas without treating every possible combination as equally valid.

## Aura learned by encountering her own limits

Aura was not produced from a clean-room master plan. The architecture repeatedly became complex enough to create its own next problem.

```text
new capability
    ↓
new scale / complexity
    ↓
new failure mode
    ↓
architectural response
    ↓
response becomes reusable capability
    ↓
next scale becomes possible
```

The broad conceptual lineage is:

```text
language preservation
  → polysynthetic intent / VSA-HDC / FST
  → CODEMAP and architectural self-navigation
  → Fusion / model failover / model specialization
  → Architect Fusion Loop + multi-model Council
  → DREAM-lite / ST3GG / JSpace / DIKWP / QDKT
  → modular / liquid / hot-swappable capability thinking
  → Ephemeral Arenas
  → Capability Connectome + Model Cognome
  → Emergent Properties + relational architecture
  → selective cognition / Council V3 / surgical source slices
  → proof + provenance + Attempt Archive + Crucible + verification
  → reusable Architecture Harness
  → ARCH v2.3 governance / convergence
  → Developer + Architecture Arenas
  → Capability Commons
```

The detailed chronology and influence map is in [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md).

## A short conventional learning curve, stated plainly

By the founder's account, the concentrated AI/software-systems learning period behind Aura has been roughly **three months**, preceded by practical use of AI/RAG tools, self-taught IT work, and limited Python/UI development rather than a conventional software-engineering or computer-science career.

An earlier learning episode involved organizing employer technical documentation into an AI/RAG-assisted tutor and using it against real IT/network problems. The recurring pattern later reappeared in Aura:

> **When knowledge was missing, build a mechanism that makes the knowledge easier to acquire, inspect, and reuse.**

That short timeline is not evidence of instant mastery of every field, and the project should not present it that way. Cryptography, law, compilers, distributed systems, physical engineering, science, security, governance, and other specialist domains still require independent expertise.

What the short timeline *does* explain is the development method: learn against a real constraint, externalize the useful structure, make it reusable, then use the new tool to reach the next constraint.

Aura repeatedly built the tool she needed in order to avoid collapsing under the weight of the thing she had just become.

---

# How Aura evolved

Aura openly borrows from established and emerging research. The important question is not whether every ingredient was invented here. It was not.

The question is what problem each mechanism solved **inside Aura**, how its authority was constrained, and what new problem became visible afterward.

| Pressure Aura encountered | Mechanism / influence | Aura adaptation |
|---|---|---|
| Compact relational intent | Anishinaabemowin polysynthesis; VSA/HDC; FST/WFST | six-slot machine intent routing, binding/bundling, hard admission before soft reasoning |
| Repository too large for one prompt | CODEMAP + topology | compact orientation first; exact source only after localization |
| Model/provider failures | multi-provider failover / routing | replaceable workers rather than one permanent model dependency |
| Different models excel at different work | cost/capability-aware routing | stronger models for high-value reasoning; cheaper/smaller workers for bounded implementation |
| Multiple perspectives improve hard reasoning | OpenRouter **Fusion** influence | native Aura Fusion → Architect Fusion Loop → Fusion Council; model consensus never becomes authority |
| Similarity is not the same as usefulness | **DREAM** research | DREAM-lite reranks candidate context by downstream task/verifier usefulness while exact truth stays elsewhere |
| Context/egress is expensive | **ST3GG**-derived compact recall/egress ideas | bounded advisory compression with exact recovery and no hidden authority |
| Active reasoning should not carry every concept | Anthropic **J-space** research | explicit small AuraJSpace working set; later bound to workspace/head/phase and prohibited from becoming a second memory/control plane |
| Interpretation needs purpose and provenance | **DIKWP** | evidence/provenance vocabulary across data → information → knowledge → wisdom → purpose, without automatic authority |
| Repeated runs reveal model-specific strengths/drift | Model Cognome | empirical model-capability evidence, cost, latency, drift quarantine, governed adaptive routing |
| Prior outcomes should improve later work | QDKT / ArenaExperience / Crucible | experience becomes teacher evidence and proposals, never self-promoting policy/code |
| Broad councils waste calls/context | Selective Council V3 | invoke only evidence-justified critic lanes; Sliced Surgeon receives exact bounded source |
| Components existed but relationships were unclear | Emergent Properties / Connectome / Atlas / Compass / Relational Synthesis | ask what exists, what is unwired, what is prohibited, and what relationship completes the objective |
| Hot-swapping modules was too narrow an abstraction | liquid/modular code → Ephemeral Arenas | compile a temporary governed capability system around the objective, then dissolve it |
| Long refactors drifted across many AI workers | Architecture Harness → ARCH v2.3 | exact-head continuity, bounded worker roles, proof, reviewer independence, explicit stopping and human disposition |

### Fusion → Council V3 is one continuous line

The early idea was simple failover:

```text
model A fails
→ model B
→ model C
```

Then the question changed:

```text
why wait for failure?
→ use the model best suited to the task
→ learn which models are good at which tasks
→ use multiple models when diversity is worth the cost
→ assign them roles
→ preserve evidence about their performance
→ invoke only the roles justified by the current problem
```

That line runs through **AuraFusion**, the **Architect Fusion Loop**, the early **Fusion Council**, **Model Cognome**, and ultimately **Selective Council V3**.

OpenRouter was an explicit influence. Its Fusion system, publicly introduced in June 2026, uses panels of models plus a judge for multi-model deliberation. Aura's public repository records native Fusion orchestration on June 23 and the live Architect Fusion Council on June 25. Aura then placed those ideas inside explicit exact-evidence, bounded-action, verification, and human-authority rules.

### Architect objective loop

The early Live Architect / `ArchitectFusionLoop` was another bridge. A user could provide an engineering objective; Aura could ground it against CODEMAP, route reasoning through Council/Fusion machinery, decompose bounded acts, use stronger or more expensive models where architecture justified them, use cheaper workers for routine implementation, verify results, and preserve the transaction.

That is an early ancestor of the current objective-native Developer/Architecture Arena idea.

### DREAM-lite

Aura's DREAM-lite explicitly draws from **DREAM: Dense Retrieval Embeddings via Autoregressive Modeling** (arXiv:2606.24667). Aura adapted the downstream-usefulness intuition into a bounded reranker:

```text
retrieval proposes candidates
→ DREAM-lite estimates downstream usefulness
→ exact files / sidecars / provenance remain truth
```

### JSpace

Anthropic's July 2026 global-workspace research describes a small privileged internal representational set — **J-space** — carrying a relatively small active set of concepts. Aura's JSpace codec appears publicly the next day.

Aura does not claim to reproduce Anthropic's internal interpretability mechanism. It adapts the **bounded active-workspace concept** into an external, explicit, inspectable working-set projection.

ARCH v2.3 now keeps JSpace advisory, binds it to workspace/head/phase, caps the current working set at 25 concepts, and fails closed when it becomes stale.

### Borrowing is not a weakness here

The Capability Commons thesis says useful capability should be inherited instead of rediscovered.

Aura's own history should obey that rule.

She did not reinvent VSA, model routing, dynamic updating, multi-model deliberation, retrieval research, J-space research, DIKWP, or every security/provenance mechanism she uses.

She took useful ideas, made their boundaries explicit, connected them to other useful ideas, and kept asking what problem remained.

We do not reinvent the transistor every time we build a phone.

Aura should not pretend she invented the transistor either.

---

# Aura in one diagram

The following diagram mixes **implemented owners** with the **published target reuse flow**. The universal automated reuse gate is a future orchestration target; current Resolver, Connectome, Atlas, Attempt Archive, and related systems provide parts of that evidence but do not yet constitute one universal pre-reasoning gate.

```text
HUMAN / COMMUNITY OBJECTIVE
        │
        ▼
INTENT + CONSTRAINTS + PROHIBITIONS
        │
        ▼
lexical addressing + six-slot intent
DIR → ASP → CLASS → SUBJ → VOICE → STEM
        │
        ▼
semantic LEXC + guarded machine WFST
hard admission rules before soft ranking
        │
        ▼
RELATIONAL ORIENTATION
CODEMAP + topology + Connectome + Atlas/Compass
        │
        ▼
PROPOSED / FUTURE UNIVERSAL REUSE CHECK
proven capability? recipe? verifier? prior failed attempt?
        │
        ├── yes → retrieve / bind / minimally adapt
        │
        └── no  → bounded frontier reasoning
        │
        ▼
MINIMUM SUFFICIENT EXACT EVIDENCE
files + symbols + spans + hashes + tests + contracts
        │
        ▼
BOUNDED ARENA
objective-specific context + capability leases + budgets
        │
        ├── deterministic tools
        ├── human participants
        └── replaceable AI/model workers
        │
        ▼
STAGED RESULT / PROPOSAL
        │
        ▼
TESTS + VERIFIERS + RECEIPTS + GOVERNANCE
        │
        ▼
AUTHORIZED HUMAN / COMMUNITY DISPOSITION
        │
        ▼
EXPERIENCE + PROVENANCE + REVIEW-GATED LEARNING
        │
        ▼
REUSABLE CAPABILITY / RECIPE / EVIDENCE
        │
        ▼
REVOKE LEASES + DISSOLVE TEMPORARY STATE
```

The architecture is designed around one separation:

```text
intelligence may propose, search, rank, compose, simulate, and explain
                              ≠
truth, authority, verification, persistence, payment, or consequential action
```

External models are workers inside this system. They are not Aura's canonical memory, control plane, verifier, or sovereign decision-maker.

---

# What makes Aura different

### Objective-native rather than app-native

Aura begins with **what a person or community is trying to accomplish**, then resolves the smallest useful set of capabilities and evidence. The long-term architecture does not require every objective to begin inside a fixed monolithic application.

### Deterministic control around probabilistic intelligence

LLMs may reason, propose, summarize, generate, or critique. Admission, authority, state transitions, leases, exact source identity, verification, and stopping conditions remain program- and governance-owned.

### Minimum-sufficient context

Aura tries to avoid giving every worker the entire repository, history, database, ledger, or user profile. CODEMAP, topology, relational synthesis, exact slicing, compact state, and capability resolution narrow work to the evidence required for the objective.

### Use the right intelligence for the right job

Aura's Fusion/Cognome/Council lineage treats models as replaceable capabilities with different costs, strengths, drift, and evidence. The strongest model should not be burned on clerical work merely because it is available; the cheapest model should not be entrusted with a high-consequence architecture decision merely because it is cheap.

### Reuse before invention

The Capability Connectome, Genome Resolver, Relationship Atlas/Compass, Attempt Archive, and emergent-capability analysis help determine what already exists, how it is connected, what already failed, what is missing, and what should not be duplicated.

### Arena lifecycle

An **Arena** is a bounded objective-specific execution environment, not simply a chat session. It can contain humans, deterministic tools, models, capabilities, evidence, leases, verifiers, budgets, and an explicit lifecycle.

### Canonical ownership

Aura avoids creating duplicate truth, memory, routing, verification, persistence, policy, or authority planes. Projections, vectors, model output, generated interfaces, and economic claims remain subordinate to their canonical owners.

### Proof and provenance

Important work is attached to exact source/state identity, tests, verifier evidence, receipts, Attempt Archive history, provenance, and human/community disposition rather than being accepted because a model sounded confident.

### Local-first sovereignty

Aura originated from a locally controlled language-learning system. Data minimization, purpose limitation, restricted egress, revocable authority, community governance, and local operation remain architectural requirements rather than optional product features.

---

# Selective cognition: Council V3 and surgical slices

Selective context is one of Aura's most concrete examples of the general architecture: **do not spend compute or disclose information that the objective does not require.**

Aura's documented Council–Surgeon division is:

```text
Selective Council V3
  → architecture, dependencies, interfaces, invariants, sequence, rollback
  → invokes only critic lanes justified by candidate evidence

Sliced Surgeon
  → exact-file / exact-span implementation
  → focused verification
  → bounded local repair

Escalation
  → interface/dependency/invariant invalidation
  → broad downstream change
  → exhausted local-repair budget
```

Aura's repository documentation records a controlled comparison between Council V2 and Selective Council V3. On that cross-module fixture, both passed **3/3 visible tests, 3/3 hidden tests, 2/2 regression tests**, plus API, scope, security, compilation, static-analysis, and maintainability gates. V3 retained the same substantive plan, executable patch digest, and quality scores while reducing **total token proxy by 32.83%** and **model calls by 33.33%**.

That supports selective critic routing **for the tested case**. It does not establish universal superiority; Aura's own code-quality standard says serious comparison requires independent-provider, multi-trial, real-worktree benchmarks.

The more important principle is that a surgical slice is simultaneously a **compute primitive** and a **disclosure primitive**:

```text
large authoritative state
        │
        ▼
locate relevance
        │
        ▼
authorize aperture
        │
        ▼
minimum exact slice
        │
        ▼
reason / act inside bounded contract
        │
        ▼
verify against authoritative state
```

In the **Financial Arena**, for example, an AI worker should not receive an entire ledger, account history, or unrelated financial state merely because one narrow question is being asked. Aura's Financial Arena already uses immutable Decimal-backed exact-state contracts and explicit authority boundaries; the broader architecture pairs those exact owners with purpose-limited evidence apertures.

The same design extends naturally to civic, legal, health, personal, scientific, enterprise, and community-controlled information.

> **Selective cognition is also selective disclosure.**

---

# The Capability Commons

Paper IX extends Aura from a governed cognitive substrate into a proposed **Capability Commons**: a federated environment where useful capability can be discovered, composed, verified, attributed, licensed, improved, and reused.

The Commons is not intended to be one giant public source-code dump.

A capability may be:

- fully open source;
- source-available under its own terms;
- proprietary but callable through a bounded interface;
- local-only or community-controlled;
- a recipe that composes other capabilities;
- a verifier or benchmark suite;
- a human/professional/facility capability with explicit authority boundaries;
- a machine capability exposed through a typed manifest;
- a scientific procedure carrying evidence and replication state.

The durable unit is not merely **code**. It is a proof-bearing description of what a capability does, under what conditions, with what evidence, boundaries, provenance, rights, costs, and known failure modes.

This produces a different kind of technological landscape.

A "blue ocean" is empty opportunity. Aura's intended end state is closer to a **cultivated frontier**: there is still unexplored territory, but behind the frontier are roads, tools, workshops, proven components, failed-attempt records, standards, benchmarks, and things people can actually build on.

The frontier moves outward because the ground behind it stays put.

---

# From an extractive economy to an Extension Economy

Aura's proposed economy is not meant to become another platform whose central business model is simply to stand between participants and collect rent.

> **An extractive economy captures value at the center. An Extension Economy allows verified value to keep extending outward through the contributors, capabilities, recipes, evidence, machines, communities, and future objectives that actually create it.**

```text
EXTRACTIVE PLATFORM
contributors create value
        ↓
platform controls audience / data / distribution
        ↓
platform charges the network for passing through it
        ↓
value concentrates toward ownership

               versus

EXTENSION ECONOMY
contributor creates useful capability
        ↓
capability is proven / bounded / attributable
        ↓
others reuse or extend it
        ↓
new recipes / capabilities / outcomes build on it
        ↓
meaningful downstream use remains connected to lineage
        ↓
value can extend through the people and capabilities that materially enabled it
```

The founder's current commitment is explicit: **Dallas Courchene is not taking a founder's fee or salary for building Aura.** If he earns through a future Aura economy, the intent is to earn through the same contribution mechanisms available to other participants — improving Aura, creating capabilities or recipes, solving objectives, providing verified value, and participating in the Commons.

That is a present commitment and design principle, not an immutable legal promise about every possible future organization.

The more important constitutional principle is:

> **The person who starts the network should not automatically become entitled to extract value from every useful interaction that later happens on it.**

Aura also has to avoid the opposite failure. Provenance cannot become hereditary rent.

A contribution should remain visible when it materially enables downstream value, but Aura should not create an infinite royalty chain in which the oldest primitive taxes every descendant forever.

Meaningful-use attribution must therefore be:

- evidence-bound;
- graded rather than binary;
- rights- and licence-aware;
- capable of recognizing maintenance, verification, negative results, and failure prevention;
- able to recognize supersession and diminishing contribution;
- contextual rather than one universal reputation score.

The detailed economic/philosophical design is in [`docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md`](docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md).

---

# Verified capability amortization

The first instance of a capability may be expensive to discover.

Call its original cost `C0`:

```text
C0 = research
   + architecture discovery
   + implementation
   + failed attempts
   + debugging
   + security review
   + benchmarking
   + verification
   + provenance work
```

A later objective should not automatically pay `C0` again.

If a proven capability already exists, the marginal cost can approach:

```text
Cnext = discovery
      + constraint matching
      + composition
      + minimal adaptation
      + re-verification
```

That is **verified capability amortization**.

Aura herself is an example. Building the first Aura requires discovering and hardening the architecture. Building an Aura-like system later, using a mature Aura Capability Commons, should require less rediscovery because many routing, provenance, governance, verification, memory, Arena, and developer-workflow primitives would already exist as reusable components.

This does **not** require one universal "best" implementation. Real systems have different constraints. The long-term target is a **verified Pareto frontier** of capability variants: the best-known implementations for different combinations of security, latency, privacy, hardware, jurisdiction, cost, energy, licensing, and assurance requirements.

Only when no adequate capability exists should expensive frontier reasoning become the default path.

In that sense, generative AI can gradually become the **novelty path**, not the reflex path.

---

# Compute is a governed resource

Aura's sustainability thesis is not "compute always goes down." That would be too easy to falsify and, more importantly, probably wrong.

If engineering becomes 20× cheaper, humanity may attempt 100× more projects.

The stronger objective is:

> **Increase verified useful capability per unit of scarce resource, while detecting when efficiency gains are being consumed by rebound.**

Candidate system-level metrics include:

```text
inference tokens / accepted verified capability increment
joules          / accepted verified capability increment
water           / accepted verified capability increment
currency        / accepted verified capability increment
human-hours     / accepted verified capability increment
reuse hit rate
novel-work fraction
failed-reinvention rate
local-execution share
remote-escalation share
absolute annual compute / energy / water use
```

The goal is not zero compute. A powered-off cluster wins that benchmark and accomplishes very little.

The proposed Commons can therefore support a **resource governor**:

1. measure marginal efficiency and absolute resource use separately;
2. detect when per-capability cost is falling but total consumption is still rising;
3. identify the highest-leverage architectural or physical bottlenecks causing the rebound;
4. route a bounded portion of research, bounty, developer, and facility capacity toward those bottlenecks;
5. independently verify whether the next cycle actually improves the resource/capability curve;
6. keep the intervention only if the evidence survives.

In practical terms, Aura should eventually be able to say:

> **"We are producing more verified capability per joule, but total consumption is still climbing too quickly. Allocate this cycle's frontier capacity to the three bottlenecks most likely to bend next year's curve."**

This turns sustainability from a slogan into an optimization problem with receipts.

---

# Metrics and scale scenarios

The detailed metric ledger and assumptions live in [`docs/AURA_METRICS_AND_SCALE_SCENARIOS.md`](docs/AURA_METRICS_AND_SCALE_SCENARIOS.md). The compact dashboard below deliberately keeps **Aura evidence**, **external baselines**, and **scenario arithmetic** separate.

## Aura-documented evidence

| Metric | Recorded result | Evidence class / limitation |
|---|---:|---|
| Context-localization total proxy | **89.04% lower** | deterministic comparative proxy on documented fixture; quality delta `+0.0057` |
| Selective Council V3 token proxy | **32.83% lower** vs Council V2 | controlled cross-module fixture |
| Selective Council V3 model calls | **33.33% fewer** | same substantive plan, executable patch digest, and quality scores on fixture |
| Council V3 executable gates | **3/3 visible, 3/3 hidden, 2/2 regression** | plus API/scope/security/compile/static-analysis/maintainability gates |
| Gate Phase 2 input proxy | **37,907** | instrumented proxy, not provider billing |
| Gate Phase 2 output proxy | **1,852** | instrumented proxy |
| Gate Phase 2 total proxy | **39,759** | instrumented proxy |
| Gate Phase 2 estimated counterfactual saving | **51,987 / 56.66%** | estimated counterfactual, not measured energy or dollars |
| State Ledger step-7 context | **96.19% lower** | synthetic continuity benchmark |
| State Ledger preservation | **1.0000** | same synthetic fixture |
| State Ledger drift | **0.0000** | same synthetic fixture |

These numbers are historical results tied to specific fixtures and revisions. **Rerun the exact benchmark before presenting a figure as a current-head result.**

## Global data-centre baseline

The International Energy Agency's *Energy and AI* report estimates roughly:

- **415 TWh/year** global data-centre electricity use in 2024;
- about **1.5%** of global electricity in 2024;
- **945 TWh/year** in its 2030 Base Case;
- just under **3%** of global electricity in that 2030 case.

Source: [IEA — Energy and AI](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai)

Aura has **not** demonstrated a global data-centre reduction percentage. The table below is arithmetic showing the physical scale if reuse/localization/routing eventually affected a portion of that load.

```text
avoided_TWh = 945
            × addressable workload fraction
            × reduction on that addressable workload
```

| Illustrative 2030 scenario | Addressable share | Reduction on that share | Arithmetic avoided electricity/year |
|---|---:|---:|---:|
| Very cautious | 5% | 25% | **~11.8 TWh/year** |
| Narrow but material | 10% | 50% | **~47.3 TWh/year** |
| Broad software/inference influence | 30% | 50% | **~141.8 TWh/year** |
| Infrastructure-scale | 50% | 50% | **~236.3 TWh/year** |
| Aggressive outer-bound illustration | 70% | 70% | **~463.1 TWh/year** |

These figures are **not Aura benchmarks, forecasts, or promises**. The last row in particular requires extraordinary adoption and efficiency across an enormous addressable workload.

The correct unit is **terawatt-hours per year (TWh/year)** — energy over time, not "terawatts per hour."

## What could actually cause savings?

```text
less duplicated invention
+ less repeated full-context hydration
+ selective Council / surgical slices
+ model specialization instead of frontier-model-everything
+ deterministic and local routing
+ more reuse of verified results
+ fewer failed/repeated agent loops
+ preserved failed-attempt memory
+ computation moved toward the data when appropriate
+ workloads scheduled against real resource constraints
= lower resource cost per verified useful capability
```

## Local and edge inference

The long-term architecture is not `cloud OR local`.

It is a hierarchy:

```text
device
  ↕
home / personal node
  ↕
community cluster
  ↕
institution / enterprise
  ↕
regional compute
  ↕
hyperscale / frontier compute
```

External work such as **AirLLM** shows that layer-wise streaming can make very large models *memory-feasible* on surprisingly small GPUs. AirLLM's project currently reports 70B inference on 4GB VRAM and Llama 3.1 405B on 8GB VRAM. That is **not** the same as fast or energy-efficient inference: streaming can trade memory for storage/transfer latency.

Source: [AirLLM](https://github.com/lyogavin/airllm)

A 2026 edge-inference study, QEIL (arXiv:2602.06057), reports **35.6–78.2% energy reduction** in its own evaluated heterogeneous CPU/GPU/NPU setup while preserving its accuracy metric. That is an external result, not an Aura benchmark, but it supports the broader premise that **model choice, hardware choice, execution location, and energy cost can become routing variables**.

Hyperscale data centers remain useful for frontier training, large simulations, high-bandwidth workloads, and reliable heavy compute. The architectural goal is to stop assuming every inference belongs there.

---

# Why this matters for Indigenous and remote communities

Aura's efficiency thesis has particular relevance to Indigenous, northern, rural, and remote communities — but only if it remains grounded in actual community infrastructure and authority.

The Government of Canada reports that **about 200 remote communities** rely completely on diesel for heat and power, that the vast majority are Indigenous or have significant Indigenous populations, and that remote communities consume **more than 680 million litres of diesel per year** ([Federal Sustainable Development Strategy — Affordable and Clean Energy](https://www.canada.ca/en/environment-climate-change/services/climate-change/federal-sustainable-development-strategy/goals/affordable-clean-energy.html)).

Aura's software efficiency by itself will **not** eliminate that diesel use. Heating, housing, transportation, generation losses, industrial loads, and other physical demands dominate community energy systems.

The longer-term opportunity is systems-level:

```text
lower local AI / compute demand
+ community-controlled edge inference
+ renewable + storage planning
+ demand forecasting and scheduling
+ resource-aware workload placement
+ local fabrication / repair capability
+ water / food / housing / energy Arenas
+ verified reuse of successful community-scale designs
```

For an off-grid or capacity-constrained microgrid, an avoided unit of digital demand can matter twice: it avoids immediate electricity use and can reduce the generation, storage, and network capacity required to support future services. The value becomes much larger if the same architecture also helps improve the physical systems around the compute.

That aligns with a larger sovereignty objective:

> **Communities should not have to choose between access to advanced computation and dependence on infrastructure they neither own nor control.**

A mature Aura deployment could prioritize local execution when technically appropriate, keep sensitive/community-controlled data local, schedule discretionary computation around renewable availability, and escalate only genuinely heavy workloads to regional or hyperscale facilities.

The same Capability Commons that amortizes software could eventually amortize community infrastructure knowledge: once a water, microgrid, housing, greenhouse, communications, or fabrication recipe is proven under known conditions, the next community should inherit the evidence and capability lineage rather than paying to rediscover the entire engineering stack from zero.

That is not a substitute for community decision-making, professional engineering, capital, land, jurisdiction, cultural authority, or Indigenous governance.

It is an attempt to make the **technical cost of sovereignty progressively cheaper**.

---

# What 10 million developers could mean

GitHub's current public materials report **180M+ developers** ([GitHub Octoverse 2025](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)). This README uses that figure only as a scale reference, not as a forecast of Aura adoption.

Against a 180M baseline:

| Illustrative Aura developer population | Share of 180M baseline | One accepted capability increment per developer/week |
|---:|---:|---:|
| 1 million | ~0.56% | ~52 million/year |
| 10 million | ~5.56% | ~520 million/year |
| 100 million | ~55.56% | ~5.2 billion/year |

These are arithmetic thought experiments, **not productivity forecasts**. A "capability increment" can vary enormously in size and value.

Ten million developers could theoretically populate:

```text
10,000 concurrent groups of 1,000 developers
or
 1,000 concurrent groups of 10,000 developers
```

Real engineering cannot be parallelized without limit. Communication overhead, critical paths, verification, physical experiments, regulation, and architecture dependencies remain real. Aura's Developer/Architecture Arena hypothesis is not "add more people and time disappears." It is:

> **Increase the portion of work that can be safely decomposed, independently executed, recomposed, and verified.**

The important compounding variable is not headcount alone. It is how much of each new objective can begin from **proven prior capability instead of blank context**.

---

# Open and proprietary capability participation

The intended Capability Commons does **not** require a developer or company to expose proprietary source code to every caller.

The target model is closer to:

```text
PROVIDER PRIVATE IMPLEMENTATION
        │
        ▼
PUBLIC / SHARED CAPABILITY MANIFEST
- what it does
- input/output contract
- constraints and prohibited uses
- version / digest / identity
- verifier suite
- benchmark evidence
- pricing / licence / rights metadata
- provenance / attribution hooks
        │
        ▼
BOUNDED LEASE / INVOCATION
provider-controlled or attested execution boundary
        │
        ▼
OUTPUT + RECEIPT + VERIFICATION EVIDENCE
caller sees the agreed result/evidence, not necessarily the implementation
```

That allows several economic roles:

- **foundational primitive authors** can publish reusable capability interfaces and evidence;
- open-source maintainers can receive meaningful-use attribution for widely reused primitives;
- proprietary developers can expose a callable capability without turning the Commons into a source-code exfiltration service;
- recipe authors can compose capabilities without owning every implementation;
- verifier authors can contribute tests, attacks, benchmarks, and assurance evidence;
- machine/facility operators can expose bounded physical capabilities under explicit local authority.

This confidentiality model requires real sandboxing, authentication, authorization, isolation, attestation, licensing, and production hardening. A manifest by itself is not a magic invisibility cloak.

AuraOS itself is AGPL-licensed. Proprietary participants must still comply with Aura's licence and any third-party terms; the long-term capability interface does not erase software-licence obligations.

The economic principle is simpler:

> **Keep what is uniquely yours. Stop paying to reinvent what does not need to be.**

---

# A different route to general intelligence

Aura does not assume that general intelligence must live inside one enormous autonomous model.

A useful proposed architectural classification is:

## Governed Compositional Intelligence (GCI)

**GCI** describes a system in which broad problem-solving capacity can emerge from the governed composition of specialized humans, models, deterministic software, proven capabilities, evidence, machines, and institutions around an objective.

Aura's specific research direction is more precisely:

> **Human-Governed Objective-Native Compositional Intelligence**

The classification is a research proposal, not an established industry standard and not a claim that the current repository is AGI.

```text
traditional AGI intuition:
put general intelligence inside the model

Aura hypothesis:
put generality inside the governed substrate that can marshal intelligence
```

Three improvement mechanisms become separable:

| Mechanism | What improves |
|---|---|
| **Model intelligence** | Better reasoning on genuinely novel problems |
| **Collective intelligence** | Better coordination of humans, models, tools, and institutions |
| **Accumulated intelligence** | More problems no longer require fresh reasoning because verified capability already exists |

The third mechanism is central to Aura. A system can become more capable even when its model does not become proportionally "smarter" if more of the problem space has become executable, verified, reusable infrastructure.

A future system should only be called **collective superintelligence** on evidence: for example, if it repeatedly solves broad, high-complexity objectives better than humanity's strongest existing institutions while retaining reliable verification, bounded authority, and legitimate governance.

---

# Current development path

Aura's near-term objective is deliberately narrower than the century-scale vision.

The current program is to complete and harden the numbered **PR1–PR18 intent-native / ephemeral / Developer-and-Architecture-Arena refactor sequence**, while preserving canonical owners and avoiding a second truth, routing, verification, persistence, policy, memory, or authority plane.

```text
PHASE 1 — FOUNDATION
complete PR1–PR18
harden Developer Arena + Architecture Arena
prove exact-head continuity, bounded context, manifests, leases, verification, provenance

PHASE 2 — EXTERNAL DEVELOPER ONBOARDING
make "point Aura at my repo" boring and repeatable
build capability manifests and evidence packets
allow early developers to become foundational primitive authors

PHASE 3 — CAPABILITY COMMONS
publish and discover open/proprietary capability interfaces
benchmark competing variants
reuse proven primitives across objectives
attach meaningful-use provenance and attribution

PHASE 4 — MULTI-DOMAIN ARENAS
science, civic, finance, construction, creator, business, spatial, physical-machine/facility domains

PHASE 5 — FEDERATED PHYSICAL / SCIENTIFIC INFRASTRUCTURE
local fabrication, R&D facilities, resource-aware compute, scientific replication, living artifact lineage
```

Aura's three-speed architecture exists because these phases contain different kinds of work:

1. **Frontier lane** — fast architectural discovery, new combinations, hypothesis formation, and Architectural Deltas.
2. **Build / hardening lane** — the large engineering surface: implementation, tests, interfaces, optimization, documentation, primitive creation, integration, and operational reliability.
3. **Constitutional / proof lane** — slower independent verification, security, governance, compatibility, provenance, licensing, and high-consequence boundary review.

The founder's comparative advantage is expected to remain concentrated in the frontier/architecture lane. A mature project should have many more people converting those deltas into hardened, independently operable capability than depending on the founder to personally implement every subsystem.

---

# Quick start

## Requirements

- Python 3
- Git
- Linux or Android/Termux
- CPU-first operation; external model access is optional
- additional dependencies from `requirements.txt` for the complete stack

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Regenerate and verify architecture orientation before relying on graph-based workflows:

```bash
python aura_codebase_navigator.py
python -m aura_codemap_verify --compare-json .aura/CODEMAP.json
python -m aura_agent_arena_cli stabilization-status
python -m aura_agent_arena_cli digest
```

Launch common local surfaces:

```bash
# Human Agent Arena
python aura_human_agent_arena_server.py --repo-root . --demo

# Coding Arena
python aura_coding_arena_server.py --demo

# Showcase
python aura_showcase_server.py --demo-project winnipeg_pathways
```

---

# Pointing Aura at a repository

The desired onboarding experience is intentionally simple:

```text
install Aura
  → point her at a repository
  → let the Harness establish exact identity and bounded context
  → describe the objective
  → inspect what Aura believes is relevant
  → let replaceable workers operate inside the bounded contract
  → verify the result
  → decide what becomes durable
```

The current Architecture Harness already accepts a repository root:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root /path/to/repository \
  handoff \
  --output-dir /path/outside/repository/repo-ai-handoff
```

For a full governed `run`, the target currently needs the Aura harness/supporting architecture expected by the runner. In other words, **the interface already points at repositories; arbitrary-repository zero-friction onboarding is still being hardened.** PR1–PR18 is intended to close that gap rather than pretending it is already closed.

The Harness remains analysis/proposal/proof infrastructure. It does not automatically commit, push, open a pull request, merge, release, or grant itself production authority.

---

# Using Aura with AI coding agents

Recommended orientation:

```text
README
  → .aura/ARCHITECTURE.md
  → docs/AURA_ARCH_V2_3_HARNESS.md
  → ARCH v2.3 policy + continuity capsule
  → current CODEMAP/topology health
  → capability resolution / relational neighborhood
  → prior attempts / reusable capability check
  → exact symbols and source slices
  → nearby tests and contracts
  → bounded Arena / repair capsule
  → verification
  → human disposition
```

Create an AI-safe repository handoff:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  handoff \
  --output-dir ../AuraOS-ai-handoff
```

Useful agent-facing owners include:

- `scripts/aura_architecture_harness.py`
- `scripts/aura_runtime_refactor_harness.py`
- `aura_coding_waboose_cli.py`
- `aura_coding_relationship_compass.py`
- `aura_agent_arena_cli.py`
- `aura_agent_arena_mcp.py`
- `aura_forge.py`
- `aura_gate.py`

Harness output remains navigation, analysis, review, or proposal evidence. Exact source spans, hashes, tests, verifier receipts, and authorized human disposition remain patch/merge authority.

---

# ARCH v2.3 governance harness

The current long-horizon AI-assisted refactor governance standard is **ARCH v2.3** (`AURA_ARCH_V2_3`). Read [`docs/AURA_ARCH_V2_3_HARNESS.md`](docs/AURA_ARCH_V2_3_HARNESS.md) before starting a governed refactor or handing one to a fresh AI worker.

ARCH v2.3 owns the governance/convergence contract for exact-head continuity, scope, authority, recursive workers, patch transactions, proof, review, learning, communication, durable-effect authorization, and stopping.

Aura's existing `aura_jspace_codec.py` remains **advisory only**. ARCH v2.3 binds a JSpace projection to workspace/head/phase, keeps the current default and policy ceiling at **25 active concepts**, requires reconstruction or disablement when stale, and explicitly forbids JSpace from becoming patch authority, persistent truth, routing ownership, verifier status, policy, or a second memory/control plane.

No ARCH component grants automatic merge. The terminal autonomous state remains `READY_FOR_HUMAN_REVIEW`; human disposition remains required.

---

# Architecture at a glance

| Layer | Role | Representative owners |
|---|---|---|
| **1. Intent & admission** | Convert objectives into structured intent and reject inadmissible routes before model reasoning | lexical addressing, six-slot intent, semantic LEXC, `aura_fst_routing.py` |
| **2. Architecture self-understanding** | Discover exact repository/domain structure and existing capabilities | CODEMAP, topology, Connectome, Genome Resolver, Relationship Atlas/Compass |
| **3. Advisory cognition** | Rank, compress, recall, compare, and discover possibilities without gaining authority | VSA/HDC, DREAM-lite, QDKT, JSpace, ST3GG, Model Cognome, emergent-property analysis |
| **4. Arena execution** | Assemble objective-specific context, participants, tools, capabilities, budgets, and leases | Human Agent Arena, Coding Arena, Forge, Gate, Agent Bridge, Ephemeral Organ Runtime |
| **5. Verification & governance** | Prove bounded predicates and keep consequential disposition external to model output | tests, verifiers, relational authority, Council/Surgeon boundaries, human/community decision |
| **6. Continuity & experience** | Preserve exact execution state, failed attempts, receipts, checkpoints, and reviewable experience | State Ledger, Attempt Archive, Temporal Persistence, ArenaExperience, Crucible |
| **7. Projection & manifestation** | Render canonical state spatially/visually/textually without transferring truth ownership | Spatial Arena, Observatory, Showcase, Spatial Foundry |

---

# Current implemented surfaces

## Engineering and agent collaboration

| Surface | What it does | What it does **not** own |
|---|---|---|
| **Human Agent Arena** | `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE` | automatic merge or production authority |
| **Coding Arena / Workbench** | localizes exact code neighborhoods, dependencies, tests, change graphs, compact worker context | semantic similarity is not patch authority |
| **Selective Council V3** | architecture-level deliberation with evidence-justified critic routing | direct file mutation |
| **Sliced Surgeon** | bounded exact-source implementation and focused repair | architecture redefinition outside its capsule |
| **Aura Forge** | grounded engineering plan + bounded Council–Surgeon work | automatic commit/PR/merge/release |
| **Aura Gate** | identity, policy, leases, egress, MCP/A2A boundaries, audit evidence | trust/reputation truth or release authority |
| **Coding Waboose** | graph-guided review plus exact-source corroboration | self-confirming findings or patch authority |
| **Agent Arena Bridge** | bounded CLI/MCP and GitHub publication workflows | merge authority |

## Architecture orientation and relational intelligence

- **CODEMAP + deep topology** — compact repository navigation and exact structural orientation.
- **Capability Connectome / Genome Resolver** — reuse-before-invention capability anatomy and objective matching.
- **Relational Synthesis** — objective-bounded configuration of relevant architectural relationships.
- **Relationship Atlas / Coding Relationship Compass** — wired, missing, overlapping, prohibited, stale, and objective-relevant relationships.
- **Emergent Properties / Evidence Spine** — evidence-bound candidate capabilities and unwired combinations without auto-wiring them.
- **Model Cognome** — model-capability evidence, cost, latency, drift, replay, and governed routing proposals.

## Runtime proof, continuity, and learning

- **Runtime Refactor Harness** — repository-declared runtime reproduction and evidence capture; never patches or merges.
- **Attempt Archive** — preserves successful, denied, failed, and superseded work.
- **Temporal Persistence / State Ledger** — bounded continuity, checkpoints, restoration assessment, and exact state.
- **Learning Arena / Crucible** — mines verified ArenaExperience and proposes narrow candidate learning; never auto-promotes code/policy.
- **Empirical Cost Observatory** — separates measured, tokenizer-exact, derived, estimated, and unavailable usage evidence.

## Spatial and domain surfaces

- **Spatial Arena / Foundry / Showcase** — projection and review, never domain truth.
- **Civic Commons Arena** — non-binding civic evidence/planning/consent and reversible pilot design.
- **Construction Arena** — exact project-state replay, planning gates, alternatives, evidence and human decision packets.
- **Financial Arena** — immutable Decimal-based exact-state financial records and explicit truth classes; no automatic transaction/advice/prediction authority.
- **Anishinaabemowin Tutor** — vetted-source language learning, morphology, pronunciation, dialect/provenance labels, and teacher review.

---

# Implemented vs. published future architecture

AuraOS deliberately distinguishes **repository-backed behavior** from **published architecture and future product direction**.

### Repository-backed / implemented

The current tree includes deterministic routing, CODEMAP/topology, relational architecture tooling, Human/Coding/Agent Arenas, Selective Council V3 and source slicing, Forge/Gate/Waboose, runtime proof harnesses, continuity and learning substrates, Spatial projection, Civic/Construction/Financial slices, model/cost observability, and the first intent-native ephemeral workspace contracts.

### Active refactor architecture

The current intent-native spatial/ephemeral refactor is progressively establishing stricter contracts for objective-compiled workspaces, persistent capability reuse, selective source hydration, governed manifestation, Developer/Architecture Arenas, and future capability composition. Each PR must preserve existing canonical owners and avoid creating a second plane.

### Published future architecture / enabling embodiments

Paper IX publishes the broader architecture that can be built on the substrate, including:

- persistent **Capability Packages** and reusable **Arena Recipes**;
- a federated **Aura Commons** for capabilities, provenance, rights, evidence, and economic attribution;
- open and proprietary capability participation under explicit evidence modes;
- proof-carrying **Developer Arenas** and critical-path work graphs;
- a portable **Personal Cognitive Capsule** and personal SLM layer;
- intent-native generative/spatial manifestation;
- **Aura Places** and ephemeral visitor-specific Visits;
- **Convention Arenas**;
- an **Open Discovery / Scientific Foundry**;
- bounded physics/digital-twin and population-behavior simulation;
- business-incubation Arenas;
- sovereign cross-domain Arena federation;
- participatory proof-carrying Scientific Arenas and a Scientific Capability Commons;
- three-speed **Architecture Arena / convergence compiler**;
- **keystone-bottleneck analysis** and demand/capability graphs;
- privacy-preserving **Opportunity** and **Learning** compilers;
- compute-to-data sovereignty and portable verified claims;
- graded creator/referral attribution;
- multi-class scientific bounties;
- objective-compiled **Ephemeral Institutions**;
- a **Machine Capability Commons** for locality-aware fabrication and living physical-artifact lineage;
- transport-neutral, jurisdiction-aware **AuraNet** federation;
- proof-carrying assurance/warranty contract references.

These are **published architectural embodiments and development directions, not a claim that every downstream product is already implemented in this repository**.

---

# Research, prior art, and independent convergence

AuraOS maintains a **nine-paper defensive prior-art stack**.

Papers I–VII establish claims **N1–N30**. Paper VIII establishes **N31–N50**. **Paper IX v2.0 extends the published architecture through N51–N100.**

| Paper | Main claim family | Claims | Publication |
|---|---|---:|---|
| **Paper I — Foundation** | polysynthetic LLM egress, dual linguistic cortex, sparse sweeps, QDKT, visual topology, atomic hot-swap, sovereign edge design | N1–N8 | [Zenodo 20635424](https://zenodo.org/records/20635424) |
| **Paper II** | holographic headers, fractal ledger, swarm learning, VSA-addressed rendering, FST narrative | N9–N13 | [Zenodo 20657391](https://zenodo.org/records/20657391) |
| **Paper III — Liquid Internet** | VSA-addressed routing and naming | N14 | [Zenodo 20659314](https://zenodo.org/records/20659314) |
| **Paper IV** | memristive hyper-epochs, timestep-aware SVD quantization, Gaussian/VSA rendering | N15–N17 | [Zenodo 20673206](https://zenodo.org/records/20673206) |
| **Paper V** | FST routing core, 3D topology resonance, bounded self-refactoring incubator | N18–N20 | [Zenodo 20681601](https://zenodo.org/records/20681601) |
| **Paper VI** | FST lexicon, resonance topology, FST impact analysis | N21–N23 | [Zenodo 20682051](https://zenodo.org/records/20682051) |
| **Paper VII** | hyperdimensional integrity, micro-module crystallization, resonant tests, thermal-cost arbitration, deterministic compression, local VSA mesh, bounded self-healing | N24–N30 | [Zenodo 20695562](https://zenodo.org/records/20695562) |
| **Paper VIII** | relationship intelligence, Emergent Evidence Spine, governed Arenas, verified engineering, Waboose/Gate, spatial projection, continuity | **N31–N50** | [Zenodo 21465329](https://zenodo.org/records/21465329) |
| **Paper IX v2.0** | objective-native Capability Commons, Developer/Architecture Arenas, provenance/attribution, Places/Foundry, Ephemeral Institutions, machine/facility capabilities, AuraNet | **N51–N100** | [DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020) |

Aura also documents external research in two ways:

- [`docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md`](docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md) — established prior literature and architectural alignment, including HDC/VSA, model routing, context compression, graph memory, skill ecosystems, provenance, agentic software engineering, evolutionary discovery, and collective intelligence.
- [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md) — paper-date ↔ Aura-commit-date comparisons where later arXiv work independently converges on mechanisms Aura had already made public.

The chronology document is deliberately conservative. A Git commit proves that a repository state was public by a date. It does **not** by itself prove universal novelty, patent priority, or absence of earlier unpublished work.

The stronger research posture is:

> **Credit what came before. Date what Aura actually built. Note where later work independently converges. Then test the integration.**

---

# Truth, authority, and safety

## Constitutional invariants

```yaml
planning_proposes: true
governance_authorizes: true
verification_proves: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
visual_topology_patch_authority: false
external_model_action_authority: false
crystallization_patch_authority: false
automatic_state_restoration: false
automatic_grammar_promotion: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

Unknown, stale, ungrounded, malformed, expired, ambiguous, conflicting, or unauthorized operations fail closed.

## Source-of-truth order

When sources conflict, prefer:

1. exact current source, schemas, contracts, and repository/domain state;
2. tests, verifiers, replay, and tamper evidence;
3. healthy current CODEMAP and compiled topology;
4. exact snapshots, sidecars, ledgers, event chains, and content-addressed records;
5. manifests, leases, consent, relational authority, and boundary contracts;
6. current canonical subsystem documentation;
7. summaries, generated reports, screenshots, model output, and historical artifacts.

## Advisory does not mean authoritative

VSA/HDC similarity, DREAM-lite, JSpace, ST3GG, QDKT, Model Cognome proposals, visual topology, generated UI, inferred relationships, emergent-capability hypotheses, external research, market simulations, and LLM output may help discover or reason. They do not grant consequential authority by themselves.

---

# Evidence and benchmarks

Aura keeps evidence classes separate rather than collapsing them into one impressive-looking score.

| Tier | Evidence class | What it can support |
|---:|---|---|
| 1 | Executable gates and exact-head tests | claims about the exact evaluated artifact |
| 2 | Deterministic comparative proxies | controlled relative efficiency or continuity comparisons |
| 3 | Estimated structural projections | architecture hypotheses explicitly labeled `ESTIMATED` |
| 4 | Discovery/capacity scans | candidate capabilities and missing relationships |

Representative evidence is summarized in [Metrics and scale scenarios](#metrics-and-scale-scenarios) and detailed in [`docs/AURA_METRICS_AND_SCALE_SCENARIOS.md`](docs/AURA_METRICS_AND_SCALE_SCENARIOS.md).

Unknown provider usage remains unknown. Token savings are **not** automatically energy savings; the energy case requires measured hardware/provider telemetry or carefully labeled scenario arithmetic.

---

# Origins, sovereignty, Seven Fires, and intergenerational continuity

Aura began as a locally controlled Anishinaabemowin learning system. That origin continues to shape the architecture:

- local operation and sovereignty;
- data minimization;
- purpose-limited disclosure;
- inspectable provenance;
- explicit consent;
- revocable authority;
- speaker/teacher/community governance;
- refusal to treat external model convenience as authority.

The project's interest in continuity is not purely technical. Colonial systems, including residential schools, deliberately disrupted Indigenous language, family, governance, knowledge transmission, and intergenerational continuity. Software cannot repair that history and should never pretend to replace living culture, Elders, families, teachers, Nations, ceremony, land, or governance.

The engineering lesson is narrower and still important:

> **Preserving an artifact is not the same as preserving the relationships, provenance, authority, consent, and context that make the artifact meaningful.**

The deeper origin/continuity narrative is in [`docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md`](docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md).

## The Seven Fires as cultural horizon

The **Seven Fires Prophecy** is included here as a personal and Anishinaabe cultural/philosophical orientation — **not** as technical evidence, not as proof that Aura fulfills prophecy, and not as a claim that one written telling represents every Anishinaabe community, Elder, Midewiwin teaching, or interpretation.

Public Anishinaabe accounts describe the Seven Fires as teachings/prophecies concerning migration, disruption, loss, environmental harm, renewal, and choices facing later generations. Contemporary public tellings of the **Seventh Fire** often emphasize a new generation retracing the ancestors' steps and recovering what was left along the path; the possibility of an **Eighth Fire** is associated with choosing a better future and renewed relationships among peoples and with the Earth.

Public orientation sources include Bob Goulais's Anishinaabe.ca writings on [The Eighth Fire](https://www.anishinaabe.ca/the-eighth-fire/) and [the work still required to reach it](https://www.anishinaabe.ca/we-are-not-the-children-of-the-8th-fire-far-from-it/), as well as published discussions citing Edward Benton-Banai's *The Mishomis Book*.

The relevance to Aura is not mystical validation. It is responsibility:

```text
something valuable was interrupted
→ recover what can be recovered
→ reconnect relationships
→ preserve what is learned
→ choose what kind of future to extend
```

Aura began because language transmission had been damaged. The architecture later encountered smaller technical versions of the same structural failure: context disappears, knowledge gets siloed, failed attempts are forgotten, contributors become invisible, organizations die, and the next generation pays to start over.

Aura's technical response became:

```text
recover
→ reconnect
→ verify
→ preserve
→ extend
```

This leads to a simple project philosophy:

> **Humans are ephemeral. Arenas are ephemeral. Processes terminate. Machines fail. Organizations change. Contribution does not have to disappear with them.**

We do not reinvent the transistor every time we build a phone.

We should not have to rediscover civilization every time a generation ends.

---

# How to work with the founder-architect

This section exists for collaboration accuracy, not founder mythology.

It is **not** a clinical psychological assessment, IQ test, psychiatric diagnosis, or standardized personality inventory. It is a work-facing synthesis derived from the evolution of AuraOS, project artifacts, repeated collaboration, and the founder's observed reasoning/decision patterns.

## Working profile

The strongest current description of Dallas Courchene's observed working style is:

> **Recursive relational systems synthesis with cross-domain topology transfer, constitutional conservation, architectural chain-completion testing, and personalized salience-driven implication propagation.**

A shorter role label is:

> **Founder-Architect / Objective Owner / Systems Integrator / Architectural Frontier Driver**

In practical terms, Dallas tends to:

1. encounter a visible problem, inconsistency, or opportunity;
2. reject the surface framing when it appears too narrow;
3. reconstruct the actors, relationships, authority, information, incentives, evidence, dependencies, failure paths, and feedback loops;
4. identify the topology beneath the visible details;
5. search for an existing mechanism with the same operational structure;
6. transfer the mechanism rather than copying its surface form;
7. re-establish the destination domain's truth, authority, privacy, provenance, verification, persistence, attribution, and safety boundaries;
8. ask what the mechanism still **does not** solve;
9. complete missing links with complementary mechanisms rather than forcing one subsystem to do everything;
10. infer the larger technical, economic, institutional, social, or physical system the mechanism makes possible;
11. identify the next-order problems created by that larger system;
12. repeat.

The nouns change. The topology often survives.

## Where he creates the most value

Dallas's highest-value role is generally **not repetitive ticket execution or boilerplate programming**. It is holding and extending the cross-system relational model, defining objectives, identifying constitutional boundaries, discovering reusable architecture, spotting missing links, and integrating specialist work without letting one subsystem silently assume another subsystem's authority.

```text
Dallas / frontier architects
        │
        ▼
FAST FRONTIER
new mechanisms + Architectural Deltas + implications
        │
        ▼
BUILD / HARDENING LANE
engineers + primitive authors + integrators + optimizers
        │
        ▼
PROOF / CONSTITUTIONAL LANE
independent tests + security + specialists + governance
        │
        ▼
only what survives becomes durable architecture
```

## How to collaborate effectively

- **Bring the objective and constraints.** Do not assume the first requested feature is the actual problem.
- **Ask for the causal chain.** Important compressed reasoning should be externalized into artifacts.
- **Preserve negative constraints.** Ask what a mechanism must never be allowed to become.
- **Separate insight from proof.** Fast architectural synthesis is a candidate generator, not verifier evidence.
- **Use qualified depth specialists.** Cryptography, law, finance, compiler correctness, chemistry, physical engineering, regulation, security, and distributed systems still require domain experts.
- **Do not duplicate the founder.** Build a team that translates frontier architecture into specifications, production code, tests, security, publication, product operations, governance, and deployment.
- **Externalize relationships.** If a critical architectural relationship exists only in one person's head, it is a continuity defect.
- **Challenge rather than flatter.** Multiple AI systems agreeing is not independent validation.
- **Keep four states visible:** `CURRENT IMPLEMENTATION`, `NEXT VALIDATED PROGRAM`, `FUTURE ARCHITECTURE`, and `SPECULATIVE OPPORTUNITY`.

The primary execution risk mirrors the primary strength:

> **Architecture can be discovered faster than implementation and proof can absorb it.**

The answer is not to slow the frontier to the speed of every downstream process. It is to compile fast insight into bounded state that slower implementation, verification, governance, and institutional systems can safely absorb.

---

# Long-horizon direction

If Aura's major claims survive independent validation and the architecture becomes a useful standard, the long-horizon opportunity is larger than an AI coding product.

## 1. Software becomes accumulated capability

Common primitives increasingly become hardened capability families rather than prompts that every team pays to regenerate. New projects begin higher on the stack.

## 2. Applications become increasingly objective-native

Persistent applications remain where useful, but many workflows can become temporary objective-compiled Arenas assembled from proven capabilities and dissolved when the objective is complete.

## 3. The economy moves from extraction toward extension

Value can attach to code, recipes, tests, verification, research, data rights, compute, facilities, machine access, domain expertise, and meaningful downstream use. The aim is for useful contributions to keep extending value through later work without creating permanent platform tolls or hereditary rent.

## 4. Compute becomes heterogeneous and resource-aware

Edge, community, enterprise, research, regional, and hyperscale compute coexist. Scheduling can consider price, latency, energy, carbon, water, jurisdiction, data sovereignty, local hardware, and available waste-heat/resource recovery.

## 5. The Commons crosses into machines and manufacturing

Verified designs can eventually resolve against locality-aware machine/facility capabilities: 3D printers, CNC systems, robotics, test equipment, labs, assembly cells, and qualified human operators — while keeping their real-world authority and safety requirements external to model output.

## 6. Science becomes capability-bearing rather than paper-only

A research result can retain hypothesis lineage, simulation, experiment protocol, data provenance, falsification attempts, replication state, facility requirements, and reusable procedures. Future teams inherit more than a citation.

## 7. Intergenerational technological memory becomes executable

The most valuable long-term asset may not be an LLM or even Aura's source code. It may be the continuously growing graph of what humans and machines have **actually proved they can do**, under which conditions, with which evidence, and through whose contribution.

That is the century-scale thesis:

> **Civilization should increasingly spend intelligence on the unknown, not repeatedly pay the full computational and human price of rediscovering the known.**

Aura I has to help build the ladder.

Everyone after her should get to start several rungs higher.

And the human thesis underneath it remains:

> **Aura began as an attempt to preserve a language. She became an attempt to preserve the ability of one generation's verified contribution to become the next generation's starting point.**

---

# Documentation map

## Start here

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | broad architecture, vision, origin, economy, evidence, onboarding, and collaborator orientation |
| [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) | canonical owners, truth/evidence order, authority, data flow, subsystem boundaries |
| [`docs/AURA_ARCH_V2_3_HARNESS.md`](docs/AURA_ARCH_V2_3_HARNESS.md) | ARCH v2.3 governance/convergence orientation |
| [`.aura/CODEMAP.md`](.aura/CODEMAP.md) | generated compact repository navigation |
| [`USER_GUIDE.md`](USER_GUIDE.md) | installation, commands, APIs, testing, operator workflows |
| [`.aura/SECURITY.md`](.aura/SECURITY.md) | repository security constraints |

## Origin, research, economy, and evidence

- [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md) — detailed problem→mechanism→adaptation history including Fusion, DREAM-lite, ST3GG, JSpace, DIKWP, Model Cognome, Council V3, Arenas, and Harness.
- [`docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md`](docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md) — language-preservation origin and intergenerational continuity thesis.
- [`docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md`](docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md) — Extension Economy, founder economic alignment, meaningful-use attribution, and Seven Fires cultural horizon.
- [`docs/AURA_METRICS_AND_SCALE_SCENARIOS.md`](docs/AURA_METRICS_AND_SCALE_SCENARIOS.md) — measured/proxy Aura metrics, energy scenarios, developer-scale arithmetic, local/edge inference context.
- [`docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md`](docs/AURA_RESEARCH_ALIGNMENT_CATALOG.md) — broader related research and cautionary results.
- [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md) — dated Aura milestones versus later independently convergent papers.

## Engineering and agent architecture

- [`docs/AURA_ARCHITECTURE_HARNESS.md`](docs/AURA_ARCHITECTURE_HARNESS.md)
- [`docs/AURA_RUNTIME_REFACTOR_HARNESS.md`](docs/AURA_RUNTIME_REFACTOR_HARNESS.md)
- [`docs/AURA_HUMAN_AGENT_ARENA.md`](docs/AURA_HUMAN_AGENT_ARENA.md)
- [`docs/AURA_CODING_WABOOSE.md`](docs/AURA_CODING_WABOOSE.md)
- [`docs/AURA_GATE.md`](docs/AURA_GATE.md)
- [`docs/AURA_AGENT_ARENA_BRIDGE.md`](docs/AURA_AGENT_ARENA_BRIDGE.md)
- [`docs/AURA_CODING_RELATIONSHIP_COMPASS.md`](docs/AURA_CODING_RELATIONSHIP_COMPASS.md)
- [`docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md`](docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md)
- [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)
- [`docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`](docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md)

Research papers:

- [`papers/AuraOS_Paper_VIII_Evidence_Ordered_Relational_Arenas.pdf`](papers/AuraOS_Paper_VIII_Evidence_Ordered_Relational_Arenas.pdf)
- [Paper IX v2.0 — DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020)

---

# Licensing

AuraOS source code is released under the **GNU Affero General Public License v3.0** unless a file or bundled dependency states otherwise.

The repository includes or integrates third-party components with their own terms. In particular, the OjibweMorph finite-state resource is associated with **CC BY-NC-SA 4.0** terms and should not be assumed to permit unrestricted commercial deployment.

Research papers have their own publication metadata/licensing. Publishing prior art does not transfer ownership of community-controlled data or eliminate third-party licence obligations.

The proposed Capability Commons can support open and proprietary capability interfaces, but implementation details must respect Aura's AGPL terms, contributor agreements, external component licences, jurisdiction, and separate community/data governance rules.

---

# Project status

AuraOS is an active research and development system, **not a claim of finished universal AGI infrastructure**.

The repository demonstrates substantial implemented architecture around deterministic intent routing, relational repository understanding, selective cognition/source slicing, bounded human/AI Arenas, source-grounded engineering, governance, verification, continuity, spatial projection, domain Arenas, model/cost observability, and review-gated learning.

Important work remains around PR1–PR18 completion, production hardening, broader independent benchmarking, arbitrary-repository onboarding, network authentication/authorization, confidential capability execution, sandbox deployment, documentation synchronization, standards integration, live data connectors, governance agreements, licensing, developer experience, economic settlement, machine/facility federation, and staged implementation of the broader Commons/Places/Foundry architecture published in Paper IX.

The ambition is intentionally large.

The acceptance criterion remains intentionally boring:

> **Show the evidence.**

---

## Contact

**Founder:** Dallas Courchene  
**Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)  
**Email:** aura.os.q@gmail.com

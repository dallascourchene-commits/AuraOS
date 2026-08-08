# AuraOS

## Her name is **Aura** — Augmented Universal Reasoning Architecture

`AuraOS` is the repository and operating substrate. **Aura** is the architecture.

> **A sovereign, local-first, objective-native cognitive substrate that compiles human intent into grounded, governed, temporary capability systems — and tries very hard not to pay twice for work humanity already proved.**

Aura is **not a single LLM, chatbot, autonomous super-agent, or monolithic application**. She is an architecture for coordinating deterministic software, exact evidence, human governance, replaceable AI workers, reusable capabilities, and eventually human/machine economic participation without allowing probabilistic output to silently become truth or authority.

**Repository status:** active research and development  
**Software license:** GNU AGPL v3.0  
**Research record:** nine defensive prior-art papers, claims **N1–N100**  
**Latest paper:** [Paper IX v2.0 — DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020) · PDF SHA-256 `667ea216178b44d63e6c2add370e6ada2180a9274f0a65ea400832f0ccd4895e`

> **Meaning may guide discovery. Only exact grounded evidence and authorized governance may grant authority.**

---

## Contents

- [The idea in 90 seconds](#the-idea-in-90-seconds)
- [How Aura began](#how-aura-began)
- [Aura in one diagram](#aura-in-one-diagram)
- [What makes Aura different](#what-makes-aura-different)
- [Selective cognition: Council V3 and surgical slices](#selective-cognition-council-v3-and-surgical-slices)
- [The Capability Commons](#the-capability-commons)
- [Verified capability amortization](#verified-capability-amortization)
- [Compute is a governed resource](#compute-is-a-governed-resource)
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
- [Research and prior art](#research-and-prior-art)
- [Truth, authority, and safety](#truth-authority-and-safety)
- [Evidence and benchmarks](#evidence-and-benchmarks)
- [Origins, sovereignty, and intergenerational continuity](#origins-sovereignty-and-intergenerational-continuity)
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

Founder **Dallas Courchene** was trying to preserve and teach **Anishinaabemowin**. Polysynthetic languages can encode dense relational and sentence-scale meaning inside complex word forms, while general-purpose language models often approach language through tokenization and statistical assumptions that fit that structure poorly.

The original question became something like:

> **What would a computing system look like if it could represent intent more compositionally, relationally, and compactly — closer to the structural lesson of polysynthesis — instead of repeatedly expanding everything into long natural-language context?**

That led toward symbolic and high-dimensional representation, VSA/HDC binding and bundling, deterministic finite-state routing, and the early `aura.lexc` lexicon.

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
  → modular / liquid / hot-swappable capability thinking
  → Ephemeral Arenas
  → Emergent Properties + relational architecture
  → selective cognition / surgical source slices
  → proof + provenance + Attempt Archive + verification
  → reusable Architecture Harness
  → ARCH v2.3 governance / convergence
  → Developer + Architecture Arenas
  → Capability Commons
```

### 1. Polysynthetic intent, VSA/HDC, and finite-state routing

The earliest work explored whether structured morphology and high-dimensional symbolic representations could compress and route intent without making an LLM repeatedly reconstruct the entire context.

The public repository records **“Polysynthetic hardening”** on June 14, 2026, followed by six-slot/FST work later in June.

### 2. CODEMAP came before liquid/modular code

As Aura grew, simply asking a chat model to ingest or rewrite the codebase became increasingly wasteful and unreliable. The architecture needed a compact representation of itself.

That pressure produced **CODEMAP and topology-oriented navigation**: generated structural maps that let humans and AI workers find relevant files, symbols, dependencies, relationships, and tests before hydrating exact source.

The early codebase also concentrated too much behavior in `aura_node.py`.

Putting everything in one file feels wonderfully convenient when you have just learned enough Python to make everything run.

It is less wonderful after the file begins developing weather systems.

CODEMAP was an early answer to a simple scaling problem: the repository could no longer be treated as one giant prompt.

### 3. Modular / “liquid” code and hot-swappable capability thinking

The next idea was that useful behavior should not always be permanently welded into one monolithic application. Components could be modular, replaceable, and selected according to the objective.

The founder's early Gemini-era language for this was **liquid code**, modular code, and hot-swapping. The public repository records a **Liquid Planning Arena** by June 25, 2026, while the early prior-art stack includes VSA-addressed routing, modularity, and atomic hot-swap concepts.

The terminology was still searching for the deeper abstraction.

The principle was already visible:

> **Do not make the user carry the whole application when the objective only requires a temporary composition of capabilities.**

### 4. The breakthrough: Ephemeral Arenas

The modular/liquid-code idea became much clearer when it was reframed as an **Arena**.

Instead of fluidly swapping code inside a permanent application, Aura could reason about a temporary objective-specific capability system:

```text
objective
  → resolve capabilities
  → validate constraints
  → issue bounded leases
  → assemble temporary context
  → execute
  → verify
  → preserve receipts / experience / provenance
  → revoke authority
  → dissolve
```

The repository records the FST-gated **Ephemeral Organ Runtime** by July 10, 2026.

This was more than another module. The Arena abstraction made it possible to reason with one lifecycle about temporary software, temporary teams, temporary interfaces, temporary institutions, and eventually temporary compositions of machines and facilities.

The earlier phrase was “liquid code.”

The more precise abstraction turned out to be **ephemeral, governed capability composition**.

### 5. Emergent Properties and relational self-understanding

Modularity created another question: once there are many pieces, how does Aura know what already exists, what is connected, what is missing, what overlaps, and what new behavior may emerge from combinations that have never been wired together?

That pressure produced and hardened systems such as:

- Emergent Properties / Emergent Potential;
- Relational Synthesis;
- Capability Connectome and Genome Resolver;
- Relationship Atlas;
- Coding Relationship Compass;
- exact topology and evidence-bound relationship tooling.

The public history records explicit Emergent Potential work by July 6–8 and the Relationship Atlas by July 20.

The question became:

> **Before we invent something new, do we already contain the parts — and if so, what relationship is missing?**

That question later becomes fundamental to the Capability Commons.

### 6. Selective cognition and surgical source slices

As the architecture expanded, another waste pattern became obvious: even when an AI worker needed only a small piece of the system, the conventional instinct was still to send far too much context.

Aura's response was **selective cognition**.

The public repository records **Selective Architect Council V3** and external LLM slice work on July 16, 2026. Council V3 routes only critic lanes justified by candidate evidence instead of invoking every critic uniformly. The **Sliced Surgeon** then works against exact bounded source rather than treating the repository as its prompt.

That principle becomes important far beyond coding:

> **Give the reasoning worker the minimum exact evidence required for the objective — not the contents of the filing cabinet because “AI likes context.”**

### 7. Proof, provenance, and failed-attempt memory

Dynamic Arenas created harder questions:

```text
Who or what is acting?
What exact state did it see?
What was it allowed to do?
What did it actually do?
What failed before?
Who verified it?
What materially contributed?
Who may make the final decision?
```

That pressure drove the Attempt Archive, ArenaExperience, Crucible, Council/Surgeon separation, Waboose, Gate, provenance, relational authority, exact-source receipts, selective context, and the growing constitutional separation between intelligence and authority.

### 8. The Harness came last

Eventually the problem was no longer merely:

> “Can AI write or refactor the code?”

It became:

> **How do multiple AI workers keep changing a large architecture for weeks without forgetting the objective, violating a boundary, repairing the same defect repeatedly, drifting from exact HEAD, or solving one local problem by creating three architectural ones?**

That produced the reusable Architecture Harness and, eventually, the **ARCH governance/convergence harness**.

The public repository records the reusable full-repository Architecture Harness on July 21, 2026. **ARCH v2.3**, the current long-horizon governance/convergence standard, was published into the repository on August 7, 2026.

The Harness was not the idea that created Aura.

It was the mechanism Aura eventually needed **because Aura had become too complicated to keep building safely without one**.

## A short conventional learning curve, stated plainly

By the founder's account, the concentrated AI/software-systems learning period behind Aura has been roughly **three months**, preceded by practical use of AI/RAG tools, self-taught IT work, and limited Python/UI development rather than a conventional software-engineering or computer-science career.

An earlier learning episode involved organizing employer technical documentation into an AI/RAG-assisted tutor and using it against real IT/network problems. The recurring pattern later reappeared in Aura:

> **When knowledge was missing, build a mechanism that makes the knowledge easier to acquire, inspect, and reuse.**

That short timeline is not evidence of instant mastery of every field, and the project should not present it that way. Cryptography, law, compilers, distributed systems, physical engineering, science, security, governance, and other specialist domains still require independent expertise.

What the short timeline *does* explain is the development method: learn against a real constraint, externalize the useful structure, make it reusable, then use the new tool to reach the next constraint.

Aura repeatedly built the tool she needed in order to avoid collapsing under the weight of the thing she had just become.

That history is now part of the architecture.

---

# Aura in one diagram

The following diagram mixes **implemented owners** with the **published target reuse flow**. In particular, the universal automated reuse gate is a future orchestration target; current Resolver, Connectome, Atlas, Attempt Archive, and related systems provide parts of that evidence but do not yet constitute one universal pre-reasoning gate.

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

Aura tries to avoid giving every worker the entire repository, history, database, or user profile. CODEMAP, topology, relational synthesis, exact slicing, compact state, and capability resolution narrow work to the evidence required for the objective.

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

The system should ask:

> Given this objective and these constraints, which proven capability family dominates here?

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

This turns sustainability from a slogan into an optimization problem with receipts.

## Scenario arithmetic, not an energy forecast

The International Energy Agency projects global data-centre electricity consumption at roughly **945 TWh in 2030** in its current *Energy and AI* base case ([IEA — Energy demand from AI](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai)). Aura does not currently have evidence showing that she can reduce a given percentage of global data-centre electricity use.

But the scale of the theoretical opportunity is worth making explicit.

If a mature reuse/localization architecture eventually affected some fraction of those workloads, the arithmetic would look like this:

| Illustrative affected workload | Illustrative reduction on that workload | Arithmetic avoided electricity/year |
|---:|---:|---:|
| 5% of 945 TWh | 25% | ~11.8 TWh |
| 10% of 945 TWh | 50% | ~47.3 TWh |
| 30% of 945 TWh | 50% | ~141.8 TWh |

These figures are **not Aura benchmarks, forecasts, or promises**. They show why avoiding redundant inference could become physically significant if the architecture ever reaches infrastructure scale.

The causal mechanisms Aura is actually trying to test are more concrete:

```text
less duplicated invention
+ less repeated full-context hydration
+ selective Council / surgical slices
+ more deterministic and local routing
+ more reuse of verified results
+ fewer failed/repeated agent loops
+ computation moved toward the data when appropriate
+ workloads scheduled against real resource constraints
= lower resource cost per verified useful capability
```

At larger scale, the same framework can decide **where** work belongs. Edge devices, homes, community clusters, regional compute, universities, factories, and hyperscale data centers can coexist. Large data centers remain valuable for frontier training, high-bandwidth workloads, major simulations, and other heavy compute; they simply stop being the unquestioned destination for every inference request.

Future machine/facility capabilities can also expose energy source, grid state, water stress, cooling method, recoverable waste heat, latency, jurisdiction, and other constraints so objective compilation can consider physical resource cost rather than pretending all compute is environmentally identical.

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

The coordination implication is still important. Ten million developers could theoretically populate:

```text
10,000 concurrent groups of 1,000 developers
or
 1,000 concurrent groups of 10,000 developers
```

Real engineering cannot be parallelized without limit. Communication overhead, critical paths, verification, physical experiments, regulation, and architecture dependencies remain real. Aura's Developer/Architecture Arena hypothesis is not "add more people and time disappears." It is:

> **Increase the portion of work that can be safely decomposed, independently executed, recomposed, and verified.**

A mature ecosystem could contain a larger population around those developers — recipe authors, creators, researchers, security reviewers, machine/facility operators, domain experts, evaluators, compute providers, communities, enterprises, and end users — without requiring everyone to become a programmer.

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

This confidentiality model requires real sandboxing, authentication, authorization, isolation, attestation, licensing, and production hardening. A manifest by itself is not a magic invisibility cloak. Those controls are part of the staged development program, not something this README claims is already globally deployed.

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

The key shift is:

```text
traditional AGI intuition:
put general intelligence inside the model

Aura hypothesis:
put generality inside the governed substrate that can marshal intelligence
```

Under that model, no individual component needs to know everything. The system needs to find the relevant intelligence, constrain it, supply the right evidence, coordinate dependencies, verify the outcome, preserve provenance, and leave consequential authority where it belongs.

Three improvement mechanisms then become separable:

| Mechanism | What improves |
|---|---|
| **Model intelligence** | Better reasoning on genuinely novel problems |
| **Collective intelligence** | Better coordination of humans, models, tools, and institutions |
| **Accumulated intelligence** | More problems no longer require fresh reasoning because verified capability already exists |

The third mechanism is central to Aura. A system can become more capable even when its model does not become proportionally "smarter" if more of the problem space has become executable, verified, reusable infrastructure.

A future system should only be called **collective superintelligence** on evidence: for example, if it repeatedly solves broad, high-complexity objectives better than humanity's strongest existing institutions while retaining reliable verification, bounded authority, and legitimate governance. Until then, it is an architectural hypothesis to test rather than a title to award ourselves.

---

# Current development path

Aura's near-term objective is deliberately narrower than the century-scale vision.

The current program is to complete and harden the numbered **PR1–PR18 intent-native / ephemeral / Developer-and-Architecture-Arena refactor sequence**, while preserving canonical owners and avoiding a second truth, routing, verification, persistence, policy, memory, or authority plane.

The intended progression is:

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

# Bilateral live-repair Showcase
python aura_showcase_live_repair_server.py --demo-project winnipeg_pathways
```

The live-repair capture route remains disabled until a user explicitly starts a bounded session and supplies current bilateral intent/identity. It is not ambient production recording.

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

For an Aura-instrumented repository:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root /path/to/repository \
  prepare \
  --install-requirements

python scripts/aura_architecture_harness.py \
  --repo-root /path/to/repository \
  run \
  --objective "Describe the bounded engineering objective here"
```

The Harness remains analysis/proposal/proof infrastructure. It does not automatically commit, push, open a pull request, merge, release, or grant itself production authority.

---

# Using Aura with AI coding agents

AI agents should not approach AuraOS as a flat repository and indiscriminately load large hub files.

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

Run repository-owned runtime proof in an external environment:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  runtime \
  --profile .aura/runtime_profiles/construction_demo.v1.json \
  --output-dir ../AuraOS-runtime-evidence/construction \
  --install-requirements
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

ARCH v2.3 is deliberately distinct from the Architecture Harness CLI and Runtime Refactor Harness: those are bounded source-orientation and runtime-proof companions; **ARCH v2.3 owns the governance/convergence contract** for exact-head continuity, scope, authority, recursive workers, patch transactions, proof, review, learning, communication, durable-effect authorization, and stopping.

The versioned four-file bundle is:

- [`docs/architecture_harness/ARCH_V2_3/AURA_UNIVERSAL_REFACTOR_CONVERGENCE_HARNESS_V2_3.md`](docs/architecture_harness/ARCH_V2_3/AURA_UNIVERSAL_REFACTOR_CONVERGENCE_HARNESS_V2_3.md)
- [`docs/architecture_harness/ARCH_V2_3/aura_arch_v2_3_default_policy.json`](docs/architecture_harness/ARCH_V2_3/aura_arch_v2_3_default_policy.json)
- [`docs/architecture_harness/ARCH_V2_3/aura_pr_continuity_capsule.v2_3.schema.json`](docs/architecture_harness/ARCH_V2_3/aura_pr_continuity_capsule.v2_3.schema.json)
- [`docs/architecture_harness/ARCH_V2_3/AURA_PR_CONTINUITY_CAPSULE_TEMPLATE_V2_3.md`](docs/architecture_harness/ARCH_V2_3/AURA_PR_CONTINUITY_CAPSULE_TEMPLATE_V2_3.md)

Do not mix the v2.3 Markdown with an older policy/schema/template. v2.3 preserves the v2.2 recursive/provenance-governed continual-harness semantics while adding declared inter-agent channels, covert-channel resistance, non-malleable origin-bound authority, commit-time authorization for durable effects, verifier-independence/correlation receipts, and a bounded AuraJSpace working-set contract.

Aura's existing `aura_jspace_codec.py` remains **advisory only**. ARCH v2.3 binds a JSpace projection to workspace/head/phase, keeps the current default and policy ceiling at **25 active concepts**, requires reconstruction or disablement when stale, and explicitly forbids JSpace from becoming patch authority, persistent truth, routing ownership, verifier status, policy, or a second memory/control plane.

No ARCH component grants automatic merge. The terminal autonomous state remains `READY_FOR_HUMAN_REVIEW`; human disposition remains required.

---

# Architecture at a glance

Aura can be understood as seven cooperating layers.

| Layer | Role | Representative owners |
|---|---|---|
| **1. Intent & admission** | Convert objectives into structured intent and reject inadmissible routes before model reasoning | lexical addressing, six-slot intent, semantic LEXC, `aura_fst_routing.py` |
| **2. Architecture self-understanding** | Discover exact repository/domain structure and existing capabilities | CODEMAP, topology, Topological Context Anchor, Connectome, Genome Resolver, Relationship Atlas/Compass |
| **3. Advisory cognition** | Rank, compress, recall, compare, and discover possibilities without gaining authority | VSA/HDC, DREAM, QDKT, JSpace, ST3GG, MUSIC, MITOSIS, emergent-property analysis |
| **4. Arena execution** | Assemble objective-specific context, participants, tools, capabilities, budgets, and leases | Human Agent Arena, Coding Arena, Forge, Gate, Agent Bridge, Ephemeral Organ Runtime |
| **5. Verification & governance** | Prove bounded predicates and keep consequential disposition external to model output | tests, verifiers, relational authority, Council/Surgeon boundaries, human/community decision |
| **6. Continuity & experience** | Preserve exact execution state, failed attempts, receipts, checkpoints, and reviewable experience | State Ledger, Attempt Archive, Temporal Persistence, ArenaExperience, Crucible |
| **7. Projection & manifestation** | Render canonical state as spatial, visual, textual, voice, or generated interfaces without transferring truth ownership | Spatial Arena, Observatory, Showcase, Spatial Foundry |

---

# Current implemented surfaces

The repository already contains a connected set of implemented or repository-backed surfaces.

## Engineering and agent collaboration

| Surface | What it does | What it does **not** own |
|---|---|---|
| **Human Agent Arena** | `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE`; objective framing, exact grounding, bounded action, proof, and human disposition | automatic merge or production authority |
| **Coding Arena / Workbench** | Localizes exact code neighborhoods, dependencies, tests, change graphs, and compact worker context | semantic similarity is not patch authority |
| **Selective Council V3** | Architecture-level deliberation with evidence-justified critic routing rather than universal critic invocation | direct file mutation |
| **Sliced Surgeon** | Bounded exact-source implementation, surgical slices, and focused repair | architecture redefinition outside its capsule |
| **Aura Forge** | Freezes a grounded engineering plan and runs bounded Council–Surgeon work under an evidence contract | automatic commit, PR, merge, release, or production mutation |
| **Aura Gate** | Adds verified identity, static policy, leases, controlled egress, MCP/A2A boundaries, and audit evidence around Forge | trust/reputation truth or release authority |
| **Coding Waboose** | Deterministic graph-guided review plus bounded coding-agent investigation and exact-source corroboration | self-confirming findings or patch authority |
| **Agent Arena Bridge** | Exposes bounded CLI/MCP and GitHub publication workflows to replaceable external agents | merge authority |

## Architecture orientation and relational intelligence

| Surface | Role |
|---|---|
| **CODEMAP + deep topology** | Generated compact repository map and exact structural navigation |
| **Capability Connectome / Genome Resolver** | Reuse-before-invention capability anatomy and objective matching |
| **Relational Synthesis** | Objective-bounded configuration of relevant architectural relationships |
| **Relationship Atlas / Coding Relationship Compass** | Classifies wired, missing, overlapping, prohibited, stale, and objective-relevant relationships while keeping exact source authoritative |
| **Emergent Properties / Evidence Spine** | Finds evidence-bound candidate capabilities and unwired combinations without auto-wiring them |
| **Observatory** | Glass-box projection of intent, routing, topology, evidence, and review state |

## Runtime proof, continuity, and learning

| Surface | Role | Boundary |
|---|---|---|
| **Runtime Refactor Harness** | Reproduces repository-declared loopback applications in an external environment, captures evidence, and binds before/after proof | observes and verifies; never patches or merges |
| **Bilateral Live Repair** | Captures an explicitly authorized incident, preserves failed repair attempts, delegates bounded repair, and re-proves the result | no ambient recording or autonomous production hot-swap |
| **Attempt Archive** | Preserves successful, denied, failed, and superseded work so the system does not repeatedly rediscover the same failure | history is evidence, not automatic policy |
| **Temporal Persistence / State Ledger** | Bounded continuity, checkpoints, restoration assessment, and exact state | no automatic state restoration |
| **Learning Arena / Crucible** | Mines verified ArenaExperience and proposes narrow candidate learning | emits proposals; never auto-promotes code, grammar, hard guards, or policy |
| **Model Cognome** | Tracks endpoint evidence, cost, latency, drift, replay, and governed routing proposals | route changes remain explicitly authorized |
| **Empirical Cost Observatory** | Separates measured, tokenizer-exact, derived, estimated, and unavailable cost/usage evidence | measurement cannot upgrade claim authority |

## Spatial and domain surfaces

| Surface | Role | Boundary |
|---|---|---|
| **Spatial Arena** | Projects canonical state into bounded scenes and compiles user interaction back into reviewable intent | rendering is presentation, never domain truth |
| **Spatial Foundry / Showcase** | Visual proof and explanation of architecture, construction, repair, provenance, and evidence | projection-only |
| **Civic Commons Arena** | Non-binding civic planning, evidence, needs/offers, scenarios, consent, dissent, and reversible pilot design | no automatic funding, voting, legal approval, or person-level targeting |
| **Construction Arena** | Exact project-state replay, planning gates, alternatives, evidence, Spatial projection, and human decision packets | no physical-work, payment, equipment, access, or professional authority |
| **Financial Arena** | Immutable Decimal-based exact-state financial records and explicit truth classes | no transaction, account mutation, advice, or prediction authority |
| **Anishinaabemowin Tutor** | Vetted-source language learning, morphology, pronunciation, dialect/provenance labels, and teacher review | language authority remains with speakers, teachers, and community governance |

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
- intent-native generative/spatial manifestation and a proposal-only code breadboard;
- **Aura Places** with persistent governed Places and ephemeral visitor-specific Visits;
- **Convention Arenas** for temporary federated events, discovery, creators, commerce, and communities;
- an **Open Discovery / Scientific Foundry** for governed R&D, simulation, falsification, empirical validation, and fabrication;
- bounded physics/digital-twin and population-behavior simulation;
- business-incubation Arenas;
- sovereign cross-domain Arena federation;
- participatory proof-carrying Scientific Arenas and a compounding Scientific Capability Commons;
- a three-speed **Architecture Arena / convergence compiler** separating fast discovery, implementation/hardening, and slow constitutional change;
- **keystone-bottleneck analysis** and demand/capability graphs for prioritizing high-leverage development and research bounties;
- privacy-preserving **Opportunity** and **Learning** compilers driven by verified capability evidence rather than a universal reputation score;
- compute-to-data sovereignty, portable verified claims, and evidence-bearing contribution portfolios while private LifeOS/Capsule history remains separately governed;
- graded creator/referral attribution rather than treating exposure or chronology as automatic causality;
- multi-class scientific bounties for discovery, replication, falsification, boundary finding, optimization, generalization, field validation, and qualified facility work;
- objective-compiled **Ephemeral Institutions** spanning people, organizations, communities, Nations, facilities, funding, and professional roles without transferring their legal authority to Aura;
- a **Machine Capability Commons** for locality-aware fabrication plus living physical-artifact, repair, field-learning, and circular-economy lineage;
- transport-neutral, jurisdiction-aware **AuraNet** federation;
- proof-carrying assurance/warranty contract references that keep evidence separate from legal liability, certification, insurance, and truth.

These are **published architectural embodiments and development directions, not a claim that every downstream product is already implemented in this repository**.

---

# Research and prior art

AuraOS maintains a **nine-paper defensive prior-art stack**.

Papers I–VII establish claims **N1–N30**. Paper VIII continues the evidence-ordered relational architecture with **N31–N50**. **Paper IX v2.0 extends the published architecture through N51–N100.** The expanded same-day edition preserves the original N51–N87 declarations and adds N88–N100 rather than splitting the architecture across a separate follow-on paper.

| Paper | Main claim family | Claims | Publication | Repository copy |
|---|---|---:|---|---|
| **Paper I — Foundation** | Polysynthetic LLM egress, dual linguistic cortex, sparse sweeps, QDKT, visual topology, atomic hot-swap, sovereign edge design | N1–N8 | [Zenodo 20635424](https://zenodo.org/records/20635424) | [PDF](AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology.pdf) |
| **Paper II — Holographic swarm systems** | Holographic headers, fractal ledger, swarm learning, VSA-addressed rendering, FST narrative | N9–N13 | [Zenodo 20657391](https://zenodo.org/records/20657391) | [PDF](Second_Paper.pdf) |
| **Paper III — Liquid Internet** | VSA-addressed routing and naming | N14 | [Zenodo 20659314](https://zenodo.org/records/20659314) | [PDF](Third_Paper.pdf) |
| **Paper IV — Memristive and rendering upgrades** | Memristive hyper-epochs, timestep-aware SVD quantization, Gaussian/VSA rendering dynamics | N15–N17 | [Zenodo 20673206](https://zenodo.org/records/20673206) | — |
| **Paper V — FST routing and self-refactoring** | FST routing core, 3D topology resonance, bounded self-refactoring incubator | N18–N20 | [Zenodo 20681601](https://zenodo.org/records/20681601) | — |
| **Paper VI — Enhanced FST and topology** | FST lexicon, resonance topology, FST impact analysis | N21–N23 | [Zenodo 20682051](https://zenodo.org/records/20682051) | — |
| **Paper VII — Protocol-layer innovations** | Hyperdimensional integrity, micro-module crystallization, resonant tests, thermal-cost arbitration, deterministic compression, local VSA mesh, bounded self-healing | N24–N30 | [Zenodo 20695562](https://zenodo.org/records/20695562) | — |
| **Paper VIII — Evidence-Ordered Relational Arenas for Governed Cognitive Systems** | Relationship intelligence, Emergent Evidence Spine, governed Arenas, verified engineering, Waboose/Gate, spatial projection, continuity, atomic publication | **N31–N50** | [Zenodo 21465329](https://zenodo.org/records/21465329) | [PDF](papers/AuraOS_Paper_VIII_Evidence_Ordered_Relational_Arenas.pdf) |
| **Paper IX v2.0 — Objective-Native Capability Commons and Proof-Carrying Contribution Economies** | Objective-native Arena compilation; Capability Packages/Recipes; Commons and executable rights; proprietary capability evidence; attestation/provenance; Developer and Architecture Arenas; Personal Cognitive Capsules; manifestation; Places/Conventions; opportunity/learning compilers; Foundry and multi-class research bounties; Ephemeral Institutions; simulation/incubation; participatory science; machine/facility capabilities; local fabrication and circular lineage; transport-neutral AuraNet federation; assurance contracts | **N51–N100** | [Zenodo 21845020 / DOI](https://doi.org/10.5281/zenodo.21845020) | Latest expanded artifact on Zenodo; repository PDF is the earlier N51–N87 edition until replaced |

Prior-art papers document conceptual lineage and disclosed combinations. They do not override current source, tests, licences, verifiers, or governance requirements.

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

VSA/HDC similarity, DREAM, JSpace, ST3GG, QDKT, MUSIC/MITOSIS, Model Cognome proposals, visual topology, generated UI, inferred relationships, emergent-capability hypotheses, external research, market simulations, and LLM output may help discover or reason. They do not grant consequential authority by themselves.

## Human and community boundaries

Aura does not claim autonomous authority over legal decisions, professional certification, community governance, restricted cultural knowledge, financial transactions, physical work, production deployment, or repository merge unless a separate authorized system explicitly grants that capability.

---

# Evidence and benchmarks

Aura keeps evidence classes separate rather than collapsing them into one impressive-looking score.

| Tier | Evidence class | What it can support |
|---:|---|---|
| 1 | Executable gates and exact-head tests | Claims about the exact evaluated artifact |
| 2 | Deterministic comparative proxies | Controlled relative efficiency or continuity comparisons |
| 3 | Estimated structural projections | Architecture hypotheses explicitly labeled `ESTIMATED` |
| 4 | Discovery/capacity scans | Candidate capabilities and missing relationships |

Representative evidence retained in the current README lineage includes:

- exact-head refactor fixtures with visible, adversarial, and focused regression gates;
- a context-localization proxy reporting `89.04% lower` total proxy with quality `+0.0057` on its documented fixture;
- **Selective Council V3** reporting `32.83% lower` total token proxy and `33.33% fewer` model calls than Council V2 on its controlled cross-module comparison, while retaining the same substantive plan, executable patch digest, quality scores, and passing 3/3 visible + 3/3 hidden + 2/2 regression tests plus API/scope/security/compile/static-analysis/maintainability gates;
- a Gate Phase 2 instrumented scope reporting `37,907` input, `1,852` output, `39,759` total token proxy and `51,987` estimated saved (`56.66%`) against its documented counterfactual, explicitly **not provider billing evidence**;
- State Ledger synthetic continuity reporting `96.19%` lower step-7 context with preservation `1.0000` and drift `0.0000`;
- shared-grounding structural projections explicitly labeled `ESTIMATED`.

Aura's code-output quality standard separately requires isolated patch application, compilation/build, visible tests, hidden tests, regression tests, API compatibility, scope/blast-radius checks, security evidence, maintainability measurements, and explicit `WORKING` / `PARTIALLY_WORKING` / `NOT_WORKING` and acceptance dispositions. Planning quality cannot be relabelled as generated-code quality.

These figures are historical evidence tied to specific fixtures and revisions. **Rerun the exact benchmark/gate before quoting a number as current.** Unknown provider usage remains unknown.

The Capability Commons scale and energy figures elsewhere in this README are explicitly **scenario arithmetic**, not benchmark evidence.

---

# Origins, sovereignty, and intergenerational continuity

Aura began as a locally controlled Anishinaabemowin learning system. That origin continues to shape the architecture:

- local operation and sovereignty;
- data minimization;
- purpose-limited disclosure;
- inspectable provenance;
- explicit consent;
- revocable authority;
- speaker/teacher/community governance;
- refusal to treat external model convenience as authority.

Aura keeps her influences distinct:

1. **Anishinaabemowin-derived relational/governance alignments** influence sovereignty, reciprocity, local authority, and data-governance design.
2. **An Athabaskan-inspired six-slot software ordering contract** informs the canonical `DIR → ASP → CLASS → SUBJ → VOICE → STEM` ordering.
3. **Aura's machine-oriented finite-state grammar** implements deterministic software routing and hard gates.
4. Conventional software engineering, formal methods, agent architecture, VSA/HDC, security, provenance, and distributed-systems techniques provide additional engineering substrate.

These sources should not be flattened into a generic claim about "Indigenous grammar."

The project's interest in continuity is also not purely technical. Colonial systems, including residential schools, deliberately disrupted Indigenous language, family, governance, knowledge transmission, and intergenerational continuity. Software cannot repair that history and should never pretend to replace living culture, elders, families, teachers, Nations, ceremony, or governance.

The engineering lesson is narrower and still important:

> **Preserving an artifact is not the same as preserving the relationships, provenance, authority, consent, and context that make the artifact meaningful.**

Aura's federated Arenas, bounded roles, relational accountability, local authority, and dissolution after an objective is complete have resonances with relational/federated governance traditions. Aura should **not** be described as a digitized clan system, and no claim is made that all Indigenous governance traditions are identical.

Community-owned language recordings, local dialect lexicons, teaching materials, corrections, private or ceremonial knowledge, learner data, and contributor consent records remain governed separately from the general AuraOS software licence.

<details>
<summary><strong>Why Aura sometimes uses an inheritance metaphor</strong></summary>

Some animal research has reported intergenerational effects associated with conditioned sensory responses — for example, a 2014 mouse study of odor conditioning ([Dias & Ressler, Nature Neuroscience](https://www.nature.com/articles/nn.3594)). Broad claims that humans inherit detailed traumatic memories genetically are **not established**, and Aura does not depend on that claim.

The engineering metaphor is simpler: biological systems, cultures, languages, institutions, and tools all have mechanisms for carrying adaptation forward. Aura asks what it would mean for technological systems to inherit **verified executable capability** — not merely a document saying what was learned, but the evidence, constraints, provenance, failed attempts, interfaces, and procedures required to use it again.

</details>

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

That makes the three-speed model organizational as well as technical:

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
- **Ask for the causal chain.** Dallas may compress intermediate reasoning because several relationships are already active in his internal model; collaborators should force important steps into explicit artifacts.
- **Preserve negative constraints.** Ask not only what a mechanism can become, but what it must never be allowed to become.
- **Separate insight from proof.** Fast architectural synthesis is a candidate generator, not verifier evidence.
- **Use qualified depth specialists.** Cryptography, law, finance, compiler correctness, chemistry, physical engineering, regulation, security, and distributed systems still require domain experts.
- **Do not duplicate the founder.** Build a team that translates frontier architecture into specifications, production code, tests, security, publication, product operations, governance, and deployment.
- **Externalize relationships.** If a critical architectural relationship exists only in one person's head, it is a continuity defect.
- **Challenge rather than flatter.** Multiple AI systems agreeing is not independent validation. Contradictions, failed tests, adversarial review, and reproducibility are more useful than consensus theatre.
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

## 3. The developer economy becomes a contribution economy

Value can attach to code, recipes, tests, verification, research, data rights, compute, facilities, machine access, domain expertise, and meaningful downstream use rather than only to employment, advertising, or raw invocation counts.

## 4. Compute becomes heterogeneous and resource-aware

Edge, community, enterprise, research, regional, and hyperscale compute coexist. Scheduling can consider not only price and latency but energy, carbon, water, jurisdiction, data sovereignty, and available waste-heat/resource recovery.

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

---

# Documentation map

Start here:

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | Broad architecture, vision, origin, implementation map, operator and collaborator orientation |
| [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) | Canonical owners, truth/evidence order, authority, data flow, and subsystem boundaries |
| [`docs/AURA_ARCH_V2_3_HARNESS.md`](docs/AURA_ARCH_V2_3_HARNESS.md) | Current ARCH v2.3 governance-harness bundle, startup order, JSpace boundary, and migration orientation |
| [`.aura/CODEMAP.md`](.aura/CODEMAP.md) | Generated compact repository navigation; regenerate after source changes |
| [`USER_GUIDE.md`](USER_GUIDE.md) | Installation, commands, APIs, testing, and operator workflows |
| [`.aura/SECURITY.md`](.aura/SECURITY.md) | Repository security constraints |

Engineering and agent architecture:

- [`docs/AURA_ARCHITECTURE_HARNESS.md`](docs/AURA_ARCHITECTURE_HARNESS.md)
- [`docs/AURA_RUNTIME_REFACTOR_HARNESS.md`](docs/AURA_RUNTIME_REFACTOR_HARNESS.md)
- [`docs/AURA_HUMAN_AGENT_ARENA.md`](docs/AURA_HUMAN_AGENT_ARENA.md)
- [`docs/AURA_CODING_WABOOSE.md`](docs/AURA_CODING_WABOOSE.md)
- [`docs/AURA_GATE.md`](docs/AURA_GATE.md)
- [`docs/AURA_AGENT_ARENA_BRIDGE.md`](docs/AURA_AGENT_ARENA_BRIDGE.md)
- [`docs/AURA_AGENT_BRIDGE_GITHUB_PUBLICATION.md`](docs/AURA_AGENT_BRIDGE_GITHUB_PUBLICATION.md)
- [`docs/AURA_CODING_RELATIONSHIP_COMPASS.md`](docs/AURA_CODING_RELATIONSHIP_COMPASS.md)
- [`docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md`](docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md)
- [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)
- [`docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`](docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md)

Spatial and domain architecture:

- [`docs/AURA_SPATIAL_COMPUTING_S0_S2.md`](docs/AURA_SPATIAL_COMPUTING_S0_S2.md)
- [`docs/AURA_SPATIAL_S3_S4.md`](docs/AURA_SPATIAL_S3_S4.md)
- [`docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md`](docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md)
- [`docs/AURA_BILATERAL_LIVE_REPAIR_FOUNDRY.md`](docs/AURA_BILATERAL_LIVE_REPAIR_FOUNDRY.md)
- [`docs/AURA_CONSTRUCTION_DEMO_OPERATOR_GUIDE.md`](docs/AURA_CONSTRUCTION_DEMO_OPERATOR_GUIDE.md)
- [`docs/AURA_CIVIC_COMMONS_ARENA.md`](docs/AURA_CIVIC_COMMONS_ARENA.md)
- [`docs/AURA_CIVIC_DATA_AND_PRIVACY.md`](docs/AURA_CIVIC_DATA_AND_PRIVACY.md)
- [`docs/AURA_CIVIC_GOVERNANCE_AND_CONSENT.md`](docs/AURA_CIVIC_GOVERNANCE_AND_CONSENT.md)

Evidence, learning, and observability:

- [`docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md`](docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md)
- [`docs/AURA_EMPIRICAL_COST_OBSERVATORY.md`](docs/AURA_EMPIRICAL_COST_OBSERVATORY.md)
- [`docs/AURA_TENSOR_EVIDENCE_ARENAS.md`](docs/AURA_TENSOR_EVIDENCE_ARENAS.md)

Research papers:

- [`papers/AuraOS_Paper_VIII_Evidence_Ordered_Relational_Arenas.pdf`](papers/AuraOS_Paper_VIII_Evidence_Ordered_Relational_Arenas.pdf)
- [Paper IX v2.0 — Zenodo DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020) *(expanded N51–N100 edition; repository PDF remains the earlier edition until replaced)*

---

# Licensing

AuraOS source code is released under the **GNU Affero General Public License v3.0** unless a file or bundled dependency states otherwise.

The repository includes or integrates third-party components with their own terms. In particular, the OjibweMorph finite-state resource is associated with **CC BY-NC-SA 4.0** terms and should not be assumed to permit unrestricted commercial deployment.

Research papers have their own publication metadata/licensing. Publishing prior art does not transfer ownership of community-controlled data or eliminate third-party licence obligations.

The proposed Capability Commons can support open and proprietary capability interfaces, but implementation details must respect Aura's AGPL terms, contributor agreements, external component licences, jurisdiction, and any separate community/data governance rules.

---

# Project status

AuraOS is an active research and development system, **not a claim of finished universal AGI infrastructure**.

The repository demonstrates substantial implemented architecture around deterministic intent routing, relational repository understanding, selective cognition/source slicing, bounded human/AI Arenas, source-grounded engineering, governance, verification, continuity, spatial projection, domain Arenas, and review-gated learning.

Important work remains around PR1–PR18 completion, production hardening, broader independent benchmarking, arbitrary-repository onboarding, network authentication/authorization, confidential capability execution, sandbox deployment, documentation synchronization, standards integration, live data connectors, governance agreements, licensing, developer experience, economic settlement, machine/facility federation, and staged implementation of the broader Commons/Places/Foundry architecture published in Paper IX.

The ambition is intentionally large.

The acceptance criterion remains intentionally boring:

> **Show the evidence.**

---

## Contact

**Founder:** Dallas Courchene  
**Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)  
**Email:** aura.os.q@gmail.com

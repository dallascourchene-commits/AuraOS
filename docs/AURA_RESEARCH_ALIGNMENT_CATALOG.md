# Aura Research Alignment Catalog

**Purpose:** orient researchers to established and emerging work that overlaps individual mechanisms in Aura  
**Scope:** architectural alignment, not proof of equivalence or priority  
**Companion chronology:** [`AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md)

---

## Read this first

Aura is a synthesis architecture. Many of her ingredients belong to mature or rapidly developing research areas: finite-state systems, VSA/HDC, model routing, graph memory, context selection, software agents, dynamic updating, multi-agent coordination, provenance, skill libraries, evolutionary search, and human–AI collective intelligence.

That is a strength, not a defect.

The research question is not:

> **Did nobody anywhere ever think of any ingredient before Aura?**

That would be both improbable and scientifically unhelpful.

The more useful questions are:

1. Which mechanisms have strong independent precedent?
2. Which research results support or challenge Aura's design choices?
3. Which combinations appear in Aura before later papers independently converge on overlapping mechanisms?
4. Which claims remain hypotheses that Aura still has to prove herself?

For detailed **paper-date ↔ Aura-commit-date** comparisons, use the companion convergence map. This catalog organizes the literature by architectural problem instead.

---

# 1. VSA / HDC as compact compositional representation

## A Survey on Hyperdimensional Computing aka Vector Symbolic Architectures, Part I

**arXiv:** [2111.06077](https://arxiv.org/abs/2111.06077)  
**v1:** 2021-11-11

Kleyko et al. survey HDC/VSA systems that combine high-dimensional distributed representations with algebraic operations capable of representing structured symbolic relationships.

### Alignment with Aura

Aura uses VSA/HDC as a compact **advisory representation and routing/composition substrate**, not as final patch authority or domain truth. Binding, bundling, similarity, and symbolic-vector composition fit directly inside this established field.

### What it does *not* validate

The survey does not validate Aura's particular polysynthetic routing, Arena lifecycle, Capability Commons, governance, or provenance architecture.

**Chronology:** established prior art.

---

# 2. Dynamic model routing and cost-aware intelligence

## RouteLLM: Learning to Route LLMs with Preference Data

**arXiv:** [2406.18665](https://arxiv.org/abs/2406.18665)  
**v1:** 2024-06-26

RouteLLM dynamically selects between stronger and weaker language models to optimize cost/quality trade-offs and reports more than 2× cost reduction in some evaluated cases without sacrificing benchmark response quality.

### Alignment with Aura

Independent support for the premise that **not every objective deserves the most expensive model**. Aura generalizes routing beyond strong-vs-weak LLM choice into deterministic admission, capability routing, local-vs-remote placement, Model Cognome evidence, bounded context, and eventually resource-aware execution.

**Chronology:** established prior art.

---

# 3. Repository context: compression helps, but blind compression can fail

## On the Effectiveness of Context Compression for Repository-Level Tasks

**arXiv:** [2604.13725](https://arxiv.org/abs/2604.13725)  
**v1:** 2026-04-15

This empirical study evaluates discrete-token, continuous-latent, and visual context compression for repository-level code tasks. In its evaluated settings, 4× compression sometimes exceeded full-context BLEU performance and high compression ratios reduced end-to-end latency by up to 50%.

### Alignment with Aura

Supports the premise behind CODEMAP, Context Crusher, selective source hydration, and surgical slices: **full context can contain enough noise that less context is sometimes both cheaper and better**.

---

## On Problems of Implicit Context Compression for Software Engineering Agents

**arXiv:** [2605.11051](https://arxiv.org/abs/2605.11051)  
**v1:** 2026-05-11

This paper finds that implicit continuous-embedding compression can work on some single-shot code-understanding tasks yet fail on complex multi-step agentic coding.

### Alignment with Aura

This is an especially useful **warning** for Aura. It supports the choice to keep exact source, hashes, tests, and authoritative state available behind explicit apertures rather than assuming a compressed latent representation can safely become canonical memory or patch authority.

Aura's stronger claim should therefore be:

> **Compress and localize for discovery; hydrate exact authoritative evidence before consequential action.**

**Chronology:** both context-compression papers predate Aura's public June milestones.

---

# 4. Graph memory and relational continuity

## Graph-based Agent Memory: Taxonomy, Techniques, and Applications

**arXiv:** [2602.05665](https://arxiv.org/abs/2602.05665)  
**v1:** 2026-02-05

This survey studies graph-based memory for agents, motivated by long-horizon tasks that require retaining and retrieving relational dependencies rather than flat histories.

### Alignment with Aura

Supports the problem framing behind the Connectome, Relationship Atlas/Compass, Attempt Archive relationships, continuity, and provenance DAGs: useful memory often concerns **how facts, capabilities, actors, evidence, and prior attempts relate**, not merely whether a text chunk is semantically similar.

**Chronology:** established prior art.

---

# 5. Modular skills and reusable capability libraries

This is one of the clearest external convergence zones around Aura's Capability Commons.

## Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward

**arXiv:** [2602.12430](https://arxiv.org/abs/2602.12430)  
**v1:** 2026-02-12

Frames the shift from monolithic agents toward composable skill packages, progressive disclosure, on-demand loading, portability, and skill security/lifecycle concerns.

**Aura relation:** Capability Packages, minimum-sufficient context, bounded tools, progressive disclosure, capability manifests.

**Chronology:** prior literature.

---

## SKILLFOUNDRY: Building Self-Evolving Agent Skill Libraries from Heterogeneous Scientific Resources

**arXiv:** [2604.03964](https://arxiv.org/abs/2604.03964)  
**v1:** 2026-04-05

Builds validated scientific skill packages carrying scope, inputs/outputs, execution procedures, environment assumptions, provenance, and tests, with library expansion, repair, merging, and pruning.

**Aura relation:** Scientific Foundry, Capability Packages, validated procedures, provenance, test-bearing reusable capability.

**Chronology:** prior literature.

---

## SkillOps: Managing LLM Agent Skill Libraries as Self-Maintaining Software Ecosystems

**arXiv:** [2605.13716](https://arxiv.org/abs/2605.13716)  
**v1:** 2026-05-13

Treats a skill library as an evolving software ecosystem with typed contracts, hierarchical organization, compatibility/risk evaluation, validation, and maintenance.

**Aura relation:** Capability Connectome, typed contracts, lifecycle maintenance, deprecation/repair, governance, graph organization.

**Chronology:** prior literature.

---

## Generative Skill Composition for LLM Agents

**arXiv:** [2606.32025](https://arxiv.org/abs/2606.32025)  
**v1:** 2026-06-30

Treats composition as deciding **which skills, how many, and in what order** instead of inserting every available skill into context. The paper reports higher pass rates and reduced prompt-token cost in its evaluated coding-agent settings.

**Aura relation:** objective-specific Arena composition, bounded capability sets, FST/dependency-constrained combinations, context economy.

**Chronology:** Aura's public Liquid Planning Arena milestone is 2026-06-25; the named Capability Connectome/Resolver came later. This is partial post-milestone convergence, not a broad priority claim.

---

## SkillCenter: A Large-Scale Source-Grounded Skill Library for Autonomous AI Agents

**arXiv:** [2607.07676](https://arxiv.org/abs/2607.07676)  
**v1:** 2026-07-08

Introduces a large source-grounded skill library emphasizing traceability from retained skill claims back to source material.

**Aura relation:** source-grounded capabilities, CODEMAP, exact provenance, capability discoverability.

**Chronology:** Aura's CODEMAP-grounded SkillWeaver and Liquid Arena were already public; Aura's named Capability Connectome appeared one day after SkillCenter's submission. Treat chronology as mixed.

---

## Dynamic Agent Skills: A Lifecycle Survey and Taxonomy of Evolving Skill Libraries

**arXiv:** [2607.10113](https://arxiv.org/abs/2607.10113)  
**v1:** 2026-07-11

Characterizes dynamic skills as lifecycle-managed, verified, evolving external artifact stores involving evidence acquisition, proposal, verification/admission, storage, retrieval/composition, maintenance, portability, provenance, rollback, and governance.

**Aura relation:** Capability Connectome/Resolver, Ephemeral Runtime, manifests, leases, receipts, reuse-before-invention, governance, maintenance.

**Chronology:** Aura's Capability Connectome (July 9), Capability Genome Resolver (July 10), and Ephemeral Organ Runtime (July 10) were already public before this survey's submission. The survey itself covers earlier work dating back years, so this indicates convergence with the **survey framing**, not priority over the skill-library field.

---

# 6. Reusable computation and capability amortization

## MiniCache: Reusable Program Caching with Small Model Interfaces for Efficient LLM Inference

**arXiv:** [2607.20507](https://arxiv.org/abs/2607.20507)  
**v1:** 2026-07-03

MiniCache converts programs-of-thought into reusable parameterized cache objects so structurally related future requests can avoid repeated target-model inference. It reports up to 3.1× lower latency and 2.8× higher throughput in its evaluated workloads.

### Alignment with Aura

MiniCache and Aura use different mechanisms, but they share an important economic intuition:

> **Once expensive cognition has produced reusable structure, stop repurchasing the same inference.**

Aura broadens this into **Verified Capability Amortization**, where reusable software, recipes, tests, evidence, procedures, and physical capabilities can reduce future discovery cost.

**Chronology:** Aura's Liquid Planning Arena predates MiniCache's submission; Aura's explicit Capability Commons / amortization formulation came later.

---

# 7. Proof-carrying action, provenance, and runtime governance

## Proof-Carrying Agent Actions: Model-Agnostic Runtime Governance for Heterogeneous Agent Systems

**arXiv:** [2606.04104](https://arxiv.org/abs/2606.04104)  
**v1:** 2026-06-02

Proposes portable action certificates containing admissibility assumptions, approval semantics, runtime evidence, and replay-ready proof across heterogeneous agent runtimes.

**Aura relation:** Act Capsules, leases, approval, receipts, evidence contracts, model-independent governance.

**Chronology:** prior literature.

---

## From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents

**arXiv:** [2606.04990](https://arxiv.org/abs/2606.04990)  
**v1:** 2026-06-03

Argues that final-answer correctness alone is insufficient for trustworthy agents and surveys evidence tracing across retrieval, tools, memory, intermediate claims, actions, provenance-bearing memory, audit, recovery, and privacy-aware tracing.

**Aura relation:** receipts, Attempt Archive, ArenaExperience, observability, exact evidence, provenance, replay, failure diagnosis.

**Chronology:** prior literature.

---

## CAVA: Canonical Action Verification and Attestation for Runtime Governance of Agentic AI Systems

**arXiv:** [2607.13716](https://arxiv.org/abs/2607.13716)  
**v1:** 2026-07-15

Formalizes canonical action identity, semantic pattern detection, approval binding, receipt integrity, runtime-portable projection, and optional attestation.

**Aura relation:** manifest/action identity, bounded authority, approval, receipts, replay, attestation/provenance.

**Chronology:** Aura's Ephemeral Organ Runtime (July 10) already contained overlapping manifest/lease/approval/receipt/dissolution mechanisms before CAVA's July 15 submission. However CAVA builds on PCAA, submitted June 2, which Aura should acknowledge as earlier work.

---

# 8. Multi-agent coordination and bounded contexts

## AgentRadio: Passive Awareness for Long-Horizon Multi-Agent Collaboration

**arXiv:** [2607.28430](https://arxiv.org/abs/2607.28430)  
**v1:** 2026-07-30

AgentRadio studies long-horizon repository work by giving different agents clean contexts while allowing asynchronous mid-execution communication. On its SWE-Atlas QnA evaluation, the reported four-agent setup reaches 62.1% versus 32.3% for the single-agent baseline used in the paper.

### Alignment with Aura

- role-specialized workers rather than one giant context;
- bounded/clean context;
- long-horizon repository coordination;
- need for information exchange across worker boundaries.

### Important difference

AgentRadio focuses on passive inter-agent awareness. Aura emphasizes **authority-bounded roles, exact evidence, selective hydration, continuity capsules, verification, and governance**. These are complementary approaches.

### Chronology

Aura's Selective Council V3 / surgical slices (July 16), Waboose multi-role review-learning (July 19), and reusable Architecture Harness (July 21) all predate AgentRadio's July 30 submission.

---

# 9. Self-evolving coding systems and verified experience

## A Comprehensive Survey on Benchmarks and Solutions in Software Engineering of LLM-Empowered Agentic System

**arXiv:** [2510.09721](https://arxiv.org/abs/2510.09721)  
**v1:** 2025-10-10

Surveys agentic software-engineering systems around planning/reasoning, memory, tool augmentation, collaboration, self-evolution, benchmarks, and formal/evaluation gaps.

**Aura relation:** useful field context for Coding Arena, Harness, Council/Surgeon, memory, tool use, verification, and multi-agent engineering.

**Chronology:** prior literature.

---

## Self-Evolving Coding Agents

**arXiv:** [2608.03392](https://arxiv.org/abs/2608.03392)  
**v1:** 2026-08-04

Surveys coding agents that adapt memory, skills, tools, framework, model behavior, or collaboration structures from prior coding interactions, emphasizing executable feedback, repository context, trajectories, reliability, safety, maintainability, cost, and generalization.

### Alignment with Aura

Aura's Crucible, ArenaExperience, Attempt Archive, Waboose review-learning, and Harness all treat previous engineering outcomes as reusable evidence.

### Aura's deliberate difference

Aura does **not** let prior experience silently become authoritative code or policy. Learning remains proposal-only until it survives explicit proof/governance gates.

### Chronology

Aura's Crucible/verified-experience work (July 11), bounded route capsules (July 12), Council V3 (July 16), Waboose review-learning (July 19), and reusable Harness (July 21) all predate this survey's August 4 submission.

---

# 10. Evolutionary engineering and scientific discovery

## AlphaEvolve: A coding agent for scientific and algorithmic discovery

**arXiv:** [2506.13131](https://arxiv.org/abs/2506.13131)  
**v1:** 2025-06-16

AlphaEvolve combines LLM-generated code modifications with evaluator feedback and evolutionary search. It reports improvements across mathematical, algorithmic, hardware, and data-center scheduling problems.

**Aura relation:** external evaluator loops, bounded candidate generation, architectural/scientific search, performance-driven competition between candidate implementations.

**Chronology:** prior literature.

---

## Scientific Algorithm Discovery by Augmenting AlphaEvolve with Deep Research

**arXiv:** [2510.06056](https://arxiv.org/abs/2510.06056)  
**v1:** 2025-10-07

DeepEvolve combines external research with evolutionary algorithm improvement, cross-file editing, debugging, and testing so research proposals are repeatedly grounded in executable results.

**Aura relation:** Open Discovery Foundry, research-to-implementation loops, falsification/verification, bounded code evolution, combining external knowledge with executable evidence.

**Chronology:** prior literature.

---

## AI Research Agents Narrow Scientific Exploration

**arXiv:** [2605.27905](https://arxiv.org/abs/2605.27905)  
**v1:** 2026-05-27

Across tens of thousands of generated research ideas, the authors find current AI research agents tend to stay closer to seed literature and produce narrower exploration than human follow-on research; differences often arise through recombining known methods rather than opening fundamentally new questions.

### Why Aura should care

This is a valuable warning for a future Scientific Foundry. Massive agent throughput does **not** automatically equal broad discovery. Aura's Foundry should therefore reward:

- falsification;
- replication;
- contradictory hypotheses;
- boundary finding;
- diversity of search trajectories;
- independent evidence;
- genuinely different objective decompositions;
- human/domain-expert participation.

The three-speed Architecture/Scientific Arena should not become a machine for producing a billion variations of the same fashionable idea.

**Chronology:** prior literature.

---

# 11. Dynamic software updating and the pre-Arena “liquid code” intuition

## Dynamic Software Updating in Java — Comparing Concepts and Resource Demands

**arXiv:** [2506.01875](https://arxiv.org/abs/2506.01875)  
**v1:** 2025-06-02

Studies dynamic software updating techniques and resource demands for updating software while it is running.

### Alignment with Aura

Useful prior context for Aura's early **liquid / modular / hot-swappable code** intuition.

### Difference

Ephemeral Arenas eventually moved the abstraction upward: rather than only swapping modules inside a long-lived program, Aura compiles a bounded temporary capability environment around an objective and dissolves its authority/state afterward.

**Chronology:** established prior art for dynamic updating.

---

# 12. Human–AI collective intelligence and GCI

## AI-enhanced Collective Intelligence

**arXiv:** [2403.10433](https://arxiv.org/abs/2403.10433)  
**v1:** 2024-03-15

Develops a framework for collective intelligence involving humans and AI, emphasizing complementary strengths and multilayer human–AI systems rather than treating intelligence as solely an individual-agent property.

### Alignment with Aura

This is important prior context for Aura's proposed **Governed Compositional Intelligence (GCI)** framing. Aura should not claim to have invented collective intelligence.

Aura's more specific architectural hypothesis is that general problem-solving can arise from **objective-native, governed composition** across humans, models, deterministic tools, evidence, reusable capabilities, institutions, and eventually machines/facilities — while authority remains explicitly bounded.

**Chronology:** established prior literature.

---

# The pattern across the literature

Across very different research communities, several common pressures keep reappearing:

```text
MONOLITHIC EVERYTHING
        ↓
modular skills / capabilities
        ↓
selective retrieval and context
        ↓
structured composition
        ↓
long-horizon memory / graph relations
        ↓
execution evidence / provenance
        ↓
approval / runtime governance
        ↓
reusable experience
        ↓
verification and maintenance
```

Aura's distinctive research program is not any single arrow.

It is the attempt to make those arrows operate as **one governed substrate** while adding:

- polysynthetic/FST intent admission;
- CODEMAP-based exact architectural self-navigation;
- advisory VSA/HDC rather than vector authority;
- Ephemeral Arenas with bounded leases and dissolution;
- Selective Council / Sliced Surgeon labor separation;
- exact-head Harness continuity;
- Attempt Archive and review-gated learning;
- meaningful-use attribution and a Capability Commons;
- cross-domain projection into civic, financial, spatial, scientific, machine/facility, and community-owned contexts;
- human/community disposition as a constitutional boundary.

That integrated hypothesis is what Aura must prove.

---

# What the literature currently supports

The independent literature makes the following Aura hypotheses **plausible enough to test seriously**:

1. **Selective context can outperform indiscriminate full context** on some repository tasks while lowering inference cost.
2. **Blind latent compression is unsafe as a universal long-horizon solution**, supporting Aura's insistence on exact-source rehydration before consequential action.
3. **Dynamic routing can materially reduce model cost** without always sacrificing quality.
4. **Reusable skills/procedures are becoming a first-class agent architecture**, supporting Capability Package / Commons research.
5. **Lifecycle, provenance, compatibility, and security become mandatory once capability libraries grow.**
6. **Long-horizon multi-agent work benefits from role/context separation but needs explicit coordination.**
7. **Agent trust increasingly requires execution provenance and evidence, not merely plausible final answers.**
8. **Retained coding experience can improve future systems, but uncontrolled self-evolution creates safety and quality problems.**
9. **AI scientific throughput alone can narrow exploration**, making diversity, falsification, replication, and human/domain governance important.
10. **Collective intelligence need not reside inside one model.**

None of those points proves Aura's complete architecture, its economics, or its projected energy savings.

They do show that Aura is attacking a set of problems the wider field increasingly recognizes as real.

---

# What Aura still has to prove

The literature should increase the standard of proof, not lower it.

Aura still needs independent evidence that her integrated architecture can:

- preserve or improve task quality while materially reducing end-to-end inference/resource cost;
- scale Capability Commons retrieval without capability-library bloat becoming the next context problem;
- maintain confidential proprietary capability execution under real adversarial conditions;
- prevent provenance/attribution systems from becoming centralized reputation or surveillance systems;
- outperform simpler routing/retrieval/agent baselines on long-horizon engineering;
- preserve governance boundaries under multi-agent concurrency and hostile inputs;
- demonstrate that reuse actually reduces **marginal resource cost per accepted verified capability** at ecosystem scale;
- avoid rebound effects where cheaper compute merely produces larger absolute resource consumption;
- support scientific breadth rather than accelerating local-search monoculture;
- demonstrate that a Governed Compositional Intelligence substrate remains controllable as its aggregate capability grows.

The correct scientific posture is therefore:

> **The field is converging on many of the pressures Aura was built to solve. Now Aura has to show that her particular integration solves them better.**

---

# Paper index

| Area | Paper | arXiv |
|---|---|---|
| VSA/HDC | Kleyko et al., HDC/VSA Survey Part I | [2111.06077](https://arxiv.org/abs/2111.06077) |
| Model routing | RouteLLM | [2406.18665](https://arxiv.org/abs/2406.18665) |
| Context compression | Effectiveness of Context Compression for Repository-Level Tasks | [2604.13725](https://arxiv.org/abs/2604.13725) |
| Context-compression limits | Problems of Implicit Context Compression for SE Agents | [2605.11051](https://arxiv.org/abs/2605.11051) |
| Graph memory | Graph-based Agent Memory | [2602.05665](https://arxiv.org/abs/2602.05665) |
| Modular skills | Agent Skills for LLMs | [2602.12430](https://arxiv.org/abs/2602.12430) |
| Scientific skill libraries | SKILLFOUNDRY | [2604.03964](https://arxiv.org/abs/2604.03964) |
| Skill lifecycle | SkillOps | [2605.13716](https://arxiv.org/abs/2605.13716) |
| Skill composition | Generative Skill Composition | [2606.32025](https://arxiv.org/abs/2606.32025) |
| Skill grounding | SkillCenter | [2607.07676](https://arxiv.org/abs/2607.07676) |
| Dynamic skills | Dynamic Agent Skills | [2607.10113](https://arxiv.org/abs/2607.10113) |
| Reusable inference | MiniCache | [2607.20507](https://arxiv.org/abs/2607.20507) |
| Proof-carrying action | PCAA | [2606.04104](https://arxiv.org/abs/2606.04104) |
| Provenance | From Agent Traces to Trust | [2606.04990](https://arxiv.org/abs/2606.04990) |
| Runtime attestation | CAVA | [2607.13716](https://arxiv.org/abs/2607.13716) |
| Multi-agent coordination | AgentRadio | [2607.28430](https://arxiv.org/abs/2607.28430) |
| Agentic software engineering | SE Agentic Systems Survey | [2510.09721](https://arxiv.org/abs/2510.09721) |
| Self-evolving coding | Self-Evolving Coding Agents | [2608.03392](https://arxiv.org/abs/2608.03392) |
| Evolutionary discovery | AlphaEvolve | [2506.13131](https://arxiv.org/abs/2506.13131) |
| Research + evolution | DeepEvolve | [2510.06056](https://arxiv.org/abs/2510.06056) |
| Scientific-search caution | AI Research Agents Narrow Scientific Exploration | [2605.27905](https://arxiv.org/abs/2605.27905) |
| Dynamic updating | Dynamic Software Updating in Java | [2506.01875](https://arxiv.org/abs/2506.01875) |
| Collective intelligence | AI-enhanced Collective Intelligence | [2403.10433](https://arxiv.org/abs/2403.10433) |

---

## Bottom line

Aura does not need the literature to say she was right.

She needs the literature to tell us **which bets are independently plausible, which ideas already have predecessors, which later systems are converging on the same bottlenecks, and where Aura's own claims are still ahead of her evidence.**

That is a much more useful kind of validation.
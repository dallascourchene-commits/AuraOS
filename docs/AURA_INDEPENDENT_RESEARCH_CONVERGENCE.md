# Aura Independent Research Convergence Map

**Status:** research-context document  
**Purpose:** compare public AuraOS milestones with independently published research that addresses overlapping architectural pressures  
**Authority:** contextual evidence only; this document does not establish scientific priority, patent priority, novelty, or independent invention by chronology alone

---

## Why this document exists

Aura's architecture developed quickly across June–August 2026. During the same period, multiple research groups independently published work on problems that overlap with individual parts of Aura:

- modular and reusable agent skills;
- source-grounded skill libraries;
- lifecycle-managed capability stores;
- structured skill composition;
- reusable computation and program caching;
- selective context and bounded execution;
- evidence tracing and execution provenance;
- proof-carrying / approval-bound agent actions;
- long-horizon multi-agent collaboration;
- self-evolving coding agents;
- retrieval, composition, repair, verification, and rollback of reusable procedures.

The correct interpretation is **convergence**, not "these papers prove Aura" and not "Aura invented every underlying technique first."

Some cited work **predates Aura's public repository milestones** and belongs in the prior-art/background column. Other papers were submitted **after specific Aura commits had already implemented overlapping mechanisms**. Those later dates are useful evidence that Aura was independently moving toward architectural pressures other groups were also discovering.

A Git commit date proves only that a particular repository state was public by that time. It does **not**, by itself, prove independent conception, broad novelty, patent priority, or lack of earlier unpublished work elsewhere.

---

# Aura public milestone spine

The following milestones are useful anchors for chronology.

| Date | Aura public milestone | Evidence |
|---|---|---|
| **2026-06-14** | Polysynthetic hardening | [`11bde99`](https://github.com/dallascourchene-commits/AuraOS/commit/11bde99e12626d51245dece8fd7fde1d7cc2a3cc) |
| **2026-06-22** | SkillWeaver research-relevance gate already uses CODEMAP targets and grounded mutation gating | [`50aeb8f`](https://github.com/dallascourchene-commits/AuraOS/commit/50aeb8f0b6d1826a8f9b1cfe328bc2513447d5d7) |
| **2026-06-25** | Liquid Planning Arena substrate: domain-neutral Arena primitives, leases, boundary contracts, shared action queues | [`ef524df`](https://github.com/dallascourchene-commits/AuraOS/commit/ef524df4cdc8dfc1c52c9f590bcb446b5e86768f) |
| **2026-07-09** | Capability Connectome + Token Economy + workflow gates; external AI systems treated as workers/routes inside Aura | [`2cc8be4`](https://github.com/dallascourchene-commits/AuraOS/commit/2cc8be499f5d9bf50ba8ee07b8f1a010466de05c) |
| **2026-07-10** | Capability Genome Resolver explicitly implements **grounded reuse before invention** | [`8a18799`](https://github.com/dallascourchene-commits/AuraOS/commit/8a18799f7891f037f133faafffb037c516439490) |
| **2026-07-10** | Ephemeral Organ Runtime: capability resolution, manifest digest, bounded lease, sandbox, verification, telemetry, revocation, dissolution | [`be45c12`](https://github.com/dallascourchene-commits/AuraOS/commit/be45c12a2a00f89e25933dc17801b4b26ee9e95d) |
| **2026-07-11** | Arena Crucible / verified experience pipeline: mine prior outcomes, validate candidates, preserve review-gated learning | [`0bacfcd`](https://github.com/dallascourchene-commits/AuraOS/commit/0bacfcd0e0584685b56c2a95ef485627ad4df92d) |
| **2026-07-12** | Deterministic route capsules and bounded data/memory apertures | [`e933c7d`](https://github.com/dallascourchene-commits/AuraOS/commit/e933c7d17fb03b16e95fc85826f83b8ee8f78111), [`183dd80`](https://github.com/dallascourchene-commits/AuraOS/commit/183dd8022704e77e13693c8e1451ca757a5ae46c) |
| **2026-07-16** | Selective Architect Council V3 + surgical source slices + executable quality evidence | [`624a8af`](https://github.com/dallascourchene-commits/AuraOS/commit/624a8afefe1824ef070f4684bcc7dc4195542162) |
| **2026-07-19** | Coding Waboose review-learning: typed lessons, deterministic detectors, Crucible replay, exact-head verification | [`c341196`](https://github.com/dallascourchene-commits/AuraOS/commit/c341196e0323013fc7c9e6adf33854b0aed8c95f) |
| **2026-07-21** | Reusable full-repository Aura Architecture Harness | [`4865e01`](https://github.com/dallascourchene-commits/AuraOS/commit/4865e013c2deb0695b86591c899fb278aff08ac5) |
| **2026-08-07** | ARCH v2.3 governance/convergence harness and Paper IX v2.0 Capability Commons / contribution-economy direction | current repository / Zenodo research record |

---

# Earlier research Aura should acknowledge as prior context

These papers were publicly submitted **before** the Aura milestone spine above. They support the broader direction, but their chronology means they should be treated as prior literature rather than post-Aura convergence.

## Agent Skills for Large Language Models — arXiv:2602.12430

**Submitted:** 2026-02-12  
**Paper:** [Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward](https://arxiv.org/abs/2602.12430)

The paper describes the shift from monolithic agents toward **composable skill packages loaded on demand**, progressive disclosure, portable skill definitions, lifecycle/security concerns, and provenance-sensitive permissions.

**Aura overlap:** Capability Packages, capability resolution, minimum-sufficient context, MCP/tool boundaries, provenance, permission/lease concepts.

**Chronology:** predates Aura's public June milestones. Cite as related prior art / independent background, not as later validation.

---

## SKILLFOUNDRY — arXiv:2604.03964

**Submitted:** 2026-04-05  
**Paper:** [SKILLFOUNDRY: Building Self-Evolving Agent Skill Libraries from Heterogeneous Scientific Resources](https://arxiv.org/abs/2604.03964)

SkillFoundry turns heterogeneous scientific resources into **validated reusable skill packages** carrying scope, inputs/outputs, execution steps, environment assumptions, provenance, and tests, then expands/repairs/merges/prunes the library through closed-loop validation.

**Aura overlap:** Capability Packages, Scientific Foundry, provenance, tests, operational contracts, repair/merge/prune concepts, reusable scientific procedures.

**Chronology:** predates Aura's public June milestones.

---

## SkillOps — arXiv:2605.13716

**Submitted:** 2026-05-13  
**Paper:** [SkillOps: Managing LLM Agent Skill Libraries as Self-Maintaining Software Ecosystems](https://arxiv.org/abs/2605.13716)

SkillOps treats skill libraries as maintainable software ecosystems, introduces typed skill contracts and a hierarchical ecosystem graph, and evaluates utility, compatibility, risk, validation, and low-overhead maintenance.

**Aura overlap:** Capability Connectome, typed contracts, reuse-before-invention, graph organization, validation, lifecycle maintenance, technical-debt avoidance.

**Chronology:** predates Aura's public June milestones.

---

## Proof-Carrying Agent Actions — arXiv:2606.04104

**Submitted:** 2026-06-02  
**Paper:** [Proof-Carrying Agent Actions: Model-Agnostic Runtime Governance for Heterogeneous Agent Systems](https://arxiv.org/abs/2606.04104)

PCAA centers governance on portable action certificates containing admissibility, assumptions, approval semantics, runtime evidence, and replay-ready proof across heterogeneous runtimes.

**Aura overlap:** Act Capsules, leases, human disposition, route/review/prove separation, receipts, runtime-independent evidence, non-model authority.

**Chronology:** predates Aura's June 14 public milestone.

---

## From Agent Traces to Trust — arXiv:2606.04990

**Submitted:** 2026-06-03  
**Paper:** [From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents](https://arxiv.org/abs/2606.04990)

This survey argues that final-answer accuracy is insufficient for agent trust and organizes evidence tracing around retrieved evidence, tool outputs, memory, intermediate claims, actions, provenance-bearing memory, debugging, audit, recovery, and privacy-aware trace infrastructure.

**Aura overlap:** exact evidence, provenance, Attempt Archive, ArenaExperience, receipts, observability, replay, failure diagnosis, evidence-bearing memory.

**Chronology:** predates Aura's June 14 public milestone.

---

# Post-milestone convergence: later papers overlapping mechanisms Aura had already made public

The examples below are the strongest chronology cases. The claim is narrow: **the cited Aura mechanism was publicly present before the paper's arXiv submission date.** That is useful evidence of independent convergence. It is not a claim that Aura predates every idea cited by the paper.

## MiniCache — reusable computation rather than repeated expensive inference

**Paper submitted:** 2026-07-03  
**Paper:** [MiniCache: Reusable Program Caching with Small Model Interfaces for Efficient LLM Inference](https://arxiv.org/abs/2607.20507)

MiniCache transforms program-of-thought programs into reusable parameterized cache objects so structurally similar future requests can avoid repeated target-model inference. It reports up to **3.1× lower latency** and **2.8× higher throughput** in its evaluated workloads.

**Aura milestone already public:** Liquid Planning Arena on **2026-06-25** ([`ef524df`](https://github.com/dallascourchene-commits/AuraOS/commit/ef524df4cdc8dfc1c52c9f590bcb446b5e86768f)).

**Overlap:** the systems are not the same. MiniCache caches reusable programs; Aura was moving toward modular/liquid capability reuse. Both independently attack the same economic absurdity: **do not repay a large-model inference cost when structurally reusable work already exists.**

**Chronology strength:** moderate. Aura's modular/liquid substrate predates the paper; Aura's later explicit Verified Capability Amortization formulation is broader and came afterward.

---

## Generative Skill Composition — selecting subsets, counts, order, and dependencies

**Paper submitted:** 2026-06-30  
**Paper:** [Generative Skill Composition for LLM Agents](https://arxiv.org/abs/2606.32025)

SkillComposer treats skill composition as a structured decision over **which skills, how many, and in what order**, rather than exposing an agent to the entire skill collection. It reports improved pass rates with lower prompt-token cost in its evaluated coding-agent experiments.

**Aura milestone already public:** Liquid Planning Arena on **2026-06-25**.

**Overlap:** modular composition around an objective; avoid exposing every capability at once; order/dependency matters; context cost matters.

**Chronology strength:** moderate. Aura's liquid/Arena substrate predates the submission by five days; the later Capability Connectome/Resolver formalization came after this paper.

---

## SkillCenter — source-grounded reusable skills at large scale

**Paper submitted:** 2026-07-08  
**Paper:** [SkillCenter: A Large-Scale Source-Grounded Skill Library for Autonomous AI Agents](https://arxiv.org/abs/2607.07676)

SkillCenter reports a large structured skill library with source-grounding and traceability requirements so retained claims map to exact sources.

**Aura milestone already public:** CODEMAP-grounded SkillWeaver/research gating (**2026-06-22**) and Liquid Planning Arena (**2026-06-25**).

**Aura Capability Connectome date:** **2026-07-09**, one day *after* SkillCenter's submission.

**Overlap:** source-grounded reusable capability, traceability, large-scale discoverability.

**Chronology strength:** mixed and therefore important to state accurately. Some Aura grounding/modularity mechanisms predate SkillCenter; the named Capability Connectome implementation does not.

---

## Dynamic Agent Skills — lifecycle-managed, verified, evolving reusable procedures

**Paper submitted:** **2026-07-11**  
**Paper:** [Dynamic Agent Skills: A Lifecycle Survey and Taxonomy of Evolving Skill Libraries](https://arxiv.org/abs/2607.10113)

The survey characterizes dynamic skill systems as **lifecycle-managed, verified, evolving artifact stores** involving evidence acquisition, proposal, verification/admission, storage, retrieval/composition, maintenance, portability, provenance, rollback, and governance.

**Aura milestones already public:**  
- Capability Connectome + workflow gates: **2026-07-09** ([`2cc8be4`](https://github.com/dallascourchene-commits/AuraOS/commit/2cc8be499f5d9bf50ba8ee07b8f1a010466de05c))  
- Capability Genome Resolver / reuse-before-invention: **2026-07-10** ([`8a18799`](https://github.com/dallascourchene-commits/AuraOS/commit/8a18799f7891f037f133faafffb037c516439490))  
- Ephemeral Organ Runtime with manifest, lease, verification, receipt, revocation, dissolution: **2026-07-10** ([`be45c12`](https://github.com/dallascourchene-commits/AuraOS/commit/be45c12a2a00f89e25933dc17801b4b26ee9e95d))

**Overlap:** reusable externalized capabilities, lifecycle, evidence, admission, retrieval/composition, maintenance/governance, provenance, rollback/dissolution.

**Chronology strength:** strong for the repository milestone versus the survey submission date. However, the paper itself surveys work from 2023–2026, so this is **not** evidence that Aura predates the underlying skill-library field.

---

## CAVA — canonical action identity, approval binding, receipts, attestation

**Paper submitted:** **2026-07-15**  
**Paper:** [CAVA: Canonical Action Verification and Attestation for Runtime Governance of Agentic AI Systems](https://arxiv.org/abs/2607.13716)

CAVA formalizes canonical runtime action identity, semantic pattern detection, approval binding, receipt integrity, runtime-portable projection, and optional attestation.

**Aura milestone already public:** Ephemeral Organ Runtime on **2026-07-10**, including deterministic manifest digest, explicit lifecycle, capability leases, action/boundary contracts, human approval, verification, audit receipt, revocation, and dissolution.

**Overlap:** action identity/binding, approval, receipts, runtime governance, replay/verification, bounded authority.

**Chronology strength:** strong for the overlapping Aura runtime-governance mechanisms versus CAVA's arXiv submission date. CAVA itself builds on PCAA, which was submitted June 2 and therefore predates Aura's public June milestone.

---

## AgentRadio — long-horizon multi-agent work with clean contexts and mid-execution coordination

**Paper submitted:** **2026-07-30**  
**Paper:** [AgentRadio: Passive Awareness for Long-Horizon Multi-Agent Collaboration](https://arxiv.org/abs/2607.28430)

AgentRadio argues that long-horizon repository work benefits from dividing work among agents with **clean contexts**, while also requiring communication during execution. On SWE-Atlas QnA, it reports a four-agent system at **62.1%** versus **32.3%** for a single Claude Code Opus 4.6 agent under its benchmark.

**Aura milestones already public:**  
- bounded Agent/Human/Coding Arena work and capability routing in early July;  
- Selective Council V3 + external LLM surgical slices: **2026-07-16** ([`624a8af`](https://github.com/dallascourchene-commits/AuraOS/commit/624a8afefe1824ef070f4684bcc7dc4195542162));  
- typed review-learning / multi-role Architect–Council–Surgeon–Waboose workflow: **2026-07-19** ([`c341196`](https://github.com/dallascourchene-commits/AuraOS/commit/c341196e0323013fc7c9e6adf33854b0aed8c95f));  
- reusable full-repository Architecture Harness: **2026-07-21** ([`4865e01`](https://github.com/dallascourchene-commits/AuraOS/commit/4865e013c2deb0695b86591c899fb278aff08ac5)).

**Overlap:** long-horizon repository understanding, division of labor, bounded/clean contexts, multi-agent coordination, context continuity.

**Difference:** AgentRadio's distinctive contribution is asynchronous passive awareness/message passing. Aura's architecture emphasizes bounded role contracts, selective evidence, exact-head continuity, proof/governance, and later Architecture Arena convergence. They are complementary rather than identical.

**Chronology strength:** strong for Aura's selective-context, multi-role, harness milestones preceding the paper submission by 9–14 days.

---

## Self-Evolving Coding Agents — reusable experience from repository trajectories

**Paper submitted:** **2026-08-04**  
**Paper:** [Self-Evolving Coding Agents](https://arxiv.org/abs/2608.03392)

This survey identifies a growing class of coding agents that improve future behavior by updating memory, skills, tools, framework, models, or collaboration structures from prior coding interactions. It emphasizes executable feedback, repository-level context, coding trajectories, safety, maintainability, cost, and generalization.

**Aura milestones already public:**  
- Arena Crucible / verified experience pipeline: **2026-07-11**;  
- route-capsule provenance and bounded apertures: **2026-07-12**;  
- Selective Council V3: **2026-07-16**;  
- Waboose review-learning and deterministic replay of learned defect classes: **2026-07-19**;  
- reusable Architecture Harness: **2026-07-21**.

**Overlap:** learning from prior coding interactions, retained trajectories, executable feedback, reusable lessons, repository context, safety and cost, review-gated system evolution.

**Difference:** Aura deliberately refuses automatic crystallization of learned experience into authoritative code/policy. Experience generates bounded proposals and evidence; independent verification and human disposition remain required.

**Chronology strength:** strong for the named Aura review-learning / Crucible / Harness implementations preceding this survey's submission.

---

# What the convergence actually supports

The combined literature does **not** prove Aura's complete architecture. It does, however, make several of Aura's design bets less isolated.

## 1. The field is moving away from "one model contains everything"

Agent-skills research, reusable procedure libraries, small-model interfaces, and modular agents all point toward **externalized capability that can be loaded or composed when needed**.

This aligns with Aura's Capability Packages, Capability Connectome, Resolver, and Arena composition model.

## 2. Reuse is becoming an inference-economics primitive

MiniCache and skill-library systems show that repeated inference over structurally reusable work is an avoidable cost center.

Aura generalizes this into **Verified Capability Amortization**: once a capability has been discovered, tested, hardened, attributed, and made composable, future objectives should increasingly pay for matching/adaptation/re-verification rather than rediscovery.

## 3. Context selection is architecture, not prompt hygiene

Structured skill composition, clean-context multi-agent work, repository slicing, and progressive-disclosure systems all converge on a practical constraint:

> More context is not automatically more intelligence.

Aura's CODEMAP, Context Crusher, bounded apertures, Selective Council V3, and Sliced Surgeon treat context as a governed resource.

## 4. Provenance and action receipts are becoming first-class trust mechanisms

PCAA, CAVA, and the execution-provenance literature independently emphasize approval binding, action identity, evidence lineage, replay, and process accountability.

Aura's manifests, leases, receipts, Attempt Archive, exact-head binding, provenance DAGs, and human disposition live in the same problem family.

## 5. Long-horizon coding needs institutional memory

AgentRadio and the self-evolving-coding-agent literature highlight context fragmentation, long-running coordination, coding trajectories, reusable experience, and feedback reliability.

Aura's Harness, Continuity Capsule, Attempt Archive, ArenaExperience, Waboose learning, and three-speed Architecture Arena can be understood as an attempt to make that institutional memory explicit and governable.

## 6. A capability ecosystem needs lifecycle governance, not just a marketplace

Dynamic Agent Skills, SkillOps, SkillFoundry, and SkillCenter all show why a growing library cannot be treated as a flat bag of tools. Skills/capabilities need evidence, validation, organization, retrieval, compatibility, maintenance, provenance, repair, deprecation/pruning, and governance.

That is directly relevant to Aura's long-term Capability Commons.

---

# Chronology summary

| Research paper | arXiv v1 | Closest Aura public milestone | Aura milestone date | Relationship |
|---|---:|---|---:|---|
| Agent Skills for LLMs | 2026-02-12 | later Capability Packages / progressive disclosure | later | **Prior literature** |
| SKILLFOUNDRY | 2026-04-05 | later Scientific Foundry / validated capabilities | later | **Prior literature** |
| SkillOps | 2026-05-13 | later Connectome / capability maintenance | later | **Prior literature** |
| PCAA | 2026-06-02 | later leases / receipts / bounded authority | later | **Prior literature** |
| Agent Traces to Trust | 2026-06-03 | later provenance / Attempt Archive / receipts | later | **Prior literature** |
| Generative Skill Composition | 2026-06-30 | Liquid Planning Arena | 2026-06-25 | **Aura milestone earlier; partial overlap** |
| MiniCache | 2026-07-03 | Liquid Planning Arena | 2026-06-25 | **Aura milestone earlier; different mechanism** |
| SkillCenter | 2026-07-08 | CODEMAP-grounded SkillWeaver / Liquid Arena | 2026-06-22 / 06-25 | **Some Aura substrate earlier; Connectome later** |
| Dynamic Agent Skills | 2026-07-11 | Connectome + Resolver + Ephemeral Runtime | 2026-07-09 / 07-10 | **Aura implementation milestones earlier** |
| CAVA | 2026-07-15 | Ephemeral Runtime governance / receipts | 2026-07-10 | **Aura overlapping runtime mechanisms earlier; PCAA prior** |
| AgentRadio | 2026-07-30 | Council V3 + Waboose roles + Harness | 2026-07-16–07-21 | **Aura overlapping coordination/context milestones earlier** |
| Self-Evolving Coding Agents | 2026-08-04 | Crucible + review-learning + Harness | 2026-07-11–07-21 | **Aura named implementations earlier** |

---

# Recommended language for public claims

Prefer:

> **AuraOS's public commit history shows that several of its implemented mechanisms were present before later arXiv papers independently described overlapping architectural pressures. Earlier papers also show that many individual ingredients have substantial prior art. Together, the record is best understood as independent convergence around modular capability, selective context, provenance, lifecycle governance, reusable experience, and long-horizon coordination — not as proof that any one project originated the entire field.**

Avoid:

> "These papers prove Aura was first."

Avoid:

> "Research now validates all of Aura."

Avoid:

> "No one had these ideas before Aura."

Those claims would be much weaker than the actual evidence.

---

# Research links

- [arXiv:2602.12430 — Agent Skills for Large Language Models](https://arxiv.org/abs/2602.12430)
- [arXiv:2604.03964 — SKILLFOUNDRY](https://arxiv.org/abs/2604.03964)
- [arXiv:2605.13716 — SkillOps](https://arxiv.org/abs/2605.13716)
- [arXiv:2606.04104 — Proof-Carrying Agent Actions](https://arxiv.org/abs/2606.04104)
- [arXiv:2606.04990 — From Agent Traces to Trust](https://arxiv.org/abs/2606.04990)
- [arXiv:2606.32025 — Generative Skill Composition for LLM Agents](https://arxiv.org/abs/2606.32025)
- [arXiv:2607.20507 — MiniCache](https://arxiv.org/abs/2607.20507)
- [arXiv:2607.07676 — SkillCenter](https://arxiv.org/abs/2607.07676)
- [arXiv:2607.10113 — Dynamic Agent Skills](https://arxiv.org/abs/2607.10113)
- [arXiv:2607.13716 — CAVA](https://arxiv.org/abs/2607.13716)
- [arXiv:2607.28430 — AgentRadio](https://arxiv.org/abs/2607.28430)
- [arXiv:2608.03392 — Self-Evolving Coding Agents](https://arxiv.org/abs/2608.03392)

---

## Bottom line

Aura's strongest research-positioning claim is not that every ingredient is unprecedented.

It is that a single architecture independently assembled an unusually broad combination of those pressures — **polysynthetic intent routing, exact architectural self-navigation, capability reuse, ephemeral objective-native composition, selective context, role-bounded multi-agent work, provenance, receipts, verified experience, governance, and long-horizon convergence** — and that the public repository gives unusually fine-grained dates for when those mechanisms appeared.

That is a defensible story because it can be checked.
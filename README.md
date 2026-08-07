# AuraOS

**Augmented Universal Reasoning Architecture**

> **A sovereign, local-first, objective-native cognitive operating substrate that compiles human intent into grounded, governed, temporary capability systems.**

AuraOS is **not a single LLM, chatbot, autonomous super-agent, or monolithic application**. It is an architecture for coordinating deterministic software, exact evidence, human governance, and replaceable AI workers without allowing probabilistic output to silently become truth or authority.

**Repository status:** active research and development  
**Software license:** GNU AGPL v3.0  
**Research record:** nine defensive prior-art papers, claims **N1–N87**  
**Latest paper:** [Paper IX — Zenodo 21843659](https://zenodo.org/records/21843659) · [repository PDF](papers/AuraOS_Paper_IX_Objective_Native_Commons_Proof_Carrying_Contribution_Economies.pdf)

> **Meaning may guide discovery. Only exact grounded evidence and authorized governance may grant authority.**

---

## Contents

- [Aura in one diagram](#aura-in-one-diagram)
- [What makes Aura different](#what-makes-aura-different)
- [Architecture at a glance](#architecture-at-a-glance)
- [Current implemented surfaces](#current-implemented-surfaces)
- [What is implemented vs. what is future architecture](#what-is-implemented-vs-what-is-future-architecture)
- [Quick start](#quick-start)
- [Using Aura with AI coding agents](#using-aura-with-ai-coding-agents)
- [ARCH v2.3 governance harness](#arch-v23-governance-harness)
- [Research and prior art](#research-and-prior-art)
- [Detailed architecture](#detailed-architecture)
- [Domain Arenas](#domain-arenas)
- [Truth, authority, and safety](#truth-authority-and-safety)
- [Evidence and benchmarks](#evidence-and-benchmarks)
- [Documentation map](#documentation-map)
- [Origins, sovereignty, and data governance](#origins-sovereignty-and-data-governance)
- [Licensing](#licensing)

---

# Aura in one diagram

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

The Capability Connectome, Genome Resolver, Relationship Atlas/Compass, and emergent-capability analysis help determine what already exists, how it is connected, what is missing, and what should not be duplicated.

### Arena lifecycle

An **Arena** is a bounded objective-specific execution environment, not simply a chat session. It can contain humans, deterministic tools, models, capabilities, evidence, leases, verifiers, budgets, and an explicit lifecycle.

### Canonical ownership

Aura avoids creating duplicate truth, memory, routing, verification, persistence, policy, or authority planes. Projections, visualizations, vector representations, model output, and generated interfaces remain subordinate to their canonical owners.

### Proof and provenance

Important work is attached to exact source/state identity, tests, verifier evidence, receipts, Attempt Archive history, provenance, and human/community disposition rather than being accepted because a model sounded confident.

### Local-first sovereignty

Aura originated from a locally controlled language-learning system. Data minimization, purpose limitation, restricted egress, revocable authority, community governance, and local operation remain architectural requirements rather than optional product features.

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

The repository contains a connected set of implemented or repository-backed surfaces. Their purpose is easier to understand when grouped by function rather than by merge chronology.

## Engineering and agent collaboration

| Surface | What it does | What it does **not** own |
|---|---|---|
| **Human Agent Arena** | `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE`; objective framing, exact grounding, bounded action, proof, and human disposition | automatic merge or production authority |
| **Coding Arena / Workbench** | Localizes exact code neighborhoods, dependencies, tests, change graphs, and compact worker context | semantic similarity is not patch authority |
| **Selective Council V3** | Architecture-level deliberation when cross-cutting reasoning is justified | direct file mutation |
| **Surgeon** | Bounded exact-source implementation and focused repair | architecture redefinition outside its capsule |
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

# What is implemented vs. what is future architecture

AuraOS deliberately distinguishes **repository-backed behavior** from **published architecture and future product direction**.

### Repository-backed / implemented

The current tree includes deterministic routing, CODEMAP/topology, relational architecture tooling, Human/Coding/Agent Arenas, Forge/Gate/Waboose, runtime proof harnesses, continuity and learning substrates, Spatial projection, Civic/Construction/Financial slices, model/cost observability, and the first intent-native ephemeral workspace contracts.

### Active refactor architecture

The current intent-native spatial/ephemeral refactor is progressively establishing stricter contracts for objective-compiled workspaces, persistent capability reuse, selective source hydration, governed manifestation, and future capability composition. Each PR must preserve existing canonical owners and avoid creating a second plane.

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
- participatory proof-carrying Scientific Arenas and a compounding Scientific Capability Commons.

These are **published architectural embodiments and development directions, not a claim that every downstream product is already implemented in this repository**.

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
python3 -m pip install -r requirements.txt
```

Regenerate and verify architecture orientation before relying on graph-based workflows:

```bash
python3 aura_codebase_navigator.py
python3 -m aura_codemap_verify --compare-json .aura/CODEMAP.json
python3 -m aura_agent_arena_cli stabilization-status
python3 -m aura_agent_arena_cli digest
```

Launch common local surfaces:

```bash
# Human Agent Arena
python3 aura_human_agent_arena_server.py --repo-root . --demo

# Coding Arena
python3 aura_coding_arena_server.py --demo

# Showcase
python3 aura_showcase_server.py --demo-project winnipeg_pathways

# Bilateral live-repair Showcase
python3 aura_showcase_live_repair_server.py --demo-project winnipeg_pathways
```

The live-repair capture route remains disabled until a user explicitly starts a bounded session and supplies current bilateral intent/identity. It is not ambient production recording.

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

ARCH v2.3 is deliberately distinct from the existing Architecture Harness CLI and Runtime Refactor Harness: those are bounded source-orientation and runtime-proof companions; **ARCH v2.3 owns the governance/convergence contract** for exact-head continuity, scope, authority, recursive workers, patch transactions, proof, review, learning, communication, durable-effect authorization, and stopping.

The versioned four-file bundle is:

- [`docs/architecture_harness/ARCH_V2_3/AURA_UNIVERSAL_REFACTOR_CONVERGENCE_HARNESS_V2_3.md`](docs/architecture_harness/ARCH_V2_3/AURA_UNIVERSAL_REFACTOR_CONVERGENCE_HARNESS_V2_3.md)
- [`docs/architecture_harness/ARCH_V2_3/aura_arch_v2_3_default_policy.json`](docs/architecture_harness/ARCH_V2_3/aura_arch_v2_3_default_policy.json)
- [`docs/architecture_harness/ARCH_V2_3/aura_pr_continuity_capsule.v2_3.schema.json`](docs/architecture_harness/ARCH_V2_3/aura_pr_continuity_capsule.v2_3.schema.json)
- [`docs/architecture_harness/ARCH_V2_3/AURA_PR_CONTINUITY_CAPSULE_TEMPLATE_V2_3.md`](docs/architecture_harness/ARCH_V2_3/AURA_PR_CONTINUITY_CAPSULE_TEMPLATE_V2_3.md)

Do not mix the v2.3 Markdown with an older policy/schema/template. v2.3 preserves the v2.2 recursive/provenance-governed continual-harness semantics while adding declared inter-agent channels, covert-channel resistance, non-malleable origin-bound authority, commit-time authorization for durable effects, verifier-independence/correlation receipts, and a bounded AuraJSpace working-set contract.

Aura's existing `aura_jspace_codec.py` remains **advisory only**. ARCH v2.3 binds a JSpace projection to workspace/head/phase, keeps the current default and policy ceiling at **25 active concepts**, requires reconstruction or disablement when stale, and explicitly forbids JSpace from becoming patch authority, persistent truth, routing ownership, verifier status, policy, or a second memory/control plane.

No ARCH component grants automatic merge. The terminal autonomous state remains `READY_FOR_HUMAN_REVIEW`; human disposition remains required.

---

# Research and prior art

AuraOS maintains a **nine-paper defensive prior-art stack**.

Papers I–VII establish claims **N1–N30**. Paper VIII continues the evidence-ordered relational architecture with **N31–N50**. Paper IX extends the published architecture through **N51–N87**.

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
| **Paper IX — Objective-Native Capability Commons and Proof-Carrying Contribution Economies** | Objective-native Arena compilation; Capability Packages/Recipes; Commons and executable rights; proprietary capability evidence; attestation/provenance; Developer Arenas; Personal Cognitive Capsules; manifestation; Places/Conventions; Foundry/simulation/incubation; participatory scientific work and compounding capability reuse | **N51–N87** | [Zenodo 21843659](https://zenodo.org/records/21843659) | [PDF](papers/AuraOS_Paper_IX_Objective_Native_Commons_Proof_Carrying_Contribution_Economies.pdf) |

Prior-art papers document conceptual lineage and disclosed combinations. They do not override current source, tests, licences, verifiers, or governance requirements.

---

# Detailed architecture

The remainder of this README gives a more technical map. For canonical ownership and exact architecture boundaries, read [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md).

## 1. Intent, lexical addressing, and guarded finite-state routing

Aura accepts ordinary language while preserving an inspectable internal route.

```text
natural language / structured objective
  → lexical address and local tags
  → six-slot intent
  → semantic LEXC
  → state-local guarded WFST
  → hard blockers
  → weighted ranking among already-admissible routes
  → admitted route or explicit denial
```

Canonical slot order:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

The six-slot software ordering is Athabaskan-inspired. Aura's machine FST/WFST is its own engineering grammar. Anishinaabemowin-derived governance/relational influences are distinct again. The project does not flatten these into one linguistic claim.

VSA/HDC resonance may help rank already-admissible alternatives. It cannot override missing grounding, tests, expired leases, risk blocks, denied capabilities, or failed verifier requirements.

## 2. CODEMAP, topology, and architecture self-understanding

Aura is designed so humans and AI workers can orient without loading the whole repository.

The architecture composes:

- `.aura/CODEMAP.json` and `.aura/CODEMAP.md`;
- compiled deep topology;
- exact file, symbol, call, import, and test relations;
- Topological Context Anchor;
- Affordance Directory and Node Inspector;
- Capability Connectome and Genome Resolver;
- Relational Index / Relationship Atlas;
- Coding Relationship Compass;
- Emergent Evidence Spine and candidate discovery;
- manifests, schemas, ownership, and test evidence.

The key rule is:

> **Generated maps locate evidence; exact current source and verifier evidence establish it.**

Regenerate CODEMAP/topology after architecture or source changes. Do not rely on historical line numbers or stale generated maps.

## 3. Relational Synthesis and the Relationship Atlas

Aura's relational systems distinguish several questions:

```text
What exists?
What is exactly wired?
What is merely advisory?
What overlaps?
What is missing?
What is stale?
What is prohibited from connecting?
What combination is relevant for this objective?
```

The Relationship Atlas/Compass can classify and bound these relationships without becoming another source-of-truth database. A JIT Relational Synthesis capsule selects the objective-relevant configuration; exact source/state remains canonical.

## 4. Planning, work decomposition, and Council–Surgeon separation

The Planning Board represents goals, actions, predicates, constraints, dependencies, backward regression, forward replay, and continuity. It proposes; it does not execute.

For engineering work:

```text
objective
  → grounding / relationship packet
  → Planning Board / Change Graph
  → bounded Act Capsules / work units
  → Council V3 for structural reasoning when needed
  → Surgeon for exact implementation
  → focused verification
  → human review
```

Local failures may return to the Surgeon. Interface, dependency, invariant, or scope-expansion failures return to architecture-level reasoning rather than being repeatedly patched locally.

## 5. Arenas, capability leases, and ephemeral execution

An Arena assembles only what one objective requires.

A typical lifecycle is:

```text
FRAME
  → GROUND
  → PLAN
  → ACT
  → PROVE
  → DECIDE
  → DISSOLVE
```

Domain-specific Arenas may introduce additional typed stages, but the same principles remain:

- bounded objective;
- explicit context and evidence;
- minimum capabilities;
- revocable/expiring leases;
- resource and cost bounds;
- no ambient authority;
- separate verification;
- external disposition;
- explicit cleanup and dissolution.

The Ephemeral Organ Runtime compiles temporary capability systems from verified manifests and leases. The FST is an admission grammar, **not** a complete security sandbox; arbitrary components require a real restricted runtime and must fail closed when the required sandbox is unavailable.

## 6. External models and Model Cognome

Aura is model-agnostic by design.

Possible workers include local/open-weight models, OpenAI-compatible endpoints, Codex, Hermes, or other MCP/A2A-connected agents. They remain replaceable.

Model Cognome tracks:

- endpoint identity and capability evidence;
- cost and latency;
- quality/drift observations;
- replay and shadow comparisons;
- route proposals and quarantine state.

Representative route classes:

```text
ZERO_MODEL | DIRECT | CASCADE | PANEL
```

Representative operating modes:

```text
LEGACY | SHADOW | PAIRED_LIVE
```

A model may recommend a route. The model does not authorize itself.

## 7. Compression, memory, and continuity

Aura uses multiple compact representations for different purposes rather than treating one vector store or chat transcript as memory.

- **Exact slicing / Context Crusher** — remove unrelated source/context.
- **VSA/HDC** — associative semantic addressing.
- **ST3GG** — compact visible advisory frames with exact-recall handles.
- **JSpace** — active route/workspace continuity.
- **QDKT** — compact observation and knowledge-transfer events.
- **State Ledger** — bounded intra-session execution state.
- **Attempt Archive** — failed/denied/successful historical work.
- **Temporal Persistence** — content-addressed checkpoints, forks, and restoration assessment.
- **ArenaExperience** — verified outcomes suitable for review-gated learning.

Restoration remains reviewable. A checkpoint does not silently regain expired authority or automatically apply itself.

## 8. Review-gated learning

Aura's learning philosophy is **learning to re-prove**, not learning to bypass proof.

```text
verified execution
  → typed outcome
  → ArenaExperience
  → TRAIN / VALIDATION / SHADOW separation
  → candidate crystallization
  → verifier + human review
  → explicit promotion or rejection
```

A research paper, model answer, route trace, or successful-looking patch is not durable learned truth by itself.

## 9. Verification, receipts, and provenance

Aura separates several questions that are often collapsed:

```text
identity      — who/what is acting?
authority     — what was it allowed to do?
execution     — what did it actually do?
provenance    — what did the result derive from?
verification  — what bounded predicates were checked?
disposition   — who accepted/rejected the consequence?
attribution   — what materially contributed?
```

Current repository mechanisms include exact hashes, contracts, tests, verifier output, append-only events, Attempt Archive evidence, action/lease identity, runtime receipts, and provenance-bearing artifacts.

Paper IX extends this architecture into a generalized Attestation/Provenance DAG and meaningful-use contribution economy. That broader Commons/economic layer is published architecture, not a claim that automated settlement is already active in the current tree.

## 10. Spatial manifestation and proposal-only interaction

Aura's spatial architecture keeps canonical truth separate from presentation.

```text
canonical domain/repository state
  → privacy-minimized adapter
  → immutable SpatialSceneSnapshot
  → device/render plan
  → replaceable renderer
  → user interaction
  → typed interaction intent / proposal
  → domain verification path
  → authorized disposition
```

A scene, splat, graph, gesture, gaze target, generated layout, or visual relationship cannot create domain authority.

The current Spatial lifecycle is:

```text
FRAME → GROUND → COMPILE_SCENE → PLAN_RENDER → PRESENT
      → INTERACT → PROVE → DECIDE → DISSOLVE
```

Paper IX generalizes this separation into **intent-native manifestation**: rich spatial, visual, textual, voice, or generative interfaces may help people understand and manipulate a proposal while canonical records remain authoritative.

## 11. Runtime Refactor Harness and bilateral live repair

The Runtime Refactor Harness is an observation/proof owner, not an autonomous coding loop.

```text
exact Git identity + repository runtime profile
  → external virtual environment
  → loopback application
  → probe/browser evidence
  → retained verification
  → artifact hashes + cleanup
  → failure or verified receipt
  → separately authorized repair
  → exact rerun
  → repaired-and-verified receipt
```

Bilateral live repair adds explicit positive and negative user intent, bounded incident capture, privacy sanitization, deterministic replay, failed-attempt preservation, bounded repair routing, isolated preview/rollback, U7 reproof, and a projection-only Spatial Foundry.

No ambient recording, automatic production hot-swap, automatic merge, or professional/physical authority is granted.

---

# Domain Arenas

## Civic Commons

Civic Commons composes needs, offers, evidence, rules, scenarios, dissent, consent, reversible pilots, and community decision packets.

It is intentionally non-binding. Models may help compare options, but they do not become governments, voters, funders, courts, or cultural authorities.

See [`docs/AURA_CIVIC_COMMONS_ARENA.md`](docs/AURA_CIVIC_COMMONS_ARENA.md).

## Construction Arena

Construction replays exact `ConstructionProjectState`, evaluates readiness/conflict/expiry, hard blockers, alternatives, and bounded Human Agent/Observatory/Spatial projections.

It does not authorize physical work, payments, equipment, site access, safety certification, engineering certification, or legal approval.

Synthetic demonstration:

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --serve
```

See [`docs/AURA_CONSTRUCTION_DEMO_OPERATOR_GUIDE.md`](docs/AURA_CONSTRUCTION_DEMO_OPERATOR_GUIDE.md).

## Financial Arena

The current Financial slice stores immutable Decimal-backed exact-state records and explicit truth classes:

```text
USER_RECORDED | IMPORTED_EXACT | DERIVED_ARITHMETIC | ASSUMPTION | UNAVAILABLE
```

It rejects silent floats, implicit rounding, inferred ownership, implicit currency conversion, contradictory lifecycle state, and model-estimated values presented as exact records.

It does not provide transaction, account-mutation, advice, or prediction authority.

## Anishinaabemowin Tutor

The tutor uses vetted sources, morphology, pronunciation guidance, dialect/provenance labels, confidence classes, privacy/governance gates, and teacher review.

Community-controlled language assets remain legally and technically distinct from the general AuraOS software layer.

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

The following may help discover, rank, compress, visualize, or explain without granting consequential authority by themselves:

- VSA/HDC similarity;
- DREAM/DREAM-lite;
- JSpace;
- ST3GG;
- QDKT;
- MUSIC/MITOSIS;
- Model Cognome proposals;
- visual topology and generated UI;
- inferred/ghost relationships;
- emergent-capability hypotheses;
- external research and LLM output.

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
- Selective Council V3 reporting `32.83% lower` total proxy than Council V2 on its controlled comparison with the same accepted patch and quality;
- a Gate Phase 2 instrumented scope reporting `37,907` input, `1,852` output, `39,759` total token proxy and `51,987` estimated saved (`56.66%`) against its documented counterfactual, explicitly **not provider billing evidence**;
- State Ledger synthetic continuity reporting `96.19%` lower step-7 context with preservation `1.0000` and drift `0.0000`;
- shared-grounding structural projections explicitly labeled `ESTIMATED`.

These figures are historical evidence tied to specific fixtures and revisions. **Rerun the exact benchmark/gate before quoting a number as current.** Unknown provider usage remains unknown.

---

# Documentation map

Start here:

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | Broad architecture, implementation map, research record, and operator orientation |
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
- [`papers/AuraOS_Paper_IX_Objective_Native_Commons_Proof_Carrying_Contribution_Economies.pdf`](papers/AuraOS_Paper_IX_Objective_Native_Commons_Proof_Carrying_Contribution_Economies.pdf)

---

# Origins, sovereignty, and data governance

Aura began as a locally controlled Anishinaabemowin learning system. That origin continues to shape the architecture:

- local operation and sovereignty;
- data minimization;
- purpose-limited disclosure;
- inspectable provenance;
- explicit consent;
- revocable authority;
- speaker/teacher/community governance;
- refusal to treat external model convenience as authority.

Aura keeps its influences distinct:

1. **Anishinaabemowin-derived relational/governance alignments** influence sovereignty, reciprocity, local authority, and data-governance design.
2. **An Athabaskan-inspired six-slot software ordering contract** informs the canonical `DIR → ASP → CLASS → SUBJ → VOICE → STEM` ordering.
3. **Aura's machine-oriented finite-state grammar** implements deterministic software routing and hard gates.
4. Conventional software engineering, formal methods, agent architecture, VSA/HDC, security, provenance, and distributed-systems techniques provide additional engineering substrate.

These sources should not be flattened into a generic claim about “Indigenous grammar.”

Community-owned language recordings, local dialect lexicons, teaching materials, corrections, private or ceremonial knowledge, learner data, and contributor consent records remain governed separately from the general AuraOS software licence.

---

# Licensing

AuraOS source code is released under the **GNU Affero General Public License v3.0** unless a file or bundled dependency states otherwise.

The repository includes or integrates third-party components with their own terms. In particular, the OjibweMorph finite-state resource is associated with **CC BY-NC-SA 4.0** terms and should not be assumed to permit unrestricted commercial deployment.

Research papers have their own publication metadata/licensing. Publishing prior art does not transfer ownership of community-controlled data or eliminate third-party licence obligations.

---

# Project status

AuraOS is an active research and development system, not a claim of finished universal AGI infrastructure.

The repository demonstrates substantial implemented architecture around deterministic intent routing, relational repository understanding, bounded human/AI Arenas, source-grounded engineering, governance, verification, continuity, spatial projection, domain Arenas, and review-gated learning.

Important work remains around production hardening, broader independent benchmarking, network authentication/authorization, sandbox deployment, documentation synchronization, standards integration, live data connectors, governance agreements, licensing, developer experience, and the staged implementation of the broader Commons/Places/Foundry architecture published in Paper IX.

---

## Contact

**Founder:** Dallas Courchene  
**Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)  
**Email:** aura.os.q@gmail.com
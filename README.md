# AuraOS

A sovereign, local-first, Arena-based cognitive operating substrate that compiles human intent into grounded, governed, temporary capability systems.

- [License: AGPL v3](https://www.gnu.org/licenses/agpl-3.0)
- [Architecture: Arena Based](#the-arena-system)
- [Target: Edge First](#quick-start)
- [Governance: Human Authority](#truth-authority-and-safety)

**AuraOS is not an LLM and it is not a single application.**
Aura is a deterministic orchestration substrate that helps humans and external AI workers understand a large system, select the smallest relevant context, assemble bounded tools, verify results, and preserve human or community authority.

AuraOS began as a locally controlled AI tutor intended to help its founder learn and preserve Anishinaabemowin without surrendering language data to large external platforms. That origin shaped the wider architecture: local control, purpose limitation, inspectable memory, provenance, data minimization, revocable capability leases, external-provider boundaries, and governance above model convenience.

---

## Contents

- [What AuraOS Is](#what-auraos-is)
- [The Core Loop](#the-core-loop)
- [The Arena System](#the-arena-system)
- [How the Architecture Fits Together](#how-the-architecture-fits-together)
- [Core Concepts](#core-concepts)
- [Architecture Self-Understanding](#architecture-self-understanding)
- [Anishinaabemowin and Data Sovereignty](#anishinaabemowin-and-data-sovereignty)
- [Truth, Authority, and Safety](#truth-authority-and-safety)
- [Quick Start](#quick-start)
- [Common Workflows](#common-workflows)
- [CODEMAP Health and Regeneration](#codemap-health-and-regeneration)
- [Future Arena Families](#future-arena-families)
- [Intent-Compiled Application Fabric](#intent-compiled-application-fabric)
- [Federated Arena Vision](#federated-arena-vision)
- [Documentation Map](#documentation-map)
- [Repository Hygiene](#repository-hygiene)
- [Prior Art](#prior-art)
- [Licensing](#licensing)

---

## What AuraOS Is

AuraOS turns a human objective into a compact, inspectable execution environment.

Instead of giving an AI agent a giant prompt and an entire repository, Aura:

1. parses the objective;
2. compresses it into a structured intent packet;
3. validates the route through finite-state constraints;
4. discovers capabilities that already exist;
5. localizes exact files, symbols, tests, evidence, and dependencies;
6. opens a bounded Arena workspace;
7. grants only the minimum capabilities required;
8. gives external workers compact, grounded context;
9. stages rather than directly promotes consequential changes;
10. verifies outputs against exact evidence;
11. requires human or community approval where authority matters;
12. records cost, provenance, state transitions, and dissolution receipts.

External models such as Hermes, Codex, Fireworks-backed workers, or other agents are **workers inside Aura's governed environment**. They are not the architecture, the memory, or the authority.

### Design goals

- **Sovereignty:** local and community control over data, memory, tools, and model egress.
- **Token efficiency:** send the smallest useful context instead of dumping full files or databases.
- **Grounding:** distinguish exact facts from advisory inference.
- **Composability:** reuse existing Aura capabilities before inventing new modules.
- **Ephemerality:** assemble temporary applications or "organs" for an objective, then revoke and dissolve them.
- **Human legibility:** let people inspect what exists, why it exists, what it depends on, what may break, and what remains uncertain.
- **Edge discipline:** preserve useful local operation on CPU-first and resource-constrained hardware.
- **Measured claims:** label usage and savings as measured, tokenizer-exact, derived, estimated, or unavailable.

---

<!-- PR92:CURRENT_ARCHITECTURE:START -->
## Current Implemented Architecture

**Implementation audit:** June 14–July 14, 2026 · **Generated topology:** 804 indexed files · 7,019 topology nodes · 14,526 topology edges

The current repository combines the earlier substrate with the major capabilities added during the audit window:

- canonical six-slot and machine-FST routing, guarded WFST challenge paths, and C1/C2 route capsules;
- CODEMAP/deep-topology grounding, the Topological Context Anchor, Capability Connectome, Capability Genome Resolver, and Model Cognome;
- Coding, Agent, Human Agent, Liquid Planning, Civic Commons, Experience/Crucible, and ephemeral-organ execution surfaces;
- reversible context crushing, visible ST3GG egress, JSpace route state, empirical cost telemetry, and governed provider egress;
- C3 proposal-only procedure induction, replay/shadow/drift evidence, federation bundles, and human-reviewed policy promotion gates;
- the unified Showcase and deployment surfaces used to inspect architecture, Winnipeg pathways, observability, and guided approvals.

### Model Cognome and adaptive routing

Aura's public compatibility router keeps `LEGACY` as the default and rollback path. `SHADOW` creates and records a graph-bound plan without provider calls. `PAIRED_LIVE` permits one explicitly authorized comparison only after purpose, current graph digest, endpoint, verifier, expiry, call budget, and egress checks pass. Execution modes are `ZERO_MODEL`, `DIRECT`, `CASCADE`, and `PANEL`.

The adaptive layer may select and execute admitted workers; it may not automatically activate or promote policy, mutate source, commit, push, merge, or replace exact source/hash patch authority. See `docs/AURA_MODEL_COGNOME_ADAPTIVE_ROUTER.md`.
<!-- PR92:CURRENT_ARCHITECTURE:END -->

## The Core Loop

```
HUMAN / COMMUNITY OBJECTIVE
           │
           ▼
```
```
┌───────────────────────────────────────────────────────────────┐
│ 1. INTENT INGESTION                                           │
│ Plain language or .aura/intents/*.aura.md                     │
│ → polysynthetic packet → six-slot LEXC validation             │
│ → deterministic machine-FST route                             │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ 2. SELF-UNDERSTANDING                                         │
│ CODEMAP + topology + Module Manifest + Affordance Directory   │
│ + Capability Connectome + Capability Genome Resolver          │
│ → what exists, why, dependencies, tests, risks, reuse plan    │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ 3. ADVISORY COGNITION                                         │
│ VSA/HDC + DREAM-lite + QDKT + JSpace + ST3GG                  │
│ → rank, recall, compress, preserve route/workspace state      │
│ → advisory only                                               │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ 4. ARENA                                                      │
│ Coding / Agent / Human Agent / Civic / domain Arena           │
│ → micro-context + action capsules + boundary contracts        │
│ → work decomposition + scenario comparison                    │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ 5. EPHEMERAL ORGANS                                           │
│ manifest → digest → lifecycle → minimum lease → sandbox       │
│ → execute → verify → project result → revoke → dissolve       │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ 6. TRUTH AND APPROVAL                                         │
│ exact spans / hashes / tests / snapshots / sidecars           │
│ → verifier gates → human or community decision                │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ 7. MEMORY AND OBSERVABILITY                                   │
│ QDKT / governed memory / audit ledgers / cost observatory     │
│ / lifecycle and dissolution receipts                          │
└───────────────────────────────────────────────────────────────┘
```

The architecture follows one central rule:

> **Meaning may guide retrieval. Only grounded evidence and authorized governance may grant authority.**

---

## The Arena System

Aura's capabilities are easiest to understand as coordinated Arenas rather than as hundreds of unrelated modules.

### Implemented Arena surfaces

| Arena or surface | Primary user | Purpose | Current authority |
|---|---|---|---|
| **Coding Arena** | Aura internals and human operators | Select a code micro-arena, inspect topology, detect candidate faults, compile action capsules, and simulate routes before a worker acts | Read-only/advisory until staged through verifier gates |
| **Agent Arena Bridge** | External coding agents | Lets Hermes, Codex, Fireworks workers, MCP clients, and CLI agents drive through Aura's CODEMAP, read-slice, staging, and verification tools | May stage candidate patches; cannot directly promote production |
| **Human Agent Arena** | Human + Aura + agent collaboration | Visual command centre for concept workspaces, node inspection, ghost hypotheses, diagnostics, impact analysis, and prepared handoffs | Human-led; visual and inferred layers are advisory |
| **Civic Commons Arena** | Communities, planners, and participants | Makes needs, offers, evidence, laws, trade-offs, scenarios, dissent, consent, pilots, and decision packets visible together | Non-binding; community/human authority remains final |
| **Anishinaabemowin Tutor** | Learners, speakers, teachers, and language programs | Vetted-source lookup, morphology, pronunciation guidance, curriculum, dialect notes, confidence labels, and review queues | Language authority remains with speakers, teachers, and community governance |
| **Liquid Planning Arena** | Domain adapters | General Action Capsules, Boundary Contracts, scoped leases, work queues, and verifier-led handoffs for code and non-code domains | Adapter-specific and bounded by contracts |
| **Ephemeral Organ Runtime** | All Arenas | Compiles temporary, capability-bounded applications from intent and dissolves them after use | Minimum explicit lease; no ambient authority |
| **Model Cognome + Adaptive Router** | Operators and governed experiments | Resolves current graph-bound context, admits endpoint profiles, plans routes, and records comparable evidence | `LEGACY` default; `SHADOW` no-call; `PAIRED_LIVE` requires explicit authorization and egress approval |

### 1. Coding Arena

The Coding Arena converts a large repository into a small, task-specific workspace.

It can:
- load CODEMAP and topology facts;
- select a node or concept;
- expand a depth-bounded micro-arena;
- identify callers, callees, tests, documents, and neighbor files;
- detect candidate wiring faults;
- compile compact worker capsules;
- attach JSpace route state;
- optionally compress egress through visible ST3GG;
- simulate route choices;
- preserve exact file, symbol, line, digest, and test references.

The visual graph helps orientation. It is not patch authority.

Key files:
- `aura_coding_arena_3d.py`
- `aura_coding_arena_server.py`
- `aura_coding_arena_grounding.py`
- `aura_coding_arena_workflow.py`
- `aura_builder_context.py`
- `aura_fst_routing.py`
- `AURA_CODING_ARENA_README.md`

### 2. Agent Arena Bridge

The Agent Arena Bridge exposes Aura's grounded workflow to external coding agents through CLI, MCP-compatible JSON-RPC, Codespaces, and optional Fireworks-backed workers.

The bridge provides:
- repository digest;
- CODEMAP search;
- authorized source slices;
- prepared micro-context;
- staged patch submission;
- verifier and test execution;
- minimal repair packets;
- hotswap status;
- ICM workspace export;
- explicit human review boundaries.

External agents should use the bridge instead of reading large hub files or scanning the repository blindly.

Key files:
- `aura_agent_arena_bridge.py`
- `aura_agent_arena_cli.py`
- `aura_agent_arena_mcp.py`
- `aura_agent_arena_fireworks.py`
- `aura_hermes_arena_mode.py`
- `docs/AURA_AGENT_ARENA_BRIDGE.md`
- `docs/AURA_HERMES_ARENA_MODE.md`

### 3. Human Agent Arena

The Human Agent Arena is the collaborative human/Aura/agent command centre.

It adds:
- typed or spoken commands;
- concept workspaces that search the full CODEMAP;
- grounded projected nodes;
- a Node Inspector;
- explanations of why a node is present;
- exact-source references without full-file dumping;
- callers, callees, tests, docs, risks, and impact analysis;
- human-created ghost edges and hypotheses;
- prepared Agent Arena handoffs;
- Civic Commons interface integration.

Node origins are explicitly distinguished:
- `exact_topology_node`
- `codemap_projected_node`
- `inferred_relationship_edge`
- `ghost_hypothesis_edge`
- `unresolved_candidate`

This prevents a visual projection or hypothesis from being mistaken for a verified source fact.

Key files:
- `aura_human_agent_arena.py`
- `aura_human_agent_arena_server.py`
- `aura_human_agent_arena/`
- `aura_human_agent_concepts.py`
- `aura_node_inspector.py`
- `docs/AURA_HUMAN_AGENT_ARENA.md`
- `docs/AURA_NODE_INSPECTOR.md`

### 4. Civic Commons Arena

The Civic Commons Arena applies the same governed substrate to community planning.

```
community objective
  → IntentPacket
  → capability resolution
  → explicit civic profile set
  → persistent session
  → temporary civic organs
  → evidence and source snapshots
  → needs and offers
  → MITOSIS workstreams
  → resource matching
  → MUSIC scenario comparison
  → legal/policy/funding context
  → map and heatmap projection
  → consent and deliberation
  → preserved dissent and representation gaps
  → What-If simulation
  → pilot design
  → non-binding Civic Decision Packet
  → organ dissolution receipts
  → governed community memory
```

The Civic Arena currently includes persistent sessions with in-memory fallback, story-aware organs, real ephemeral-runtime integration, result projection, evidence snapshots, Civic UI/API integration, map views, optional bounded model brokering, and cost telemetry.

It must not:
- infer or auto-activate cultural profiles;
- treat generated scenarios as binding decisions;
- erase dissent or representation gaps;
- present fixture or snapshot material as current legal advice;
- transfer final authority to a model.

Key files:
- `aura_civic_runtime.py`
- `aura_civic_ephemeral_integration.py`
- `aura_civic_organs.py`
- `aura_civic_session_store.py`
- `aura_civic_result_projector.py`
- `aura_civic_model_broker.py`
- `aura_civic_cost_integration.py`
- `docs/AURA_CIVIC_COMMONS_ARENA.md`
- `docs/AURA_CIVIC_DATA_AND_PRIVACY.md`
- `docs/AURA_CIVIC_GOVERNANCE_AND_CONSENT.md`
- `docs/AURA_CIVIC_DEMO.md`

### 5. Anishinaabemowin Tutor

The Anishinaabemowin tutor is a domain deployment of Aura's sovereignty principles.

Its response pipeline is:
```
learner input
  → orthography normalization
  → vetted lexicon lookup
  → translation guard
  → Treaty 1 / external-dialect conflict check
  → data-governance gate
  → morphology
  → pronunciation guidance
  → response with confidence + sources + dialect notes
  → teacher review when uncertain
  → learner profile update
```

Tutor answers are not returned as unqualified strings. Responses carry:
- confidence status;
- source references;
- dialect notes;
- morphology where available;
- pronunciation guidance;
- caution labels;
- teacher-review status.

Key files:
- `aura_ojibwe_tutor_engine.py`
- `aura_language_source_registry.py`
- `aura_language_data_governance.py`
- `aura_language_privacy_policy.py`
- `aura_language_review_queue.py`
- `aura_ojibwe_dialect_profile.py`
- `aura_ojibwe_translation_guard.py`
- `aura_ojibwe_audio_consent_registry.py`
- `aura_ojibwe_curriculum_graph.py`
- `aura_ojibwe_morph_bridge.py`
- `test_aura_ojibwe_tutor.py`

### 6. Ephemeral Organ Runtime

An ephemeral organ is a temporary application assembled for one bounded objective.

```
objective
  → IntentPacket
  → capability resolution
  → semantic LEXC route
  → machine effect route
  → product automaton
  → signed/digested manifest
  → minimum capability lease
  → sandbox preparation
  → execution
  → declarative UI/result schema
  → verification
  → cost/resource record
  → capability revocation
  → dissolution receipt
```

The runtime combines:
- semantic route validation;
- deterministic machine routing;
- lifecycle transitions;
- capability subset checks;
- component digests;
- path policy;
- sandbox availability;
- resource budgets;
- verifier gates;
- human approval requirements.

The FST is an admission grammar, not a complete security sandbox. Arbitrary components require a properly restricted Wasmtime/WASI environment. If the required sandbox is unavailable, the runtime must fail closed.

Key files:
- `.aura/ephemeral_app.lexc`
- `aura_ephemeral_manifest.py`
- `aura_ephemeral_fst.py`
- `aura_ephemeral_lifecycle.py`
- `aura_ephemeral_sandbox.py`
- `aura_ephemeral_registry.py`
- `aura_ephemeral_registry_store.py`
- `aura_ephemeral_runtime.py`
- `aura_ephemeral_verifier.py`
- `docs/AURA_EPHEMERAL_ORGAN_RUNTIME.md`
- `docs/AURA_EPHEMERAL_SECURITY_MODEL.md`

---

## How the Architecture Fits Together

### Layer 1 — Intent and deterministic routing

Aura accepts ordinary language or structured intent documents in `.aura/intents/`.

The intent layer performs:
- parsing and normalization;
- polysynthetic compression;
- six-slot LEXC validation;
- deterministic machine-FST routing;
- CODEMAP localization;
- capability matching;
- cost and quality policy selection.

The canonical six-slot software constraint is:

```
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

`DIR` is the canonical execution name. `SPATIAL` and `DIRECTION` are documented aliases.

This ordering is a software design constraint inspired by Athabaskan morphotactic structure as identified by the project creator. It is not presented as a linguistically validated model of any language.

### Layer 2 — Architecture self-knowledge

Aura can inspect itself without requiring an agent to read the entire repository.

It composes:
- `.aura/CODEMAP.json` and `.aura/CODEMAP.md`;
- AST/dependency topology;
- `MODULE_MANIFEST.json`;
- Affordance Directory;
- Capability Connectome;
- Capability Lane Registry;
- Concept Workspace;
- Node Inspector;
- test and documentation relationships;
- plugin and agent-tool registries.

The **Capability Genome Resolver** answers:
- What already exists for this objective?
- Which exact functions, tests, docs, and commands are relevant?
- Why does a capability exist?
- What does it depend on?
- What should be reused?
- What is genuinely missing?
- What should not be reinvented?

### Layer 3 — Advisory cognition

Aura uses several compact advisory layers:
- VSA/HDC for semantic addressing and associative recall;
- DREAM-lite for usefulness ranking;
- QDKT for compact state and knowledge transfer;
- JSpace for active route/workspace state;
- ST3GG for visible, reversible egress compression;
- MUSIC for multi-objective comparison;
- MITOSIS for workstream decomposition;
- symbolic trace memory for continuity;
- emergent-potential scans for unwired capability hypotheses.

These layers help discover, rank, compress, and navigate. They do not authorize consequential actions.

### Layer 4 — Grounded execution

Grounded execution is based on exact evidence:
- repository-relative file paths;
- symbols and semantic IDs;
- source line ranges;
- content digests and signature hashes;
- tests and verifier output;
- source snapshots and sidecars;
- boundary contracts;
- capability leases;
- explicit consent and approval.

### Layer 5 — External workers

External LLMs and coding agents are optional workers.

Aura decides:
- whether a model is needed;
- which context it may receive;
- whether the context should be compressed;
- which tools it may use;
- what output format is accepted;
- what must be verified;
- when a human must approve.

### Layer 6 — Memory and observability

Aura records:
- route and workflow state;
- test and verifier outcomes;
- provider usage;
- cost and latency;
- quality-normalized comparisons;
- repair cost;
- scope violations;
- lifecycle transitions;
- capability revocation;
- dissolution receipts;
- governed community or learner memory.

The Empirical Cost Observatory distinguishes:
- `MEASURED`
- `TOKENIZER_EXACT`
- `DERIVED`
- `ESTIMATED`
- `UNAVAILABLE`

Cheaper output is not called a verified saving when quality or verification regresses.

---

## Core Concepts

### Polysynthetic intent parsing

Aura's intent compiler turns a long request into a compact structured packet. The packet is used for routing and context selection, not as a substitute for exact source truth.

### Three distinct FST-related layers

Aura keeps three sources and roles separate:

1. **Anishinaabemowin-derived semantic and governance alignment**
   Concepts such as mutual benefit, relational responsibility, and integrity influence module policy and headers. These alignments are design constraints and have not been formally validated as linguistic software models.
2. **Athabaskan-inspired six-slot morphotactic constraint**
   `DIR → ASP → CLASS → SUBJ → VOICE → STEM` provides canonical software ordering.
3. **Aura's machine-oriented FST routing language**
   `aura_fst_routing.py` provides deterministic symbols, hard gates, weighted alternatives, grounding blockers, test requirements, risk classes, and route decisions.

These must not be flattened into a generic claim about "Indigenous grammar."

### VSA / HDC

Aura uses high-dimensional vectors as semantic addresses and associative memory. Vectors help locate and rank related concepts under noise, but exact data remains in files, sidecars, snapshots, and databases.

### JSpace

Aura's JSpace codec stores compact active route/workspace state:
- intent;
- artifact;
- action;
- scope;
- risk;
- grounding;
- tests;
- quality;
- cost;
- selected route;
- next state;
- verifier requirement.

JSpace helps preserve continuity between planning, retrieval, worker execution, and verification. It is advisory only.

### ST3GG

ST3GG is Aura's visible, reversible compact egress and recall layer.

For Arena capsules it:
- serializes the exact original;
- computes a content hash;
- creates a compact visible-ASCII representation;
- stores the original in a local recall ledger;
- emits a recall pointer;
- enables compression only when the measured or estimated threshold is worthwhile;
- strips forbidden tokenizer carriers.

Hidden Unicode, zero-width payloads, private-use characters, bidirectional controls, tag characters, and covert carrier techniques are forbidden.

### DREAM-lite

DREAM-lite reranks candidates by usefulness and context fit. It does not override exact grounding.

### QDKT

QDKT carries compact state and knowledge-transfer events between stages. It supports continuity and memory but does not grant patch or civic authority.

### MUSIC and MITOSIS

- **MUSIC** compares multiple objectives or scenarios without reducing every decision to one score.
- **MITOSIS** decomposes a large objective into bounded workstreams or Act Capsules.

### Emergent Property Detector

Aura's emergent-potential system scans CODEMAP, topology, tests, manifests, and module evidence for capabilities that may already be latent but unwired.

The verifier:
- clusters duplicate candidates;
- suppresses mirrored paths;
- scores focus, evidence, representative quality, and novelty;
- adds advisory JSpace context;
- optionally compacts reports through ST3GG;
- records trace-memory events;
- classifies candidates conservatively.

It is strictly report-only:
```
NO_PATCHES
NO_CODE_WRITES
NO_UNIFIED_DIFF
NO_AUTOWIRING
REPORT_ONLY
```

### Capability Connectome and Genome Resolver

The Connectome explains each capability's:
- purpose;
- appropriate and inappropriate use;
- implementation modules;
- symbols;
- tests;
- docs;
- related capabilities;
- token-saving role;
- truth boundary;
- risks;
- future potential.

The Genome Resolver composes that graph with CODEMAP, topology, manifests, affordances, lanes, plugins, concept workspaces, Node Inspector, and Agent Arena tools to enforce **reuse before invention**.

---

## Architecture Self-Understanding

Aura is designed so another human or AI can become oriented without loading millions of tokens.

### Orientation order

1. Read this `README.md`.
2. Read `.aura/CODEMAP.md`.
3. Check CODEMAP topology health.
4. Query `.aura/CODEMAP.json` through Aura tools instead of opening it whole.
5. Use the Capability Genome Resolver for an objective.
6. Use the Human Agent Arena or Node Inspector for relationships and risk.
7. Read only exact source slices.
8. Read the relevant subsystem document.
9. Run focused tests and verifiers.
10. Treat historical reports and daily digests as non-canonical.

### Useful commands

```bash
# Build or fully regenerate CODEMAP and deep topology
python3 aura_codebase_navigator.py

# Query the compact map without rescanning
python3 aura_codebase_navigator.py --query "ephemeral civic runtime"

# Show stabilization and topology health
python3 -m aura_agent_arena_cli stabilization-status

# Get a compact repository orientation packet
python3 -m aura_agent_arena_cli digest

# Resolve what already exists before inventing a module
python3 -m aura_agent_arena_cli resolve-capabilities --objective "Add a governed marketplace matching Arena"

# Build the capability connectome
python3 -m aura_agent_arena_cli capability-connectome

# Open the Human Agent Arena
python3 aura_human_agent_arena_server.py --repo-root .

# Inspect a source slice instead of reading a large file
python3 -m aura_agent_arena_cli read-slice --file aura_civic_runtime.py --symbol run_civic_organ
```

### Source-of-truth order

When sources conflict, use this order:

1. exact source code and schemas;
2. tests and verifier artifacts;
3. current healthy CODEMAP/topology facts;
4. source snapshots, sidecars, and ledgers;
5. module manifests and boundary contracts;
6. current subsystem documentation;
7. this README's high-level synthesis;
8. old reports, digests, extracted text, and archived notes.

---

## Anishinaabemowin and Data Sovereignty

Aura's language architecture places community authority above model convenience.

### Governance levels

- `PUBLIC`
- `COMMUNITY_ONLY`
- `TEACHER_REVIEW`
- `RESTRICTED`
- `CEREMONIAL_PRIVATE`

Hard rules include:
- restricted and ceremonial-private material must never reach an external LLM;
- community-only and teacher-review material require an active authorized context;
- ceremonial-private material is blocked from programmatic access;
- access decisions are audited;
- learner identity and private memory must not leak through model egress;
- audio use requires explicit consent;
- uncertain language output enters review instead of being presented as authoritative.

### Tutor confidence classes

- `VERIFIED`
- `CANDIDATE_NEEDS_REVIEW`
- `BLOCKED`

### Dialect and provenance

The default tutor profile is Treaty 1 Plains Ojibwe. External resources may be used as references, but dialect differences must be disclosed rather than silently flattened.

Every approved learning object should preserve:
- source identity;
- licence;
- dialect;
- contributor and consent status;
- access class;
- review status;
- revision history;
- permitted downstream uses.

### Community data model

A production deployment should keep community language assets legally and technically separate from the general AuraOS software layer.

Community-controlled assets may include:
- recordings;
- local dialect lexicons;
- teaching materials;
- speaker corrections;
- community-only examples;
- review decisions;
- learner-community data;
- restrictions on ceremonial or sensitive knowledge.

AuraOS may provide the software infrastructure without acquiring ownership of those assets.

---

## Truth, Authority, and Safety

### Authority matrix

| Layer | May discover or rank? | May grant capabilities? | May authorize a patch or civic decision? |
|---|---|---|---|
| **VSA / semantic similarity** | Yes | No | No |
| **DREAM-lite / MUSIC** | Yes | No | No |
| **JSpace** | Yes | No | No |
| **ST3GG** | Yes | No | No |
| **QDKT / trace memory** | Yes | No | No |
| **Visual topology / generated UI** | Yes | No | No |
| **CODEMAP exact file and symbol facts** | Yes | No by itself | Evidence only |
| **FST route** | Yes | Admission only | No by itself |
| **Capability lease** | Enables bounded use | Yes, within lease | No promotion authority |
| **Tests and verifiers** | Validate | No | Evidence for approval |
| **Human/community governance** | Yes | Yes | Yes, within legal and policy authority |

### Patch authority

```
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

Patch authority requires exact source facts, tests, verifier gates, boundary contracts, and human approval.

### Ephemeral execution rule

```
ALLOW(action) =
  intent_route.complete
  AND machine_route.accepted
  AND lifecycle.transition_allowed
  AND requested_capabilities ⊆ granted_lease
  AND component_digests_verified
  AND policy_checks_pass
  AND sandbox_available
  AND verifier_gate_passes
  AND required_human_approval_present
```

### Fail-closed defaults

```
NO ROUTE            → DENY
UNKNOWN EFFECT      → DENY
NO LEASE            → DENY
HASH MISMATCH       → DENY
TTL EXPIRED         → DENY
NO REQUIRED SANDBOX → DENY
MISSING CONSENT     → DENY
UNGROUNDED AUTHORITY → DENY
```

### Human approval boundaries

Human approval is required before:
- consequential external-agent work;
- production mutation;
- commit, push, or pull request;
- live or high-risk effects;
- crystallizing an ephemeral organ into a permanent capability;
- activating community or cultural profiles;
- publishing or training on governed language data;
- converting Civic scenarios into real-world decisions.

---

## Quick Start

### Requirements

- Python 3
- Git
- Linux or Android/Termux
- CPU-first operation; external model access is optional
- additional packages from `requirements.txt` for the complete stack

### Install

```bash
# Android / Termux
pkg install python git cmake

# Clone
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

# Setup
bash setup.sh
pip install -r requirements.txt
```

### Regenerate architecture maps first

```bash
python3 aura_codebase_navigator.py
python3 -m aura_agent_arena_cli stabilization-status
```

Do not rely on graph-based workflows when topology health reports zero nodes.

### Launch the legacy REPL

```bash
python3 aura_node.py
```

### Launch the Coding Arena

```bash
python3 aura_coding_arena_server.py --host 127.0.0.1 --port 8080
```

Offline demo:

```bash
python3 aura_coding_arena_server.py --host 127.0.0.1 --port 8080 --demo
```

### Launch the Human Agent Arena

```bash
python3 aura_human_agent_arena_server.py --repo-root .
```

Default local URL: `http://127.0.0.1:8090`

### Launch the Native Cockpit

```bash
python3 -m aura_native_cockpit_server --repo-root .
```

### Use the Agent Arena CLI

```bash
python3 -m aura_agent_arena_cli digest
python3 -m aura_agent_arena_cli capability-connectome
python3 -m aura_agent_arena_cli stabilization-status
```

### Run a Civic Commons demo

```bash
python3 -m aura_agent_arena_cli civic-demo --story hairstylist
python3 -m aura_agent_arena_cli civic-demo --story youth_centre
python3 -m aura_agent_arena_cli civic-demo --story council_pulse
```

### Use the tutor from Python

```python
from aura_ojibwe_tutor_engine import OjibweTutorEngine, TutorMode

tutor = OjibweTutorEngine()
response = tutor.respond(
    "boozhoo",
    mode=TutorMode.WORD_LOOKUP,
    session_id="local-demo",
)
print(response.display())
```

---

## Common Workflows

### Orient an AI agent

```bash
python3 -m aura_agent_arena_cli stabilization-status
python3 -m aura_agent_arena_cli digest
python3 -m aura_agent_arena_cli resolve-capabilities --objective "Explain the Civic Commons ephemeral organ lifecycle"
```

Then use `read-slice` on the returned exact symbols. Do not open `aura_node.py` or other hub files in full unless no smaller grounded path exists.

### Prepare a coding task

```bash
python3 -m aura_agent_arena_cli prepare --objective "Refactor Fireworks egress" --target-file aura_agent_arena_fireworks.py
python3 -m aura_agent_arena_cli context --task-id A1 --format both
```

### Stage and verify a patch

```bash
python3 -m aura_agent_arena_cli stage-patch --task-id A1 --diff-file /tmp/aura_patch.diff
python3 -m aura_agent_arena_cli verify --scope declared
python3 -m aura_agent_arena_cli status
```

### Run an emergent capability audit

Use the report-only emergent route to ask what may already be latent in the architecture. Treat every result as a candidate requiring exact grounding and separate implementation approval.

### Plan a civic scenario

```bash
python3 -m aura_agent_arena_cli civic-create --objective "Our community needs a youth-led learning and cultural centre"
python3 -m aura_agent_arena_cli civic-status --session-id <id>
python3 -m aura_agent_arena_cli civic-mitosis --session-id <id>
python3 -m aura_agent_arena_cli civic-scenarios --session-id <id>
python3 -m aura_agent_arena_cli civic-export --session-id <id>
```

---

## CODEMAP Health and Regeneration

Aura's CODEMAP is not a static documentation file. It is generated architecture infrastructure.

### Generated artifacts

- `.aura/CODEMAP.json` — machine-readable compact map
- `.aura/CODEMAP.md` — human-readable orientation map
- `Aura_Memory/live_topology_ast.json` — runtime deep-topology artifact

### Full rebuild

```bash
python3 aura_codebase_navigator.py
```

A healthy result should report non-zero topology nodes and edges.

### Incremental refresh with topology

```bash
python3 aura_codebase_navigator.py --refresh path/to/changed_file.py --refresh-topology
```


---

## Future Arena Families

The following are architecture-supported directions, **not claims of completed production products**.

### Social / Community Discovery Arena

Instead of a static feed controlled by engagement ranking:

```
user intent
  → consented profile and context
  → governed source search
  → temporary matching organs
  → people / posts / events / knowledge constellations
  → provenance and trust views
  → user-controlled memory
  → organ dissolution
```

Potential properties:
- intent-first discovery instead of infinite scrolling;
- community-governed recommendation rules;
- visible reasons for each match;
- no automatic use of private data;
- portable preference and consent controls;
- 3D relationship constellations rather than walls of text.

### Marketplace Arena

Instead of browsing a fixed two-dimensional catalogue:

```
need / offer / budget / place / timing / values
  → verified listings and source snapshots
  → ephemeral comparison organs
  → resource matching
  → multi-objective MUSIC scenarios
  → price / availability / provenance sidecars
  → negotiation or contact handoff
```

Potential uses include local services, Indigenous businesses, skills exchange, community procurement, travel, housing, and mutual-aid resource matching.

Exact prices, dates, inventory, legal terms, and identity claims must remain in authoritative sidecars or live verified sources—not vectors or generated summaries.

### Web3 / Coordination Arena

A future coordination Arena may use:
- portable consent receipts;
- capability leases;
- signed contribution records;
- community-defined identity and reputation;
- transparent treasury or resource proposals;
- non-binding scenario comparison;
- local-first and federated governance.

Aura does not require a blockchain for every trust problem. A ledger should be used only where it provides a measurable governance benefit over a simpler signed database.

### Spatial AR / VR Arena

Aura's existing code topology and declarative ephemeral UI schemas can support future spatial interfaces where:
- files, people, services, evidence, and scenarios appear as inspectable nodes;
- selecting a node opens a temporary task-specific interface;
- the interface is generated from a declarative schema rather than arbitrary remote code;
- every visual object resolves to exact sidecar or source data;
- users can move from a 3D overview to precise text and evidence;
- accessibility includes equivalent list, table, keyboard, and screen-reader views.

The 3D/AR/VR surface must remain replaceable. Rendering is a view over truth, not the truth itself.



---

## Intent-Compiled Application Fabric

Aura's consumer-scale future is not a larger collection of monolithic websites and apps. It is an intent-compiled application fabric in which a person begins with an objective and Aura assembles a temporary, governed environment from compatible modules.

```text
person-owned or authorized data
+ current intent
+ consent, place, time, budget, and constraints
+ governed capability modules
  -> six-slot IntentPacket
  -> admitted capability graph
  -> temporary personal Arena
  -> adaptive 2D / 3D / AR / voice interface
  -> verified result or memory
  -> capability revocation and dissolution
```

The user no longer has to begin by choosing which platform will own the journey. The user states what they are trying to accomplish. Aura discovers the smallest compatible capabilities, presents their permissions and trade-offs, assembles the interface, and preserves only what the user or participants approve.

### From data silos to purpose-limited views

In the conventional platform model, a music service owns listening history, a dating service owns relationship preferences, a marketplace owns transaction history, and a social network owns the relationship graph.

In an Aura fabric, the person or governing community retains the authoritative data and grants narrow views such as:

```text
music_preferences_for_this_event
calendar_availability_for_these_people
approved_photos_for_this_memory_video
mobility_requirements_for_this_route
budget_range_for_this_purchase
```

The active intent becomes a first-class data-governance object. A module receives only the fields, duration, destination, and derivative-use rights required for the objective.

Semantic representations may locate relevant songs, people, products, memories, places, posts, or modules, but exact content and permissions remain in authoritative sidecars.

> **Intent selects. Vectors point. Sidecars prove. Governance authorizes.**

### Modules instead of totalizing applications

The reusable unit becomes a signed, bounded capability module rather than a complete platform. Modules may provide calendar access, music selection, night-sky positioning, weather, routing, reservations, camera capture, audio recording, video editing, budgeting, accessibility, consent, AR presentation, or memory timelines.

A module contract should declare:

- supported intent slots;
- input and output schemas;
- required capabilities;
- data classes and destinations;
- retention and training policy;
- offline behavior and resource budget;
- declarative interface and accessibility contract;
- verifier, rollback, licence, signature, digest, and revocation information.

Providers can contribute one excellent capability without acquiring the user's complete identity, relationship, media, location, and payment history.

### Six-slot grammar as a semantic compatibility layer

The canonical software grammar can act as a semantic ABI for independently developed capabilities:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

At the fabric level:

- `DIR` identifies target, domain, or destination;
- `ASP` identifies lifecycle, timing, duration, or completion state;
- `CLASS` identifies capability or object class;
- `SUBJ` identifies the authorized person, group, device, or institution;
- `VOICE` identifies agency, delegation, proposal, automation, or review mode;
- `STEM` identifies the core operation.

This common ordering helps Aura determine which modules can compose. It does not replace signatures, schemas, policy, sandboxes, leases, verifiers, or human approval.

### Example: Perfect Date Arena

A person could ask:

> Create a meaningful date Friday evening. We like stargazing, quiet food, live acoustic music, and personal memories. Keep it under $180, do not expose our location publicly, record only after mutual consent, and create a private short film afterward.

Aura may assemble:

- shared calendar and weather modules;
- astronomy and route modules;
- restaurant, event, music, and budget modules;
- accessibility and private-location policy modules;
- mutual media-consent, camera, audio, and video-editing modules;
- a relationship memory-timeline and private playback module.

The music provider does not need to own the calendar. The video editor does not need the complete relationship history. The reservation provider does not acquire the memory archive. Each module receives a purpose-limited view and loses its temporary lease when the Arena dissolves.

### Family and personal Arenas

The same substrate can support family reunion planning, caregiving, household coordination, emergency preparedness, shared histories, education, travel, creative projects, and private celebrations.

A family governance layer may persist while temporary sub-Arenas form for particular objectives. Children, Elders, caregivers, guests, and administrators receive different permissions rather than unrestricted access to a single family graph.

### Interfaces as replaceable projections

An Arena may render as an accessible 2D screen, a voice workflow, a 3D constellation, an AR environment, a shared wall display, or a task-specific control panel. The interface adapts to the objective, user, device, accessibility needs, attention, privacy, and surroundings.

Rendering remains a view over truth. Every spatial object must resolve to exact source data, provenance, permissions, and available actions.

The strongest expression is a **personal reality compiler**:

```text
intent
+ governed personal context
+ authorized world data
+ modular capabilities
+ chosen aesthetic and accessibility profile
  -> temporary digital environment for the present moment
```

### Creator and module economy

Developers, artists, communities, institutions, and service providers can publish narrow interoperable capabilities and Arena templates rather than rebuilding identity, messaging, media, payments, recommendations, and governance inside every app.

Potential templates include a Perfect Date Arena, Family Reunion Arena, Personal Learning Arena, Travel Arena, Community Event Arena, Emergency Preparedness Arena, Creative Production Arena, or Small Business Launch Arena.

Users should be able to fork a template, replace modules, change governance, and preserve an editable version without surrendering their data to the template publisher.

### Fractal composition

The same pattern applies at every scale:

```text
module
  -> temporary organ
  -> personal Arena
  -> family or team Arena
  -> community or institutional Arena
  -> temporary Arena of Arenas
```

A camera module inside a Date Arena and a Health Capacity Arena inside a national emergency federation use the same principles: explicit boundaries, exact sidecars, minimum leases, replaceable interfaces, purpose-limited federation, verification, approval, revocation, and dissolution.

### What must be solved

This future requires more than adding plugins to an LLM. It depends on:

- signed module manifests and supply-chain security;
- stable schemas, identity references, units, and version negotiation;
- usable consent and permission design;
- coherent generated interfaces and accessibility guarantees;
- source licences, API terms, and derivative-data controls;
- resistance to manipulative personalization and hidden advertising;
- participant rights in dating, family, health, memory, and social Arenas;
- graceful failure, module replacement, and rollback;
- economic incentives for interoperability rather than data capture.

The detailed architecture, module contract, examples, roadmap, risks, and first demonstration are documented in `docs/AURA_INTENT_COMPILED_APPLICATION_FABRIC.md`.

---

## Federated Arena Vision

Aura's long-term product model is not one omnipotent application. It is a federation of sovereign, bounded Arenas that can temporarily compose around a shared objective.

```text
Social Policy Arena ───────┐
Healthcare Arena ──────────┤
Budget Arena ──────────────┼─> Temporary Federated Objective Arena
Infrastructure Arena ──────┤      -> minimum authorized representations
Emergency Arena ───────────┤      -> cross-domain scenarios
Community Governance Arena ┘      -> human-governed action
```

Each participating Arena retains its own:

- data custody and exact source sidecars;
- legal, professional, cultural, or community authority;
- identity, privacy, and consent rules;
- capability leases and verifier gates;
- right to revoke access, disconnect, or continue offline.

The higher-order Arena receives compact intent and state capsules plus exact authorized references. It does not automatically acquire every underlying record or become a super-agent with unrestricted authority.

### Offline Disaster Coordination Arena

An offline-first Disaster Coordination Arena could compose community, shelter, health, transportation, infrastructure, supply, volunteer, NGO, and government emergency Arenas during a flood, wildfire, storm, evacuation, or communications outage.

A frontline worker should be able to see the operational constellation and answer bounded questions such as:

- Which verified shelters still have accessible capacity?
- Which nearby requests match the worker's role, equipment, and current lease?
- Where are food, water, medicine, fuel, generators, and transport available?
- Which routes are confirmed open, restricted, or unverified?
- Which assignments are already owned so effort is not duplicated?
- Which issue can be handled locally and which requires escalation?

The design should remain useful without an LLM through deterministic routing, local stores, forms, maps, resource matching, append-only event journals, store-and-forward synchronization, and human workflows. Model workers may summarize or propose, but they do not become the incident commander.

This direction aligns with the project's longstanding D.A.R.T. — Disaster Assistance Response Team — concept for First Nations and other communities.

### Government and institutional federation

A public-sector deployment could maintain separate Arenas for social policy, economic policy, budgets, healthcare, housing, infrastructure, environment, education, emergency management, Indigenous and treaty obligations, public safety, and defence logistics or civil support.

A temporary coordination Arena could examine one policy or emergency across those domains while preserving statutory authority, professional responsibility, treaties, Indigenous jurisdiction, procurement rules, privacy law, public accountability, and human decision-making.

Aura is not proposed as an autonomous government, military targeting system, weapon, or mass-surveillance platform. Defence-related direction is limited to governed logistics, readiness, humanitarian support, infrastructure, supply, and civil-emergency coordination.

### Intent-indexed social and public information network

A future Social or Public Information Arena may organize licensed public and consented information by intent rather than engagement ranking:

```text
public or consented sources
  -> connector-specific collection
  -> provenance and rights checks
  -> exact post/article/event sidecars
  -> VSA intent and topic representations
  -> time- and location-aware discussion constellations
  -> semantic zoom to exact sources
```

VSA may cluster related posts, claims, questions, events, offers, and knowledge across different vocabularies. The vector remains an address and routing layer; exact content, timestamps, permissions, deletion state, and provenance remain in authoritative sidecars or source systems.

Discussion heatmaps should represent topics, public questions, claims, and aggregate activity—not covert psychological or political profiles of individuals.

### Market differentiation

Disaster-management systems, crisis maps, common operational pictures, enterprise data integration, federated data spaces, social-listening tools, and agent frameworks already exist as separate categories.

Aura's proposed differentiation is a governed composition substrate joining these categories through:

- local-first and intermittent-network operation;
- purpose-limited Arena federation;
- compact semantic capsules with exact sidecar drill-down;
- temporary capabilities, leases, revocation, and dissolution;
- visible uncertainty, objections, and representation gaps;
- deterministic admission before model reasoning;
- human, professional, legal, Indigenous, and community authority above model confidence.

The detailed architecture, safety boundaries, competitive landscape, market directions, and demonstration roadmap are documented in `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md`.

---

## Documentation Map

### Canonical orientation

| Document | Role | Status |
|---|---|---|
| `README.md` | Central architecture, Arena model, safety, orientation, and roadmap | Canonical high-level entry point |
| `.aura/CODEMAP.md` | Generated compact repository map | Canonical only when topology health is non-zero |
| `.aura/CODEMAP.json` | Machine-readable files, symbols, commands, topology links, digests | Query through Aura tools; do not load whole by default |
| `USER_GUIDE.md` | Detailed REPL, setup, and module reference | Needs continued Arena-era refresh |
| `.aura/SECURITY.md` | Repository security constraints | Canonical security policy |
| `docs/AURA_FST_PROVENANCE_AND_SECURITY.md` | Linguistic provenance, routing-layer separation, and FST security role | Canonical |
| `docs/AURA_AGENT_ARENA_BRIDGE.md` | External-agent workflow | Canonical subsystem guide |
| `docs/AURA_HUMAN_AGENT_ARENA.md` | Human Agent Arena | Canonical subsystem guide |
| `docs/AURA_NODE_INSPECTOR.md` | Grounded node ontology and inspection | Canonical subsystem guide |
| `docs/AURA_EPHEMERAL_ORGAN_RUNTIME.md` | Ephemeral runtime lifecycle | Canonical subsystem guide |
| `docs/AURA_EPHEMERAL_SECURITY_MODEL.md` | Sandbox and capability security | Canonical subsystem guide |
| `docs/AURA_CIVIC_COMMONS_ARENA.md` | Civic product architecture | Update alongside completion changes |
| `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md` | Arena federation, disaster relief, public-sector, social-intent, and market vision | Canonical architecture-supported direction |
| `docs/AURA_INTENT_COMPILED_APPLICATION_FABRIC.md` | Modular personal Arenas, governed data views, spatial interfaces, and module economy | Canonical architecture-supported direction |
| `docs/AURA_EMPIRICAL_COST_OBSERVATORY.md` | Usage, cost, and quality measurement | Canonical subsystem guide |
| `AURA_CODING_ARENA_README.md` | Coding Arena runbook and benchmarks | Canonical subsystem guide |

### Documentation rule

A new major capability should update, in the same pull request:
1. source and tests;
2. CODEMAP with healthy topology;
3. relevant subsystem document;
4. this `README.md` when the overall architecture changes;
5. `USER_GUIDE.md` when commands or operator workflows change;
6. any completion ledger or roadmap that would otherwise become misleading.

---

## Repository Hygiene

Aura's repository is large enough that stale prose and runtime debris can misorient both humans and AI agents.

### Canonical source tree policy

Keep active architecture documentation in:
- `README.md`
- `USER_GUIDE.md`
- `.aura/`
- `docs/`
- named subsystem runbooks

Move historical material to:
```
docs/archive/
docs/archive/reports/
docs/archive/digests/
docs/archive/extracted_papers/
```

### Remove or archive after verification

The following categories should not remain mixed with canonical source:
- `*.bak`
- `*.corrupt.bak`
- editor temporary files such as `~-*`
- copied or superseded implementation reports;
- old daily digests;
- duplicate extracted text when the source paper and canonical notes already exist;
- generated benchmark reports that are no longer referenced;
- obsolete completion ledgers whose milestones have been implemented;
- runtime databases, temporary prompts, and local memory snapshots.

Examples currently deserving review include:
- `aura_topological_scanner.py.bak`
- `aura_liquid_planning_arena.py.bak`
- `.mempalace/aura_memory.db.corrupt.bak`
- `~-AuraSovereign`
- old daily digest files;
- stale Civic completion documentation;
- older architecture reports that describe Aura as REPL-only.

Use Git history as the archive for deleted source copies. Do not keep `.bak` files in the active architecture graph unless they are required test fixtures.

### Ignore policy

Runtime and generated state should generally be ignored unless it is an intentional reproducible fixture:
- `Aura_Memory/`
- local SQLite databases and WAL files;
- temporary organ directories;
- local ST3GG recall ledgers;
- provider usage caches;
- screenshots;
- transient topology files;
- private learner or community data.

Curated public fixtures should be clearly labelled and separated from live or private data.

---

## Prior Art

AuraOS maintains a seven-paper defensive prior-art stack. The papers describe the conceptual lineage of the substrate; current source, tests, and verifiers determine implemented behavior.

| Paper | Main claim family | Record |
|---|---|---|
| **Protocol-layer innovations** | HIVP, micro-module crystallization, resonant tests, thermal-cost API arbitration, deterministic compression, local VSA compute mesh, bounded self-healing | [Zenodo 20695562](https://zenodo.org/records/20695562) |
| **Enhanced FST and topology** | FST lexicon, resonance topology, FST impact analysis | [Zenodo 20682051](https://zenodo.org/records/20682051) |
| **FST routing and self-refactoring** | routing core, 3D topology resonance, self-refactoring incubator | [Zenodo 20681601](https://zenodo.org/records/20681601) |
| **Memristive and rendering upgrades** | memristive hyper-epochs, timestep-aware SVD quantization, Gaussian/VSA rendering dynamics | [Zenodo 20673206](https://zenodo.org/records/20673206) |
| **Liquid Internet** | VSA-addressed routing and naming without IP/DNS dependency at the cognitive layer | [Zenodo 20659314](https://zenodo.org/records/20659314) |
| **Holographic swarm systems** | holographic headers, fractal ledger, swarm learning, VSA rendering, FST narrative | [Zenodo 20657391](https://zenodo.org/records/20657391) |
| **Foundation** | polysynthetic LLM egress, dual linguistic cortex, sparse sweeps, QDKT, topology, hotswap, edge design | [Zenodo 20635424](https://zenodo.org/records/20635424) |

Prior-art papers, implementation reports, and extracted text are reference material. They do not override current code, tests, licences, or governance requirements.

---

## Testing and Verification

Run focused tests for the subsystem being changed.

Examples:

```bash
# Coding and agent Arenas
python3 -m pytest tests/test_aura_coding_arena_3d.py tests/test_aura_coding_arena_grounding.py test_aura_coding_arena_workflow.py -q

# Human Agent Arena and Node Inspector
python3 -m pytest tests/test_aura_human_agent_concepts.py tests/test_aura_node_inspector.py -q

# Ephemeral runtime
python3 -m pytest tests/test_aura_ephemeral_fst.py tests/test_aura_ephemeral_lifecycle.py tests/test_aura_ephemeral_manifest.py tests/test_aura_ephemeral_runtime.py tests/test_aura_ephemeral_sandbox.py -q

# Civic Commons
python3 -m pytest tests/test_aura_civic_commons_arena.py tests/test_aura_civic_completion.py tests/test_aura_civic_snapshots_and_store.py -q

# Anishinaabemowin tutor
python3 -m pytest test_aura_ojibwe_tutor.py -q
```

Do not publish aggregate pass counts unless they were rerun on the referenced commit and the exact command is recorded.

---

## Licensing

AuraOS is released under the **GNU Affero General Public License v3.0**. Modified network deployments are subject to AGPL source-availability requirements.

### Third-party language dependency

The repository includes or integrates the OjibweMorph finite-state resource under **CC BY-NC-SA 4.0**.

That licence is:
- attribution-required;
- non-commercial;
- share-alike.

Do not assume the integrated morphology component may be used in a commercial product. Obtain separate commercial permission, isolate the non-commercial component, or develop a properly authorized Treaty 1-controlled alternative before commercial deployment.

### Community data

The AuraOS software licence does not grant rights to:
- community-owned language data;
- recordings;
- cultural knowledge;
- local dialect resources;
- learner data;
- private or ceremonial material;
- contributor identities or consent records.

Those assets require separate governance, consent, and licensing instruments.

---

## Contributing and AI-Agent Rules

Before proposing a new module:

1. run topology health;
2. query CODEMAP;
3. resolve existing capabilities;
4. inspect related nodes, tests, and docs;
5. reuse existing capability lanes where possible;
6. open a bounded Arena;
7. preserve exact grounding;
8. stage rather than mutate production directly;
9. run focused tests and verifiers;
10. obtain human approval;
11. refresh CODEMAP with topology;
12. update canonical documentation.

Never:
- treat JSpace, VSA, ST3GG, DREAM, QDKT, screenshots, or summaries as patch authority;
- dump secrets or private memory;
- send governed language data to an external model;
- auto-activate cultural profiles;
- silently broaden scope after a verifier failure;
- invent symbols or dependencies;
- keep a temporary organ alive beyond its lease;
- auto-crystallize an experimental capability;
- describe fixture civic evidence as current legal advice;
- present estimated savings as measured.

---

## Project Status

AuraOS is an active research and development system.

Implemented components include:
- polysynthetic intent ingestion;
- semantic LEXC and deterministic machine-FST routing;
- high-dimensional associative memory;
- CODEMAP and architecture inspection;
- Capability Connectome and Genome Resolver;
- Coding Arena;
- Agent Arena Bridge;
- Human Agent Arena and Node Inspector;
- Coding Workbench workflow gates;
- visible ST3GG Arena egress;
- compact JSpace route state;
- emergent-capability discovery and verification;
- Ephemeral Organ Runtime;
- Civic Commons Arena;
- Anishinaabemowin tutor and data-governance stack;
- empirical token, cost, latency, and quality observability.

Important production-hardening work remains, including:
- healthy CODEMAP regeneration after major merges;
- stronger documentation synchronization;
- authentication and authorization for network-exposed interfaces;
- production sandbox deployment and testing;
- live-source freshness and legal review for Civic deployments;
- formal community governance agreements for language data;
- commercial licensing resolution for third-party language resources;
- broader independent benchmarks and security review;
- cleanup of deprecated reports, backups, and runtime artifacts.

---

## Contact

- **Founder:** Dallas Courchene
- **GitHub:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)
- **Email:** aura.os.q@gmail.com

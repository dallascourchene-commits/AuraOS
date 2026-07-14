# AuraOS Architecture

> **Canonical compact architecture anchor for humans and AI agents**
>
> This document explains how AuraOS is organized, which layers are authoritative, how the Arenas fit together, and how to navigate the repository without loading the entire codebase.

**Architecture audit:** June 14–July 14, 2026 (through draft PR #92)
**CODEMAP state:** 804 indexed files · 7,019 topology nodes · 14,526 topology edges
**Topology source:** `compiled_deep_topology`

---

## 1. Architectural Identity

AuraOS is a **sovereign, local-first, Arena-based cognitive operating substrate**.

It is not:

- a single language model;
- a conventional chatbot;
- a monolithic autonomous agent;
- a visual interface wrapped around an LLM;
- a system where semantic similarity can authorize code changes;
- a system where generated civic scenarios replace human or community decisions.

Aura compiles human intent into a governed workflow:

```text
OBJECTIVE
  → structured IntentPacket
  → semantic and machine FST routing
  → capability discovery and reuse
  → grounded micro-context
  → bounded Arena
  → temporary capability leases / ephemeral organs
  → optional external workers
  → exact verification
  → human or community approval
  → governed memory, telemetry, and dissolution receipts
```

The central invariant is:

> **Meaning may guide retrieval. Only grounded evidence and authorized governance may grant authority.**

---

<!-- PR92:ARCH_EVOLUTION:START -->
## 1A. Implemented Evolution During the Architecture Audit

The June 14–July 14, 2026 commit/PR audit shows that Aura evolved from a substrate-and-router core into a governed, self-describing application fabric. The authoritative implementation is organized by layer rather than by pull-request number:

| Layer | Implemented current surface | Authority boundary |
|---|---|---|
| Intent and route | Canonical six-slot LEXC, machine FST, guarded WFST challenges, C1 context capsules, and C2 live-route capsules | Grammar and route acceptance constrain work; they do not create permission |
| Grounding and self-model | CODEMAP, compiled topology, Topological Context Anchor, Capability Connectome, Capability Genome Resolver, Model Cognome | Current exact spans, hashes, graph digests, tests, and manifests outrank semantic inference |
| Arenas and temporary applications | Coding, Agent, Human Agent, Liquid Planning, Civic Commons, Experience/Crucible, ephemeral organs | Minimum leases, lifecycle enforcement, verifier gates, human/community authority, mandatory dissolution |
| Learning and procedure evidence | Experience V2, Crucible candidate review, C3 isolated trials, replay/shadow/drift evaluation | Candidates and trials are proposal-only; no automatic procedure or policy activation |
| Model execution | Legacy calibration router plus governed adaptive `SHADOW` and authorized `PAIRED_LIVE` routes | External models are workers; live calls require admission, authorization, current evidence, and approved egress |
| Compression and continuity | Reversible context crushing, visible ST3GG, JSpace, DREAM-lite, QDKT, MUSIC, MITOSIS | Compression and ranking remain advisory and recoverable |
| Observability and federation | Usage normalization, pricing snapshots, cost attribution, policy observations, signed/redacted federation bundles | Unknown cost stays unknown; remote evidence cannot silently become local policy |
| Human inspection and deployment | Native Cockpit, Coding Workbench, Human Agent Arena, unified Showcase, Winnipeg demo, Docker/Render/Hugging Face surfaces | Presentation is not authority; guided gates remain explicit |

This audit supersedes older summaries that described only the pre-Arena or pre-Cognome architecture. Historical reports remain useful as provenance, not as current system maps.
<!-- PR92:ARCH_EVOLUTION:END -->

## 2. Truth and Authority Model

Aura deliberately separates **advisory cognition** from **authoritative evidence**.

### 2.1 Advisory layers

These layers may help discover, rank, compress, remember, or visualize:

- VSA / HDC resonance;
- DREAM and DREAM-lite ranking;
- QDKT state and knowledge-transfer events;
- JSpace route/workspace state;
- ST3GG compact recall handles;
- MUSIC comparison;
- MITOSIS decomposition;
- semantic similarity;
- visual topology;
- generated interface schemas;
- screenshots and summaries;
- emergent-capability hypotheses;
- inferred or ghost edges.

They may not authorize production mutation, civic decisions, cultural-profile activation, or access to restricted data.

### 2.2 Authoritative layers

Authority is grounded in:

- exact repository-relative file paths;
- exact symbols and semantic IDs;
- source line ranges;
- content digests and signature hashes;
- current CODEMAP and compiled topology facts;
- tests and verifier outputs;
- source snapshots and exact sidecars;
- manifests and boundary contracts;
- explicit capability leases;
- consent records;
- human, teacher, speaker, or community approval;
- applicable legal and governance authority.

### 2.3 Patch authority

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

No advisory layer becomes patch authority.

### 2.4 Consequential-action rule

```text
ALLOW(action) =
    intent_route.complete
    AND machine_route.accepted
    AND lifecycle.transition_allowed
    AND requested_capabilities ⊆ granted_lease
    AND component_digests_verified
    AND policy_checks_pass
    AND required_sandbox_available
    AND verifier_gate_passes
    AND required_human_approval_present
```

Unknown, ungrounded, expired, ambiguous, or unauthorized actions fail closed.

---

## 3. Architectural Planes

AuraOS is best understood as eight cooperating planes.

```text
┌──────────────────────────────────────────────────────────────┐
│ 1. HUMAN / COMMUNITY INTENT                                  │
├──────────────────────────────────────────────────────────────┤
│ 2. INTENT COMPILATION AND FST ROUTING                        │
├──────────────────────────────────────────────────────────────┤
│ 3. SELF-MODEL, CAPABILITY DISCOVERY, AND GROUNDING           │
├──────────────────────────────────────────────────────────────┤
│ 4. ADVISORY COGNITION AND COMPRESSION                        │
├──────────────────────────────────────────────────────────────┤
│ 5. ARENAS AND EPHEMERAL ORGANS                               │
├──────────────────────────────────────────────────────────────┤
│ 6. EXTERNAL WORKERS AND CONTROLLED EGRESS                    │
├──────────────────────────────────────────────────────────────┤
│ 7. VERIFICATION, APPROVAL, MEMORY, AND OBSERVABILITY         │
├──────────────────────────────────────────────────────────────┤
│ 8. DOMAIN DEPLOYMENTS: LANGUAGE, CIVIC, RESEARCH, MESH, AR   │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Plane 1 — Human and Community Intent

Aura accepts objectives through multiple surfaces:

- structured `.aura/intents/*.aura.md` files;
- Native Cockpit commands;
- Agent Arena CLI or MCP calls;
- Coding Arena graph interactions;
- Human Agent Arena typed or spoken commands;
- Civic Commons sessions;
- the legacy `aura_node.py` REPL;
- direct Python APIs such as the Anishinaabemowin tutor.

Intent is not treated as permission. It is a request that must be parsed, routed, grounded, bounded, and approved.

Primary modules:

- `aura_intent_ingestion.py`
- `aura_native_cockpit.py`
- `aura_native_cockpit_server.py`
- `aura_agent_arena_cli.py`
- `aura_human_agent_arena.py`
- `aura_civic_runtime.py`
- `aura_node.py` — legacy REPL/orchestrator; never load whole for normal agent work

---

## 5. Plane 2 — Intent Compilation and FST Routing

### 5.1 Polysynthetic intent packet

Aura compresses natural-language objectives into structured packets so routing and retrieval do not depend on repeating a large prompt.

Primary modules:

- `aura_substrate.py`
- `aura_intent_ingestion.py`
- `aura_positional_parser.py`
- `gateway.py`

### 5.2 Three distinct FST-related layers

These layers have different origins and must not be conflated.

#### A. Anishinaabemowin-derived governance alignment

Project-defined alignments such as mutual benefit, relational responsibility, and integrity appear in architecture and module headers.

They are design and governance constraints. They are not presented as formally validated linguistic software behavior.

#### B. Athabaskan-inspired six-slot software constraint

Canonical order:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

Aliases:

- `DIR`: `SPATIAL`, `DIRECTION`
- `ASP`: `ASPECT`
- `CLASS`: `CLASSIFIER`
- `SUBJ`: `SUBJECT`

Primary implementation:

- `aura_lexc.py`
- `aura_positional_parser.py`
- relevant `.lexc` files under `.aura/`

#### C. Aura machine-oriented FST routing

The machine routing language represents:

- intent;
- artifact;
- action;
- scope;
- risk;
- grounding;
- tests;
- quality;
- cost;
- route decision;
- next state.

Primary module:

- `aura_fst_routing.py`

The FST is an **admission grammar**. It may reject or constrain an action. It may not create authority that was never granted.

---

## 6. Plane 3 — Self-Model, Capability Discovery, and Grounding

Aura is designed to explain:

- what exists;
- where it exists;
- why it exists;
- what depends on it;
- which tests and documents support it;
- what may break if it changes;
- which internal tools already solve an objective;
- what is genuinely missing.

### 6.1 CODEMAP

Generated artifacts:

- `.aura/CODEMAP.json` — machine-readable file, symbol, command, digest, and topology index
- `.aura/CODEMAP.md` — compact human orientation map
- `Aura_Memory/live_topology_ast.json` — generated runtime topology

Primary generator:

- `aura_codebase_navigator.py`

Current healthy map:

```text
804 indexed files · 7,019 topology nodes · 14,526 topology edges
source: compiled_deep_topology
```

### 6.2 Deep topology

Primary modules:

- `aura_topological_scanner.py`
- `aura_topology_health.py`
- `aura_topological_context_anchor.py`
- `aura_topology_analyzer.py`
- `aura_topology_manager.py`
- `aura_understand_graph_bridge.py`

Node identifier contract:

```text
<file>::<symbol>
```

The current highest-degree hubs include:

- `aura_node.py`
- `aura_agent_arena_cli.py`
- `aura_live_architect.py`
- `aura_architect_loop.py`
- `aura_fst_routing.py`
- `aura_scientific_memory.py`
- `aura_human_agent_arena.py`
- `aura_music_coding_arena.py`
- `aura_topological_context_anchor.py`
- `aura_understand_graph_bridge.py`

High degree does not mean “read this file first.” It means the file is a hub and should normally be approached through symbols and slices.

### 6.3 Capability self-description

| System | Purpose |
|---|---|
| Affordance Directory | Explains which internal tool to use, when to use it, and when not to |
| Capability Connectome | Living graph of capabilities, relationships, tests, docs, risk, and token-saving roles |
| Capability Genome Resolver | Composes CODEMAP, topology, manifests, affordances, lanes, plugins, concepts, Node Inspector, and Agent Arena tools |
| Concept Workspace | Builds a bounded workspace around a human concept |
| Node Inspector | Explains why a node is present, exact grounding, relationships, risks, and safe next actions |
| Understand Graph | Builds layered graph packets, tours, and changed-file impact views |
| Module Manifest | Tracks module ownership and declared capabilities |
| `[AURA_MASTER_KEY]` headers | Cheap local metadata for dependencies, functions, tier, and alignment |

Primary modules:

- `aura_affordance_directory.py`
- `aura_capability_connectome.py`
- `aura_capability_resolver.py`
- `aura_human_agent_concepts.py`
- `aura_node_inspector.py`
- `aura_understand_graph_bridge.py`
- `aura_module_manifest.py`

### 6.4 Reuse-before-invention rule

Before creating a new module:

1. validate topology health;
2. query CODEMAP;
3. resolve capabilities;
4. inspect the relevant concept workspace;
5. identify existing functions, tests, docs, and lanes;
6. reuse or compose existing capabilities;
7. create a new capability only when the gap is grounded.

---

## 7. Plane 4 — Advisory Cognition and Compression

### 7.1 VSA / HDC

High-dimensional vectors provide semantic addresses, noise-tolerant recall, and relationship ranking.

Exact prices, source text, legal facts, code, permissions, and private data must remain in authoritative sidecars or source stores.

Primary modules include:

- `aura_core.py`
- `aura_substrate.py`
- `gateway.py`
- `aura_hv_cache.py`
- `aura_associative_core.py`

### 7.2 JSpace

JSpace preserves compact active route/workspace state:

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

Primary module:

- `aura_jspace_codec.py`

JSpace is continuity state, not hidden reasoning or patch authority.

### 7.3 ST3GG

ST3GG is visible, reversible compression and recall.

Arena egress:

1. serializes the exact original capsule;
2. computes a hash;
3. creates a compact visible-ASCII representation;
4. stores the original in a local recall ledger;
5. emits a pointer;
6. enables compression only when savings pass the configured threshold;
7. strips forbidden tokenizer carriers.

Primary modules:

- `aura_arena_st3gg_codec.py`
- `aura_st3gg_recall.py`
- `aura_tokenizer_guard.py`

Forbidden:

- zero-width payloads;
- private-use carriers;
- bidi controls;
- tag characters;
- hidden Unicode;
- covert steganographic instruction channels.

### 7.4 DREAM, QDKT, MUSIC, and MITOSIS

| Layer | Role |
|---|---|
| DREAM / DREAM-lite | Usefulness and context-fit ranking |
| QDKT | Compact state and knowledge-transfer memory |
| MUSIC | Multi-objective comparison and scenario ranking |
| MITOSIS | Objective decomposition into bounded workstreams or child capsules |

Primary modules:

- `aura_dream_engine.py`
- `aura_dream_retrieval.py`
- `aura_qdkt.py`
- `aura_music_coding_arena.py`
- `aura_mitosis.py`

### 7.5 Emergent capability detector

The emergent-potential system searches for plausible unwired combinations among existing abilities.

The verifier:

- clusters duplicates;
- suppresses mirrored paths;
- scores evidence, focus, novelty, and representative quality;
- adds advisory JSpace state;
- may compact reports through ST3GG;
- records trace events;
- returns conservative classifications.

Safety contract:

```text
NO_PATCHES
NO_CODE_WRITES
NO_UNIFIED_DIFF
NO_AUTOWIRING
REPORT_ONLY
```

Primary modules:

- `aura_emergent_potential_repl.py`
- `aura_emergent_result_verifier.py`
- `aura_emergent_capability_auditor.py`

---

## 8. Plane 5 — Arena Architecture

An Arena is a bounded workspace that connects intent, exact evidence, capabilities, constraints, workers, verification, and approval.

### 8.1 Coding Arena

Purpose:

- select a small code region;
- inspect topology;
- identify files, symbols, tests, and relationships;
- detect candidate faults;
- compile Action Capsules;
- simulate route choices;
- prepare grounded worker context.

Primary modules:

- `aura_coding_arena_3d.py`
- `aura_coding_arena_server.py`
- `aura_coding_arena_grounding.py`
- `aura_coding_arena_workflow.py`
- `aura_builder_context.py`

The visualization is a view. Exact source facts remain authoritative.

### 8.2 Agent Arena Bridge

Purpose:

- let external coding agents drive through Aura;
- provide compact repository orientation;
- search CODEMAP;
- authorize bounded source slices;
- prepare micro-context;
- stage patches;
- run verifiers and tests;
- emit repair packets;
- expose promotion readiness;
- export ICM review workspaces.

Primary modules:

- `aura_agent_arena_bridge.py`
- `aura_agent_arena_cli.py`
- `aura_agent_arena_mcp.py`
- `aura_agent_arena_fireworks.py`
- `aura_hermes_arena_mode.py`

No tool may directly promote model output to production.

### 8.3 Human Agent Arena

Purpose:

- human-led exploration of the architecture;
- typed or spoken concept commands;
- CODEMAP-projected nodes;
- exact-source inspection;
- caller/callee/test/doc expansion;
- risk and impact analysis;
- human-created ghost hypotheses;
- prepared Agent Arena handoffs;
- Civic Commons interface.

Primary modules:

- `aura_human_agent_arena.py`
- `aura_human_agent_arena_server.py`
- `aura_human_agent_arena/`
- `aura_human_agent_concepts.py`
- `aura_node_inspector.py`

Node origins:

- `exact_topology_node`
- `codemap_projected_node`
- `inferred_relationship_edge`
- `ghost_hypothesis_edge`
- `unresolved_candidate`

### 8.4 Liquid Planning Arena

Provides domain-neutral primitives:

- `ActionCapsule`
- `BoundaryContract`
- `ArenaLease`
- shared action queues;
- scoped work;
- world-state deltas;
- adapter-specific verification.

Primary module:

- `aura_liquid_planning_arena.py`

### 8.5 Civic Commons Arena

Transforms a community objective into a transparent, non-binding planning environment.

```text
objective
  → explicit profiles
  → persistent session
  → temporary civic organs
  → evidence and source snapshots
  → needs and offers
  → MITOSIS workstreams
  → resource matching
  → MUSIC scenarios
  → legal/policy context
  → map projection
  → consent and deliberation
  → preserved dissent
  → What-If
  → pilot
  → Civic Decision Packet
  → dissolution receipts
  → governed memory
```

Primary modules:

- `aura_civic_runtime.py`
- `aura_civic_ephemeral_integration.py`
- `aura_civic_organs.py`
- `aura_civic_session_store.py`
- `aura_civic_result_projector.py`
- `aura_civic_model_broker.py`
- `aura_civic_cost_integration.py`
- `aura_civic_memory.py`

Civic outputs remain non-binding. Aura is not legal advice and does not replace community authority.

---

## 9. Ephemeral Organ Runtime

An ephemeral organ is a temporary application assembled from existing capabilities for one objective.

```text
objective
  → capability resolution
  → six-slot semantic route
  → machine effect route
  → product automaton
  → manifest and digest
  → explicit lease
  → sandbox
  → execution
  → declarative result/UI schema
  → verification
  → result projection
  → capability revocation
  → dissolution receipt
```

Primary modules:

- `.aura/ephemeral_app.lexc`
- `aura_ephemeral_adapter_registry.py`
- `aura_ephemeral_manifest.py`
- `aura_ephemeral_manifest_finalizer.py`
- `aura_ephemeral_fst.py`
- `aura_ephemeral_lifecycle.py`
- `aura_ephemeral_lifecycle_enforcer.py`
- `aura_ephemeral_path_policy.py`
- `aura_ephemeral_sandbox.py`
- `aura_ephemeral_registry.py`
- `aura_ephemeral_registry_store.py`
- `aura_ephemeral_runtime.py`
- `aura_ephemeral_verifier.py`

Security principles:

- no ambient authority;
- requested capabilities must be a subset of the lease;
- unknown routes deny;
- path escapes deny;
- expired leases deny;
- arbitrary native execution requires a properly restricted Wasmtime/WASI runtime;
- if the required sandbox is unavailable, fail closed;
- crystallization is a proposal, never automatic promotion;
- dissolution is mandatory.

---

## 10. Plane 6 — External Workers and Controlled Egress

External models are optional workers, not Aura's memory or authority.

Possible workers include:

- Hermes;
- Codex;
- Fireworks-backed workers;
- MCP clients;
- hosted provider panels;
- local models.

Aura controls:

- whether a model is required;
- which worker tier is allowed;
- the maximum context;
- which exact source slices are exposed;
- whether ST3GG compression is worthwhile;
- which capabilities and tools are leased;
- accepted output format;
- verification requirements;
- human approval checkpoints.

Primary modules:

- `aura_llm_egress.py`
- `aura_agent_arena_bridge.py`
- `aura_agent_arena_fireworks.py`
- `aura_hermes_arena_mode.py`
- `aura_fusion.py`
- `aura_api_rotator.py`
- `aura_tokenizer_guard.py`

<!-- PR92:MODEL_COGNOME:START -->
### 10.1 Model Cognome and governed adaptive routing

The Model Cognome is the evidence and profile layer used to reason about model capabilities without treating model identity, benchmark reputation, or semantic fit as permission. Current routing composes:

```text
objective + explicit targets
  → Capability Genome Resolver
  → Capability Connectome path packet
  → Topological Context Anchor
  → exact source spans, hashes, callers, callees, tests, dependencies
  → graph-bound TaskContext
  → Model Cognome candidate profiles
  → hard admission and policy checks
  → LEGACY, SHADOW, or explicitly authorized PAIRED_LIVE execution
  → unified observations, verifier result, replay/shadow evidence
```

Public compatibility modes:

- `LEGACY`: existing calibration-ledger behavior; default and rollback path.
- `SHADOW`: plans and records a governed route; provider calls are forbidden.
- `PAIRED_LIVE`: performs one explicitly authorized comparison route.

Execution semantics:

- `ZERO_MODEL`: injected deterministic executor only.
- `DIRECT`: one admitted model followed by the named verifier.
- `CASCADE`: fallback only after call failure or verifier rejection.
- `PANEL`: at least two panel profiles plus one judge profile through AuraFusion.

`PAIRED_LIVE` authorization is content-addressed and bound to the named approver, verifier, purpose digest, current Capability Connectome graph digest, allowed routes/profiles, nonce, issue/expiry times, and maximum calls. The router revalidates current capability-path evidence and endpoint lifecycle before execution and fallback calls. Forced-model selection is an override request, never an admission bypass.

Primary modules:

- `aura_model_cognome.py`
- `aura_model_cognome_bridge.py`
- `aura_model_cognome_store_io.py`
- `aura_model_cognome_execution_auth.py`
- `aura_shadow_model_router.py`
- `aura_adaptive_model_router.py`
- `aura_adaptive_model_executor.py`
- `aura_adaptive_fusion.py`
- `aura_router_adaptive_compat.py`
- `aura_ai_router.py`
- `docs/AURA_MODEL_COGNOME_ADAPTIVE_ROUTER.md`

Explicit non-authorities:

```yaml
legacy_default: true
shadow_provider_calls: false
paired_live_requires_authorization: true
automatic_policy_activation: false
automatic_policy_promotion: false
automatic_source_mutation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
patch_authority: exact_source_spans_and_hashes_only
```
<!-- PR92:MODEL_COGNOME:END -->

Secrets must come from environment variables or ignored local secret files. They must never be written to CODEMAP, prompts, ledgers, or responses.

---

## 11. Plane 7 — Verification, Approval, Memory, and Observability

### 11.1 Verification

Verification may include:

- focused tests;
- declared tests;
- full test suites when appropriate;
- AST checks;
- boundary-contract checks;
- source-hash checks;
- topology/world-state deltas;
- result-schema validation;
- cost and resource-budget checks;
- dissolution verification.

Primary modules:

- `aura_validation.py`
- `aura_patch_quality_gate.py`
- `aura_resonant_test_oracle.py`
- `aura_ephemeral_verifier.py`
- `aura_civic_result_projector.py`
- `aura_topology_health.py`

### 11.2 Workflow gates

The Coding Workbench follows a checkpoint sequence:

```text
OPEN_WORKSPACE
→ SCOPE_TASK
→ FILTER_CONTEXT
→ LOCALIZE_CODE
→ RANK_CODE_REGIONS
→ SLICE_CONTEXT
→ BUILD_CHANGE_GRAPH
→ DETECT_REFACTOR_CANDIDATES
→ SPLIT_WORK
→ CREATE_ACT_CAPSULES
→ PREPARE_AGENT_HANDOFF
→ STAGE_PATCH
→ RUN_TESTS
→ VERIFY_PATCH
→ HUMAN_REVIEW
→ PR_READY
```

Exceptional gates include:

- `NEED_TOPOLOGY_REPAIR`
- `BLOCKED_SECURITY_RISK`

### 11.3 Memory

Memory is separated by role:

- exact SQLite/JSONL records;
- QDKT transfer state;
- symbolic trace memory;
- scientific paper memory;
- ST3GG recall ledgers;
- governed civic memory;
- learner profiles;
- review queues;
- ephemeral lifecycle receipts.

Vector memory is a pointer and ranking substrate. It does not replace exact stores.

### 11.4 Cost observability

The Empirical Cost Observatory records:

- provider usage;
- tokenizer-exact or estimated tokens;
- cost;
- latency;
- verified success;
- quality;
- repair cost;
- context lines;
- scope violations;
- attribution by stage.

Measurement classes:

- `MEASURED`
- `TOKENIZER_EXACT`
- `DERIVED`
- `ESTIMATED`
- `UNAVAILABLE`

A cheaper failed run cannot claim verified savings.

Primary modules:

- `aura_empirical_cost_ledger.py`
- `aura_cost_attribution.py`
- `aura_cost_telemetry_events.py`
- `aura_usage_normalizer.py`
- `aura_pricing_registry.py`

---

<!-- PR92:LEARNING_GATES:START -->
### 11.5 Experience, Crucible, and C1/C2/C3 evidence gates

Aura's recent learning path is deliberately split so experience cannot silently become procedure or policy:

```text
observed execution
  → Experience V2 record
  → Crucible candidate/proposal
  → C1 graph-bound context capsule
  → C2 explicitly authorized live route capsule
  → C3 isolated trial and procedure evidence
  → replay and SHADOW comparison
  → drift/quality/cost/verifier evidence
  → human-reviewed promotion proposal
```

Key boundaries:

- experience storage is descriptive, not executable authority;
- Crucible outputs are candidates requiring review;
- C1 packets bind context to exact topology and evidence digests;
- C2 live routes require explicit authorization, approved egress, and verifier identity;
- C3 trials are isolated and may propose procedures but never auto-activate them;
- replay, shadow, drift, and federation evidence may support a promotion proposal only;
- policy activation remains separate from model execution and requires human review.

Primary surfaces include `aura_experience_v2.py`, Crucible modules, route-capsule schemas, governed trial/procedure modules, policy observation stores, and the Model Cognome evidence bridge.
<!-- PR92:LEARNING_GATES:END -->

## 12. Plane 8 — Domain Deployments

### 12.1 Anishinaabemowin tutor

The tutor applies Aura's provenance and sovereignty rules to language learning.

```text
learner input
  → normalization
  → vetted-source lookup
  → translation guard
  → dialect conflict check
  → data-governance gate
  → morphology
  → pronunciation guidance
  → confidence + sources + dialect notes
  → teacher review if uncertain
  → learner-profile update
```

Primary modules:

- `aura_ojibwe_tutor_engine.py`
- `aura_language_source_registry.py`
- `aura_language_data_governance.py`
- `aura_language_privacy_policy.py`
- `aura_language_review_queue.py`
- `aura_ojibwe_dialect_profile.py`
- `aura_ojibwe_dialect_conflict_resolver.py`
- `aura_ojibwe_translation_guard.py`
- `aura_ojibwe_audio_consent_registry.py`
- `aura_ojibwe_curriculum_graph.py`
- `aura_ojibwe_morph_bridge.py`
- `aura_ojibwe_lexicon_sidecar.py`

Governance levels:

- `PUBLIC`
- `COMMUNITY_ONLY`
- `TEACHER_REVIEW`
- `RESTRICTED`
- `CEREMONIAL_PRIVATE`

Restricted and ceremonial-private material must never reach external models.

### 12.2 Research and scientific memory

Primary systems:

- arXiv foraging and chronological backtracking;
- metadata-first ingestion;
- opt-in PDF processing;
- formula-preserving paper memory;
- research manifests;
- SkillWeaver gating;
- compact RAEC/VSA context retrieval.

Primary modules:

- `arxiv_forager.py`
- `aura_scientific_memory.py`
- `aura_paper_memory.py`
- `aura_research_manifest_ingest.py`
- `aura_skill_weaver.py`

### 12.3 Mesh and federation

Primary systems:

- local peer discovery;
- bounded compute offload;
- VSA-addressed routing concepts;
- signed/redacted capsule federation;
- swarm planning;
- thermal and trust-aware selection.

Primary modules:

- `aura_mesh.py`
- `aura_federation.py`
- `aura_swarm.py`
- `aura_goal_planner.py`
- `aura_blockchain/`

### 12.4 Spatial and AR interfaces

Aura can project code, civic evidence, and future domain objects into spatial views.

Rules:

- rendering is replaceable;
- visual nodes resolve to exact source or sidecar data;
- generated UIs are declarative;
- accessibility requires equivalent text, list, and table views;
- the visual surface never becomes authority.

Primary modules:

- `aura_coding_arena_3d.py`
- `aura_topology_ws_bridge.py`
- `aura_vsa_rendering.py`
- `aura_human_agent_arena/`

---

<!-- PR92:SHOWCASE_DEPLOYMENT:START -->
### 12.5 Unified Showcase and deployment surfaces

The unified Showcase is the human inspection layer for architecture, guided gates, observability, Winnipeg pathways, and demonstration projects. Recent deployment work adds Docker, Render, and Hugging Face-compatible launch surfaces around the same governed runtime rather than creating a second authority path.

Rules:

- demo fixtures and seeded Winnipeg data must be labelled as fixtures or snapshots;
- observability panels report evidence and measurement class, not guaranteed savings;
- a UI approval control must call the same underlying gate as CLI/API workflows;
- deployment configuration may expose a surface but may not weaken leases, egress policy, verifier requirements, or human/community authority;
- showcase rendering and narrative summaries remain non-authoritative projections.

Primary surfaces include `aura_showcase_server.py`, showcase UI assets, guided-gate APIs, deployment manifests, and the Winnipeg demo project.
<!-- PR92:SHOWCASE_DEPLOYMENT:END -->

## 13. Canonical Files and Generated Artifacts

### 13.1 Canonical architecture and governance

- `README.md`
- `.aura/ARCHITECTURE.md`
- `.aura/SECURITY.md`
- `.aura/AURA.md`
- `.aura/ROLES.md`
- `.aura/OUTPUT_FORMATS.md`
- `USER_GUIDE.md`
- current subsystem documents under `docs/`

### 13.2 Generated orientation artifacts

- `.aura/CODEMAP.json`
- `.aura/CODEMAP.md`
- `.aura/understand_graph.json`
- `.aura/understand_graph_tour.json`
- `.aura/understand_graph_diff.json`
- `.aura/graphify_graph.json`
- `.aura/AFFORDANCE_MAP.json`

Generated artifacts are valid only when their health and freshness checks pass.

### 13.3 Runtime and local state

Typically under ignored paths such as:

- `Aura_Memory/`
- `Aura_Staging/`
- `.mempalace/`
- local SQLite databases;
- ST3GG recall ledgers;
- temporary organ directories;
- provider caches;
- screenshots;
- private learner/community data.

Do not treat runtime state as portable source code unless it is deliberately curated as a public fixture.

---

## 14. AI Orientation Protocol

An AI agent entering the repository should follow this sequence:

```text
1. Read README.md
2. Read .aura/ARCHITECTURE.md
3. Read .aura/CODEMAP.md
4. Run topology-health or stabilization-status
5. Run digest
6. Resolve capabilities for the objective
7. Search CODEMAP
8. Inspect a concept or node
9. Read exact slices only
10. Read the relevant subsystem document
11. Prepare an Arena task
12. Stage, test, verify, and request human review
13. Refresh CODEMAP after accepted writes
```

Recommended commands:

```bash
python3 -m aura_agent_arena_cli topology-health
python3 -m aura_agent_arena_cli stabilization-status
python3 -m aura_agent_arena_cli digest
python3 -m aura_agent_arena_cli resolve-capabilities --objective "<objective>"
python3 -m aura_agent_arena_cli search --query "<concept>" --kind symbol
python3 -m aura_agent_arena_cli read-slice --file <file> --symbol <symbol>
```

### Hub-file rule

Do not load these files whole for ordinary work:

- `aura_node.py`
- `aura_agent_arena_cli.py`
- `aura_live_architect.py`
- `aura_architect_loop.py`
- `aura_human_agent_arena.py`
- large test or scientific-memory hubs

Use CODEMAP symbols, line ranges, neighbors, and `read-slice`.

---

## 15. Extension Protocol

A new Arena or organ should provide:

1. a clear human objective and non-goals;
2. a capability-resolution packet;
3. explicit data and authority boundaries;
4. semantic and machine routes;
5. a manifest with deterministic digest;
6. minimum capability lease;
7. lifecycle states and TTL;
8. path, network, device, and secret policy;
9. declarative input/output schemas;
10. exact truth stores or sidecars;
11. tests and verifiers;
12. cost/resource telemetry;
13. human or community approval points;
14. dissolution and revocation behavior;
15. documentation and CODEMAP refresh.

A new domain adapter must not bypass Arena contracts.

---

## 16. Maintenance Invariants

After a successful source change:

```bash
python3 aura_codebase_navigator.py --refresh path/to/changed.py --refresh-topology
python3 -m aura_agent_arena_cli topology-health
```

For a full rebuild:

```bash
python3 aura_codebase_navigator.py
```

Reject a generated map when:

- topology nodes are zero;
- topology edges are zero after a previously healthy build;
- symbol or command indexes are empty;
- neighbor-file data disappears;
- source hashes are unavailable;
- the map was generated before the source changes it claims to describe.

Update in the same pull request:

- source;
- tests;
- affected subsystem docs;
- `USER_GUIDE.md` for operator-facing commands;
- `README.md` for high-level architecture changes;
- `.aura/ARCHITECTURE.md` for architectural boundaries;
- healthy CODEMAP artifacts.

---

## 17. Current Boundaries and Non-Claims

AuraOS is active research software.

Do not claim that:

- FST validation alone is a secure sandbox;
- VSA or JSpace proves truth;
- ST3GG grants patch authority;
- generated Civic scenarios are decisions or legal advice;
- the language tutor replaces fluent speakers or teachers;
- third-party language resources are commercially licensed unless permission exists;
- all benchmark values are measured when some are estimated;
- every subsystem is production-hardened;
- an external model is Aura's cognition or memory;
- an ephemeral organ may become permanent automatically.

---

## 18. Compact Architectural Summary

```text
AuraOS =
  sovereign intent compiler
  + deterministic FST admission and routing
  + self-describing CODEMAP/topology
  + capability reuse graph
  + advisory VSA/JSpace/ST3GG/DREAM/QDKT
  + bounded Arenas
  + ephemeral capability leases
  + Model Cognome and governed adaptive routes
  + optional external workers
  + Experience/Crucible/C1-C3 proposal gates
  + exact tests/verifiers
  + human/community authority
  + governed memory and measured cost
```

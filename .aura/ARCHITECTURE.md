# AuraOS Architecture

> Canonical architecture, ownership, data-flow, and authority anchor for humans and AI agents

**Architecture audit:** reviewed through July 17, 2026 and the preceding three weeks of merged development, including guarded Arena WFSTs, capability resolution, Planning Board/event history, relational authority, ST3GG/J2/QDKT consolidation, Model Cognome, Human Agent/Observatory/Crucible separation, external-worker slice sessions, Civic Commons, Construction E0–E14, Financial exact state, temporal persistence, Tensor Evidence, empirical cost, benchmarks, and public deployment surfaces.

**Navigation rule:** read this file before subsystem documents. Regenerate CODEMAP/topology from the current tree after architecture or source changes.

```bash
python3 aura_codebase_navigator.py
python3 -m aura_codemap_verify --compare-json .aura/CODEMAP.json
```

**Topology source:** `compiled_deep_topology`

## 1. Architectural identity

AuraOS — Augmented Universal Reasoning Architecture — is a sovereign, local-first, Arena-based cognitive operating substrate.

It is not:

- a single LLM;
- a conventional chatbot;
- a monolithic autonomous agent;
- a visual wrapper around an external model;
- a framework where semantic similarity can authorize changes;
- a system where planning, execution, proof, and governance are collapsed into one output.

The canonical end-to-end flow is:

```text
HUMAN OR COMMUNITY OBJECTIVE
  → lexical address and structured intent
  → DIR → ASP → CLASS → SUBJ → VOICE → STEM
  → semantic LEXC and machine WFST admission
  → capability discovery and ownership resolution
  → exact repository/domain grounding
  → bounded Arena and revocable leases
  → deterministic tools and optional external workers
  → staged proposal or action
  → tests, verifiers, and relational governance
  → authorized human/community decision
  → receipts, telemetry, experience, and review-gated learning
```

> **Meaning may guide discovery. Only exact grounded evidence and authorized governance may grant authority.**

## 2. Provenance and design boundaries

Aura originated as a locally controlled Anishinaabemowin learning system. This shaped persistent architectural priorities:

- local operation and sovereignty;
- data minimization;
- purpose-limited sharing;
- inspectable memory and provenance;
- explicit consent and revocable authority;
- human, speaker, teacher, professional, and community governance;
- bounded external egress;
- refusal to treat model convenience as authority.

Aura keeps distinct influences distinct:

- Anishinaabemowin-derived governance and relational design alignments;
- an Athabaskan-inspired six-slot software ordering contract;
- Aura's machine-oriented semantic finite-state routing grammar;
- conventional engineering, formal methods, agent, and neuro-symbolic components.

These are not one language system and must not be documented as interchangeable.

## 3. Constitutional invariants

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
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

Unknown, stale, ungrounded, malformed, expired, ambiguous, conflicting, or unauthorized operations fail closed.

Presentation is never authority. A UI control, ranking, route, graph, probability, model response, compact frame, or generated plan cannot create permission that was never granted.

## 4. Truth and evidence order

When sources disagree, use this order:

1. exact current source, schema, contract, and repository state;
2. exact tests, verifiers, replay, and tamper evidence;
3. healthy current CODEMAP and compiled topology facts;
4. exact snapshots, sidecars, ledgers, event chains, and content-addressed records;
5. manifests, leases, consent, relational-authority, and boundary contracts;
6. current canonical subsystem documentation;
7. summaries, generated reports, screenshots, research sidecars, and historical artifacts.

Advisory cognition includes:

- semantic similarity;
- VSA/HDC resonance;
- DREAM and DREAM-lite;
- JSpace state;
- ST3GG compact frames;
- QDKT compatibility evidence;
- MUSIC and MITOSIS suggestions;
- Tensor Evidence propagation;
- Model Cognome route proposals;
- visual topology and inferred/ghost edges;
- emergent-capability hypotheses;
- external research and model output.

Advisory cognition may discover, rank, compress, explain, or remember. It may not authorize production mutation, policy activation, restricted-data access, cultural-profile activation, civic decisions, Financial actions, Construction operations, or learning promotion.

## 5. Architectural planes

AuraOS is organized into twelve cooperating planes.

### Plane 1 — Intent and lexical addressing

Accepts ordinary human objectives and compiles them into a stable internal address.

```text
surface language
  → local tags and lexical address
  → six-slot intent packet
  → canonical objective and purpose
```

The six-slot order is:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

It encodes operational location/direction, lifecycle/aspect, action class, subject/actor, voice/authority mode, and operation stem.

### Plane 2 — Finite-state admission and guarded routing

Aura uses two cooperating finite-state layers:

1. semantic LEXC routing for immediate incoming intent;
2. state-local machine WFSTs for Arena lifecycle and action admission.

Hard guard order precedes soft ranking:

```text
state identity
  → capability/policy
  → lease/consent/validity/risk
  → evidence/verifier requirements
  → reject blockers
  → rank only admissible options
```

The shared guarded-WFST fabric can expose route context across Coding, Human, Civic, Construction, and other Arenas without making those domains share one truth store.

Primary owners include:

- `aura.lexc`;
- `aura_arena_wfst_runtime.py`;
- `aura_human_agent_wfst_adapter.py`;
- `aura_coding_workbench_wfst_adapter.py`;
- `.aura/arena_routes/*.json`.

### Plane 3 — Self-model, CODEMAP, and capability discovery

The self-model derives from current repository evidence:

- file and role inventory;
- symbol semantic IDs, signatures, hashes, and line ranges;
- command index;
- imports, calls, schemas, tests, routes, and neighbors;
- compiled deep topology;
- Topological Context Anchor;
- Node Inspector and Affordance Directory;
- Capability Connectome;
- Capability Genome Resolver;
- stabilization and ownership manifests.

Primary owners include:

- `aura_codebase_navigator.py`;
- `aura_codemap_verify.py`;
- `.aura/CODEMAP.json`;
- `.aura/CODEMAP.md`;
- `topology_map.json`;
- `aura_topological_context_anchor.py`;
- `aura_capability_connectome.py`;
- `aura_capability_resolver.py`;
- `aura_capability_resolver_v2.py`;
- associated stabilization and manifest modules.

The resolver must search for canonical reusable owners before introducing a new module. CODEMAP vectors and topology edges help navigation; they are not patch authority.

### Plane 4 — Planning, symbolic replay, and continuity

The canonical Planning Board is a proposal-only intermediate representation over goals, actions, predicates, constraints, effects, contingencies, and explicit variables.

It supports:

- deterministic identities and serialization;
- BC0–BC5 continuity stages;
- bounded backward regression;
- forward symbolic replay;
- cycle and no-progress detection;
- frontier convergence and explanation;
- read-only projections into Coding and Civic domains;
- append-only event projection and independent history reconstruction.

Primary owners include:

- `aura_planning_board.py`;
- `aura_planning_regression.py`;
- `aura_planning_frontier.py`;
- `aura_planning_events.py`;
- planning projector/history modules;
- `aura_coding_arena_planning.py`;
- `aura_civic_planning.py`.

Planning validity is not execution authority.

### Plane 5 — Relational authority and governance

Relational authority binds permission to an exact proposed action or event.

An authorization should preserve:

- action/event identity and digest;
- capability and policy scope;
- role and delegation chain;
- quorum and required participants;
- validity window and revocation;
- risk class;
- verifier requirements;
- emergency reason and after-action review where applicable.

Emergency authority is intentionally narrower than ordinary authority and cannot silently erase consent, quorum, or review requirements.

Governance output may admit an action into an Arena. It does not prove the action succeeded; verifiers do that.

### Plane 6 — Arenas and ephemeral organs

An Arena is a bounded execution/review context with:

- state and route identity;
- action/boundary capsules;
- capability leases;
- declared tools/workers;
- sandbox and egress policy;
- verifier requirements;
- lifecycle receipts;
- explicit authority limits.

An ephemeral organ is a temporary capability system compiled for an objective. Its lifecycle is:

```text
request
  → capability resolution
  → manifest/dependency closure
  → sandbox/runtime selection
  → leases and boundaries
  → execution
  → verification
  → telemetry/cost evidence
  → dissolution
  → receipt
```

Arbitrary user Python requires real process isolation. If the requested sandbox does not exist, compilation fails closed instead of falling back to unsafe in-process execution.

Primary owners include:

- `aura_ephemeral_runtime.py`;
- `aura_ephemeral_sandbox.py`;
- `aura_ephemeral_registry_store.py`;
- `aura_capability_resolver.py` and `aura_capability_resolver_v2.py`;
- `aura_arena_tool_runtime.py`;
- Arena-specific adapters and route manifests.

### Plane 7 — Human Agent, Coding Workbench, and external workers

The Human Agent Arena is the governed command centre:

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

It integrates:

- exact objective and evidence framing;
- concept workspace and topology dialogue;
- bounded tools and worker calls;
- persistent attempt history;
- emergent finding/research workspace;
- external-LLM slice sessions;
- temporal persistence;
- domain projections such as Construction;
- verifier and human decision surfaces.

The Coding Workbench localizes exact source and tests, builds bounded change graphs/capsules, stages work, and verifies results. It does not grant itself merge authority.

External workers receive bounded slice leases containing exact source/test/state and output constraints. They are replaceable tools and cannot receive ambient repository, production, cultural, civic, Financial, or Construction authority.

Primary owners include:

- `aura_human_agent_arena.py`;
- `aura_human_agent_arena_server.py`;
- `aura_coding_workbench_capsule_adapter.py`;
- `aura_coding_workbench_wfst_adapter.py`;
- `aura_agent_arena_cli.py`;
- `aura_agent_arena_mcp.py`;
- external-LLM slice-session and refactor-evidence modules.

### Plane 8 — Observatory and glass-box explanation

The Observatory is separate from the Human Agent and Learning Arena.

It may show:

- objective and normalized intent;
- lexical/six-slot address;
- route state and guard decisions;
- exact files, symbols, spans, hashes, and tests;
- topology identifiers;
- compression and worker-route decisions;
- verifier requirements;
- purpose-limited projections from domains.

It cannot:

- create capability leases;
- execute workers;
- stage or apply changes;
- approve a proposal;
- expose unrestricted payloads;
- make an observation eligible for learning by itself.

Primary owners include:

- `aura_showcase_observatory_handoff.py`;
- Observatory projections in domain profiles;
- `aura_showcase/` and Human Agent browser surfaces.

### Plane 9 — Evidence, receipts, telemetry, and cost

Aura preserves evidence without collapsing unlike classes.

Canonical evidence objects include:

- append-only event and sidecar records;
- tool/action decision receipts;
- Arena lifecycle/dissolution receipts;
- worker/refactor output records;
- verification packets and Judge disposition;
- attempt archive entries;
- `OutcomeVector`;
- `ArenaExperience V3`;
- provider usage and empirical cost observations;
- Tensor Evidence references and propagation records;
- benchmark and claim-boundary records.

Empirical Cost Observatory classifies measurement as:

```text
MEASURED | CALCULATED | ESTIMATED | UNAVAILABLE
```

Provider-reported usage, tokenizer-exact counts, deterministic proxies, bytes, and chars/4 remain separate fields. Unknown usage is not zero.

Tensor Evidence localizes belief updates to evidence-relevant regions. It cannot turn a propagated belief into exact source or domain truth.

### Plane 10 — Experience and proposal-only learning

Only governed, verified execution can create learning-eligible experience.

```text
Arena execution
  → verifier evidence
  → OutcomeVector
  → sanitized ArenaExperience V3
  → TRAIN / VALIDATION / SHADOW
  → CRYSTALLIZATION_PROPOSED
  → independent verifier and human review
```

A raw prompt, model response, research paper, observation, failed route, or screenshot is not automatically an `ArenaExperience`.

The current learned surface is limited to:

```text
soft_weight_profile.empirical_uncertainty
```

Crucible cannot alter hard guards, transitions, capabilities, risk classes, consent, source code, active grammar, route policy, Financial exact state, Construction truth, civic authority, or repository merge state.

Primary owners include:

- `aura_arena_experience.py`;
- `aura_arena_experience_ledger.py`;
- `aura_arena_crucible.py`;
- `aura_crucible_validation.py`.

### Plane 11 — Compression and continuity substrates

Aura has several bounded representations. Their purposes are distinct.

#### Context localization

Exact source/test slicing removes unrelated repository context while preserving hashes, dependencies, and verifier requirements.

#### ST3GG

ST3GG V2 provides compact advisory frames and exact recall handles. Compatibility facades can read older frame shapes while new writes use the canonical contract. Admission should reject frames whose protocol overhead eliminates the context benefit.

#### JSpace

- J0 — local task state;
- J1 — Arena-local continuity;
- J2 — governed cross-system continuity and provenance.

J2 packets preserve trust, consent, expiry, schema, route, and evidence boundaries during cross-system handoff.

#### QDKT

Canonical QDKT observation events are append-only evidence. Legacy QDKT results may remain readable through explicit compatibility mappings, but compatibility does not transfer write ownership.

#### Symbolic Trace Memory

Raw trace references, compact atoms, and independently consolidated canvases remain separate. A canvas is an interpretation, not a replacement for exact trace evidence.

#### State Ledger and temporal persistence

`RefactorStateLedger V3` preserves compact intra-session state. `TemporalCheckpointRegistry` provides content-addressed inter-session checkpoints and parent/fork history.

```text
Arena state
  → canonical projection
  → payload digest + invariant digests + exact HEAD
  → checkpoint DAG
  → assessment
       exact/unchanged → DIRECT_RESUME_REVIEW_REQUIRED
       oversized → MITOSIS_REQUIRED
       changed → RESTORATION_COUNCIL_REQUIRED
```

Restoration never applies state automatically.

Primary owners include:

- ST3GG contract/codec/compatibility modules;
- JSpace codec and J2 continuity modules;
- QDKT observation and compatibility modules;
- symbolic-trace and trace-canvas modules;
- `aura_refactor_state_ledger.py`;
- `aura_temporal_persistence.py`;
- `aura_arena_persistence_adapters.py`;
- `aura_wfst_temporal_adapter.py`;
- `aura_agent_arena_persistence_bridge.py`;
- `aura_persistence_cli.py`.

### Plane 12 — Model Cognome and controlled egress

Model Cognome separates endpoint identity, evidence, telemetry, route proposal, and live authorization.

Route classes:

```text
ZERO_MODEL | DIRECT | CASCADE | PANEL
```

Operating modes:

```text
LEGACY | SHADOW | PAIRED_LIVE
```

The Capability Connectome can propose a route into Model Cognome, but proposal and production authorization remain distinct.

A paired-live authorization binds:

- purpose;
- graph/route digest;
- endpoint identity;
- verifier requirements;
- expiry;
- budget;
- nonce/replay policy;
- egress class;
- rollback and quarantine behavior.

Open-weight mechanistic evidence is aggregate-only and shape checked. Raw activations/logits are excluded from general telemetry and public artifacts. Gray-box and black-box endpoints cannot receive unsupported mechanistic claims.

Replay, drift, quarantine, promotion, federation, and local/on-prem policy remain review-gated.

Primary owners include:

- `aura_model_cognome_store.py`;
- `aura_adaptive_model_router.py`;
- shadow/paired-live router modules;
- Cognome telemetry, replay, probe, drift, federation, and policy owners.

## 6. Canonical ownership matrix

| Concern | Canonical owner | Projections/compatibility | Must not become a second owner |
|---|---|---|---|
| Repository truth | Current Git tree, exact source/schemas/tests | CODEMAP, topology, summaries | Visual graph, VSA, research, model output |
| Intent route | Intent contracts, semantic LEXC, machine WFST | UI route diagrams, JSpace/ST3GG packets | Worker interpretation |
| Capability truth | Capability Connectome, Genome Resolver, and manifests | Native Cockpit, Affordance Directory | New duplicate registries |
| Planning truth | `aura_planning_board.py` and canonical planning contracts | Coding/Civic shadows, history projector | Arena UI state |
| Event history | Canonical append-only event/sidecar contracts | Planning history, compatibility readers | Mutable summary JSON |
| Authority | Relational authority, leases, consent, human/community decision | Gate dialogue and UI explanations | Planner, model, score, or Observatory |
| Arena lifecycle | Arena runtime, route, manifest, lease, receipt | Browser/CLI status | Worker process |
| Code patch evidence | Exact source spans/hashes, staged diff, tests/verifiers | CODEMAP localization, Council plan | VSA/topology/JSpace/ST3GG |
| Human Agent workflow | Human Agent state and guarded runtime | Showcase/Human browser projections | Observatory or Attempt Archive |
| Experience | `ArenaExperience V3` and Experience Ledger | Crucible datasets and reports | Raw trace, prompt, or research result |
| Learning proposal | Crucible and validation owners | Observatory/experience views | Active grammar or route manifests |
| Model endpoint evidence | Model Cognome store/policy | Connectome route proposal, dashboards | Informal model reputation |
| Cost evidence | Empirical Cost Observatory and provider records | Dashboards, refactor reports | Proxy promoted to invoice |
| Construction truth | `ConstructionProjectState` and immutable event/claim owners | Adapter, Human Agent profile, Observatory | Checkpoint, UI, model, sensor score |
| Financial truth | Immutable exact-state Financial contracts/ledger | Future purpose-limited indicators | Planner, model estimate, public telemetry |
| Civic governed state | Civic session/contracts and verified organ output | Maps, scenarios, review packets | Binding vote/funding/legal decision |
| Temporal continuity | State Ledger and Temporal Checkpoint Registry | Arena-specific adapters and baton | Domain truth store |

## 7. Human Agent, Observatory, Attempt Archive, and Crucible separation

These surfaces are connected but cannot collapse.

```text
OBSERVATORY
  explain and bound
    → HUMAN AGENT ARENA
      admit and execute
        → ATTEMPT ARCHIVE + VERIFIER RECEIPTS
          → EXPERIENCE LEDGER
            record complete verified outcome
              → CRUCIBLE
                test and propose
```

### Observatory

Review-only explanation and handoff.

### Human Agent

Guarded task lifecycle, tools, workers, and human decision.

### Attempt Archive

Immutable/replayable record of success, denial, failure, evidence, and disposition. It is audit history, not automatic training data.

### Experience Ledger

Stores sanitized complete verified episodes with stable identity. Wall-clock timing is excluded from identity where replay idempotence requires it.

### Crucible

TRAIN/VALIDATION/SHADOW mining and proposal-only crystallization.

## 8. Council–Surgeon engineering architecture

Aura separates deliberation from bounded implementation.

```text
Selective Council V3
  → architecture
  → dependencies/interfaces
  → invariants/sequence
  → rollback/cost only when justified

Sliced Surgeon
  → exact-file implementation
  → focused verification
  → bounded local repair
```

Scope and tests are universal critic lanes. Other lanes are selected from plan structure, dependency, continuity, risk, and measured uncertainty.

Escalation occurs when:

- an interface or dependency is invalidated;
- an invariant no longer holds;
- downstream scope expands materially;
- rollback or authority assumptions change;
- local repair budget is exhausted.

`AURA_REFACTOR_OUTPUT_RECORD_V1` preserves prompt/patch identity, exact gates, failures, disposition, provider-reported versus estimated usage, and claim boundaries.

Grounded phase capsules allow one exact evidence bundle to be shared across bounded phases without giving every phase unrestricted repository context.

## 9. Civic Commons Arena

Civic Commons is a non-binding governed planning and coordination domain.

It integrates:

- Civic session contracts and explicit synthetic/official/user truth classes;
- Ephemeral Organ Runtime;
- capability resolution and decomposition;
- privacy-filtered map projections;
- official-source snapshot/sidecar acquisition;
- local community overlays with explicit consent;
- needs, assets, resources, dissent, and representation gaps;
- MITOSIS decomposition;
- MUSIC trade-off views;
- simulation-only what-if analysis;
- reversible pilot design;
- privacy-filtered community memory;
- model broker with fixture fallback;
- Planning Board shadow and history projection;
- Human Agent Coding handoff for product defects.

Architectural boundaries:

- all bundled Winnipeg stories/records are `SYNTHETIC_DEMO_DATA`;
- official snapshots require provenance/freshness and do not become endorsement;
- the map filters jurisdiction, viewport, zoom, privacy class, and precision;
- person-level vulnerability mapping is rejected;
- dissent and representation gaps remain visible;
- scenarios do not declare a hidden winner;
- what-if outputs are simulation only;
- pilots are reversible/non-binding;
- no automatic funding, voting, procurement, legal approval, surveillance, or service allocation.

## 10. SCO Construction Arena

The completed E0–E14 Construction architecture is a narrow adapter over canonical Aura owners. It does not create duplicate Planning, governance, Experience, Crucible, persistence, Human Agent, or Observatory systems.

```text
immutable Construction claims/evidence/events
  → ConstructionProjectState replay
  → exact readiness/expiry/conflict/scope checks
  → hard candidate blockers
  → advisory probabilistic signal over admissible candidates
  → deterministic cheapest/fastest/recommended/safest roles
  → planning capsule + boundary + lease
  → WFST/verifier packet
  → purpose-limited Human Agent profile
  → stricter read-only Observatory projection
  → external authorized decision
```

Invariants:

- `ConstructionProjectState` is the sole Construction truth owner;
- evaluation state digest exactly matches the projected state;
- candidate IDs are revalidated against exact source candidates;
- blockers execute before ranking;
- high probabilistic/model/sensor scores cannot rescue a blocked route;
- blocked candidates may remain visible but cannot be recommended;
- role ordering is deterministic and alternatives remain distinct;
- runtime packets cannot mutate the event chain;
- browser surfaces have no approve/execute operation;
- checkpoint references use canonical identity and exact local HEAD checks;
- cross-Arena batons are payload free and non-mutating;
- physical work, payment, access, equipment, safety, engineering, inspection, legal, regulatory, source, commit, push, PR, and merge authority remain false.

Primary owners include:

- `aura_construction_contracts.py`;
- `aura_construction_state.py`;
- `aura_construction_authority.py`;
- `aura_construction_adapter.py`;
- `aura_construction_human_agent.py`;
- `aura_construction_refactor_completion.py`;
- Construction fixture, benchmark, learning, and Architect harness modules;
- `.aura/arena_routes/construction.v1.json`.

Real connectors and consequential operational authority are future policy programs, not unfinished E0–E14 software.

## 11. Financial Arena exact-state architecture

The first Financial Arena stage is a local, immutable exact-state record layer.

It models:

- accounts and balances;
- dated transactions and cash flows;
- debts, rates, and fees;
- asset values;
- tax assumptions;
- evidence references and freshness;
- explicit currency and units;
- user authority and provenance.

Truth classes:

```text
USER_RECORDED
IMPORTED_EXACT
DERIVED_ARITHMETIC
ASSUMPTION
UNAVAILABLE
```

Invariants:

- Decimal arithmetic only; no silent float coercion;
- explicit quantization and rounding;
- deterministic serialization/digest/replay;
- no inferred consent, ownership, jurisdiction, or authority;
- no implicit FX conversion;
- future/as-of/lifecycle contradictions fail closed;
- duplicate/conflicting identities fail closed;
- model-estimated values cannot be represented as exact records;
- raw ledger data remains local/purpose limited;
- no advice, prediction, optimization, account connector, payment, transfer, trade, filing, lending, or external mutation authority.

Purpose-limited Planning Board indicators and scenario layers are separate stages and must not transfer ledger ownership.

## 12. Model Cognome architecture

The Model Cognome is an evidence and policy substrate for choosing optional model workers.

Canonical concerns remain separate:

1. endpoint identity and provider family;
2. observed capabilities and limitations;
3. benchmark/test evidence class;
4. telemetry, latency, cost, and usage completeness;
5. privacy/egress policy;
6. route proposal;
7. live authorization;
8. replay, drift, quarantine, promotion, federation, and rollback.

A Capability Connectome path can propose a model route. Model Cognome policy determines whether the route is eligible. Relational authorization and egress policy determine whether live execution is permitted.

`SHADOW` cannot call a provider. `PAIRED_LIVE` cannot run without a matching authorization. Promotion cannot occur solely because a shadow score is higher.

## 13. Temporal persistence architecture

Aura continuity is layered:

1. `RefactorStateLedger V3` — intra-session compact execution state;
2. `TemporalCheckpointRegistry` — inter-session content-addressed checkpoints;
3. append-only parent/fork registry and digest chain;
4. Arena-specific canonical projections;
5. temporal guard evidence;
6. review-only restoration packet.

Invariants:

- checkpoint identity excludes wall-clock metadata where required for idempotence;
- payload and invariants have explicit digests;
- exact repository HEAD is bound and compared;
- files are repository confined and atomically written;
- parent checkpoints belong to the correct Arena/session lineage;
- forks use explicit parent/branch identity;
- stale/future/branch-offset classifications fail closed;
- handoffs contain references/digests, not payloads;
- Observatory never exposes checkpoint payloads;
- no checkpoint becomes a second domain truth store;
- no legal immutability or court-admissibility claim is made;
- no automatic restore, model call, code application, grammar promotion, physical action, payment, access, certification, commit, push, PR, or merge.

## 14. Benchmark and claim architecture

Aura keeps unlike evidence separate.

| Tier | Evidence | Permitted claim |
|---:|---|---|
| 1 | Exact executable gates, tests, replay, verifier/Judge disposition | Working status for the exact evaluated artifact |
| 2 | Deterministic comparative proxy with comparable quality | Controlled relative efficiency or continuity |
| 3 | Estimated structural projection | Architecture estimate labeled `ESTIMATED` |
| 4 | Discovery/capacity scan | Candidate capability or missing-wire hypothesis |

Evidence must preserve:

- artifact/head identity;
- exact test/gate counts;
- quality comparison where efficiency is claimed;
- provider-reported versus estimated usage;
- measurement completeness;
- failed gates;
- disposition;
- claim boundary.

No Tier 3 or Tier 4 result becomes Tier 1 without governed execution and verifier evidence.

## 15. Deployment and presentation surfaces

Aura supports several deployment/presentation layers:

- local CLI/REPL;
- Native Cockpit;
- Coding Arena;
- unified Human Agent Arena;
- four-surface Showcase: Civic, Human Agent, Observatory, Crucible;
- containerized showcase/Render path;
- Hugging Face public demo path;
- MCP Agent Bridge;
- Hermes/local-model and optional provider workers;
- guided Winnipeg Civic demonstration;
- AR/spatial and broader application-fabric prototypes.

Deployment does not change authority. Public demos use synthetic or explicitly public evidence and must not expose private memory, raw activations, raw Financial/Construction records, credentials, or community-restricted knowledge.

## 16. Compatibility and migration policy

Aura frequently introduces canonical V2/V3 contracts while preserving legacy reads.

Compatibility rules:

- new writes use the canonical owner;
- legacy artifacts remain readable through explicit mappings;
- compatibility output is labeled;
- translation preserves IDs/provenance where possible;
- unsupported fields fail closed or remain `UNAVAILABLE`;
- compatibility does not transfer ownership back to the legacy format;
- removal requires measured migration evidence and rollback planning.

This policy applies to guarded Arena routes, ST3GG, QDKT, JSpace continuity, Planning Board projections, Model Cognome routing, event contracts, and other consolidated surfaces.

## 17. Security, privacy, and cultural governance

Security is structural:

- least-privilege capability leases;
- explicit purpose and egress classes;
- exact scope and expiry;
- repository confinement;
- real sandbox requirements for arbitrary code;
- content-addressed evidence and tamper checks;
- append-only events and receipts;
- replay/nonce rules;
- local/quarantine/federation boundaries;
- aggregate-only public telemetry;
- no secrets in prompts or committed artifacts;
- fail-closed unknowns.

Cultural and community governance adds:

- speaker/teacher/community authority where appropriate;
- no invented translations;
- no activation of restricted profiles from semantic similarity;
- no flattening of distinct Nations/languages into generic labels;
- explicit consent and purpose limitation;
- revocation and deletion paths where the governing contract requires them.

## 18. Implemented architecture versus roadmap

Implemented repository capabilities are described above as implemented.

Architecture-supported but separately gated product directions include:

- intent-compiled consumer application fabrics;
- sovereign Arena federations and social/public information networks;
- disaster coordination and institutional deployments;
- real owner/contractor/payment/access/sensor Construction connectors;
- Financial indicators, scenarios, connectors, recommendations, and LifeOS presentation;
- AR and spatial experiences beyond current prototypes;
- module marketplaces and commercial packaging;
- autonomous production promotion.

These require separate implementation, privacy/security review, governance, measurement, and domain authorization. They must not be inferred from architectural compatibility alone.

AuraOS evidence does not establish consciousness, unrestricted autonomy, universal model superiority, legal certification, court admissibility, or production readiness outside exact measured gates.

## 19. Architecture maintenance protocol

After an architecture-changing merge:

1. identify canonical owners and any compatibility layers;
2. update this file, `README.md`, and `USER_GUIDE.md` together when the public/operator model changes;
3. update subsystem documents and machine-readable evidence;
4. add or update exact tests and authority assertions;
5. regenerate CODEMAP/topology from the final tree;
6. inspect generated ownership/file cards;
7. verify no temporary integration tools remain;
8. verify claim language against the evidence tier;
9. merge only the exact reviewed head;
10. perform post-merge verification and record intentional deferrals.

The canonical test for a healthy change is not merely that code runs. It is that ownership remains singular, authority remains explicit, evidence remains inspectable, compatibility remains bounded, and the system can explain why the change is allowed.

# AuraOS

**AuraOS — Augmented Universal Reasoning Architecture — is a sovereign, local-first cognitive operating substrate that compiles human intent into grounded, governed, temporary capability systems.**

Aura is not a single language model and does not depend on one provider. Local deterministic components, exact repository evidence, finite-state guards, capability leases, verifiers, human governance, and purpose-limited memory form the operating system. Hermes, Codex, Fireworks-backed models, OpenAI-compatible endpoints, local Ollama models, and other agents can serve as replaceable workers inside that system.

Aura began as a locally controlled Anishinaabemowin learning system. That origin shaped its continuing design priorities: sovereignty, local operation, data minimization, provenance, explicit consent, purpose-limited sharing, revocable authority, and human/community governance. Aura keeps its sources distinct: Anishinaabemowin-derived governance alignments, an Athabaskan-inspired six-slot software ordering contract, and Aura's machine-oriented finite-state routing grammar are related design influences, not one flattened linguistic claim.

> **Meaning may guide discovery. Only exact grounded evidence and authorized governance may grant authority.**

## What Aura does

```text
ordinary human objective
  → intent ingestion and lexical addressing
  → DIR → ASP → CLASS → SUBJ → VOICE → STEM
  → semantic LEXC and machine WFST admission
  → capability discovery and reuse
  → exact files, symbols, spans, hashes, tests, and boundaries
  → bounded Arena and capability leases
  → deterministic tools and optional external workers
  → staged proposal
  → tests, verifiers, and governance
  → human/community decision
  → receipts, experience, telemetry, and review-gated learning
```

This architecture is designed to reduce unnecessary context, preserve exact evidence, make model behavior replaceable, and keep consequential authority outside probabilistic outputs.

## Current system map

AuraOS now contains a connected family of operating surfaces rather than one monolithic agent.

| Surface | Implemented role | Authority boundary |
|---|---|---|
| **Native Cockpit** | Ingests structured objectives, resolves capabilities, prepares bounded handoffs, and routes work to existing Aura lanes | Planning and preparation only |
| **Aura Observatory** | Shows lexical addressing, six-slot intent, FST route, CODEMAP localization, compression, topology, and worker handoff | Glass-box review surface; no execution or permission |
| **Human Agent Arena** | Runs `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE` with exact evidence and human gates | Guarded execution and review; no automatic merge |
| **Coding Workbench / Coding Arena** | Localizes code, ranks bounded regions, builds change graphs, prepares capsules, and verifies candidate work | Exact source spans and hashes remain patch authority |
| **Aura Forge** | Compiles a frozen Coding Arena plan and Arena Evidence Contract, then runs bounded Council–Surgeon slice sessions | Stops at verifier-backed human review; no automatic commit, PR, merge, or production mutation |
| **Aura Gate** | Wraps an exact Forge contract with verified OIDC identity, static policy, expiring leases, governed egress, MCP/A2A adapters, comparisons, and append-only audit evidence | Private Forge-specific proof; no identity-in-body trust, automatic promotion, or release authority |
| **Coding Waboose** | Computes exact diff/symbol/dependency impact, runs deterministic scans, and lets coding agents steer run-specific evidence review | Review only; agent findings cannot self-confirm or mutate, commit, push, open, or merge |
| **Agent Arena Bridge** | Exposes bounded CLI/MCP workflows and external-agent handoffs | External agents remain workers, not authorities |
| **Planning Board** | Represents proposal-only goals, actions, predicates, constraints, backward regression, forward replay, and continuity stages | Cannot execute or authorize actions |
| **Civic Commons Arena** | Coordinates governed civic objectives, evidence, needs, resources, scenarios, consent, dissent, and reversible pilots | Non-binding; no funding, voting, legal approval, or person-level targeting |
| **Construction Arena** | Replays exact project state, evaluates blocked/admissible proposals, and projects bounded Human Agent and Observatory views | No physical work, payment, access, equipment, or professional authority |
| **Spatial Arena** | Projects canonical domain state into immutable scenes and runs a governed `FRAME → GROUND → COMPILE_SCENE → PLAN_RENDER → PRESENT → INTERACT → PROVE → DECIDE → DISSOLVE` lifecycle | Presentation and proposal only; no domain mutation, renderer authority, raw-sensor retention, automatic resume, or merge |
| **Financial Arena** | Stores immutable Decimal-based exact-state financial records and explicit truth classes | No advice, prediction, transaction, connector, or account-mutation authority |
| **Learning Arena / Crucible** | Mines verified `ArenaExperience` records across TRAIN, VALIDATION, and SHADOW | Emits `CRYSTALLIZATION_PROPOSED`; never auto-promotes code, grammar, or policy |
| **Ephemeral Organ Runtime** | Compiles temporary capability systems with manifests, leases, sandbox policy, verification, dissolution, and receipts | No ambient authority; arbitrary components fail closed without a real sandbox |
| **Model Cognome** | Records endpoint capability evidence, usage, cost, latency, drift, replay, shadow, and governed route proposals | Active routing changes require explicit authorization and verification |
| **Empirical Cost Observatory** | Separates measured, calculated, estimated, and unavailable usage/cost evidence | Measurement cannot mutate production or upgrade a claim class |

<!-- AURA_FORGE_V1:START -->
## Aura Forge — Verified Engineering OS

Aura Forge is the first commercial product surface over Aura's existing Coding Arena and
controlled refactor owners. It does not introduce a second planner, patch store, verifier,
or learning path.

```text
engineering objective
  → CODEMAP/topology grounding
  → frozen Architect/Coding Arena plan
  → AURA_FORGE_ARENA_EVIDENCE_CONTRACT_V1
  → bounded source/test slice lease
  → external worker unified diff
  → canonical staging, verification, and repair
  → READY_FOR_HUMAN_REVIEW
  → separate authorized promotion decision
```

`aura_forge.py` binds the objective, exact repository identity, plan phase, Act Capsules,
source/test references, allowed files, required gates, worker budgets, authority, and
lifecycle into one deterministic contract. External workers remain replaceable and receive
no ambient repository or release authority.

See [`docs/AURA_FORGE.md`](docs/AURA_FORGE.md).
<!-- AURA_FORGE_V1:END -->

<!-- AURA_GATE_PHASE2:START -->
## Aura Gate — Sovereign Agent Governance Gateway

Aura Gate Phase 2 wraps the retained Forge prepare/start boundary with an exact authority
envelope. It verifies OIDC identity offline against an operator-pinned RS256 JWKS, derives
a deployment-local pseudonymous actor reference, admits only content-addressed static
policy, issues a bounded Arena lease, and starts only the frozen Forge contract ID and
digest. Forge actions, egress releases, and lease transitions carry append-only pre-action
evidence, and every worker payload passes through a purpose-, destination-, data-,
retention-, and budget-bound egress capsule.

```text
verified identity + exact purpose + static policy
  → Forge prepare
  → Gate authority envelope + expiring lease
  → exact Forge start
  → governed MCP/A2A turns
  → verifier-backed human-review packet
  → dissolution or explicit revocation
```

The current proof is Forge-specific OIDC/private single-node deployment. SAML/SCIM,
HA/Kubernetes, arbitrary-domain policy, and vendor-certified SIEM integration are deferred.
It never commits, pushes, creates a pull request, merges, releases, or promotes policy.

See [`docs/AURA_GATE.md`](docs/AURA_GATE.md).
<!-- AURA_GATE_PHASE2:END -->

<!-- AURA_CODING_WABOOSE_V1:START -->
## Coding Waboose — graph-guided code review

Coding Waboose combines deterministic program analysis with replaceable coding-agent
investigation. Aura computes changed symbols, callers, callees, tests, schemas, shared-resource
neighbors, exact source anchors, and tool evidence. Codex, Hermes, or another MCP client may
supply run-specific review questions and semantic findings, but cannot invent authoritative
edges, mark its own findings proven, or apply a fix.

```text
change or workspace
  → exact diff and changed symbols
  → bidirectional dependency-impact slice
  → syntax/static/test scans
  → run-specific focus directives
  → diagnostic Coding Breadboard
  → bounded coding-agent investigation
  → exact-source corroboration and precision-first ranking
  → human review packet
  → optional Aura Forge repair handoff
```

See [`docs/AURA_CODING_WABOOSE.md`](docs/AURA_CODING_WABOOSE.md).
<!-- AURA_CODING_WABOOSE_V1:END -->

## Canonical architecture

### 1. Intent and finite-state routing

Aura supports ordinary language input while preserving a deterministic internal route.

```text
lexical address and local tags
  → six-slot intent packet
  → semantic LEXC route
  → state-local guarded WFST
  → hard guards before soft ranking
  → admitted action or explicit denial
```

The canonical slot order is:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

VSA/HDC resonance may rank only already-admissible options. It cannot override missing evidence, blocked risk, an expired lease, a denied capability, or a failed verifier requirement.

### 2. CODEMAP, topology, and capability reuse

Aura's self-model is built from the current repository:

- `.aura/CODEMAP.json` and `.aura/CODEMAP.md`;
- compiled deep topology and symbol relations;
- Topological Context Anchor;
- Node Inspector and Affordance Directory;
- Capability Connectome and Capability Genome Resolver;
- module manifests, command indexes, tests, and ownership metadata.

The resolver searches existing owners before new code is proposed. Generated topology is navigation evidence, not proof by itself. Exact current source, symbols, spans, hashes, tests, schemas, and verifier output remain authoritative.

Primary resolver owners include `aura_capability_resolver.py` and the graph-pinned `aura_capability_resolver_v2.py` facade over Capability Connectome evidence.

The current synchronized map indexes more than one thousand repository files and a deep graph of thousands of nodes and edges. Regenerate it after architecture or source changes rather than relying on historical line numbers.

### 3. Planning, events, continuity, and governance

Aura separates proposal, authority, and proof:

```text
Planning Board proposal
  → relational authority and quorum decision
  → append-only event/sidecar evidence
  → independent history projection
  → execution inside an admitted Arena
  → verifier receipt
```

The Planning Board provides typed goals/actions, BC0–BC5 continuity, bounded backward regression, forward symbolic replay, and compatibility shadows over existing systems. Planning artifacts can be projected into canonical append-only events and independently reconstructed without becoming execution authority.

Relational authority binds approvals to an exact action ID, action digest, capability/policy scope, validity window, role, quorum, delegation chain, and risk class. Emergency authority remains narrower, temporary, reason-bearing, and review-producing.

### 4. Human Agent, external workers, and Council–Surgeon engineering

The Human Agent Arena is the main governed collaboration surface:

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

It includes:

- concept workspaces and exact node inspection;
- topology-anchored gate dialogue;
- bounded tools and capability leases;
- an Attempt Archive that preserves successful, denied, and failed work;
- persistent emergent-property findings and bounded arXiv/GitHub research;
- grounded phase capsules with shared evidence rather than repeated repository context;
- external-LLM slice sessions that lease only required source, tests, state, and constraints;
- reviewable refactor output records with exact gate evidence and claim classes.

Selective Council V3 performs architecture-level deliberation only where critic lanes are justified. The sliced Surgeon performs exact-file implementation, focused verification, and bounded repair. Local assertion failures may return to the Surgeon; interface, dependency, invariant, or expanded-scope failures return to the Council.

### 5. Compression and continuity substrates

Aura uses several distinct compression and state representations without treating them as interchangeable truth:

- **Context Crusher / exact slicing** — removes unrelated repository context;
- **ST3GG** — compact advisory frames and exact-recall handles with protocol-overhead-aware admission;
- **JSpace J0/J1/J2** — compact route, Arena, and cross-system continuity packets;
- **QDKT** — canonical observation events and read-only compatibility evidence around retained legacy results;
- **Symbolic Trace Memory** — raw references, compact atoms, and independently consolidated canvases;
- **State Ledger V3** — compact intra-session execution state;
- **Temporal Persistence** — content-addressed checkpoints, forks, restoration assessment, and payload-free cross-Arena handoff.

Temporal restoration produces one of these review decisions:

- `DIRECT_RESUME_REVIEW_REQUIRED`;
- `MITOSIS_REQUIRED`;
- `RESTORATION_COUNCIL_REQUIRED`.

No checkpoint automatically applies state, invokes a model, promotes a hotswap, mutates grammar, commits code, or merges a branch.

### 6. Experience and proposal-only learning

A raw prompt, research paper, failed attempt, route trace, or model response is not learned truth.

```text
governed Arena execution
  → verifier evidence
  → OutcomeVector
  → ArenaExperience V3
  → TRAIN / VALIDATION / SHADOW separation
  → CRYSTALLIZATION_PROPOSED
  → verifier and human review
```

The current Crucible can propose changes only to a narrow soft-weight surface such as `soft_weight_profile.empirical_uncertainty`. It cannot change hard guards, transitions, capabilities, consent, risk classes, source code, active grammar, route policy, or governance authority.

### 7. Model Cognome and controlled egress

Model Cognome separates endpoint identity, capability evidence, cost/latency telemetry, route policy, and authorization.

Supported route classes include:

```text
ZERO_MODEL | DIRECT | CASCADE | PANEL
```

Operating modes include:

```text
LEGACY | SHADOW | PAIRED_LIVE
```

- `LEGACY` preserves established behavior and rollback.
- `SHADOW` plans and compares without provider execution.
- `PAIRED_LIVE` requires explicit purpose, graph digest, endpoint, verifier, expiry, budget, nonce/replay, and egress authorization.

Open-weight mechanistic evidence is optional and aggregate-only. Gray-box and black-box endpoints cannot be assigned unsupported mechanistic claims. Drift, quarantine, federation, and promotion remain review-gated.

## Domain Arenas

### Civic Commons

Civic Commons combines ephemeral organs, official-source snapshots, local profiles, truth classes, MITOSIS decomposition, MUSIC trade-off surfaces, consent/dissent preservation, simulation-only what-if analysis, reversible pilot design, privacy-filtered community memory, and a model broker with fixture fallback.

All included demonstration stories and community overlays are explicitly labeled. The system rejects person-level vulnerability maps, binding votes, automatic funding, legal approval, unrestricted surveillance, and invented Indigenous-language translations.

### SCO Construction

The completed E0–E14 Construction refactor reuses canonical Aura owners for planning, governance, receipts, WFST admission, Experience, Crucible, persistence, Human Agent, and Observatory.

#### Construction Human Agent profile

The Construction Human Agent profile is purpose-limited to the admitted planning capsule and keeps decision authority external; its paired Observatory projection is stricter and read-only.

```text
immutable claims/evidence/events
  → ConstructionProjectState replay
  → exact readiness/conflict/expiry checks
  → hard blockers before ranking
  → deterministic proposal roles
  → bounded Human Agent profile
  → stricter read-only Observatory projection
  → external authorized decision
```

`ConstructionProjectState` is the only Construction truth owner. Probabilistic or sensor scores cannot rescue a blocked route. Real connectors, physical/equipment control, payment release, access control, safety/engineering/legal certification, and commercial field claims remain separate future programs.


<!-- AURA_SPATIAL_S5_S6:START -->
### Spatial Arena and Construction projection

Spatial S5 completes Aura's governed presentation lifecycle, while the Construction-only S6 adapter projects exact `ConstructionProjectState` and its validated runtime packet without creating another Construction ledger.

```text
canonical domain truth
  → privacy-minimized adapter
  → immutable SpatialSceneSnapshot
  → deterministic device/render plan
  → ephemeral presentation session
  → review-only interaction
  → render evidence + Attempt Archive + assessment-only checkpoint
  → read-only Observatory projection
  → human/domain decision packet
  → exact renderer-boundary receipt
  → lease and session dissolution
```

The canonical lifecycle is:

```text
FRAME → GROUND → COMPILE_SCENE → PLAN_RENDER → PRESENT
      → INTERACT → PROVE → DECIDE → DISSOLVE
```

`DECIDE` emits a review packet; it does not apply a decision. `DISSOLVE` preserves the client's evidence class and requires exact session, scene, and render-plan bindings. Emergency close never fabricates renderer cleanup. Public Construction identifiers are hashed, restricted/sensitive projections remain local and abstract, and floor-plan manifests are admitted only when they are local, privacy-compatible, explicitly non-survey, and contain no person-level data.

Validate the route and run the synthetic, non-persistent demonstration:

```bash
python aura_spatial_cli.py --repo-root . validate-route
python aura_spatial_cli.py --repo-root . synthetic-construction-demo
```

See [`docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md`](docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md).
<!-- AURA_SPATIAL_S5_S6:END -->

### Financial exact state

The first Financial Arena slice provides immutable Decimal-backed records for accounts, balances, transactions, cash flows, debts, asset values, fees, tax assumptions, provenance, freshness, currencies, and units. It distinguishes:

```text
USER_RECORDED | IMPORTED_EXACT | DERIVED_ARITHMETIC | ASSUMPTION | UNAVAILABLE
```

It rejects silent floats, implicit rounding, inferred ownership, implicit currency conversion, future/lifecycle contradictions, duplicate identities, and model-estimated values presented as exact state. Planning Board indicators and scenarios remain separately bounded stages.

## Evidence and benchmark hierarchy

Aura does not collapse unlike evidence into one score.

| Tier | Evidence class | What it can support |
|---:|---|---|
| 1 | Executable gates and exact-head tests | Claims about the exact evaluated artifact |
| 2 | Deterministic comparative proxies | Controlled relative efficiency or continuity comparisons |
| 3 | Estimated structural projections | Architecture hypotheses labeled `ESTIMATED` |
| 4 | Discovery and capacity scans | Candidate capabilities and missing wires |

Representative current evidence includes:

- executable fixture: `3/3` visible, `3/3` hidden, `2/2` regression, `WORKING`, `ACCEPTED`;
- exact-head AuraOS refactor: `32/32` visible/property, `35/35` adversarial, `24/24` regression;
- context-localization proxy: `89.04%` lower total proxy with quality `+0.0057`;
- Selective Council V3: `32.83%` lower total proxy than Council V2 on the controlled fixture with the same accepted patch and quality;
- Aura Gate Phase 2 instrumented Agent Bridge + Council V3 scope: `37,907` input,
  `1,852` output, and `39,759` total token proxy, with `51,987` estimated saved
  (`56.66%`) against the documented counterfactual; full Codex-session provider totals
  were unavailable, so this is not billing evidence;
- State Ledger synthetic continuity: `96.19%` less step-7 context, preservation `1.0000`, drift `0.0000`;
- shared grounding evidence: `53.1936%` projected structural savings, explicitly `ESTIMATED` rather than provider billing.

Provider-reported usage, tokenizer-exact measurements, deterministic token proxies, byte counts, and chars/4 estimates remain separate fields. Unknown usage remains unknown.

## Quick start

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python3 -m pip install -r requirements.txt
python3 aura_codebase_navigator.py
python3 -m aura_agent_arena_cli topology-health
python3 -m aura_agent_arena_cli stabilization-status
python3 -m aura_agent_arena_cli digest
```

Launch the unified Human Agent surface:

```bash
python3 aura_human_agent_arena_server.py --repo-root . --demo
```

Launch the four-surface showcase:

```bash
python3 aura_showcase_server.py --demo-project winnipeg_pathways
```

Launch the local Coding Arena:

```bash
python3 aura_coding_arena_server.py --demo
```

Run the Construction completion audit:

```bash
python3 -m aura_construction_refactor_completion --repo-root .
```

Verify temporal persistence:

```bash
python3 -m aura_persistence_cli --repo-root . verify-registry
```

## Truth and authority invariants

```yaml
planning_proposes: true
governance_authorizes: true
verification_proves: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
visual_topology_patch_authority: false
external_model_action_authority: false
crystallization_patch_authority: false
automatic_grammar_promotion: false
automatic_state_restoration: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

Unknown, stale, ungrounded, malformed, expired, ambiguous, or unauthorized work fails closed.

## Implemented architecture versus product direction

Implemented repository capabilities are documented as implemented. Broader directions—including intent-compiled consumer application fabrics, sovereign Arena federations, disaster coordination, institutional deployments, production spatial/XR deployments, public information networks, module marketplaces, and real-world Construction/Financial connectors—remain architecture-supported product directions until separately built, reviewed, measured, and authorized.

AuraOS evidence does not establish consciousness, unrestricted autonomy, universal model superiority, legal certification, court admissibility, or production readiness beyond the exact measured gates.

## Documentation

- [`USER_GUIDE.md`](USER_GUIDE.md) — installation, operating workflows, commands, APIs, testing, and troubleshooting
- [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) — canonical ownership, planes, data flows, contracts, and authority model
- [`.aura/CODEMAP.md`](.aura/CODEMAP.md) — current compact repository navigation
- [`docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md`](docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md) — governed Spatial lifecycle, Construction projection, privacy, evidence, checkpoints, Agent Bridge/MCP/CLI, and dissolution boundaries
- [`docs/AURA_GATE.md`](docs/AURA_GATE.md) — Phase 2 authority flow, identity, policy, protocols, deployment, audit, and proof limits
- [`docs/AURA_COUNCIL_V3_EFFICIENCY_AND_SCALE_ENHANCEMENT_PROPOSAL.md`](docs/AURA_COUNCIL_V3_EFFICIENCY_AND_SCALE_ENHANCEMENT_PROPOSAL.md) — operation-DAG, parallel-wave, quality, speed, and token-efficiency recommendations for Council V3.1
- [`docs/AURA_HUMAN_AGENT_ARENA.md`](docs/AURA_HUMAN_AGENT_ARENA.md)
- [`docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md`](docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md)
- [`docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md`](docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md)
- [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)
- [`docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`](docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md)
- [`docs/AURA_EMPIRICAL_COST_OBSERVATORY.md`](docs/AURA_EMPIRICAL_COST_OBSERVATORY.md)
- [`docs/AURA_TENSOR_EVIDENCE_ARENAS.md`](docs/AURA_TENSOR_EVIDENCE_ARENAS.md)
- [`docs/AURA_SCO_PHASE5_E9_E14_COMPLETION_PLAN.md`](docs/AURA_SCO_PHASE5_E9_E14_COMPLETION_PLAN.md)

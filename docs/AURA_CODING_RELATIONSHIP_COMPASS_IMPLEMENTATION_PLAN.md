# Aura Coding Relationship Compass — Comprehensive Implementation Plan

> **Program status:** implementation in progress — C0 through C5 implemented; C6–C9 pending
> **Canonical name:** Aura Coding Relationship Compass  
> **Reference architecture:** ENG-ATLAS v2.4, reconciled with current AuraOS  
> **Repository baseline:** `dallascourchene-commits/AuraOS` main source SHA `4865e013c2deb0695b86591c899fb278aff08ac5`  
> **Harness request digest:** `322da709fab875d844fb4d45bd345931`  
> **Harness run digest:** `67b1e8a55c084385425c32fab03e050f`  
> **Authority:** planning evidence only; exact current source spans and hashes remain patch authority

## 1. Executive decision

Aura should implement the **Coding Relationship Compass** as an objective-scoped orchestration and compilation layer over existing canonical owners. It must not become another repository graph, another policy engine, another memory truth store, or a direct mutation path.

The permanent pipeline is:

```text
human coding objective
  → canonical six-slot intent packet
  → Connectome capability selection
  → exact Evidence Spine grounding
  → bounded Relational Index neighborhood
  → objective-scoped Relationship Atlas classification
  → typed relationship compatibility / Breadboard preflight
  → bounded Emergent candidate discovery
  → Planning Board plan and Selective Council V3 review
  → Change Graph + Agent IR + proposal-only Act Capsules
  → Surgeon implementation
  → Coding Waboose / tests / verifiers / Crucible replay
  → human maintainer decision
  → governed experience projection
```

The key design rule is:

```text
Global anatomy is compiled once at MINIMAL depth.
Deep relationship reasoning occurs only inside an evidence-backed objective neighborhood.
```

This is required by the current repository scale. The clean reference-bound harness run found:

- 21 principal Connectome nodes and 60 explicit capability edges;
- 14,037 Relational Index participants and 29,006 relations across 22 groups;
- 29,006 MINIMAL Atlas assessments, 7 missing configurations, and 7 prohibitions;
- an estimated 98,511,666 full pair comparisons if Atlas were allowed to reason globally;
- 7,041 abilities scanned by Emergent Properties, yielding one candidate that still required grounding;
- a clean, read-only, reference-bound full harness run in 27.504 seconds.

The Compass is therefore valuable, but it must solve selection and bounded compilation—not add another global all-pairs pass.

## 2. Evidence and governance basis

This plan was produced from the exact full-repository harness merged in PR #176 and bound to both supplied documents by file name, byte size, and SHA-256:

| Evidence input | SHA-256 | Bytes |
|---|---:|---:|
| `# ARCHITECTURAL REFERENCE SPECIFICA.txt` | `959fe77de795bb045c43e660328b4e7c2c712052966e5a93ff031962f99c985e` | 46,426 |
| `USER_GUIDE (5)(2).md` | `a951f84422ce0c7eddb9fbc5fae40139552d3db15f11b61a096d3eec9127598e` | 43,899 |

The run preserved these invariants:

```yaml
source_main_sha: 4865e013c2deb0695b86591c899fb278aff08ac5
repository_clean_before: true
repository_clean_after: true
production_mutation: false
safe_to_patch: false
human_review_required: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

Architect returned intensity 3, `BLOCK_BUILDER`, and `ready_for_incubator=false`. That is the correct result at this stage: the architecture is coherent enough to plan, but construction must remain blocked until phase contracts, exact source slices, tests, and rollback gates exist.

Selective Council V3 classified this work as a **PROGRAM**:

```yaml
task_count: 10
dependency_edges: 9
sequential_depth: 10
distinct_files: 29
large_or_xl_tasks: 8
selected_critic_lanes:
  - scope
  - tests
  - sequence
  - continuity
  - rollback
  - cost
```

The final enriched phase plan was then run through Council V3's actual selective critic route using deterministic local critic evidence. All six lanes approved the plan; the candidate score after critique was `0.91`. The Council receipt remains planning-only and grants no implementation authority.

## 3. What to preserve, adapt, and reject from ENG-ATLAS v2.4

### 3.1 Preserve

The following ideas are architecturally sound and should become permanent:

1. **Objective-scoped orchestration.** Connectome, Relational Synthesis, Atlas, Emergent Properties, and Architect should cooperate through one bounded packet.
2. **Global MINIMAL plus local deep analysis.** Full-repository anatomy remains linear in current participants/relations; STANDARD or DEEP reasoning is restricted to a selected neighborhood.
3. **Typed compatibility preflight.** Cheap deterministic checks should reject impossible, prohibited, over-budget, or under-evidenced connections before graph expansion or model use.
4. **Explicit relationship classes.** Aura must distinguish exactly wired, overlapping but unwired, auxiliary, adapter-required, missing, redundant, prohibited, and uncertain relationships.
5. **Evidence-carrying recommendations.** Every candidate must retain exact source references, truth class, objective relevance, risks, prohibitions, required tests, and a smallest verification experiment.
6. **Bi-temporal experience history.** Aura should preserve when a relationship was valid and when the observation was recorded, without rewriting history.
7. **Capsule compilation.** Approved plan elements should become deterministic Change Graph, Agent IR, Act Capsule, Surgeon, and review packets rather than remaining prose.
8. **Edge-conscious execution.** Bounded neighborhoods, compact projections, deterministic filters, and zero-model routing should be the default.

### 3.2 Adapt

Several reference ideas need to be fitted to Aura's existing owners rather than copied literally.

#### A. Keep the canonical six-slot intent route

Aura already uses:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

The Compass must reuse `PolysyntheticIntentPacket`; it must not create a second six-slot parser.

The software projection should be:

| Slot | Software role in Compass |
|---|---|
| `DIR` | scope, reach, and routing direction |
| `ASP` | lifecycle and mutation posture: proposal, active, completed, iterative |
| `CLASS` | data/resource/thermal compatibility class |
| `SUBJ` | authenticated actor and delegated role |
| `VOICE` | boundary, port direction, and transitivity |
| `STEM` | requested operation or capability identity |

Domain, truth class, proof status, policy scope, and source identity remain separate typed fields. They must not be overloaded into the six slots.

#### B. Replace string regex authority with typed contracts

The reference's six-character regex prototype becomes an immutable `RelationshipContract` and `RelationshipCompatibilityAssessment` using enums, exact versioning, canonical serialization, and hard-guard evaluation. A bitset may be used as a derived acceleration index, but never as the truth owner or authorization object.

#### C. Treat Breadboard language as an engineering model

“Pins,” “tracks,” “load,” “circuit breaker,” and “short circuit” are useful explanatory and preflight concepts. They do not prove hardware equivalence, eliminate compilation failures, or create physical guarantees. Production claims must say “preflight incompatibility detection” rather than “zero-runtime faults.”

#### D. Use current governed memory owners

Bi-temporal observations should flow through QDKT, Symbolic Trace Memory, the Arena Experience Ledger, Temporal Persistence, and Crucible. A new Engraphis-style SQLite database must not become a parallel source of architectural truth.

If a local SQL acceleration cache is later justified, it must be:

- derived and fully rebuildable;
- versioned and migration-tested;
- bounded by bytes, rows, query time, and retention;
- WAL-safe and lock-safe;
- content-addressed;
- free of raw source, secrets, private prompts, and authority objects;
- disposable without loss of canonical evidence.

#### E. Treat complexity and latency as benchmark targets

“O(1),” “microsecond,” and “hardware-level” claims are not accepted until measured on the exact implementation. The required claim is narrower: indexing and typed filters should reduce candidate work before expensive analysis, while measured receipts disclose hardware, input size, cache state, and evidence class.

### 3.3 Reject from the starter code

Do not copy the illustrative `LocalEngraphisStore` and regex-gated `ActCapsule` directly. It has production-critical deficiencies:

- MD5-based short IDs and timestamp-dependent identity;
- regex matching used as a permission check;
- broad subject/predicate invalidation that can erase distinct valid facts;
- `SELECT *` recall scans with no query or row bounds;
- an advertised six-term formula but a much simpler multiplication in code;
- transaction time incorrectly reused as last access time;
- no schema version, migration, concurrency, corruption, WAL, or recovery policy;
- receipts that do not bind the complete canonical record or prior receipt;
- no exact repository head, source span, truth class, verifier, or human disposition;
- direct patch payload carriage before governed Change Graph and Forge/Surgeon staging;
- no separation between proposal evidence and mutation authority.

## 4. Canonical ownership map

The Compass coordinates these owners; it does not replace them.

| Responsibility | Canonical owners |
|---|---|
| Six-slot intent and binding | `aura_polysynthetic_intent.py`, `aura_intent_ingestion.py` |
| Capability inventory and route | `aura_capability_connectome.py`, `aura_capability_connectome_v2.py`, `aura_affordance_directory.py` |
| Exact atomic grounding | `aura_emergent_evidence_spine.py`, CodeTopo, current source hashes |
| Repository anatomy | `aura_relational_index.py` |
| Objective JIT composition | `aura_relational_synthesis.py` |
| Relationship meaning and prohibitions | `aura_relationship_atlas.py` |
| Unwired candidate discovery | `aura_emergent_potential_repl.py`, `aura_emergent_result_verifier.py` |
| Symbolic planning and continuity | `aura_planning_board.py`, `aura_coding_arena_planning.py` |
| Coding circuit preflight | `aura_coding_waboose_breadboard.py` |
| Architecture and critic routing | `aura_live_architect.py`, `aura_architect_council_v3.py` |
| Executable proposal IR | `aura_change_graph.py`, `aura_agent_ir_compiler.py` |
| Local implementation and repair | Surgeon, Coding Arena, Forge |
| Review and learned defect classes | Coding Waboose, Crucible |
| Observation and continuity memory | `aura_qdkt_observations.py`, `aura_symbolic_trace_memory.py`, `aura_arena_experience_ledger.py`, `aura_temporal_persistence.py` |
| Publication | Agent Bridge atomic GitHub publication lane; human merge remains separate |

Only two new source owners are justified:

1. `aura_coding_relationship_compass.py` — objective-scoped orchestration and packet compilation.
2. `aura_relationship_contracts.py` — immutable compatibility contracts, projections, outcomes, and deterministic preflight.

Everything else is an extension of an existing canonical owner.

## 5. Target contracts

### 5.1 `RelationshipContract`

```yaml
schema_version: AURA_RELATIONSHIP_CONTRACT_V1
contract_id: content_addressed
objective_digest: required
intent_packet_digest: required
source_repository:
  repo_head: exact
  working_tree_digest: exact
  relational_index_digest: exact
  atlas_digest: exact
domain: CODE | MEMORY | GOVERNANCE | SPATIAL | NETWORK | OTHER
slots:
  DIR: bounded_scope_or_reach
  ASP: lifecycle_and_mutation_posture
  CLASS: data_resource_thermal_class
  SUBJ: authenticated_actor_role
  VOICE: boundary_and_port_direction
  STEM: operation_or_capability_identity
truth_class: exact_enum
authority_posture: exact_enum
proof_status: exact_enum
policy_scope: explicit
resource_budget: explicit
source_refs: exact_spans_and_hashes
prohibition_ids: []
```

### 5.2 `RelationshipCompatibilityAssessment`

```yaml
schema_version: AURA_RELATIONSHIP_COMPATIBILITY_V1
assessment_id: content_addressed
left_contract_digest: required
right_contract_digest: required
outcome: COMPATIBLE | ADAPTER_REQUIRED | AUXILIARY_ONLY | PROHIBITED | INSUFFICIENT_EVIDENCE
hard_guard_results: []
port_matches: []
resource_fit: bounded_result
authority_fit: bounded_result
required_adapters: []
missing_evidence: []
risks: []
required_verifiers: []
advisory_score: optional_after_hard_guards
patch_authority: false
human_review_required: true
```

Hard guards execute in this order:

1. repository and packet identity;
2. exact source freshness;
3. capability and policy scope;
4. actor, delegation, lease, consent, and validity;
5. prohibited relationship patterns;
6. scope, resource, thermal, data, and egress budgets;
7. proof and verifier readiness;
8. only then advisory ranking.

### 5.3 `RelationalNeighborhoodRequest`

```yaml
schema_version: AURA_RELATIONAL_NEIGHBORHOOD_REQUEST_V1
objective_digest: required
seed_participant_ids: bounded
seed_source_refs: exact
max_hops: 1..3
max_nodes: bounded
max_edges: bounded
max_candidate_pairs: bounded
allowed_relation_types: explicit
minimum_truth_class: explicit
include_tests: boolean
include_docs: boolean
include_auxiliary: boolean
stop_on_prohibition: boolean
```

Default profiles:

| Profile | Hops | Nodes | Edges | Maximum pairs | Use |
|---|---:|---:|---:|---:|---|
| `EDGE` | 1 | 64 | 256 | 2,016 | mobile/local quick routing |
| `STANDARD` | 2 | 128 | 512 | 8,128 | normal architecture work |
| `DEEP` | 3 | 256 | 1,024 | 32,640 | explicit high-risk authorization only |

The engine must stop at every bound and emit truncation evidence. It must never silently expand to all repository participants.

### 5.4 `CodingRelationshipCompassPacket`

```text
CodingRelationshipCompassPacket
├── objective and six-slot intent
├── exact repository identity and request digest
├── selected Connectome capabilities and route reasons
├── exact seed source slices and hashes
├── bounded relational neighborhood and inclusion evidence
├── Atlas assessments
│   ├── exactly wired / preserve
│   ├── overlapping but unwired
│   ├── auxiliary
│   ├── adapter required
│   ├── missing / redundant / uncertain
│   └── prohibited
├── compatibility assessments and hard-guard trace
├── bounded emergent candidates
├── smallest verification experiments
├── Planning Board proposal and Council V3 reports
├── required files, symbols, tests, schemas, and verifiers
├── Change Graph / Agent IR / Act Capsule proposals
├── cost, token, node, edge, pair, and cache evidence
├── risk map, rollback conditions, and claim boundaries
└── authority flags (all non-mutating)
```

Every recommendation must identify the exact functions/classes, source hashes, current data contract, required adapter, negative activation conditions, and proof required before construction.

## 6. Processing lifecycle

### Stage 1 — Normalize the objective

- Bind ordinary language to `PolysyntheticIntentPacket`.
- Record outcome, constraints, non-goals, risk, expected artifacts, forbidden changes, evidence threshold, budget, and desired depth.
- Reject empty, contradictory, unauthenticated, or mutation-seeking requests that lack the required authority route.

### Stage 2 — Select capabilities

- Build/enrich the Connectome once for the current identity.
- Resolve capability paths and classify nodes as available, selected, active, auxiliary, unresolved, or prohibited.
- Prefer existing owners and adapters before proposing a new module.
- Preserve route reasons and deterministic/model-dependent execution classes.

### Stage 3 — Ground exact source

- Run the Emergent Evidence Spine against selected files/symbols.
- Bind current repository head, atomic inventory digest, source hashes, tests, dependency edges, and risk map.
- Fail closed when exact grounding is unavailable.

### Stage 4 — Extract a bounded neighborhood

- Seed from exact atomic functions, capability implementations, tests, schemas, and declared interfaces.
- Expand deterministically by relation priority and truth class.
- Preserve an inclusion reason for every participant and edge.
- Stop at hop/node/edge/pair/byte/time budgets.
- Return a truncation frontier for optional Council-authorized expansion.

### Stage 5 — Classify with Atlas

- Keep repository-wide Atlas at `MINIMAL`.
- Run `OBJECTIVE_STANDARD` or `OBJECTIVE_DEEP` only on the neighborhood.
- Evaluate all seven existing prohibitions first.
- Classify exact wiring, overlap, auxiliary adjacency, missing motifs, redundant paths, adapters, uncertainty, and proof status.

### Stage 6 — Run compatibility and Breadboard preflight

- Project canonical intent and source evidence into typed relationship contracts.
- Reuse Planning Board `PortSpec`, direction, cardinality, constraints, effects, and reversibility concepts.
- Compile a Waboose Breadboard showing compatible tracks, adapter requirements, open circuits, feedback loops, overloads, and prohibited shorts.
- Return reasons; never mutate code or policy.

### Stage 7 — Discover bounded emergent candidates

Every candidate must include:

- exact participating symbols and evidence;
- objective relevance;
- proposed mechanism;
- expected benefit;
- failure modes and prohibited effects;
- confidence and evidence class;
- smallest deterministic verification experiment;
- a candidate Change Graph representation;
- `NEEDS_GROUNDING`, `READY_TO_TEST`, or another existing verifier status.

No emergent candidate can self-promote.

### Stage 8 — Plan with Architect and Council V3

- Architect consumes the Compass packet instead of rediscovering repository context.
- Council V3 routes only critic lanes justified by measured plan structure.
- Cross-system work of this size requires all six lanes.
- The plan is split into phase capsules with exact invariant digests, files/spans, dependencies, tests, rollback, and continuity checkpoints.
- Interface, invariant, dependency, material scope, or cost failures return to Council; local assertion failures go to Surgeon.

### Stage 9 — Compile proposal IR

- Convert accepted Planning Board actions into Change Graph nodes and dependencies.
- Add test, risk, verifier, authority, and rollback nodes.
- Compile Agent IR and Act Capsules only for exact grounded spans.
- Keep `safe_to_patch=false` until the normal Forge/Surgeon staging workflow admits a separate implementation action.

### Stage 10 — Verify, decide, and learn

- Surgeon implements one bounded phase.
- Coding Waboose, static checks, focused tests, owner regressions, schemas, Crucible replay, and human review prove or reject it.
- Record successful, failed, denied, abandoned, and rolled-back attempts.
- Project only eligible verified experience into QDKT/trace/experience memory.
- Never convert a clean past receipt into a guarantee for a future head.

## 7. Phased implementation program

Each phase is independently reviewable and reversible. Do not combine the program into one giant implementation PR.

### C0 — Harness and provenance hardening

**Implementation status:** complete in the current implementation branch; focused harness, Atlas, and read-only Architect regressions pass.

**Purpose:** make architecture analysis reproducible, reference-bound, resumable, and genuinely read-only.

**Files:**

- `scripts/aura_architecture_harness.py`
- `aura_relationship_atlas.py`
- `aura_architect_loop.py`
- `tests/test_aura_architecture_harness.py`
- `tests/test_aura_relationship_atlas.py`
- `test_aura_architect_loop.py`
- `docs/AURA_ARCHITECTURE_HARNESS.md`

**Implemented during this planning run:**

1. Coerce serialized custom output paths back to `Path` before use.
2. Allow Atlas to compile from supplied Relational Index data with `persist=False`.
3. Prevent Atlas markdown/navigation writes during read-only harness analysis.
4. Add `refresh_codemap=False` to Architect grounding and use it from the harness.
5. Bind external reference files into request and run receipts by size and SHA-256.
6. Add regression tests for all of the above.

**Acceptance:**

- focused harness/Atlas/Architect suite passes;
- final reference-bound run reports `ok=true`;
- pre/post repository identity and status are identical;
- output artifacts exist only outside the source checkout;
- missing or changed reference files invalidate resume.

**Rollback:** revert the C0 commit set; no state migration is required.

### C1 — Contract, schema, and ontology lock

**Implementation status:** complete in the current implementation branch with strict runtime/schema parity, authority tamper rejection, deterministic digests, and hard-guard ordering.

**Purpose:** establish stable types before expanding behavior.

**New files:**

- `aura_relationship_contracts.py`
- `schemas/aura_relationship_contract.schema.json`
- `schemas/aura_relationship_compatibility.schema.json`
- `schemas/aura_relational_neighborhood_request.schema.json`
- `schemas/aura_coding_relationship_compass.schema.json`
- `tests/test_aura_relationship_contracts.py`

**Existing owners touched:**

- `aura_polysynthetic_intent.py`
- `aura_relational_synthesis.py`
- `aura_relationship_atlas.py`

**Deliverables:**

- immutable enums/dataclasses and strict canonical deserialization;
- explicit split between six-slot intent, domain, truth, proof, authority, and policy;
- deterministic digests and exact-key validation;
- typed compatibility outcomes and hard-guard reasons;
- no regex authority and no raw patch payload.

**Acceptance:** schema/runtime parity, unknown-key rejection, enum exhaustiveness, digest determinism, tamper tests, cultural-claim language review, and all authority flags false.

**Rollback:** delete the unused V1 contracts before any public writer exists. After a writer exists, version rather than mutate the schema.

### C2 — Objective normalization and Connectome selection

**Implementation status:** complete in the current implementation branch by rebasing the safe PR #175 seed over C0 and binding it to the C1 objective contract.

**Purpose:** turn the objective into a bounded initial capability set.

**Primary files:**

- `aura_coding_relationship_compass.py` (new orchestrator)
- `aura_capability_connectome.py`
- `aura_capability_connectome_v2.py`
- `aura_affordance_directory.py`
- `tests/test_aura_coding_relationship_compass.py`

**Deliverables:**

- strict Compass intent admission;
- deterministic objective contract;
- selected/active/auxiliary/unresolved/prohibited capability classes;
- route reasons and zero-model eligibility;
- current implementation/test/document references;
- bounded target file and symbol lists.

**PR #175 reuse:** retain its objective-scoped compiler, Connectome enrichment, exact Evidence Spine use, proposal-only authority flags, affordance registration, and focused tests. Rebase after C0 and replace overlapping Atlas/harness changes with the C0 versions.

**Acceptance:** unrelated architecture prompts do not route through Compass; explicit Compass/cross-plane prompts do; no full repository source is placed in a model prompt; exact source grounding is required.

**Rollback:** disable the Compass affordance and Architect route; legacy grounding remains available.

### C3 — Exact bounded relational neighborhood

**Implementation status:** complete in the current implementation branch with canonical digest validation, deterministic exact-seed expansion, six independent budgets, reverse-index selectors, and explicit frontier/truncation receipts.


**Purpose:** prevent full-index construction from being the first operation for every Compass request.

**Primary files:**

- `aura_relational_index.py`
- `aura_emergent_evidence_spine.py`
- `aura_coding_relationship_compass.py`
- `tests/test_aura_relational_index.py`
- `tests/test_aura_coding_relationship_compass.py`

**Deliverables:**

- `extract_relational_neighborhood(request, index)`;
- deterministic priority queue by exactness, relation class, and objective evidence;
- bounded reverse-index lookup by file, symbol, capability, test, schema, and owner;
- per-node/edge inclusion reasons;
- frontier and truncation receipt;
- time, node, edge, pair, output-byte, and recursion budgets.

**Acceptance:** no quadratic loop; stable result ordering; exact seeds always retained; bounds hold under adversarial dense fixtures; stale index fails closed; complete source tree is not scanned after a valid current index is loaded.

**Rollback:** retain existing full-index APIs; remove the new neighborhood entry point.

### C4 — Objective-scoped Atlas reasoning

**Implementation status:** complete in the current implementation branch with `MINIMAL_GLOBAL`, `OBJECTIVE_STANDARD`, and `OBJECTIVE_DEEP` profiles, bounded local compilation, global pair guards, and a byte-bounded semantic-no-op LRU cache.


**Purpose:** separate global relationship coverage from local deeper intelligence.

**Primary files:**

- `aura_relationship_atlas.py`
- `aura_relational_synthesis.py`
- `aura_coding_relationship_compass.py`
- `tests/test_aura_relationship_atlas.py`
- `tests/test_aura_relational_synthesis.py`

**Deliverables:**

- profiles `MINIMAL_GLOBAL`, `OBJECTIVE_STANDARD`, and `OBJECTIVE_DEEP`;
- compile from a supplied bounded participant/edge set;
- preserve current 8-dimensional assessments and 7 prohibitions;
- objective-local overlap, auxiliary, missing motif, redundancy, conflict, and adapter analysis;
- nonpersistent default for Compass;
- byte-bounded LRU cache keyed by repository/index/neighborhood/profile digests.

**Acceptance:** global STANDARD/DEEP remains refused above pair limit; local deep output validates; all prohibitions precede ranking; cache eviction is deterministic; cache removal changes no semantic result.

**Rollback:** use current MINIMAL Atlas projection only.

### C5 — Typed compatibility and Coding Breadboard

**Implementation status:** complete in the current implementation branch with typed interfaces, seven ordered hard guards, proposal-only Planning Board projection, circuit breakers, and human/machine Breadboard receipts.


**Purpose:** convert relationship meaning into deterministic preflight without granting authority.

**Primary files:**

- `aura_relationship_contracts.py`
- `aura_planning_board.py`
- `aura_coding_arena_planning.py`
- `aura_coding_waboose_breadboard.py`
- `tests/test_aura_planning_board.py`
- `tests/test_aura_coding_arena_planning.py`
- `tests/test_aura_coding_waboose_breadboard.py`
- `tests/test_aura_relationship_contracts.py`

**Deliverables:**

- projection from `PolysyntheticIntentPacket` and exact evidence to `RelationshipContract`;
- compatibility matrix for port direction/cardinality, lifecycle, actor, boundary, resource/data class, and operation;
- adapter-required and auxiliary-only outcomes;
- prohibition and insufficient-evidence circuit breakers;
- Planning Board projection with preconditions/effects/reversibility;
- human-readable Breadboard and machine-readable receipt.

**Acceptance:** optative/proposal routes cannot mutate; output-output, cardinality, policy, actor, stale-proof, over-budget, and prohibited fixtures fail with exact reasons; advisory scores cannot override hard guards.

**Rollback:** keep compatibility as an Observatory-only shadow projection; do not energize it in Architect selection.

### C6 — Bounded Emergent discovery and verification experiments

**Purpose:** discover useful unwired combinations only after exact local selection.

**Primary files:**

- `aura_emergent_potential_repl.py`
- `aura_emergent_result_verifier.py`
- `aura_coding_relationship_compass.py`
- related Emergent tests and fixtures

**Deliverables:**

- accept the neighborhood and compatibility results as bounded inputs;
- exclude exact/prohibited/redundant relationships;
- require mechanism, benefit, risk, failure conditions, and smallest experiment;
- cluster and diversify candidates;
- compile candidate Change Graph nodes without patch authority;
- preserve rejected and suppressed candidate receipts.

**Acceptance:** every candidate is traceable to exact evidence; no generic repository-wide scan is triggered; deterministic fixture ordering; unsafe candidates remain `TOO_RISKY`; missing evidence remains `NEEDS_GROUNDING`.

**Rollback:** omit emergent candidates from the Compass packet; the main grounding pipeline remains useful.

### C7 — Architect, Council V3, Change Graph, Agent IR, and Act Capsules

**Purpose:** turn grounded relationship intelligence into bounded implementation work.

**Primary files:**

- `aura_live_architect.py`
- `aura_architect_council_v3.py`
- `aura_change_graph.py`
- `aura_agent_ir_compiler.py`
- `aura_coding_relationship_compass.py`
- Architect, Change Graph, and Agent IR tests

**Deliverables:**

- explicit Compass grounding route before filename inference;
- no duplicate MUSIC/Mitosis emergent pass when Compass evidence is present;
- Council V3 critic routing recorded in the plan receipt;
- phase capsules with invariant digests and continuity checkpoints;
- Change Graph nodes for actions, tests, risks, adapters, prohibitions, proof, rollback, and human decisions;
- actual proposal-only Act Capsules, replacing “capsule hints”;
- Surgeon-ready requests limited to exact spans and declared tests.

**Acceptance:** local assertion failures route to Surgeon; interface/dependency/invariant/scope failures route to Council; no task crosses phase scope; capsule compiler refuses missing source hashes, tests, or authority boundaries; no automatic commit/PR/merge.

**Rollback:** disable Compass routing and continue to use deterministic CODEMAP planning.

### C8 — Governed bi-temporal experience projection

**Purpose:** learn which relationships succeeded, failed, or were rejected without creating a competing truth store.

**Primary files:**

- `aura_qdkt_observations.py`
- `aura_symbolic_trace_memory.py`
- `aura_arena_experience_ledger.py`
- `aura_temporal_persistence.py`
- Crucible and Coding Waboose learning owners
- corresponding tests and schemas

**Deliverables:**

- a relationship-experience observation type;
- valid-time interval bound to repository heads and relationship identities;
- transaction time bound to receipt creation;
- verifier and human disposition;
- success, failure, denial, abandonment, and rollback outcomes;
- Ebbinghaus-style decay only as an advisory retrieval rank over experience, never canonical relation validity;
- why/timeline projections reconstructed from receipts;
- Crucible replay scenarios for promoted lessons.

**Eligibility gate:** no observation becomes a reusable lesson until exact experience, verifier evidence, authority disposition, privacy checks, and current-source corroboration are present.

**Acceptance:** historical facts are never overwritten; stale experience is labeled; cache/database loss is recoverable from canonical receipts; failed attempts remain visible; private/raw source is excluded.

**Rollback:** stop new experience projection and rebuild/ignore the derived store; canonical architecture remains intact.

### C9 — Interfaces, rollout, and measured proof

**Purpose:** expose the Compass safely and prove it improves coding work.

**Primary files:**

- `aura_agent_arena_mcp.py` or a narrow bridge module
- `aura_affordance_directory.py`
- Coding Arena/Human Agent/Observatory projection owners
- `docs/AURA_CODING_RELATIONSHIP_COMPASS.md`
- `USER_GUIDE.md`, `.aura/ARCHITECTURE.md`, `README.md`
- schemas, examples, benchmarks, and end-to-end tests

**Read-only tools:**

```text
aura_compass_prepare
  → aura_compass_neighborhood
  → aura_compass_classify
  → aura_compass_breadboard
  → aura_compass_plan
  → aura_compass_compile_capsules
```

The first five tools are read-only/proposal-only. Capsule compilation still produces no patch authority and must hand off to the normal Forge/Surgeon workflow.

**Rollout:**

1. `SHADOW` for explicit Compass intents.
2. Compare against current Architect grounding without provider execution.
3. Limited route for named cross-system refactors after quality gates pass.
4. Optional `PAIRED_LIVE` only under explicit provider, budget, nonce, and verifier authorization.
5. General availability only after repeated exact-head evidence.

**Acceptance:** CLI/MCP/schema parity; no unrestricted payloads; browser views remain non-authoritative; accessibility; deterministic receipts; exact-head end-to-end test; documentation claims match measured evidence.

**Rollback:** remove/disable affordance and bridge exposure while retaining internal APIs.

## 8. Test and verification matrix

Every phase runs compilation, static checks, focused tests, canonical-owner regressions, schema validation, tamper tests, and authority checks before CODEMAP regeneration.

Minimum retained suite:

```text
tests/test_aura_architecture_harness.py
tests/test_aura_relationship_atlas.py
tests/test_aura_relational_index.py
tests/test_aura_relational_synthesis.py
tests/test_aura_coding_relationship_compass.py
tests/test_aura_relationship_contracts.py
tests/test_aura_planning_board.py
tests/test_aura_coding_arena_planning.py
tests/test_aura_coding_waboose_breadboard.py
Architect Council V3 tests
Change Graph and Agent IR tests
QDKT, trace memory, experience ledger, temporal persistence, Waboose, and Crucible tests
```

Required adversarial cases:

- stale repository head, index, Atlas, source span, or intent digest;
- unknown schema keys and enum values;
- symlink/path traversal and oversized reference/output files;
- dense graph, cycle, self-loop, duplicate edge, and pair explosion;
- prohibited wiring disguised through aliases;
- proposal intent attempting state mutation;
- actor/delegation mismatch;
- output-to-output and cardinality mismatch;
- over-thermal/CPU/memory/token/egress budget;
- missing verifier, test, rollback, or human decision;
- cache poisoning, stale cache, partial write, lock contention, corruption, and rebuild;
- replay and receipt tampering;
- hidden mutation of `.aura`, CODEMAP, topology, memory, or source during read-only analysis.

## 9. Performance, cost, and evidence requirements

### Hard bounds

- No full-repository STANDARD or DEEP all-pairs Atlas pass.
- Default neighborhood: at most 128 nodes, 512 edges, and 8,128 candidate pairs.
- Explicit DEEP ceiling: 256 nodes, 1,024 edges, and 32,640 pairs.
- Every array, string, source slice, test list, candidate list, cache entry, and serialized packet has count and byte bounds.
- Every bounded operation has a timeout/cancellation path and a receipt describing truncation.

### Baseline

The clean reference-bound harness run completed the current global MINIMAL workflow in 27.504 seconds on the planning container. This is a baseline for regression comparison, not a universal SLA.

### Required benchmark arms

1. current Architect/CODEMAP grounding;
2. Compass with global MINIMAL + bounded STANDARD;
3. Compass with compatibility preflight but no model;
4. optional paired provider route under explicit authorization.

Measure separately:

- elapsed time;
- peak RSS and serialized bytes;
- nodes, edges, pairs, source lines, and candidate counts;
- provider-reported tokens when available;
- tokenizer-exact or clearly labeled proxy tokens;
- cache hit/miss and build time;
- target localization precision/recall;
- required-file and required-test recall;
- prohibited-relationship recall;
- accepted finding precision;
- implementation test pass rate and review defects.

Do not claim savings unless quality is comparable or better. Never convert unavailable tokens or cost into zero.

## 10. Continuity and PR strategy

### Phase capsule rule

Each C0–C9 phase records:

- exact objective and phase ID;
- source main SHA and invariant digests;
- allowed files and source spans;
- inputs, dependencies, interfaces, and expected outputs;
- tests, verifiers, and evidence class;
- authority boundary;
- rollback/abandonment condition;
- remaining work and next checkpoint.

Use temporal checkpoints between phases. A changed repository head or invariant requires Restoration Council review, not blind resume.

### Pull request sequence

Recommended sequence:

1. **PR A — C0 harness hardening and this plan.** No Compass production route.
2. **PR B — C1 contracts and schemas.** Types only.
3. **PR C — C2–C3 selection and bounded neighborhood.** Rebase and reuse safe PR #175 work.
4. **PR D — C4 Atlas objective profiles.** No Breadboard or Architect activation yet.
5. **PR E — C5 compatibility/Breadboard.** Shadow projection only.
6. **PR F — C6 emergent experiments.** Still proposal-only.
7. **PR G — C7 Architect/Council/capsule compilation.** Explicit intents only.
8. **PR H — C8 governed experience projection.** Learning gate closed by default.
9. **PR I — C9 tools, UI, rollout, benchmarks, and final documentation.**

PR #175 should not be merged unchanged. It is a valuable implementation seed, but it predates C0's harness fixes and does not yet provide true bounded-neighborhood construction, typed compatibility/Breadboard contracts, actual Change Graph/Agent IR compilation, governed bi-temporal learning, or complete performance budgets.

Each PR follows:

```text
exact grounding
  → phase capsule
  → Council V3 when architecture/interfaces change
  → Surgeon implementation
  → focused tests and owner regressions
  → Coding Waboose
  → Crucible replay where applicable
  → manual review
  → CODEMAP/topology regeneration
  → final exact-head verification
  → human merge decision
```

## 11. Cross-cutting invariants

```yaml
compass_is_orchestration_layer: true
compass_is_truth_owner: false
compass_is_policy_authority: false
compass_is_patch_authority: false
relationship_contract_is_derived_projection: true
six_slot_parser_is_reused: true
linguistic_families_are_not_declared_interchangeable: true
hard_guards_precede_advisory_ranking: true
global_atlas_profile: MINIMAL
objective_deep_analysis_is_bounded: true
candidate_relationships_cannot_self_promote: true
prohibitions_require_reason_and_are_evaluated_first: true
exact_current_source_is_required: true
memory_is_derived_and_rebuildable: true
failures_and_denials_are_retained: true
production_mutation: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

## 12. Definition of done

The Compass program is complete only when all of the following are true:

1. An objective produces a canonical intent packet and exact repository identity.
2. Connectome selection is bounded, explainable, and prefers current owners.
3. Exact source/test/schema grounding succeeds or the run fails closed.
4. Neighborhood extraction proves it did not exceed hop/node/edge/pair/byte/time limits.
5. Atlas classifies the local neighborhood and evaluates all prohibitions first.
6. Typed compatibility and Breadboard preflight produce exact, testable reasons.
7. Emergent candidates carry mechanisms, failure modes, and smallest experiments.
8. Council V3 reviews every required lane and emits phase capsules.
9. Accepted actions compile into valid Change Graph, Agent IR, and proposal-only Act Capsules.
10. Surgeon and review systems can implement and verify each phase independently.
11. Verified outcomes can be projected into governed bi-temporal experience without overwriting canonical truth.
12. Shadow/paired evidence shows equal or better coding quality under disclosed cost and performance measurements.
13. Documentation, schemas, runtime behavior, generated navigation, and exact-head tests describe the same artifact.
14. A human maintainer explicitly approves each merge and any later activation.

## 13. Immediate next implementation action

Review the **C3–C5 implementation batch** after branch CI and exact-head verification. The next implementation batch should begin **C6**: bounded Emergent discovery and verification experiments over the C3 neighborhood, C4 objective Atlas, and C5 compatibility/Breadboard receipts.

Do not allow C6 discovery to bypass C5 hard guards, expand beyond C3 budgets, or promote advisory findings into exact truth without current source and verifier evidence.

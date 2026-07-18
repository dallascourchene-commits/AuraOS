# Aura Relational Synthesis — Current-Main Refactoring and Integration Plan

**Status:** Active implementation plan  
**Repository baseline:** `main` at `940a7510904a984795ea26560d54133e52680115`  
**Baseline feature:** merged PR #156, Emergent Evidence Spine + Coding Waboose V1.1  
**Active branch:** `feature/aura-relational-synthesis-r1`  
**Active phase:** Phase 1 — contracts and shadow compiler  
**Primary Arenas:** Coding Waboose, Coding Arena, Agent Bridge  
**Later projections:** Human Agent, Observatory, Crucible, Tensor Evidence, Construction, Civic, Financial, Model Cognome  
**Plan type:** reuse-first, additive, feature-flagged, evidence-bound

---

## 1. Executive decision

Aura should adopt a canonical **Relational Synthesis layer** that gives each atomic function, capability, action, person, state object, or Arena object two simultaneous identities:

1. an exact atomic identity owned by source, schema, manifest, test, runtime state, or another canonical truth owner;
2. an objective-specific relational identity describing why it participates, what role it occupies, what it depends on, what authority constrains it, what consequences flow through it, and what proof must exist.

```text
Ahead-of-Time relational anatomy
  + Just-in-Time objective synthesis
  + exact current revalidation
  = bounded Relational Synthesis Capsule
```

The AOT layer materializes stable anatomy and reverse indexes. The JIT layer selects the smallest evidence-complete objective configuration and revalidates it against current canonical owners. This prevents both repeated full-repository rediscovery and stale instant recall.

Relational Synthesis is a **compiled view**. It must not become another CODEMAP, topology engine, Capability Connectome, planner, truth store, patch engine, verifier, authority service, or learning authority.

---

## 2. Current merged baseline

PR #156 made the following sequence permanent:

```text
Capability Connectome V2
  → Capability Resolver V2
  → complete atomic-function inventory
  → exact CodeTopo dependency closure
  → bounded Emergent Capability Auditor
  → research projection
  → Coding Arena / Waboose / Human Agent / Agent Bridge projections
  → verifier and human decision
```

The regenerated current-main self-model reports:

```text
files:                 1,111
estimated text tokens: 3,714,161
topology nodes:        9,020
topology edges:        19,897
topology source:       compiled_deep_topology
```

Phase 0 of the earlier plan is complete: PR #156 merged; CODEMAP and deep topology were regenerated; invalid-target and bounded-endpoint defects were fixed; CodeRabbit lessons require current-head reproof; and temporary finalization machinery was removed.

Relational work therefore starts from merged `main`, not a pre-merge PR head.

---

## 3. Architectural synthesis from both source documents

### 3.1 Relational identity is the missing unit

A function is not operationally meaningful in isolation. Its current objective-specific meaning comes from the full configuration around it:

```text
atomic object
  + role bindings
  + typed dependencies
  + authority boundaries
  + evidence
  + temporal or causal readiness
  + proof obligations
  = relational identity
```

The useful innovation is not ordinary graph traversal. It is governed compilation of an n-ary, role-labelled, evidence-pinned configuration that cannot silently detach code from system responsibilities.

### 3.2 AOT anatomy and JIT synthesis are complementary

The architecture discussion's “full body sweep” becomes an AOT materialized anatomy, but the plan rejects precomputing every possible objective combination.

Precompute:

- macro domains;
- surgical cross-domain bundles;
- reverse indexes;
- candidate motifs;
- freshness and invalidation receipts.

Compile per objective:

- focal participants;
- exact current closure;
- current diff/workspace/range identity;
- authority and lease state;
- tests and verifier obligations;
- source slices;
- omitted boundaries;
- causal path status;
- Arena projection budgets.

“Instant recall” is a performance target to benchmark, not an unmeasured O(1) guarantee.

### 3.3 The six-slot contract is reused, not copied

Relational Synthesis uses the existing canonical `PolysyntheticIntentPacket`:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

| Slot | Relational responsibility |
|---|---|
| DIR | relationship neighbourhood, destination, affected Arena |
| ASP | lifecycle, readiness, recurrence, expiry, causal stage |
| CLASS | relation, capability, or operation family |
| SUBJ | focal participant |
| VOICE | agency, consent, authority, delegation posture |
| STEM | transformation or operation |

No seventh slot is added. Adjunct risk, tests, cost, grounding, and jurisdiction remain orthogonal. The engineering contract is described as polysynthesis-inspired; it is not presented as a universal claim about polysynthetic languages or speakers.

### 3.4 Hard guards precede relational ranking

```text
state identity
  → capability and policy
  → lease / consent / validity / risk
  → evidence and verifier requirements
  → reject blockers
  → relational lookup and soft ranking among admitted options
```

No VSA resonance, Connectome affinity, learned motif, tensor score, or model proposal may rescue an option that failed a hard guard.

---

## 4. Phase 1 grounding discoveries

The first Aura-native grounding run used broad explicit files and proved an important constraint:

> Broad file targets can consume the bounded seed budget with every callable in an early large module, crowding out intended canonical owners.

The upgraded seed precedence is:

1. explicit file and qualified symbol;
2. explicit qualified symbol;
3. changed qualified symbols from exact diff/range/workspace;
4. Capability Resolver exact matches;
5. Connectome implementation symbols pinned to files;
6. exact related functions;
7. advisory objective affinity fallback.

Broad file-only seeding is valid for inventory browsing, but must not be the primary precision path for an evidence-complete relational capsule.

The refined grounding receipt binds exact slices for:

- `AuraEmergentEvidenceSpine.run`;
- `build_atomic_function_inventory`;
- `_assemble_packet`;
- `_source_slice`;
- `PolysyntheticIntentPacket.from_slots`;
- `PolysyntheticIntentPacket.canonical_dict`;
- `PolysyntheticIntentPacket.digest`;
- `ExecutableRouteCapsule.from_dict`;
- `ExecutableRouteCapsule.canonical_dict`;
- `ExecutableRouteCapsule.digest`;
- `CodingArenaCompatibilityReport.__post_init__`;
- `CodingArenaCompatibilityReport.to_dict`;
- `CodeTopoNode.to_dict`;
- `CodeTopoEdge.to_dict`;
- `canonical_json`;
- `stable_digest`;
- `stable_id`.

### 4.1 Test proof correction

An Evidence Spine packet may contain an exact test filename without exposing the exact callable that owns a test edge or the invariant it proves.

```text
test filename ≠ exact test callable proof
```

Phase 1 must preserve exact test callables when present, mark filename-only ownership `UNRESOLVED`, emit a proof obligation rather than fabricating a callable relation, and carry the gap into the omitted-boundary record.

---

## 5. Architecture containers

| Container | Canonical owner and phase | Role |
|---|---|---|
| C0 Exact Self-Model | CODEMAP, topology, CodeTopoAnchor | exact IDs, spans, hashes, calls, imports, tests |
| C1 Capability Anatomy | Connectome V1/V2, Resolver V2, Affordance Directory | reuse and advisory capability paths |
| C2 Materialized Relational Anatomy | future `aura_relational_index.py`, Phase 2 | generated AOT cache and reverse indexes |
| C3 Objective Relational Synthesis | `aura_relational_synthesis.py`, Phase 1+ | digest-pinned objective view |
| C4 Coding Diagnostic Circuit | Waboose, Review Arena, Breadboard, Phase 4 | relational review circuits |
| C5 External Worker Lease | Agent Bridge, MCP, persistence, Phase 5 | bounded worker projection |
| C6 Evidence and Verification | tests, verifiers, receipts | proof, not authorization |
| C7 Governed Relational Learning | Waboose Learning, DREAM-lite, QDKT, Crucible, Phase 7 | verified motif learning |
| C8 Observatory/Human Projection | Observatory and Human Agent, Phase 8 | explanation only |

---

## 6. Canonical authority invariants

```yaml
atomic_source_identity_is_exact: true
relational_capsule_is_compiled_view: true
relational_capsule_is_patch_authority: false
connectome_is_advisory: true
emergent_motifs_are_advisory_until_reproved: true
tensor_projection_is_advisory: true
agent_proposed_relations_are_not_exact: true
planning_proposes: true
verification_proves: true
human_authorizes: true
safe_to_patch: false
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

---

## 7. Core V1 contracts

### 7.1 Truth classes

```text
EXACT_SOURCE
EXACT_SCHEMA
EXACT_TEST
EXACT_MANIFEST
EXACT_RUNTIME
ADVISORY_CONNECTOME
ADVISORY_AFFINITY
INFERRED_MOTIF
UNRESOLVED
```

Exact classes require current digests and evidence references. Unresolved participants must not carry exactness.

### 7.2 Relational participant

A participant binds deterministic ID, participant type, role, truth class, canonical owner/ref, current digest when exact, evidence refs, freshness, qualified symbol, and bounded metadata. Identity is based on canonical identity—not current role—so one participant may hold different roles without becoming duplicate truth.

### 7.3 Typed relation

A relation binds deterministic ID, relation type, source/target participant IDs, truth class, evidence refs, and metadata. Every emitted endpoint must be present; exact relations require evidence.

### 7.4 Relational group

A group is an n-ary role-labelled configuration containing role bindings, typed relations, predicates, temporal conditions, authority constraints, proof obligations, boundary, canonical owner refs, and deterministic ID/digest. V1 uses immutable serializable data; no hypergraph dependency is required.

### 7.5 Proof obligation and boundary

Proof status is `OPEN`, `SATISFIED`, `CONTRADICTED`, or `DEFERRED`. A satisfied obligation must carry evidence.

Every group and capsule records included IDs, omitted relation count, omitted counts by reason, unresolved relations, budget truncation, and endpoint completeness. Omitted counts must balance exactly.

### 7.6 Relational Synthesis Capsule

The capsule binds objective and digest, canonical six-slot intent packet/digest, repository HEAD, inventory and Connectome digests, source Evidence Spine packet identity, participants, groups, source slices, tests, active Arena, boundary, explicit false authority fields, and deterministic capsule ID/digest.

---

## 8. Phase 1 — Contracts and shadow compiler

### Deliverables

- `aura_relational_synthesis.py`;
- `schemas/aura_relational_participant.schema.json`;
- `schemas/aura_relational_group.schema.json`;
- `schemas/aura_relational_synthesis_capsule.schema.json`;
- `tests/test_aura_relational_synthesis.py`;
- this upgraded plan;
- exact grounding receipt;
- validation and Waboose evidence.

### Compiler input and limits

The compiler accepts a supplied, successful, exactly grounded `AuraEmergentEvidenceSpine` packet plus a canonical `PolysyntheticIntentPacket`.

It must not crawl the repository independently, create a second source inventory, execute a model, mutate Waboose or Agent Bridge, write an AOT index, or authorize repair.

It fails closed on mismatched repository HEAD, packet digest, inventory digest, objective/intent binding, source identity, qualified symbol, source hash, relation endpoint, duplicate ID, or authority field.

### Three initial shadow groups

#### `closure_packet_integrity`

Proves every dependency relation has both selected endpoints, every selected atomic participant has a source slice, qualified symbols and hashes remain current, and relation evidence is not patch authority.

#### `test_proof_ownership`

Preserves exact test callables and exact `TESTS` relations when present. Filename-only tests become unresolved participants with explicit proof obligations.

#### `input_scope_authority`

Binds an exact authority manifest directly. Function-name matches for input parser, scope normalizer, and packet assembler remain candidate role bindings with open proof obligations until structural, schema, manifest, or verifier evidence proves the role. Missing roles become explicit unresolved participants. Affinity fallback may never silently widen an explicit target.

### Phase 1 compatibility

No changes are made to Waboose prepare/finalize, Forge handoff, Agent Bridge packets, MCP tools, route capsules, learning promotion, or production runtime behavior. The public surface is a pure JSON shadow compiler.

### Required tests

- deterministic serialization under reordered inputs;
- qualified symbol preservation;
- duplicate rejection;
- endpoint completeness;
- exact/advisory/unresolved separation;
- stale HEAD/packet/inventory rejection;
- omitted-boundary accounting;
- contract/schema round-trip;
- strict Boolean and authority parsing;
- objective/intent mismatch rejection.

### Exit gate

```text
exact qualified-symbol grounding
→ py_compile
→ focused pytest
→ Ruff fatal rules
→ Bandit
→ schema checks
→ Phase 1 Waboose review
→ manual relational audit
→ remove temporary workflow
→ refresh touched CODEMAP paths
→ keep PR open for human review
```

---

## 9. Phase 2 — AOT relational index

Create `aura_relational_index.py` only after Phase 1 contracts stabilize. Deliver full-body sweep, macro groups, surgical bundles, reverse indexes, build receipt, atomic writes, full/incremental builders, status CLI, and optional CODEMAP refresh hook.

Initial macro domains:

1. intent and lexical routing;
2. WFST and route admission;
3. CODEMAP/topology/grounding;
4. Connectome and resolution;
5. Planning Board and breadboards;
6. relational authority and governance;
7. Coding Workbench/Forge/Waboose;
8. Agent Bridge and external workers;
9. evidence/verification/telemetry;
10. memory/DREAM/QDKT/Crucible;
11. persistence/checkpoints/JSpace;
12. Observatory/Human Agent;
13. Civic Commons;
14. Construction;
15. Financial exact state;
16. Tensor Evidence.

Initial surgical bundles:

```text
Coding Waboose + CodeRabbit Learning + DREAM-lite + QDKT
Construction + Tensor Evidence + HDC/VSA
Agent Bridge + temporal persistence + slice leases
FST + Capability Resolver + route capsules + capability leases
Crucible + verifier receipts + Arena Experience
CODEMAP + Connectome + Emergent Auditor + research lane
```

Keyword-only membership remains advisory. Exact membership requires source, topology, test, schema, affordance, or manifest evidence.

Freshness includes repository HEAD, workspace digest when relevant, CODEMAP digest, topology digest, Connectome digest, atomic inventory digest, and relational profile/schema digest. A stale index never claims exact grounding.

---

## 10. Phase 3 — Higher-order emergent motifs

Extend the existing auditor additively while preserving pairwise output by default.

Initial motifs:

- input-to-authority expansion;
- failure-to-state leakage;
- schema-to-runtime drift;
- closure-to-packet integrity;
- test-to-proof preservation;
- source-to-inventory integrity;
- learning-to-current-reproof.

Outputs are exact existing configuration, grounded missing relation, advisory motif candidate, future potential missing roles, or contradicted configuration. None grants patch authority.

---

## 11. Phase 4 — Coding Waboose relational circuits

Feature-flagged integration adds capsule/group/path/proof/boundary fields and a Breadboard substrate:

```text
Relational Capsule component
  → participant role components
  → causal path components
  → proof obligation components
  → directive investigation components
```

Initial deterministic packs:

- `relational_endpoint_integrity`;
- `relational_identity_consistency`;
- `relational_test_proof_integrity`;
- `relational_authority_path_integrity`;
- `relational_state_transition_consistency`.

Every pack requires positive and benign-lookalike fixtures.

---

## 12. Phase 5 — Agent Bridge and MCP

Feature-flagged tools:

- `aura_relational_index_status`;
- `aura_relational_group_lookup`;
- `aura_relational_capsule`;
- `aura_waboose_relational_packet`.

Requirements: strict types, exact repository-relative paths, source disclosure false by default, participant/source budgets, stale identity rejection, no mutation/promotion tools, and candidate agent relations that cannot self-upgrade to exact. Checkpoints preserve IDs and digests rather than unrestricted source copies.

---

## 13. Phase 6 — Route capsule and ephemeral lifecycle

Do not overload `CODING.LOCALIZE.V1`. Add `CODING.RELATIONAL_REVIEW.V1` after shadow validation.

```text
compile → digest → admit → lease read-only capabilities → project
→ receive evidence → verify → persist approved receipt refs → dissolve
```

The AOT index persists; objective capsules dissolve.

---

## 14. Phase 7 — Governed relational learning

Extend grounded CodeRabbit lessons with focal/participant roles, relation types, causal shape, authority family, proof-obligation types, and capsule/evidence digests.

```text
teacher finding
  → exact reviewed-head grounding
  → relational signature
  → DREAM-lite retrieval
  → QDKT observation
  → independent confirmation
  → Crucible proposal
  → false-positive and holdout validation
  → human-reviewed deterministic rule
```

No teacher, DREAM-lite result, QDKT crystal, or Crucible proposal is patch authority.

---

## 15. Phase 8 — Tensor Evidence, Observatory, Human Agent

Only after exact capsules stabilize:

```text
exact truth → exact typed relations → relational capsule
→ tensor factor projection → supported / contradicted / unresolved advisory result
```

Observatory explains participants, roles, inclusion reasons, truth classes, causal consequences, omissions, budgets, authority, tests/verifiers, and HEAD freshness. It does not execute.

---

## 16. Phase 9 — Cross-Arena adapters

Separate domain plans and verifier reviews are required for Human Agent readiness, Construction, Civic consent/jurisdiction, Financial exact state, and Model Cognome configuration. Coding success does not prove domain correctness.

```text
Construction:
task + prerequisites + materials + professional authority + site conditions
+ evidence + verifier + readiness

Civic:
proposal + affected people + consent + dissent + jurisdiction + treaty/law
+ evidence + quorum + appeal + review

Financial:
value + account + owner + currency + jurisdiction + transaction source
+ purpose restriction + authorization + settlement + reconciliation evidence
```

Domain truth owners remain canonical.

---

## 17. Metrics

Quality: confirmed defect recall, false-positive rate, independent Waboose/CodeRabbit findings, regression rate, repair attempts.

Friction: tool calls, searches, source lines delivered, context estimate, provider-reported usage where available, late scope expansion, handoffs, time to first confirmed finding.

Relational:

```text
RELATIONAL_COMPLETENESS_RATE
INSPECTABLE_RELATION_RATE
LATE_RELATION_DISCOVERY_RATE
CURRENT_REPROOF_RATE
```

AOT: full/incremental build time, lookup latency, index size, cache hit rate, stale rejection rate, and live revalidation time. Projected token savings must not be reported as provider-billed savings.

---

## 18. Merge protocol

Each phase:

1. resolve capabilities and prove reuse;
2. create a bounded phase packet;
3. implement only that phase;
4. run focused tests;
5. refresh touched CODEMAP paths;
6. verify topology;
7. run Coding Waboose;
8. perform manual relational audit;
9. request CodeRabbit;
10. implement valid findings;
11. rerun gates;
12. merge only after explicit human authorization.

Suggested series: R1 contracts/compiler; R2 AOT index; R3 motifs; R4 Waboose; R5 Agent Bridge; R6 route lifecycle; R7 learning; R8 Tensor/Observatory; R9 domain adapters.

---

## 19. Failure modes and controls

| Risk | Control |
|---|---|
| combinatorial explosion | AOT anatomy + JIT objective capsules |
| duplicate truth store | canonical refs, digest pinning, live revalidation |
| stale instant recall | freshness tuple and fail-closed invalidation |
| broad-seed crowding | qualified-symbol precedence |
| graph bloat | role budgets, mandatory-before-optional, explicit omissions |
| missing test proof | callable-level proof obligations |
| cultural overclaim | polysynthesis-inspired engineering wording |
| learning overfit | independent confirmation, holdouts, current reproof |
| tensor authority leak | advisory projection only |
| agent relation invention | candidate status until canonical validation |
| bureaucracy | MINIMAL, STANDARD, DEEP profiles |
| source disclosure | explicit bounded opt-in only |

---

## 20. Definition of success

Aura Relational Synthesis succeeds when a future agent receives the smallest current relationship configuration needed for an objective; every exact claim points to a canonical owner and digest; every endpoint is inspectable; unresolved roles are visible rather than invented; test proof names callables and invariants when exact; AOT lookup reduces rediscovery without bypassing JIT revalidation; learned motifs accelerate investigation without gaining authority; and no relational layer can mutate, patch, promote, commit, push, open, or merge by itself.

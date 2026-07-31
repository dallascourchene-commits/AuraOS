# AuraOS Architecture

> Canonical architecture, ownership, data-flow, and authority anchor for humans and AI agents

**Architecture audit:** reviewed through July 31, 2026 and the preceding merged development, including Relational Synthesis R2, Gate Phase 2, Spatial S0–S6, Construction Arena G0–G8, the merged Construction + Pascal Spatial Foundry PR1–PR5 path through PR #252, Coding Relationship Compass C0–C9, typed Coding Waboose review learning, source-integrity and Crucible ancestry hardening, bounded browser/interchange/Gaussian representation support, the Runtime Refactor Harness, and the atomic Agent Bridge GitHub publication lane.

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

## 3. AI-safe repository handoff boundary

The architecture harness treats AI review/export as an untrusted-input boundary. `scripts/aura_architecture_harness.py handoff` inventories the exact `HEAD` tree, preserves source commit and Git blob identity, streams working-tree SHA-256 values, and emits a bounded deterministic review companion outside the repository.

Three dispositions are canonical:

- `SOURCE_REVIEW`: tracked UTF-8 source/configuration/documentation below the configured ceiling; eligible for the lightweight Git-blob archive;
- `DIGEST_ONLY`: binary, oversized, symlink, sensitive, or runtime content represented only by bounded metadata;
- `REGENERATE_FROM_FINAL_TREE`: CODEMAP, topology, live topology AST, and P9 substrate outputs regenerated only after authoritative source and tests stabilize in Linux/LF.

Generated maps remain navigation evidence and never become patch authority. Dirty repositories fail closed by default; unrestricted giant diffs and unbounded subprocess capture are prohibited. Long architecture runs are supervised by a proposal-only watchdog: a 10-minute check-in classifies healthy, slow-but-progressing, stalled, or unknown state, while a 20-minute hard checkpoint terminates the child safely and requires explicit `--resume`. Watchdog receipts are external run artifacts and grant no mutation authority. The full exact Git export remains a separate forensic reconstruction artifact rather than the preferred AI review input.

## 3A. Exact-head transport and atomic bundle boundary

`scripts/aura_exact_head_transport.py` is the reusable exact-head transport owner introduced by Issue #200. It binds every operation to a lowercase 40-character expected commit, verifies the observed `HEAD`, and requires a clean working tree before and after export, materialization, or bundle construction. Failure receipts, archives, temporary materializations, and final bundle files must remain outside the source checkout.

The publication-bundle path is all-or-nothing. It emits canonical whole-file add/replace/delete operations only after validating the complete candidate tree against an explicit allowlist. Out-of-scope additions, modifications, deletions, symlinks, and special files fail closed, including formatter-induced whole-file changes. The architecture export workflow extracts the exact request revision into an external tools directory, compiles that request harness and transport helper, detaches to exact `main`, runs the request transport into a non-authoritative comparison directory, independently generates the authoritative native `git archive`, and requires byte-for-byte equality before upload. The helper prepares evidence only: `production_mutation=false`, `automatic_publication=false`, and `merge_authority=false`.

## 3B. Runtime Refactor Harness boundary

The Runtime Refactor Harness is an observation-and-proof owner attached to the stable Architecture Harness entrypoint. It does not replace Coding Arena, Forge, Waboose, Council, Crucible, Observatory, or Agent Bridge.

```text
repository-owned runtime profile + exact Git identity
  → external virtual environment
  → loopback-only server
  → readiness evidence
  → bounded real probe/browser sequence
  → retained verification commands
  → artifact hashes + cleanup receipt
  → RUNTIME_FAILURE_REPRODUCED or RUNTIME_VERIFIED
  → separately authorized repair
  → exact-profile rerun bound to the failed baseline
  → REPAIRED_AND_VERIFIED
  → Waboose + human review
```

Primary owners are `scripts/aura_runtime_refactor_harness.py`, the `runtime` delegation in `scripts/aura_architecture_harness.py`, repository profiles under `.aura/runtime_profiles/`, subsystem probes under `tests/runtime/`, and `docs/AURA_RUNTIME_REFACTOR_HARNESS.md`.

The harness distinguishes source truth, presentation truth, performance evidence, integrity evidence, and authority. A valid performance overrun may emit a degraded receipt without destroying a verified presentation; malformed timing, stale identity, unsafe paths, failed integrity, missing artifacts, non-loopback serving, process timeout, source mutation, or failed retained verification remain hard blockers.

```yaml
runtime_profile_authority: false
runtime_evidence_authority: false
production_mutation: false
automatic_fix: false
runtime_evidence_authority: false
automatic_runtime_patch: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

Runtime evidence can localize defects and prove a candidate repair on one exact tree. It cannot grant patch, publication, Construction, renderer, professional, or merge authority.

<!-- AURA_CONSTRUCTION_PASCAL_DEMO_OPERATIONS:START -->
## 3C. Construction + Pascal Spatial Foundry demonstration boundary

The merged PR1–PR5 Construction + Pascal Spatial Foundry is one governed demonstration path over existing owners. It does not add another Construction truth store, renderer truth store, runtime verifier, archive, rollback authority, policy plane, persistence plane, routing plane, or learning owner.

```text
clean exact repository head + bilateral confirmation
  → canonical Construction state and identity
  → P4 loopback server on 127.0.0.1:8768
  → pinned Pascal 2D/3D presentation organ
  → P3 synchronized Design / Floor Plan / As-built / Compare views
  → deterministic fifteen-chapter Director
  → explicit bounded incident capture
  → retained replay and Construction Demo Runtime Profile V2 on 127.0.0.1:8767
  → isolated repair route, degraded preview, exact rollback, successful preview
  → canonical U7 P0 → P1 → current reproof and human disposition
  → terminal dissolution and fresh relaunch
  → current-run screenshots, JSON receipts, Runtime Harness proof, and bilateral Waboose review
```

Ownership remains explicit:

- **Aura** owns bilateral intent, canonical Construction state, evidence, obligations, candidate roles, authority, Director admission, capture/replay, Runtime Profile V2 delegation, Attempt Archive references, rollback proof, U7 reproof, cleanup, and human-review disposition.
- **Pascal** is the pinned local disposable geometry/presentation organ for storey, node, dimensions, selection, and 2D/3D visual working state.
- **The local browser** is the trusted same-origin presentation agent under Trust Model A. The protocol proves ordering, anti-replay, current-run receipt binding, and retained browser/runtime evidence; it does not claim hostile-browser pixel attestation.

There are two operator surfaces:

1. manual presenter mode for a narrated recording, controlled through the Director UI;
2. full bilateral proof mode through `scripts/aura_construction_pascal_spatial_foundry_pr5_runtime.py`, which owns an exclusive fresh external evidence directory, drives headless Chromium, captures seventeen screenshots and exact JSON evidence, runs focused JavaScript/Python/CODEMAP checks, terminates the server, runs bilateral Waboose, verifies source preservation, and stops at human review.

Primary implementation owners:

- `aura_construction_foundry_director.py`;
- `aura_construction_pascal_spatial_foundry_p4_server.py`;
- `aura_construction_pascal_spatial_foundry_p3_server.py`;
- `aura_pascal_spatial_presentation_part1.py` through `aura_pascal_spatial_presentation_part5.py`;
- `scripts/aura_construction_pascal_spatial_foundry_pr5_runtime.py`;
- `scripts/aura_runtime_refactor_harness.py`;
- `scripts/aura_runtime_profile_v2_adapter.py`;
- `.aura/runtime_profiles/construction_pascal_spatial_foundry.v1.json`;
- `.aura/runtime_profiles/construction_pascal_spatial_foundry_bilateral.v2.json`;
- `tests/runtime/construction_pascal_spatial_foundry_browser_probe.cjs`;
- `tests/runtime/construction_pascal_spatial_foundry_probe_contract.cjs`.

Operational documentation is canonicalized in:

- `docs/AURA_CONSTRUCTION_FOUNDRY_OPERATOR_GUIDE.md`;
- `docs/AURA_CONSTRUCTION_FOUNDRY_VIDEO_SCRIPT.md`;
- `docs/AURA_CONSTRUCTION_FOUNDRY_EVIDENCE_GUIDE.md`;
- `docs/AURA_PASCAL_CONSTRUCTION_SPATIAL_FOUNDRY_MVP.md`.

Authority remains:

```yaml
projection_only: true
runtime_evidence_authority: false
construction_truth_mutation: false
professional_authority: false
physical_work_authority: false
payment_release: false
access_control: false
automatic_patch: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
automatic_deployment: false
automatic_learning_promotion: false
human_review_required: true
```
<!-- AURA_CONSTRUCTION_PASCAL_DEMO_OPERATIONS:END -->

## 4. Constitutional invariants

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

Presentation is never authority. A UI control, ranking, route, graph, probability, model response, compact frame, or generated plan cannot create permission that was never granted.

## 5. Truth and evidence order

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

<!-- AURA_JULY20_ARCHITECTURE_RECONCILIATION:START -->
## 4A. July 19–20 merged architecture reconciliation

### Spatial representation and governed presentation plane

Aura Spatial is one layered projection system over canonical owners, not a parallel topology or domain truth store.

```text
exact canonical owner
  → representation-independent Spatial contracts
  → rooted transforms + manifest-only asset registry
  → deterministic scene compilation
  → bounded interchange and representation decoding
  → device/render-plan negotiation
  → ephemeral presentation session
  → review-only interaction and minimized proof
  → assessment-only persistence
  → external human/domain decision
  → renderer-bound cleanup + lease dissolution
```

The merged stack is cumulative:

1. **S0–S2:** immutable frames/assets/entities/links/scenes/interactions, deterministic transforms, canonicalization, referential integrity, bounded Coding/Showcase adapters, six-slot interaction compilation, and fail-closed Forge handoff;
2. **S3-A/S3-B:** immutable device profiles, deterministic render planning, bounded session/server contracts, active WebGL2, shadow-only WebGPU, explicitly activated WebXR, accessible 2D, headless parity, deterministic camera/picking, cancellation, telemetry, and cleanup receipts;
3. **S4-A:** bounded glTF/GLB and PLY import with explicit units, coordinate conversion, provenance, metadata limits, and no external resource or executable-content authority;
4. **S4-B:** local-only SPZ v4 and `KHR_gaussian_splatting` RC import, deterministic fallback, immutable Gaussian payloads, decoded digest binding, Python/JavaScript parity, no-copy preflight, aggregate allocation/GPU/frame budgets, cancellation, disposal, and adversarial corpus validation;
5. **S5:** governed Spatial WFST lifecycle with exact scene/render-plan/session bindings, persistent Agent Bridge/MCP access, bounded proof metrics, Attempt Archive evidence, assessment-only checkpoints, Observatory projection, decision packets, and dissolution;
6. **Construction S6:** privacy-minimized projection of `ConstructionProjectState` and a canonically issued Construction runtime packet. The binding registry prevents fabricated or independently re-digested packet dictionaries from entering the adapter.

Primary current owners include `aura_spatial_arena.py`, `aura_spatial_session.py`, `aura_spatial_construction.py`, `aura_construction_runtime_binding.py`, `aura_spatial_agent_bridge.py`, `aura_spatial_mcp.py`, `aura_spatial_cli.py`, the browser renderer modules, representation importers, `.aura/arena_routes/spatial.v1.json`, and their schemas/tests.

Spatial authority remains:

```yaml
projection_only: true
renderer_authority: false
execution_authority: false
production_mutation: false
automatic_resume: false
automatic_merge: false
human_or_domain_decision_required: true
```

### Review-learning and source-integrity plane

Coding Waboose review learning extends the existing review owner with bounded external-review normalization, typed lesson contracts, deterministic security/boundedness/schema/workflow/evidence detectors, exact-head scans, and Crucible replay receipts. Source integrity binds review evidence to canonical UTF-8 content, source digests, exact Git head/tree state, registry digests, merge ancestry, and non-vacuous scenarios. It rejects unsafe symlinks, malformed files, exceeded file/byte budgets, stale ancestry, unsigned/tampered registries, and unsupported semantic-completion claims.

Primary owners include `aura_coding_waboose_review_lessons.py`, `aura_coding_waboose_review_learning.py`, `aura_review_lessons_security.py`, `aura_agent_arena_review_learning_bridge.py`, `aura_agent_arena_review_learning_mcp.py`, `.aura/review_lessons/`, and the review-learning schemas/harness/tests.

Detector findings and replay results remain review evidence only. They cannot write source, confirm their own finding, promote a rule, commit, push, create a PR, or merge.

### Atomic GitHub publication plane

The Agent Bridge now has a permanent publication owner that removes the need for temporary source payloads and workflow materializers.

```text
exact repository snapshot + bounded change manifest
  → prepare publication contract
  → create mode: fresh snapshot ref
     or update mode: exact open same-repository PR
  → GraphQL createCommitOnBranch(expectedHeadOid)
  → server-side commit and ref CAS
  → publication/recovery evidence
  → evidence-only merge preparation
  → separately authenticated trusted-human merge
```

`aura_agent_arena_github_bridge.py` owns validation, canonical contracts, transport, compare-and-swap publication, recovery evidence, and merge preparation. `aura_agent_arena_github_mcp.py` exposes `aura_github_prepare_publication`, `aura_github_execute_publication`, and `aura_github_prepare_merge` without accepting bearer tokens as arguments.

Constitutional boundaries:

```yaml
publication_requires_explicit_authorization: true
graphql_compare_and_swap: true
caller_workflow_paths_allowed: false
automatic_branch_delete: false
force_ref_update: false
merge_authority_in_mcp: false
automatic_merge: false
human_review_required: true
```

Ambiguous publication failures return expected/observed ref evidence and do not automatically delete a ref, because GitHub ref deletion lacks an expected-OID compare-and-swap guard.
<!-- AURA_JULY20_ARCHITECTURE_RECONCILIATION:END -->

## 6. Architectural planes

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
- `aura_relational_index.py`;
- `aura_relational_synthesis.py`;
- `aura_relationship_atlas.py`;
- `aura_coding_relationship_compass.py`;
- associated stabilization and manifest modules.

For broad architecture/refactor objectives, the Coding Relationship Compass is the objective-scoped orchestration layer over these owners. It selects a Connectome capability path, grounds exact atomic source and tests, loads or builds a validated Relational Index, extracts a deterministic budget-bounded neighborhood, compiles an `OBJECTIVE_STANDARD` or `OBJECTIVE_DEEP` Atlas, evaluates typed compatibility, and emits a proposal-only Planning Board/Coding Breadboard receipt. Its final C6–C9 layer performs bounded Emergent discovery, compiles validated Change Graph/phase/Act Capsule/Agent IR artifacts, routes local versus structural failures to Surgeon or Council V3, projects append-only bi-temporal relationship experience, and exposes six strict bridge/MCP tools. It is not a new truth owner and cannot authorize provider execution or mutation. Architect uses its bounded packet before legacy filename inference; an admitted Compass route fails closed rather than bypassing hard guards.

Relationship-experience receipts are authenticated, bounded inputs rather than trusted prose. Their shared constructor boundary enforces canonical identity, digest, finite timestamp, exact authority flags, list/item/aggregate byte limits, and pre-sanitized reason text. `PRIVATE_REDACTED` references admit only kind-specific opaque placeholders or lowercase-hex digest tokens; prefixing private source text with `redacted:` is invalid. These invariants run before QDKT/timeline projection and Arena ledger persistence, so no alternate loader can bypass them.

The resolver must search for canonical reusable owners before introducing a new module. CODEMAP vectors, Connectome paths, Atlas assessments, and topology edges help navigation; they are not patch authority.

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

<!-- AURA_FORGE_V1:START -->
#### Aura Forge verified engineering surface

Aura Forge is a product façade over the canonical Coding Arena, Agent Bridge, frozen
Architect plan, Controlled Refactor Session, safe external-LLM slice leasing, staging,
verification, output-vault, and human-review owners.

```text
FRAME → GROUND → PLAN
  → Arena Evidence Contract
  → ACT through bounded Surgeon turns
  → PROVE through canonical verifiers
  → DECIDE through a human review packet
  → DISSOLVE or enter a separately authorized promotion workflow
```

`AURA_FORGE_ARENA_EVIDENCE_CONTRACT_V1` preserves exact repository/CODEMAP identity,
plan-phase identity, Act Capsules, source line ranges, dependencies, tests, route evidence,
allowed files, required gates, model budgets, and non-promotion authority invariants.

Forge cannot commit, push, open a pull request, merge, mutate production, or convert
hotswap readiness into promotion authority.
<!-- AURA_FORGE_V1:END -->

<!-- AURA_GATE_PHASE2:START -->
#### Aura Gate authority envelope

Aura Gate is the Phase 2 governance wrapper around the retained Forge contract and
canonical Arena lease. It does not become a second planner, Forge runtime, event store,
identity provider, egress transport, verifier, or promotion path.

```text
private OIDC boundary
  → offline pinned-RS256 identity verification
  → exact purpose + content-addressed static policy
  → Forge prepare
  → GateAuthorityEnvelope(exact Forge contract ID + digest)
  → append PRE_ACTION event + issue expiring Arena lease
  → reauthorize identity/policy/audit/lease
  → Forge start_prepared(exact retained contract)
  → purpose-limited canonical egress bytes + capsule
  → verifier-backed READY_FOR_HUMAN_REVIEW
  → dissolution, expiry, or explicit revocation
```

Canonical owners are deliberately separated:

- `aura_gate.py` owns Forge-specific policy admission, authority envelopes, and durable
  lease transitions, including one-use actor/policy/request-nonce indexing and outbound
  Gate-release budgets;
- `aura_gate_oidc.py` owns offline OIDC verification and pseudonymous actor references;
- `aura_gate_egress.py` owns exact admitted bytes and content-addressed egress capsules;
- `aura_gate_audit.py` adapts Gate events to the canonical append-only event/payload
  owners and chained authority receipts;
- `aura_gate_comparison.py` owns shadow and one-use-authorized paired-live evidence;
- `aura_gate_adapters.py` owns the Gate-only MCP 2025-06-18 and A2A v1.0 projections;
- `aura_gate_server.py` owns the fixed-route private HTTP/OIDC boundary;
- `aura_forge.py` retains preparation, staging, verification, and human-review ownership.

`VerifiedGateIdentity` is an injected trust-boundary value, not a self-authenticating
credential. The HTTP boundary constructs it only through the pinned verifier. Direct
Python callers must do the same; protocol-body actor, identity, claims, or authorization
fields are never authority. Raw bearer tokens and raw OIDC claim documents cannot enter
Gate audit/SIEM evidence.

The MCP owner is a message-level projection, not a complete authenticated transport. The
cleartext A2A server is restricted to numeric loopback and is not the HTTPS transport
required for an A2A production deployment. Persisted Gate authority does not imply
resumable in-memory Forge sessions after process restart.

The current proof is Forge-specific OIDC/private single-node deployment. SAML/SCIM,
HA/Kubernetes, arbitrary-domain policy, and vendor-certified SIEM connectors remain
separate, review-gated programs. Gate cannot commit, push, open a pull request, merge,
release, activate policy, or promote production state.
<!-- AURA_GATE_PHASE2:END -->

<!-- AURA_CODING_WABOOSE_V1:START -->
#### Coding Waboose

Coding Waboose is the canonical pre-repair review surface over CODEMAP, compiled topology,
exact source slices, deterministic tools, external-agent MCP handoffs, and Forge repair intake.
It has a separate lifecycle:

```text
FRAME → DIFF → SLICE → SCAN → INVESTIGATE
  → CORROBORATE → RANK → DECIDE → REPAIR_HANDOFF → DISSOLVE
```

Aura owns exact changed-file/symbol extraction, callers/callees/shared-resource impact,
source anchors, deterministic findings, evidence status, deduplication, and ranking. A
replaceable coding agent may propose focus directives and semantic findings. Agent-generated
call graphs, confidence, or self-declared confirmation are not authority.

The Coding Waboose cannot edit production files, apply a fix, commit, push, open a pull request,
or merge. Confirmed findings can become bounded Aura Forge repair requests; Forge must still
compile a separate evidence contract, stage the candidate, verify it, and stop for human review.

Primary owners include:

- `aura_coding_waboose.py` — public Coding Waboose owner;
- `aura_coding_waboose_breadboard.py` — proposal-only diagnostic circuit compiler;
- `aura_review_arena.py` — internal reusable scan/corroboration engine;
- `aura_coding_waboose_cli.py`;
- `schemas/aura_coding_waboose_contract.schema.json` and the internal `schemas/aura_review_contract.schema.json`;
- Coding Waboose tools on `aura_agent_arena_persistence_bridge.py` and `aura_agent_arena_mcp.py`;
- `docs/AURA_CODING_WABOOSE.md`.
<!-- AURA_CODING_WABOOSE_V1:END -->

<!-- AURA_SPATIAL_SUBSTRATE_S0_S6:START -->
#### Spatial Arena projection and governed presentation substrate

Aura's Spatial architecture is a representation-independent projection layer over retained domain owners. It does not become a second CODEMAP, Coding Arena, Civic map, Construction state, event store, renderer authority, checkpoint owner, or mutation path.

```text
canonical domain truth
  → bounded privacy-aware domain adapter
  → immutable SpatialSceneSnapshot
  → deterministic device profile and render plan
  → ephemeral presentation session
  → review-only interaction
  → exact render evidence and assessment-only continuity
  → human/domain decision packet
  → client-bound cleanup evidence
  → lease/session dissolution
```

The governed S5 route is finite:

```text
FRAME → GROUND → COMPILE_SCENE → PLAN_RENDER → PRESENT
      → INTERACT → PROVE → DECIDE → DISSOLVE
```

Canonical ownership is split deliberately:

- `aura_spatial_contracts.py` owns immutable frame, asset, entity, link, scene, interaction, device, render-plan, receipt, and dissolution contracts;
- `aura_spatial_coordinate_frames.py` validates rooted frames and deterministic transforms;
- `aura_spatial_asset_registry.py` validates content-addressed manifests without fetching, decoding, training, or rendering;
- `aura_spatial_scene.py` compiles immutable scenes and enforces referential integrity;
- `aura_spatial_projection.py` provides bounded domain projections and reuses retained topology/Coding owners;
- `aura_spatial_render_plan.py` owns deterministic device compilation and renderer negotiation;
- `aura_spatial_session.py` owns ephemeral projection sessions and immutable render/dissolution receipts;
- browser adapters provide bounded accessible, headless, WebGL2, shadow WebGPU, explicit-gesture WebXR, interaction, and telemetry surfaces;
- S4-A importers admit bounded local glTF/GLB and PLY interchange as derived projection assets;
- S4-B Gaussian interchange follows the pinned `KHR_gaussian_splatting` release-candidate profile, retains deterministic point-cloud/accessibility/headless fallbacks, and enforces pre-allocation/resource/disposal ceilings;
- `aura_spatial_arena.py` owns the S5 lifecycle and binds purpose, privacy, domain state, scene, render plan, session, read-only capsule/boundary/lease, evidence, checkpoint, archive, cost, decision, and dissolution identities;
- `aura_spatial_construction.py` is the Construction-only S6 projector over exact `ConstructionProjectState` and a validated Construction runtime packet;
- `aura_spatial_agent_bridge.py`, `aura_agent_arena_persistence_bridge.py`, `aura_agent_arena_mcp.py`, and `aura_spatial_mcp.py` expose typed preparation and bounded post-prepare review tools;
- `aura_arena_persistence_adapters.py` owns payload-minimized, assessment-only Spatial checkpoint projection;
- `.aura/arena_routes/spatial.v1.json` is the finite route grammar.

`FRAME` binds the normalized objective, purpose digest, privacy class, egress policy, actor, and source references. `GROUND` binds one canonical external domain owner and exact state/evidence digests. `COMPILE_SCENE` admits one immutable scene. `PLAN_RENDER` deterministically intersects scene requirements, device capability, preference, and resource ceilings. `PRESENT` creates only an ephemeral session. `INTERACT` remains review-only. `PROVE` records render evidence, Attempt Archive evidence, calculated cost, and a parent-linked assessment-only checkpoint. `DECIDE` compiles a packet for an authorized human or domain owner but cannot apply it. `DISSOLVE` releases the lease/session only after a cleanup receipt is bound to the exact session, scene, and render plan.

Evidence classes remain explicit. Generic Agent/MCP proof defaults to `DERIVED`. Browser evidence may be `MEASURED` only through the exact scene/render-plan/device/fixture-bound telemetry validator. Client-reported renderer cleanup remains `CLIENT_REPORTED`; Aura never upgrades it to independently verified disposal. Allocated renderers report `DISPOSED`; headless/synthetic paths report `NOT_ALLOCATED`. Emergency close never fabricates cleanup and records unobserved/unreleased boundaries honestly.

Spatial privacy classes are `PUBLIC`, `PROJECT`, `RESTRICTED`, and `SENSITIVE`; egress is `LOCAL_ONLY` or `ADMITTED_RENDER_WORKER`. Restricted and sensitive runs are local-only. External render work requires allowlisted workers, pre-admitted capability digests, a network-enabled device profile, and a positive byte budget. The admission baton contains only bounded worker/capability/manifest identities and exact scene/plan/domain/lease digests—never asset URIs, scene payloads, raw domain state, raw sensor data, or person-level data.

The Construction S6 projector verifies the nested Action Capsule, Boundary Contract, Arena Lease, evaluation digest, candidate identities, proposal boundaries, and human-release boundaries before projection. It emits abstract project/scope/proposal state, aggregate counts, uncertainty/evaluation identities, and privacy-compatible local non-survey floor-plan manifests. It excludes event/evidence payloads, actor/claimant/worker/person identity, consent records, raw sensors, survey-authoritative coordinates, and every physical-work/payment/access/equipment/professional/legal/engineering/regulatory authority. Public identifiers are hashed; restricted/sensitive projections are abstract and reject floor-plan geometry.

All scene coordinates, layouts, topology assets, meshes, point clouds, Gaussian manifests, renderer hints, gestures, gaze, anchors, visual selections, device profiles, telemetry, checkpoints, and decision packets retain:

```yaml
patch_authority: exact_source_spans_and_hashes_only
renderer_authority: false
execution_authority: false
automatic_resume: false
automatic_merge: false
```

Production OpenXR deployments, capture/reconstruction/training pipelines, remote asset delivery, unrestricted sensor ingestion, additional S6 domain adapters, and consequential S7 promotion remain separately governed programs.
<!-- AURA_SPATIAL_SUBSTRATE_S0_S6:END -->

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

## 7. Canonical ownership matrix

| Concern | Canonical owner | Projections/compatibility | Must not become a second owner |
|---|---|---|---|
| Repository truth | Current Git tree, exact source/schemas/tests | CODEMAP, topology, summaries | Visual graph, VSA, research, model output |
| Intent route | Intent contracts, semantic LEXC, machine WFST | UI route diagrams, JSpace/ST3GG packets | Worker interpretation |
| Capability truth | Capability Connectome, Genome Resolver, and manifests | Native Cockpit, Affordance Directory | New duplicate registries |
| Planning truth | `aura_planning_board.py` and canonical planning contracts | Coding/Civic shadows, history projector | Arena UI state |
| Event history | Canonical append-only event/sidecar contracts | Planning history, compatibility readers | Mutable summary JSON |
| Authority | Relational authority, leases, consent, human/community decision | Gate dialogue and UI explanations | Planner, model, score, or Observatory |
| Forge-specific gateway authority | `aura_gate.py` over exact Forge contract, OIDC identity, static policy, and canonical Arena lease | MCP/A2A Task/tool projections and private HTTP responses | Protocol body, worker, agent card, SIEM export, or comparison preference |
| Gate identity | `aura_gate_oidc.py` with operator-pinned public JWKS and secret local actor salt | Pseudonymous bounded authority metadata and digests | Raw token/claims document, request body, model output, or mutable session profile |
| Gate egress | `aura_gate_egress.py` exact canonical bytes and capsule | Protocol response/transport projection | Provider call, destination, or worker claim |
| Gate audit history | Canonical append-only event/payload owners through `aura_gate_audit.py` plus chained receipts | Deterministic SIEM JSONL projection | SQLite lease status, log stream, or SIEM index |
| Arena lifecycle | Arena runtime, route, manifest, lease, receipt | Browser/CLI status | Worker process |
| Spatial scene truth | Canonical domain owner plus immutable `SpatialSceneSnapshot` | Renderer, browser, accessibility, Observatory, and decision projections | Visual state, renderer cache, telemetry, or checkpoint |
| Spatial presentation lifecycle | `aura_spatial_arena.py`, route grammar, exact session/render receipts, and read-only lease | Agent Bridge, MCP, CLI, browser adapters | Domain truth, Construction ledger, renderer authority, or automatic resume |
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

## 8. Human Agent, Observatory, Attempt Archive, and Crucible separation

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

## 9. Council–Surgeon engineering architecture

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

## 10. Civic Commons Arena

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

## 11. SCO Construction Arena

The completed E0–E14 Construction architecture is a narrow adapter over canonical Aura owners. It does not create duplicate Planning, governance, Experience, Crucible, persistence, Human Agent, or Observatory systems.

### Construction Human Agent and Observatory

The Construction Human Agent is a purpose-limited projection over canonical project state and an admitted planning capsule. The corresponding Observatory surface is read-only, payload-minimized, and cannot approve, execute, or mutate Construction state.

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

## 12. Financial Arena exact-state architecture

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

## 13. Model Cognome architecture

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

## 14. Temporal persistence architecture

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

## 15. Benchmark and claim architecture

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

The Aura Gate Phase 2 Agent Bridge/Council V3 record reports a scoped proxy of `37,907`
input, `1,852` output, and `39,759` total tokens, with `51,987` (`56.66%`) estimated saved
against its explicit counterfactual. Full Codex-session provider totals were unavailable.
This `DERIVED_COUNTERFACTUAL_WITH_CHAR4_TOKEN_PROXY` record is engineering evidence, not
billing and not a whole-session token total.

## 16. Deployment and presentation surfaces

Aura supports several deployment/presentation layers:

- local CLI/REPL;
- Native Cockpit;
- Coding Arena;
- unified Human Agent Arena;
- four-surface Showcase: Civic, Human Agent, Observatory, Crucible;
- containerized showcase/Render path;
- Hugging Face public demo path;
- MCP Agent Bridge;
- Aura Gate private HTTP/A2A server and Gate-only MCP adapter;
- Hermes/local-model and optional provider workers;
- guided Winnipeg Civic demonstration;
- AR/spatial and broader application-fabric prototypes.

Deployment does not change authority. Public demos use synthetic or explicitly public evidence and must not expose private memory, raw activations, raw Financial/Construction records, credentials, or community-restricted knowledge.

## 17. Compatibility and migration policy

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

## 18. Security, privacy, and cultural governance

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

## 19. Implemented architecture versus roadmap

Implemented repository capabilities are described above as implemented.

Architecture-supported but separately gated product directions include:

- intent-compiled consumer application fabrics;
- sovereign Arena federations and social/public information networks;
- disaster coordination and institutional deployments;
- real owner/contractor/payment/access/sensor Construction connectors;
- Financial indicators, scenarios, connectors, recommendations, and LifeOS presentation;
- production WebXR/OpenXR deployments, capture/reconstruction/training, remote rendering, and additional governed Spatial domain adapters;
- module marketplaces and commercial packaging;
- autonomous production promotion.

These require separate implementation, privacy/security review, governance, measurement, and domain authorization. They must not be inferred from architectural compatibility alone.

AuraOS evidence does not establish consciousness, unrestricted autonomy, universal model superiority, legal certification, court admissibility, or production readiness outside exact measured gates.

## 20. Architecture maintenance protocol

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

<!-- AURA_CONSTRUCTION_G7_G8 -->
## Construction Arena G7–G8 presentation and proof layer

Canonical ownership remains singular:

```text
ConstructionDemoAssetPack
  → build_construction_demo_project_fixture
  → build_construction_demo_runtime_packet
  → project_construction_demo_to_scene
  → negotiate_spatial_render_plan
  → compile_construction_demo_packet
  → ConstructionSceneRenderer
  → Gaussian/graph/overlay recording surface
  → deterministic presentation tour
  → read-only Observatory / human decision packet
  → exact renderer disposal
```

`aura_construction_demo_director.py` owns presentation sequencing only. `ConstructionProjectState`, `ConstructionArenaAdapter`, `ConstructionDemoAssetPack`, the G4 fixture, the G5 projector, and the G6 renderer passes retain their existing truth and lifecycle ownership.

The current recording client is fail-closed: deterministic fallback Gaussian rendering is implemented; browser GLB/SPZ decoding and a real mesh draw pass are not. Mesh/hybrid controls remain disabled, and an admitted real pack is never replaced by fabricated fallback geometry.

## AI-agent harness topology

```text
CODEMAP / exact source identity
  → Architecture Harness doctor and AI-safe handoff
  → Capability Connectome + Relational Index
  → Relationship Atlas + Relational Synthesis
  → Emergent Properties proposals
  → Coding Relationship Compass
  → Coding Waboose diagnostic breadboard
  → Council V3 / Surgeon repair preparation
  → Crucible verification
  → Observatory human evidence review
  → exact-head human-authorized publication
```

These are separate owners with bounded roles. The Architecture Harness reconstructs and supervises the environment; Waboose reviews; Compass compiles impact evidence; Council/Surgeon prepare strategies; Crucible tests; Observatory presents evidence; Agent Bridge/MCP connects replaceable agents. None of them independently author source truth, apply production mutations, approve physical Construction work, publish, or merge.

Generated CODEMAP/topology is navigation evidence and must be regenerated from the final source tree. Exact source spans, hashes, tests, runtime receipts, and human authorization remain authoritative.

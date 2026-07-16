# AuraOS Architecture

> **Canonical compact architecture anchor for humans and AI agents**

**Architecture audit:** July 16, 2026, through merged PR #133 and the governed-learning documentation sync.  
**Previous full architecture anchor:** [`f38fca0/.aura/ARCHITECTURE.md`](https://github.com/dallascourchene-commits/AuraOS/blob/f38fca03304b37b51738db99b3076490a880c31f/.aura/ARCHITECTURE.md).  
**CODEMAP rule:** regenerate with `python aura_codebase_navigator.py` after architecture changes.  
**Topology source:** `compiled_deep_topology`.

## 1. Architectural Identity

AuraOS is a **sovereign, local-first, Arena-based cognitive operating substrate**.

It is not a single language model, conventional chatbot, monolithic autonomous agent, visual wrapper around an LLM, system where semantic similarity authorizes code changes, or system where generated civic scenarios replace human or community decisions.

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
  → governed memory, telemetry, learning evidence, and dissolution receipts
```

Central invariant:

> **Meaning may guide retrieval. Only grounded evidence and authorized governance may grant authority.**

## 2. Architectural Planes

```text
1. HUMAN / COMMUNITY INTENT
2. INTENT COMPILATION AND FST/WFST ROUTING
3. SELF-MODEL, CAPABILITY DISCOVERY, AND GROUNDING
4. ADVISORY COGNITION, COMPRESSION, AND VISUALIZATION
5. ARENAS, WORKBENCHES, AND EPHEMERAL ORGANS
6. EXTERNAL WORKERS AND CONTROLLED EGRESS
7. VERIFICATION, APPROVAL, MEMORY, COST, AND OBSERVABILITY
8. EXPERIENCE, CRUCIBLE, AND PROPOSAL-ONLY LEARNING
9. DOMAIN DEPLOYMENTS: LANGUAGE, CIVIC, RESEARCH, MESH, AR
```

| Plane | Implemented surface | Authority boundary |
|---|---|---|
| Intent and route | Six-slot LEXC, machine FST, guarded WFST, context and live-route capsules | Grammar and route acceptance constrain work; they do not create permission |
| Grounding and self-model | CODEMAP, compiled topology, Topological Context Anchor, Capability Connectome, Genome Resolver, Model Cognome | Exact current spans, hashes, tests, graph digests, and manifests outrank inference |
| Advisory cognition | VSA/HDC, DREAM, QDKT, JSpace, ST3GG, MUSIC, MITOSIS, semantic ranking, visual topology | Discovery and compression only; no patch authority |
| Arenas | Coding, Agent, Human Agent, Liquid Planning, Civic Commons, Experience/Crucible, ephemeral organs | Minimum leases, lifecycle enforcement, verifier gates, human/community authority |
| Model execution | Local models and governed external egress | Models are workers; live calls require admission, authorization, evidence, and approved egress |
| Observability | Usage normalization, cost ledger, pricing snapshots, attribution, policy observations | Unknown cost stays unknown; estimated and provider-reported usage remain separate |
| Learning | Experience V3, Crucible review, replay, Shadow, drift evaluation | Complete verified experiences only; proposals never auto-promote |
| Deployment | Native Cockpit, Coding Workbench, Human Agent Arena, Showcase, civic and language surfaces | Presentation is not authority |

## 3. Truth and Authority Model

### Advisory layers

These may discover, rank, compress, remember, hypothesize, or visualize:

- VSA / HDC resonance;
- DREAM and DREAM-lite ranking;
- QDKT state;
- JSpace workspace state;
- ST3GG compact recall handles;
- MUSIC comparison;
- MITOSIS decomposition;
- semantic similarity;
- visual topology;
- screenshots and summaries;
- emergent-capability hypotheses;
- inferred and ghost edges; and
- external research metadata and untrusted sidecars.

They may not authorize production mutation, civic decisions, cultural-profile activation, restricted-data access, active grammar changes, or learning promotion.

### Authoritative layers

Authority is grounded in:

- repository-relative file paths;
- exact symbols and semantic IDs;
- source line ranges;
- content and signature hashes;
- current CODEMAP and compiled topology facts;
- tests and verifier outputs;
- source snapshots and exact sidecars;
- manifests and boundary contracts;
- capability leases and lifecycle state;
- consent records; and
- human, teacher, speaker, community, legal, or governance approval.

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
visual_topology_patch_authority: false
research_metadata_patch_authority: false
learned_weight_patch_authority: false
crystallization_patch_authority: false
active_grammar_mutation: false
automatic_grammar_promotion: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
```

Unknown, ungrounded, expired, ambiguous, or unauthorized actions fail closed.

## 4. Human Agent, Observatory, Emergent Evidence, and Crucible

Aura uses four connected but non-collapsible surfaces:

```text
OBSERVATORY (explain and bound)
  → HUMAN AGENT ARENA (admit and execute)
  → EXPERIENCE LEDGER (record verified outcome)
  → CRUCIBLE (mine and propose)
```

| Surface | Inputs | Outputs | Forbidden authority |
|---|---|---|---|
| Observatory | intention, six-slot packet, route decision, exact localization, bounded topology/context | review trace and bounded handoff | execution, staging, mutation, permission, learning eligibility |
| Human Agent Arena | human command, exact evidence, selected findings/research, capability and lifecycle state | guarded workflow state, staged/verified work, tool-run records, `ArenaExperience` lineage | bypassing WFST admission or treating visuals/semantic matches as patch authority |
| Emergent Refactor Workspace | imported reports, seed provenance, objective search, bounded public research | content-addressed findings/evidence and reviewable refactor packets | silent evidence dropping, unbounded network work, pre-admission workflow mutation |
| Crucible | complete sanitized `ArenaExperience V3`, verifier evidence, `OutcomeVector`, current grammar digest | TRAIN/VALIDATION/SHADOW evaluation and `CRYSTALLIZATION_PROPOSED` packets | hard-guard changes, source mutation, active grammar promotion, automatic deployment |

Guarded lineage:

```text
ordinary intention
  → Observatory trace
  → bounded Human Agent handoff
  → FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
  → verifier evidence + OutcomeVector
  → ArenaExperience V3
  → Crucible TRAIN / VALIDATION / SHADOW
  → CRYSTALLIZATION_PROPOSED
  → verifier and human review
```

The emergent workspace is a grounding aid inside this lineage, not a parallel authority channel.

- exact seed artifacts are provenance-checked;
- content identities exclude volatile timestamps;
- run and research files are authoritative over recoverable indexes;
- missing requested finding or evidence IDs fail closed;
- network work is bounded;
- untrusted sidecars remain untrusted; and
- special executions are normalized into the Human Agent tool-run registry.

The Observatory-to-learning adapter always begins with:

```yaml
status: AWAITING_VERIFIED_EXPERIENCE
eligible_for_crucible: false
```

Only a subsequent governed, verified experience can cross that boundary. The Crucible may propose only `soft_weight_profile.empirical_uncertainty`; it cannot change hard guards, states, transitions, capabilities, risk classes, verifier requirements, source code, or active grammar manifests.

## 5. Council–Surgeon Cognitive Labor

Aura treats planning quality, orchestration quality, executable code quality, cost evidence, and learning evidence as separate classes.

```text
Selective Council V3
  → architecture, dependencies, interfaces, invariants, sequence, rollback
  → critic lanes admitted from evidence and risk

Sliced Surgeon
  → exact-file implementation
  → focused verification
  → bounded local repair

Escalation
  → interface/dependency/invariant invalidation
  → broad downstream change
  → exhausted local-repair budget
```

Universal critic lanes are scope and tests. Sequence, continuity, rollback, and cost are called when plan structure and risk justify them.

Every executable arm should emit `AURA_REFACTOR_OUTPUT_RECORD_V1`, preserving exact test counts, failures, errors, JUnit digests, API, scope, security, static analysis, maintainability, completeness, working status, failed gates, and final disposition. Aggregate scores never override mandatory gates.

## 6. Benchmark Evidence Hierarchy

| Tier | Evidence | Current examples | Permitted claim |
|---:|---|---|---|
| 1 | Executable gates with retained failures and quality | V3 fixture `3/3 + 3/3 + 2/2`; real refactor `32/32 + 35/35 + 21/21` | Working status and disposition for the measured artifact |
| 2 | Deterministic comparative proxies | Aura slices **89.04%** lower total proxy; V3 **32.83%** lower than Council V2; State Ledger **96.19%** less context at step 7 | Comparative fixture efficiency, not billing |
| 3 | Estimated structural projections | Shared grounding evidence **53.1936%** projected reduction on PR #138 head `15bea1a` | Provisional structural estimate only |
| 4 | Discovery and capacity scans | `708` Python files, `10,815` nodes, `20,764` edges, 15 probes; seven projections remained `NEEDS_GROUNDING` | Candidate discovery only |

Tier 3 and Tier 4 evidence cannot be promoted into Tier 1 claims without governed execution, comparable quality evidence, and verifier review.

### Current measured executable results

- Selective Council V3 used 12 calls instead of 18, reduced total-token proxy by **32.83%**, and retained the same selected plan, executable patch digest, `ACCEPTED` disposition, and code-quality scores as Council V2 on the controlled fixture.
- The controlled V3 patch passed visible `3/3`, hidden `3/3`, and regression `2/2`, with observed quality `100.00` and benchmark quality `97.50`.
- The real AuraOS branch trial passed visible/property `32/32`, review-derived adversarial `35/35`, and focused regression `21/21`, with observed quality `100.00` and benchmark quality `93.50`.

### Current efficiency evidence

- Context localization reduced total-token proxy from `131,655` to `14,431` (**89.04%**) while changing grounded-plan quality by `+0.0057`.
- The compact State Ledger used 234 proxy tokens versus 6,140 for recorded history at step 7 (**96.19% less context**) with state preservation `1.0000` and drift `0.0000` in the synthetic test.
- The proposed shared-grounding structure compares `2,004` repeated-evidence proxy tokens with `938` shared-evidence proxy tokens: `1,066` avoided, **53.1936% projected savings**. This is `ESTIMATED`, not provider billing and not a merged-main implementation claim.

## 7. Arenas and Lifecycle

The Human Agent Arena uses:

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

A route may construct a preview before admission, but persistent workflow evidence is committed only after guarded success. Denied actions leave workflow evidence unchanged.

The Coding Arena and visual projections may orient the operator. The Agent Arena Bridge prepares bounded machine work. The Human Agent Arena coordinates people, Aura, and workers. The Observatory explains. The Experience ledger records verified outcomes. The Crucible proposes learning. No surface absorbs the authority of another.

## 8. External Workers and Controlled Egress

External workers receive the minimum bounded context necessary for an Act Capsule. They cannot expand allowed scope, bypass verification, directly mutate production, or promote Crucible proposals.

Provider routing is governed by local policy and current configuration. Provider identity never changes the authority model.

## 9. Memory, Cost, and Continuity

Aura preserves:

- intent and plan identity;
- exact redacted prompt and response evidence;
- estimated and provider-reported tokens separately;
- provider-reported cost when supplied;
- stages, verifier results, repairs, replans, and rollbacks;
- compact State Ledger snapshots;
- outcome and human-review boundaries;
- ArenaExperience projections; and
- lifecycle and dissolution receipts.

Unknown cost remains unknown. A deterministic char/4 proxy is labeled as a proxy. A structural estimate is labeled `ESTIMATED`. Neither is relabelled as a provider invoice.

## 10. Navigation and Maintenance

Read `.aura/ARCHITECTURE.md` first, then `.aura/CODEMAP.md`, then targeted CODEMAP records, exact source, tests, and focused domain documentation.

After architecture changes:

```bash
python aura_codebase_navigator.py
```

Require current file cards, non-zero indexes, non-zero topology, and `compiled_deep_topology`. Historical reports remain provenance, not current authority.

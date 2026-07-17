# AuraOS User Guide

> Operator guide for the current sovereign, local-first, Arena-based AuraOS architecture

**Audit window:** architecture and merged work reviewed through July 17, 2026, including the preceding three weeks of Planning Board, event history, relational authority, J2/ST3GG/QDKT, Model Cognome, Human Agent, external-worker, Civic Commons, Construction, Financial, persistence, evidence, benchmark, and public-showcase development.

**CODEMAP rule:** regenerate navigation after architecture or source changes. Do not trust historical line numbers when the current tree can be inspected directly.

```bash
python3 aura_codebase_navigator.py
python3 -m aura_codemap_verify --compare-json .aura/CODEMAP.json
```

## 1. Operator mental model

AuraOS is not a chatbot that receives a prompt and acts directly. It is an operating substrate that compiles a human objective into a bounded task.

```text
objective
  → structured intent and lexical address
  → six-slot route
  → finite-state admission
  → capability resolution
  → exact repository or domain grounding
  → bounded Arena and leases
  → deterministic tools and optional workers
  → proposal or staged change
  → verification
  → human/community decision
  → receipts and review-gated learning
```

Remember three rules:

```text
Planning proposes.
Governance authorizes.
Verification proves.
```

Semantic similarity, VSA resonance, topology, ST3GG, JSpace, QDKT, model output, research papers, and generated summaries can assist discovery and explanation. They do not grant patch, policy, civic, financial, Construction, or cultural authority.

## 2. Installation and first validation

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python3 -m pip install -r requirements.txt
python3 aura_codebase_navigator.py
python3 -m aura_agent_arena_cli topology-health
python3 -m aura_agent_arena_cli stabilization-status
python3 -m aura_agent_arena_cli digest
```

Healthy navigation has:

- non-zero file and symbol indexes;
- non-zero topology nodes and edges;
- current repository-relative paths;
- `compiled_deep_topology` as the topology source;
- no stale digest warning for the files you plan to touch.

Keep these outside the repository:

- API keys and tokens;
- private learner or community data;
- restricted cultural/language material;
- bank credentials and raw financial exports;
- private memory and prompts containing secrets;
- real Construction evidence unless an authorized storage policy exists.

## 3. Choose the right interface

| Interface | Use it for | Launch |
|---|---|---|
| **Native Cockpit** | Objective ingestion, capability resolution, topology paths, and bounded handoff preparation | `python3 -m aura_native_cockpit_server` |
| **Agent Arena CLI** | Repository health, localization, prepared coding tasks, staging, verification, cost, and domain commands | `python3 -m aura_agent_arena_cli` |
| **Coding Arena** | Visual code topology, exact source regions, route simulation, and capsule review | `python3 aura_coding_arena_server.py --demo` |
| **Human Agent Arena** | Human/Aura/agent workflows, gate dialogue, attempts, emergent evidence, Construction profile, persistence, and tools | `python3 aura_human_agent_arena_server.py --repo-root . --demo` |
| **Aura Showcase** | Guided four-surface Civic, Human Agent, Observatory, and Crucible demonstration | `python3 aura_showcase_server.py --demo-project winnipeg_pathways` |
| **Agent Arena MCP** | Bounded MCP-compatible external-agent tools | `python3 -m aura_agent_arena_mcp` |
| **Legacy REPL** | Existing `!commands` and compatibility workflows | `python3 aura_node.py` |

The browser surfaces are not authority. A button, chart, ranking, dialogue, or visual node does not approve a consequential action.

## 4. Orient yourself before changing code

Read in this order:

1. `README.md` — present-day system overview;
2. `.aura/ARCHITECTURE.md` — canonical ownership and authority;
3. `.aura/CODEMAP.md` — current compact navigation;
4. the relevant document under `docs/`;
5. exact source/test slices returned by Aura;
6. current verifier and workflow evidence.

Query the current map:

```bash
python3 aura_codebase_navigator.py --query "human agent persistence handoff"
```

Read an exact symbol slice:

```bash
python3 -m aura_agent_arena_cli read-slice \
  --file aura_temporal_persistence.py \
  --symbol TemporalCheckpointRegistry
```

Resolve existing owners before creating a module:

```bash
python3 -m aura_agent_arena_cli resolve-capabilities \
  --objective "Add a review-only domain projection to the Human Agent Arena"
```

Do not start by loading all of `aura_node.py`, opening the entire CODEMAP JSON, grepping the whole repository blindly, or giving an external model unrestricted write access.

## 5. Understand the intent route

Aura can accept ordinary language while retaining a deterministic internal representation.

```text
lexical tags / local address
  → DIR
  → ASP
  → CLASS
  → SUBJ
  → VOICE
  → STEM
  → semantic LEXC route
  → machine WFST state and guard checks
```

The six slots are a software ordering contract. They help Aura state where an action applies, its lifecycle, action class, actor, authority/voice, and operation. They are not a claim that distinct Indigenous language families are interchangeable.

Guard evaluation order matters:

1. verify exact state and route identity;
2. verify capability and policy scope;
3. verify lease, consent, validity, and risk;
4. reject hard blockers;
5. rank remaining admissible options with deterministic or advisory signals;
6. require the declared verifier and human/community gate.

A high semantic or probabilistic score cannot rescue a route that failed a hard guard.

## 6. Run a governed Human Agent workflow

The Human Agent Arena follows:

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

### FRAME

Record the objective, purpose, success criteria, non-goals, risk, privacy, and required authority.

### GROUND

Gather exact files, symbols, spans, hashes, schemas, tests, current state digests, manifests, and relevant constraints. Use topology only to find likely regions.

### PLAN

Prefer existing capabilities. Create proposal-only Planning Board nodes or a Council plan when dependencies, interfaces, sequence, rollback, or cross-domain effects need deliberation.

### ACT

Execute only inside an admitted Arena with the required lease and sandbox policy. External workers receive bounded inputs.

### PROVE

Run exact compilation, tests, schema validation, static checks, replay, invariants, and domain verifiers. Preserve failures.

### DECIDE

A human, teacher, speaker, community, maintainer, professional, or other authorized body decides according to the domain. The workflow records disposition and claim boundaries.

An operation may construct preview context before admission, but active workflow evidence must be committed only after the guarded operation succeeds. A denied action must not alter the active workflow.

## 7. Use the Observatory correctly

Aura Observatory is a glass-box explanation surface. It can display:

- the original objective and normalized intent;
- lexical and six-slot addressing;
- route state and guard decisions;
- localized files, symbols, spans, and hashes;
- topology identifiers and neighboring modules;
- context-compression decisions;
- selected worker route and egress class;
- verification requirements;
- bounded handoff packets.

It cannot:

- create a lease;
- execute a worker;
- stage or apply a patch;
- approve a civic or Construction action;
- expose unrestricted private payloads;
- make an item eligible for learning by itself.

Showcase handoffs:

```text
POST /api/showcase/observatory/handoff/human
POST /api/showcase/observatory/handoff/learning
```

A pre-experience learning handoff must remain:

```yaml
status: AWAITING_VERIFIED_EXPERIENCE
eligible_for_crucible: false
```

## 8. Use the Attempt Archive and gate dialogue

The guided Human Agent surfaces preserve successful, denied, and failed attempts.

Use the Attempt Archive to answer:

- What objective was attempted?
- Which exact evidence was available?
- Which route and capability were requested?
- Which guard denied or admitted the action?
- Which worker/tool ran?
- Which test or verifier failed?
- Was repair local, escalated, abandoned, or accepted?

Do not delete failed attempts merely because a later attempt passed. Failures are evidence for debugging, audit, rollback, and future review. They are not automatically training data.

Gate dialogue may explain a denial and propose what exact evidence is missing. It must not fabricate the missing evidence or bypass the gate.

## 9. Use the Planning Board

The Planning Board is proposal-only intermediate representation.

It supports:

- typed goals, actions, predicates, constraints, effects, and contingencies;
- explicit actor, tool, time, and location variables;
- BC0–BC5 continuity stages;
- bounded backward regression from a goal;
- forward symbolic replay;
- no-progress and cycle detection;
- explanation traces;
- immutable event projection;
- independent history reconstruction.

Use it when a task needs multi-step reasoning, alternatives, continuity, or explicit preconditions/effects. Do not treat a valid plan as permission to execute.

Planning action or event authorization should be bound to:

- exact action/event ID and digest;
- capability and policy scope;
- role and delegation chain;
- quorum where required;
- validity window;
- risk class;
- verifier requirements;
- human/community disposition.

Emergency authority must remain narrow, temporary, reason-bearing, and review-producing.

## 10. Use guarded Coding Arena workflows

A coding workflow should look like this:

```text
objective
  → capability resolution
  → CODEMAP/topology localization
  → exact source/test slice
  → bounded change graph or phase capsule
  → optional external worker session
  → staged patch
  → exact tests and static checks
  → patch evaluator / Judge
  → human maintainer decision
```

### Grounded phase capsules

When a refactor spans multiple phases, compile a shared exact evidence bundle once and reference it from bounded phase capsules. This avoids re-sending the same repository context while preserving independent tests, ownership, and rollback.

Each capsule should state:

- exact objective and phase;
- required inputs and invariant digests;
- allowed files/spans;
- dependencies and interfaces;
- expected outputs;
- tests and verifier requirements;
- authority boundary;
- rollback or abandonment condition.

### Council–Surgeon workflow

Use Selective Council V3 for architecture, dependencies, interfaces, invariants, sequence, rollback, and cost when evidence justifies those critic lanes.

Use the sliced Surgeon for:

- exact-file implementation;
- focused tests;
- local deterministic repair;
- bounded cleanup.

```text
local assertion/test failure → Surgeon repair
interface/dependency/invariant failure → Council replan
material scope expansion → Council replan
repair budget exhausted → stop or escalate
```

### Patch authority

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

A VSA hit, JSpace link, topology edge, model suggestion, or research result can identify a candidate region. It cannot authorize the edit.

## 11. Use external LLM slice sessions

External workers should receive compact, explicit leases rather than the full repository.

A slice session should contain only what the worker needs:

- task objective and non-goals;
- exact source slices and hashes;
- related tests and interfaces;
- state ledger or phase-capsule references;
- permitted files and operations;
- budget and time limits;
- output contract;
- verifier requirements;
- secrets/egress restrictions.

Preserve a session record containing worker identity, model/endpoint evidence, prompt identity, leased context, response/patch identity, usage evidence class, tests, failed gates, disposition, and claim boundaries.

The worker does not receive commit, push, PR, merge, production-write, cultural-profile, civic, Financial, or Construction authority unless a separate explicit governance contract grants the exact narrow action.

## 12. Use Model Cognome routing

Model Cognome records what an endpoint is known to do, under which evidence class and authorization.

Route classes:

```text
ZERO_MODEL | DIRECT | CASCADE | PANEL
```

Operating modes:

```text
LEGACY | SHADOW | PAIRED_LIVE
```

Use them as follows:

- **ZERO_MODEL** — local deterministic workflow is sufficient;
- **DIRECT** — one authorized endpoint is justified;
- **CASCADE** — bounded escalation from cheaper/local to stronger workers;
- **PANEL** — multiple independent workers are justified by risk or uncertainty;
- **LEGACY** — preserve established route and rollback;
- **SHADOW** — compute and compare a proposed route without provider execution;
- **PAIRED_LIVE** — execute the old and proposed route only under explicit live authorization.

A live authorization should bind purpose, graph digest, endpoint, verifier, expiry, budget, nonce/replay policy, and egress class.

Mechanistic evidence rules:

- open-weight evidence must be aggregate-only and shape-checked;
- raw activations/logits should not enter general telemetry or public artifacts;
- gray-box and black-box endpoints cannot receive unsupported mechanistic labels;
- drift and promotion decisions remain review-gated;
- local/quarantined/federated stores must preserve purpose and trust boundaries.

## 13. Use ST3GG, JSpace, QDKT, and trace memory

These systems solve different problems.

### ST3GG

Use ST3GG for compact advisory frames and exact recall handles. Verify that protocol overhead does not exceed the context saved. Do not treat a compact frame as a substitute for exact source or domain evidence.

### JSpace

- J0 carries local task state.
- J1 carries Arena-local continuity.
- J2 carries governed cross-system continuity and provenance.

Use J2 when work moves between distinct systems or sessions and needs exact boundary/authority metadata.

### QDKT

Use canonical QDKT observation events for new writes. Legacy QDKT artifacts may be read through compatibility facades. Compatibility is not evidence that legacy writes should continue.

### Symbolic Trace Memory

Keep raw trace references separate from compact atoms and consolidated canvases. A canvas is an interpretation over preserved trace references, not a replacement for them.

## 14. Use temporal persistence and cross-Arena handoff

Aura continuity has two distinct levels:

1. **State Ledger V3** — compact intra-session execution state;
2. **Temporal checkpoints** — content-addressed inter-session state with parent/fork history.

Verify the registry:

```bash
python3 -m aura_persistence_cli --repo-root . verify-registry
```

List checkpoint metadata without loading payloads:

```bash
python3 -m aura_persistence_cli --repo-root . list --arena-id human_agent_arena
```

Assess a checkpoint:

```bash
python3 -m aura_persistence_cli --repo-root . assess \
  --checkpoint-id CHK-... \
  --repo-head "$(git rev-parse HEAD)" \
  --invariants-json /tmp/current-invariants.json \
  --remaining-context-tokens 7000 \
  --surgeon-context-limit 10000
```

Possible review decisions:

- `DIRECT_RESUME_REVIEW_REQUIRED` — HEAD and invariants match;
- `MITOSIS_REQUIRED` — remaining work exceeds the configured context threshold;
- `RESTORATION_COUNCIL_REQUIRED` — repository state or persisted invariants changed.

Human Agent persistence endpoints:

```text
GET  /api/human-agent/persistence/checkpoints
GET  /api/human-agent/persistence/checkpoints/{checkpoint_id}
POST /api/human-agent/persistence/checkpoint
POST /api/human-agent/persistence/assess
POST /api/human-agent/persistence/restoration-packet
POST /api/human-agent/persistence/handoff
```

Agent Bridge tools:

```text
aura_checkpoint_session
aura_list_checkpoints
aura_restore_checkpoint
aura_fork_checkpoint
aura_handoff_checkpoint
```

A handoff is a payload-free digital baton. It identifies the checkpoint, source/target Arena, payload digest, and required gate. It does not mutate the target. Temporal labels such as `TEMP:STALE` or `TEMP:BRANCH_OFFSET` force refresh and re-verification.

## 15. Run the Emergent Refactor Workspace

The workspace stores and searches Aura's own emergent-property findings without treating them as proven implementations.

It can:

- verify committed seed report sizes and SHA-256 provenance;
- recover authoritative stored evidence when a secondary JSONL index is incomplete;
- search findings by objective and status;
- gather bounded official arXiv and GitHub research;
- keep PDF/README sidecars explicitly untrusted;
- content-address research evidence and refactor packets;
- fail closed when requested findings/evidence are missing;
- attach a packet to the Human Agent workflow only after guarded admission.

Endpoints:

```text
GET  /api/human-agent/emergent/runs
GET  /api/human-agent/emergent/runs/{run_id}
GET  /api/human-agent/emergent/search?q=...
GET  /api/human-agent/emergent/findings/{finding_id}
POST /api/human-agent/emergent/import
POST /api/human-agent/emergent/refactor-packet
POST /api/human-agent/research/search
GET  /api/human-agent/research/evidence
GET  /api/human-agent/research/evidence/{evidence_id}
```

Seed evidence:

```text
Aura_Memory/emergent_results/seed_runs/2026-07-16/
```

Research metadata is an evidence input. It does not become patch evidence until exact local grounding and verification occur.

## 16. Run the Learning Arena / Crucible

Crucible eligibility requires:

1. admitted execution;
2. verifier evidence;
3. an `OutcomeVector`;
4. a complete sanitized `ArenaExperience V3`;
5. correct TRAIN/VALIDATION/SHADOW separation.

The output is:

```text
CRYSTALLIZATION_PROPOSED
```

The current permitted learned surface is narrow:

```text
soft_weight_profile.empirical_uncertainty
```

Crucible cannot alter:

- hard guards or state transitions;
- capabilities or consent;
- risk classes or verifier requirements;
- source code or active grammar;
- Model Cognome production routes;
- civic decisions;
- Financial exact state;
- Construction truth;
- commit, push, PR, or merge state.

A proposed crystallization needs independent verifier and human review.

## 17. Run the Civic Commons showcase

Launch:

```bash
python3 aura_showcase_server.py --demo-project winnipeg_pathways
```

Open:

```text
http://127.0.0.1:8091
```

Container launch:

```bash
docker compose -f docker-compose.showcase.yml up --build
```

The guided journey is:

```text
WELCOME
→ FRAME_OBJECTIVE
→ SELECT_CONTEXT
→ EXPLORE_MAP
→ ADD_COMMUNITY_INPUT
→ DECOMPOSE_WORK
→ COMPARE_SCENARIOS
→ REVIEW_CONSENT
→ RUN_WHAT_IF
→ DESIGN_PILOT
→ REVIEW_PACKET
→ COMPLETE
```

All included Winnipeg records are synthetic demonstration data. The map is a server-filtered aggregate projection. It rejects person-level vulnerability maps for homelessness, addiction, crime, health, child welfare, Indigenous identity, poverty, or immigration status.

Civic outputs are non-binding. No scenario ranking, what-if result, pilot packet, model broker output, or community-memory match can automatically approve funding, law, voting, procurement, surveillance, or service allocation.

## 18. Run the SCO Construction review surface

Launch the deterministic fictional profile:

```bash
python3 aura_human_agent_arena_server.py --repo-root . --demo
```

Open the **Construction** tab. It shows:

- project, state, event-chain, evaluation, and profile identities;
- admissible and blocked candidates;
- hard blockers before model/sensor ranking;
- proposal-only time/cost/idle deltas;
- deterministic option roles;
- the next external human/professional/owner/legal route;
- a stricter read-only Observatory projection;
- an optional review-gated checkpoint;
- a payload-free cross-Arena baton.

Endpoints:

```text
GET  /api/human-agent/construction/status
GET  /api/human-agent/construction/profile
GET  /api/human-agent/construction/observatory
GET  /api/human-agent/construction/candidates/{candidate_id}
POST /api/human-agent/construction/handoff
POST /api/human-agent/construction/checkpoint
```

The checkpoint request must use the exact current HEAD:

```json
{
  "repo_head": "<git rev-parse HEAD>",
  "parent_checkpoint_id": "",
  "branch_name": ""
}
```

Validate the completed E0–E14 implementation:

```bash
python3 -m aura_construction_refactor_completion --repo-root .
```

`ConstructionProjectState` remains the only Construction truth owner. The profile contains no raw project evidence and cannot authorize physical work, payment, access, equipment control, inspection, safety, engineering, law, regulation, source changes, or merge.

## 19. Use the Financial exact-state layer

The first Financial Arena stage is a local exact-state ledger, not an adviser.

Records use:

- `Decimal`, never silent binary float;
- explicit currency, units, and dates;
- immutable identity and deterministic serialization;
- provenance and freshness;
- explicit truth classes;
- digest/replay/tamper verification.

Truth classes include:

```text
USER_RECORDED
IMPORTED_EXACT
DERIVED_ARITHMETIC
ASSUMPTION
UNAVAILABLE
```

Treat missing information as `UNAVAILABLE`. Do not infer account ownership, consent, jurisdiction, exchange rates, future values, or authority. Do not place raw ledger records into general model context, public artifacts, CODEMAP ownership prose, or telemetry.

The exact-state layer does not provide financial, tax, legal, investment, credit, or lending advice. It cannot connect to accounts, handle credentials, initiate payments, place trades, transfer funds, file taxes, or mutate external accounts.

Planning Board indicators, scenarios, recommendations, LifeOS quests, and external connectors are separate future or separately governed stages.

## 20. Use the Ephemeral Organ Runtime

An ephemeral organ is a temporary capability system, not merely an imported function.

A proper organ lifecycle includes:

1. request and objective;
2. capability resolution;
3. manifest and dependency closure;
4. sandbox/runtime selection;
5. leases and boundary contracts;
6. execution;
7. verification;
8. telemetry and cost evidence;
9. dissolution;
10. receipt and optional experience projection.

Arbitrary user-supplied Python requires a real sandbox. When no required isolation exists, fail closed instead of treating an in-process import as safe.

The Capability Genome Resolver should prefer reusable owners and explicit compatibility before proposing a new component.

## 21. Read benchmark and cost evidence correctly

Evidence classes are ordered:

1. executable gates and exact-head tests;
2. deterministic comparative proxies;
3. estimated structural projections;
4. discovery/capacity scans.

| Tier | Example | Correct interpretation |
|---:|---|---|
| 1 | visible/hidden/regression tests and verifier disposition | Working status for the exact evaluated artifact |
| 2 | context localization, Council V2/V3, State Ledger comparison | Controlled relative comparison, not billing |
| 3 | shared-grounding token estimate | Structural projection labeled `ESTIMATED` |
| 4 | topology/emergent scans | Candidate discovery, not implementation proof |

Keep these fields separate:

- provider-reported input/output/cache tokens;
- tokenizer-exact local measurements;
- deterministic token proxies;
- byte counts;
- chars/4 estimates;
- measured/calculated/estimated/unavailable cost;
- exact test and verifier evidence.

Never convert unknown usage into zero. Never present a proxy as an invoice. Do not promote Tier 3 or Tier 4 evidence into Tier 1 without governed execution and comparable quality evidence.

## 22. Testing and documentation maintenance

For a changed module:

1. compile exact Python files;
2. run fatal/static checks appropriate to the module;
3. run focused tests;
4. run relevant canonical-owner regressions;
5. run schema/replay/tamper tests where state is persisted;
6. verify authority flags remain false where required;
7. regenerate CODEMAP/topology;
8. inspect the final diff and claim language.

General commands:

```bash
python3 -m pytest -q
python3 aura_codebase_navigator.py
python3 -m aura_codemap_verify --compare-json .aura/CODEMAP.json
```

For large branches, use focused tests plus the exact subsystem workflow rather than assuming a broad legacy workflow proves the changed surface.

Documentation should state:

- canonical owner;
- implemented behavior;
- data flow;
- authority boundary;
- exact evidence class;
- unresolved work;
- intentional policy deferrals;
- commands and tests that actually exist.

## 23. Troubleshooting

### CODEMAP contains stale paths or zero metadata

Regenerate from the current tree. Verify the exact file card and compiled topology. Do not manually patch generated maps.

### A route is blocked despite a high score

Inspect hard blockers first: state digest, capability, consent, lease, risk, expiry, evidence readiness, conflict, or verifier requirements. Soft ranking cannot override them.

### A denied action changed workflow evidence

Treat it as a governance regression. Build preview context without mutation; commit active workflow evidence only after admission succeeds.

### A refactor packet is empty or partial

Verify every selected finding, research-evidence ID, source slice, hash, test, and dependency. Missing selected evidence must fail closed.

### Research blocks the UI

Confirm bounded end-to-end deadlines, threaded execution, result limits, and sidecar limits. Do not remove the untrusted-text boundary.

### A checkpoint will not resume directly

Compare exact repository HEAD and invariant digests. Stale/branch-offset state belongs in Restoration Council review; oversized work belongs in MITOSIS.

### A generated map push loses a race

Compare the intervening commit. Accept only a verified map-only change or rerun from the new exact head. Never overwrite a concurrent source or documentation change as if it were generated noise.

### A model route has no cost or usage evidence

Keep it `UNAVAILABLE` or the exact lower claim class. Do not invent provider usage or upgrade a calculated/proxy estimate to measured evidence.

### The Civic or Construction UI appears to approve an action

Stop and inspect the surface. These interfaces must remain proposal/review only. Any executable approval affordance is an authority regression.

## 24. Non-negotiable safety and authority rules

```yaml
external_workers_are_tools: true
planning_is_proposal_only: true
observatory_is_review_only: true
crucible_output_is_proposal_only: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
visual_topology_patch_authority: false
automatic_state_restoration: false
automatic_grammar_promotion: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

AuraOS evidence does not establish consciousness, unrestricted autonomy, universal model superiority, legal certification, court admissibility, or production readiness outside the exact measured and reviewed gates.

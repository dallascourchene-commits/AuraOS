# AuraOS User Guide

> Operator guide for the current sovereign, local-first, Arena-based AuraOS architecture

**Audit window:** architecture and work reviewed through July 20, 2026, including Relational Synthesis R2, Gate Phase 2, Spatial S0–S5 and Construction-only S6, typed Coding Waboose review learning, source-integrity/Crucible replay hardening, browser/interchange/Gaussian security, and the atomic Agent Bridge GitHub publication lane merged in PRs #162–#170.

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
| **Aura Forge API** | Frozen-plan verified engineering runs with an exact Arena Evidence Contract and bounded worker sessions | `from aura_forge import AuraForgeRuntime` |
| **Aura Gate** | Forge-specific OIDC identity, static policy, expiring leases, governed egress, MCP/A2A translation, audit, and private serving | `python3 -m aura_gate_server` |
| **Coding Waboose** | Graph-guided diff review, deterministic scans, coding-agent focus, exact-source corroboration, and Forge repair handoff | `python3 aura_coding_waboose_cli.py run --request review_request.json` |
| **Coding Arena** | Visual code topology, exact source regions, route simulation, and capsule review | `python3 aura_coding_arena_server.py --demo` |
| **Human Agent Arena** | Human/Aura/agent workflows, gate dialogue, attempts, emergent evidence, Construction profile, persistence, and tools | `python3 aura_human_agent_arena_server.py --repo-root . --demo` |
| **Aura Showcase** | Guided four-surface Civic, Human Agent, Observatory, and Crucible demonstration | `python3 aura_showcase_server.py --demo-project winnipeg_pathways` |
| **Agent Arena MCP** | Bounded MCP-compatible external-agent tools, including persistent Spatial review operations | `python3 -m aura_agent_arena_mcp` |
| **Spatial CLI** | Validate the Spatial WFST and run a synthetic, private-data-free Construction lifecycle | `python3 aura_spatial_cli.py --repo-root . validate-route` |
| **Agent Bridge GitHub publication** | Prepare and atomically publish bounded file changes with exact-head compare-and-swap; prepare merge evidence without merge authority | `aura_github_prepare_publication → aura_github_execute_publication → aura_github_prepare_merge` |
| **Legacy REPL** | Existing `!commands` and compatibility workflows | `python3 aura_node.py` |

The browser surfaces are not authority. A button, chart, ranking, dialogue, or visual node does not approve a consequential action.

### Review a coding run before repair

Use Coding Waboose when the question is not only "does it compile?" but also
"which typed diagnostic circuit should be energized, and what exact forward and backward
proof path does it require?" Coding Waboose uses the Planning Board/Coding Breadboard when "what exact
callers, callees, schemas, tests, state transitions, authority boundaries, or shared resources
could this change affect?"

```bash
python3 aura_coding_waboose_cli.py run --request review_request.json
```

For Codex, Hermes, or another MCP client, keep the MCP server alive and call:

```text
aura_waboose_prepare
→ aura_waboose_scan
→ aura_waboose_agent_packet
→ aura_waboose_submit_findings
→ aura_waboose_finalize
```

A review finding is not patch authority. Select a generated Forge repair request only after
examining the exact evidence, then let Forge stage and verify the separate repair.

<!-- AURA_JULY20_OPERATOR_UPDATE:START -->
### Run the governed Spatial lifecycle

Validate the Spatial route:

```bash
python3 aura_spatial_cli.py --repo-root . validate-route
```

Run the non-persistent synthetic Construction demonstration:

```bash
python3 aura_spatial_cli.py --repo-root . synthetic-construction-demo
```

The demonstration uses fixture data, writes no persistent demo state, allocates no renderer, and ends with a human-review decision packet plus a dissolution receipt. For real integrations, the operator must provide a canonically issued Construction runtime packet; reconstructing an equivalent dictionary is rejected.

The lifecycle is:

```text
FRAME → GROUND → COMPILE_SCENE → PLAN_RENDER → PRESENT
      → INTERACT → PROVE → DECIDE → DISSOLVE
```

Operator rules:

- admit only canonical `aura://` asset identifiers accepted by the scene registry;
- keep raw sensor payloads, nested telemetry, data URLs, credentials, and person-level data outside proof metrics;
- treat browser renderer and cleanup evidence according to its declared evidence class;
- never interpret a render receipt, checkpoint, interaction, or decision packet as domain mutation authority;
- dissolve the session and release its lease even after failed preparation or presentation.

### Publish GitHub changes atomically

The permanent publication tools are:

```text
aura_github_prepare_publication
→ aura_github_execute_publication
→ review and verification
→ aura_github_prepare_merge
→ separate trusted-human merge action
```

Create mode requires an immutable base snapshot and a branch name that does not exist and has never been used by a historical PR. Update mode requires the exact open, unmerged, same-repository PR number and exact current head SHA. Publication fails closed when the branch moved, the PR does not match, an operation/type/encoding is noncanonical, bounds are exceeded, or any caller-supplied path enters `.github/workflows/`.

Set `AURA_GITHUB_TOKEN` only in the operator environment. Never pass it through MCP arguments. The merge-preparation tool provides evidence but cannot invoke a connector or claim merge authority.

### Use learned review lessons safely

Typed review lessons and Crucible replay help Coding Waboose look for previously observed defect classes, including authority aliases, protected metadata overrides, count-only bounds, unsafe source paths, URI aliases, schema/runtime drift, unwired regressions, and stale evidence claims. Treat detector output as a review lead until exact current source and tests corroborate it. A clean replay is evidence for the exact reviewed head, not a permanent guarantee about future commits.
<!-- AURA_JULY20_OPERATOR_UPDATE:END -->

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

### Aura Forge V1

Use Forge when a coding task needs a stable product-level contract around the existing
Coding Arena workflow.

```python
from aura_forge import AuraForgeRuntime

forge = AuraForgeRuntime(repo_root=".")
opened = forge.start({
    "objective": "Refactor failure routing while preserving public APIs",
    "target_file": "pkg/router.py",
    "target_symbol": "route_failure",
    "acceptance_criteria": ["visible, hidden, and regression tests pass"],
    "risk_map": ["interface drift", "scope expansion"],
    "provider": "external",
    "model": "provider-model",
})
```

Inspect `opened["contract"]` before sending the leased turn to a worker. The contract
includes exact task evidence, allowed files, required gates, budgets, and authority limits.
Submit only the worker's bounded unified diff through `forge.submit(...)`.

A completed run stops at `READY_FOR_HUMAN_REVIEW`. `human_review_packet` may expose
verifier and hotswap-readiness evidence, but it never performs promotion, commit, push,
pull-request creation, merge, or production mutation.

Focused validation:

```bash
python -m py_compile aura_forge.py tests/test_aura_forge.py
python -m pytest -q tests/test_aura_forge.py
```

See `docs/AURA_FORGE.md` for the complete contract and failure boundaries.

### Aura Gate Phase 2

Use Gate when a Forge run must cross an authenticated, purpose-limited enterprise-style
boundary. Gate first calls `AuraForgeRuntime.prepare`, then binds the exact retained contract ID and
digest into a content-addressed authority envelope and canonical Arena lease. `start`
calls only `AuraForgeRuntime.start_prepared` for that frozen contract. It does not prepare a second
plan or expose an ungoverned Forge method.

```text
OIDC verify → policy admit → Forge prepare → Gate lease
  → audit pre-action → exact Forge start → governed egress
  → bounded submit/status/revoke → human review → dissolution
```

Prepare these operator-controlled inputs outside source control:

- an exact policy derived through `GatePolicyManifest.create(...)`;
- OIDC issuer/audience configuration;
- a pinned public RS256 JWKS;
- a secret actor-salt file with at least 32 nontrivial bytes;
- separate writable state, audit, and SIEM-export directories;
- a pre-created writable `Aura_Staging` directory inside the selected worktree.

Required process configuration is:

```text
AURA_GATE_REPO_ROOT
AURA_GATE_POLICY_FILE
AURA_GATE_OIDC_FILE
AURA_GATE_JWKS_FILE
AURA_GATE_ACTOR_SALT_FILE
AURA_GATE_STATE_ROOT
AURA_GATE_AUDIT_ROOT
AURA_GATE_SIEM_ROOT
AURA_GATE_HOST
AURA_GATE_PORT
```

Use `AURA_GATE_POLICY_ID` when a policy file contains multiple manifests. The current
cleartext server accepts numeric loopback addresses only, and the container proof pins
`127.0.0.1`. The server performs no OIDC discovery or remote JWKS fetch.

```bash
python3 -m aura_gate_server
```

For the container proof, provide an immutable
`AURA_GATE_BASE_IMAGE=<image>@sha256:<64-lowercase-hex>`, exact policy ID and port,
CPU/memory ceilings, distinct state/audit/SIEM volume names, a writable staging path, and
all required host paths. The digest-pinned base must already contain Git, pytest, and the
complete Aura runtime/test dependency closure. Ensure UID/GID `65532:65532` can read the
actor-salt bind and write staging, state, audit, and SIEM paths. Then
validate interpolation before building:

```bash
docker compose -f docker-compose.aura-gate.yml config
docker compose -f docker-compose.aura-gate.yml up --build
```

This Compose profile uses `network_mode: host`, fixes the service to `127.0.0.1`, and has
no `ports:` publication. Use Docker Engine on Linux, or Docker Desktop 4.34+ after enabling
the host-networking opt-in. Host networking removes container network-namespace isolation;
retain OS firewall, provider allowlist, DNS, and enterprise egress controls. The read-only
root, dropped capabilities, and Gate egress capsule are not substitutes for those controls.
Do not add a public bind or unreviewed reverse proxy to this cleartext single-node proof.

The anonymous route is only `GET /health`. Authenticated A2A routes require a bearer
token and `A2A-Version: 1.0`; `POST /message:send` also requires
`Content-Type: application/a2a+json` plus explicit
`configuration.returnImmediately=true`. HTTP success wraps the Task as `{"task": ...}`;
task polling and cancellation use `GET /tasks/{id}?historyLength=0` and
`POST /tasks/{id}:cancel`. The Gate-only MCP adapter exposes exactly:

```text
aura_gate_prepare
aura_gate_start
aura_gate_submit
aura_gate_status
aura_gate_revoke
```

The A2A adapter supports `message/send`, `tasks/get`, and `tasks/cancel`; cancellation is
an explicit lease revocation. Identity always comes from the verified transport boundary,
never from MCP arguments or A2A message parts.

The MCP adapter is a message-level projection, not the MCP HTTP authorization profile or
a complete MCP network transport. A host must provide and test connection lifecycle,
OAuth/protected-resource discovery, TLS/Origin controls, and inject only
the verified identity. Likewise, A2A v1.0 requires HTTPS for production; this cleartext
HTTP profile is a loopback-only proof.

`VerifiedGateIdentity` is not self-authenticating when constructed directly in Python.
Only inject instances returned by `OIDCIdentityVerifier` or a separately reviewed trusted
identity boundary. Never deserialize an actor, identity, claims, or authorization object
from request JSON into this type.

Gate audit evidence contains pseudonymous actor and content digests, not raw bearer tokens,
raw OIDC claim documents, worker prompts/responses, or credentials. SIEM export requires
the verified `aura-gate-auditor` role and writes an exclusive, non-overwriting JSONL
projection only within the configured SIEM root. The shipped server has no SIEM HTTP route
or scheduler; invoke the trusted Python API or a separately reviewed offline operator job.

Each actor/policy/request nonce is one-use and indexed durably before lease issuance.
Distinct egress-capsule operations consume the persisted Gate egress-release allowance
used as a provider-call proxy; that counter limits Gate releases, not retries made by an
external network client. Reported token usage is validated when present. Lease/audit
evidence survives restart, but every nonterminal Forge run is process-local; drain before
restart or status will revoke it when Forge state is unavailable.

Paired-live comparisons are a trusted in-process proof, not currently Gate policy/OIDC/
audit/server operations. They verify observable provider/start counter deltas after each opaque
arm returns. Counter mismatch invalidates the evidence, but only a separately enforced
provider broker or network policy can prevent extra calls inside an injected executor.

Focused validation:

```bash
python3 -m pytest -q \
  tests/test_aura_forge.py \
  tests/test_aura_gate.py \
  tests/test_aura_gate_oidc.py \
  tests/test_aura_gate_egress.py \
  tests/test_aura_gate_audit.py \
  tests/test_aura_gate_comparison.py \
  tests/test_aura_gate_adapters.py \
  tests/test_aura_gate_server.py \
  tests/test_aura_gate_deployment.py \
  tests/test_aura_gate_contract_artifacts.py
```

Before merging a Gate change, regenerate CODEMAP from tracked repository content, verify
compiled deep topology, run the focused contracts and repository CI, and inspect the PR
with a code-review service. Address every valid actionable review thread, rerun the affected
contracts after the final commit, and merge only when the authority envelope, documentation,
generated navigation, and release checks describe the same artifact.

The proof is Forge-specific OIDC/private single-node deployment. It does not claim
SAML/SCIM, HA/Kubernetes, arbitrary-domain policy, vendor-certified SIEM integration, or
automatic commit, push, PR, merge, release, or promotion. See `docs/AURA_GATE.md` for the
authority flow, deployment contract, standards links, schema/example, benchmark evidence,
and exact limitations.

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

### Compile a Coding Relationship Compass packet

Use the Compass when an architecture or refactor objective spans several Aura systems and does not yet name an exact source target:

```python
from aura_coding_relationship_compass import compile_coding_relationship_compass

packet = compile_coding_relationship_compass(
    "combine Connectome, Relational Synthesis, and Atlas to code better",
    repo_root=".",
)
```

The packet binds Connectome capability routing, exact atomic source/test grounding, one JIT Relational Synthesis capsule, and a bounded MINIMAL Atlas projection. Inspect `recommended_targets`, `required_tests`, `relationships_to_preserve`, `missing_roles`, `required_adapters`, and `prohibitions`. The packet is proposal-only and cannot authorize a patch. Architect uses this route before filename fallback for matching broad objectives.

See `docs/AURA_CODING_RELATIONSHIP_COMPASS.md`.

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


## 19. Run the governed Spatial Arena and Construction projection

Use the Spatial Arena when a canonical domain owner needs a bounded visual or spatial projection without transferring truth or authority into the renderer. The Construction adapter is the implemented S6 domain slice. It accepts an exact `ConstructionProjectState` and validated Construction runtime packet; untyped JSON cannot prepare a Construction projection.

Validate the finite route first:

```bash
python aura_spatial_cli.py --repo-root . validate-route
```

Run the synthetic demonstration:

```bash
python aura_spatial_cli.py --repo-root . synthetic-construction-demo
```

The demo uses a temporary state root, synthetic fixtures, no private data, no production connector, and no persistent demonstration state. Its output includes exact scene/render-plan/proof/checkpoint/decision/dissolution identities and keeps physical work, payment, access control, and automatic merge false.

The lifecycle is exact:

```text
FRAME
→ GROUND
→ COMPILE_SCENE
→ PLAN_RENDER
→ PRESENT
→ INTERACT
→ PROVE
→ DECIDE
→ DISSOLVE
```

Operator rules:

- `FRAME` binds objective, actor reference, privacy class, egress policy, and purpose digest.
- `GROUND` binds one canonical domain owner and exact state/evidence digests.
- `COMPILE_SCENE` admits one immutable, referentially valid scene.
- `PLAN_RENDER` deterministically intersects the scene, device profile, preferred renderers, and budgets.
- `PRESENT` allocates only the bounded ephemeral projection session.
- `INTERACT` compiles review-only selection/navigation intent; it cannot mutate domain state.
- `PROVE` records render evidence, Attempt Archive evidence, and an assessment-only checkpoint. Generic agent/MCP proof is `DERIVED`; measured browser evidence must pass the exact telemetry validator.
- `DECIDE` creates a human/domain packet only. It does not apply a decision.
- `DISSOLVE` requires a cleanup receipt bound to the exact session, scene, and render plan. Allocated renderers report `DISPOSED`; headless/synthetic paths report `NOT_ALLOCATED`.

Privacy classes are `PUBLIC`, `PROJECT`, `RESTRICTED`, and `SENSITIVE`. Restricted and sensitive runs are local-only. Public Construction projections hash project, scope, and candidate identifiers. Restricted/sensitive projections reject floor-plan geometry. Project-level floor plans must be local or Aura-addressed, privacy-compatible, explicitly `survey_authority=false`, and explicitly `person_level_data_included=false`.

Python-typed preparation is available through `aura_spatial_prepare_construction`. JSON MCP intentionally exposes only post-preparation tools:

```text
aura_spatial_status
aura_spatial_interact
aura_spatial_prove
aura_spatial_decide
aura_spatial_observatory
aura_spatial_restore_assessment
aura_spatial_dissolve
```

Restore is assessment-only and never resumes automatically. Emergency close does not claim renderer cleanup; absent client evidence remains unobserved and unreleased. No Spatial packet can authorize Construction work, payment, access, equipment, inspection, safety, engineering, law, regulation, survey truth, source mutation, commit, push, pull request, or merge.

See `docs/AURA_SPATIAL_S5_S6_CONSTRUCTION.md` for the canonical ownership and evidence contract.

## 20. Use the Financial exact-state layer

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

## 21. Use the Ephemeral Organ Runtime

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

## 22. Read benchmark and cost evidence correctly

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

The Aura Gate Phase 2 record is scoped to instrumented Agent Bridge retrieval and
Selective Council V3 planning: `37,907` input, `1,852` output, and `39,759` total token
proxy, with `51,987` (`56.66%`) estimated saved against its documented counterfactual.
Full Codex-session provider totals were unavailable. Treat this as
`DERIVED_COUNTERFACTUAL_WITH_CHAR4_TOKEN_PROXY`, not billing or a whole-session total.

## 23. Testing and documentation maintenance

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

## 24. Troubleshooting

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

## 25. Non-negotiable safety and authority rules

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

# AuraOS

A sovereign, local-first, Arena-based cognitive operating substrate that compiles human intent into grounded, governed, temporary capability systems.

**AuraOS is not an LLM.** Aura helps humans and external AI workers understand large systems, select the smallest useful context, assemble bounded tools, verify results, preserve plans and evidence, and keep consequential authority with people or communities.

Aura began as a locally controlled tutor for learning and preserving Anishinaabemowin without surrendering language data to large external platforms. That origin shaped the wider architecture: local control, data minimization, inspectable memory, provenance, purpose-limited egress, revocable capability leases, and governance above model convenience.

The complete pre-benchmark architecture README is preserved at [`docs/README_PRE_ARCHITECT_BENCHMARK.md`](docs/README_PRE_ARCHITECT_BENCHMARK.md).

## Contents

- [What Aura Does](#what-aura-does)
- [Architect Benchmark Prompt](#architect-benchmark-prompt)
- [Planning Benchmarks](#planning-benchmarks)
- [Executable Refactor Code Quality](#executable-refactor-code-quality)
- [Council–Surgeon Hybrid Benchmark](#councilsurgeon-hybrid-benchmark)
- [Persistent Refactor History](#persistent-refactor-history)
- [External LLM Slice Sessions](#external-llm-slice-sessions)
- [Architecture](#architecture)
- [Benchmark Refactor Skeleton](#benchmark-refactor-skeleton)
- [Truth and Safety](#truth-and-safety)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Status and Licensing](#status-and-licensing)

## What Aura Does

Instead of giving an AI agent a giant prompt and an entire repository, Aura:

1. parses the objective;
2. compiles a structured intent packet;
3. validates the route through finite-state constraints;
4. discovers existing capabilities;
5. localizes exact files, symbols, tests, evidence, and dependencies;
6. opens a bounded Arena;
7. leases only required capabilities and context;
8. stages proposed changes;
9. runs tests, Shadow checks, and verifiers;
10. returns bounded repair evidence when a gate fails;
11. escalates graph-level failures without escalating every local test failure;
12. requires human approval for consequential promotion;
13. records prompts, outputs, tokens, state, verification, repairs, costs, and lifecycle receipts.

External models such as Hermes, Codex, OpenAI, Anthropic, Gemini, Fireworks-backed workers, or local models are **workers inside Aura's governed environment**. They are not Aura's architecture, memory, verifier, or authority.

## Architect Benchmark Prompt

The benchmark objective was recorded exactly:

> Scan the AuraOS repository and produce a grounded, staged refactor skeleton that consolidates memory, skill, capability, and agentic functions to improve the Human Agent Arena. Reuse existing Aura architecture, preserve compatibility through explicit adapters, retain plans and verifier evidence, and require human approval before mutation or promotion.

The shared planning instruction was also recorded exactly:

> Return JSON only. Produce a bounded Aura Architect refactor plan with fields: architecture_decision, target_file, target_symbol, act_tasks, acceptance_criteria, rollback_conditions, risk_map, constraints. Each act task must include task_id, objective, target_file, target_symbol, related_files, allowed_scope, acceptance, expected_output=UNIFIED_DIFF, and size. Use only repository facts present in the context. Prefer existing modules and explicit adapters over a new giant abstraction. The plan must persist in the Human Agent Arena, preserve verifier evidence, stage all changes, and require human approval before mutation or promotion.

`AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V2` emitted a prompt manifest containing **20 exact prompt entries**: the broad-context prompt, the single sliced prompt, two planner prompts, fifteen Shadow prompts, and one Judge prompt. Each entry includes byte size, digest, estimated input/output tokens, and provider-reported token fields when available.

<!-- AURA_ARCHITECT_PLANNING_BENCHMARK:START -->
## Planning Benchmarks

**Status:** reproducible fixture-based planning benchmark; no production mutation.  
**Measured code head:** `002ece8a22c0982b883efb54e381ef9f2329e034`.  
**Tokens:** deterministic char/4 proxies; normalized cost is comparative, not a provider invoice.

| Arm | Calls | Input token proxy | Output token proxy | Total token proxy | Grounded-plan quality | Normalized cost* |
|---|---:|---:|---:|---:|---:|---:|
| Broad-context single planner | 1 | 130,486 | 1,169 | 131,655 | 0.9550 | $0.133993 |
| **Aura-slice single planner** | **1** | **12,764** | **1,667** | **14,431** | **0.9607** | **$0.017765** |
| Length-aware Architect Council V2 | 18 | 163,936 | 4,633 | 168,569 | **0.9625** | $0.177835 |

\*Normalized cost uses a declared $1/M input and $3/M output proxy rate card.

### Current measured findings

- Aura slices reduced input-token proxy by **90.22%** and total-token proxy by **89.04%** versus broad context.
- The sliced plan changed grounded-plan quality by **+0.0057**.
- Council total-token proxy was **28.04% higher** than broad context.
- The Council changed grounded-plan quality by **+0.0075**.
- Selected plan profile: **LONG**, 8 tasks, 17 distinct files.
- Governance contract: **all submitted plan-level governance fields preserved**.
- Call accounting: **18 attempted, 18 recorded, 0 failed**.
- Prompt manifest: **20 exact entries**.

### Council role accounting

| Role | Calls | Estimated input | Estimated output |
|---|---:|---:|---:|
| Planner | 1 | 399 | 2,011 |
| Planner Alt | 1 | 400 | 1,546 |
| Shadow | 15 | 135,582 | 1,001 |
| Judge | 1 | 27,555 | 75 |

### Fixture and claim boundary

The long-plan critic lanes use explicit deterministic fixture aliases (continuity→tests, rollback→cost, sequence→scope). These are reproducible fixture invocations, not independent live-provider responses. The benchmark supports context-selection and controlled planning comparisons for this measured head; it does not establish general model superiority, provider-billed savings, consciousness, or production readiness.
<!-- AURA_ARCHITECT_PLANNING_BENCHMARK:END -->

<!-- AURA_REFACTOR_CODE_QUALITY:START -->
## Executable Refactor Code Quality

Planning quality and executable code quality are recorded separately. The earlier planning and synthetic hybrid arms remain `CODE_QUALITY_UNAVAILABLE` because they did not independently produce and evaluate real patches. The executable fixture applies each method's unified diff in an isolated workspace and records every measured result—even when an acceptance gate fails.

| Method | Calls | Total token proxy | Visible | Hidden | Regression | API | Scope | Security | Working status | Disposition | Observed | Benchmark |
|---|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---:|
| Broad-context implementer | 1 | 131,654 | 3/3 | 1/3 | 2/2 | PASS | PASS | PASS | `PARTIALLY_WORKING` | `PARTIAL` | 80.34 | 78.33 |
| Aura-slice Surgeon | 1 | 14,868 | 3/3 | 2/3 | 2/2 | PASS | PASS | PASS | `PARTIALLY_WORKING` | `PARTIAL` | 88.89 | 86.67 |
| Council V2 + Surgeon | 18 | 158,545 | 3/3 | 3/3 | 2/2 | PASS | PASS | PASS | `WORKING` | `ACCEPTED` | 100.00 | 97.50 |
| **Selective Council V3 + Surgeon** | **12** | **106,494** | **3/3** | **3/3** | **2/2** | **PASS** | **PASS** | **PASS** | **`WORKING`** | **`ACCEPTED`** | **100.00** | **97.50** |

Performance and portability were not measured, so measurement completeness was 97.5%. The broad and sliced methods retain their passing compilation, visible tests, regression tests, API, scope, security, and maintainability evidence; they are `PARTIAL` because held-out behavior failed.

### Selective Council V3

Compared with Council V2 on the same frozen role fixture, V3 produced:

- **33.33% fewer model calls** — 12 instead of 18;
- **40.00% fewer critic reports** — 9 instead of 15;
- **33.58% lower input-token proxy**;
- **32.83% lower total-token proxy**;
- **0.0000 planning-quality delta**;
- the same substantive selected plan;
- the same executable patch digest;
- the same `ACCEPTED` disposition and code-quality scores.

This is positive evidence that selective Council calling is better on this controlled fixture. It is not yet a general claim across independent models or production AuraOS refactors.

Every executable arm emits `AURA_REFACTOR_OUTPUT_RECORD_V1`, validated by `schemas/aura_refactor_output_record.schema.json`. Estimated and provider-reported input/output tokens are stored separately. The record preserves exact test counts, failing-test IDs, JUnit digests, API, scope, security, static-analysis, maintainability, completeness, working status, failed gates, and final disposition.

Aura uses ISO/IEC 25010:2023, ISO/IEC 5055:2021, NIST SSDF 1.1, OWASP SAMM, and SWE-bench-style isolated evaluation as reference frameworks. This is not certification or an official benchmark submission.

Detailed evidence: [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md).  
Standard protocol: [`docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`](docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md).
<!-- AURA_REAL_REFACTOR_TRIAL:START -->
### Latest real AuraOS refactor trial

**Measured code head:** `002ece8a22c0982b883efb54e381ef9f2329e034`.  
**Selected plan:** `PLAN-D-SELECTIVE-COUNCIL-V3-SURGEON`; expected selection match: **True**.  
**Working status:** `WORKING`; disposition: `ACCEPTED`.

| Gate family | Passed | Total | Failures | Errors |
|---|---:|---:|---:|---:|
| Visible/property | 32 | 32 | 0 | 0 |
| Review-derived adversarial | 35 | 35 | 0 | 0 |
| Focused regression | 21 | 21 | 0 | 0 |

- Observed quality: **100.00**.
- Benchmark quality: **93.50**.
- Measurement completeness: **93.5%**.
- Patch digest: `0c0b1ad98678e0c33b2e66775a625832`.
- Required gates: compile=PASS, api_compatibility=PASS, security=PASS, static_analysis=PASS, container_build=PASS, selected_plan_bound_to_arena=PASS, local_output_vault=PASS, record_redaction=PASS.

This trial is a real branch refactor with held-out and review-derived tests, but the planning arms are frozen assisted artifacts rather than blinded independent-provider generations. Performance and calibrated maintainability remain unmeasured.
<!-- AURA_REAL_REFACTOR_TRIAL:END -->
<!-- AURA_REFACTOR_CODE_QUALITY:END -->

## Council–Surgeon Hybrid Benchmark

The second benchmark tests the proposed division of cognitive labor:

| Vector | Single sliced planner — “The Surgeon” | Multi-agent Council — “The Board” |
|---|---|---|
| Optimal scope | Local implementation, single-module refactoring, pure code synthesis | Architecture, cross-domain dependencies, trade-offs, graph repair |
| Context | Hyper-narrow slices plus compact State Ledger | System indexes, dependency trees, invariants, plan history |
| Output | Compile-ready bounded patch capsule | Execution sequence, interfaces, invariants, rollback conditions |
| Failure mode | Tunnel vision and missed global effects | Consensus drift, boilerplate, token tax, latency |

The operating policy is:

```text
Council once → long execution graph
Surgeon → each bounded Act Capsule
local test failure → Surgeon local repair
interface/dependency/invariant failure → Council replan → Surgeon resumes
```

### Multi-step execution scaling

| Steps | Turns | Estimated input | Estimated output | Provider-reported input* | Provider-reported output* | Estimated tokens per completed step |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 602 | 51 | 452 | 51 | 653.0 |
| 4 | 5 | 3,287 | 255 | 2,513 | 255 | 885.5 |
| 8 | 9 | 5,984 | 459 | 4,611 | 459 | 805.4 |
| 10 | 11 | 7,405 | 562 | 5,730 | 562 | 796.7 |

\*These are deterministic fixture-reported values, not provider billing records.

The 4-, 8-, and 10-step cases include one forced local repair. All cases reached `READY_FOR_HUMAN_REVIEW` without production mutation.

### State preservation and context drift

Aura passes a lightweight State Ledger rather than replaying the full historical conversation. The ledger contains plan identity, completed/current tasks, dependency map, invariants, latest stage/verification digests, repair attempts, replan count, and execution status.

For the 10-step local-repair run:

| Point | State Ledger proxy | Full-history proxy | History avoided | Ledger/history ratio | State preservation | Context drift |
|---|---:|---:|---:|---:|---:|---:|
| Step 3 | 227 | 1,670 | 1,443 | 13.59% | 1.0000 | 0.0000 |
| Step 7 | 234 | 6,140 | 5,906 | 3.81% | 1.0000 | 0.0000 |

By step 7, the compact ledger used approximately **96.19% fewer context tokens than replaying recorded history**, while deterministic fact matching found no state loss in this synthetic test.

The graph-replan case also retained a **1.0000 minimum state-preservation score** and **0.0000 maximum drift**; its step-7 ledger was 237 tokens versus 6,032 tokens of history.

### Token amortization

Council V2's one-time planning cost was 158,545 total token proxy.

| 10-step scenario | Initial Council | Surgeon execution | Council replan | Hybrid total | Council planning amortized per step | Avoided Council-every-step tax* |
|---|---:|---:|---:|---:|---:|---:|
| Local failure repaired by Surgeon | 158,545 | 8,147 | 0 | 166,692 | 15,854.5 | 1,426,905 — 90.00% |
| Graph failure escalated to Council | 158,545 | 8,115 | 2,039 | 168,699 | 15,854.5 | 1,424,866 — 89.87% |

\*“Council every step” is a clearly labeled extrapolation: 158,545 planning tokens × 10 steps. It is not a measured provider run.

This confirms the **accounting mechanics** of the hybrid hypothesis: one strategic Council can be amortized across many bounded implementation steps, and a graph replan can remain much smaller than rerunning the entire initial Council. It does **not yet prove** that the Council improves real multi-step patch quality; that requires provider-backed, blinded, repository-mutating-in-temporary-worktree trials.

### Rollback recovery

Two step-4 failures were injected:

- **Local assertion failure:** routed `SURGEON_LOCAL_REPAIR`; one repair turn; no Council call; completed all 10 steps.
- **Interface/dependency/invariant failure:** routed `ESCALATE_TO_COUNCIL_REPLAN`; no local repair; one bounded replan of 2,039 token proxy; Surgeon resumed and completed all 10 steps.

The router also escalates after the local-repair budget is exhausted, even when the initial failure appeared local.

## Persistent Refactor History

Every recorded refactor can now preserve:

- objective and plan phase hash;
- exact redacted prompt and response evidence in content-addressed files;
- prompt and response digests;
- estimated input and output tokens;
- provider-reported input/output tokens and cost when supplied;
- Act Capsule, stage, verifier, repair, and Council-replan events;
- State Ledger snapshots and drift measurements;
- final outcome and human-review boundary;
- learning notes and ArenaExperience V3 projection.

The compact append-only stream is stored at:

```text
Aura_Memory/refactor_chronicle.jsonl
```

Redacted content evidence is stored separately under:

```text
Aura_Memory/refactor_evidence/
```

Benchmark runs are indexed in:

```text
Aura_Memory/benchmarks/benchmark_registry.jsonl
```

Benchmark workflows use artifact-local registries so each evidence package is independently replayable. Full histories are retained for human recall and learning, while future model turns receive the compact State Ledger rather than the entire conversation.

## External LLM Slice Sessions

Aura exposes a provider-neutral mechanism through which an external LLM can work inside the Agent Arena without downloading the repository.

```bash
python aura_agent_arena_mcp_external_llm.py
```

The additive MCP entrypoint exposes the original Agent Arena tools plus:

| Tool | Purpose |
|---|---|
| `aura_llm_session_open` | Prepare an Arena and return the first leased turn |
| `aura_llm_session_next` | Return the pending turn |
| `aura_llm_session_submit` | Stage and verify a response, then return completion, local repair, or replan requirement |
| `aura_llm_session_status` | Return safe public state, token totals, and history summary |
| `aura_llm_session_export` | Export review evidence inside Aura's staging boundary |

```text
objective
→ Aura prepares Arena state and cognitive-labor route
→ one Act Capsule plus State Ledger is leased
→ external model returns one bounded diff
→ Aura stages and verifies
→ pass: next capsule or READY_FOR_HUMAN_REVIEW
→ local failure: bounded Surgeon repair
→ graph/invariant failure: Council replan requirement
```

A turn contains only the objective, role, gate, Act Capsule, exact source/test slices, compact State Ledger, allowed files, do-not-touch files, failure evidence, output contract, and token budgets. No repository archive is included.

`run_live_architect_with_external_callback()` lets Aura use external providers for planner, alternate-planner, Shadow, Judge, and worker roles without importing provider-specific SDKs. Aura retains grounding, verification, rollback, ledger, and human-review authority.

Session exports are confined to:

```text
Aura_Staging/external_llm_sessions/
```

Absolute paths, parent traversal, symlink escapes, and resolved-path escapes are rejected.

Key files:

- `aura_external_llm_session.py`
- `aura_external_llm_session_recorded.py`
- `aura_external_llm_session_persistent.py`
- `aura_external_llm_session_safe.py`
- `aura_refactor_state_ledger.py`
- `aura_refactor_chronicle.py`
- `aura_refactor_chronicle_recorded.py`
- `aura_cognitive_labor_router.py`
- `aura_benchmark_registry.py`
- `aura_agent_arena_mcp_external_llm.py`

## Architecture

```text
HUMAN / COMMUNITY OBJECTIVE
→ intent packet and machine-FST route
→ CODEMAP, topology, manifests, affordances, capability lanes
→ Council for systemic planning when justified
→ sliced Surgeon for bounded execution
→ State Ledger for continuity without conversation replay
→ stage, test, verify, repair, replan, or rollback
→ exact evidence and human/community approval
→ refactor chronicle, benchmark registry, experience, cost, and lifecycle records
```

Implemented surfaces include semantic LEXC routing, CODEMAP and deep topology, Capability Connectome and Genome Resolver, Coding Arena, Agent Arena Bridge, Human Agent Arena, Architect Fusion Loop, Planning Board projections, external-LLM slice sessions, Refactor Arena staging, Arena Experience and ledgers, Crucible proposal paths, Ephemeral Organ Runtime, empirical observability, Civic Commons prototypes, and Anishinaabemowin tutoring and governance.

Advisory systems may rank, recall, compress, and plan. They never replace exact source spans, hashes, tests, verifier evidence, and human approval.

## Benchmark Refactor Skeleton

The Council-selected skeleton contains eight bounded Act Capsules:

1. persistent Human Agent plan workspace;
2. capability-lane, affordance, and SkillWeaver consolidation;
3. Architect-to-Planning-Board projection;
4. governed Architect experience capture;
5. canonical Agent Arena MCP slice sessions;
6. explicit SkillWeaver adapter input;
7. Human Agent plan/revision visualization;
8. Experience-ledger and Crucible handoff.

```yaml
next_gate: HUMAN_REVIEW_BEFORE_REFACTOR
production_mutation: false
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

Council V2 preserves the governance fields lost by V1. Before product integration, its normalization and length-aware critic routing must be folded into the canonical Live Architect path, the scope classifier must distinguish repository evidence from repository-wide authority, and focused tests must be mapped for the Arena Experience target.

## Truth and Safety

Advisory-only evidence includes model suggestions, VSA/HDC similarity, DREAM scores, QDKT observations, JSpace routes, ST3GG pointers, screenshots, summaries, and heuristic benchmark scores.

Consequential promotion requires exact source spans and hashes, valid leases, staged diff boundaries, tests, verifier evidence, topology-delta evidence, rollback information, and digest-bound human approval.

The external-LLM adapter prohibits repository download through a turn, direct production mutation, automatic commit/push/merge/promotion, gate bypass, unrestricted export paths, and model or VSA output becoming patch authority.

## Reproduce

```bash
python aura_codebase_navigator.py
python aura_architect_consolidation_benchmark_v2.py prepare --repo-root . --output-dir benchmark-output
python benchmarks/architect_consolidation/generate_gpt56_pilot_fixture.py --output benchmark-output/responses.gpt-5.6-thinking.json
python aura_architect_consolidation_benchmark_v2.py score --repo-root . --output-dir benchmark-output --responses benchmark-output/responses.gpt-5.6-thinking.json --input-rate 1.0 --output-rate 3.0
python aura_architect_benchmark_report.py --report benchmark-output/architect_consolidation_benchmark.json --responses benchmark-output/responses.gpt-5.6-thinking.json --skeleton benchmark-output/architect_consolidation_skeleton.json
python aura_multistep_refactor_benchmark.py --repo-root . --output-dir benchmark-output/multistep --lengths 1,4,8,10
python aura_hybrid_refactor_benchmark.py --repo-root . --output-dir benchmark-output/hybrid --planning-report benchmark-output/architect_consolidation_benchmark.json
```

## Quick Start

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python aura_codebase_navigator.py
python aura_agent_arena_mcp_external_llm.py --list-tools
python -m pytest -q tests/test_aura_external_llm_session.py tests/test_aura_refactor_chronicle_and_length.py
```

## Documentation

- [`docs/README_PRE_ARCHITECT_BENCHMARK.md`](docs/README_PRE_ARCHITECT_BENCHMARK.md) — preserved complete architecture README
- [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) — canonical architecture and invariants
- [`.aura/CODEMAP.md`](.aura/CODEMAP.md) and [`.aura/CODEMAP.json`](.aura/CODEMAP.json) — human and machine code maps
- [`USER_GUIDE.md`](USER_GUIDE.md) — operator and REPL reference
- [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md) — planning benchmark evidence
- [`docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md`](docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md) — external-model protocol
- [`docs/AURA_AGENT_ARENA_BRIDGE.md`](docs/AURA_AGENT_ARENA_BRIDGE.md) — Agent Arena
- [`docs/AURA_HUMAN_AGENT_ARENA.md`](docs/AURA_HUMAN_AGENT_ARENA.md) — Human Agent Arena
- [`docs/AURA_EMPIRICAL_COST_OBSERVATORY.md`](docs/AURA_EMPIRICAL_COST_OBSERVATORY.md) — empirical measurement
- [`.aura/SECURITY.md`](.aura/SECURITY.md) — security constraints

## Status and Licensing

AuraOS is active research and development software. Current evidence supports slice-based context efficiency, full-contract Council planning, compact state preservation, token amortization, and selective local-repair versus graph-replan routing in reproducible fixture and synthetic tests.

Remaining work includes provider-backed blinded multi-step refactors in temporary worktrees, tokenizer-exact and billed-token runs, selective critic-lane optimization, canonical integration of Council V2, persistent Human Agent plan revisions, governed Experience/Crucible learning, independent security review, production authentication, community data governance, and repository cleanup.

AuraOS is released under the **GNU Affero General Public License v3.0**. Integrated OjibweMorph finite-state resources use **CC BY-NC-SA 4.0** and must not be assumed commercially licensed. The software licence does not grant rights to community-owned language data, recordings, cultural knowledge, learner data, private or ceremonial material, identities, or consent records.

- **Founder:** Dallas Courchene
- **Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)

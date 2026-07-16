# AuraOS

A sovereign, local-first, Arena-based cognitive operating substrate that compiles human intent into grounded, governed, temporary capability systems.

**AuraOS is not an LLM.** Aura helps humans and external AI workers understand a large system, select the smallest relevant context, assemble bounded tools, verify results, retain plans and evidence, and preserve human or community authority.

Aura began as a locally controlled tutor for learning and preserving Anishinaabemowin without surrendering language data to large external platforms. That origin shaped the architecture: local control, data minimization, inspectable memory, provenance, purpose-limited egress, revocable capability leases, and governance above model convenience.

The complete pre-benchmark architecture README is preserved at [`docs/README_PRE_ARCHITECT_BENCHMARK.md`](docs/README_PRE_ARCHITECT_BENCHMARK.md).

## Contents

- [What Aura Does](#what-aura-does)
- [First Architect Consolidation Benchmark](#first-architect-consolidation-benchmark)
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
11. requires human approval for consequential promotion;
12. records provenance, cost, state, and lifecycle receipts.

External models such as Hermes, Codex, OpenAI, Anthropic, Gemini, Fireworks-backed workers, or local models are **workers inside Aura's governed environment**. They are not Aura's architecture, memory, verifier, or authority.

## First Architect Consolidation Benchmark

**Benchmark:** `AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V1`  
**Status:** reproducible single-session pilot; plan-only; no production mutation  
**Model fixture:** GPT-5.6 Thinking, single-session assisted pilot

### Objective

> Scan the AuraOS repository and produce a grounded, staged refactor skeleton that consolidates memory, skill, capability, and agentic functions to improve the Human Agent Arena. Reuse existing Aura architecture, preserve compatibility through explicit adapters, retain plans and verifier evidence, and require human approval before mutation or promotion.

The same repository snapshot, objective, JSON plan contract, and deterministic grounding rubric were used across three arms.

| Arm | Calls | Input token proxy | Output token proxy | Total token proxy | Grounded-plan quality | Normalized cost* |
|---|---:|---:|---:|---:|---:|---:|
| Broad-context single planner | 1 | 130,485 | 1,169 | 131,654 | 0.9550 | $0.133992 |
| Aura-slice single planner | 1 | 13,201 | 1,667 | 14,868 | 0.9607 | $0.018202 |
| Aura Architect Council | 12 | 90,020 | 4,121 | 94,141 | 0.9458 | $0.102383 |

\*Normalized cost uses a declared $1/M input-token proxy and $3/M output-token proxy rate card. It is derived for comparison and is **not** a provider invoice or current provider price.

### Results

- Aura slices reduced input-token proxy by **89.88%** versus broad context.
- Aura slices reduced total-token proxy by **88.71%** and normalized comparison cost by **86.42%**.
- The sliced plan's deterministic quality changed by **+0.0057**.
- The 12-call Council remained **28.49%** below broad context in total-token proxy and **23.59%** below it in normalized cost.
- Council quality changed by **-0.0092** and did **not** outperform the single sliced planner.
- The tested inventory contained **860** source/config/document files, **52,671,947** bytes, and **1,538,107** lines, with a **13,167,987** char/4 token proxy.
- The Aura-slice input was **99.90%** below that full-repository proxy. The broad baseline was **99.01%** below it because it used a relevance-ranked 520,000-character cap rather than every repository byte.

### What this supports

This first run supports narrow claims that Aura can replace a broad repository handoff with a much smaller exact-slice packet, preserve grounded-plan quality on this task, and measure the aggregate cost of a real multi-role Architect Council.

It does **not** yet establish general quality superiority, Council superiority, production refactor success, provider-billed cost savings, production readiness, consciousness, or a conclusively revolutionary architecture.

### Defects discovered

1. **Localization drift:** generic `LOCALIZE_FIRST` candidates initially ranked civic, AMD, and server modules before the Architect/Human-Agent spine. The refined adapter now ranks exact spans, selected capability lanes, grounded affordances, objective-core files, then fallbacks.
2. **Plan contract loss:** `ArchitectFusionCouncil._normalize_plan_spec()` did not preserve planner-level `acceptance_criteria`, `rollback_conditions`, `risk_map`, or `constraints`.
3. **Scope false positive:** wording about “repository and source digests” was interpreted as repo-wide write authority and routed one exact task `PLAN_ONLY`.
4. **Test-neighbor gap:** `aura_arena_experience.py::build_arena_experience` had no nearby test mapping under the current heuristic.

The benchmark preserves these failures as evidence. The generated skeleton remains a human-review proposal rather than refactor-ready code.

### Measurement labels

- Repository bytes, lines, file count, CODEMAP size, and call count: **MEASURED**.
- Token values: **ESTIMATED** char/4 proxies.
- Quality scores and normalized costs: **DERIVED**.
- Provider-reported tokens and billed costs: **UNAVAILABLE** in this fixture run.
- The pilot was not blinded; all role fixtures were authored in one GPT-5.6 Thinking session.
- The values above come from the first scored workflow snapshot. The PR may receive later safety and documentation commits while retaining the same reproducible fixture and benchmark commands.

### Reproduce

```bash
python aura_codebase_navigator.py
python aura_architect_consolidation_benchmark_refined.py prepare --repo-root . --output-dir benchmark-output
python benchmarks/architect_consolidation/generate_gpt56_pilot_fixture.py --output benchmark-output/responses.gpt-5.6-thinking.json
python aura_architect_consolidation_benchmark_refined.py score --repo-root . --output-dir benchmark-output --responses benchmark-output/responses.gpt-5.6-thinking.json --input-rate 1.0 --output-rate 3.0
python aura_architect_benchmark_report.py --report benchmark-output/architect_consolidation_benchmark.json --responses benchmark-output/responses.gpt-5.6-thinking.json --skeleton benchmark-output/architect_consolidation_skeleton.json
```

See [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md) for full evidence and limitations.

## External LLM Slice Sessions

Aura now exposes a provider-neutral mechanism through which an external LLM can work inside the Agent Arena without downloading the repository.

```bash
python aura_agent_arena_mcp_external_llm.py
```

The additive MCP entrypoint exposes the original Agent Arena tools plus:

| Tool | Purpose |
|---|---|
| `aura_llm_session_open` | Prepare an Arena and return the first leased turn |
| `aura_llm_session_next` | Return the pending turn |
| `aura_llm_session_submit` | Stage and verify a response, then return completion or repair |
| `aura_llm_session_status` | Return safe public state and history |
| `aura_llm_session_export` | Export review evidence inside Aura's staging boundary |

```text
objective
→ Aura prepares Arena state
→ one Act Capsule is selected
→ exact source and test slices are leased
→ external model returns one bounded diff
→ Aura stages and verifies
→ pass: next capsule or READY_FOR_HUMAN_REVIEW
→ fail: bounded repair packet and repair turn
```

A turn includes only the objective, role, gate, Act Capsule, exact slices, allowed files, do-not-touch files, failure evidence, output contract, and token budgets. No repository archive is included.

`run_live_architect_with_external_callback()` also lets Aura use external providers for its real planner, alternate-planner, Shadow, Judge, and worker roles without importing provider SDKs. Aura retains grounding, verification, rollback, ledger, and human-review authority.

Session exports are confined to:

```text
Aura_Staging/external_llm_sessions/
```

Absolute paths, parent traversal, and resolved-path escapes are rejected.

Key files:

- `aura_external_llm_session.py`
- `aura_external_llm_session_safe.py`
- `aura_agent_arena_mcp_external_llm.py`
- `tests/test_aura_external_llm_session.py`
- `docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md`

## Architecture

```text
HUMAN / COMMUNITY OBJECTIVE
→ intent packet and machine-FST route
→ CODEMAP, topology, manifests, affordances, capability lanes
→ advisory VSA/DREAM/QDKT/JSpace/ST3GG cognition
→ bounded Coding, Agent, Human Agent, Civic, or domain Arena
→ temporary leases, Action Capsules, and boundary contracts
→ stage, test, verify, compare, repair, or rollback
→ exact evidence and human/community approval
→ experience, audit, cost, and lifecycle records
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

Before implementation, the skeleton requires repair of Council contract preservation, scope classification, and the missing experience test mapping.

## Truth and Safety

Advisory-only evidence includes model suggestions, VSA/HDC similarity, DREAM scores, QDKT observations, JSpace routes, ST3GG pointers, screenshots, summaries, and heuristic benchmark scores.

Consequential promotion requires exact source spans and hashes, valid leases, staged diff boundaries, tests, verifier evidence, topology-delta evidence, rollback information, and digest-bound human approval.

The external-LLM adapter prohibits repository download through a turn, direct production mutation, automatic commit/push/merge/promotion, gate bypass, unrestricted export paths, and model or VSA output becoming patch authority.

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
python -m pytest -q tests/test_aura_external_llm_session.py
```

## Documentation

- [`docs/README_PRE_ARCHITECT_BENCHMARK.md`](docs/README_PRE_ARCHITECT_BENCHMARK.md) — preserved complete architecture README
- [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) — canonical architecture and invariants
- [`.aura/CODEMAP.md`](.aura/CODEMAP.md) and [`.aura/CODEMAP.json`](.aura/CODEMAP.json) — human and machine code maps
- [`USER_GUIDE.md`](USER_GUIDE.md) — operator and REPL reference
- [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md) — full benchmark
- [`docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md`](docs/AURA_EXTERNAL_LLM_SLICE_SESSIONS.md) — external-model protocol
- [`docs/AURA_AGENT_ARENA_BRIDGE.md`](docs/AURA_AGENT_ARENA_BRIDGE.md) — Agent Arena
- [`docs/AURA_HUMAN_AGENT_ARENA.md`](docs/AURA_HUMAN_AGENT_ARENA.md) — Human Agent Arena
- [`docs/AURA_EMPIRICAL_COST_OBSERVATORY.md`](docs/AURA_EMPIRICAL_COST_OBSERVATORY.md) — empirical measurement
- [`.aura/SECURITY.md`](.aura/SECURITY.md) — security constraints

## Status and Licensing

AuraOS is active research and development software. The first Architect benchmark provides strong pilot evidence for slice-based context efficiency on one repository-planning task, while also showing that more multi-agent deliberation did not automatically improve quality.

Remaining work includes Council contract preservation, improved scope and test mapping, persistent Human Agent plan revisions, governed Architect Experience/Crucible integration, tokenizer-exact and provider-billed blinded benchmarks, independent security review, production authentication, community data governance, and repository cleanup.

AuraOS is released under the **GNU Affero General Public License v3.0**. Integrated OjibweMorph finite-state resources use **CC BY-NC-SA 4.0** and must not be assumed commercially licensed. The software licence does not grant rights to community-owned language data, recordings, cultural knowledge, learner data, private or ceremonial material, identities, or consent records.

- **Founder:** Dallas Courchene
- **Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)

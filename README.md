# AuraOS

A sovereign, local-first, Arena-based cognitive operating substrate that compiles human intent into grounded, governed, temporary capability systems.

**AuraOS is not an LLM.** External models—including Hermes, Codex, OpenAI, Anthropic, Gemini, Fireworks-backed workers, and local models—operate as bounded workers inside Aura's governed environment. They are not Aura's architecture, memory, verifier, or authority.

Aura began as a locally controlled system for learning and preserving Anishinaabemowin without surrendering language data to large external platforms. That origin shaped the wider architecture: local control, data minimization, inspectable memory, provenance, purpose-limited egress, revocable capability leases, human and community authority, and governance above model convenience.

The previous complete README remains available in repository history at [`f38fca0/README.md`](https://github.com/dallascourchene-commits/AuraOS/blob/f38fca03304b37b51738db99b3076490a880c31f/README.md). The pre-benchmark architecture README remains preserved at [`docs/README_PRE_ARCHITECT_BENCHMARK.md`](docs/README_PRE_ARCHITECT_BENCHMARK.md).

## Contents

- [What Aura Does](#what-aura-does)
- [Governed Human-Agent Learning Loop](#governed-human-agent-learning-loop)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Benchmark Evidence Dashboard](#benchmark-evidence-dashboard)
- [Council–Surgeon Operating Policy](#councilsurgeon-operating-policy)
- [Truth and Authority](#truth-and-authority)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Status and Licensing](#status-and-licensing)

## What Aura Does

Instead of giving an AI worker a giant prompt and an entire repository, Aura:

1. parses the objective;
2. compiles a structured intent packet;
3. validates the route through finite-state constraints;
4. discovers and reuses existing capabilities;
5. localizes exact files, symbols, tests, evidence, and dependencies;
6. opens a bounded Arena;
7. leases only the required capabilities and context;
8. stages proposed changes rather than granting direct production access;
9. runs tests, Shadow checks, and verifiers;
10. returns bounded repair evidence when a gate fails;
11. escalates graph-level failures without escalating every local test failure;
12. requires human approval for consequential promotion; and
13. records prompts, outputs, tokens, state, verification, repairs, costs, and lifecycle receipts.

## Governed Human-Agent Learning Loop

Aura separates **understanding**, **governed execution**, and **learning** so evidence cannot silently become authority.

| Surface | Role | Authority boundary |
|---|---|---|
| **Aura Observatory** | Explains how an intention was parsed, routed, localized, compressed, and bounded | Review-only; it does not stage changes, run workers, mutate production, or grant permission |
| **Human Agent Arena** | Human/Aura/agent command centre for `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE` | Actions pass guarded WFST admission; exact spans, hashes, tests, verifiers, leases, and human approval remain authoritative |
| **Emergent Refactor Workspace** | Imports and searches emergent findings, preserves provenance, gathers bounded arXiv/GitHub evidence, and compiles reviewable refactor packets | Findings and research are evidence inputs only; unresolved selections fail closed and context is committed only after guarded admission |
| **Learning Arena / Crucible** | Mines complete verified `ArenaExperience` records and proposes empirical-uncertainty updates | TRAIN/VALIDATION/SHADOW separation; proposal-only crystallization; no automatic grammar, policy, source, commit, push, PR, or merge authority |

Canonical lineage:

```text
ordinary human intention
  → Aura Observatory
  → bounded Human Agent task
  → FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
  → verifier evidence
  → OutcomeVector
  → ArenaExperience V3
  → Learning Arena / Crucible
  → TRAIN / VALIDATION / SHADOW
  → CRYSTALLIZATION_PROPOSED
  → verifier and human review
```

The merged emergent-research surface adds content-addressed run/evidence storage, exact seed provenance verification, bounded public research, normalized tool-run records, and a local UI for selecting findings and research evidence. It does **not** bypass the Arena lifecycle or promote hypotheses into production authority.

## Architecture at a Glance

```text
HUMAN / COMMUNITY OBJECTIVE
  → intent packet and machine-FST route
  → CODEMAP, topology, manifests, affordances, capability lanes
  → Selective Council when systemic planning is justified
  → sliced Surgeon for bounded implementation
  → compact State Ledger for continuity without conversation replay
  → stage, test, verify, repair, replan, or rollback
  → exact evidence and human/community approval
  → chronicle, cost, experience, and lifecycle records
```

Primary surfaces include semantic LEXC routing, machine FST/WFST admission, CODEMAP and compiled topology, Capability Connectome and Genome Resolver, Coding Arena, Agent Arena Bridge, Human Agent Arena, Architect Fusion Loop, Planning Board projections, external-LLM slice sessions, Refactor Arena staging, Arena Experience ledgers, Crucible proposal paths, Ephemeral Organ Runtime, empirical observability, Civic Commons, and Anishinaabemowin tutoring and governance.

Advisory systems may rank, recall, compress, visualize, and hypothesize. They never replace exact source spans, hashes, tests, verifier evidence, leases, consent, and human or community approval.

## Benchmark Evidence Dashboard

Evidence is organized by strength. **Executable gate evidence outranks token proxies; deterministic comparative proxies outrank estimated structural projections; discovery scans identify opportunities but do not prove implementation quality.**

### Tier 1 — Executable gate evidence

| Benchmark | Calls / tests | Result | Claim boundary |
|---|---:|---|---|
| **Selective Council V3 + Surgeon cross-module fixture** | 12 calls; visible `3/3`; hidden `3/3`; regression `2/2` | `WORKING`, `ACCEPTED`; observed `100.00`; benchmark `97.50`; API, scope, security, compilation, and static-analysis gates passed | Controlled executable fixture |
| **Real AuraOS refactor trial** | visible/property `32/32`; review-derived adversarial `35/35`; focused regression `21/21` | `WORKING`, `ACCEPTED`; observed `100.00`; benchmark `93.50`; required gates passed | Real branch trial; planning arms were frozen assisted artifacts, not blinded independent-provider generations |

### Tier 2 — Deterministic comparative proxies

| Benchmark | Baseline | Aura result | Difference | Claim boundary |
|---|---:|---:|---:|---|
| **Context localization** | broad context `131,655` total-token proxy; quality `0.9550` | Aura slice `14,431`; quality `0.9607` | **89.04% lower** total proxy; quality `+0.0057` | Reproducible fixture; not provider billing |
| **Selective Council routing** | Council V2: 18 calls, 15 critic reports, `158,545` total proxy | V3: 12 calls, 9 critic reports, `106,494` | **33.33% fewer calls**, **40.00% fewer critic reports**, **32.83% lower** total proxy; same selected plan, patch digest, and accepted quality | Controlled fixture |
| **State Ledger continuity** | step-7 full history `6,140` proxy tokens | compact ledger `234` | **96.19% less context**; preservation `1.0000`; drift `0.0000` | Synthetic multi-step continuity test |

### Tier 3 — Estimated structural projections

| Projection | Counterfactual | Proposed structure | Result | Claim boundary |
|---|---:|---:|---:|---|
| **Shared grounding evidence** | repeated evidence in nine capsules: `2,004` proxy tokens | one shared evidence object plus references: `938` | `1,066` avoided; **53.1936% projected savings** | PR #138 head `15bea1a`; `ESTIMATED` / `PROJECTED_STRUCTURAL_TOKEN_PROXY`; not provider billing and not a merged-main implementation claim |

### Tier 4 — Discovery and capacity projections

| Scan | Scope | Result | Claim boundary |
|---|---|---|---|
| **Emergent capacity scan** | `708` Python files; `10,815` topology nodes; `20,764` edges; 15 probes | 0 probe failures; strongest recurring missing wire appeared 5 times | Discovery evidence only; recurrence is not patch correctness |
| **Grounded capacity projections** | 7 capacity probes | 0 probe failures; every candidate remained `NEEDS_GROUNDING` | No production-readiness or code-quality claim |

Detailed benchmark evidence remains in the repository's benchmark documents, output records, seed-run reports, and append-only registries. Estimated and provider-reported tokens are stored separately; unknown costs remain unknown.

## Council–Surgeon Operating Policy

```text
Selective Council once → architecture, dependencies, interfaces, invariants,
                          sequence, risks, and rollback
Sliced Surgeon          → each bounded Act Capsule
local test failure      → bounded Surgeon repair
interface/dependency/
invariant failure       → Council replan → Surgeon resumes
```

Universal critic lanes are scope and tests. Sequence, continuity, rollback, and cost lanes are admitted from measured plan structure and risk instead of being called uniformly.

## Truth and Authority

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

Consequential promotion requires exact source spans and hashes, valid capability leases, staged-diff boundaries, tests, verifier evidence, topology-delta evidence, rollback information, and digest-bound human approval.

## Quick Start

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python aura_codebase_navigator.py
```

Launch the Human Agent Arena:

```bash
python aura_human_agent_arena_server.py --repo-root .
# Open http://127.0.0.1:8090
```

Launch the unified Showcase with Observatory and Learning Arena surfaces:

```bash
python aura_showcase_server.py
```

Run focused documentation and Human Agent tests with the relevant test modules under `tests/` before promotion.

## Documentation

- [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) — canonical architecture, authority, learning boundaries, and benchmark hierarchy
- [`USER_GUIDE.md`](USER_GUIDE.md) — current operator guide
- [`docs/AURA_HUMAN_AGENT_ARENA.md`](docs/AURA_HUMAN_AGENT_ARENA.md) — Human Agent Arena detail
- [`docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md`](docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md) — Observatory → Human Agent → Crucible lineage
- [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md) — executable benchmark evidence
- [`docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`](docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md) — output-quality protocol
- [`docs/AURA_EMPIRICAL_COST_OBSERVATORY.md`](docs/AURA_EMPIRICAL_COST_OBSERVATORY.md) — empirical measurement
- [`.aura/CODEMAP.md`](.aura/CODEMAP.md) and [`.aura/CODEMAP.json`](.aura/CODEMAP.json) — human and machine code maps
- [`.aura/SECURITY.md`](.aura/SECURITY.md) — security constraints

## Status and Licensing

AuraOS is active research and development software. Current evidence supports slice-based context efficiency, selective Council routing on controlled fixtures, executable refactor evaluation, compact state preservation, bounded repair versus graph-replan routing, and governed Human Agent/Observatory/Crucible lineage. It does not establish consciousness, general model superiority, universal provider savings, or production readiness.

AuraOS is released under the **GNU Affero General Public License v3.0**. Integrated OjibweMorph finite-state resources use **CC BY-NC-SA 4.0** and must not be assumed commercially licensed. The software licence does not grant rights to community-owned language data, recordings, cultural knowledge, learner data, private or ceremonial material, identities, or consent records.

- **Founder:** Dallas Courchene
- **Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)

# AuraOS

## Her name is **Aura** — Augmented Universal Reasoning Architecture

`AuraOS` is the repository and operating substrate. **Aura** is the architecture.

> **A sovereign, local-first, objective-native cognitive substrate for coordinating deterministic software, exact evidence, human governance, replaceable AI workers, and reusable capability — without allowing probabilistic output to silently become truth or authority.**

> **Human / automated reviewer orientation:** Evaluate AuraOS in this order: **what exists → measured evidence → implementation status → architecture → future direction**. This repository contains working software, active refactor work, published enabling architecture, and longer-range research in the same tree. Those categories are intentionally distinct.

### If you only read one block

- **AuraOS is working research software**, not only a paper or roadmap.
- **PR #255 and PR #269 are merged foundations** for the current intent-native / verified-ephemeral-workspace refactor.
- On the current **Architect Consolidation** pilot, the Aura-slice planner used **88.71% less total token proxy** than the broad-context planner while its deterministic grounded-plan score changed from **0.9550 to 0.9607**.
- On the current **Executable Refactor Code-Quality** fixture, **Selective Council V3 + Surgeon** produced the same accepted patch digest and measured quality as Council V2 + Surgeon while using **33.33% fewer model calls** and **32.83% less total token proxy**.
- Those are **fixture-bound measurements**, not universal performance guarantees, provider billing, energy measurements, or independent industry benchmarks.
- **R** = repository-backed; **P** = active program/refactor; **E** = enabling reference architecture; **S** = scenario/research hypothesis.
- External research is used in two ways: to **calibrate Aura's measured mechanisms against related work** and to document **mechanism-level convergence or influence**. External papers do not prove Aura's implementation.
- AuraOS is **not yet** a zero-friction arbitrary-repository product, an autonomous merge authority, a deployed real-money capability economy, or a measured global energy-saving system.

**Repository status:** active research and development  
**Software license:** GNU AGPL v3.0  
**Research record:** nine defensive publications, claims N1–N100; Zenodo provides dated public records, **not peer review**  
**Latest paper:** [Paper IX v2.0 — DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020)  
**PR1 foundation:** [#255](https://github.com/dallascourchene-commits/AuraOS/pull/255)  
**PR2 foundation:** [#269](https://github.com/dallascourchene-commits/AuraOS/pull/269)

> **Meaning may guide discovery. Only exact grounded evidence and authorized governance may grant authority.**

---

## Contents

1. [What exists](#1-what-exists)
2. [Architecture at a glance](#2-architecture-at-a-glance)
3. [Evidence](#3-evidence)
4. [Implementation status](#4-implementation-status)
5. [Core mechanisms in plain language](#5-core-mechanisms-in-plain-language)
6. [Truth, authority, and safety](#6-truth-authority-and-safety)
7. [Quick start](#7-quick-start)
8. [Research convergence and prior art](#8-research-convergence-and-prior-art)
9. [What is not claimed](#9-what-is-not-claimed)
10. [Investigate and challenge the claims](#10-investigate-and-challenge-the-claims)
11. [Why Aura exists](#11-why-aura-exists)
12. [Future direction](#12-future-direction)
13. [Licensing and status](#13-licensing-and-status)

---

# 1. What exists

AuraOS is a working repository with deterministic routing, generated structural maps, tests, schemas, governed coding surfaces, model-routing infrastructure, bounded workspaces, provenance/continuity machinery, domain Arenas, and an active numbered refactor program.

## Repository snapshot

The last generated CODEMAP snapshot referenced by the current README reports:

| Fact | Generated evidence |
|---|---:|
| Files indexed | **1,576** |
| Repository bytes indexed | **59,522,794** |
| Estimated text tokens | **5,371,792** |
| Deep-topology nodes | **11,393** |
| Deep-topology edges | **27,882** |
| Python modules indexed | **977** |
| Schema / lexicon artifacts indexed | **232** |

Source: [`.aura/CODEMAP.md`](.aura/CODEMAP.md).

These are generated navigation counts. They describe the indexed tree at generation time; they are not marketing constants or canonical source authority.

## Merged refactor foundation

### PR1 — intent-native spatial workspace contracts

[#255](https://github.com/dallascourchene-commits/AuraOS/pull/255) separated:

```text
PARSE → BIND → ADMIT
```

The guarded final verification reported **46/46 focused tests passed**, along with compilation, schema validation, fatal Ruff checks, diff checks, and generated-map synchronization.

### PR2 — verified ephemeral workspace lifecycle

[#269](https://github.com/dallascourchene-commits/AuraOS/pull/269) preserved V1 while adding a separately verified interactive Workspace V2 lifecycle.

Its documented gate included:

- **52 focused PR2 tests**;
- **81 retained V1 / Phase-0 / PR1 tests**;
- compilation and fatal Ruff checks;
- Draft 2020-12 schema validation;
- identity/scope checks;
- additional hardening around hostile callbacks, cancellation, expiry, identity, memory budgets, races, and cleanup.

PR2 binds graph, adapter, schema, implementation, and source identity before activation; constrains DAG execution, TTL, budgets, retries, cancellation, and cleanup; revokes leases at terminal states; and prevents dissolved workspaces from silently resuming.

PR3 onward continues the broader numbered program. Do not infer current PR status from this README; use GitHub for live branch/review state.

## Implemented surfaces worth inspecting first

| Surface | Repository-backed role | Important boundary |
|---|---|---|
| **FST / WFST intent routing** | structures and admits intent through bounded machine grammar | routing does not create truth or authority |
| **CODEMAP + topology** | compact repository navigation over files, symbols, and relationships | generated navigation, not patch authority |
| **Capability Connectome / Genome Resolver** | asks what capability already exists and how it relates before invention | reuse candidates remain advisory until grounded |
| **Relationship Atlas / Compass / Relational Synthesis** | exposes wired, missing, overlapping, stale, and prohibited relationships | exact source remains authoritative |
| **Human Agent Arena** | `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE` | human disposition remains terminal |
| **Coding Arena / Workbench** | localizes exact code neighborhoods, dependencies, tests, and worker context | similarity never outranks exact source |
| **Council V3** | invokes only critic lanes justified by plan structure and risk | planning cannot mutate source |
| **Sliced Surgeon** | receives bounded exact-source slices for implementation | cannot redefine architecture outside scope |
| **Forge + Gate** | coordinates grounded work under identity, policy, lease, and egress boundaries | no automatic merge/release authority |
| **Waboose** | graph-guided review plus exact-source corroboration | findings cannot self-confirm or self-patch |
| **Model Cognome** | records model/provider evidence, cost, latency, drift, and route proposals | no model-vote authority |
| **Attempt Archive / ArenaExperience / Crucible** | preserves successful, failed, denied, and superseded work and proposes bounded learning | experience cannot silently become policy |
| **ARCH / runtime harnesses** | preserve exact-head continuity, bounded work, proof, review, and terminal state | no autonomous merge |
| **Spatial / Civic / Financial / other Arenas** | governed domain projections and task-specific surfaces | projection does not become domain truth |

For canonical ownership and exact paths, inspect [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) and [`.aura/CODEMAP.md`](.aura/CODEMAP.md).

---

# 2. Architecture at a glance

Aura's repository-backed engineering loop is:

```text
HUMAN / COMMUNITY OBJECTIVE
        │
        ▼
INTENT + CONSTRAINTS + PROHIBITIONS
        │
        ▼
FST / WFST ROUTING + ADMISSION
        │
        ▼
CAPABILITY DISCOVERY + RELATIONAL ORIENTATION
Connectome / Resolver / CODEMAP / topology / Atlas
        │
        ▼
MINIMUM RELEVANT EXACT EVIDENCE
files + symbols + spans + hashes + tests + contracts
        │
        ▼
BOUNDED WORK
Arena / Council / Surgeon / Forge / replaceable workers
        │
        ▼
TESTS + VERIFIERS + RECEIPTS
        │
        ▼
HUMAN / COMMUNITY DISPOSITION
        │
        ▼
EXPERIENCE + PROVENANCE + REVIEW-GATED LEARNING
```

The important idea is not that every step is novel in isolation.

It is the composition and the boundaries:

```text
similarity       ≠ truth
navigation       ≠ patch authority
planning         ≠ execution
execution        ≠ verification
verification     ≠ promotion
experience       ≠ authority
generated map    ≠ canonical source
model opinion    ≠ governance
temporary state  ≠ permanent authority
```

Aura uses ordinary tools where ordinary tools are sufficient. The architecture focuses on what happens **between** tools when probabilistic workers, long-running work, provenance, sensitive data, multiple models, and consequential authority are involved.

---

# 3. Evidence

This README now centers its quantitative engineering claims on **two current benchmark documents**.

Older exploratory benchmark families remain useful historical evidence, but they are not used here to stack increasingly large percentages into one headline.

## 3.1 Architect Consolidation Benchmark — context localization

Source: [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)

**Status:** reproducible single-session planning pilot; no production mutation.  
**Model fixture:** GPT-5.6 Thinking, one assisted session.  
**Token values:** deterministic proxy, not tokenizer/provider billing.

All arms received the same repository commit, objective, JSON plan contract, and deterministic grounding rubric.

| Arm | Calls | Input proxy | Output proxy | Total proxy | Grounded-plan quality |
|---|---:|---:|---:|---:|---:|
| Broad-context planner | 1 | 130,485 | 1,169 | **131,654** | **0.9550** |
| Aura-slice planner | 1 | 13,201 | 1,667 | **14,868** | **0.9607** |
| Aura Architect Council | 12 | 90,020 | 4,121 | **94,141** | **0.9458** |

Measured/derived comparison of the single-planner arms:

- **89.88% lower input-token proxy** for the Aura slice;
- **88.71% lower total-token proxy**;
- grounded-plan quality changed by **+0.0057**;
- the broad baseline was already relevance-ranked and capped rather than receiving every repository byte.

The Council used less total proxy than the broad-context planner, but its deterministic plan-quality score was lower than the single sliced planner. That negative result remains visible.

### What this supports

On this task, Aura's localization machinery produced a much smaller exact-slice planning packet without a measured loss in the benchmark's deterministic grounded-plan score.

### What this does not support

It does not establish:

- general model-quality superiority;
- Council superiority;
- provider-billed cost savings;
- production refactor success;
- a universal 88.71% reduction;
- energy or carbon savings.

The benchmark itself records defects discovered during evaluation, including localization ranking errors, lost plan-level contracts during Council normalization, a false repo-wide scope route, and a missing nearby-test mapping. The experiment is useful partly because it exposes those failures rather than hiding them.

---

## 3.2 Executable Refactor Code-Quality Benchmark

Source: [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)

This benchmark moves beyond planning and compares actual patches on the same controlled cross-module task, starting fixture, allowed source files, visible tests, hidden tests, regression tests, API checks, scope checks, security scan, static analysis, and maintainability measurement.

| Refactoring method | Calls | Total proxy | Visible | Hidden | Regression | Disposition | Observed score | Benchmark score |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Broad-context implementer | 1 | **131,654** | 3/3 | 1/3 | 2/2 | `PARTIAL` | 80.34 | 78.33 |
| Aura-slice Surgeon | 1 | **14,868** | 3/3 | 2/3 | 2/2 | `PARTIAL` | 88.89 | 86.67 |
| Council V2 + Surgeon | 18 | **158,545** | 3/3 | 3/3 | 2/2 | `ACCEPTED` | 100.00 | 97.50 |
| **Selective Council V3 + Surgeon** | **12** | **106,494** | **3/3** | **3/3** | **2/2** | **`ACCEPTED`** | **100.00** | **97.50** |

The single sliced Surgeon used **88.71% less total token proxy** than the broad-context implementer and passed one additional held-out test, but it remained `PARTIAL`.

Both Council-guided arms passed every required gate.

### Selective Council V3 versus Council V2

On the frozen fixture, V3 preserved V2's accepted result while using:

- **33.33% fewer total model calls** — 12 vs. 18;
- **40.00% fewer critic reports** — 9 vs. 15;
- **33.58% lower input-token proxy**;
- **32.83% lower total-token proxy**;
- **0.0000 planning-quality delta**;
- the same substantive selected plan after version-only metadata is excluded;
- the same executable patch digest;
- the same final code-quality scores and `ACCEPTED` disposition.

That is a positive controlled ablation.

It is not evidence that every critic lane should always be skipped or that every Aura refactor will save one third of its model calls.

### What remains to prove

The benchmark explicitly calls for:

- independent provider calls;
- tokenizer-exact/provider-billed usage;
- repeated independent trials;
- broader task suites;
- real AuraOS tasks in isolated worktrees;
- independently authored hidden tests;
- mutation, coverage, typing, dependency, and performance gates where relevant;
- blinded maintainability review;
- variance and confidence intervals.

---

## 3.3 External calibration — related research, not a leaderboard

The following results are useful because they test related pressures in independent systems. They are **not directly comparable scoreboards**: tasks, models, token accounting, context sources, and evaluation metrics differ.

| Independent work | Reported result | Relation to Aura |
|---|---|---|
| [FastContext — arXiv:2606.14066](https://arxiv.org/abs/2606.14066) | up to **60% lower coding-agent token consumption** with up to **5.5% higher end-to-end resolution** across its evaluated SWE-bench/SWE-QA settings | supports separating repository exploration/localization from the main solving context |
| [SWE-Pruner — arXiv:2601.16746](https://arxiv.org/abs/2601.16746) | **23–54% token reduction** on agent tasks such as SWE-bench Verified with minimal reported performance impact | supports task-conditioned context pruning rather than fixed blind compression |
| [Squeez — arXiv:2604.04979](https://arxiv.org/abs/2604.04979) | removed **92% of input tokens** on its tool-output-pruning test while reaching **0.86 recall / 0.80 F1** | shows large evidence pruning can be possible when the pruning target is narrow and task-conditioned |
| [State-in-Context Minification — arXiv:2606.01326](https://arxiv.org/abs/2606.01326) | **42% lower average input tokens** on SWE-bench Verified but a **12 percentage-point resolution drop** | important counterexample: context reduction can harm task success when it removes the wrong information |

The useful conclusion is not:

> Aura beats these systems.

The defensible conclusion is:

> **Context selection is itself an engineering variable. Independent work shows that selective repository/context reduction can materially reduce token cost, but it can also lower task success when pruning destroys answer-determining information. Aura's current fixtures test one architecture for preserving exact evidence while reducing the context aperture.**

That is the standard the next Aura benchmark tier should continue to test.

---

# 4. Implementation status

The repository, refactor program, defensive publications, and future scenarios are not the same evidence class.

| Tag | Meaning |
|---|---|
| **R — Repository-backed** | implemented or directly represented by current source/contracts/tests |
| **P — Program / active refactor** | specified in the governed numbered refactor program; may not yet be merged |
| **E — Enabling reference architecture** | detailed published embodiment intended to be implementable, but not represented as deployed end-to-end |
| **S — Scenario / research hypothesis** | scale model, extrapolation, or research framing requiring future evidence |

## Repository-backed substrate — R

Representative examples include:

- FST/WFST intent routing;
- CODEMAP/deep topology;
- Human and Coding Arenas;
- Council V3;
- Sliced Surgeon;
- Forge;
- Gate;
- Waboose;
- Connectome/Genome Resolver;
- Atlas/Compass/Relational Synthesis;
- Model Cognome;
- Attempt Archive/ArenaExperience/Crucible;
- Architecture/runtime harnesses;
- PR1/PR2 workspace contracts and lifecycle;
- governed domain projections already present in source.

`R` does **not** mean every performance claim about a component has been independently established.

## Active program — P

The numbered refactor continues to generalize and harden the existing substrate around:

- objective-native workspace/project compilation;
- source-first project reconstruction;
- hierarchical selective hydration;
- Developer/Architecture Arena hardening;
- persistent capability contracts and recipes;
- broader arbitrary-repository onboarding;
- provenance, package, rights, and economic interfaces.

Check the current numbered refactor plan and live GitHub PR state rather than assuming every `P` item is merged.

## Enabling architecture — E

Paper IX describes farther embodiments such as:

- Capability Commons;
- Personal Cognitive Capsule;
- Aura Places;
- Open Discovery Foundry;
- machine/facility capability participation;
- Ephemeral Institutions;
- AuraNet/federation.

These are disclosed architecture, not claims of completed deployment.

## Scenario / research hypothesis — S

This includes:

- large adoption arithmetic;
- civilization-scale economic consequences;
- global energy-reduction scenarios;
- mature real-money Extension Economy behavior;
- broad GCI / collective-intelligence classification.

These questions may be worth studying. They are not current Aura benchmarks.

---

# 5. Core mechanisms in plain language

Aura uses project-specific names partly because the names also encode **negative authority boundaries**. The generic concept tells you what a component may do; the Aura contract often also tells you what it must never silently become.

| Aura term | Approximate conventional concept | Aura-specific boundary |
|---|---|---|
| **CODEMAP** | repository topology/index | navigation only; generated map is not source authority |
| **Connectome / Genome Resolver** | capability/dependency graph + reuse resolver | asks what already exists before invention |
| **Atlas / Compass / Relational Synthesis** | relationship/dependency analysis | identifies relationships; exact source decides |
| **Council V3** | selective multi-model / multi-critic planner | critic/model output cannot authorize mutation |
| **Surgeon** | bounded code implementation worker | operates on authorized exact slices |
| **Forge** | governed engineering orchestrator | prepares/coordinates work; no automatic merge |
| **Gate** | identity/policy/capability-security envelope | leases and policy bound authority and egress |
| **Waboose** | graph-guided code review | finding is evidence, not self-confirming patch authority |
| **Model Cognome** | model/provider capability registry | records route evidence; no model vote creates truth |
| **Arena** | bounded objective-specific execution environment | participants/capabilities/authority have explicit lifecycle |
| **Ephemeral Workspace / Organ** | temporary lifecycle-controlled runtime | leases revoke and temporary authority dissolves |
| **Attempt Archive** | failed/superseded attempt ledger | remembers failure without promoting history into policy |
| **Crucible** | review-gated learning/evaluation pipeline | learning remains proposal-only until independently promoted |
| **ARCH** | long-horizon refactor continuity/convergence governance | exact state, proof, review, stop conditions; no autonomous merge |

Aura is not replacing `grep`, Git, `pytest`, AST parsers, JSON Schema, model APIs, or linters.

It is trying to make the **system around those tools** more bounded, evidence-bearing, reusable, and governable.

---

# 6. Truth, authority, and safety

A condensed version of Aura's constitutional discipline is:

```text
planning proposes
governance authorizes
verification proves

exact source / canonical records
    >
generated summaries / semantic similarity / visual topology

hard admission
    before
soft ranking

model output
    never silently becomes
authority
```

Representative invariants include:

```yaml
patch_authority: exact_source_spans_and_hashes_only
external_model_action_authority: false
vsa_patch_authority: false
visual_topology_patch_authority: false
automatic_grammar_promotion: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

Unknown, stale, malformed, expired, conflicting, or unauthorized consequential work is intended to fail closed.

For the current canonical boundaries, inspect:

- [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md)
- [`.aura/SECURITY.md`](.aura/SECURITY.md)
- [`docs/AURA_ARCH_V2_3_HARNESS.md`](docs/AURA_ARCH_V2_3_HARNESS.md)

---

# 7. Quick start

## Requirements

- Python >= 3.10
- Git
- Linux or Android/Termux
- dependencies from `requirements.txt`
- CPU-first operation is supported; external model access is optional for many surfaces

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Regenerate/verify structural orientation:

```bash
python aura_codebase_navigator.py
python -m aura_codemap_verify --compare-json .aura/CODEMAP.json
python -m aura_agent_arena_cli stabilization-status
python -m aura_agent_arena_cli digest
```

Launch common local surfaces:

```bash
python aura_human_agent_arena_server.py --repo-root . --demo
python aura_coding_arena_server.py --demo
python aura_showcase_server.py --demo-project winnipeg_pathways
```

## Point the Architecture Harness at a repository

```bash
python scripts/aura_architecture_harness.py \
  --repo-root /path/to/repository \
  handoff \
  --output-dir /path/outside/repository/repo-ai-handoff
```

Important boundary:

> **A full zero-friction governed run against an arbitrary foreign repository is still P-class work.**

The architecture can inspect/orient around a supplied repository root, but the complete arbitrary-repository governed execution path is still being hardened.

---

# 8. Research convergence and prior art

Aura maintains two distinct research relationships.

## 8.1 Independent empirical calibration

Section 3 compares Aura's current benchmark mechanisms with independent work on repository exploration, task-conditioned pruning, tool-output pruning, and minification.

Those papers provide context for the **problem**, not proof of Aura.

## 8.2 Mechanism-level chronology / convergence

In some cases, dated Aura repository artifacts show a mechanism before later publications independently named, benchmarked, or systematized an overlapping pressure.

That claim must remain narrow:

- commit/merge chronology supports **timing**;
- mechanism comparison supports **technical overlap**;
- neither alone proves universal novelty;
- known borrowings/influences remain explicitly credited;
- later refinements can have mixed lineage even when an earlier Aura mechanism predates a paper.

Detailed chronology and provenance:
[`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md)

Architecture lineage and acknowledged influences:
[`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md)

## 8.3 Defensive publications

Aura's nine-paper stack is a dated public research/prior-art record.

| Paper | Claim family | Claims |
|---|---|---:|
| **I** | polysynthetic/edge cognitive substrate, VSA/HDC, routing, topology | N1–N8 |
| **II** | holographic/swarm/network concepts | N9–N13 |
| **III** | VSA-addressed Liquid Internet | N14 |
| **IV** | methodological/training/rendering extensions | N15–N17 |
| **V** | FST routing / self-refactoring | N18–N20 |
| **VI** | enhanced FST / topology / impact analysis | N21–N23 |
| **VII** | bounded protocol-layer hardening | N24–N30 |
| **VIII** | evidence-ordered relational Arenas and governed combinations | N31–N50 |
| **IX v2.0** | objective-native capability composition / Commons and enabling embodiments | N51–N100 |

A useful historical transition is:

```text
early broad exploration
→ increasingly bounded protocols
→ evidence-ordered governed combinations
→ objective-native compositional architecture
```

A defensive publication is **not** peer review, independent validation, a patent grant, or proof that every historical claim remains current.

---

# 9. What is not claimed

AuraOS is an active research substrate, not a finished universal product.

The README does **not** claim:

- that every Paper IX embodiment is deployed;
- that arbitrary repositories can already be onboarded with zero configuration and full governed execution;
- that Aura can autonomously merge consequential changes;
- that all model outputs are correct because they passed through Aura;
- that one benchmark establishes general superiority;
- that token-proxy savings equal provider-billed savings;
- that token savings automatically equal energy/carbon/water savings;
- that a generated CODEMAP or vector representation is canonical truth;
- that research convergence proves Aura implementation or priority over entire fields;
- that current local fixtures substitute for independent multi-provider trials;
- that a real-money capability marketplace is deployed;
- that spatial simulation is physical truth;
- that future social, scientific, economic, or institutional embodiments are already production systems.

If a limitation is already declared here, it is not a reason to discard unrelated repository-backed evidence. It is the boundary of the claim being made.

---

# 10. Investigate and challenge the claims

Aura's claims should become stronger by surviving attempts to break them.

| Area | Useful hostile question | Start here |
|---|---|---|
| **Context / benchmark validity** | Can you reproduce the localization and Council V2→V3 results? Can you build tasks where the benefit disappears? | the two benchmark docs in Section 3 |
| **Compiler / lifecycle correctness** | Can a schema-valid but semantically invalid graph activate or survive cancellation/dissolution? | PR1/PR2 contracts and tests |
| **Security / authority** | Can a worker escape leases, forge identity/evidence, or turn model output into authority? | `.aura/SECURITY.md`, Gate, ARCH |
| **Governance bypass** | Can an agent commit/merge/self-promote despite the stated invariants? | ARCH, Forge, Gate, Crucible |
| **Provenance** | Can evidence or authorship be forged, replayed, detached, or silently upgraded? | exact-head / receipt / provenance owners |
| **Research chronology** | Does the cited Aura mechanism really predate the paper, or is the comparison just naming similarity? | convergence doc + Git history |
| **Architecture fit** | Can a local fix satisfy tests while violating a higher-level owner/invariant? | `.aura/ARCHITECTURE.md`, CODEMAP, tests |

### Verify the current architecture

1. [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md)
2. [`.aura/CODEMAP.md`](.aura/CODEMAP.md)
3. current source + tests for the subsystem in question
4. [`USER_GUIDE.md`](USER_GUIDE.md)

### Verify the quantitative claims

1. [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)
2. [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)

### Understand the Harness

1. [`docs/AURA_ARCH_V2_3_HARNESS.md`](docs/AURA_ARCH_V2_3_HARNESS.md)
2. [`docs/AURA_ARCHITECTURE_HARNESS.md`](docs/AURA_ARCHITECTURE_HARNESS.md)
3. [`docs/AURA_RUNTIME_REFACTOR_HARNESS.md`](docs/AURA_RUNTIME_REFACTOR_HARNESS.md)

### Inspect research lineage

1. [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md)
2. [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md)
3. Papers I–IX

---

# 11. Why Aura exists

Aura began with a narrower problem: building a locally controlled Anishinaabemowin learning system on constrained hardware without requiring community language infrastructure to live entirely inside proprietary external platforms.

That origin helped establish design pressures that remained useful as the repository grew:

- local control;
- resource constraint;
- compact structured intent;
- data minimization;
- explicit provenance;
- bounded external-provider access;
- continuity;
- revocable authority;
- human/community governance.

The polysynthetic-language inspiration should be read carefully. Aura does **not** claim that its six-slot machine grammar is a complete model of Anishinaabemowin or Dene/Athabaskan grammar.

The engineering lesson was narrower:

> **Dense meaning can be composed from constrained relationships rather than represented as an unstructured bag of words.**

As Aura grew, its own development repeatedly exposed another pattern:

```text
new capability
→ new complexity
→ new failure mode
→ architectural response
→ verified response becomes reusable
```

CODEMAP, selective Council, the Surgeon split, Attempt Archive, Waboose, and the Harness all emerged in response to concrete scaling or continuity problems.

Detailed origin:
[`docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md`](docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md)

Detailed architecture history:
[`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md)

---

# 12. Future direction

Aura's longer-term direction is **reuse before unnecessary regeneration**.

A solved capability can be expensive to discover, implement, debug, test, secure, benchmark, and document the first time.

The next objective should not automatically pay that full cost again.

As a deliberately dry analogy:

> **We do not reinvent the transistor every time we build a phone. Software agents should not need to rediscover every verified primitive every time somebody opens a new chat.**

Paper IX explores an objective-native model:

```text
objective
→ discover applicable capability
→ compose only what is needed
→ adapt the novel delta
→ verify in the new context
→ execute inside a bounded Arena
→ preserve evidence / provenance
→ dissolve temporary authority
→ retain reusable capability
```

This is where the Capability Commons, recipes, Developer/Architecture Arenas, Places, Foundry, and other E/S-class directions enter.

They belong **after** the repository-backed architecture and evidence because they are consequences and research directions, not substitutes for current proof.

Further reading:

- [`docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md`](docs/AURA_EXTENSION_ECONOMY_AND_SEVEN_FIRES.md)
- [`docs/AURA_METRICS_AND_SCALE_SCENARIOS.md`](docs/AURA_METRICS_AND_SCALE_SCENARIOS.md)
- Paper IX v2.0

Large adoption, energy, economic, and societal arithmetic is intentionally kept in those deeper documents rather than presented as current README benchmark evidence.

---

# 13. Licensing and status

AuraOS source code is released under the **GNU Affero General Public License v3.0** unless a file or bundled dependency states otherwise.

Third-party components retain their own terms. Community-owned language recordings, local dialect lexicons, teaching materials, corrections, private or ceremonial knowledge, learner data, and contributor-consent records are separately governed from the general AuraOS software licence.

AuraOS is active R&D.

Important work remains around:

- the numbered PR program;
- production hardening;
- independent benchmarking;
- arbitrary-repository onboarding;
- confidential capability execution;
- network authentication/authorization;
- provenance and standards integration;
- economic/governance mechanisms;
- downstream Paper IX embodiments.

The ambition can be large.

The acceptance criterion can remain pleasantly boring:

> **Show the evidence.**

---

## Contact

**Founder:** Dallas Courchene  
**Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)  
**Email:** aura.os.q@gmail.com

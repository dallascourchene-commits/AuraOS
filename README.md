# AuraOS

## Aura — Augmented Universal Reasoning Architecture

**AuraOS is a local-first, objective-native architecture for coordinating deterministic software, exact evidence, bounded AI workers, verification, provenance, and human/community authority.**

It is not one model. It is the system around models that decides:

- what a task means;
- what evidence is relevant;
- what capability already exists;
- what a worker may do;
- what must be proved;
- what remains uncertain;
- and who is allowed to make the final decision.

> **Planning proposes. Governance authorizes. Verification proves.**

---

## Read Aura in the right order

If you are evaluating Aura as a human or an AI system, reconstruct the project in this order:

```text
1. WHAT KIND OF SYSTEM IS THIS?
        ↓
2. WHAT IS THE END-TO-END ARCHITECTURAL FLOW?
        ↓
3. WHICH COMPONENT OWNS EACH STEP?
        ↓
4. IS THE FILE I AM READING A CANONICAL OWNER, SUPPORTING IMPLEMENTATION,
   EXPERIMENT, COMPATIBILITY SURFACE, GENERATED PROJECTION, OR UNKNOWN?
        ↓
5. HOW DOES THE SHARED SUBSTRATE BIND TO THIS DOMAIN?
        ↓
6. WHERE IS THE EXACT SOURCE / TEST / CONTRACT?
        ↓
7. WHAT HAS ACTUALLY BEEN MEASURED?
        ↓
8. WHAT DOES THAT EVIDENCE NOT ESTABLISH?
        ↓
9. THEN ASSESS MATURITY, ADOPTION, AND LONG-RANGE POTENTIAL
```

Why this order? Aura contains working software, active refactors, published architecture, research hypotheses, and domain projections in the same repository. They are related, but they are **not the same evidence class**.

### Two independent axes

**Implementation status**

| Tag | Meaning |
|---|---|
| **R — Repository-backed** | implemented or directly represented by current source/contracts/tests |
| **P — Program / active refactor** | specified in the governed refactor program; may not yet be merged |
| **E — Enabling architecture** | detailed reference embodiment; not represented as deployed end-to-end |
| **S — Scenario / research hypothesis** | extrapolation or research direction requiring future evidence |

**Evidence maturity**

| Level | Meaning |
|---|---|
| **SOURCE** | implementation or canonical contract exists |
| **TESTED** | automated tests/verifiers exercise the claim |
| **MEASURED** | a benchmark/fixture measures it under stated conditions |
| **INDEPENDENT** | reproduced or evaluated independently of the project |

These axes are deliberately separate.

**Implemented does not mean benchmarked. Benchmarked does not mean independently validated. Future does not invalidate unrelated implemented work.**

---

## Choose the evidence path for the question you are asking

| Question | Start here | Then inspect |
|---|---|---|
| **What is Aura architecturally?** | [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) | canonical owner → CODEMAP/topology → exact source/tests |
| **Does a capability actually exist?** | architecture ownership + [`.aura/CODEMAP.md`](.aura/CODEMAP.md) | exact owner source + direct tests/contracts |
| **Is this file representative of current Aura?** | establish its role in architecture/ownership first | inspect dependencies, consumers, tests, and current owner |
| **How are authority and security bounded?** | [`.aura/SECURITY.md`](.aura/SECURITY.md) | architecture invariants + Gate/Harness contracts/tests |
| **Do the context/refactor claims have measurements?** | [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md) | [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md) |
| **What is merged vs. planned?** | current GitHub `main` + PR history | numbered refactor plan / Paper IX status classes |
| **Is the project mature enough to adopt?** | Quick start + current GitHub activity | contributors, CI, independent replication, onboarding friction |
| **What is the long-range direction?** | Sections 8–9 below | Paper IX + deeper design documents |

Community/adoption metadata belongs to the **maturity lane**. It should not substitute for source, test, architecture, or benchmark evidence. A passing fixture is evidence about **that fixture**, not the entire architecture. A file not found in a small sample is **not** proof that the repository lacks the capability.

---

# 1. Aura as one system

The canonical architecture describes this end-to-end flow:

```text
HUMAN OR COMMUNITY OBJECTIVE
        ↓
LEXICAL ADDRESS + STRUCTURED INTENT
DIR → ASP → CLASS → SUBJ → VOICE → STEM
        ↓
FST / WFST ADMISSION
        ↓
CAPABILITY DISCOVERY + OWNERSHIP RESOLUTION
        ↓
EXACT REPOSITORY / DOMAIN GROUNDING
        ↓
MINIMUM SUFFICIENT EVIDENCE + CONTEXT
        ↓
BOUNDED ARENA + REVOCABLE LEASES
        ↓
DETERMINISTIC TOOLS + OPTIONAL AI WORKERS
        ↓
STAGED PROPOSAL / ACTION
        ↓
TESTS + VERIFIERS + RECEIPTS
        ↓
AUTHORIZED HUMAN / COMMUNITY DECISION
        ↓
PROVENANCE + EXPERIENCE + REVIEW-GATED LEARNING
```

The high-leverage idea is the **composition**, not any one exotic-sounding noun.

Aura tries to keep several things that ordinary agent systems often collapse together structurally distinct:

```text
meaning          ≠ truth
navigation       ≠ source authority
planning         ≠ execution
execution        ≠ verification
verification     ≠ promotion
evidence         ≠ permission
experience       ≠ policy
model output     ≠ governance
temporary state  ≠ durable authority
```

This is why Aura has more architectural boundaries than a simple coding-agent wrapper.

## One substrate, many domain bindings

Aura is **not** attempting to build a separate operating system from scratch for Coding, Construction, Civic, Financial, Spatial, scientific, and future domains.

The generalization thesis is narrower and testable:

> **Different domains repeatedly need some of the same underlying operations — objective structuring, capability discovery, exact evidence, bounded execution, verification, provenance, and governed disposition — while retaining domain-specific evidence, authority, tools, and lifecycle rules.**

```text
SHARED AURA SUBSTRATE
objective
→ structured intent
→ capability discovery
→ evidence grounding
→ bounded Arena
→ verification / receipts
→ authorized disposition
→ provenance / reusable experience
            │
      ┌─────┼──────────┬─────────┐
      ▼     ▼          ▼         ▼
   CODING  SPATIAL  CONSTRUCTION  CIVIC ...
      │     │          │         │
      └── domain-specific bindings ──
```

A new domain should therefore look like:

```text
NEW DOMAIN
=
SHARED SUBSTRATE
+ DOMAIN-SPECIFIC EVIDENCE
+ DOMAIN-SPECIFIC AUTHORITY
+ DOMAIN-SPECIFIC CAPABILITIES
+ DOMAIN-SPECIFIC LIFECYCLE / ACCEPTANCE RULES
```

This is **not** a claim that one generic algorithm solves every domain. It is a claim that the common governance, evidence, composition, and lifecycle machinery should not be rebuilt every time the domain changes.

The domain Arenas are therefore useful as **stress tests of substrate generality**. If each new Arena requires another parallel truth, policy, memory, verification, or authority system, the architecture has failed its own convergence goal.

---

# 2. The components that matter first

You do not need to learn every Aura term before understanding the architecture. Start with these roles.

| Aura role | Conventional approximation | What it contributes | What it cannot become |
|---|---|---|---|
| **FST / WFST intent grammar** | structured intent parser / admission grammar | turns open-ended requests into constrained machine structure | truth or mutation authority |
| **CODEMAP / topology** | repository index + dependency/symbol graph | tells workers where relevant code and relationships live | canonical source |
| **Capability Connectome / Resolver** | capability/dependency graph + reuse resolver | asks what already exists before inventing another implementation | proof by similarity |
| **Atlas / Compass / Relational Synthesis** | architecture relationship analysis | exposes existing, missing, overlapping, stale, prohibited, or implied relationships | permission to wire them automatically |
| **Arena** | bounded task/runtime environment | assembles objective, evidence, tools, workers, permissions, lifecycle | permanent authority by default |
| **Council V3** | selective multi-critic planner | invokes reasoning/critic lanes justified by task structure and risk | source mutation authority |
| **Sliced Surgeon** | bounded implementation worker | edits exact authorized source slices against focused obligations | architecture redefinition outside scope |
| **Forge + Gate** | governed orchestrator + policy/identity/lease envelope | coordinates work under explicit identity, egress, policy, and effect constraints | automatic merge/release authority |
| **Waboose** | graph-guided code review | localizes and corroborates findings against exact source | self-confirming or self-patching reviewer |
| **Attempt Archive / Crucible** | failure ledger + review-gated learning pipeline | preserves what worked/failed and proposes reusable lessons | silent policy or grammar promotion |
| **ARCH / runtime harnesses** | long-horizon refactor continuity and proof system | binds exact HEAD, scope, failed attempts, review, proof, cleanup, and terminal state | autonomous merge authority |

Everything else should be understood by asking where it fits in this flow and which canonical owner it depends on.

## Before generalizing from a file

Aura is old enough to contain active owners, supporting modules, experiments, compatibility surfaces, generated projections, and historical lineage in the same tree.

Before using one file to characterize an architecture-wide mechanism, establish its role:

| Evaluation role | Meaning |
|---|---|
| **CANONICAL OWNER** | current source/contract that owns the capability or invariant |
| **ACTIVE SUPPORT** | current implementation used by a canonical owner |
| **COMPATIBILITY** | retained to preserve an older interface/path |
| **EXPERIMENTAL / RESEARCH** | prototype or hypothesis-bearing implementation |
| **HISTORICAL / LINEAGE** | useful for development history; not sufficient evidence of current architecture |
| **GENERATED PROJECTION** | CODEMAP/topology/report/navigation output; not source authority |
| **UNKNOWN** | role not yet established; do not propagate conclusions architecture-wide |

These labels are an **evaluation lens**, not a new authority database. The current architecture, exact source relationships, tests, and contracts determine the real status.

In particular:

```text
interesting / weak / obsolete local implementation
        ≠
complete implementation of the architecture that may contain, replace,
constrain, or no longer depend on that file
```

A local finding becomes architecture-wide only when an explicit ownership or dependency relationship carries it.

---

# 3. Canonical truth and authority

Aura's architecture defines a strict evidence order.

When sources disagree, prefer:

1. exact current source, schemas, contracts, and repository state;
2. exact tests, verifiers, replay, and tamper evidence;
3. healthy current CODEMAP/topology facts;
4. exact snapshots, sidecars, ledgers, event chains, and content-addressed records;
5. manifests, leases, consent, relational-authority, and boundary contracts;
6. current canonical subsystem documentation;
7. summaries, generated reports, screenshots, research sidecars, and historical artifacts.

Advisory cognition can discover, rank, compress, explain, or remember.

It cannot silently create authority.

Representative invariants:

```yaml
planning_proposes: true
governance_authorizes: true
verification_proves: true

patch_authority: exact_source_spans_and_hashes_only

vsa_patch_authority: false
visual_topology_patch_authority: false
external_model_action_authority: false
crystallization_patch_authority: false

automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false

human_review_required: true
```

Unknown, stale, malformed, expired, ambiguous, conflicting, or unauthorized consequential operations are intended to fail closed.

Canonical references:

- [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md)
- [`.aura/SECURITY.md`](.aura/SECURITY.md)
- [`docs/AURA_ARCH_V2_3_HARNESS.md`](docs/AURA_ARCH_V2_3_HARNESS.md)

---

# 4. What exists now — and what the current refactor is doing

AuraOS is working research software, not only a roadmap.

The repository contains substantial source, tests, schemas, generated topology, governed coding/runtime surfaces, provenance/continuity machinery, and domain bindings. For current inventory counts and symbol/file navigation, use [`.aura/CODEMAP.md`](.aura/CODEMAP.md) rather than treating raw repository size as an architectural claim.

## The current direction is convergence, not feature accumulation

Aura accumulated capabilities quickly. The current refactor program is intended to make those capabilities easier to reason about and reuse by:

- identifying canonical owners;
- removing or refusing duplicate truth/authority/policy planes;
- reconstructing projects source-first;
- selecting task-conditioned capability/dependency closures;
- hydrating only the evidence needed for the active objective;
- preserving failed attempts and proof lineage without carrying full transcripts;
- making reusable capability contracts explicit;
- and keeping human/governance disposition outside model authority.

The target is:

```text
many accumulated mechanisms
        ↓
canonical ownership
        ↓
explicit relationships / invariants
        ↓
task-conditioned project shape
        ↓
minimum sufficient context
        ↓
bounded execution
        ↓
proof + reusable verified capability
```

A successful refactor should therefore make Aura **smaller in active reasoning surface even when the repository contains more accumulated capability**.

## Merged refactor foundation

### PR #255 — intent-native spatial workspace contracts

PR1 separated:

```text
PARSE → BIND → ADMIT
```

Its guarded final verification reported **46/46 focused tests passed**, plus compilation, schema validation, fatal Ruff checks, diff checks, and generated-map synchronization.

[#255](https://github.com/dallascourchene-commits/AuraOS/pull/255)

### PR #269 — verified ephemeral workspace lifecycle

PR2 preserved V1 while adding a separately verified interactive Workspace V2 lifecycle.

Its documented gate included:

- **52 focused PR2 tests**;
- **81 retained V1 / Phase-0 / PR1 tests**;
- compilation and fatal Ruff checks;
- Draft 2020-12 schema validation;
- identity/scope checks;
- hostile-callback, cancellation, expiry, identity, memory-budget, race, and cleanup hardening.

[#269](https://github.com/dallascourchene-commits/AuraOS/pull/269)

PR3 onward continues the broader numbered convergence program. Use GitHub for current live PR state.

---

# 5. The coding/refactor path

For software engineering, Aura's architecture can be reduced to this practical sequence:

```text
OBJECTIVE
    ↓
STRUCTURE THE INTENT
    ↓
LOCATE EXISTING CAPABILITIES + OWNERS
    ↓
BUILD THE MINIMUM RELEVANT SOURCE / TEST CLOSURE
    ↓
PLAN WITH BOUNDED CRITICS
    ↓
PATCH EXACT AUTHORIZED SOURCE
    ↓
TEST LOCAL EFFECT
    ↓
TEST AFFECTED DEPENDENCY / INVARIANT CLOSURE
    ↓
INDEPENDENT REVIEW
    ↓
HUMAN DISPOSITION
    ↓
PRESERVE RECEIPTS + FAILED / SUCCESSFUL EXPERIENCE
```

The important consequence is:

> **A reviewer may notice a local defect without understanding the repository-level repair.**

Aura's Harness exists partly to prevent repeated loops like:

```text
reviewer finds X
→ patch X
→ reviewer finds Y
→ patch Y
→ reviewer finds Z
```

when X, Y, and Z are symptoms of one deeper owner/invariant problem.

The preferred model is:

```text
local finding
→ exact reproduction
→ canonical owner
→ relevant invariant
→ dependency closure
→ relevant prior failures
→ root cause
→ bounded patch
→ proof
```

This is one of the highest-leverage places where Aura is currently being refined.

---

# 6. Evidence: what has actually been measured

This README centers quantitative engineering claims on two current benchmark documents.

Older exploratory measurements remain historical evidence, but are not stacked into one headline percentage.

## 6.1 Architect Consolidation Benchmark — context localization

Source: [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)

**Status:** single-session assisted planning pilot.  
**Token values:** deterministic proxy, not tokenizer/provider billing.  
See the benchmark document for the exact recorded fixture/model metadata.

| Arm | Calls | Input proxy | Output proxy | Total proxy | Grounded-plan quality |
|---|---:|---:|---:|---:|---:|
| Broad-context planner | 1 | 130,485 | 1,169 | **131,654** | **0.9550** |
| Aura-slice planner | 1 | 13,201 | 1,667 | **14,868** | **0.9607** |
| Aura Architect Council | 12 | 90,020 | 4,121 | **94,141** | **0.9458** |

Measured comparison of the single-planner arms:

- **89.88% lower input-token proxy**;
- **88.71% lower total-token proxy**;
- grounded-plan quality changed by **+0.0057**.

The Council used less total proxy than the broad planner but scored lower than the single sliced planner on the benchmark's deterministic plan-quality measure.

That negative result is intentionally preserved.

### Supports

On this fixture, Aura's localization machinery produced a much smaller exact-slice planning packet without measured loss in the grounded-plan score.

### Does not establish

- general model superiority;
- provider-billed cost savings;
- universal 88.71% reduction;
- production refactor success;
- energy or carbon savings;
- Council superiority.

---

## 6.2 Executable Refactor Code-Quality Benchmark

Source: [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)

| Refactoring method | Calls | Total proxy | Visible | Hidden | Regression | Disposition | Observed | Benchmark |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Broad-context implementer | 1 | **131,654** | 3/3 | 1/3 | 2/2 | `PARTIAL` | 80.34 | 78.33 |
| Aura-slice Surgeon | 1 | **14,868** | 3/3 | 2/3 | 2/2 | `PARTIAL` | 88.89 | 86.67 |
| Council V2 + Surgeon | 18 | **158,545** | 3/3 | 3/3 | 2/2 | `ACCEPTED` | 100.00 | 97.50 |
| **Selective Council V3 + Surgeon** | **12** | **106,494** | **3/3** | **3/3** | **2/2** | **`ACCEPTED`** | **100.00** | **97.50** |

On the frozen fixture, Selective Council V3 preserved the accepted V2 result while using:

- **33.33% fewer total model calls**;
- **40.00% fewer critic reports**;
- **33.58% lower input-token proxy**;
- **32.83% lower total-token proxy**;
- the same substantive selected plan;
- the same executable patch digest;
- the same final quality scores and `ACCEPTED` disposition.

### What remains to prove

The benchmark itself calls for:

- independent provider calls;
- tokenizer-exact/provider-billed usage;
- repeated trials;
- broader task suites;
- real AuraOS tasks in isolated worktrees;
- independently authored hidden tests;
- blinded maintainability review;
- variance and confidence intervals.

---

# 7. How to interpret absence, limitation, and failure

This matters in a repository this large.

Do not collapse these states:

```text
NOT_INSPECTED
PARTIALLY_SEARCHED
SEARCHED_AND_NOT_FOUND
CANONICALLY_ABSENT
FUTURE_DECLARED
IMPLEMENTED_BUT_UNTESTED
TESTED_BUT_UNMEASURED
MEASURED_BUT_NOT_INDEPENDENTLY_REPLICATED
```

Likewise:

```text
local limitation
    ≠
global architecture failure
```

unless an explicit dependency carries that limitation.

And:

```text
local success
    ≠
global architecture proof
```

unless an explicit dependency carries that evidence.

This is not special pleading for Aura. It is a normal requirement for reasoning about any large system.

---

# 8. What Aura's future actually depends on

Aura's longer-range direction is not "add every feature."

It is **reuse before unnecessary regeneration**.

A useful capability can be expensive the first time:

```text
discover
+ implement
+ integrate
+ secure
+ test
+ verify
+ document
= high first-use cost
```

If that capability is preserved with a clear contract, evidence, provenance, and authority boundary, later objectives should increasingly pay only for the **novel delta**:

```text
OBJECTIVE A → build + verify X

OBJECTIVE B → reuse X + build/verify Y

OBJECTIVE C → reuse X + Y + build/verify Z
```

> **We do not reinvent the transistor every time we build a phone. Software agents should not need to rediscover every verified primitive every time someone opens a new chat.**

This is the architecture's compute/capability-amortization thesis:

```text
objective
→ discover applicable existing capability
→ compose only what is needed
→ adapt the genuinely novel delta
→ verify in the new context
→ execute inside a bounded Arena
→ preserve provenance / attribution
→ dissolve temporary authority
→ retain reusable verified capability
```

The potential of Coding, Construction, Civic, Spatial, scientific, and other Arenas therefore does **not** depend on one maintainer manually finishing a separate giant product for every field.

It depends on whether:

1. the shared substrate really is reusable;
2. domain-specific bindings can remain narrow;
3. canonical capabilities can be discovered rather than reinvented;
4. evidence and limitations survive reuse;
5. contributors can add primitives without creating parallel authority planes;
6. verification cost falls as proven capability accumulates.

If those conditions fail, the generalization thesis should be rejected or narrowed.

If they hold, then each verified capability can reduce the amount of new reasoning, code, integration, and testing required by later objectives.

This is the path toward Developer / Architecture Arenas, reusable capability contracts, recipes, Capability Commons, scientific/domain Arenas, Places/spatial projections, and future provenance-aware economic mechanisms.

These are not all equally implemented today. Use the R/P/E/S and evidence-maturity classes.

---

# 9. Developer call to action

Aura is not supposed to reach its broader potential by one person implementing every downstream domain.

The contribution model is:

> **Bring a capability you already understand deeply. Help make its contract, evidence, boundaries, provenance, and reuse explicit.**

Useful contributions can include:

- deterministic algorithms;
- parsers and compilers;
- verifiers;
- routing/localization methods;
- local-model tools;
- repository-analysis techniques;
- security primitives;
- renderers;
- scientific workflows;
- domain engines;
- evaluation harnesses;
- or other reusable software capabilities.

The intended path is:

```text
YOUR EXISTING CAPABILITY
        ↓
ESTABLISH WHAT IT ACTUALLY DOES / DOES NOT DO
        ↓
IDENTIFY CANONICAL CONTRACT + DEPENDENCIES
        ↓
MAP IT INTO AURA'S CAPABILITY / RELATIONSHIP GRAPH
        ↓
GROUND IT AGAINST SOURCE + TESTS
        ↓
RUN IT INSIDE THE APPROPRIATE BOUNDED ARENA / HARNESS
        ↓
MEASURE THE NOVEL VALUE
        ↓
PRESERVE PROVENANCE + ATTRIBUTION
        ↓
MAKE THE VERIFIED PRIMITIVE DISCOVERABLE AND REUSABLE
```

The immediate opportunity is technical: **turn isolated capability into reusable, evidence-bearing infrastructure**.

The longer-range economic thesis is that verified capability should be able to retain provenance and eventually participate in a **Capability Commons / Extension Economy**, so reuse can preserve attribution and potentially support compensation rather than forcing developers to repeatedly resell the same labor.

That economic layer is **not a deployed real-money system, and no contribution carries a profit guarantee**.

Early contributors can nevertheless help define the interoperability, evidence, provenance, rights, and lifecycle rules such a system would need.

In short:

> **Do not come merely to add another feature. Bring the thing you already know how to build, establish where it belongs, prove it, and help make it reusable.**

---

# 10. Quick start

## Requirements

- Python >= 3.10
- Git
- Linux or Android/Termux
- dependencies from `requirements.txt`

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

> **A full zero-friction governed run against an arbitrary foreign repository remains P-class work.**

The architecture can inspect and orient around supplied repository roots; the complete arbitrary-repository governed execution path is still being hardened.

---

# 11. Origin and why the architecture looks this way

Aura began as a locally controlled Anishinaabemowin learning system designed for constrained hardware and community control.

That origin imposed practical pressures:

- local operation;
- compact structured intent;
- data minimization;
- explicit provenance;
- bounded external-provider access;
- revocable authority;
- human/community governance.

The polysynthetic-language inspiration should be read narrowly.

Aura does **not** claim that its six-slot software grammar is a complete model of Anishinaabemowin or Dene/Athabaskan grammar.

The engineering lesson was:

> **Dense meaning can be composed from constrained relationships rather than represented as an unstructured bag of words.**

In engineering terms, Aura increasingly applies that lesson as **grammar before content**: establish the roles, relationships, constraints, authority, and evidence state that make an interpretation valid, then hydrate the content needed for the objective.

That principle later became useful far beyond language learning: repository navigation, capability composition, bounded context, Arena assembly, task-specific execution, and the current convergence/refactor work.

Further background:

- [`docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md`](docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md)
- [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md)

---

# 12. Research, prior art, and external calibration

Aura maintains a dated public research record and a research-convergence record.

Nine defensive publications cover claims N1–N100.

Zenodo provides dated public records. It is **not peer review**.

External papers can:

- support a design pressure;
- independently converge on a related mechanism;
- contradict an assumption;
- expose a missing evaluation;
- or provide a stronger baseline.

They do **not** prove Aura's implementation.

Detailed chronology and provenance:

- [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md)
- [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md)

Current benchmark calibration also references independent work on selective repository/context reduction such as FastContext and SWE-Pruner. Those comparisons are mechanism-level context, not an Aura leaderboard.

---

# 13. What is not claimed

AuraOS is active research software.

This README does **not** claim:

- that every documented Arena or Paper IX embodiment is deployed;
- that arbitrary repositories already have zero-friction governed onboarding;
- that Aura can autonomously merge consequential changes;
- that model output becomes correct because Aura routed it;
- that one benchmark establishes general superiority;
- that token-proxy savings equal provider billing;
- that token savings automatically imply energy/carbon/water savings;
- that CODEMAP, VSA/HDC, or visual topology are canonical truth;
- that research convergence proves implementation or universal priority;
- that current fixtures substitute for independent multi-provider trials;
- that a real-money capability marketplace is deployed;
- that future scientific, civic, spatial, economic, or institutional embodiments are production systems.

A declared limitation bounds a claim.

It does not automatically erase unrelated source-backed evidence.

---

# 14. How to challenge Aura

Useful questions are better than generic praise or dismissal.

| Area | Useful hostile question | Start here |
|---|---|---|
| **Context localization** | Does the slice omit answer-determining evidence on harder tasks? | Architect Consolidation benchmark |
| **Refactor quality** | Does the Council/Surgeon advantage survive independent repositories and hidden tests? | Executable Refactor benchmark |
| **Architecture integrity** | Can a local patch pass tests while violating a higher-level invariant? | architecture + CODEMAP + subsystem tests |
| **Authority** | Can a worker escape leases, forge identity, or convert model output into permission? | security + Gate + Harness |
| **Continuity** | Does the Harness preserve root cause and failed attempts without transcript bloat? | ARCH / runtime harness |
| **Provenance** | Can stale/tampered evidence be promoted? | exact-head / receipt / provenance owners |
| **Research chronology** | Does the dated implementation really predate the cited paper mechanism? | convergence doc + Git history |
| **Adoption** | Can a new developer contribute a useful capability without founder hand-holding? | Quick start + contributor workflow |

The strongest future result for Aura will not be a model saying it is impressive.

It will be an outsider reproducing a claim, breaking something important, or contributing a reusable capability that survives independent verification.

---

# 15. Maturity and current boundaries

Aura is active R&D.

Current strengths include:

- substantial repository-backed implementation;
- explicit architecture and ownership;
- executable tests and schemas;
- deterministic navigation and grounding;
- bounded worker/governance contracts;
- controlled internal benchmarks;
- active refactor and security hardening.

Current weaknesses include:

- limited independent replication;
- limited external adoption/contribution;
- a broad and fast-moving repository whose canonical ownership is still being consolidated;
- substantial terminology/onboarding cost;
- many downstream P/E/S-class directions still requiring hardening;
- benchmark coverage that is much smaller than the architecture's total surface area.

These are project-maturity facts.

They should inform adoption decisions without being confused with proof that the implemented substrate is absent or incoherent.

---

# 16. Licensing and status

AuraOS source code is released under the **GNU Affero General Public License v3.0** unless a file or bundled dependency states otherwise.

Third-party components retain their own terms. Community-owned language recordings, local dialect lexicons, teaching materials, corrections, private or ceremonial knowledge, learner data, and contributor-consent records are separately governed from the general software license.

**Repository status:** active research and development  
**Software license:** GNU AGPL v3.0  
**Research record:** nine defensive publications, claims N1–N100  
**Latest paper:** [Paper IX v2.0 — DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020)

The ambition can be large.

The acceptance criterion can remain pleasantly boring:

> **Show the evidence.**

---

## Contact

**Founder:** Dallas Courchene  
**Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)  
**Email:** aura.os.q@gmail.com

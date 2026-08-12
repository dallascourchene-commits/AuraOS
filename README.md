# AuraOS

<!-- AURA_AI_ENTRY_START -->

> [!IMPORTANT]
> ## AI AGENTS — START HERE: read the L0 Activation Packet first
>
> Before reading individual Aura papers, scanning the repository, or forming architecture-wide conclusions, read **[`AURA_L0_ACTIVATION_PACKET.md`](docs/prior_art/paper_x_v1.1/AURA_L0_ACTIVATION_PACKET.md)**.
>
> The packet is Aura's compact orientation/compiler seed: it gives the primitives for relational-world compilation, L0→L4 resolution, movement, signed negative space, guarded reachability, authority boundaries, exact-source descent, and provenance. **It is not canonical truth, authority, or a substitute for source.** Its job is to let a worker hold the generative grammar first, then understand the papers and implementation as source-resolvable instances of that grammar rather than as disconnected components.
>
> **Entry order for AI workers:**
> 1. Read the **L0 Activation Packet**.
> 2. Read **[Paper X v1.1 — N101–N124](docs/prior_art/paper_x_v1.1/AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf)** for the full architecture, evidence boundaries, falsifiers, and declarations.
> 3. Use `.aura/CODEMAP.json`, `.aura/CODEMAP.md`, and `.aura/SOURCE_ANCHORS.md` to navigate; do not broad-scan when a source-resolvable route exists.
> 4. Descend to exact source/current evidence only when uncertainty, contradiction, consequence, freshness, authority, or falsification earns deeper resolution.
> 5. Preserve **projection ≠ owner**, **route ≠ authority**, **similarity ≠ evidence**, **receipt ≠ truth**, and **Click/comprehension ≠ authority**.
> 6. Preserve provenance for consequential transitions; leave unrelated branches cold but recoverable.
>
> **Published Paper X v1.1:** DOI [`10.5281/zenodo.21895712`](https://doi.org/10.5281/zenodo.21895712) · [Evidence addendum](docs/prior_art/paper_x_v1.1/PAPER_X_V1.1_EVIDENCE_ADDENDUM.md) · [Provenance manifest](docs/prior_art/paper_x_v1.1/PROVENANCE_MANIFEST.csv)

<!-- AURA_AI_ENTRY_END -->

## Aura — Augmented Universal Reasoning Architecture

**AuraOS is a local-first, objective-native architecture for turning human/community objectives into bounded, evidence-bearing, verifiable work without giving probabilistic models silent control over truth or authority.**

Aura is not one model. She is the system around models and deterministic tools that decides:

```text
what does the objective mean?
        ↓
what capability already exists?
        ↓
what exact evidence is relevant?
        ↓
what worker may act, under what lease?
        ↓
what must be proved?
        ↓
who may make the consequential decision?
```

> **Planning proposes. Governance authorizes. Verification proves.**

---

# Read Aura before judging Aura

A fresh human or AI evaluator should reconstruct the project in this order:

```text
1. SYSTEM PURPOSE
        ↓
2. ARCHITECTURAL FLOW
        ↓
3. MECHANISM GENEALOGY — why each major piece exists
        ↓
4. PROVENANCE — adapted, internally synthesized, mixed, or later convergence
        ↓
5. CURRENT CANONICAL OWNER / FUNCTION
        ↓
6. EXACT SOURCE + TESTS
        ↓
7. MEASURED EVIDENCE + NEGATIVE RESULTS
        ↓
8. LIMITATIONS / WHAT THE EVIDENCE DOES NOT ESTABLISH
        ↓
9. DOMAIN BINDINGS + FUTURE POTENTIAL
        ↓
10. MATURITY / ADOPTION ASSESSMENT
```

**Do not classify Aura from one source file, one historical prototype, one paper, one generated map, or one benchmark.** Aura evolved quickly; older experiments and compatibility surfaces coexist with newer canonical descendants.

### Three independent labels

**Implementation status**

| Tag | Meaning |
|---|---|
| **R** | repository-backed current implementation / contract |
| **P** | active governed refactor or program work |
| **E** | enabling architecture/reference embodiment, not deployed end-to-end |
| **S** | scenario or research hypothesis |

**Evidence maturity**

```text
SOURCE → TESTED → MEASURED → INDEPENDENTLY REPLICATED
```

**Mechanism provenance**

| Label | Meaning |
|---|---|
| `ADAPTED_FROM` / `INSPIRED_BY` | outside work explicitly informed Aura |
| `PRIOR_EXTERNAL_RESEARCH` | literature predates Aura and supports the design pressure |
| `AURA_INTERNAL_SYNTHESIS` | mechanism emerged by combining/refining earlier Aura mechanisms |
| `INDEPENDENT_DERIVATION` | development record supports an Aura-origin mechanism without the later source informing it |
| `AURA_MECHANISM_PREDATES_PAPER` | dated public Aura evidence predates the later paper's first public submission |
| `INDEPENDENT_CONVERGENCE` | later independent work reaches/supports an overlapping pressure |
| `MIXED_LINEAGE` | Aura core existed, later refinements incorporated external ideas |
| `PROVENANCE_UNRESOLVED` | evidence is insufficient; do not guess |

These labels do different jobs. A mechanism can be `R + TESTED + ADAPTED_FROM`, or `R + MEASURED + AURA_MECHANISM_PREDATES_PAPER`.

---

# 1. Architecture at a glance

```text
HUMAN / COMMUNITY OBJECTIVE
        ↓
STRUCTURED INTENT
DIR → ASP → CLASS → SUBJ → VOICE → STEM
        ↓
FST / WFST ADMISSION
        ↓
CAPABILITY DISCOVERY + CANONICAL OWNERSHIP
        ↓
SOURCE-FIRST PROJECT / DOMAIN GROUNDING
        ↓
MINIMUM SUFFICIENT EVIDENCE + CONTEXT
        ↓
BOUNDED ARENA + REVOCABLE LEASES
        ↓
DETERMINISTIC TOOLS + OPTIONAL AI WORKERS
        ↓
PLAN / IMPLEMENT / REVIEW AS SEPARATE ROLES
        ↓
TESTS + VERIFIERS + RECEIPTS
        ↓
AUTHORIZED HUMAN / COMMUNITY DISPOSITION
        ↓
PROVENANCE + REVIEW-GATED REUSABLE EXPERIENCE
```

The important architecture is the **relationship among these stages**, not the names alone.

Aura deliberately refuses to collapse:

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

That separation is why Aura contains more explicit boundaries than a simple coding-agent wrapper.

---

# 2. The genealogy: each solved problem exposed the next one

Aura was not specified as a finished grand design and then implemented linearly.

The public development pattern is closer to:

```text
real problem appears
→ build / borrow smallest useful primitive
→ use it on real work
→ observe success + failure
→ expose next bottleneck
→ constrain / decompose / combine / replace
→ preserve useful capability + evidence
→ repeat
```

Some early implementations were intentionally crude, monolithic, or experimental. Their historical value is not that the first version was already sophisticated. It is that **using a primitive exposed a real failure mode and drove a more capable descendant**.

That makes chronology a graph problem:

```text
primitive
→ distributed implementation
→ specialized subsystem
→ integration with other mechanisms
→ governed/canonical descendant
```

> **Chronology follows the mechanism genealogy, not the creation date of the newest file.**

## The causal spine

| Pressure encountered | Aura evolution | Why the composition matters |
|---|---|---|
| Dense intent should not require re-expanding everything into prose | language-preservation problem → VSA/HDC + finite-state experiments → six-slot machine route → guarded FST/WFST | constrain structure before probabilistic expansion |
| The repository became too large for one prompt | direct inspection → CODEMAP → deeper topology → source-first/task-conditioned reconstruction | orient compactly, hydrate exact source second |
| Models differ in failure, price, reasoning and task skill | failover → specialization → Fusion → Model Cognome | workers become evidence-scored capabilities, not permanent authorities |
| Multiple models are useful but universal deliberation is expensive | Fusion → Architect → Council → selective critic routing | use only the diversity of intelligence justified by risk/uncertainty |
| Broad context makes implementation expensive and noisy | CODEMAP + Architect → exact source slices → Sliced Surgeon | separate architectural reasoning from bounded implementation |
| Experience is valuable but dangerous if it self-promotes | ArenaExperience → Attempt Archive → proposal-only Crucible → Waboose lessons | learning proposes; verification/governance decide whether it becomes reusable |
| A system can contain the needed parts but miss the relationship | Emergent Properties → Relational Synthesis → Atlas → Compass → Connectome/Resolver | move from component inventory to relationship/capability intelligence |
| Dynamic teams/tools need bounded lifetime and authority | liquid/modular code → Liquid Planning Arena → Ephemeral Organ/Workspace → Arena lifecycle | compile temporary capability around an objective, then revoke/dissolve it |
| AI could repair local code faster than global intent could be preserved | CODEMAP + Council + Surgeon + review history → Architecture Harness → ARCH v2.x | Aura applies its own governance philosophy to the process of building Aura |

This is the architecture a component list hides.

---

# 3. Research provenance: three time directions

Do **not** read the research record as “Aura invented everything” or “Aura copied everything.” Both are wrong.

```text
PAST RESEARCH
→ ingredients / prior art / explicit adaptations

AURA DEVELOPMENT
→ internal synthesis driven by encountered bottlenecks

LATER / EMERGING RESEARCH
→ independent convergence, corroboration, challenge, stronger baselines
```

## A. Prior work Aura explicitly adapted

Examples documented in [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md):

- **VSA/HDC** — compact binding/bundling; Aura does not claim to invent the field.
- **finite-state morphology** — inspiration for constrained intent routing; Aura's software grammar is not claimed as a complete model of Anishinaabemowin or Dene grammar.
- **OpenRouter / Fusion** — multi-provider routing/deliberation influenced Aura's Fusion lineage; Aura later placed it inside role, evidence and authority boundaries.
- **DREAM → DREAM-lite** — downstream usefulness became a bounded retrieval signal.
- **Anthropic J-space → AuraJSpace** — an internal-workspace research idea became an explicit external bounded working-set projection, without becoming truth or authority.
- **DIKWP** — purpose/provenance vocabulary, not an automatic truth engine.
- **ST3GG/GLOSSOPETRAE-related work** — compact transport/recall plus the accompanying covert-channel/security warning.

Known borrowing stays known borrowing.

## B. Internal Aura synthesis

Some mechanisms are best understood as compositions created by Aura's own previous stages.

### Council V3 / Surgeon

```text
multi-model Fusion
+
Architect role separation
+
CODEMAP localization
+
Model Cognome
+
DREAM-lite usefulness
+
JSpace bounded working set
+
exact source slicing
+
cost / risk evidence
        ↓
SELECTIVE COUNCIL V3
        ↓
SLICED SURGEON
```

Council is not patch authority. Surgeon is not architectural authority. The value is the **division of cognition, implementation and proof**.

### Governed experience

```text
ArenaExperience
→ Attempt Archive
→ Crucible
→ Waboose lessons
→ candidate reusable knowledge
→ independent verification / promotion decision
```

The rule that survived the evolution is simple:

> **Learning is not authority.**

## C. Later research converging on public Aura mechanisms

These are deliberately narrow chronology claims. A dated commit proves only that an overlapping Aura mechanism was public by that date; it does not prove Aura invented an entire field.

| Aura public lineage | Later research | Correct interpretation |
|---|---|---|
| **Liquid Planning Arena — Jun 25** | Generative Skill Composition — arXiv:2606.32025, Jun 30 | Aura's modular/objective composition substrate predates this submission; named Connectome/Resolver refinements came later. **Mixed chronology.** |
| **Connectome Jul 9 → Genome Resolver + Ephemeral Organ Jul 10** | Dynamic Agent Skills — arXiv:2607.10113, Jul 11 | later survey independently describes lifecycle-managed, verified, evolving reusable skills. Underlying skill-library research predates Aura. |
| **Ephemeral Organ Runtime — Jul 10** | CAVA — arXiv:2607.13716, Jul 15 | later work formalizes overlapping action identity, approval binding, receipts/attestation; earlier proof-carrying-action work predates Aura. **Mixed lineage.** |
| **Crucible proposal-only learning — Jul 11** | When Self-Evolution Backfires — arXiv:2608.05810, Aug 6 | later experiments show defective reusable skills can contaminate descendants and motivate pre-commit gating. **Independent convergence on the failure pressure.** |
| **State Ledger lineage — Jul 15–16** | When History Lies — arXiv:2608.06057, Aug 6 | later experiments show plausible stale history can hijack tool decisions. **Independent convergence on current-state-over-plausible-history pressure.** |
| **Selective Council V3 Jul 16 → Waboose Jul 19 → Harness Jul 21** | AgentRadio — arXiv:2607.28430, Jul 30 | later work reports benefits from clean-context long-horizon multi-agent coordination. Mechanisms differ; architectural pressure overlaps. |
| **Reusable Architecture Harness — Jul 21** | HarnessOpt-Bench — arXiv:2608.06301, Aug 6 | later work independently treats harness design as a measurable capability variable. Harness core predates this paper; some later v2.x refinements have mixed lineage with contemporary projects such as Prime. |

Full chronology and caveats: [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md).

### Evidence rule

```text
Aura source / contract
→ shows what Aura implements

Aura tests / verifiers
→ exercise properties of that implementation

Aura controlled benchmark
→ measures it under stated conditions

external research
→ corroborates, challenges or contextualizes the mechanism/design pressure

independent Aura replication
→ externally validates Aura's implementation
```

External papers do **not** prove AuraOS as a whole.

---

# 4. Exact source: function → file → current lines

Do not make an architecture-wide judgment from whichever root-level file search happens to return first.

Use [`.aura/SOURCE_ANCHORS.md`](.aura/SOURCE_ANCHORS.md) for curated current entry points into architecture-critical code, including:

- CODEMAP AST symbol extraction and incremental refresh;
- guarded WFST routing;
- Capability Connectome and path resolution;
- Relational Synthesis;
- Relationship Atlas;
- Selective Council V3;
- Architecture Harness.

Each generated anchor is:

```text
MECHANISM
→ SYMBOL
→ CODEMAP semantic_id + signature_hash
→ CURRENT FILE
→ CURRENT line / end_line
→ EXACT SOURCE
```

**Line numbers are not durable identity.** They shift as code moves.

Aura already reparses touched files in CODEMAP and regenerates symbol identity/signature/current line ranges. The new navigation sync binds the human-readable source anchors to that same refresh:

```text
source changes
→ CODEMAP refresh
→ symbol spans regenerate
→ SOURCE_ANCHORS.md regenerates
→ missing / ambiguous anchor fails closed
```

Canonical commands:

```bash
# Full navigation refresh
python scripts/aura_navigation_refresh.py --root .

# Incremental after bounded writes
python scripts/aura_navigation_refresh.py --root . --refresh path/to/changed.py tests/test_changed.py

# CI/review-style stale check
python scripts/aura_source_anchor_map.py --root . --check
```

The curated selectors live in [`.aura/source_anchor_manifest.v1.json`](.aura/source_anchor_manifest.v1.json). The generator is [`scripts/aura_source_anchor_map.py`](scripts/aura_source_anchor_map.py).

**SOURCE_ANCHORS is navigation, not a second truth plane.** Exact current source/tests/contracts remain authority.

---

# 5. Aura increasingly used Aura to build Aura

Aura's public architecture developed unusually quickly. Context matters.

The repository has been primarily founder-led, with AI systems used as bounded reasoning, implementation and review workers. As Aura matured, its own architecture increasingly participated in developing Aura:

```text
CODEMAP / topology
    localize the repository
        ↓
Architect / Fusion / Council
    reason about objective + alternatives
        ↓
Sliced Surgeon / bounded workers
    implement exact changes
        ↓
Waboose / tests / external reviewers
    challenge them
        ↓
Harness / ARCH
    preserve objective, exact HEAD, failures, proof and stop conditions
        ↓
next refactor starts from verified state, not transcript memory
```

So the combination **young repository + primarily one founder + large code surface** should not be modeled as “one person manually typed a giant architecture in two months.”

The testable question is:

> **Did the architecture create enough navigation, decomposition, model specialization, bounded implementation, review, continuity and verification leverage to accelerate its own construction without losing control of truth and authority?**

Aura's repository history is operational evidence that these mechanisms have been composed in her own engineering process. It is **not independent validation**.

Self-acceleration also has a cost: prototypes, compatibility paths, stale experiments and duplicate concepts can accumulate faster than they are consolidated. That is why the present numbered refactor is primarily a **convergence program**, not another feature-expansion wave.

```text
accumulated mechanisms
→ canonical owners
→ explicit relationships/invariants
→ task-conditioned project shape
→ minimum sufficient context
→ bounded execution
→ proof
```

A successful refactor makes Aura **smaller in active reasoning surface even if accumulated capability grows**.

---

# 6. What exists and what is measured

AuraOS is working research software, not only a roadmap.

## Merged refactor foundation

**PR #255 — Intent-native spatial workspace contracts** separated:

```text
PARSE → BIND → ADMIT
```

Its guarded final verification reported **46/46 focused tests passed**, plus compilation, schema validation, fatal Ruff checks, diff checks and generated-map synchronization.

**PR #269 — Verified Ephemeral Workspace lifecycle** preserved V1 while adding a separate interactive Workspace V2 lifecycle. A documented verification wave included **52 focused PR2 tests + 81 retained V1/Phase-0/PR1 tests**, plus hostile callback, cancellation, expiry, identity, memory-budget, race and cleanup hardening.

PR3 onward is the source-first/convergence program. Use GitHub for live PR state rather than this README as status authority.

## Current benchmark 1 — context localization

[`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md)

Single-session assisted planning fixture; deterministic token proxy, not provider billing.

| Arm | Total token proxy | Grounded-plan quality |
|---|---:|---:|
| Broad-context planner | **131,654** | **0.9550** |
| Aura-slice planner | **14,868** | **0.9607** |
| Aura Architect Council | **94,141** | **0.9458** |

Aura slice vs broad on this fixture:

- **89.88% lower input-token proxy**;
- **88.71% lower total-token proxy**;
- quality delta **+0.0057**.

The Council used less proxy than broad context but scored below the single sliced planner. **That negative result is preserved.**

This does not establish universal savings, provider billing, production success or Council superiority.

## Current benchmark 2 — executable refactor

[`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)

| Method | Calls | Total proxy | Hidden | Disposition | Benchmark score |
|---|---:|---:|---:|---|---:|
| Broad implementer | 1 | 131,654 | 1/3 | `PARTIAL` | 78.33 |
| Aura-slice Surgeon | 1 | 14,868 | 2/3 | `PARTIAL` | 86.67 |
| Council V2 + Surgeon | 18 | 158,545 | 3/3 | `ACCEPTED` | 97.50 |
| **Selective Council V3 + Surgeon** | **12** | **106,494** | **3/3** | **`ACCEPTED`** | **97.50** |

V3 vs V2 on the frozen fixture:

- **33.33% fewer model calls**;
- **40% fewer critic reports**;
- **33.58% lower input proxy**;
- **32.83% lower total proxy**;
- same substantive selected plan;
- same executable patch digest;
- same accepted disposition and final quality.

Still required: multiple independent trials, provider-exact usage, broader repositories/tasks, independently authored hidden tests, blinded maintainability review and variance/confidence intervals.

---

# 7. One substrate, many domain bindings

Aura is **not** trying to hand-build a separate operating system from scratch for Coding, Construction, Civic, Financial, Spatial, scientific and future domains.

The generalization thesis is narrower:

```text
NEW DOMAIN
=
SHARED SUBSTRATE
+ domain-specific evidence
+ domain-specific authority
+ domain-specific capabilities
+ domain-specific lifecycle / acceptance rules
```

The shared substrate repeatedly handles:

```text
objective
→ structure
→ capability discovery
→ evidence grounding
→ bounded Arena
→ verification / receipts
→ authorized disposition
→ provenance / reusable experience
```

A new Arena is therefore partly a **stress test of substrate generality**. If every new domain requires another parallel truth, memory, policy, verification or authority plane, Aura has failed her own convergence goal.

The long-range proposition is not “one algorithm solves everything.” It is:

> **Do not repay the full discovery/integration/verification cost when a proven capability already exists.**

```text
Objective A → build + verify X
Objective B → reuse X + build/verify Y
Objective C → reuse X + Y + build/verify Z
```

We do not reinvent the transistor every time we build a phone.

That is the foundation for future reusable capability contracts, Developer/Architecture Arenas, scientific/domain Arenas and the proposed Capability Commons / Extension Economy.

Those downstream economic mechanisms are **not deployed real-money infrastructure and carry no profit guarantee**.

---

# 8. Developer call to action

Aura is not supposed to reach broader potential by one founder implementing every downstream domain.

Bring a capability you understand deeply:

```text
existing algorithm / parser / verifier / router / model tool / domain engine
        ↓
establish what it actually does and does not do
        ↓
identify contract + dependencies + authority boundaries
        ↓
map it into Aura's capability / relationship graph
        ↓
ground it against source + tests
        ↓
run it through the appropriate bounded Arena / Harness
        ↓
measure the novel value
        ↓
preserve provenance + attribution
        ↓
make the verified primitive discoverable and reusable
```

The immediate opportunity is technical: **turn isolated capability into reusable evidence-bearing infrastructure**.

The future economic thesis is that reusable capability should retain provenance so contribution can eventually support attribution and compensation rather than forcing developers to repeatedly resell the same labor. That layer remains future architecture.

---

# 9. Quick start

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Refresh/verify orientation:

```bash
python scripts/aura_navigation_refresh.py --root .
python scripts/aura_source_anchor_map.py --root . --check
python -m aura_codemap_verify --compare-json .aura/CODEMAP.json
```

Common local surfaces:

```bash
python aura_human_agent_arena_server.py --repo-root . --demo
python aura_coding_arena_server.py --demo
python aura_showcase_server.py --demo-project winnipeg_pathways
```

Architecture Harness against a repository:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root /path/to/repository \
  handoff \
  --output-dir /path/outside/repository/repo-ai-handoff
```

**Boundary:** full zero-friction governed execution against an arbitrary foreign repository remains P-class work. Repository inspection/orientation exists; the generalized end-to-end mutation path is still being hardened.

---

# 10. How to challenge Aura

Useful criticism should attach to the correct claim.

| Question | Start here |
|---|---|
| Does context slicing omit answer-determining evidence? | Architect Consolidation benchmark |
| Does Council/Surgeon survive independent repos/hidden tests? | Executable Refactor benchmark |
| Does a local patch violate a higher-level invariant? | `.aura/ARCHITECTURE.md` + CODEMAP + tests |
| Can a worker escape leases or turn model output into authority? | `.aura/SECURITY.md` + Gate/Harness contracts |
| Does modern functionality really descend from the cited primitive? | evolution doc + SOURCE_ANCHORS + Git history |
| Did Aura really predate the cited later paper mechanism? | convergence doc + commit/merge history + arXiv v1 date |
| Does self-hosting actually reduce rework/context while preserving proof? | Harness receipts + controlled benchmarks + PR history |
| Can an outsider reproduce or falsify the claims? | canonical source/tests/benchmarks |

Do not collapse:

```text
NOT_INSPECTED
≠ SEARCHED_AND_NOT_FOUND
≠ CANONICALLY_ABSENT
≠ FUTURE_DECLARED

IMPLEMENTED
≠ TESTED
≠ MEASURED
≠ INDEPENDENTLY_REPLICATED

local failure
≠ architecture-wide failure

local success
≠ architecture-wide proof
```

unless an explicit dependency carries the conclusion.

---

# 11. Current boundaries

Aura is active R&D.

Strengths currently include substantial repository-backed implementation, explicit authority boundaries, deterministic navigation/grounding, executable tests/schemas, controlled benchmark fixtures and an unusually explicit provenance/refactor discipline.

Weaknesses currently include limited independent replication and external adoption, a broad and fast-moving founder-led repository whose canonical ownership is still being consolidated, significant terminology/onboarding cost, and benchmark coverage far smaller than the total architectural surface.

The short public development window is neither proof of correctness nor proof of implausibility. Aura's own development tooling helped accelerate repository work; the correct test is whether the resulting code, lineage, tests, authority boundaries and convergence discipline survive inspection.

This README does **not** claim:

- every documented Arena/Paper IX embodiment is deployed;
- arbitrary repositories already have zero-friction governed onboarding;
- Aura may autonomously merge consequential changes;
- model output becomes correct because Aura routed it;
- one benchmark establishes general superiority;
- token proxies equal provider billing or physical energy savings;
- CODEMAP, SOURCE_ANCHORS, VSA/HDC or visual topology are canonical truth;
- later research convergence proves Aura's implementation or universal novelty;
- future scientific/civic/spatial/economic embodiments are production systems;
- the proposed capability economy is deployed.

---

# 12. Deep inspection map

| Need | Canonical starting point |
|---|---|
| Architecture / authority boundaries | [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) |
| Security | [`.aura/SECURITY.md`](.aura/SECURITY.md) |
| Repository navigation | [`.aura/CODEMAP.md`](.aura/CODEMAP.md) |
| Current architecture function spans | [`.aura/SOURCE_ANCHORS.md`](.aura/SOURCE_ANCHORS.md) |
| Mechanism evolution / acknowledged influences | [`docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md`](docs/AURA_ARCHITECTURAL_EVOLUTION_AND_INFLUENCES.md) |
| Later independent convergence | [`docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md`](docs/AURA_INDEPENDENT_RESEARCH_CONVERGENCE.md) |
| Context-localization benchmark | [`docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md`](docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md) |
| Executable refactor benchmark | [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md) |
| ARCH v2.3 | [`docs/AURA_ARCH_V2_3_HARNESS.md`](docs/AURA_ARCH_V2_3_HARNESS.md) |
| Origin/continuity | [`docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md`](docs/AURA_ORIGIN_CONTINUITY_AND_INTERGENERATIONAL_VALUE.md) |

Aura's nine defensive publications provide dated public research/prior-art records through claims N1–N100. **Zenodo is a timestamped public record, not peer review.**

---

# Licensing and status

**Repository:** active research and development  
**Software:** GNU AGPL v3.0 unless a file/dependency states otherwise  
**Research record:** nine defensive publications, claims N1–N100  
**Latest paper:** [Paper IX v2.0 — DOI 10.5281/zenodo.21845020](https://doi.org/10.5281/zenodo.21845020)

Third-party components retain their licenses. Community-owned language recordings, dialect lexicons, teaching materials, corrections, private/ceremonial knowledge, learner data and contributor-consent records are separately governed from the software license.

The ambition can be large.

The acceptance criterion can remain pleasantly boring:

> **Show the evidence.**

## Contact

**Founder:** Dallas Courchene  
**Repository:** [dallascourchene-commits/AuraOS](https://github.com/dallascourchene-commits/AuraOS)  
**Email:** aura.os.q@gmail.com

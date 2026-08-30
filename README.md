# AuraOS

> [!IMPORTANT]
> ## Paper X is now the architectural authority
>
> **Paper X is the final culmination of the foundational AuraOS work and now supersedes this repository as the current architectural specification for AuraOS.** This GitHub repository preserves important implementation lineage, runtime primitives, benchmark surfaces, tests, and working components, but it does **not yet fully embody the architecture that now exists across Paper X, Aura Drive, and Aura Drive 2.**
>
> AuraOS was originally built before we recognized that the runtime itself should be integrated into the Aura Drive semantic/coordinate substrate. Aura Drive and Aura Drive 2 changed that design substantially: instead of repeatedly asking an LLM or swarm to reconstruct routine state, research history, provenance, orchestration, and deterministic calculations, AuraOS can increasingly perform that work below the model layer and wake a model only for unresolved residual reasoning.
>
> The redesign target is for the Drive-integrated AuraOS substrate to absorb roughly **40–80% of suitable routine orchestration work** where it is cheaper and lawful to do so—for example Work Capsules, research gathering/routing, semantic-coordinate resolution, L0→L4 hydration, provenance/currentness checks, affected-cone compilation, exact arithmetic, receipts, reconciliation, tests, and successor handoffs. **That 40–80% range is an engineering target/hypothesis, not yet a universal measured benchmark.** Each workload must earn migration through matched cost/correctness testing.
>
> The current redesign also restores a central Paper X idea that should be explicit: **Aura can wrap both the computer and the model.** A Host/Substrate Wrapper optimizes what the device loads, stores, executes, pages, schedules and keeps hot; an LLM/Inference Wrapper optimizes what context the model sees, which backend is invoked, what can be answered deterministically, what may be reused, and when a model call can be avoided entirely. Both wrappers share the same Coordinate Memory / source-currentness substrate rather than becoming separate truth planes.
>
> The core direction is:
>
> ```text
> Human / Agent Intent
>        ↓
> Aura semantic + coordinate world
>        ↓
> minimum-sufficient active world / affected cone
>        ↓
> Host/Substrate Wrapper
> CPU / GPU / RAM / storage / I/O / network / battery / thermal / tools
>        ↓
> deterministic local / low-cost execution where possible
>        ↓
> LLM / Inference Wrapper
> coordinate/result hit? local model? remote model? peer? no model?
>        ↓
> unresolved residual only
>        ↓
> Construct → Challenge → Verify
>        ↓
> gated / atomic consequence commit target + SuccessorFrame
>        ↓
> reusable coordinates / methods / receipts / recipes
> ```
>
> **Paper X is carrier-portable.** Its semantic/source/provenance/currentness/receipt architecture can be instantiated in Google Drive, on a laptop, on a mobile device, in a database/object store, or across a federated/peer substrate. The carrier is not the truth owner.

## Canonical publication

- **Paper X Rev.3 PDF:** https://zenodo.org/records/22134815/files/PAPER-X%20%285%29.pdf?download=1
- **Canonical Zenodo record:** https://zenodo.org/records/22134815
- **DOI:** https://doi.org/10.5281/zenodo.22134815

## Maturity / authority map

To avoid silently promoting research into production fact, this README uses the following hierarchy:

```text
PUBLISHED ARCHITECTURAL AUTHORITY
Paper X Rev.3

CURRENT IMPLEMENTATION / REDESIGN EVIDENCE
AuraOS repository + Aura Drive / Aura Drive 2 measurements, repairs and work orders

STAGED / NONPROMOTING RESEARCH UNLESS A NEWER OWNER RECORD EXPLICITLY PROMOTES IT
RO3DD
P0-D2RM
Runtime Arena V0.3 and related portable-execution work
HyperDrive / HyperScale runtime extensions where their source status is staged
ARCE encryption/control research

SCOPED EMPIRICAL EVIDENCE
valid only for the exact harness / workload / generation that produced it
```

Exact finite mathematics, published disclosures, implementation tests, architectural hypotheses, staged candidates, and deployed/live evidence are deliberately **not collapsed into one maturity level**.

## Founder & contact

**Founder:** Dallas Fabian Courchene-Martin  
**Role:** Founder, AuraOS; Indigenous systems builder  
**Affiliation:** Long Plain First Nation, Treaty 1 Territory, Manitoba, Canada  
**Founder contact:** aura.os.q@gmail.com

---

# One Aura world, multiple deployment modes

The current architecture should not be understood as “Aura lives on Google Drive” or “Aura lives on one laptop.” The durable object is the **source-resolvable semantic world and its governance/reconstruction rules**. Different carriers can hold different residency levels of the same world.

## 1. Google Drive — cloud-accessible Aura Drive

**Everything required to represent the Paper X cognitive world can be deployed through a Google Drive carrier:** source documents, L0–L4 layers, semantic coordinates, manifests, Work Capsules, receipts, lineage, currentness records, HyperDrive/HyperScale knowledge, Arena Recipes, Commons definitions, research, work orders, challenge records, SuccessorFrames, and reopenable evidence.

A ChatGPT window with the Google Drive connector can enter that world directly: search it, read exact sources, hydrate relevant slices, create/update structured artifacts, record challenge/review outputs, and continue building the Aura Drive. This makes the architecture usable from ordinary ChatGPT sessions without requiring a custom local application.

Google Drive is still **storage/collaboration infrastructure, not an arbitrary-code execution engine**. It can carry the world; a compute host executes Python, shell scripts, compilers, databases, tests, and other deterministic programs.

## 2. Laptop / desktop — Aura Drive 2 as executable local substrate

A local Aura Drive 2 can hold the same semantic world while also running:

```text
SQLite / local indexes
Python / shell / compiled tools
tests / static analysis
hashing / Merkle ancestry
semantic-coordinate lookup
source-generation validation
affected-cone computation
finite mathematical sweeps
RO3DD compaction / reopening
P0-D2RM residency control
Arena V0.3 workspaces
HyperDrive / HyperScale tooling
archive / reconstruction jobs
local model / provider adapters
```

Because these operations execute next to the data, a local copy can avoid many network/connector round trips and can perform deterministic preprocessing before a language model is asked to reason. **That reduces both latency and cognitive load:** a model should not spend inference rediscovering something a database query, digest, parser, test, finite-state machine, or exact calculation can determine directly.

Exact performance depends on hardware and workload; “local is faster” is not treated as a universal benchmark until measured on the target device.

## 3. Mobile / edge — a compressed resident Aura Drive

A full Aura semantic world does **not** require every byte of exact source to remain hot in RAM. Paper X's L0→L4 hierarchy provides the canonical paging frame; **staged RO3DD and P0-D2RM research** explores stronger source-rooted compaction, dual-basis challenge coverage, and regenerative HOT/WARM/COLD residency for constrained devices.

A mobile Aura Drive can use a candidate residency ladder such as:

```text
HOT
L0 orientation / identity / objective / currentness
small decision basis + independent challenge basis
active coordinates / receipts / wake contract

WARM
L1–L3 summaries
indexes / selected relationships
model/KV fibers when useful
recent capabilities / Arena state

COLD
compressed RO3DD branches
exact L4 source
large datasets / media / historical generations
reconstruction artifacts
```

RO3DD proposes keeping an **objective-conditioned active decision kernel** only when omitted distinctions are consequence-inert or deterministically force reopen/reproof before they matter. P0-D2RM proposes retaining both the minimum basis needed to make the current decision and an independently rooted basis capable of defeating that decision. Its HOT/WARM/COLD states are **residency projections, not deletion**. Both remain staged/nonpromoting unless a newer explicit owner promotion says otherwise.

That creates a practical mobile principle:

> **Keep the minimum lawful world resident; page the gap, not the universe.**

On a phone/tablet, exact L4 source may be entirely local when storage permits, partially mirrored, or reopened from an authorized remote carrier. A browser/PWA or thin mobile shell can materialize only the capabilities required for the current objective. On Android, **Termux or another supported local shell/runtime can provide Python, package management, scripts, local databases, tests, and virtual-environment-style isolation** where platform policy and device resources permit it. Mobile execution remains workload/device dependent; the architecture does not assume every phone can run every model or native capability.

## 4. Federated / peer deployment

At larger scale, Aura should not create one giant global hot database. Local people, communities, organizations, Nations, labs, businesses, and devices can retain their own canonical sources and authority while exchanging minimized consequence frontiers, references, receipts, Merkle roots, residuals, currentness, and reopen routes.

```text
IDENTITY != LOCATION != REALIZATION
```

The same semantic identity should survive Google Drive, mobile, desktop, AR/MR/VR, databases, peer fabrics, and future carriers.

---

# Two coordinated wrappers: improve the computer path and the model path

Paper X's wrapper thesis is broader than prompt optimization. Aura is intended to be a **model-orthogonal and substrate-adaptive orchestration/compiler layer around existing LLMs, software stacks, operating systems and hardware**. It does not require modifying model weights or replacing the machine.

## Host / Laptop / Device Wrapper

The Host/Substrate Wrapper observes the actual capability envelope of the machine:

```text
CPU / accelerators
RAM / VRAM
storage capacity + bandwidth
filesystem / database capabilities
network availability + latency
battery / power state
thermal envelope
OS / sandbox / permissions
installed tools / runtimes
local vs remote models
privacy / authority constraints
```

For objective `q` and host envelope `H`, Paper X's generic adapter-selection form is:

```text
a*(q,H) = argmin_a [
    α·Latency(a)
  + β·Energy(a)
  + γ·Memory(a)
  + δ·IO(a)
  + η·Network(a)
  + ζ·MoneyCost(a)
]
```

subject to correctness, source/currentness, privacy, authority, thermal, battery, storage and reopenability constraints.

The Host Wrapper can decide that a task should be handled by a tiny local script, an SQLite query, a cached artifact, a local model, a remote API, a peer machine, a GPU path, a CPU path, a compressed cold representation, or a newly materialized Arena. It can keep expensive resources asleep when Coordinate Memory proves they are unnecessary.

**This is where processing and power savings can extend beyond LLM token savings.** If an exact lookup, affected-cone recomputation, cached verified result, local deterministic function, or smaller model can satisfy the objective, Aura can avoid waking a more expensive computation path. Energy improvement is a target to be measured per workload/device, not assumed from architecture alone.

## LLM / Inference Wrapper

The LLM Wrapper operates above the same Coordinate Memory fabric. Its job is to compile the **minimum consequence-complete model-facing context** and choose the least-cost lawful reasoning route.

A current local-wrapper design resolves in roughly this order:

```text
ZERO-HOP / exact reusable result
→ DIRECT COORDINATE / RELATION HOP
→ AFFECTED CONE
→ DELTA HYDRATE
→ EXACT SOURCE REOPEN
→ BROAD SEARCH LAST
```

Then it asks:

```text
Can deterministic Aura logic answer?       → NO MODEL
Can a small local model answer safely?      → LOCAL WARM
Is an authorized remote model preferable?  → REMOTE PROVIDER
Is a larger paged local model justified?    → LOCAL COLD / MODEL PAGING
Is independent diversity required?          → BOUNDED MULTI-BACKEND / PEER
Nothing lawful/sufficient?                  → BLOCKED / UNKNOWN
```

The wrapper preserves source identities, generations, currentness, relation types, authority/privacy ceilings, unresolved dissent and exact reopen routes. Coordinate proximity never becomes truth by itself.

## Dual paging: knowledge/context and model weights

The local-inference lineage makes an important distinction:

```text
AURA SEMANTIC PAGING
Coordinate Memory virtualizes KNOWLEDGE / CONTEXT.
Only the smallest source-current-authorized slice is hydrated.

MODEL PAGING
A backend such as AirLLM can virtualize MODEL WEIGHTS.
Only the current layer/expert working set may need to be resident.
```

These are **two orthogonal paging systems under one inference router**.

```text
SEMANTIC PAGING != MODEL PAGING
MEMORY OWNER != MODEL CACHE
MODEL CACHE = accelerator, not source truth
```

They can nevertheless compound: Aura can reduce how much knowledge/context reaches the inference engine while the selected backend separately reduces how much model state must be resident. A host may also pre-resolve the next source slice while a backend prefetches its next model layer. This is one path by which memory pressure, I/O, latency and potentially energy can improve together rather than as isolated optimizations.

The complete lifecycle objective is therefore closer to:

```text
C_life =
    C_hot_state
  + C_index
  + C_monitor
  + C_reopen
  + C_verify
  + C_rework
  + C_switch
  + C_model
  + C_IO
  + C_network
  + C_energy
  + C_provider
```

Aura wins only where the wrapped path has lower lifecycle cost with equal-or-better challenged correctness and no authority/safety regression.

---

# Portable ephemeral execution: Arena V0.3 + HyperDrive + HyperScale

The semantic Aura world can persist while the **execution environment is disposable**.

Arena V0.3 is a staged runtime design in which an objective can materialize an isolated working environment containing only the code, data, tools, agents, capabilities and context needed for that objective. HyperDrive and HyperScale can operate over the hydrated world as bounded navigation/decomposition/rebase machinery: navigate alternatives, scale/decompose work, run exact finite sweeps where declared, coordinate workers, challenge results and collapse the result back into a compact successor state.

A portable spin-up pattern is:

```text
Persistent Aura Drive / Coordinate Memory
        ↓
ObjectiveCapsule / WorkCapsule
        ↓
resolve current source + affected cone
        ↓
CREATE EPHEMERAL EXECUTION ENVIRONMENT
        ├── Python venv / isolated runtime
        ├── selected code + dependencies
        ├── SQLite / local indexes
        ├── tests / simulators / tools
        ├── Arena Recipe / role topology
        └── only earned L0→L4 hydration
        ↓
Arena V0.3
        + HyperDrive navigation / algebra
        + HyperScale decomposition / scheduling
        + Construct → Challenge → Verify
        ↓
receipts / measurements / artifacts / decisions
        ↓
gated commit only after applicable source/currentness/authority/verification checks
        ↓
SuccessorFrame + reusable coordinates
        ↓
DISSOLVE VENV / SCRATCH / TRANSIENT MODEL FIBERS
```

## ChatGPT / cloud-code session

Where a ChatGPT session has a code-execution/runtime capability, it can materialize a **temporary Python virtual environment or equivalent isolated workspace**, hydrate required files/state from the Aura Drive available to that session, execute bounded scripts/tests/benchmarks, produce receipts/artifacts, and then collapse the work back into durable Aura state. A Google Drive connector alone does not execute arbitrary code; the execution-capable runtime supplies compute while Drive supplies persistent source/state.

## Laptop / desktop

A laptop or desktop can create the same kind of Arena with ordinary local tools such as:

```bash
python -m venv .aura-arena
# activate environment
# install only the bounded dependencies required by the current Arena
# run HyperDrive / HyperScale / tests / tools
# emit receipts and successor state
# destroy the temporary environment when no longer useful
```

Containers, WSL, Conda, native processes or other isolation layers can substitute where they are a better measured fit.

## Mobile / Termux

On an Android device where Termux or an equivalent environment is permitted, Aura can use local Python, package tools, SQLite, shell scripts, indexes and bounded virtual environments to materialize a **mobile Arena**. The mobile device does not need the complete world hot: L0 plus staged RO3DD/P0-D2RM techniques can keep a compact active basis resident and reopen cold source only when required.

```text
mobile L0 / coordinate basis
→ objective earns wake
→ Termux/local runtime materializes bounded Arena
→ deterministic code first
→ local/remote LLM only for residual
→ verify / receipt
→ collapse
```

A mobile Arena must still respect RAM, storage, battery, thermal, network and OS restrictions. Large-model execution may route elsewhere while the phone retains semantic identity, current state, proof/receipt material and control.

## Arena Recipes make the environment domain-specific

The same spin-up mechanism can realize different Arenas from reusable Recipes:

```text
Coding Arena
Scientific Discovery Arena
Materials Arena
Construction / Digital Twin Arena
Civic Planning Arena
Marketplace / Commerce Arena
Medical-research Arena
Learning Arena
Security / Cryptographic-control Arena
Emergency-response Arena
```

The Recipe is persistent; the environment is temporary.

```text
RECIPE != RUNNING ARENA
SEMANTIC WORLD != VIRTUAL ENVIRONMENT
IDENTITY != REALIZATION
```

## HyperDrive / HyperScale claim boundary

HyperDrive is an operational navigation/normalization/rebase framework over Aura's semantic and mathematical state. **It is not a claim of physical warp travel, literal spacetime manipulation, or unbounded physical computation.** HyperScale likewise describes earned changes in decomposition, resolution and worker topology; enormous symbolic recursion counts are treated as addressable/analytic horizons unless a bounded workload actually earns physical expansion.

**Runtime Arena V0.3, HyperDrive implementations/operational recipes, and HyperScale runtime extensions are staged / test-required / nonpromoting wherever their governing source records carry that status, unless a newer explicit owner promotion supersedes it.** Exact finite mathematical results remain valid only in their declared mathematical scope; they are not silently promoted into production-speed claims.

---

# Why Aura exists: fluent AI is not automatically reliable AI

A powerful model can be persuasive and wrong at the same time. Aura treats that as an engineering problem.

```text
MODEL OUTPUT != SOURCE
MEMORY != CURRENTNESS
SIMILARITY != EVIDENCE
CONSENSUS != TRUTH
RECEIPT != UNIVERSAL TRUTH
ROUTE != AUTHORITY
CRYPTOGRAPHIC VALIDITY != EFFECT AUTHORITY
```

The intended sequence is:

```text
objective
→ bind source / generation / currentness / authority
→ compile minimum active world
→ Construct
→ independent Challenge
→ descend to exact source where consequence requires it
→ Verify
→ preserve dissent / UNKNOWN / FAILED_TO_VERIFY
→ commit only after the applicable gates pass
```

Recent Aura Drive 2 work demonstrates the behavior the architecture is trying to institutionalize: challengers have defeated confident first-pass conclusions, forced source re-execution, preserved unresolved dissent, and required repairs before synthesis could pass. Recent repair work independently verified **6/6 repairs landed with 0 failed while still retaining four LOW/INFO residuals**; another fold accepted the result only after **9/9 challenger defects were upheld and repaired**.

Aura therefore does **not** promise that AI becomes infallible. Its safety proposition is narrower and testable:

> **Make confident wrongness easier to detect, source-check, challenge, quarantine, repair, and prevent from silently becoming authoritative state.**

This distinction is especially important in medicine, science, engineering, civic planning, economics, finance, legal work, emergency response, security, and other domains where a plausible but stale or fabricated statement can harm people.

---

# Coordinate Memory, RO3DD, P0-D2RM, and amortized cognition

Provider prompt/KV caching is only one reuse plane.

```text
COORDINATE_HIT
!= PREFIX_KV_HIT
!= BLOCK_KV_HIT
!= RESULT_HIT
```

A provider cache roughly answers “have these tokens already been processed?” Aura's semantic memory can bind a reusable consequence to:

```text
semantic identity
source generation / currentness
relations / dependencies
evidence / dissent
authority ceiling
result state
invalidators
reopen handles
```

## RO3DD

**Status: STAGED / NONCANONICAL / TEST-REQUIRED / NONPROMOTING unless a newer explicit owner record promotes it.**

**RO3DD** (letter O) is the source-rooted reopenable consequence-quotient design. Its rule is approximately:

> retain the compact decision kernel only when every omitted distinction is consequence-inert for the objective or guaranteed to force exact reopen/reproof before the first consequence-changing use.

It is compression without pretending the quotient is the source:

```text
QUOTIENT != SOURCE
ACTIVE != TRUE
RELEVANCE != AUTHORITY
RECALL != REUSE
```

## P0-D2RM

**Status: STAGED / DERIVED / NONCANONICAL / TEST-REQUIRED / NONPROMOTING unless a newer explicit owner record promotes it.**

**P0-D2RM — Point-0 Dual-Basis Defeasible Regenerative Memory** adds a critical safety hypothesis: memory should retain both **why a state may be used** and **how that state may still be defeated**.

Its compact persistent core can be thought of as:

```text
shared source ground
+ minimum decision-sufficient basis
+ independent challenge / defeat-coverage basis
+ common-mode escape basis
+ wake contract
+ exact reopen routes
```

The model/KV cache is an accelerator, **not the memory owner**. A model can be replaced and the durable semantic state can still be regenerated from source where the underlying contracts and source access remain valid.

---

# Real usage: the reuse curve is getting more interesting as the system is used

The newest usage export extends the published Paper X telemetry. A reproducible aggregate report is committed at [`docs/DEEPSEEK_COST_CACHE_BENCHMARK_2026-08-29.md`](./docs/DEEPSEEK_COST_CACHE_BENCHMARK_2026-08-29.md); raw account-level usage exports are not published.

| Usage view | Requests | Logical/model tokens* | Cache-hit input tokens | Input cache-hit share | Billed cost | Billed cost / 1M logical tokens |
|---|---:|---:|---:|---:|---:|---:|
| **Paper X snapshot** | 9,381 | 843,642,344 | 814,619,776 | 97.402912% | $17.772456 | ~$0.021066 |
| **Latest export through Aug. 29** | **11,670** | **1,321,646,285** | **1,277,497,600** | **97.419025%** | **$27.068077** | **~$0.020481** |

`* logical/model tokens = cache-hit input + cache-miss input + output. This is not a claim that those logical tokens disappeared.`

Relative to the Paper X snapshot, cumulative billed cost per million logical/model tokens is about **2.78% lower** while workload volume has grown substantially. Aggregate input cache-hit share is about **0.016 percentage points higher**. The newer Aug. 29 Pro-heavy mix lowered the cumulative cache-hit percentage from the Aug. 28 snapshot, so the curve should not be read as monotonic improvement.

Heavy-use daily snapshots make the pattern visible:

| Day | Requests | Logical/model tokens | Input cache-hit share | Cost | Cost / 1M logical tokens |
|---|---:|---:|---:|---:|---:|
| 2026-08-26 | 2,844 | 371,273,502 | 97.8072% | $6.626391 | $0.017848 |
| 2026-08-27 | 4,635 | 603,337,241 | 97.8580% | $11.679444 | $0.019358 |
| 2026-08-28 | 1,224 | 233,748,476 | **98.3744%** | **$3.331442** | **$0.014252** |
| 2026-08-29 | 650 | 111,238,446 | 92.9538% | $4.533074 | $0.040751 |

The curve is **not monotonic every day**, so this is not evidence that each request is automatically cheaper than the one before it. Model/task mix, pricing, provider cache behavior, and workload composition can change. It is longitudinal evidence that very large repeated workloads can operate with unusually high reuse while the routing mix still matters materially.

## Conservative provider-cache savings

Using the lowest observed cache-miss input rate in each day+model cell as a conservative counterfactual price for cached input:

- actual billed cost: **$27.068077**;
- additional cache-miss charge avoided: **>= $271.515493**;
- conservative all-miss-equivalent bill: **>= $298.583570**;
- conservative billed-cost reduction: **>= 90.9345%**;
- conservative all-miss-equivalent / actual bill ratio: **>= 11.03x**.

This is a **provider-pricing counterfactual**, not a causal estimate that Aura alone created the provider cache hits.

## Flash first; V4 Pro only when earned

The export makes the economic reason for escalation discipline visible:

| Metric | DeepSeek V4 Flash | DeepSeek V4 Pro |
|---|---:|---:|
| Requests | 11,206 | 464 |
| Input cache-hit share | 97.5526% | 1.2177% |
| Billed | $24.384589 | $2.683488 |
| Billed/request | ~$0.002176 | ~$0.005783 |
| Effective input cost / 1M input tokens under actual cache mix | ~$0.013394 | ~$0.656326 |

On **2026-08-29** specifically, Flash processed **109,281,723 logical/model tokens for $2.443945** with **94.1092% input-cache hits**. Pro processed **1,956,723 logical/model tokens for $2.089129** with **0% cache hits**. Under that actual workload/cache mix, Pro was about **47.74x more expensive per logical/model token**. Task difficulty and output quality were not controlled, so that ratio is a routing-economic witness, not a quality-adjusted verdict on the models.

DeepSeek V4 Pro therefore **must not be the default remote reasoning lane merely because it is the larger/higher-priced model**. The preferred route is:

```text
REUSE / HYPERDRIVE COLLAPSE
→ NO_MODEL / AURAOS DETERMINISTIC
→ active authorized high-reasoning interactive endpoint where appropriate
→ admitted LOCAL route when adequate
→ DEEPSEEK V4 FLASH / STANDARD lower-cost remote residual
→ DEEPSEEK V4 PRO only when earned
→ another frontier provider only with explicit current authority
```

A Pro escalation is earned when lower-cost routes fail declared adequacy/success criteria, or when a preregistered comparison predicts/measures enough incremental correctness, repair, verification, latency, or reusable-cognition value to justify the incremental lifecycle cost.

```text
EscalateToPro(a) only if
E[Δ VerifiedValue(a)] > Δ LifecycleCost(a) + RiskMargin(a)
```

subject to source/currentness, authority, privacy, budget, and consequence constraints. Model size or a `Pro` label is not itself evidence of value.

## Cost follows the action; quality follows verification

Every consequential execution path should produce or extend `CognitiveEfficiencyReceiptV1`. Provider dollars are only one component:

```text
C_action =
    C_provider
  + C_compute
  + C_IO
  + C_network
  + C_latency
  + C_coordination
  + C_verification
  + C_rework
```

Each receipt should bind the action/command/WorkCapsule/Arena identity; source generation/currentness; route and provider/model/version/rate generation; cache-hit, cache-miss, and output tokens; billed provider dollars; observable local compute/I/O/network/latency/energy; deterministic/model calls avoided; verification and repair; declared success criteria; final disposition; reusable verified state produced; and invalidators/reopen triggers.

`UNKNOWN COST != ZERO COST.` A no-model route may have $0 provider spend and still consume local compute, I/O, latency, or coordination. Reuse/reconstruction avoided should be reported as a separately evidenced counterfactual rather than silently subtracted.

For matched Aura/control workloads, report **provider cost per verified outcome, lifecycle cost per verified outcome, time to verified result, success/acceptance, challenged correctness, surviving defects, repair/rework, cost per repaired defect, cost per reusable verified artifact, cache savings, recomputation avoided, reusable cognition created, and quality delta versus matched control**. Do not force those into one scalar unless the weighting is preregistered and interpretable.

Aura also has a distinct semantic reuse layer. **HSC-196** recorded a real cold call of **43,743 prompt + 763 completion tokens**, followed by an identical accepted coordinate/result reuse requiring **0 provider tokens**. **HSC-198** observed **95.9% provider cache-read** in the cold live-dispatch wave and then **27/27 coordinate hits with zero provider tokens** in the scoped same-objective warm rerun, but the cold wave also failed its preregistered timeout criterion (**10 PASS / 17 TIMEOUT**) and had a WorkCapsule prompt-content defect. The failure remains visible instead of being converted into a quality claim.

Later **AWJ-023** governed DeepSeek dispatch evidence records a real canary, ACK-before-effect, zero-duplicate replay, stale-revision refusal before effect, restart absorption, dispatcher **21/21**, and an identity-distinct three-worker successor triad, reaching `GATE10_READY / READY_FOR_OWNER_PROMOTION / NONPROMOTING`. **AWJ-025** later returned `GATE10_PARTIAL / READY_FOR_OWNER_DISPOSITION` instead of being mislabeled complete. These are bounded workflow-quality/governance witnesses; they are not matched model-quality controls.

The current claim is therefore deliberately scoped:

> **Current bounded evidence shows that Aura can substantially reduce provider cost in scoped workloads through provider-cache exploitation plus source-bound semantic/result reuse while maintaining explicit challenge, verification, replay, stale-state, restart, and Gate-10 controls. Several scoped witnesses return already-accepted consequences with zero additional provider tokens. Universal causal savings and universal superior output quality are not yet established; those require matched non-Aura controls with action-linked cost/quality receipts.**

## Lifecycle-efficiency counterfactual and blind Gate-10 campaign

Token/cache economics are now treated as a **floor**, not the complete economic unit. The lifecycle model includes provider/model work plus rehydration, rediscovery, stale work, duplicate work/effects, verification, bug escape, repair/rewrite, regression, coordination, and downstream blast radius. The full sensitivity analysis is in [`docs/AURA_LIFECYCLE_SAVINGS_COUNTERFACTUAL_2026-08-29.md`](./docs/AURA_LIFECYCLE_SAVINGS_COUNTERFACTUAL_2026-08-29.md), and the preregistered blind benchmark design is in [`docs/AURA_BLIND_GATE10_BENCHMARK_PROTOCOL_2026-08-30.md`](./docs/AURA_BLIND_GATE10_BENCHMARK_PROTOCOL_2026-08-30.md).

A simple provider/rework sensitivity model uses:

```text
C_noAura_provider(f,r) = (C_A + f*S_C) * (1 + r)

C_A = $27.068077 actual provider cost
S_C = $271.515493 conservative provider-cache opportunity
f   = fraction of cache opportunity attributable to Aura-enabled workload structure
r   = extra model/provider rework needed without Aura to reach equal verified quality
```

| Sensitivity point | Cache attribution `f` | Extra no-Aura rework `r` | Modelled no-Aura equivalent | Saving vs actual | Saving share | No-Aura / Aura |
|---|---:|---:|---:|---:|---:|---:|
| Attribution-zero reference | 0% | 10% | $29.77 | $2.71 | 9.1% | 1.10x |
| **Conservative** | 25% | 10% | **$104.44** | **$77.37** | **74.1%** | **3.86x** |
| **Central sensitivity** | 50% | 25% | **$203.53** | **$176.46** | **86.7%** | **7.52x** |
| **Strong** | 75% | 40% | **$322.99** | **$295.92** | **91.6%** | **11.93x** |
| Stress / full attribution | 100% | 50% | $447.88 | $420.81 | 94.0% | 16.55x |

These are **MODELLED / SENSITIVITY** values, not causal benchmark results. The conservative-to-strong 74–92% band is a hypothesis surface whose assumptions must be replaced by matched-control measurements.

The semantic-reuse witness is stronger than provider-prefix caching alone: HSC-198's same-objective warm rerun returned **27/27 Coordinate Hits and 0 API tokens**. At the cheapest observed August 27 Flash rates, reconstructing the same work would still have cost about **$0.432239** even if every repeated input token got the cheapest observed provider cache-hit price, or about **$7.209174** at the cheapest observed miss rate. A current verified result hit can therefore be economically better than a cheap inference-cache hit because no inference is required.

Observed repair evidence also shows why first-response token cost is incomplete. One independent challenge upheld **9/9 defects**, after which repairs passed **17/17 tests + 13/13 controller checks**. Another fold verified **6/6 repairs** while preserving four additional precision residuals. Using only those 13 sampled issues, illustrative defect-escape assumptions span **1.625 to 39 engineering hours avoided**; those hours are not monetized until a real loaded labor rate is supplied.

### AWJ-028 blind A/B campaign

The next claim-bearing test is a genuinely blind **Aura vs no-Aura** Gate-10 campaign. Its baseline design contains **20 logical triad swarms**: nine CONTROL triads, nine AURA triads, one blind evaluator triad, and one final Gate-10 synthesis triad. Physical expansion `3 → 9 → 27 → 81` is earned only by unresolved independent frontier and current provider/budget authorization; duplicate identical prompts are not independent evidence.

The 3×3 adversarial lattice covers:

1. **27-bit / 27-cell sharding and exact reconstruction** — reorder, missing/corrupt/duplicate shards, aliases, misleading near-matches, typed impossibility/UNKNOWN and exact provenance;
2. **semantic currentness / stale-state traps** — superseded generations, same-name sources, contradictory newer evidence, invalidated coordinates and false-reuse traps;
3. **code-generation / repair cascades** — race conditions, exception-contract mismatch, replay/idempotency bugs, leaks, stale fixtures, bad tests, hidden dependencies and tempting wrong rewrites;
4. **hallucination / citation / provenance stress** — plausible decoys, absent facts, mixed generations and required abstention;
5. **long-context / minimum-hydration reconstruction** — decisive sparse facts beyond useful context with high-similarity distractors;
6. **replay / restart / duplicate-effect safety** — duplicate/reordered commands, stale revisions, restart and lease/fence timing;
7. **multi-agent independence / dissent** — independent first-pass C/C/V versus broadcast-first debate and majority vote;
8. **routing economics / escalation** — verified reuse/no-model, deterministic/local routes, Flash-class residuals and Pro-class escalation only when earned;
9. **end-to-end composite torture test** — sharding, currentness, code repair, misinformation, replay, long context, exact mathematics, routing and final auditable consequence in one objective.

Hallucination is not reduced to one vague number. The campaign separately scores:

```text
H_source      unsupported or source-contradicted factual claims
H_citation    fabricated or incorrect source attribution
H_currentness once-true but stale/wrong for the current objective
H_inference   conclusion not justified by evidence or executable result
```

Initial hallucinations and hallucinations surviving Challenge/Verify are both retained. The blind evaluator freezes semantic scores before arm labels are revealed, reconstructs ground truth independently from immutable sources/generators/tests, retains FAIL/TIMEOUT/PARTIAL/UNKNOWN runs, and audits treatment leakage.

The primary economic score is:

```text
VerifiedLifecycleEfficiency = VerifiedConsequenceValue / TotalLifecycleCost
```

but the denominator and all correctness/safety/currentness dimensions must also be published separately. Gate 10 requires preregistration integrity, blinding, reproducible scoring, exact run-to-token/cost receipts, independent source/test reconstruction, uncertainty/effect-size reporting where supported, preserved negative results, and an explicit bounded claim ceiling. `GATE10_READY` remains `READY_FOR_OWNER_PROMOTION / NONPROMOTING`; the campaign cannot self-promote universal superiority claims.

## The amortization hypothesis

For a verified foundation with initial cost `F`, reusable fraction `r_t`, new work `W_t`, and lookup/revalidation/coordination cost `V_t`:

```text
C_total(T) ≈ F + Σ[(1 - r_t)·W_t + V_t]

C_average(T) = F/T + average[(1 - r_t)·W_t + V_t]
```

If reuse coverage rises faster than maintenance and validation overhead, expensive cognition becomes infrastructure and marginal cost falls. If stale-state repair, coordination, or reproof dominates, it does not. That is now a benchmarkable systems hypothesis.

Negative results can amortize too. A verified failed path can prevent thousands of later researchers from unknowingly paying to rediscover the same dead end, while its invalidators preserve the conditions under which that path should be reopened.

---

# From one researcher to 100 million participants

Aura's scaling idea is **not** “run 100 million agents on the same prompt.” It is:

> **Do not pay twice for a solved consequence unless independent reproof has value. Activate the smallest useful independent frontier, then return verified results to the shared substrate.**

A useful wall-time lower-bound model is:

```text
T_wall >= L_critical
          + W_novel_parallel / N_eff
          + C_coordination
          + C_verification
```

`N_eff` is effective independent evidence capacity, not raw headcount. Correlated agents do not become independent merely because more copies exist.

| Scale | What changes | What can amortize |
|---|---|---|
| **1 user/team** | build first coordinates, tests, methods, Recipes, negative results | repeated local reconstruction |
| **10** | share verified foundations and independent challenge | onboarding, literature maps, environment setup, known calculations |
| **100–10,000** | domain specialization, capability competition, federated registries | duplicated research, adapters, validation infrastructure |
| **10,000–1M** | communities, universities, Nations, businesses, labs, facilities | cross-project reuse and shared infrastructure |
| **1M–100M+** | federated global consequence frontiers, local authority/custody | civilization-scale reuse without one planetary hot context |

These are **architectural scaling scenarios, not measured 100-million-user throughput claims**.

The potential is largest where work is highly decomposable: software engineering, literature synthesis, theorem search, simulation, data analysis, materials discovery, design-space exploration, modeling, standards comparison, and distributed scientific workflows. Physical experiments, biological growth, scarce equipment, sequential causal chains, professional review, and necessary independent replication still impose real lower bounds.

---

# One Arena Engine, many Arena Recipes

Papers VIII–IX form the bridge from domain-specific Arenas to the current redesign. Paper VIII established the evidence/authority rule:

> **Planning proposes. Governance authorizes. Verification proves.**

Paper IX made the objective—not the permanent application—the first-class unit of computing.

```text
Arena_q = Compile(
    Objective_q,
    Semantics_q,
    Evidence_q,
    Constraints_q,
    Capabilities_q,
    Rights_q,
    Authority_q,
    Identity_q,
    Context_q,
    Device_q,
    Budget_q,
    ProofObligations_q,
    Completion_q,
    Dissolution_q
)
```

The current redesign collapses separate application engines into **one ephemeral Arena Engine plus reusable Arena Recipes**.

> **An Arena Recipe is the reusable pattern, not the implementation.**

A Recipe can specify roles, dependencies, proof obligations, fallback logic, presentation, completion, dissolution, and optional economic terms. Runtime resolves those roles against the current capabilities, versions, rights, policy, jurisdiction, evidence, cost, privacy, and device.

```text
PERSISTENT
capabilities / methods
Arena Recipes
coordinates / source identities
rights / entitlements
provenance / attribution
verified evidence / negative results
Place manifests
relationships

EPHEMERAL
capability activations
objective-specific UI
rooms / layouts / projections
workers / model fibers
transient caches
leases / temporary secrets
```

---

# Applications across domains

The same substrate can compile radically different objective-specific worlds. These are architecture-supported applications/research directions, **not claims that Aura currently possesses medical, scientific, engineering, legal, financial, governmental, or regulatory authority.**

| Domain | Example Aura role | Boundary |
|---|---|---|
| **Medicine / health research** | current-source literature, patient-authorized data projections, evidence-conflict detection, specialist review, protocol/trial matching | clinicians, patients, institutions and regulators retain authority |
| **Science** | literature reconstruction, data curation, derivation, hypothesis generation, falsification, replication, uncertainty, experiment design | simulation/consensus cannot promote itself into empirical truth |
| **Materials science / chemistry** | candidate materials, parameter search, multi-simulator comparison, process Recipes, facility/lab matching | physical characterization and safety evidence remain decisive |
| **Engineering / construction** | codes, BIM/digital twins, alternatives, cost/schedule, hazards, inspections, simulation-reality comparison | qualified humans retain approval/procurement/actuation authority |
| **Civic planning / public infrastructure** | evidence maps, scenarios, deliberation packets, resource tradeoffs, community/Nation governance | simulated people are not authority; public decisions remain human/governed |
| **Economics / finance** | scenario models, dependency graphs, assumptions, market/economic simulation, audit trails | forecasts are advisory; legal/financial authority remains external |
| **Energy / climate / environment** | microgrid modeling, water/food/energy dependencies, land/resource scenarios, sensor + simulation evidence | real measurements and responsible authorities remain canonical |
| **Emergency response** | live terrain/incidents, routes, assets, forecasts, teams, evidence and competing plans in one shared Arena | human incident command retains action authority |
| **Software / Web development** | repository as semantic world, affected-cone source hydration, tests, security review, capability composition | source/tests/owners decide; visual or model projection is not patch authority |
| **Web-4.0-style spatial computing** | objective-native AR/MR/VR/desktop/mobile environments, Places, remote people + AI agents, digital twins | Aura does not claim ownership of the term Web 4.0 |
| **Online marketplace / commerce** | objective matching, product/service Places, virtual try-on, direct commerce, provenance, support/returns | rights, payment and consumer/legal obligations stay explicit |
| **Education / training** | individualized Learning Arenas, simulations, verified capability portfolios, mentor/human review | no single opaque reputation score is required |
| **Security / encryption operations** | generation/currentness-aware cryptographic context, blind indexes, receipts, key/suite migration | standard reviewed crypto supplies hardness; Aura geometry is not a cipher |

The larger **Open Discovery Foundry** concept can link unmet needs to literature, simulation, falsification, independent review, physical experiment, manufacturing/fabrication, field validation, and then return the resulting methods/capabilities to the Commons.

---

# Aura Places, Visits, marketplace, and a Web-4.0-style human layer

Paper IX defines **Aura Places** as persistent signed/versioned/portable definitions governed by a person, creator, business, organization, community, or Nation. The Place persists; each visitor receives an **ephemeral Visit** compiled for their objective and relationship.

A Place can include:

- media gallery / live studio;
- public, private, invited, subscriber, or backstage rooms;
- collaboration and community spaces;
- digital closets, product showrooms, virtual try-on, and digital twins;
- direct commerce, subscriptions, commissions, referrals, loyalty, co-design;
- customer support, repair, and returns;
- Arena Recipes, capabilities, research discoveries, services, and creator tools;
- provenance, attribution, and evidence-bearing contribution portfolios.

```text
PlaceManifest(version)
    + visitor / objective / relationship
    + permissions / entitlements
    + device / network / accessibility
    ↓
Ephemeral Visit
    ↓
transfer only missing assets / deltas
    ↓
interaction + minimized receipts
    ↓
dissolve temporary state
```

Convention Arenas can temporarily assemble many Places into an event. The hall can disappear after the event while authorized relationships, purchases, subscriptions, entitlements, saved artifacts, receipts, and digital twins persist.

---

# Aura Commons: shared capability, provenance, attribution, and settlement

Aura Commons is **not a second truth plane** and not merely an app store. It is a federated discovery/composition/accounting layer over canonical owners and bounded execution.

It can coordinate:

```text
capabilities / methods / Arena Recipes
package and publisher identities
licences / rights / entitlements
verification / performance / security evidence
provenance / attestation
bounties / demand signals
Places / assets / procedural generators
community / Nation / enterprise / offline registries
revocation / migration / dispute / appeal
payment references / settlement adapters
```

No single registry needs to become the universal truth owner.

## Meaningful-use attribution—including superseded work

The economic unit is not token count, message count, invocation count, or raw commit count. A contribution can be evaluated from proof-carrying dependency evidence such as:

```text
executed?
verified?
output survived?
downstream consumed it?
prevented a failure?
accepted by user/canonical owner?
enabled later work?
superseded but still causally foundational?
maintenance/security role?
quality / latency / compute / bandwidth delta?
counterfactual marginal contribution?
```

This means **superseded code or an older Arena Recipe does not have to become economically invisible**. If it materially enabled the successor, the Attestation/Provenance DAG can preserve that ancestry. Attribution should remain contestable and amendable when later evidence changes the causal picture.

The hard separation remains:

```text
LICENCE
!= PROVENANCE
!= ATTRIBUTION
!= ECONOMIC ENTITLEMENT
!= TRUTH / AUTHORITY
```

Open-source use does not automatically create royalties. Provenance does not automatically create debt. Payment must arise from an explicit lawful rule or agreement: subscription allocation, per-use licence, verified-result payment, bounty, maintenance/security reward, upstream dependency share, Arena Recipe share, Place/service revenue, cooperative allocation, voluntary Commons support, conventional payment rails, or lawful smart-contract settlement.

## Self-feeding Commons flywheel

```text
real objective
→ missing capability / bottleneck
→ bounty / opportunity
→ human / AI / specialist contribution
→ independent benchmark / verification
→ eligible capability / Recipe
→ downstream meaningful use
→ attestation / attribution
→ explicit settlement where applicable
→ maintenance / optimization
→ next objective
```

The deeper hypothesis is that the Commons becomes a **shared amortization substrate**: a solved, verified and reusable work unit can subsidize every later compatible objective.

---

# Near-gas-free ledger lineage

Aura's earlier N10 lineage disclosed a **Gas-Free Fractal Ledger** concept using a Merkle-DAG, Proof-of-Presence ideas, and RAM-staking instead of token-denominated gas.

The mature claim boundary is stricter:

> **“Gas-free” means no mandatory token gas fee in that design; it does not mean zero physical cost.** RAM, storage, compute, bandwidth, hardware, verification, operations, and administration still consume resources.

The mature Aura Commons does **not require a blockchain or token**. The ledger can be one optional provenance/settlement adapter among conventional databases, append-only logs, payment processors, cooperative ledgers, or smart-contract systems.

Historical thermodynamic/device-entropy ideas are not treated as automatically secure roots. Newer ARCE work assigns auxiliary physical entropy **zero credited security bits until independently characterized** for entropy, threat model, conditioning, privacy, restart behavior, and common-cause failure.

---

# Encryption and cryptographic control

The newer **ARCE** encryption/control work is **staged, noncanonical, test-required, and cryptographic-review-required**. Its central idea is not to invent an Aura-specific magical cipher. It is to combine standard reviewed cryptographic hardness with Aura's source/currentness/authority context.

```text
STANDARD CRYPTOGRAPHIC HARDNESS
AES / standardized AEAD
ML-KEM / ML-DSA where appropriate
standardized hybrid TLS constructions
SHA-2 / approved transcript hashes
Ascon-class lightweight primitives where permitted
OS / hardware-protected key storage

        +

AURA CONTEXT BINDING
semantic identity
source generation / currentness
authority / purpose
domain separation
W0 witness / receipts
blind indexes
replay / nonce state
epoch / generation leases
reopen / invalidation paths
crypto-agile migration
```

Candidate profiles explore high-assurance PQ/traditional hybrid mechanisms, AES-256-class authenticated encryption, constrained-device Ascon profiles where justified, generation-bound crypto agility, HMAC blind indexes, and W0/Merkle-style tamper-evident state.

Aura's toroidal, tesseract, Morton, 27-cell, and other geometric structures can organize locality, interlacing, encrypted blocks, redundancy, reconstruction, and wake neighborhoods. They are **not cryptographic hardness**:

```text
Toroidal / tesseract / 27-cell interlacing
!= encryption
!= entropy
!= authentication
```

A 27-bit or 27-cell layout is not a cryptographic security boundary.

---

# 3-6-9 orchestration and swarm scaling

Aura uses 3-6-9 as an **orchestration grammar**, not a numerological or universal physical law.

- **3** — smallest reviewable Construct / Challenge / Verify cell.
- **6** — paired triads for perturbation, challenge and parallel work.
- **9** — three triads closing a larger analysis/execution/reconciliation cycle.

The physical worker count is separate from logical topology. Useful scaling is governed by independence, conflict, latency, budget, and evidence value—not by multiplying agents blindly.

Later Aura Drive 2 work ran a **27-objective live swarm battery**. The preregistered cold wave returned **27/27 receipts but 10 PASS / 17 TIMEOUT at concurrency 7**, so the apex was `REPAIR_REQUIRED`. A warm same-objective rerun through Coordinate Memory then returned **27/27 coordinate hits with zero provider tokens**. Both results remain visible because failure evidence is part of the architecture.

---

# Benchmark evidence hierarchy

Aura uses an append-only evidence discipline:

1. **Current / superseding evidence**
2. **Current failures / falsifiers / residuals**
3. **Historical / scoped repository evidence**

`PASS in one harness != universal PASS`.

## Current / superseding measured evidence

| Surface | Latest measured result | Boundary |
|---|---:|---|
| **Latest longitudinal provider export** | **11,670 requests; 1,321,646,285 logical/model tokens; 1,277,497,600 cache-hit input tokens; 97.419025% input cache-hit share; $27.068077 billed** | Real provider accounting through Aug. 29; not a controlled attribution study. |
| **Conservative provider-cache counterfactual** | **actual $27.068077 vs >= $298.583570 all-miss-equivalent; >= $271.515493 additional charge avoided; >= 90.9345% billed-cost reduction** | Same-day/model price-only lower-bound counterfactual; does not prove Aura uniquely caused cacheability. |
| **Lifecycle savings sensitivity** | **$104.44 conservative / $203.53 central / $322.99 strong no-Aura provider+rework equivalent vs $27.068 actual; 74.1% / 86.7% / 91.6% modelled saving share** | MODELLED sensitivity analysis; not matched-control causal evidence. |
| **Aug. 29 Flash vs Pro routing witness** | **Flash: 109,281,723 logical/model tokens, $2.443945, 94.1092% input-hit; Pro: 1,956,723 tokens, $2.089129, 0% hit; Pro ~47.74x higher billed cost per logical/model token under actual mix** | Task difficulty/quality not controlled; routing-economic evidence only. |
| **Paper X provider snapshot** | **9,381 requests; 843,642,344 logical/model tokens; 97.402912% input cache-hit share; $17.772456 actual vs $209.580400 price-only all-miss counterfactual** | Not a 97% logical-token reduction; does not prove Aura uniquely caused cacheability. |
| **HSC-196 cold task** | **43,743 prompt + 763 completion tokens; $0.01012704** | Bounded real task/provider/host measurement. |
| **HSC-196 coordinate-result reuse** | identical accepted coordinate result: **0 provider tokens** | Aura-level reuse, separate from provider prefix/KV cache. |
| **HSC-198 cold 27-objective swarm** | **27/27 receipts; 10 PASS / 17 TIMEOUT; 31,816,596 prompt + 317,459 completion; $0.709600** | Failed preregistered timeout criterion; NONPROMOTING / NOT_GATE10. |
| **HSC-198 provider cache** | **30,514,432 / 31,816,596 prompt tokens cache-read = 95.9%** | Provider cache plane. |
| **HSC-198 warm Coordinate Store** | **27/27 COORDINATE_HIT; 0 API tokens; 31,816,596 prompt tokens avoided on scoped repeat** | Same-objective reuse only; not arbitrary-hit-rate proof. |
| **AWJ-023 governed DeepSeek dispatch** | **real canary; ACK-before-effect; zero-duplicate replay; stale revision refused pre-effect; restart absorption; dispatcher 21/21; identity-distinct three-worker successor triad; GATE10_READY** | Strong bounded governed-execution evidence; not a matched model-quality control. |
| **AWJ-025 outcome discipline** | **GATE10_PARTIAL / READY_FOR_OWNER_DISPOSITION** | Partial evidence preserved rather than mislabeled complete. |
| **AWJ-028 blind benchmark campaign** | **20 logical triad baseline: 9 CONTROL + 9 AURA + blind evaluator + Gate-10 synthesis; 3×3 adversarial lattice** | ISSUED / PREREGISTERED design; execution results not yet claimed. |
| **AutoLineage / AutoRoute HSC-193** | **38/38 selftest; 20/20 parity; 60/60 whitespace; 12/12 DryRun** | Exact tested path only. |
| **Later navigator regressions** | **172/172 non-concurrency PASS; sector/cell parity 15/15 + live** | Strong bounded regression evidence. |
| **Integrated upsert concurrency** | later four-way routing minted **3 distinct JIDs for one source** | Open integrated concurrency defect; prevents universal zero-collision claim. |
| **Arena v1.3 local hardening** | Morton **27/27**; storm **160/160**; same-JID stress **400 → 50 winners / 350 typed conflicts / 0 silent collisions** | Local-grade bounded evidence. |
| **Paper X spatial slice** | **33/33 PASS**, stale-epoch gating, cross-modal equivalence, adaptive **30/45/60 FPS** governor | Software/projection evidence; physical device latency still separate. |
| **HyperScale HSC-187** | bypass ON **7.08 ms** vs OFF **6.25 ms** = **13.23% slower** | Falsifier triggered; optimization not promoted. |
| **Exact scale sweep** | **40,320 permutations → 108 running-GCD trajectories; 219/255 subsets reach gcd=1; s=4 minimax; virtual completion {6,8,24}** | Exact finite mathematics, not production speed. |
| **Factor-controller witness** | **3,333,960-state OP7 brute-force** matched treewidth-1 DP winner/cost | Bound algorithmic equivalence witness. |

## Current failures and open residuals

| Residual | Disposition |
|---|---|
| Integrated upsert race | **OPEN / CONFIRMED** |
| HSC-198 cold swarm timeouts | **FAIL by preregistration: 17/27** |
| Work Capsule prompt-content defect in that harness | objective text was omitted; blocks semantic-quality interpretation of that wave |
| 81-worker live leg | open benchmark; logical addressability is not useful live concurrency evidence |
| `<95 MiB` RSS | not achieved in measured host process |
| official InjecAgent `0% ASR` | unverified as official end-to-end result |
| official Tau-bench `100%` | unverified as official pass^k |
| 40–80% local task absorption | redesign target / hypothesis |
| universal cognitive superiority | **not established; matched controls required** |
| AWJ-028 causal savings/hallucination delta | **PREREGISTERED / RESULTS NOT YET CLAIMED** |

## Historical repository measurements

| Surface | Historical result | Boundary |
|---|---:|---|
| Six-slot FST routing | **1,366,040.46 iterations/s; 8,196,242.75 transitions/s** | deterministic transition microkernel only |
| `3^n` Merkle aggregation | **2,460.61 rollups/s; 895,661.61 hashes/s** | depth-5 bounded benchmark |
| SQLite WAL | **19,934.69 writes/s @ 5 workers** | one-row transaction throughput |
| Peak process RSS | **116.71 MiB** | historical host process |
| Serialized state projection | **72.73% fewer bytes (286 B → 78 B)** | byte serialization, not universal token reduction |
| UDP localhost | median **7.080 µs**, p95 **10.126 µs** | localhost RTT, not remote mesh |
| InjecAgent-derived hard gate | **0 / 868 attack transitions reached executable state** | gate-layer test only |
| Legacy τ-bench compatibility | **42 / 42** | bounded legacy sample, not official τ-bench pass^k |
| 25-slot daemon fleet | **25 / 25 exact-once DONE; 0 duplicate fleet payloads** | valid for that harness; later integrated race is a different path |

Repository scorecards:

- [`docs/DEEPSEEK_COST_CACHE_BENCHMARK_2026-08-29.md`](./docs/DEEPSEEK_COST_CACHE_BENCHMARK_2026-08-29.md)
- [`docs/AURA_LIFECYCLE_SAVINGS_COUNTERFACTUAL_2026-08-29.md`](./docs/AURA_LIFECYCLE_SAVINGS_COUNTERFACTUAL_2026-08-29.md)
- [`docs/AURA_BLIND_GATE10_BENCHMARK_PROTOCOL_2026-08-30.md`](./docs/AURA_BLIND_GATE10_BENCHMARK_PROTOCOL_2026-08-30.md)
- [`docs/INDUSTRY_BENCHMARK_SCORECARD.md`](./docs/INDUSTRY_BENCHMARK_SCORECARD.md)
- [`docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`](./docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md)
- [`docs/SECURITY_AND_ACCURACY_SCORECARD.md`](./docs/SECURITY_AND_ACCURACY_SCORECARD.md)
- [`docs/ADVANCED_BENCHMARKS.md`](./docs/ADVANCED_BENCHMARKS.md)

---

# Quickstart for the historical repository runtime

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

python aura_node.py
python aura_daemon.py
python aura_swarm_runner.py
```

The present GitHub runtime is **implementation lineage**, not yet the complete Paper X / Aura Drive architecture described above.

## Reproduce historical repository benchmarks

```bash
python3 scripts/aura_industry_benchmark_validation.py
python3 scripts/aura_advanced_benchmark_runner.py
python3 scripts/aura_security_accuracy_harness.py
```

Machine-readable receipts prove only their declared execution relationship/scope. A digest or signature does not by itself establish semantic truth, currentness, human identity, or promotion authority.

---

# Licensing and Commons boundary

AuraOS's current licensing posture is **GNU Affero General Public License v3.0 / AGPL-3.0-only** where marked in the current Paper X/reference package.

Copyleft is a strong barrier against silently enclosing covered network software, but it is not an automatic patent shield, royalty system, economic-entitlement contract, or universal governance mechanism.

The Commons intentionally keeps:

```text
source licence
provenance
attribution
economic settlement
governance / truth / authority
```
as distinct layers.

---

# Evidence provenance / synchronization note

This README intentionally preserves multiple generations instead of flattening them:

- Papers I–VII foundational/distributed/bounded-protocol lineage;
- Paper VIII governed/evidence-ordered Arenas;
- Paper IX objective-native composition, Commons, Arena Recipes, Places and economic lineage;
- Paper X Rev.3 as the current foundational architecture;
- later Aura Drive / Aura Drive 2 measurements, repairs, falsifiers and redesign work;
- staged/nonpromoting RO3DD/P0-D2RM/ARCE and related research where its current status requires that label;
- staged/test-required Arena V0.3 / HyperDrive / HyperScale runtime work where governing sources retain that status;
- historical repository benchmarks whose exact harnesses remain valid even when later evidence narrows the system-wide conclusion.

Where later evidence narrows, supersedes, repairs, or falsifies an older headline, the older result remains visible under its original scope instead of being rewritten.

**Current engineering objective:** rebuild AuraOS so the executable code catches up to Paper X and the Aura Drive architecture—across cloud Drive, local laptop/desktop, mobile/edge, and federated carriers—while preserving source currentness, independent challenge, human authority, honest benchmarks, and the ability to reopen everything that compression leaves cold.
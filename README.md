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
> The core direction is:
>
> ```text
> Human / Agent Intent
>        ↓
> Aura semantic + coordinate world
>        ↓
> minimum-sufficient active world / affected cone
>        ↓
> deterministic local / low-cost execution where possible
>        ↓
> reusable coordinate / result / capability hit?
>     yes ↙                    ↘ no
> reuse + revalidate       LLM / swarm for residual
>        \                    /
>         Construct → Challenge → Verify
>                     ↓
>      atomic consequence commit + SuccessorFrame
>                     ↓
> reusable coordinates / methods / receipts / recipes
> ```
>
> **Paper X is carrier-portable.** Its semantic/source/provenance/currentness/receipt architecture can be instantiated in Google Drive, on a laptop, on a mobile device, in a database/object store, or across a federated/peer substrate. The carrier is not the truth owner.

## Canonical publication

- **Paper X Rev.3 PDF:** https://zenodo.org/records/22134815/files/PAPER-X%20%285%29.pdf?download=1
- **Canonical Zenodo record:** https://zenodo.org/records/22134815
- **DOI:** https://doi.org/10.5281/zenodo.22134815

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
archive / reconstruction jobs
local model / provider adapters
```

Because these operations execute next to the data, a local copy can avoid many network/connector round trips and can perform deterministic preprocessing before a language model is asked to reason. **That reduces both latency and cognitive load:** a model should not spend inference rediscovering something a database query, digest, parser, test, finite-state machine, or exact calculation can determine directly.

Exact performance depends on hardware and workload; “local is faster” is not treated as a universal benchmark until measured on the target device.

## 3. Mobile / edge — a compressed resident Aura Drive

A full Aura semantic world does **not** require every byte of exact source to remain hot in RAM. Paper X's L0→L4 hierarchy, **RO3DD** source-rooted consequence quotient, and **P0-D2RM** dual-basis regenerative memory make a mobile resident form possible.

A mobile Aura Drive can use a residency ladder such as:

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

RO3DD keeps an **objective-conditioned active decision kernel** only when omitted distinctions are consequence-inert or deterministically force reopen/reproof before they matter. P0-D2RM goes further by retaining both the minimum basis needed to make the current decision and an independently rooted basis capable of defeating that decision. Its HOT/WARM/COLD states are **residency projections, not deletion**.

That creates a practical mobile principle:

> **Keep the minimum lawful world resident; page the gap, not the universe.**

On a phone/tablet, exact L4 source may be entirely local when storage permits, partially mirrored, or reopened from an authorized remote carrier. A browser/PWA or thin mobile shell can materialize only the capabilities required for the current objective. Platform restrictions still determine which scripts/native modules can execute locally.

## 4. Federated / peer deployment

At larger scale, Aura should not create one giant global hot database. Local people, communities, organizations, Nations, labs, businesses, and devices can retain their own canonical sources and authority while exchanging minimized consequence frontiers, references, receipts, Merkle roots, residuals, currentness, and reopen routes.

```text
IDENTITY != LOCATION != REALIZATION
```

The same semantic identity should survive Google Drive, mobile, desktop, AR/MR/VR, databases, peer fabrics, and future carriers.

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

**P0-D2RM — Point-0 Dual-Basis Defeasible Regenerative Memory** adds a critical safety property: memory should retain both **why a state may be used** and **how that state may still be defeated**.

Its compact persistent core can be thought of as:

```text
shared source ground
+ minimum decision-sufficient basis
+ independent challenge / defeat-coverage basis
+ common-mode escape basis
+ wake contract
+ exact reopen routes
```

The model/KV cache is an accelerator, **not the memory owner**. A model can be replaced and the durable semantic state can still be regenerated from source.

---

# Real usage: the reuse curve is getting more interesting as the system is used

The newest usage export extends the published Paper X telemetry.

| Usage view | Requests | Logical/model tokens* | Cache-hit input tokens | Input cache-hit share | Billed cost | Billed cost / 1M logical tokens |
|---|---:|---:|---:|---:|---:|---:|
| **Paper X snapshot** | 9,381 | 843,642,344 | 814,619,776 | 97.402912% | $17.772456 | ~$0.021066 |
| **Latest export through Aug. 28** | **11,020** | **1,210,407,839** | **1,175,105,664** | **97.828502%** | **$22.535003** | **~$0.018618** |

`* logical/model tokens = cache-hit input + cache-miss input + output. This is not a claim that those logical tokens disappeared.`

The cumulative billed cost per million logical/model tokens declined by about **11.6%** between those snapshots while the workload grew substantially. The input cache-hit share increased by about **0.43 percentage points**.

Heavy-use daily snapshots make the pattern visible:

| Day | Requests | Logical/model tokens | Input cache-hit share | Cost | Cost / 1M logical tokens |
|---|---:|---:|---:|---:|---:|
| 2026-08-26 | 2,844 | 371,273,502 | 97.8072% | $6.626391 | $0.017848 |
| 2026-08-27 | 4,635 | 603,337,241 | 97.8580% | $11.679444 | $0.019358 |
| 2026-08-28 | 1,224 | 233,748,476 | **98.3744%** | **$3.331442** | **$0.014252** |

The curve is **not monotonic every day**, so this is not evidence that each request is automatically cheaper than the one before it. Model/task mix, pricing, provider cache behavior, and workload composition can change. It is longitudinal evidence that very large repeated workloads are operating with unusually high reuse and that the cumulative effective billed cost has moved downward.

Aura also has a distinct semantic reuse layer. HSC-196 recorded a real cold call of **43,743 prompt + 763 completion tokens**, followed by an identical coordinate/result reuse requiring **0 provider tokens**. HSC-198 observed **95.9% provider cache-read** in the cold live-dispatch wave and then **27/27 coordinate hits with zero provider tokens** in the scoped same-objective warm rerun.

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

The current design collapses separate application engines into **one ephemeral Arena Engine plus reusable Arena Recipes**.

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
| **Latest longitudinal provider export** | **11,020 requests; 1,210,407,839 logical/model tokens; 1,175,105,664 cache-hit input tokens; 97.828502% input cache-hit share; $22.535003 billed** | Real provider accounting through Aug. 28; not a controlled attribution study. |
| **Paper X provider snapshot** | **9,381 requests; 843,642,344 logical/model tokens; 97.402912% input cache-hit share; $17.772456 actual vs $209.580400 price-only all-miss counterfactual** | Not a 97% logical-token reduction; does not prove Aura uniquely caused cacheability. |
| **HSC-196 cold task** | **43,743 prompt + 763 completion tokens; $0.01012704** | Bounded real task/provider/host measurement. |
| **HSC-196 coordinate-result reuse** | identical coordinate result: **0 provider tokens** | Aura-level reuse, separate from provider prefix/KV cache. |
| **HSC-198 cold 27-objective swarm** | **27/27 receipts; 10 PASS / 17 TIMEOUT; 31,816,596 prompt + 317,459 completion; $0.709600** | Failed preregistered timeout criterion; NONPROMOTING / NOT_GATE10. |
| **HSC-198 provider cache** | **30,514,432 / 31,816,596 prompt tokens cache-read = 95.9%** | Provider cache plane. |
| **HSC-198 warm Coordinate Store** | **27/27 COORDINATE_HIT; 0 API tokens; 31,816,596 prompt tokens avoided on scoped repeat** | Same-objective reuse only; not arbitrary-hit-rate proof. |
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
- historical repository benchmarks whose exact harnesses remain valid even when later evidence narrows the system-wide conclusion.

Where later evidence narrows, supersedes, repairs, or falsifies an older headline, the older result remains visible under its original scope instead of being rewritten.

**Current engineering objective:** rebuild AuraOS so the executable code catches up to Paper X and the Aura Drive architecture—across cloud Drive, local laptop/desktop, mobile/edge, and federated carriers—while preserving source currentness, independent challenge, human authority, honest benchmarks, and the ability to reopen everything that compression leaves cold.
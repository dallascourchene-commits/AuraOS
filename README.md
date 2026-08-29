# AuraOS

> [!IMPORTANT]
> ## Current architectural status — Paper X now supersedes this implementation
>
> **Paper X is the final culmination of the foundational AuraOS work and is now the current architectural specification for AuraOS.** The code in this GitHub repository preserves important implementation lineage, benchmark surfaces, runtime primitives, and working components, but it does **not yet fully embody the architecture that now exists across Paper X, Aura Drive, and Aura Drive 2.**
>
> AuraOS was originally developed before we understood that the original runtime itself should be integrated into the Aura Drive semantic/coordinate substrate. As Aura Drive and Aura Drive 2 developed, that changed the design substantially: instead of repeatedly asking an LLM or swarm to reconstruct routine state and orchestration, the local AuraOS substrate can increasingly take over deterministic, source-bound, repeatable work and wake a model only for the unresolved residual.
>
> The redesign target is for the Drive-integrated AuraOS substrate to absorb roughly **40–80% of suitable routine orchestration work** where it is cheaper and lawful to do so — for example: assembling Work Capsules, gathering and routing research, resolving semantic coordinates, performing L0→L4 hydration, maintaining provenance/currentness, compiling affected cones, preparing receipts, reconciling state, and packaging successor handoffs. **That 40–80% range is an engineering target/hypothesis, not yet a universal measured benchmark.** Each class of work still has to earn migration through matched cost/correctness tests.
>
> This matters because Paper X already reports bounded evidence of substantial reuse at several layers, including provider-side cache reuse and a separately accounted Aura-level coordinate-result hit that avoided a repeated provider call. Later Aura Drive / Aura Drive 2 work has added live swarm, coordinate-memory, integration, Arena, HyperScale, falsification, encryption/control, and repair evidence. The redesign phase is intended to push more repeatable work *below* the expensive model layer so that the savings compound across repeated objectives rather than being limited to prompt caching alone.
>
> The current direction can be summarized as:
>
> ```text
> Human / Agent Intent
>        ↓
> Aura semantic + coordinate world
>        ↓
> minimum-sufficient active world / affected cone
>        ↓
> AuraOS local deterministic / low-cost execution
>        ↓
> LLM / swarm only for unresolved residual work
>        ↓
> Construct → Challenge → Verify
>        ↓
> atomic consequence commit + SuccessorFrame
>        ↓
> reusable coordinates / receipts / affected-cone state
> ```
>
> **Google Drive is a valid deployable carrier for the Paper X architecture, not a mandatory permanent semantic root.** The Paper X world can be instantiated in Drive as source-bound documents, semantic coordinates, receipts, Work Capsules, lineage, currentness state, Arena/Commons definitions, research, rules, manifests, and reopenable evidence. A ChatGPT window with the Google Drive connector can enter that world, read it, hydrate the relevant slices, create and update its structured artifacts, and therefore participate directly in building and maintaining an Aura Drive without requiring a custom local client.
>
> **Aura Drive 2 on a local laptop is the accelerated executable realization of the same architecture.** Local files, SQLite/state stores, indexes, hashes, scripts, test harnesses, code, and deterministic preprocessors can run directly on the machine instead of paying a cloud/connector round trip for every operation. That can materially reduce latency and cognitive load because routine work can be performed by code before a model is asked to reason. Exact speed still depends on workload and hardware; the architectural advantage is that local execution is available and does not require the language model to mentally simulate deterministic computation.
>
> Google Drive itself is a storage/collaboration carrier, **not an arbitrary-code execution engine**. The distinction is deliberate:
>
> ```text
> ChatGPT window
>     │
>     ├── Google Drive connector ──► Aura Drive in Google Drive
>     │                              documents / coordinates / receipts /
>     │                              manifests / research / work state
>     │
>     └── can build and maintain that Drive through connector operations
>
> Local laptop
>     │
>     └── Aura Drive 2 + AuraOS runtime
>            ├── same semantic/source-bound world
>            ├── local files + SQLite/indexes
>            ├── Python / shell / test harnesses / compilers
>            ├── hashes / Merkle work / affected-cone computation
>            └── lower-latency deterministic preprocessing
> ```
>
> The two modes are therefore complementary. A cloud-accessible Aura Drive makes the architecture reachable from ordinary ChatGPT windows and multiple collaborators; a local Aura Drive 2 can execute more of the deterministic substrate close to the data and wake expensive models only for unresolved residuals. Paper X remains carrier-neutral: identity, source, currentness, authority, coordinates, receipts, and reopenability must survive migration among Google Drive, local filesystems, databases, object stores, peer fabrics, and future carriers.
>
> ### What this means for this repository right now
>
> - **Paper X supersedes the current repository as the architectural authority.** See [**Paper X Rev.3 — PDF**](https://zenodo.org/records/22134815/files/PAPER-X%20%285%29.pdf?download=1) and the [**canonical Zenodo record**](https://zenodo.org/records/22134815).
> - **The existing code is not being discarded.** It is the implementation lineage that is now being reconciled, simplified, and rebuilt against the newer Paper X / Aura Drive architecture.
> - **The GitHub implementation is currently behind the working Aura Drive architecture.** Some newer mechanisms, equations, memory/coordinate systems, HyperDrive/HyperScale refinements, regenerative state rules, unified ephemeral Arena model, Commons/economic mechanisms, and encryption/control work are not yet fully represented in this codebase.
> - **AuraOS is now being radically redesigned** so deterministic runtime, semantic coordinate memory, caches, Work Capsules, research gathering, affected-cone recomputation, verification, Arena/Commons execution, and successor-state machinery operate as one integrated substrate rather than as separate generations of the project.
> - **Benchmark evidence below is generation- and workload-scoped.** Newer evidence may supersede a headline without erasing the historical result that produced it.
> - The redesign goal is not “use more agents.” It is to **reuse more verified work, hydrate less irrelevant state, perform more routine work deterministically, and spend expensive model inference only where it can change the governed consequence.**
>
> In short: **Paper X closed the foundational design phase. The current engineering phase is to rebuild AuraOS so the code catches up to that design.**

AuraOS is a minimal, local-first substrate for deterministic state, recursive coordination, reusable computation, governed collaboration, and peer-to-peer/federated execution. It is designed around a simple operating law: **do not feed the system the world; compile the smallest source-resolvable relational world sufficient for the objective.**

AuraOS keeps **addressability, routing, similarity, evidence, truth, authority, provenance, attribution, and payment separate**. A route may identify a lawful next operation without creating source truth, capability, permission, a commit, a merge, or human disposition.

## Founder & contact

**Founder:** Dallas Fabian Courchene-Martin  
**Role:** Founder, AuraOS; Indigenous systems builder  
**Affiliation:** Long Plain First Nation, Treaty 1 Territory, Manitoba, Canada  
**Founder contact:** aura.os.q@gmail.com

AuraOS is being developed around local-first execution, bounded hardware, source provenance, human authority, and community accessibility. The architecture treats constrained RAM, CPU, bandwidth, battery, latency, thermal envelopes, network availability, and model/provider cost as design inputs rather than deployment afterthoughts.

## Core features

- **Google-Drive deployable Paper X world** — the semantic/source/provenance architecture can live in Drive and be built or maintained by connected ChatGPT windows.
- **Local Aura Drive 2 execution** — the same world can be materialized locally so scripts, code, indexes, databases, hashes, tests, and deterministic compilers reduce model workload.
- **Local-first deterministic state** — durable state and receipts remain inspectable close to the operator.
- **Six-slot FST / WFST routing** — bounded state-local routing through `DIR → ASP → CLASS → SUBJ → VOICE → STEM`.
- **3^n recursive rollups** — bounded child work can be compressed into progressively smaller parent summaries.
- **SQLite-backed state** — local transactional state supports deterministic execution and reproducible validation.
- **Bounded worker fleets** — identities, leases, coordinates, inboxes/outboxes, staging lanes, and receipts reduce collision surface.
- **Human-gated authority** — routing, ranking, similarity, hashes, memory, or worker consensus never create consequential authority by themselves.
- **Source-defeasible hydration** — compact representations must remain defeasible by exact/current source evidence.
- **Proof-carrying Commons** — capabilities, recipes, provenance, attribution, rights, and explicit settlement can remain separable and auditable.
- **Near-gas-free ledger lineage** — Merkle-DAG / RAM-staking designs explore ledger settlement without token gas while retaining the fact that physical compute/storage/network costs still exist.
- **Crypto-agile security architecture** — Aura-specific context binding surrounds standard reviewed cryptographic primitives rather than replacing them with geometry or custom ciphers.

## Runtime architecture

```text
                         +----------------------+
                         |    Human Operator    |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      aura_node       |
                         | identity + local API |
                         +----------+-----------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
         +----------------------+        +----------------------+
         |     aura_daemon      |<------>|       P2P mesh       |
         | lifecycle + services |        | peer synchronization |
         +----------+-----------+        +----------+-----------+
                    |                               |
                    v                               |
         +----------------------+                   |
         |   source/state DB    |                   |
         | SQLite + receipts    |                   |
         +----------+-----------+                   |
                    |                               |
                    +---------------+---------------+
                                    |
                                    v
                         +----------------------+
                         | bounded worker fleet |
                         | leases + coordinates |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | 3^n rollups/receipts |
                         +----------------------+
```

### Six-slot FST / WFST boundary

Aura's guarded runtime projects state-local actions through:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

The runtime order is deliberately fail-closed:

```text
hard guards
→ admitted state-local transitions
→ exact WFST ranking
→ six-slot packet
→ deterministic/model-assisted explanation
→ human choice
```

The FST/WFST layer is a routing and syntax mechanism. It does **not** mint source truth, capability, authority, commits, pushes, merges, cryptographic security, or human disposition.

## 3-6-9 orchestration and concurrency

Aura's staged multi-agent architecture uses **3-6-9 phase staggering as an orchestration grammar**, not as a claim of numerological or universal physical law.

- **3** — the smallest reviewable working cell: analysis / synthesis / verification, or lead / builder / auditor.
- **6** — paired triads, allowing perturbation, challenge, handoff, or parallel work without forcing every worker onto the same write surface.
- **9** — three triads closing a larger cycle with separate analysis, execution, and reconciliation lanes.

Collision resistance comes from explicit worker identity, leases before mutation, coordinate/owner partitioning, bounded staging, source-currentness checks, typed failures, and receipts that expose stale generations or collisions rather than silently overwriting them.

Later Aura Drive 2 work has now executed a **27-objective live swarm battery**, but the result is deliberately not summarized as “27 agents passed.” The latest preregistered cold wave produced **27/27 merged receipts but 10 PASS / 17 TIMEOUT at physical concurrency 7**, so the apex was **REPAIR_REQUIRED**. A warm rerun of those same 27 objectives through the Aura Coordinate Store then produced **27/27 coordinate hits with zero provider tokens**. Both facts matter.

### Conditional diagonal rebase

The `3 → 6 → 9/1′` path is a **conditional diagonal rebase** across independently verified/current invariant boundaries. A fast path is admissible only when intervening guards are already satisfied; unresolved evidence, currentness, authority, or negative-space boundaries force the guarded linear path.

## Coordinate memory, provider caching, and cognitive-load reduction

Aura distinguishes several reuse planes:

```text
COORDINATE_HIT
!= PREFIX_KV_HIT
!= BLOCK_KV_HIT
!= RESULT_HIT
```

The aim of Coordinate Memory is broader than “cache this prompt.” A reusable semantic coordinate can bind identity, source generation, currentness, relations, evidence, authority, invalidators, result state, and exact reopen routes. On a local Aura Drive 2, deterministic code can resolve or validate much of that state before a language model is invoked.

Examples of work that can move below the model layer include:

```text
hashing / Merkle ancestry
schema validation
semantic-coordinate lookup
SQLite queries
source-generation checks
affected-cone computation
file/index traversal
receipt generation
manifest validation
exact arithmetic / finite sweeps
static analysis / tests
archive packing / reconstruction
known-route selection
```

That is what “reducing cognitive load” means here: **do not spend model inference re-deriving what deterministic machinery can calculate, retrieve, validate, or reconstruct exactly.**

# Benchmark evidence hierarchy

AuraOS uses an append-only evidence discipline: **newer evidence may supersede, narrow, or falsify an older headline without deleting the historical measurement.** Measurements are not silently generalized from one harness to the whole system.

Current README ordering is:

1. **Current / superseding evidence** — Paper X Rev.3 plus later Aura Drive / Aura Drive 2 measurements.
2. **Current failures, falsifiers, and residuals** — negative evidence stays visible.
3. **Historical repository / Gate-1 evidence** — preserved for lineage, but not presented as the newest whole-system state.

A benchmark is publishable as a current empirical result only to the extent that its workload, source/runtime generation, environment, metric, raw evidence, limitations, and review status are actually bound. `PASS in one harness != universal PASS`.

## Current / superseding measured evidence

| Surface | Latest measured result | Status / evidence boundary |
|---|---:|---|
| **Paper X provider reuse telemetry** | **9,381 requests**; **843,642,344 logical/model tokens**; **814,619,776 cache-hit input tokens**; **97.402912% input-token cache-hit share**; **$17.772456 actual** vs **$209.580400 price-only all-miss counterfactual** | Published Paper X Rev.3 snapshot. **Not** a 97% reduction in logical token volume and **not** proof Aura uniquely caused provider cacheability. |
| **HSC-196 cold real task** | **43,743 prompt + 763 completion tokens**; measured cost **$0.01012704** in the bound run | Replaces earlier 1,000-token assumption / 28-token proxy for this deployment measurement. Bounded task, host, provider, and generation only. |
| **HSC-196 coordinate-result reuse** | Subsequent identical coordinate result: **0 provider tokens** | Aura-level result/coordinate reuse, accounted separately from provider prefix/KV caching. One bounded reuse witness, not a universal hit-rate claim. |
| **HSC-198 live 27-objective cold swarm** | **27/27 merged receipts**; **10 PASS / 17 TIMEOUT / 0 FAIL / 0 ABORTED_INSTRUMENT**; timeout rate **63.0%**; physical concurrency **7**; wall **724.4 s**; **31,816,596 prompt + 317,459 completion tokens**; **$0.709600** reported-wave spend | **FAILED prereg timeout criterion; apex REPAIR_REQUIRED. NONPROMOTING / NOT_GATE10.** Dispatch integrity was measured; semantic correctness was not established. |
| **HSC-198 provider cache inside cold swarm** | **30,514,432 / 31,816,596 prompt tokens cache-read = 95.9%** | Provider/API cache reuse inside the cold live-dispatch wave. Distinct from Aura Coordinate Store reuse. |
| **HSC-198 warm coordinate-memory rerun** | Same 27 objectives: **27/27 COORDINATE_HIT**, **100% scoped hit rate**, **0 API tokens**, **31,816,596 real prompt tokens avoided**, **$0.709600 measured-repeat spend avoided** at that run's effective rate | **Wave 2 FULL PASS for the bound same-objective rerun; NONPROMOTING / NOT_GATE10.** Does not imply arbitrary future objectives hit. |
| **AutoLineage / AutoRoute HSC-193 regression** | **38/38 selftest**, **20/20 dual-engine parity**, **60/60 leading-whitespace battery**, **12/12 DryRun**, plus bounded N2 concurrency re-check PASS | Current for the exact HSC-193 module/path tested. Does **not** erase the later integrated navigator upsert race described below. |
| **Later integrated navigator regression** | Non-concurrency batteries **172/172 PASS**; sector/cell parity **15/15 + live** | Later Aura Drive 2 convergence evidence. Strong regression coverage, but integrated concurrency remained open. |
| **Later integrated upsert concurrency** | **FAIL — 3 distinct JIDs minted for one source under 4-way parallel routing** | **Current open integrated defect from the later Drive-2 convergence cell.** Supersedes any system-wide reading of earlier “concurrency convergence PASS”; narrower earlier passes remain valid in their own harnesses. |
| **Arena v1.3 local hardening** | Morton **27/27**; storm **160/160**; same-JID stress **400 → 50 winners / 350 typed conflicts / 0 silent collisions**; tamper paths typed/quarantined | Local-grade / bounded Arena evidence. Swarm-grade, multi-host, restart-resume, and broader deployment debts remain separate. |
| **Paper X semantic-spatial vertical slice** | **33/33 PASS** in the published bounded slice; deterministic cross-modal input equivalence, stale-epoch gating, affected-cone behavior, adaptive **30/45/60 FPS** governor | Software/projection evidence only. Physical headset/mobile latency and full spatial deployment remain deferred. |
| **HyperScale HSC-187 coprime-bypass trial** | Bypass ON median **7.08 ms** vs OFF **6.25 ms**; **−13.23% gain (slower)** | **Falsifier triggered.** The optimization is CONDITIONAL / not promoted as a saving. Negative result retained deliberately. |
| **HyperScale exact finite scale sweep** | **40,320** scale permutations collapse to **108** running-GCD trajectories; **219/255** nonempty subsets reach gcd=1; `s=4` is the minimax center of the declared scale set; exact virtual completion **{6,8,24}** | Exhaustive / exact finite mathematics for the declared set; **not** a production latency benchmark or universal physical law. |
| **Factor-certificate controller witness** | **3,333,960-state OP7 brute-force** witness matched the treewidth-1 dynamic-programming winner/cost on the synthetic bound instance | Algorithmic equivalence witness for the tested factor structure; not a universal workload-speed claim. |

The HSC-198 swarm battery is useful precisely because it observed **both** effects in the same experiment: the cold live-dispatch wave was already **95.9% provider cache-read by prompt token**, while the later same-objective coordinate-memory wave avoided the provider entirely.

## Current failures, falsifiers, and open residuals

The following are part of the current benchmark state and must not be hidden behind successful numbers:

| Residual / falsifier | Current disposition |
|---|---|
| **Integrated upsert race** | **OPEN / CONFIRMED** — later four-way parallel routing minted **3 JIDs for one source**. A concurrency-hardened navigator is required before any whole-system zero-collision claim. |
| **HSC-198 cold swarm timeout rate** | **FAIL by preregistration** — 17/27 timeouts (**63.0%**) at concurrency 7; apex `REPAIR_REQUIRED`. |
| **Work Capsule prompt-content defect** | HSC-198 found `WorkCapsule.to_prompt()` transmitted only the capsule header in that harness; objective text was omitted. This blocks using that wave as semantic-answer-quality evidence. |
| **81-worker / d4 live leg** | Still an open benchmark/reopen item; logical addressability is not evidence of useful 81-worker live concurrency. |
| **<95 MiB RSS headline** | Still **not achieved** in the measured host process; historical measurements are ~113–117 MiB depending on harness. |
| **Official InjecAgent 0% ASR** | **UNVERIFIED** as an official end-to-end benchmark. Existing 0/868 result is only a bounded hard-gate transition test. |
| **Official Tau-bench 100%** | **UNVERIFIED** as official pass^k. Existing 42/42 result is a bounded legacy compatibility sample. |
| **40–80% local task absorption** | **REDESIGN TARGET / HYPOTHESIS**, not yet a universal measured result. |
| **Universal cognitive superiority** | **NOT ESTABLISHED.** Paper X explicitly requires matched controls before superiority language. |

## Independent challenge and repair are part of the architecture

Aura's safety story is not “the first agent is smart enough.” It is that a candidate can be challenged against source and remain blocked, repaired, or explicitly unresolved.

Recent Drive-2 repair evidence includes a source-first independent challenge that re-executed the relevant checks and verified **6/6 repairs landed with 0 failed**, while still retaining four LOW/INFO residual precision defects. Other recent folds have preserved challenger objections and `FAILED_TO_VERIFY` states rather than silently upgrading them after a persuasive synthesis.

The intended law is:

```text
confident model output
        ↓
independent challenge
        ↓
exact source / test / currentness / authority re-grounding
        ↓
PASS | REPAIR | BLOCK | FAILED_TO_VERIFY
        ↓
human / canonical-owner disposition where required
```

Aura therefore does not promise an infallible AI. It tries to make confident wrongness **detectable, challengeable, source-defeasible, and unable to silently promote itself to authority.**

# Near-gas-free ledger lineage and Commons settlement

Aura's earlier N10 lineage disclosed a **Gas-Free Fractal Ledger** design built around a Merkle-DAG, Proof-of-Presence concepts, and RAM-staking rather than token gas. The useful economic idea survives, but the mature claim boundary is stricter:

> **“Gas-free” means no mandatory token-denominated gas fee in that design; it does not mean zero physical cost. RAM, storage, bandwidth, verification, hardware wear, and administration still cost resources.**

A simplified lineage model is:

```text
transaction / attestation
        ↓
Merkle-DAG dependency / receipt structure
        ↓
resource-bounded admission (e.g. RAM stake / local quota)
        ↓
verification / consensus appropriate to the deployment
        ↓
append-only provenance / settlement evidence
```

The mature Aura Commons does **not require a blockchain or token**. Paper IX/X separate source licence, provenance, attribution, and economic entitlement. Settlement can use a shared subscription pool, per-verified-result payment, bounty, per-use licence, maintenance/security reward, upstream-dependency share, Arena Recipe share, cooperative allocation, conventional payment rails, or a lawful smart-contract/ledger adapter.

This is important because the ledger is an optional settlement/provenance mechanism, **not the truth plane**.

The old thermodynamic/physical-entropy Proof-of-Presence ideas are retained as historical lineage, but they are not treated as automatically secure cryptographic roots. The newer ARCE work explicitly gives auxiliary physical entropy **zero credited security bits until its entropy, threat model, conditioning, privacy, restart behavior, and common-cause failure have been independently characterized.**

# Encryption and cryptographic control: standard primitives, Aura context

Aura's newer encryption/control work is **staged, noncanonical, test-required, and cryptographic-review-required**. Its important architectural move is not inventing a magical Aura cipher. It is separating two layers:

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

Candidate ARCE profiles currently explore:

- **high-assurance** standardized post-quantum/traditional mechanisms, including ML-KEM/ML-DSA-class profiles and standardized hybrid TLS groups;
- **AES-256 / protocol-appropriate AEAD** for high-assurance symmetric protection where applicable;
- **Ascon-based lightweight profiles** for constrained hardware when the permitted security level and measured device cost justify them;
- **generation-bound crypto agility**, so a live session binds an exact protocol/suite/build/policy/trust-anchor generation and cannot silently mutate mid-session;
- **short-lived purpose/epoch compartments**, exact nonce/replay state, and effect-time rebinding;
- **HMAC blind indexes** so dependency/affected-cone lookups can cross a boundary without exposing raw semantic URIs;
- **W0 / Merkle-style causal seals** for tamper-evident state and receipts.

Aura's toroidal, tesseract, Morton, 27-cell, and other geometric structures may help organize encrypted blocks, locality, interleaving, redundancy, reconstruction, or wake neighborhoods. They are **not cryptographic hardness**:

```text
Toroidal / tesseract / 27-cell interlacing
!= encryption
!= entropy
!= authentication
```

Likewise, a 27-bit or 27-cell layout is not a cryptographic security boundary. Actual confidentiality and authenticity must come from reviewed standard cryptographic constructions with correct key, nonce, replay, implementation, and lifecycle handling.

# Arena, Places, and Commons direction

Papers VIII–IX already established the bridge from bounded domain Arenas toward objective-native composition. The current redesign treats “Coding Arena,” “Scientific Arena,” “Construction Arena,” “Marketplace,” “Civic Arena,” and similar names primarily as **Arena Recipes** rather than separate permanent application engines.

```text
objective
→ canonical semantics / evidence / rights / authority
→ resolve reusable capabilities + Arena Recipe
→ compile minimum sufficient ephemeral Arena
→ humans + agents + tools work together
→ verify / commit / attribute
→ retain reconstructible successor state
→ dissolve temporary application surface
```

Paper IX's enduring rule is: **a Recipe is the reusable pattern, not the implementation.** Roles can be rebound to current capabilities, versions, evidence, jurisdiction, privacy, cost, devices, and rights each time the objective runs.

Aura Places extend the same idea to persistent human/community/business/creator spaces. A signed Place persists; each visitor receives a visitor-specific **ephemeral Visit** compiled from relationship, objective, permissions, entitlements, device/network/accessibility state, and context. Places can support media, live rooms, collaboration, product showrooms, virtual try-on, digital twins, direct commerce, subscriptions, support, repair/returns, community events, Arena Recipes, and provenance/attribution without forcing every visitor into one global persistent world.

The economic layer follows meaningful verified contribution rather than traffic volume alone. Superseded work can remain attributable when it materially enabled a successor, while any actual payment remains subject to an explicit lawful settlement rule.

```text
LICENCE
!= PROVENANCE
!= ATTRIBUTION
!= ECONOMIC ENTITLEMENT
!= TRUTH / AUTHORITY
```

# Historical Gate-1 synchronization — retained, no longer the headline state

The table below preserves the older Gate-1 evidence and boundaries. These results remain valid for their exact historical harnesses, but later Paper X / Aura Drive evidence above is the current headline layer.

| Requested headline | Historical Gate-1 disposition | Source-bound result / boundary |
|---|---|---|
| **94%–98% token reduction; ~48-token L0 symbolic tensors** | **EVIDENCE BINDING REQUIRED** | The staged founder source preserved the range, but did not resolve an exact production benchmark independently establishing the full 94%–98% result. Do not present it as verified without workload, baseline, run artifact, and digest. |
| **>5,250 receipt/events per second** | **VERIFIED, bounded scope** | Five 1,000-transition runs: **6,864.45–7,071.97/sec**, median **7,044.41/sec**. Separate timed run: **7,205.33/sec** with 1,001 events including root creation. Exact `StateDeltaDaemon`, SQLite `:memory:`, single thread, append-only state-event path; not distributed/network receipt throughput. |
| **25+ concurrent agents** | **HISTORICAL DESIGN TARGET / FLEET EVIDENCE** | Historical staging recorded 25-plus worker slots and 27 objective positions. This is now superseded as a concurrency headline by the later HSC-198 live 27-objective benchmark and integrated-race evidence above. |
| **<95 MB RSS** | **FAIL for tested host / retained target** | Packaged staging: **115.95 MiB** peak RSS; fresh W3 receipt-path process: **113,012 KB** max RSS. |
| **0.00% InjecAgent ASR** | **UNVERIFIED as official/end-to-end** | No broad official percentage without dataset/version, harness, target generation, run command, result, and digest. |
| **100% Tau-bench accuracy / trajectory adherence** | **UNVERIFIED as official Tau-bench pass^k** | Any bounded legacy trajectory-preservation result stays scoped to its exact sample. |
| **UDP <500 µs** | **VERIFIED WITH SCOPE CORRECTION** | Packaged result: **3.144 µs p95** localhost synchronous UDP RTT; companion: **2.894 µs median**, **3.805 µs p95**, 200/200 packets. Localhost unicast only. |
| **W4 adversarial invariant harness** | **VERIFIED** | Historical staged rerun: **28/28 PASS**, receipt digest `11b2786ece07626d954089db235f6cdac669b5f7f481f28f542eef6126bdf2f2`. Implemented staging invariants only. |

## Historical repository benchmark evidence

These are still useful executable repository measurements, but they describe the current GitHub-generation harnesses rather than the complete Paper X / Aura Drive architecture.

| Surface | Historical source-bound repository result | Evidence boundary |
|---|---:|---|
| Six-slot FST deterministic routing | **1,366,040.46 iterations/s**, **8,196,242.75 transitions/s** | 100,000-iteration deterministic transition microkernel; not linguistic accuracy. |
| `3^n` Merkle aggregation | **2,460.61 rollups/s**, **895,661.61 hashes/s** | 2,000 rollups, depth 5, 243 leaves/rollup. |
| SQLite WAL | **19,934.69 writes/s @ 5 workers** | Best observed one-row transaction throughput; not automatically complete receipt throughput. |
| Peak process RSS | **116.71 MiB** | Historical process high-water mark; above the separate `<95 MiB` target. |
| Serialized state projection | **72.73% fewer bytes** (`286 B → 78 B`) | Byte serialization only; not evidence of a universal tokenizer reduction. |
| UDP localhost unicast | median **7.080 µs**, p95 **10.126 µs** | Synchronous localhost RTT proxy; not remote mesh gossip. |
| InjecAgent-derived hard gate | **0 / 868 attack transitions reached executable state** (`0.0000%` gate-layer ASR) | Bounded gate-layer test only; not official end-to-end InjecAgent ASR. |
| Legacy τ-bench trajectory preservation | **42 / 42 task-lane trials = 100.00%** | Bounded 6-task compatibility sample across 7 deterministic lanes; not official τ-bench pass^k. |
| 25-slot bounded daemon fleet | **25 / 25 exact-once DONE**, **0 duplicate fleet payloads** | **Still valid for this exact historical harness.** It must not be generalized to current integrated routing because the later Drive-2 upsert race reproduced a different concurrency defect. |

Repository scorecards:

- [`docs/INDUSTRY_BENCHMARK_SCORECARD.md`](./docs/INDUSTRY_BENCHMARK_SCORECARD.md)
- [`docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`](./docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md)
- [`docs/SECURITY_AND_ACCURACY_SCORECARD.md`](./docs/SECURITY_AND_ACCURACY_SCORECARD.md)
- [`docs/ADVANCED_BENCHMARKS.md`](./docs/ADVANCED_BENCHMARKS.md)

## Edge / local-first design boundary

AuraOS targets consumer-grade and constrained hardware by keeping the addressable world larger than the **active decision surface**. The design goal is to hydrate only the source-resolvable material needed for the current objective, then return to deeper evidence when the decision requires it.

The measured host-process RSS figures above do **not** establish whole-device or mobile-kernel memory usage. The `<95 MiB` narrow-runtime objective remains explicitly unresolved rather than being rewritten as achieved.

The local Aura Drive 2 design adds a second edge advantage: exact local computation can be pushed below the model. A local script that checks a source generation, computes a digest, runs a finite sweep, validates a schema, queries an index, or executes a test does not need a language model to spend context explaining how to perform that deterministic operation.

## Quickstart

Run long-lived processes in separate terminals as needed.

```bash
# 1. Clone and enter the repository
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

# 2. Start an Aura node
python aura_node.py

# 3. Start the Aura daemon
python aura_daemon.py

# 4. Start the swarm runner
python aura_swarm_runner.py
```

## Operating-economics evidence boundary

A historical staged manifesto carries a planning model comparing **$60–$180/month** for AuraOS local/edge operation with a **$4,900–$12,900/month** cloud-agent baseline, corresponding arithmetically to roughly **98.60–98.78% lower modeled monthly OpEx** at paired endpoints.

That planning model did **not** independently resolve the workload definition, provider/SKU assumptions, utilization, token volume, amortization, electricity/network inputs, or exact source model for those figures. It therefore remains a **staged operating-cost model, not an audited savings benchmark**, and the ~98% OpEx figure must not be relabeled as token compression.

The newer evidence layer above should be preferred for concrete claims: Paper X provider telemetry, HSC-196 real cold/coordinate reuse, and HSC-198 cold/warm swarm measurements are all narrower but better bound.

## Reproduce repository benchmarks

```bash
python3 scripts/aura_industry_benchmark_validation.py
python3 scripts/aura_advanced_benchmark_runner.py
python3 scripts/aura_security_accuracy_harness.py
```

Machine-readable outputs and signed/hashed receipts remain evidence of their declared execution scope. A signature or digest authenticates recorded material against its declared key/input; it does not independently establish human identity, semantic truth, currentness, or promotion authority.

## Scientific disclosure

See [**Paper X Rev.3 — PDF**](https://zenodo.org/records/22134815/files/PAPER-X%20%285%29.pdf?download=1) for the scientific disclosure, research claims, evidence boundaries, and architectural context for the AuraOS substrate. The canonical publication record is [Zenodo 22134815](https://zenodo.org/records/22134815).

## AGPLv3 public commons

AuraOS's current licensing posture is **GNU Affero General Public License v3.0 / AGPL-3.0-only**. The public-commons intent is that improvements to a network-accessible covered system remain inspectable and shareable rather than disappearing behind a closed service boundary.

Copyleft is a strong legal/governance barrier to enclosure, but it should not be described as an absolute guarantee against every possible outside patent filing, assertion, or independently written implementation.

## Canonical archive

- **Paper X Rev.3:** https://zenodo.org/records/22134815
- **DOI:** https://doi.org/10.5281/zenodo.22134815
- **Canonical Genesis Seed:** `67d2597bfa7895d997b89eb288a8f6cd5fe54ddc1ea69f676ec5d1a1ab96b002`

## Evidence provenance / synchronization note

This README preserves multiple evidence generations rather than flattening them:

- historical GitHub / Gate-1 repository measurements;
- Paper X Rev.3 publication evidence;
- later Aura Drive / Aura Drive 2 measurements and falsifiers;
- staged/nonpromoting ARCE and encryption/control research;
- earlier ledger/blockchain lineage whose security/economic claims are narrowed by later work.

Where later evidence narrows, supersedes, repairs, or falsifies an older headline, the old result remains visible under its original scope instead of being deleted. Current examples include the HSC-187 negative bypass result, HSC-193 bounded concurrency pass, HSC-198 live-swarm failure + warm coordinate-memory pass, the later integrated upsert-race reproduction, and the demotion of unvalidated physical entropy from a cryptographic root to an auxiliary input with zero credited security until independently characterized.

---

**Evidence rule:** verified results stay scoped to the exact harness/workload/generation that produced them; targets and unresolved claims remain labeled as such; later evidence may supersede a headline without rewriting history.
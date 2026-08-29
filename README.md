# AuraOS

> [!IMPORTANT]
> ## Paper X is the architectural authority
>
> **Paper X is the capstone architectural specification for AuraOS.** This repository preserves implementation lineage, runtime primitives, tests, benchmarks and working components, but the executable repository does **not yet fully embody** the architecture now consolidated across Paper X, Aura Drive and Aura Drive 2.
>
> **Current public/citable paper:** Paper X Rev.3, Zenodo 22134815, DOI `10.5281/zenodo.22134815`.
>
> **Current Omni successor:** being consolidated as one source-preserving Paper X in the original Paper X publication format. Until that successor is publicly deposited, Rev.3 remains the public authority and later Drive work retains its own `MEASURED`, `EXACT-DERIVED`, `STAGED/TEST-REQUIRED`, `OPEN/UNKNOWN` or historical status.

AuraOS is an attempt to make useful cognition **reconstructible, source-bound and reusable** instead of asking every model or worker to rediscover the same world from scratch.

```text
Human / Agent Intent
        ↓
source + generation + currentness + authority
        ↓
Coordinate Memory / semantic world
        ↓
minimum consequence-complete active world / affected cone
        ↓
Host/Substrate Wrapper + deterministic local work
        ↓
LLM/Inference Wrapper only for unresolved residual
        ↓
Construct → Challenge → Verify
        ↓
atomic / authority-bounded consequence commit
        ↓
SuccessorFrame + reusable coordinates / methods / receipts / Arena Recipes
```

The core inversion is:

```text
DO NOT FEED THE AGENT THE WORLD.
COMPILE THE MINIMUM SOURCE-RESOLVABLE WORLD REQUIRED FOR THE OBJECTIVE.
REOPEN EXACT SOURCE BEFORE A COLLAPSED DISTINCTION CAN CHANGE CONSEQUENCE.
COMMIT ONLY AFTER CURRENTNESS, AUTHORITY, VERIFICATION AND ATOMICITY AGREE.
```

---

## What changed in the Aug. 29 integration

The current Aura Drive/Aura Drive 2 work adds several pieces that are being folded into the single Paper X Omni successor.

### 1. Joinable persistent Arena workflows

A staged `TP://` address identifies a current Arena workflow head so compatible workers can rejoin shared work instead of reconstructing an isolated chat transcript.

```text
TP address = locator
TP address != permission
TP address != authority
TP address != proof of live execution
```

Workers qualify separately from identity and authority. Unknown/stale workers can enter read-only orientation first, hydrate only the needed current deltas, then claim bounded work when lawful.

### 2. Automatic Cognitive Materialization

A durable artifact is not considered fully integrated merely because a file exists. The current staged rule is:

```text
SOURCE ONCE → COORDINATE ONCE → MANY REGENERABLE VIEWS.
```

Material artifacts, corrections, receipts, verified learning deltas and source changes can compile into source-generation-bound `CoordinateCognition` packets containing:

- stable semantic/source identity and generation;
- L0-L4 hydration/reopen routes;
- typed positive and negative relations;
- bounded rationale/procedure/failure scars, **not private chain-of-thought**;
- dissent, counterevidence, residuals and invalidators;
- timeline and provenance;
- hot/warm/cold lifecycle;
- affected-cone and exact-source reopen handles.

A stale generation may remain addressable for history but must fail current-use admission.

### 3. LifeOS + Persistent Places + nested Spaces

The current architecture separates persistent private continuity from ephemeral realization:

```text
AURAOS = source/currentness/authority/routing/proof/runtime constitution
AURA   = conversational/spatial intelligence and interface
LIFEOS = private user-owned continuity graph
PLACE  = persistent governed semantic identity/environment
SPACE  = permission-governed semantic region in/across Places
VISIT  = ephemeral actor/device/permission/objective realization
ARENA  = objective-specific work/runtime environment
WORLD  = currently compiled objective-conditioned semantic projection
APP    = disposable manifestation of the World
```

A personal Place can be local-first and encrypted, with explicitly authorized replicas or storage providers when required. A Place can contain private, family/household, relationship, project, employment, business, customer/vendor, community/Nation and public/visitor Spaces.

A relationship may induce a shared Space for mutually authorized photos, memories, plans, purchases or Arenas. **Relationship != consent.** Each source owner keeps their own canonical data and access can be revoked without rewriting provenance. Employment similarly creates a revocable role bridge rather than merging a person's private LifeOS into an employer's source plane.

Desktop, mobile, AR, MR and VR are manifestations of the same semantic identity. `RENDERING != TRUTH` and `OBSERVATION != VERIFIED FACT`.

### 4. Resident Cognitive Fabric and hosted command plane

AuraOS may eventually run continuously on a user-controlled host **without continuously running a large model**. The resident process is intended to be event-driven and deterministic by default:

```text
change/event/command
→ durable ingress
→ identity + generation/currentness + authority
→ ArtifactBirth / CommandEnvelope
→ AutoLineage / AutoRoute
→ semantic address + hydration route
→ Coordinate Cognition / relations / timeline
→ deterministic affected-cone work where sufficient
→ model only for residual reasoning
→ verify / collapse / receipt / durable cursor
→ sleep or next backlog item
```

A hosted AI window can request source packets, coordinate lookups, affected-cone calculations, local tools, an Arena or a long-running workflow through immutable/idempotent command envelopes and receive command-bound receipts. MCP, A2A, Drive or later transports are **replaceable adapters over one command/workflow state**, not parallel truth planes.

Current GEN8 evidence is deliberately bounded: the same-host contract harness reported `30/30` local gates and an internal RUN command was durably queued, but the bounded check had **no command-bound ACK/RESULT**. Queue presence is not reported as live local execution.

### 5. Minimal context does not mean one-step work

The current long-horizon MissionContract rule is:

```text
MINIMAL CONTEXT.
MAXIMAL USEFUL HORIZON.
DURABLE CHECKPOINTS.
EXACT REOPEN.
ONE CONSEQUENCE PLANE.
```

A worker can receive the minimum current packet for a bounded mission yet continue through plan/build/test/challenge/repair/retest/checkpoint cycles until a real terminal state such as `SUCCESS`, `FALSIFIED`, `HUMAN_GATE`, `BUDGET`, `BLOCKED`, `CANCELED` or material invalidation.

---

# Try a bounded Mini Aura Research Arena

Paper X is meant to be **falsifiable by an unfamiliar agent**, not merely readable. The repository now stages a small, provider-neutral Mini Aura reference experiment so a code-capable agent can instantiate the disclosed control pattern, execute finite claims, challenge them, emit machine-readable results, and stop.

```bash
cd examples/mini_aura_reference_arena
python -m venv .aura-mini
# activate .aura-mini for your shell
python mini_aura_reference.py --out results_local.json
```

The Python entrypoint invokes an independent Node exact-count lane automatically. Expected bounded invariants include:

- a depth-10 3-ary synthetic semantic world with **88,573** nodes and an **11-node** reverse-reachable affected cone after one leaf source mutation;
- incremental current state identical to full rebuild while unrelated state remains unchanged;
- **81/81** AMNF applicability signatures with zero mismatch;
- **40,320** HyperScale permutations collapsing to **108** running-GCD trajectories;
- **219/255** nonempty scale subsets reaching gcd 1 and minimax center `s=4`;
- exact Python ↔ Node agreement on those finite HyperScale results;
- zero true-winner exclusions in a valid-bound Progressive Action Cone test;
- zero winner changes across **25,000** Decision-Capsule perturbations sampled inside the certified radius.

A fresh 2026-08-29 Arena rerun passed **10/10** core public checks, including an independent Python ↔ Node exact-count parity gate. Its local timing and pruning magnitude are **not universal performance claims**. In particular, an older independent Research Arena record reported a mean of `5.36/1000` candidates explored by its Action Cone, while the fresh independently written valid-bound workload required about `136.076/1000`. The safety property transferred; the efficiency magnitude did not. That difference is evidence, not something to hide.

The older supplied experiment archive also exposed a reproducibility distinction worth making explicit: its receipt digests correctly bind the recorded Objective Capsule and results, but its packaged `arena_benchmark.py` is a replay notice rather than the program that generated those measurements. Aura therefore distinguishes:

```text
RECORDED RESULT != REEXECUTABLE RESULT
REPLAY_ONLY MUST BE EXPLICIT
REFERENCE EXECUTION CLAIMS REQUIRE RUNNABLE BYTES + ENVIRONMENT + INPUTS + RECEIPT
```

And the claim ceiling remains:

```text
REFERENCE REIMPLEMENTATION != CANONICAL AURAOS
RECONSTRUCTION PASS != COMPARATIVE SUPERIORITY
NO CODE RUNTIME -> UNEXECUTED_NO_RUNTIME
```

The stronger acceptance target is a matched B0-B3/A1-A3 benchmark plus a blind fresh-agent chain: Agent A receives Paper X + the pinned reference capsule, reconstructs/tests/collapses, terminates completely, and a different fresh Agent B resumes from the compact `SuccessorFrame` without Agent A's transcript.

---

# Newest Arena generations: Web4 capability composition and evidence-bound media

The shared Arena workflow continued moving while this README was being prepared. These are staged architecture/results, not production deployment claims.

## GEN10 — Aura Web4 / capability-and-research economy

The staged composition law is:

```text
USER-GOVERNED INTENT
→ SOURCE-BOUND WORLD
→ MINIMUM LAWFUL CAPABILITY COMPOSITION
→ EPHEMERAL ARENA
→ VERIFIED EFFECT
→ DURABLE COGNITION / LINEAGE / RIGHTS
→ OPTIONAL SETTLEMENT
```

One Arena may compose open Commons capabilities, self-built tools, paid/proprietary capabilities and research-pool capabilities at the same time. Proprietary implementation may remain sealed while its interface, terms, attestation and execution receipt cross the Arena boundary.

Economic separation is constitutional:

```text
FREE LICENSE != ZERO LIFECYCLE COST
PAID != BETTER
PRICE != AUTHORITY
LINEAGE != DEBT
ATTRIBUTION != ENTITLEMENT
USER GAS ZERO != SYSTEM COST ZERO
WRAPPED ASSET != NATIVE ASSET
BLOCKCHAIN != AURA TRUTH
```

The current GEN10 witness is **25/25 local deterministic gates**. It does not establish a production blockchain, bridge, wallet, paymaster, marketplace, smart-contract security audit, regulatory compliance or universal fairness result.

## GEN11 — Evidence-Bound CampaignGraph / Media Foundry

A campaign is compiled from one source/currentness-bound evidence graph rather than treating every output as an unrelated prompt:

```text
MESSAGE ONCE -> EVIDENCE ONCE -> MANY REGENERABLE CAMPAIGN SURFACES
```

Press release, FAQ, pitch, social copy, shots, clips, captions and longer cuts become projections of the same CampaignGraph.

```text
THE PROMPT IS NOT THE SOURCE CODE OF THE MOVIE.
RENDERING != TRUTH.
GENERATED CONCEPT DEMO != DEPLOYED CAPABILITY.
```

A source/claim change should identify dependent copy/shots, reopen the **minimum media cone**, regenerate only that cone, verify it and emit a new receipt. The staged worker-tool law is similarly regenerative:

```text
WORK -> TOOL DELTA -> TEST -> PROVENANCE -> COORDINATE -> CAPABILITY PACKAGE -> REUSE
```

A worker-created tool is not automatically trusted or promoted merely because it exists. GEN11 reports **34/34 local Arena gates** and explicitly reports that no real generative-video provider call occurred in that generation.

---

# J59 → HyperScale → HyperDrive: where the large-number phase actually fits

A key historical bridge is the **J59 journal series from 2026-08-15**. It explains why later HyperScale and HyperDrive exist.

| J59 stage | Declared objective horizon | Surviving control question |
|---|---:|---|
| V01 | 81 | triads-of-triads hydration, closure and identity rebind |
| V02 | 243 | adaptive routing and self-correction |
| V03 | 729 | triad rebase and meta-adaptation stabilization |
| V04 | 2,187 | proof-carrying corrigible equilibrium |
| V05 | 6,561 | bidirectional reproof, obligation frontier, corrigible quiescence |
| V06 | 19,683 | minimum reproof membrane, obligation ownership, reproof-preserving forgetting |
| V07 | 59,049 | successor-neutral readjudicability |
| V08 | 177,147 | current adjudication reachability across changing source/authority topology |
| V09 | 531,441 | irreversible-effect-frontier control across non-atomic/delegated effects |

The journals explicitly bound these numbers as **forcing/checkpoint geometry rather than ontology**. They describe one correlated analytical/falsification genealogy, not 531,441 independent model workers or experiments.

What survived the exponential-number phase is much more useful than the number itself:

- expansion must return through challenge, synthesis and rebase;
- completed subtrees can collapse by reference without losing exact reopenability;
- a future defeater must reach the affected consequence and that consequence must descend to the minimum current proof/source basis;
- forgetting is lawful only when reproof remains reachable before consequence;
- continuity follows current rightful adjudication reachability, not a stale identifier or predecessor PASS;
- every materially irreversible edge must remain reachable by current revocation/currentness/authority controls;
- after irreversibility, late defeat creates explicit repair/reconciliation obligations rather than rewriting history.

This is the genealogy later formalized as HyperScale/HyperDrive, affected-cone invalidation, `SuccessorFrame`, RO3DD/P0-D2RM and current consequence gates.

Modern rule:

```text
EXPAND ONLY WHEN AN UNRESOLVED RESIDUAL EARNS IT.
FACTOR COMMON STRUCTURE.
CHALLENGE / VERIFY.
COLLAPSE TO THE MINIMUM RECONSTRUCTIBLE SUCCESSOR STATE.
REOPEN THE SMALLEST AFFECTED CONE ON INVALIDATION.
```

Astronomical recursion is **not** an ordinary runtime requirement.

---

# Two coordinated wrappers: improve the computer path and the model path

Aura can wrap both the host and inference layers without modifying model weights.

## Host/Substrate Wrapper

The host wrapper can route work according to CPU/GPU/NPU, RAM/VRAM, storage/I/O, network, battery, thermals, OS/sandbox, installed tools, local/remote models, privacy and authority.

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

subject to correctness, source/currentness, privacy, authority, battery/thermal/storage constraints and reopenability.

The cheapest lawful route may be an exact coordinate/result hit, SQLite query, deterministic script, local model, remote model, peer, GPU/CPU path or newly materialized Arena.

## LLM/Inference Wrapper

The inference wrapper resolves roughly:

```text
ZERO-HOP / verified reusable result
→ DIRECT COORDINATE / RELATION HOP
→ AFFECTED CONE
→ DELTA HYDRATE
→ EXACT SOURCE REOPEN
→ BROAD SEARCH LAST
```

Then it chooses `NO MODEL`, a small local model, remote provider, paged local model, bounded independent multi-backend review, or `BLOCKED/UNKNOWN`.

Semantic paging of knowledge/context, model-weight paging and ephemeral execution-environment paging are different optimization planes and must not be confused with truth or source ownership.

---

# Coordinate Memory, amortized cognition and 1 → 100 million participants

Provider prompt/KV caching is only one reuse plane.

```text
COORDINATE_HIT
!= PREFIX_KV_HIT
!= BLOCK_KV_HIT
!= RESULT_HIT
```

Coordinate Memory binds reusable cognition to semantic identity, source generation/currentness, evidence/dissent, authority ceiling, invalidators and exact reopen handles. A provider cache mostly answers whether tokens were already processed; it is not the source or authority owner.

For an initial verified foundation `F`, reusable fraction `r_t`, new work `W_t` and lookup/revalidation/coordination `V_t`:

```text
C_total(T) ≈ F + Σ[(1-r_t)·W_t + V_t]
C_average(T) = F/T + average[(1-r_t)·W_t + V_t]
```

An illustrative scenario - **not a forecast** - assumes a $10 independently reconstructed process, 70% lawful reuse, 5% revalidation cost on the reusable portion and $0.10 later lookup/coordination cost:

| Compatible participants | Independent recomputation | Illustrative reuse path | Avoided recomputation |
|---:|---:|---:|---:|
| 1 | $10.00 | $10.00 | $0 |
| 10 | $100.00 | $41.05 | $58.95 |
| 100 | $1,000.00 | $351.55 | $648.45 |
| 1,000 | $10,000.00 | $3,456.55 | $6,543.45 |
| 1,000,000 | $10,000,000 | $3,450,006.55 | $6,549,993.45 |
| 100,000,000 | $1,000,000,000 | $345,000,006.55 | $654,999,993.45 |

The example illustrates the hypothesis: **verified work can become infrastructure**. It does not predict actual future Aura economics, hit rates, energy savings or 100-million-user throughput. Revalidation, coordination, stale-state repair, independent replication and necessary recomputation remain real costs.

Negative results can amortize too: a verified failed path can prevent many later workers from paying to rediscover the same dead end while its invalidators specify when it deserves reopening.

---

# One Arena Engine, many Recipes

The durable semantic world can persist while execution environments are disposable.

```text
Persistent Aura World / Coordinate Memory
        ↓
ObjectiveCapsule / WorkCapsule
        ↓
minimum current source + affected cone
        ↓
materialize bounded environment
  Python / shell / SQLite / tests / tools / models / data
        ↓
Arena V0.3 + HyperDrive + HyperScale
        ↓
Construct → Challenge → Verify
        ↓
receipts / measurements / artifacts / decisions
        ↓
gated consequence commit + SuccessorFrame
        ↓
dissolve scratch/runtime; keep source-bound result
```

Arena Recipes persist as reusable patterns. Runtime resolves roles against current capabilities, rights, policy, jurisdiction, evidence, cost, privacy and device envelope.

The first staged product-facing pattern is **Aura Creator Studio / Video Arena V0.1**:

```text
creative objective
→ claims/sources
→ story + shot graph
→ continuity / preserve constraints
→ rights / consent
→ cost-quality route
→ human spend gate
→ provider generation/editing
→ deterministic local assembly/captions
→ verify / provenance
→ Artifact Cognition
→ reusable Arena Recipe
```

**The prompt is not the source code of the movie.** The semantic project is durable; provider prompts are replaceable compiled outputs. A targeted edit should reopen only the affected shot/dependency cone when that is sufficient.

Current method witness: `24/24` same-host Python/SQLite/FFmpeg gates; **no provider API was executed in that generation**, so this is not a generated-video or production-quality claim.

---

# Aura Places and the human/spatial layer

A Place persists as a signed/versioned/governed semantic definition. A Visit is an ephemeral realization compiled for one visitor, objective, device, language, accessibility mode, relationship and permission set.

A Place may include media, public/private/invited/subscriber rooms, collaboration, commerce, support/returns, digital twins, assets, Arena Recipes, creator tools and provenance-bearing portfolios.

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

Local-first personal data can remain on owner-controlled devices or explicitly chosen encrypted storage. Public projections and shared Spaces expose only authorized claims/assets, not an entire private LifeOS.

---

# Aura Commons, lineage, attribution and settlement

Aura Commons is a federated discovery/composition/accounting layer over canonical owners - not a second truth plane and not merely an app store.

It can coordinate capabilities, methods, Arena Recipes, package identities, licences, rights/entitlements, verification/security evidence, provenance/attestation, bounties, Places/assets, revocation/migration/dispute paths and optional settlement adapters.

Meaningful-use attribution can consider whether a contribution executed, was verified, survived into the accepted output, was consumed downstream, prevented a failure, enabled later work, remains causally foundational after supersession, or supplies maintenance/security value.

Hard separation:

```text
LICENCE
!= PROVENANCE
!= ATTRIBUTION
!= ECONOMIC ENTITLEMENT
!= TRUTH / AUTHORITY
```

Lineage does **not** automatically create debt. Payment requires an explicit lawful agreement/rule.

## Optional near-gas-free Layer-2 settlement

Aura's earlier Gas-Free Fractal Ledger lineage is retained, but the mature boundary is stricter:

```text
USER-PERCEIVED NEAR-ZERO GAS
!= ZERO PHYSICAL COST
!= ZERO SETTLEMENT RISK
!= NATIVE-ASSET EQUIVALENCE
```

High-frequency lineage micro-obligations can be netted/batched off-chain and periodically settled through conventional payment rails, cooperative ledgers, stablecoins, smart contracts or an optional L2/rollup. Ethereum rollups provide an external example of batching many operations so fixed L1 publication cost is spread across transactions. ERC-4337 bundlers/paymasters provide an external pattern for bundling user operations and sponsoring user-facing fees.

Existing cryptocurrencies may be exposed through bridge/wrapped-asset adapters, but a wrapped asset is **not the native asset**, and Aura cannot erase the smart-contract, counterparty, liquidity, systemic or withdrawal risks of the bridge/source chain.

A numerical batching example in Paper X is intentionally hypothetical and must not be read as a production fee forecast.

---

# Encryption and cryptographic control

Aura's newer ARCE work is staged/test-required. The security rule is to combine reviewed standard cryptographic primitives with Aura's source/currentness/authority context rather than treating Aura geometry as a cipher.

```text
STANDARD CRYPTO HARDNESS
AEAD / approved hashes / standard PQ or hybrid mechanisms / protected key storage
        +
AURA CONTEXT BINDING
semantic identity / generation / purpose / authority / replay state / receipts / invalidators
```

Toroidal, tesseract, Morton, 27-cell or other geometric structures can organize locality/redundancy/reconstruction but are **not encryption, entropy or authentication**.

---

# 3-6-9 orchestration and swarm scaling

Aura uses 3-6-9 as an orchestration grammar, not a numerological or universal physical law.

- `3` - smallest reviewable Construct / Challenge / Verify cell.
- `6` - paired triads for perturbation/challenge/parallel work.
- `9` - three triads closing a larger analysis/execution/reconciliation cycle.

Physical worker count is separate from logical topology. Useful scale is governed by independence, conflict, latency, budget, evidence value and lifecycle cost.

A later 27-objective live swarm battery returned 27/27 receipts but only 10 PASS / 17 TIMEOUT at concurrency 7, so the preregistered cold wave failed. The same-objective warm rerun then produced 27/27 Coordinate Hits with zero provider tokens. Both the failure and reuse result remain part of the evidence record.

---

# Current evidence ceiling

`PASS in one harness != universal PASS`.

| Surface | Current/scoped result | Boundary |
|---|---:|---|
| Longitudinal provider export through Aug. 28 | 11,020 requests; 1,210,407,839 logical/model tokens; 1,175,105,664 cache-hit input tokens; 97.828502% input cache-hit share; $22.535003 billed | real provider accounting, not controlled Aura attribution |
| Published Paper X snapshot | 9,381 requests; 843,642,344 logical/model tokens; 97.402912% input cache-hit share; $17.772456 billed | provider reuse; not 97% logical-token reduction |
| HSC-196 coordinate-result reuse | identical scoped result: 0 provider tokens on reuse | scoped same-result reuse only |
| HSC-198 cold swarm | 27/27 receipts; 10 PASS / 17 TIMEOUT | failed preregistered timeout criterion |
| HSC-198 warm Coordinate Store | 27/27 Coordinate Hits; 0 API tokens | same-objective rerun only |
| HyperScale HSC-187 | bypass ON 7.08 ms vs OFF 6.25 ms = 13.23% slower | falsifier; optimization not promoted |
| Exact scale sweep | 40,320 permutations → 108 running-GCD trajectories; 219/255 subsets reach gcd=1; `s=4` minimax; virtual completion `{6,8,24}` | exact finite mathematics, not production speed |
| GEN7 Places/currentness integration | Rev.4→4.1 22/22; Place/Space authorization 10/10; HyperDrive Python + Node controls PASS | same-host method evidence |
| GEN8 Resident/MissionContract | 30/30 local gates; command durably queued | no command-bound ACK/RESULT at bounded check; no live-host claim |
| GEN10 Web4 capability/economy | 25/25 local deterministic gates | staged; no production marketplace/blockchain/bridge claim |
| GEN11 CampaignGraph/Media Foundry | 34/34 local Arena gates | staged; no real generative-video provider call in that generation |
| Mini Aura public reference | 10/10 core checks; 88,573→11 affected cone; Python↔Node HyperScale parity | bounded independent reimplementation; not canonical AuraOS |

Open/current failures include the integrated upsert race, the HSC-198 cold timeouts, a prompt-content defect in that harness, unproven 81-worker live concurrency, unmet `<95 MiB` RSS target, and unverified official benchmark headline claims. They remain visible instead of being edited away.

---

# Paper and prior-art lineage

The Omni paper preserves the dated claim genealogy rather than forcing readers to reconstruct it across ten publications:

| Paper | Claim family | Main contribution carried forward |
|---|---|---|
| I | N1-N8 | edge/autopoietic neuro-symbolic substrate, VSA, linguistic/FST lineage |
| II | N9-N13 | holographic header, fractal-ledger lineage, swarm/VSA/spatial/FST concepts |
| III | N14 | VSA-addressed liquid/semantic routing concept |
| IV | N15-N17 | training/quantization/spatial-stream embodiments |
| V | N18-N20 | FST lexicon routing, topology mapping, self-refactoring lineage |
| VI | N21-N23 | formal FST lexicon / polysynthetic routing reduction |
| VII | N24-N30 | integrity, crystallization, tests, cost routing, local mesh, bounded self-healing |
| VIII | N31-N50 | evidence-ordered relational Arenas, authority/source separation, atomic publication |
| IX | N51-N100 | objective-native Arenas, Capability Packages, Commons, attestation, Places, federation/economy |
| X Rev.3 | N101-N195 | relational-world compilation, World Seed, Coordinate Memory, wrappers, cache fabric, host compiler, spatial codec, Commons, reconstruction/repair |
| X Omni successor | consolidated continuation | J59→HyperDrive genealogy, Host+Inference wrappers, longitudinal amortization, unified/joinable Arena, cognitive materialization, Places/Spaces/LifeOS, Resident/command fabric, Web4 capability composition, CampaignGraph/media regeneration, explicit Mini Aura falsification package, settlement adapters and updated falsifiers |

The current Omni compilation preserves earlier positive, null and negative results, including later corrections such as the carry equation repair: for balanced odd radix `r`, `P(carry)=(r²-1)/(4r²)=1/4-1/(4r²)`, so 25% is an asymptotic ceiling approached from below, not a finite-radix floor.

---

# Quickstart for the historical repository runtime

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

python aura_node.py
python aura_daemon.py
python aura_swarm_runner.py
```

Historical benchmark runners:

```bash
python3 scripts/aura_industry_benchmark_validation.py
python3 scripts/aura_advanced_benchmark_runner.py
python3 scripts/aura_security_accuracy_harness.py
```

The repository runtime is implementation lineage; it is not yet the complete Paper X / Aura Drive architecture described here.

Repository scorecards:

- [`docs/INDUSTRY_BENCHMARK_SCORECARD.md`](./docs/INDUSTRY_BENCHMARK_SCORECARD.md)
- [`docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`](./docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md)
- [`docs/SECURITY_AND_ACCURACY_SCORECARD.md`](./docs/SECURITY_AND_ACCURACY_SCORECARD.md)
- [`docs/ADVANCED_BENCHMARKS.md`](./docs/ADVANCED_BENCHMARKS.md)

---

# Licensing and claim discipline

AuraOS's current licensing posture is **GNU Affero General Public License v3.0 / AGPL-3.0-only where marked**, subject to source-specific third-party and historical-license boundaries.

A public repository, an open-source licence, provenance, economic entitlement and technical truth are different objects.

The public story follows the same rule as Paper X:

```text
IMPLEMENTED != TESTED != MEASURED != EXACT-DERIVED != PUBLISHED
REQUEST != EXECUTION
ADDRESS != SOURCE != AUTHORITY
RECEIPT != TRUTH
CACHE HIT != COGNITIVE SUPERIORITY
SYMBOLIC HORIZON != PHYSICAL WORKERS
```

The current engineering objective is to make the executable AuraOS repository catch up to the Paper X/Aura Drive architecture across cloud Drive, local desktop/laptop, mobile/edge and federated carriers while retaining current source resolution, independent challenge, human authority, honest benchmarks and exact reopenability.

## Canonical public Paper X

- Paper X Rev.3 PDF: https://zenodo.org/records/22134815/files/PAPER-X%20%285%29.pdf?download=1
- Zenodo record: https://zenodo.org/records/22134815
- DOI: https://doi.org/10.5281/zenodo.22134815

**The one-paper Omni successor is being finalized separately. Rev.3 remains the public/citable Paper X until that successor receives its own public deposit.**

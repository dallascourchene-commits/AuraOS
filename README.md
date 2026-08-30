# AuraOS

> [!IMPORTANT]
> ## Paper X remains the architectural authority
>
> **Current public/citable paper:** Paper X Rev.3 — Zenodo `22134815`, DOI `10.5281/zenodo.22134815`.
>
> This repository now contains staged reference implementations and currentness successors that extend beyond Rev.3. Until the next Paper X successor is publicly deposited, later work retains its own evidence class: `MEASURED`, `EXACT-DERIVED`, `STAGED/TEST-REQUIRED`, `OPEN/UNKNOWN`, or historical.
>
> `REPOSITORY != PAPER AUTHORITY` · `REFERENCE IMPLEMENTATION != PRODUCTION DEPLOYMENT` · `RECEIPT != TRUTH`

AuraOS is a **source-bound cognitive substrate**: useful cognition, source/currentness, failure evidence, authority boundaries and exact reopen paths live outside any one model/session so future workers can reconstruct the minimum world required for an objective instead of rediscovering the same world from scratch.

```text
human / agent intent
        ↓
source + generation + currentness + authority
        ↓
Root Arena / recursive Sub-Arenas
        ↓
domain lens + Temporal NOW + Coordinate Memory
        ↓
minimum lawful L0-L4 hydration
        ↓
deterministic work first
        ↓
ExpertBundle only for unresolved residual
        ↓
Construct → Challenge → Verify
        ↓
authority-bounded consequence
        ↓
SuccessorFrame + receipts + reusable cognition/capabilities
```

The governing inversion is:

```text
DO NOT FEED THE AGENT THE WORLD.
COMPILE THE MINIMUM SOURCE-RESOLVABLE WORLD REQUIRED FOR THE OBJECTIVE.
REOPEN EXACT SOURCE BEFORE A COLLAPSED DISTINCTION CAN CHANGE CONSEQUENCE.
```

---

# Current Aug. 29 architecture

## 1. Persistent Arena → recursive Sub-Arenas

The durable Arena is a source-bound project/workflow world. A Python venv, container, hosted model, provider call or swarm worker is a replaceable realization inside it.

```text
tp://arena/<arena_sid>/subarena/<semantic_sid>
<stable address>?g=<generation>&head=<manifest_digest_16>
```

Every admitted durable project, tool, research direction, campaign, Place, workflow or finding can expose an L0 doorway with exact deeper reopen routes:

```text
L0 = compact portal / purpose / current source pointers
L1 = dependencies + relations + equations + scripts + commands
L2 = working neighborhood + residuals + receipts + affected cone
L3 = operating model + algorithms + tests + capability/swarm recipes
L4 = exact source + code + receipts + benchmark bytes
```

`SUB-ARENA != SOURCE OWNER`  
`PORTAL != BODY COPY`  
`ADDRESS != AUTHORITY`

A fresh worker should enter through Root L0, resolve the objective to candidate Sub-Arenas, expand only hard dependencies, see lateral overlaps, and hydrate deeper only when consequence earns it.

## 2. Temporal Arena / `ArenaNowCapsule`

Semantic topology answers **what relates to what**. Temporal topology answers **what changed, what is active, what is blocked, what is due, and what wakes next**.

```text
ARENA STATE
= SEMANTIC GRAPH
× TEMPORAL GRAPH
× SOURCE/CURRENTNESS
× AUTHORITY
```

Aura distinguishes:

```text
EVENT_AT != RECORDED_AT != DUE_AT
TEMPORAL ADJACENCY != CAUSAL DEPENDENCY
TODO != WORK ORDER
SCHEDULER != AUTHORITY
```

The intended resident surface is a bounded `ArenaNowCapsule`: active/ready/blocked/waiting/stale work, reminders, human decisions, claims/leases, next wakes, critical dependencies, recent material deltas and exact cold-history reopen handles.

A fresh worker should not have to reread the entire TODO list, JSpace ledger, calendar, Drive modification history and predecessor chats just to discover what matters now.

## 3. DomainLensShardV1 + Kaleido-27

One canonical source object may be important in different ways for different domains without duplicating truth.

```text
DomainLensShard(object, domain, objective)
=
source identity
+ source generation
+ relation subset
+ salience / residency
+ L0-L3 projection
+ exact L4 reopen
+ invalidators
+ authority ceiling
```

```text
rho(object | domain, objective, time)
∈ { HOT, WARM, COLD, TRANSIENT, FENCE, BLOCK }
```

`LENS != SOURCE OWNER`  
`SALIENCE != TRUTH`  
`DOMAIN DIFFERENCE != EVIDENCE INDEPENDENCE`

### The 27 boundary is ternary, not binary

The current reference uses:

```text
K27(object, domain) ∈ {0,1,2}^27
3^27 = 7,625,597,484,987 states
≈ 42.794 binary bits of capacity
```

That is **27 trits**, not a canonical 27-bit semantic ID.

The checked reference uses `SHA-256(SID|domain) mod 3^27`. Independent characterization shows that it behaves as a useful uniform hash partition, **not a semantic-locality hash**. Semantic locality lives above it in Sub-Arena scope, dependency structure, DomainLens, Coordinate Memory and Temporal NOW.

```text
SEMANTIC SCOPE FIRST
→ PHYSICAL SHARD SECOND
```

Canonical identity remains stable semantic SID + source owner + generation/currentness. A K27 collision falls back to semantic disambiguation.

## 4. Adaptive ternary prefix sharding

One 27-trit K27 key can be partitioned at different prefix depths without re-keying:

| Prefix | Partitions |
|---:|---:|
| 3 trits | 27 |
| 6 trits | 729 |
| 9 trits | 19,683 |
| 12 trits | 531,441 |
| 15 trits | 14,348,907 |
| 18 trits | 387,420,489 |
| 27 trits | 7,625,597,484,987 |

At 100M uniformly distributed lens entries, ideal load is approximately 3.70M entries at a 3-trit prefix, 137k at 6, 5,081 at 9, 188 at 12, and 7 at 15.

This makes prefix depth a candidate physical cache/storage/work-routing knob across edge devices, workstations, servers, Commons indexes and research pools. It does **not** make K27 the source or meaning of the object.

## 5. Resident Cognitive Fabric: ChatGPT ↔ Aura ↔ OpenCode/DeepSeek

AWJ-015 stages the resident seam between Drive transport and governed local execution.

After one-time host bootstrap, the target resident can:

- observe configured Aura Drive roots and local AuraOS changes;
- maintain durable currentness cursors;
- allocate deterministic L0 state without waking a model for every artifact;
- maintain SQLite WAL backlog, claims, leases and restart/idempotency state;
- admit bounded D0 commands automatically while D1+ remains human-gated;
- dispatch bounded work through an OpenCode/DeepSeek adapter when configured and authorized;
- expand the preregistered 9-task `R/B/A` benchmark into 27 provider tasks only under exact causal/provider/budget gates;
- return command-bound result envelopes to the outbound bus;
- keep read-only observer and bounded writer credentials separate.

Reference status:

```text
17/17 local clean-room gates PASS
compileall PASS
live owner-host installation / live DeepSeek execution: not established by that receipt
```

The success condition is deliberately stronger than “a command file exists”:

```text
ChatGPT writes authorized command
→ resident consumes it
→ bounded worker executes
→ command-bound ACK/RESULT/ERROR returns
```

`QUEUE PRESENCE != EXECUTION`.

## 6. Expert Fabric: only use the expert mixture the residual earns

AWJ-016 composes semantic routing with replaceable execution backends:

```text
source/currentness/authority/privacy
→ Sub-Arena + domain + Temporal NOW
→ minimum WorkCapsule
→ ExpertBundle
→ execution backend(s)
→ Construct / Challenge / Verify
→ HyperDrive collapse
```

Current staged route classes:

```text
NO_MODEL
LOCAL_FAST
AIRLLM_LARGE_LOCAL
PINNED_REMOTE_MODEL
HETEROGENEOUS_TRIAD
```

The critical separation is:

```text
K27 != MoE expert ID
DOMAIN != model-internal expert number
MODEL-INTERNAL MoE GATE != Aura semantic router
```

Aura selects the lawful **model/backend/role mixture**. A sparse-MoE model may then choose its own internal experts independently.

### AirLLM

AirLLM is treated as a **paged local inference/materialization backend** for private/offline/batch work where local sovereignty may matter more than layer/offload latency. It is not the default interactive path and not Aura's semantic router.

Upstream AirLLM projects advertise unusually strong memory-capacity claims; those claims are third-party claims, not Aura measurements, and require their own reproducible hardware/model/revision benchmark evidence before Aura should depend on them publicly.

### Cache identity

A K27 shard or semantic coordinate must never be a model KV-cache identity by itself. The staged minimum binding is:

```text
semantic SID
| source generation
| domain/task
| concrete model identity
| preset generation
| WorkCapsule digest
```

Production should additionally bind tokenizer/model revision, system prompt, tool schema, inference parameters, endpoint/provider class and provider-specific cache namespace where relevant.

---

# Current bounded evidence

| Surface | Current result | Establishes | Does not establish |
|---|---:|---|---|
| Mini Aura reference Arena | 10/10 public core checks | finite reconstructible reference invariants + Python/Node parity | production AuraOS / superiority |
| DomainLens/K27 reference | 13/13 PASS | one-source/many-lenses, residency, affected cone, 27-trit parity, fail-closed collision handling | causal reasoning-quality gain |
| Independent K27 stress | 300,000 keys / 0 full collisions observed | useful uniform partition behavior in tested sample | K27 as canonical identity |
| K27 semantic-locality falsifier | mean Hamming `17.99766/27` over 50k related pairs | current SHA-based K27 is effectively random wrt semantic edit locality | failure of higher semantic scope |
| Expert Fabric | 18 Python gates + independent Node K27 parity witness | deterministic ExpertBundles, privacy gates, model/source cache binding, route classes | live AirLLM/provider inference |
| Resident Cognitive Fabric | 17/17 clean-room + compileall | reference observe/backlog/dispatch/receipt mechanics | live installed resident/provider execution |
| Web4 reference | 25/25 local deterministic gates | bounded capability/economic semantics | production marketplace/L2/bridge |
| Campaign/Media Foundry | 34/34 local gates | evidence-bound CampaignGraph / affected-media logic | provider-generated production footage / deployed XR |

## Fresh nine-task routing/hydration ablation

A deterministic ablation compares:

```text
R = regular broad orientation
B = rebase-only hard dependency closure, without domain-lens narrowing
A = full Aura structural route:
    hard closure + selected domain lenses + bounded WorkCapsule + ExpertBundle
```

The checked graph has 16 object SIDs × 6 domains = 96 possible object-domain projections. The benchmark assigns every projection the same synthetic 4 KiB hydration cost and every A-task an additional 2 KiB WorkCapsule cost. It isolates **routing structure**, not LLM intelligence or provider billing.

Across nine frozen Aura maintenance/research tasks:

| Condition | Projection-equivalents hydrated | Equal-cost bytes |
|---|---:|---:|
| R — regular broad | 864 | 3,538,944 |
| B — rebase-only | 342 | 1,400,832 |
| A — full Aura route | 114 | 485,376 |

Structural reductions:

```text
A vs R: 86.2847%
A vs B: 65.3509%
B vs R: 60.4167%
```

Full-Aura route policy selected:

```text
3 × NO_MODEL
2 × LOCAL_FAST
2 × AIRLLM_LARGE_LOCAL
1 × PINNED_REMOTE_MODEL
1 × HETEROGENEOUS_TRIAD
```

If all selected backends were present and authorized, the heterogeneous Triad represents three independent-model calls, for eight model calls across the nine tasks. **No provider or AirLLM inference was executed in this deterministic ablation.**

The `86.2847%` figure therefore means **fewer equal-cost hydration bytes in this bounded structural workload**. It does not mean 86% smarter, cheaper or faster end-to-end.

## Current discrepancy preserved instead of hidden

GEN16 prose records a `24/96` scope-before-route example. The currently checked executable reference yields `22/96` for its present seed/domain selection.

```text
96 possible object-domain projections
11 objects in hard dependency closure
2 selected domains
22 detailed lens projections
≈ 77.08% of object-domain combinations pruned before detailed traversal
```

This is routing-space reduction, not equivalent token/cost/quality reduction. The 22/96 vs 24/96 difference remains an explicit currentness/reconciliation item.

---

# Small/local models and swarms

The high-leverage candidate is not a magic ternary identifier. It is **precompiling the worker's relevant cognitive neighborhood before inference begins**.

Conventional fresh-worker pattern:

```text
objective
→ broad corpus/search
→ retrieve many chunks
→ model reconstructs relationships/currentness
→ model decides what matters
→ work
→ next worker repeats much of the orientation
```

Aura target pattern:

```text
objective
→ Root L0
→ hard dependency closure
→ domain lens
→ Temporal NOW
→ K27 physical shard/cache
→ currentness + authority gate
→ L0/L1 hot packet
→ exact L4 only as earned
→ ExpertBundle only for unresolved work
→ ArtifactBirth / affected cone
→ HyperDrive successor
```

This should matter most when the durable graph is large, many workers operate concurrently, a small local model cannot ingest the whole world, privacy favors local work, source generations change frequently, or only a small residual warrants expensive inference.

HyperScale therefore asks:

```text
HOW MUCH INDEPENDENT UNRESOLVED FRONTIER EXISTS?
```

not:

```text
HOW MANY AGENTS CAN WE SPAWN?
```

Current swarm policy prefers `0/1/3/9` workers when sufficient. Twenty-seven physical provider calls are reserved for a preregistered matched experiment or another independently justified frontier; logical `3×3×3` geometry is not a mandate to buy 27 model calls.

---

# Reproduce the bounded references

## Mini Aura

```bash
cd examples/mini_aura_reference_arena
python -m venv .aura-mini
# activate .aura-mini for your shell
python mini_aura_reference.py --out results_local.json
```

Finite invariants include:

- depth-10 ternary world: 88,573 nodes;
- 11-node reverse-reachable affected cone after one leaf mutation;
- 81/81 AMNF applicability signatures;
- 40,320 HyperScale permutations → 108 running-GCD trajectories;
- 219/255 nonempty scale subsets reaching gcd 1;
- Python/Node exact-count parity;
- valid-bound Action-Cone and Decision-Capsule safety checks.

## DomainLens / K27

```bash
cd examples/arena_navigation_domain_lens
python domain_lens_reference.py
```

## Expert Fabric + structural R/B/A

```bash
cd examples/arena_expert_fabric
python checks.py
python paired_rba_systems_benchmark.py
```

These references intentionally test bounded control semantics. They are not production performance demonstrations.

---

# LifeOS / Places / Worlds / disposable apps

```text
AURAOS = governed source/currentness/authority substrate
AURA   = conversational/spatial intelligence/interface
LIFEOS = private user-owned continuity substrate
PLACE  = persistent governed semantic identity/environment
SPACE  = permission-governed semantic region
VISIT  = ephemeral actor/device/permission/objective realization
ARENA  = objective-specific runtime/workspace
WORLD  = objective-conditioned semantic projection
APP    = disposable realization of the World
```

Persistent Place/Space/Coordinate Cognition can be projected into desktop, phone, accessible 2D, headless-agent, AR/MR/XR or later interfaces without making the render authoritative.

```text
RENDERING != TRUTH
OBSERVATION != VERIFIED FACT
RELATIONSHIP != CONSENT
PRIVATE LIFEOS != PUBLIC PROFILE
```

---

# Aura Web4 / Commons / capability economy

A staged Arena may compose:

- free/open Commons capabilities;
- self-built tools;
- community/public-good capabilities;
- paid/proprietary capabilities;
- source-bound R&D-pool outputs.

```text
USER-GOVERNED INTENT
→ MINIMUM LAWFUL CAPABILITY COMPOSITION
→ EPHEMERAL ARENA
→ VERIFIED EFFECT
→ COGNITION / LINEAGE / RIGHTS
→ OPTIONAL SETTLEMENT
```

```text
FREE LICENSE != ZERO LIFECYCLE COST
PAID != BETTER
PRICE != AUTHORITY
LINEAGE != DEBT
ATTRIBUTION != ENTITLEMENT
USER-VISIBLE GAS ≈ 0 != SYSTEM COST 0
WRAPPED ASSET != NATIVE ASSET
BLOCKCHAIN != AURA TRUTH
```

Optional L2/paymaster/batched-settlement concepts remain staged; this README does not claim a production bridge, wallet, paymaster, custody system, audited contract or regulatory approval.

---

# Creator Studio / evidence-bound media

Creator Studio applies the same source/currentness model to media:

```text
MESSAGE ONCE
→ EVIDENCE ONCE
→ MANY REGENERABLE CAMPAIGN SURFACES
```

Claims, evidence, story graph, shots, continuity, rights, provider attempts, accepted assets and provenance persist. Provider prompts/clips are replaceable realizations.

```text
THE PROMPT IS NOT THE SOURCE CODE OF THE MOVIE.
GENERATED CONCEPT VISUALIZATION != IMPLEMENTATION EVIDENCE.
```

A source claim change should reopen only dependent press/social/video assets, not the entire project.

---

# High-risk application boundaries

Aura's architecture can help compile evidence, simulations, workflows and decision support across domains. **It does not inherit the professional or governmental authority of those domains.**

| Domain | Aura may assist with | Authority that remains external/human |
|---|---|---|
| Medicine / health | organize source material, patient-authorized context, research evidence, workflow support | licensed clinicians and applicable clinical/regulatory processes retain diagnosis/treatment authority; Aura output is not medical approval |
| Engineering / construction | models, constraints, calculations, simulations, procurement/workflow evidence | qualified engineers, inspectors, safety codes and permit authorities retain approval; simulations are not stamped engineering |
| Science / R&D | literature/evidence organization, experiment planning, negative-result reuse, hypothesis/falsification workflow | empirical observation, reproducible experiment and scientific review determine evidence; simulation/rendering cannot become empirical fact |
| Law / governance / civic planning | source retrieval, option analysis, public-process/workflow support | lawyers, courts, elected/authorized governments, communities/Nations and lawful decision processes retain legal/governance authority |
| Finance / commerce | budgeting, comparison, capability composition, provenance/settlement planning | users, regulated financial actors, audited contracts and applicable law retain transaction/custody/investment authority |
| Public safety / high-consequence operations | source-bound planning, verification and consequence analysis | authorized humans/institutions retain operational authority; D1+ effects remain independently gated |

The same principle applies elsewhere:

```text
CAPABILITY != AUTHORITY
SIMULATION != EMPIRICAL TRUTH
RECOMMENDATION != PROFESSIONAL APPROVAL
```

---

# HyperScale / HyperDrive

Aura's earlier large-number triadic journals are forcing/checkpoint genealogy, not an ordinary requirement to launch astronomical worker counts.

What survives operationally:

```text
EXPAND ONLY WHEN AN UNRESOLVED RESIDUAL EARNS IT.
FACTOR COMMON STRUCTURE.
CHALLENGE / VERIFY.
COLLAPSE TO THE MINIMUM RECONSTRUCTIBLE SUCCESSOR STATE.
REOPEN THE SMALLEST AFFECTED CONE ON INVALIDATION.
```

Completed subtrees can collapse by reference while preserving exact reproof/reopen. Source/currentness changes reopen affected consequences, and late defeat after an irreversible effect creates explicit repair/reconciliation instead of rewriting history.

---

# Open causal benchmark: regular vs rebase-only vs full Aura

The strongest pending test is matched across the same provider/model/version/config:

```text
R = ordinary fresh worker
    objective only; no Aura orientation/reuse

B = rebase-only worker
    compact frozen successor/rebase packet
    but no live Coordinate Memory / DomainLens / HyperDrive / ExpertBundle

A = full Aura worker
    source/currentness
    + Root/Sub-Arena navigation
    + Coordinate Memory
    + DomainLens/K27 where earned
    + Temporal NOW
    + deterministic/no-model path
    + ExpertBundle
    + Construct/Challenge/Verify
    + HyperDrive successor
```

The preregistered design uses **9 matched tasks × R/B/A = 27 provider calls**.

A causal comparison requires one exact provider/model/version/config across R/B/A. Model mismatch makes the cost/quality comparison noncausal.

Measure source fidelity, unsupported relations, final task quality, input/output/cache tokens, hydration bytes, broad searches, exact-source L4 opens, duplicate work, wall time, provider cost, currentness errors, replacement-worker resume fidelity, revalidation/reopen cost and total lifecycle cost.

Until command-bound results exist, this remains an open benchmark—not a completed superiority claim.

---

# Evidence discipline

```text
SIMILARITY != EVIDENCE
RECEIPT != TRUTH
CACHE HIT != TRUTH
QUEUE PRESENCE != EXECUTION
STAGED != DEPLOYED
RECORDED RESULT != REEXECUTABLE RESULT
MODEL OUTPUT != PROMOTED SOURCE
```

A strong Aura claim should be reconstructible by a skeptic: find exact source, reproduce the disclosed environment, change a source, observe the affected cone, kill the first worker, resume with a different worker, and measure what actually had to be rediscovered.

---

# Public challenge

Read Paper X Rev.3.

Run the bounded references.

Change a source.

Verify whether only the dependent state reopens.

Kill the first worker.

Give a different worker the compact successor state.

Measure what it must rediscover.

Then compare the matched regular / rebase-only / full-Aura conditions.

**The goal is not to make the model remember more. The goal is to make the system forget safely, reopen exactly, and stop paying to rediscover cognition that is already current, lawful, source-bound and reusable.**

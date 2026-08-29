# AuraOS

> [!IMPORTANT]
> ## Paper X remains the architectural authority
>
> **Current public/citable paper:** Paper X Rev.3 — Zenodo `22134815`, DOI `10.5281/zenodo.22134815`.
>
> The repository now contains staged reference implementations and currentness successors that extend beyond Rev.3. Until the next Paper X successor is publicly deposited, later work must retain its evidence class: `MEASURED`, `EXACT-DERIVED`, `STAGED/TEST-REQUIRED`, `OPEN/UNKNOWN`, or historical.
>
> `REPOSITORY != PAPER AUTHORITY` · `REFERENCE IMPLEMENTATION != PRODUCTION DEPLOYMENT` · `RECEIPT != TRUTH`

AuraOS is a **source-bound cognitive substrate**: it tries to preserve useful cognition outside any one model/session so future workers can reconstruct the minimum world required for an objective instead of rediscovering the same world from scratch.

```text
human / agent intent
        ↓
source + generation + currentness + authority
        ↓
Root Arena / Sub-Arena navigation
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

The newest staged work composes earlier Coordinate Memory / HyperDrive / HyperScale work into a more explicit operating substrate.

## 1. Persistent Arena → recursive Sub-Arenas

The Arena is not just a temporary Python environment or chat window. The durable object is the **source-bound workflow/project world**; workers and execution environments are replaceable realizations.

```text
tp://arena/<arena_sid>/subarena/<semantic_sid>
```

A current manifest is versioned separately:

```text
<stable address>?g=<generation>&head=<manifest_digest_16>
```

Every durable project, tool, research direction, campaign, Place, workflow, or accepted finding can be represented by an L0 portal with exact L1-L4 reopen paths.

```text
L0 = compact portal / what this is / where truth lives
L1 = dependencies + relations + equations + scripts + commands
L2 = current working neighborhood / residuals / receipts / affected cone
L3 = operating model / algorithms / tests / capability + swarm recipes
L4 = exact source / code / receipts / benchmark bytes
```

`SUB-ARENA != SOURCE OWNER`  
`PORTAL != BODY COPY`  
`ADDRESS != AUTHORITY`

A fresh worker should enter through Root L0, resolve the objective to candidate Sub-Arenas, expand hard dependencies, see lateral overlaps, and hydrate deeper only when consequence earns it.

## 2. Temporal Arena / NOW Capsule

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

The intended resident surface is a bounded `ArenaNowCapsule` containing only current active/ready/blocked/waiting/stale work, reminders, human decisions, claims/leases, next wakes, critical dependencies, and exact cold-history reopen handles.

A fresh model should not have to reread the entire TODO list, JSpace ledger, Calendar, Drive modification history, and every predecessor chat just to discover what matters now.

## 3. DomainLensShardV1 + Kaleido-27

One canonical source object may be important in different ways for different domains without duplicating truth.

```text
DomainLensShard(object, domain, objective)
=
source identity
+ source generation
+ relation subset
+ salience
+ residency
+ L0-L3 projection
+ exact L4 reopen
+ invalidators
+ authority ceiling
```

Example residency:

```text
rho(object | domain, objective, time)
∈ { HOT, WARM, COLD, TRANSIENT, FENCE, BLOCK }
```

Salience changes routing/attention, **not truth**.

### The 27 boundary is ternary, not binary

The current reference uses:

```text
K27(object, domain) ∈ {0,1,2}^27
```

That is **27 trits**, not a 27-bit semantic ID.

```text
3^27 = 7,625,597,484,987 states
≈ 42.794 binary bits of capacity
```

K27 is currently a **physical partition/cache-routing hint below semantic scope**. Canonical identity remains the stable semantic SID + source owner + generation/currentness. Collisions fail closed to semantic disambiguation.

The currently checked implementation uses `SHA-256(SID|domain) mod 3^27`; independent characterization shows that this behaves like a uniform hash partition, **not a semantic-locality hash**. Semantic locality comes from Sub-Arena scope, dependency graph, DomainLens, Coordinate Memory, and Temporal NOW.

That is intentional architecture:

```text
semantic scope first
→ physical shard second
```

not:

```text
hash shard = truth / meaning
```

## 4. Hierarchical ternary sharding

The same 27-trit key supports adaptive prefix partitioning without re-keying:

| Prefix | Partitions |
|---:|---:|
| 3 trits | 27 |
| 6 trits | 729 |
| 9 trits | 19,683 |
| 12 trits | 531,441 |
| 15 trits | 14,348,907 |
| 18 trits | 387,420,489 |
| 27 trits | 7,625,597,484,987 |

At 100M lens entries, ideal uniform load is roughly:

- 3-trit prefix: 3.70M entries/shard
- 6-trit prefix: 137k
- 9-trit prefix: 5,081
- 12-trit prefix: 188
- 15-trit prefix: 7

A phone, workstation, cache node, R&D pool, or swarm lane can therefore operate at a different partition depth while the canonical object identity remains unchanged.

## 5. Resident Cognitive Fabric: ChatGPT ↔ Aura ↔ OpenCode/DeepSeek

AWJ-015 stages the resident seam between proven Drive transport and governed local execution.

After one-time host bootstrap, the target resident can:

- observe both Aura Drive roots and local AuraOS changes;
- maintain durable currentness cursors;
- allocate deterministic L0 state without waking a model for every artifact;
- maintain SQLite WAL backlog, claims, leases, restart/idempotency state;
- admit D0 commands automatically while D1+ effects remain human-gated;
- dispatch bounded work through an OpenCode/DeepSeek adapter;
- expand the preregistered 9-task `R/B/A` benchmark into 27 provider tasks when the exact provider/model is pinned and authorized;
- return command-bound result envelopes to the outbound Drive bus;
- keep observer credentials separate from bounded writer credentials.

Reference package status:

```text
17/17 local clean-room gates PASS
compileall PASS
live laptop install / live DeepSeek execution: NOT established by that receipt
```

The success condition is deliberately stronger than “a command file exists”:

```text
ChatGPT writes authorized command
→ resident consumes it
→ bounded worker executes
→ command-bound ACK/RESULT/ERROR returns
```

Queue presence alone is not execution proof.

## 6. Expert Fabric: only use the model/expert mixture the residual earns

AWJ-016 composes Aura's semantic routing with execution backends.

```text
source/currentness/authority/privacy
→ Sub-Arena + domain + Temporal NOW
→ minimum WorkCapsule
→ ExpertBundle
→ execution backend(s)
→ Construct / Challenge / Verify
→ HyperDrive collapse
```

Current staged routing classes:

```text
NO_MODEL
LOCAL_FAST
AIRLLM_LARGE_LOCAL
OPENROUTER_PINNED / pinned remote provider-model
OPENROUTER_TRIAD / heterogeneous independent panel
```

The crucial separation is:

```text
K27 != MoE expert ID
DOMAIN != model-internal expert number
MODEL-INTERNAL MoE GATE != Aura semantic router
```

Aura selects the lawful **model/backend/role mixture**. A sparse-MoE model may then select its own internal experts independently.

### AirLLM

AirLLM is treated as a **paged local inference/materialization backend**, especially for private/offline/batch work where latency is less important than sovereignty or fitting a larger model into constrained accelerator memory.

It is not the default interactive path and it is not Aura's semantic router.

Current public AirLLM documentation describes layer/expert streaming intended to reduce resident VRAM; those upstream performance claims require their own reproducibility scrutiny and are not Aura benchmark results.

### Cache identity

A K27 shard or semantic coordinate must never be a model KV-cache identity by itself.

The staged cache binding includes at least:

```text
semantic SID
| source generation
| domain/task
| concrete model identity
| preset generation
| WorkCapsule digest
```

Production should also bind tokenizer/model revision, system prompt, tool schema, inference parameters, provider endpoint class, and provider-specific cache namespace where relevant.

---

# Current reference evidence

These are **bounded system/reference results**, not universal claims of cognitive superiority.

| Surface | Current result | What it establishes | What it does not establish |
|---|---:|---|---|
| Mini Aura reference Arena | 10/10 public core checks | finite reconstructible reference invariants + Python/Node parity | production AuraOS or comparative superiority |
| DomainLens/K27 reference | 13/13 PASS | one-source/many-lenses, residency, affected-cone, 27-trit parity, fail-closed collisions | causal reasoning-quality gain |
| Independent K27 stress | 300,000 keys, 0 observed full collisions | uniform practical hash partition in the tested sample | identity safety at arbitrary scale |
| K27 semantic-locality falsifier | mean Hamming 17.99766/27 over 50k related pairs | current SHA-based K27 is effectively random wrt semantic edit locality | semantic scope failure — semantics live above K27 |
| Expert Fabric package | 18 Python gates + independent Node K27 parity | deterministic ExpertBundles, privacy gates, cache binding, domain-specific routes | live AirLLM/provider execution |
| Resident Cognitive Fabric | 17/17 local clean-room + compileall | reference observer/backlog/dispatch/receipt mechanics | live installed resident/provider call |
| Web4 reference | 25/25 local deterministic gates | bounded capability/economic contract semantics | production marketplace/L2/bridge |
| Campaign/Media Foundry | 34/34 local gates | evidence-bound CampaignGraph / affected-media logic | generated provider footage or deployed AR/XR |

### Fresh 9-task routing/hydration ablation

A fresh local ablation compared three deterministic orientation conditions on the checked 16-object × 6-domain reference graph:

```text
R = regular/broad orientation
B = rebase-only hard dependency closure, no domain-lens narrowing
A = full Aura structural route:
    hard closure + selected domain lenses + bounded WorkCapsule + ExpertBundle
```

Each object-domain projection was assigned the same synthetic 4 KiB hydration cost; the Aura condition also paid a 2 KiB WorkCapsule cost per task. This isolates routing/hydration structure and **does not** pretend to measure model reasoning quality, provider token billing, or production latency.

Across nine frozen Aura maintenance/research tasks:

| Condition | Projection-equivalents hydrated | Equal-cost bytes |
|---|---:|---:|
| R — regular broad | 864 | 3,538,944 |
| B — rebase-only | 342 | 1,400,832 |
| A — full Aura structural route | 114 | 485,376 |

Observed structural reductions:

```text
A vs R: 86.2847% fewer equal-cost hydrated bytes
A vs B: 65.3509% fewer equal-cost hydrated bytes
B vs R: 60.4167% fewer equal-cost hydrated bytes
```

The full-Aura ExpertBundle policy routed the nine tasks as:

```text
3 × NO_MODEL
2 × LOCAL_FAST
2 × AIRLLM_LARGE_LOCAL
1 × OPENROUTER_PINNED
1 × OPENROUTER_TRIAD
```

The `OPENROUTER_TRIAD` policy lane represents three independent-model calls, so the nine-task policy would imply eight model calls total if all selected backends were available/authorized. **No provider or AirLLM inference was executed in this ablation.**

These numbers quantify deterministic work removed **before** model inference. They are not evidence that Aura makes an LLM 86% smarter, 86% cheaper, or 86% faster end-to-end.

### Current reference discrepancy kept visible

The GEN16 prose reports a `24/96` example for scope-before-route. The currently checked executable reference yields `22/96` for its present seed/domain selection.

This README uses the executable result where discussing the current code and keeps the discrepancy open for source reconciliation rather than silently choosing the more favorable number.

For the checked 16-object × 6-domain reference graph:

```text
all object-domain projections = 96
hard closure for sample objective = 11 objects
2 selected domains = 22 detailed lens projections
22 / 96 retained
≈ 77.08% of object-domain projection combinations pruned before detailed traversal
```

That is a **routing-space reduction**, not a 77.08% token/cost/quality claim.

---

# Why this matters for small/local models and swarms

The highest-leverage outcome is not “a magic 27-trit key.”

It is that Aura can increasingly precompile the worker's relevant world before inference begins.

Without this substrate, a fresh worker often does:

```text
objective
→ broad corpus/search
→ retrieve many chunks
→ reconstruct relationships/currentness
→ infer what matters
→ perform work
→ next worker repeats much of the orientation
```

The target Aura path is:

```text
objective
→ Root L0
→ hard dependency closure
→ domain lens
→ Temporal NOW
→ K27 physical partition/cache
→ currentness + authority gate
→ L0/L1 hot packet
→ exact L4 only as earned
→ ExpertBundle only for unresolved work
→ result / ArtifactBirth
→ affected-cone update
→ HyperDrive successor
```

That should matter most when:

- the durable graph grows to millions/billions of source-bound projections;
- many workers operate concurrently;
- a small local model cannot absorb the entire knowledge base;
- private/offline work should stay local;
- the same canonical object participates in several domains;
- frequent source changes make stale retrieval dangerous;
- only a small unresolved residual requires expensive frontier inference.

HyperScale therefore asks:

```text
HOW MUCH INDEPENDENT UNRESOLVED FRONTIER EXISTS?
```

not:

```text
HOW MANY AGENTS CAN WE SPAWN?
```

The current swarm policy prefers `0/1/3/9` workers when sufficient and reserves 27 physical provider workers for a preregistered matched benchmark or another independently justified frontier.

---

# Reproducible bounded references

## Mini Aura

```bash
cd examples/mini_aura_reference_arena
python -m venv .aura-mini
# activate .aura-mini
python mini_aura_reference.py --out results_local.json
```

Expected finite invariants include:

- depth-10 ternary world: 88,573 nodes;
- 11-node reverse-reachable affected cone after one leaf mutation;
- 81/81 AMNF applicability signatures;
- 40,320 HyperScale permutations → 108 running-GCD trajectories;
- 219/255 nonempty scale subsets reaching gcd 1;
- Python/Node exact-count parity;
- Decision-Capsule and valid-bound action-cone safety checks.

## Arena navigation / DomainLens / K27

```bash
cd examples/arena_navigation_domain_lens
python domain_lens_reference.py
```

The reference also invokes/compares an independent Node 27-trit lane.

The code is intentionally bounded. It tests control semantics, not production AuraOS performance.

---

# LifeOS, Places, Worlds and disposable apps

The human-facing direction remains:

```text
AURAOS = governed source/currentness/authority substrate
AURA   = conversational/spatial intelligence/interface
LIFEOS = private user-owned continuity substrate
PLACE  = persistent governed semantic identity/environment
SPACE  = permission-governed semantic region
VISIT  = ephemeral actor/device/permission/objective realization
ARENA  = objective-specific runtime/workspace
WORLD  = current objective-conditioned semantic projection
APP    = disposable realization of the World
```

The persistent layer is the governed Place/Space/Coordinate Cognition.

The UI can be regenerated for desktop, phone, accessible 2D, headless agents, AR/MR/XR, or later devices.

```text
RENDERING != TRUTH
OBSERVATION != VERIFIED FACT
RELATIONSHIP != CONSENT
PRIVATE LIFEOS != PUBLIC PROFILE
```

---

# Aura Web4 / Commons / capability economy

The staged capability-composition model allows one Arena to combine:

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

Economic and authority boundaries remain explicit:

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

Optional L2/paymaster/batched-settlement concepts remain staged; no production bridge, wallet, paymaster, custody system, or audited settlement contract is claimed here.

---

# Creator Studio / evidence-bound media

Aura Creator Studio is a reference application of the same architecture.

```text
MESSAGE ONCE
→ EVIDENCE ONCE
→ MANY REGENERABLE CAMPAIGN SURFACES
```

A durable media project contains claims, evidence, story graph, shots, continuity, rights, provider attempts, accepted assets, currentness, and provenance.

```text
THE PROMPT IS NOT THE SOURCE CODE OF THE MOVIE.
GENERATED CONCEPT VISUALIZATION != IMPLEMENTATION EVIDENCE.
```

Change one source-bound claim → reopen only the dependent press/social/video cone → regenerate/verify only that cone.

---

# J59 → HyperScale → HyperDrive

Aura's earlier large-number triadic journals are best read as forcing/checkpoint geometry, not as a requirement to launch astronomical numbers of model workers.

What survived:

- expansion must return through challenge/synthesis/rebase;
- completed subtrees can collapse by reference with exact reopen;
- forgetting is lawful only when reproof remains reachable;
- source/currentness changes reopen the minimum affected consequence cone;
- independent frontier, not symbolic recursion count, determines real scaling;
- after an irreversible consequence, later defeat creates explicit repair/reconciliation rather than rewriting history.

Modern operational rule:

```text
EXPAND ONLY WHEN AN UNRESOLVED RESIDUAL EARNS IT.
FACTOR COMMON STRUCTURE.
CHALLENGE / VERIFY.
COLLAPSE TO THE MINIMUM RECONSTRUCTIBLE SUCCESSOR STATE.
REOPEN THE SMALLEST AFFECTED CONE ON INVALIDATION.
```

---

# Current open benchmark: regular vs rebase-only vs full Aura

The strongest next causal test is deliberately matched.

For each frozen task:

```text
R = ordinary fresh worker
    objective only; no Aura orientation/reuse

B = rebase-only worker
    same model/tools + compact frozen successor/rebase packet
    but no live Coordinate Memory / DomainLens / HyperDrive expert assistance

A = full Aura worker
    same model/tools
    + source/currentness
    + Root/Sub-Arena navigation
    + Coordinate Memory
    + DomainLens/K27 only where earned
    + Temporal NOW
    + deterministic/no-model path
    + ExpertBundle
    + Construct/Challenge/Verify
    + HyperDrive successor
```

The preregistered design uses 9 matched tasks × `R/B/A` = **27 provider calls**.

A causal comparison requires the **same exact provider/model/version/config** across R/B/A. If that cannot be held fixed, the result must be classified noncausal.

Measure at least:

- source fidelity / unsupported relation rate;
- final task quality;
- context bytes/tokens hydrated;
- exact-source L4 opens;
- broad searches;
- duplicate work;
- wall time;
- provider/model cost;
- currentness errors;
- worker-resume fidelity;
- revalidation/reopen cost;
- total lifecycle cost, not only first-call latency.

Until command-bound results exist, this remains the key open benchmark—not a completed superiority claim.

---

# Evidence discipline

Aura deliberately preserves negative results and boundary conditions.

```text
SIMILARITY != EVIDENCE
RECEIPT != TRUTH
CACHE HIT != TRUTH
QUEUE PRESENCE != EXECUTION
STAGED != DEPLOYED
RECORDED RESULT != REEXECUTABLE RESULT
MODEL OUTPUT != PROMOTED SOURCE
```

A powerful architecture is only useful if a fresh skeptic can reconstruct what happened, find the exact source, change it, observe the affected cone, and reproduce or falsify the claimed result.

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

**The goal is not to make the model remember more. The goal is to make the system forget safely, reopen exactly, and stop paying to rediscover cognition that is already current, lawful, source-bound, and reusable.**

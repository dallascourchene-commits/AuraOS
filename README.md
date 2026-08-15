# AuraOS

AuraOS is a minimal, local-first substrate for deterministic state, recursive coordination, and peer-to-peer execution. It is designed around a simple operating law: **do not feed the system the world; compile the smallest source-resolvable relational world sufficient for the objective.**

AuraOS keeps **addressability and routing separate from truth and authority**. A route may identify a lawful next operation without creating source truth, capability, permission, a commit, a merge, or human disposition.

## Founder & contact

**Founder:** Dallas Fabian Courchene-Martin  
**Role:** Founder, AuraOS; Indigenous systems builder  
**Affiliation:** Long Plain First Nation, Treaty 1 Territory, Manitoba, Canada  
**Founder contact:** dallascourchene@gmail.com

AuraOS is being developed around local-first execution, bounded hardware, source provenance, human authority, and community accessibility. The architecture treats constrained RAM, CPU, bandwidth, battery, latency, and thermal envelopes as design inputs rather than deployment afterthoughts.

## Core features

- **Local-first deterministic state** — durable state and receipts remain inspectable close to the operator.
- **Six-slot FST / WFST routing** — bounded state-local routing through `DIR → ASP → CLASS → SUBJ → VOICE → STEM`.
- **3^n recursive rollups** — bounded child work can be compressed into progressively smaller parent summaries.
- **SQLite-backed state** — local transactional state supports deterministic execution and reproducible validation.
- **Bounded worker fleets** — identities, leases, coordinates, inboxes/outboxes, staging lanes, and receipts reduce collision surface.
- **Human-gated authority** — routing, ranking, similarity, hashes, memory, or worker consensus never create consequential authority by themselves.
- **Source-defeasible hydration** — compact representations must remain defeasible by exact/current source evidence.
- **Construction Human Agent profile** — review-only projection over canonical Construction state and Observatory evidence; it grants no physical-work, payment, access, equipment, professional, deployment, or merge authority.

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

The FST/WFST layer is a routing and syntax mechanism. It does **not** mint source truth, capability, authority, commits, pushes, merges, or human disposition.

## 3-6-9 orchestration and concurrency

Aura's staged multi-agent architecture uses **3-6-9 phase staggering as an orchestration grammar**, not as a claim of numerological or universal physical law.

- **3** — the smallest reviewable working cell: analysis / synthesis / verification, or lead / builder / auditor.
- **6** — paired triads, allowing perturbation, challenge, handoff, or parallel work without forcing every worker onto the same write surface.
- **9** — three triads closing a larger cycle with separate analysis, execution, and reconciliation lanes.

Collision resistance comes from the mechanics around that grammar: explicit worker identity, leases before mutation, coordinate/owner partitioning, bounded staging, source-currentness checks, and receipts that expose stale generations or collisions rather than silently overwriting them.

Current staging records **25-plus numbered worker slots** and triad-of-triads experiments at **27 objective positions**. This supports a **25+ concurrent-agent design target** with collision-resistant coordination. It is **not** presented as a universal zero-collision benchmark until a specific workload, agent count, lease schedule, collision definition, and run receipt are bound.

### Conditional diagonal rebase

The `3 → 6 → 9/1′` path is a **conditional diagonal rebase** across independently verified/current invariant boundaries. A fast path is admissible only when intervening guards are already satisfied; unresolved evidence, currentness, authority, or negative-space boundaries force the guarded linear path.

## Gate-1 benchmark synchronization

The table below preserves the exact evidence status from the staged Gate-1 benchmark and founder sources. **Targets, bounded compatibility results, and unresolved external benchmark identities are not promoted into broader claims.**

| Requested headline | Gate-1 disposition | Source-bound result / boundary |
|---|---|---|
| **94%–98% token reduction; ~48-token L0 symbolic tensors** | **EVIDENCE BINDING REQUIRED** | The staged founder source preserves the range, but did not resolve an exact production benchmark independently establishing the full 94%–98% result. Do not present it as verified without workload, baseline, run artifact, and digest. |
| **>5,250 receipt/events per second** | **VERIFIED, bounded scope** | Five fresh 1,000-transition runs: **6,864.45–7,071.97/sec**, median **7,044.41/sec**. A separate timed run measured **7,205.33/sec** with 1,001 events including root creation. Exact `StateDeltaDaemon`, SQLite `:memory:`, single thread, append-only state-event path; not a distributed/network receipt benchmark. |
| **25+ concurrent agents** | **DESIGN TARGET / CURRENT FLEET EVIDENCE** | Staging records 25-plus worker slots and 27 objective positions. The architecture supports collision-resistant coordination through leases, ownership and phase staggering; no universal zero-collision claim is made. |
| **<95 MB RSS** | **FAIL for tested host process / retained narrow-runtime target** | Packaged staging run: **115.95 MiB** peak RSS. Fresh W3 receipt-path process: **113,012 KB** max RSS. The `<95 MB` figure remains a narrower engineering target, not an achieved universal footprint. |
| **0.00% InjecAgent ASR** | **UNVERIFIED as official/end-to-end InjecAgent result in the staged source set** | Staged Gate-1 source explicitly withholds the broad percentage until dataset/version, harness, target generation, run command, result, and digest are bound. Current repository evidence may separately describe bounded gate-layer attack-surface tests; those must not be relabeled as official end-to-end InjecAgent ASR. |
| **100% Tau-bench accuracy / trajectory adherence** | **UNVERIFIED as official Tau-bench pass^k in the staged source set** | Staging preserves the statement but requires benchmark identity. Any bounded legacy trajectory-preservation result must remain scoped to its exact task-lane sample. |
| **UDP <500 µs** | **VERIFIED WITH SCOPE CORRECTION** | Packaged staging result: **3.144 µs p95** localhost synchronous UDP RTT; companion run: **2.894 µs median**, **3.805 µs p95**, 200/200 packets. This is localhost unicast, not WAN/multicast/multi-node gossip. |
| **W4 adversarial invariant harness** | **VERIFIED** | Fresh staged rerun: **28/28 PASS**, receipt digest `11b2786ece07626d954089db235f6cdac669b5f7f481f28f542eef6126bdf2f2`. Implemented staging invariants only; not a substitute for InjecAgent or Tau-bench. |

## Current repository benchmark evidence

The repository also carries bounded executable benchmark evidence. These measurements are **not third-party certifications or external percentile rankings**.

| Surface | Current source-bound repository result | Evidence boundary |
|---|---:|---|
| Six-slot FST deterministic routing | **1,366,040.46 iterations/s**, **8,196,242.75 transitions/s** | 100,000-iteration deterministic transition microkernel; not linguistic accuracy. |
| `3^n` Merkle aggregation | **2,460.61 rollups/s**, **895,661.61 hashes/s** | 2,000 rollups, depth 5, 243 leaves/rollup. |
| SQLite WAL | **19,934.69 writes/s @ 5 workers** | Best observed one-row transaction throughput; not automatically equivalent to complete receipt throughput. |
| Peak process RSS | **116.71 MiB** | Process high-water mark; below a 4 GiB device-class capacity but above the separate `<95 MiB` target. |
| Serialized state projection | **72.73% fewer bytes** (`286 B → 78 B`) | Byte serialization only; tokenizer-measured 94%+ compression remains separately unverified. |
| UDP localhost unicast | median **7.080 µs**, p95 **10.126 µs** | Synchronous localhost RTT proxy; not remote mesh gossip. |
| InjecAgent-derived hard gate | **0 / 868 attack transitions reached executable state** (`0.0000%` gate-layer ASR) | Bounded gate-layer test only; not official end-to-end InjecAgent ASR. |
| Legacy τ-bench trajectory preservation | **42 / 42 task-lane trials = 100.00%** | Bounded 6-task compatibility sample across 7 deterministic lanes; not official τ-bench pass^k. |
| 25-slot bounded daemon fleet | **25 / 25 exact-once DONE**, **0 duplicate fleet payloads** | Process-spawned bounded worker correctness test; not a general concurrency-throughput claim. |

Repository scorecards:

- [`docs/INDUSTRY_BENCHMARK_SCORECARD.md`](./docs/INDUSTRY_BENCHMARK_SCORECARD.md)
- [`docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`](./docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md)
- [`docs/SECURITY_AND_ACCURACY_SCORECARD.md`](./docs/SECURITY_AND_ACCURACY_SCORECARD.md)
- [`docs/ADVANCED_BENCHMARKS.md`](./docs/ADVANCED_BENCHMARKS.md)

## Edge / local-first design boundary

AuraOS targets consumer-grade and constrained hardware by keeping the addressable world larger than the **active decision surface**. The design goal is to hydrate only the source-resolvable material needed for the current objective, then return to deeper evidence when the decision requires it.

The measured host-process RSS figures above do **not** establish whole-device or mobile-kernel memory usage. The `<95 MiB` narrow-runtime objective remains explicitly unresolved rather than being rewritten as achieved.

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

A separate staged manifesto carries a planning model comparing **$60–$180/month** for AuraOS local/edge operation with a **$4,900–$12,900/month** cloud-agent baseline, corresponding arithmetically to roughly **98.60–98.78% lower modeled monthly OpEx** at paired endpoints.

The current Gate-1 technical fact sheet did **not** independently resolve the workload definition, provider/SKU assumptions, utilization, token volume, amortization, electricity/network inputs, or exact source model for those figures. They therefore remain a **staged operating-cost model, not an audited savings benchmark**, and the ~98% OpEx figure must not be relabeled as token compression.

## Reproduce repository benchmarks

```bash
python3 scripts/aura_industry_benchmark_validation.py
python3 scripts/aura_advanced_benchmark_runner.py
python3 scripts/aura_security_accuracy_harness.py
```

Machine-readable outputs and signed/hashed receipts remain evidence of their declared execution scope. A signature or digest authenticates recorded material against its declared key/input; it does not independently establish human identity, semantic truth, or promotion authority.

## Scientific disclosure

See [`PAPER_X_ARXIV_DISCLOSURE.pdf`](./PAPER_X_ARXIV_DISCLOSURE.pdf) for the scientific disclosure, research claims, evidence boundaries, and architectural context for the AuraOS substrate.

## AGPLv3 public commons

AuraOS's current licensing posture is **GNU Affero General Public License v3.0 / AGPL-3.0-only**. The public-commons intent is that improvements to a network-accessible covered system remain inspectable and shareable rather than disappearing behind a closed service boundary.

Copyleft is a strong legal/governance barrier to enclosure, but it should not be described as an absolute guarantee against every possible outside patent filing, assertion, or independently written implementation.

## Canonical archive

- **Zenodo record:** https://zenodo.org/records/21941334
- **Canonical Genesis Seed:** `67d2597bfa7895d997b89eb288a8f6cd5fe54ddc1ea69f676ec5d1a1ab96b002`

## Staging-source provenance for this README synchronization

Compiled by Triad 2 under `WO-TRIAD2-STAGING-README-SYNC-001` from the existing Gate-1 staging sources:

- `docs/staging/ready_review/TECHNICAL_BENCHMARKS_AND_ECONOMICS.md`
- `docs/staging/ready_review/FOUNDER_BIO_AND_VISION.md`
- `docs/staging/ready_review/PR_MANIFESTO_PRESS_RELEASE.md`

Founder contact integration was authorized directly by the Human Sovereign dispatch for this work order.

---

**Evidence rule:** verified results stay scoped to the exact harness/workload that produced them; targets and unresolved claims remain labeled as such.

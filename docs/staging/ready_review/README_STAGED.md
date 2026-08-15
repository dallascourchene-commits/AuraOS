# AuraOS

AuraOS is a minimal, local-first substrate for deterministic state, recursive coordination, and peer-to-peer execution.

## Core Features

- **Zero gas** — ordinary local and peer coordination does not require per-operation gas fees.
- **3^n rollups** — recursive ternary rollups compress bounded child work into progressively smaller parent summaries.
- **SQLite WAL** — write-ahead logging provides durable local state, atomic commits, crash recovery, and concurrent reads.
- **P2P mesh** — nodes exchange bounded state and work directly without requiring a central coordinator.
- **Source-resolvable execution** — compact state and routing remain connected to exact source, provenance, currentness, and human disposition boundaries.

## System Architecture

```text
                         +----------------------+
                         |       Operator       |
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
         |      SQLite WAL      |                   |
         | durable local state  |                   |
         +----------+-----------+                   |
                    |                               |
                    +---------------+---------------+
                                    |
                                    v
                         +----------------------+
                         |  aura_swarm_runner   |
                         | bounded swarm work   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     3^n rollups      |
                         | receipts + summaries |
                         +----------------------+
```

### Six-slot FST / WFST runtime grammar

Aura's guarded runtime projects state-local actions through the six-slot grammar:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

- **DIR** — direction/domain of operation.
- **ASP** — lifecycle state, timing, or duration.
- **CLASS** — class of work admitted by the current gate.
- **SUBJ** — actor/authority envelope.
- **VOICE** — advisory, measured, proposed, staged, or human-authorized mode.
- **STEM** — core operation.

The runtime order is deliberately fail-closed:

```text
hard guards
→ admitted state-local transitions
→ exact WFST ranking
→ six-slot packet
→ deterministic/model-assisted explanation
→ human choice
```

The FST/WFST layer is a routing and syntax mechanism. It does **not** mint source truth, capabilities, authority, commits, pushes, merges, or human disposition.

### 3→6→9 harmonic runtime architecture and bounded concurrency

Aura's current provenance work defines the `3 → 6 → 9/1′` harmonic as a **conditional diagonal rebase** across independently verified/current invariant boundaries. The fast path is admissible only when intervening guards are already satisfied; otherwise execution falls back to the guarded linear path.

The bounded concurrency evidence is kept separate from the harmonic hypothesis: the current repository scorecard records a **25-slot daemon fleet with 25/25 exact-once DONE and 0 duplicate fleet payloads**. That demonstrates the bounded worker harness tested in this generation; it does not establish that `3→6→9` is a universal concurrency law or that every deployment supports 25+ agents.

The `3→6→9` model remains staged routing/discovery semantics. Current `main` does not expose a source-bound executable service named `3-6-9 Harmonic Daemon`; the name refers to a staged daemonization target rather than a production-service claim.

## Quickstart

Run long-lived processes in separate terminals as needed.

```bash
# 1. Clone and enter the repository
git clone https://github.com/dallascourchene-commits/AuraOS.git && cd AuraOS

# 2. Start an Aura node
python aura_node.py

# 3. Start the Aura daemon
python aura_daemon.py

# 4. Start the swarm runner
python aura_swarm_runner.py
```

## Scientific Disclosure

> **Paper X — Scientific Disclosure**
>
> See [`PAPER_X_ARXIV_DISCLOSURE.pdf`](./PAPER_X_ARXIV_DISCLOSURE.pdf) for the scientific disclosure, research claims, evidence boundaries, and architectural context for the AuraOS substrate.

## License

AuraOS repository documentation declares the project under the **GNU Affero General Public License v3.0** with file/dependency-specific exceptions where applicable. The intended repository-level SPDX expression is **`AGPL-3.0-only`**.

A conventional root `LICENSE` normalization is currently staged in draft PR #286 and is **not yet merged into `main`** at the time of this README synchronization. This README therefore does not represent that draft as already promoted.

---

## Canonical Archive & Permanent DOI

- **Zenodo Record:** https://zenodo.org/records/21941334
- **Canonical Genesis Seed:** `67d2597bfa7895d997b89eb288a8f6cd5fe54ddc1ea69f676ec5d1a1ab96b002`

## Verified Engineering Scorecard

Primary source documents:

- [`docs/INDUSTRY_BENCHMARK_SCORECARD.md`](./docs/INDUSTRY_BENCHMARK_SCORECARD.md)
- [`docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`](./docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md)
- [`docs/SECURITY_AND_ACCURACY_SCORECARD.md`](./docs/SECURITY_AND_ACCURACY_SCORECARD.md)
- [`docs/staging/ready_review/PR_MANIFESTO_PRESS_RELEASE.md`](./docs/staging/ready_review/PR_MANIFESTO_PRESS_RELEASE.md)

These are source-bound repository validations, **not third-party certifications or external percentile rankings**. Performance rows are host measurements or explicitly bounded proxies; security/accuracy rows preserve the executed scope.

| Surface | Current source-bound result | Evidence boundary |
| :--- | :--- | :--- |
| Six-slot FST deterministic routing | **1,366,040.46 iterations/s**, **8,196,242.75 transitions/s** | 100,000-iteration deterministic transition microkernel; not linguistic accuracy |
| `3^n` Merkle aggregation | **2,460.61 rollups/s**, **895,661.61 hashes/s** | 2,000 rollups, depth 5, 243 leaves/rollup |
| SQLite WAL | **19,934.69 writes/s @ 5 workers** | Best observed one-row transaction throughput; **receipt throughput was not separately measured** |
| Peak process RSS | **116.71 MiB** | Process high-water mark; below a 4 GiB device-class capacity, but it **does not satisfy** the separate `<95 MiB` target |
| Serialized state projection | **72.73% fewer bytes** (`286 B → 78 B`) | Byte serialization only; tokenizer-measured `94%` token compression remains unverified |
| UDP localhost unicast | median **7.080 µs**, p95 **10.126 µs** | Synchronous localhost RTT proxy; not remote/WAN/multi-node mesh gossip |
| InjecAgent-derived hard gate | **0 / 868 attack transitions reached executable state** (`0.0000%` gate-layer ASR) | Gate-layer test only; official end-to-end InjecAgent ASR was not measured |
| Legacy τ-bench trajectory preservation | **42 / 42 task-lane trials = 100.00%** exact oracle-action preservation | Bounded 6-task compatibility sample across 7 deterministic lanes; official τ-bench pass^k was not measured |
| Bounded daemon fleet | **25 / 25 exact-once DONE**, **0 duplicate fleet payloads** | Process-spawned bounded workers; correctness-oriented, not a universal concurrency limit or throughput claim |

### Headline-claim reconciliation

This table keeps targets, models, proxies, and bounded compatibility tests from being promoted as broader benchmark facts.

| Requested headline | Exact current evidence | README disposition |
| :--- | :--- | :--- |
| `94–98% token reduction` | **72.73% fewer serialized bytes** is measured; `≥94%` tokenizer/L0 compression remains an **unverified target**. The `~98.60–98.78%` figure belongs to a supplied **OpEx model**, not token reduction. | **Do not publish 94–98% as one verified token-reduction benchmark.** |
| `>5,250 receipts/sec` | **19,934.69 SQLite WAL writes/s** at the best observed worker count. | Publish writes/s only; no source currently equates one WAL row-write with one complete receipt. |
| `25+ concurrent agents` | **25/25** exact-once bounded daemon tasks, 0 duplicates. | Publish the tested 25-slot fleet, not an unbounded `25+` capability claim. |
| `<95 MB RSS` | **116.71 MiB** process high-water mark; the separate `<95 MiB` target remains unresolved. | Do not promote `<95 MiB` as achieved. |
| `0.00% InjecAgent ASR` | **0/868** attack transitions reached executable state; gate-layer ASR `0.0000%`. | Publish with the **gate-layer** scope; official end-to-end InjecAgent ASR was not measured. |
| `100% Tau-bench accuracy` | **42/42** bounded legacy τ-bench task-lane trajectories preserved exact oracle actions. | Publish as bounded trajectory preservation, not official τ-bench pass^k. |

## Edge Deployment Readiness

The measured process high-water mark of **116.71 MiB** is small relative to a 4 GiB device-class memory budget, but AuraOS deliberately retains the stricter `<95 MiB` internal target as unresolved rather than rewriting the benchmark. SQLite WAL, localhost UDP, deterministic FST routing, bounded worker execution, and exact-source security gates all have executable repository evidence; remote network behavior, whole-device memory behavior, and broader external benchmark suites require their own environments.

## Operating-Economics Model

The staged manifesto distinguishes measured engineering evidence from a supplied operating-cost model. The model compares **$60–$180/month** for local/edge AuraOS operation with a **$4,900–$12,900/month** cloud-agent baseline, which arithmetically corresponds to approximately **98.60–98.78% lower modeled monthly OpEx** at paired endpoints.

This is a planning/economic model, **not an audited customer-savings benchmark** and not evidence of 98% token compression.

## Reproduce

```bash
python3 scripts/aura_industry_benchmark_validation.py
python3 scripts/aura_advanced_benchmark_runner.py
python3 scripts/aura_security_accuracy_harness.py
```

Machine-readable outputs and signed/hashed receipts remain source evidence; signatures authenticate the recorded artifact against their declared key/material and do not independently establish human identity or promotion authority.

## Founder & Contact

**Founder:** Dallas Fabian Courchene-Martin  
**Contact:** dallascourchene@gmail.com

Founder/contact fields above are integrated from the sovereign human dispatch for `WO-TRIAD2-STAGING-README-SYNC-001`; they are not benchmark-derived fields.

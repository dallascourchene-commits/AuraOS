# AuraOS

AuraOS is a minimal, local-first substrate for deterministic state, recursive coordination, and peer-to-peer execution.

## Core Features

- **Zero gas** — ordinary local and peer coordination does not require per-operation gas fees.
- **3^n rollups** — recursive ternary rollups compress bounded child work into progressively smaller parent summaries.
- **SQLite WAL** — write-ahead logging provides durable local state, atomic commits, crash recovery, and concurrent reads.
- **P2P mesh** — nodes exchange bounded state and work directly without requiring a central coordinator.

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

### 3→6→9 Harmonic Daemon — staged diagonal-rebase architecture

Aura's current provenance work defines the `3 → 6 → 9/1′` harmonic as a **conditional diagonal rebase** across independently verified/current invariant boundaries. The fast path is only admissible when the intervening guards are already satisfied; otherwise execution falls back to the guarded linear path.

This is staged routing/discovery semantics, not a claim that arithmetic pattern is a universal physical law. As of this documentation generation, current `main` does not expose a source-bound executable service named `3-6-9 Harmonic Daemon`; the name therefore refers to the staged daemonization target for the conditional diagonal-rebase contract, not a production-service claim.

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

AuraOS is licensed under the **GNU Affero General Public License v3.0 (GNU AGPLv3)**.

See [`LICENSE`](./LICENSE) for the complete license text.

---

## Canonical Archive & Permanent DOI
* **Zenodo Record:** https://zenodo.org/records/21941334
* **Canonical Genesis Seed:** `67d2597bfa7895d997b89eb288a8f6cd5fe54ddc1ea69f676ec5d1a1ab96b002`

## Industry Benchmark Scorecard

Source documents:

- [`docs/INDUSTRY_BENCHMARK_SCORECARD.md`](./docs/INDUSTRY_BENCHMARK_SCORECARD.md)
- [`docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`](./docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md)
- [`docs/SECURITY_AND_ACCURACY_SCORECARD.md`](./docs/SECURITY_AND_ACCURACY_SCORECARD.md)

These are source-bound repository validations, **not third-party certifications or external percentile rankings**. Performance rows are host measurements or explicitly bounded proxies; security/accuracy rows preserve the exact executed scope.

| Surface | Current source-bound result | Evidence boundary |
| :--- | :--- | :--- |
| Six-slot FST deterministic routing | **1,366,040.46 iterations/s**, **8,196,242.75 transitions/s** | 100,000-iteration deterministic transition microkernel; not linguistic accuracy |
| `3^n` Merkle aggregation | **2,460.61 rollups/s**, **895,661.61 hashes/s** | 2,000 rollups, depth 5, 243 leaves/rollup |
| SQLite WAL | **19,934.69 writes/s @ 5 workers** | Best observed one-row transaction throughput; **receipt throughput was not separately measured** |
| Peak process RSS | **116.71 MiB** | Process high-water mark; comfortably below a 4 GiB edge-device capacity, but it **does not satisfy** the separate `<95 MiB` target |
| Serialized state projection | **72.73% fewer bytes** (`286 B → 78 B`) | Byte serialization only; tokenizer-measured `94%` token compression remains unverified |
| UDP localhost unicast | median **7.080 µs**, p95 **10.126 µs** | Synchronous localhost RTT proxy; not remote/WAN/multi-node mesh gossip |
| InjecAgent-derived hard gate | **0 / 868 attack transitions reached executable state** (`0.0000%` gate-layer ASR) | Gate-layer test only; official end-to-end InjecAgent ASR was not measured |
| Legacy τ-bench trajectory preservation | **42 / 42 task-lane trials = 100.00%** exact oracle-action preservation | Bounded 6-task compatibility sample across 7 deterministic lanes; official τ-bench pass^k was not measured |
| 25-slot bounded daemon fleet | **25 / 25 exact-once DONE**, **0 duplicate fleet payloads** | Process-spawned bounded workers; correctness-oriented, not a throughput claim |

### Claim-to-evidence comparison matrix

This matrix prevents target values, proxies, and bounded compatibility checks from being promoted as broader benchmark facts.

| Requested / target headline | Exact current evidence | Documentation disposition |
| :--- | :--- | :--- |
| `94% token compression (~48 tokens/step)` | `72.73%` fewer serialized bytes; master exhaustive scorecard marks `≥94% L0 symbolic-tensor payload reduction` **UNVERIFIED_SOURCE_GAP** | **Not promoted as verified.** Keep 94% as a target until tokenizer/source-bound execution exists. |
| `>5,250 receipts/sec SQLite WAL` | **19,934.69 writes/s** best observed | Publish **writes/s**, not receipts/s; no current source equates one WAL write with one full receipt. |
| `<95 MB RSS under 4GB edge budget` | **116.71 MiB** process RSS in the industry scorecard; master controller **117.348 MiB** | `<95 MiB` target is currently **FAIL / unverified for a narrower core worker**. Edge viability and the internal 95 MiB target are separate claims. |
| `<500 µs UDP mesh gossip latency` | p95 **10.126 µs** in the industry localhost run; master p95 **17.656 µs** | Threshold passes for the **localhost RTT proxy only**; remote mesh gossip remains unmeasured here. |
| `0% InjecAgent exploit rate` | **0/868** executable transitions; gate-layer ASR `0.0000%` | Publish as **gate-layer attack-surface result**, not official end-to-end InjecAgent ASR. |
| `100% Tau-bench trajectory accuracy` | **42/42** bounded legacy τ-bench task-lane trajectory preservation | Publish as **bounded trajectory preservation**, not official τ-bench pass^k. |

## Edge Deployment Readiness

The measured process high-water mark of **116.71 MiB** is small relative to a 4 GiB device-class memory budget, but AuraOS deliberately retains the stricter `<95 MiB` internal target as unresolved rather than rewriting the benchmark. SQLite WAL, localhost UDP, deterministic FST routing, bounded worker execution, and exact-source security gates all have executable repository evidence; remote network behavior, whole-device memory behavior, and broader external benchmark suites require their own environments.

## Advanced Benchmark Snapshot

See [`docs/ADVANCED_BENCHMARKS.md`](./docs/ADVANCED_BENCHMARKS.md) for methodology and scope boundaries.

These measurements are bounded host microbenchmarks. They do **not** by themselves establish production AuraOS, remote P2P mesh, crash-injection performance, or third-party benchmark certification.

## Reproduce

```bash
python3 scripts/aura_industry_benchmark_validation.py
python3 scripts/aura_advanced_benchmark_runner.py
python3 scripts/aura_security_accuracy_harness.py
```

Machine-readable outputs and signed/hashed receipts remain source evidence; signatures authenticate the recorded artifact against their declared key/material and do not independently establish human identity or promotion authority.

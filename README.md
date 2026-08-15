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

## Advanced Benchmark Snapshot

See [`docs/ADVANCED_BENCHMARKS.md`](./docs/ADVANCED_BENCHMARKS.md) for methodology and scope boundaries.

These measurements are bounded host microbenchmarks. They do **not** by themselves establish production AuraOS, remote P2P mesh, or crash-injection performance.

| Measurement | Result | Verification boundary |
| :--- | :--- | :--- |
| Synthetic JSON state projection | `286 B → 78 B` (**72.73% fewer bytes**) | Byte serialization only; not tokenizer-measured token compression |
| UDP localhost unicast | **299,701.80 datagrams/s**, median RTT **2.824 µs**, p95 RTT **3.225 µs** | 200 synchronous loopback round trips; not multicast/remote hops |
| SQLite WAL clean reopen/checkpoint | **0.309 ms**, `500/500` rows, `integrity_check=ok` | Clean reopen/checkpoint; no crash/chaos injection |

## Reproduce

```bash
python3 scripts/aura_advanced_benchmark_runner.py
```

Machine-readable results are written to `advanced_benchmark_results.json`.

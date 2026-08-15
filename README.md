# AuraOS

AuraOS is a minimal, local-first substrate for coordinating deterministic nodes, durable state, recursive rollups, and peer-to-peer execution without requiring a gas-metered chain for ordinary operation.

## Core features

- **Zero gas** — local/off-chain coordination and state transitions do not require per-operation gas fees.
- **3^n rollups** — recursive ternary aggregation compresses many child operations into progressively smaller parent summaries.
- **SQLite WAL** — write-ahead logging provides durable local state, atomic commits, crash recovery, and concurrent read access.
- **P2P mesh** — nodes exchange bounded state and work directly across a peer mesh rather than depending on one central coordinator.

## System architecture

```text
                         +----------------------+
                         |      Operator        |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      aura_node       |
                         | identity + local API |
                         +----------+-----------+
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
        +----------------------+           +----------------------+
        |     aura_daemon      |           |       P2P mesh       |
        | state + SQLite WAL   |<--------->| peer synchronization |
        +----------+-----------+           +----------+-----------+
                   |                                  |
                   +----------------+-----------------+
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

The operating rule is simple: keep exact state local, exchange only the bounded information peers need, roll work upward recursively, and preserve receipts for consequential transitions.

## Quickstart

```bash
# 1. Clone and enter the repository
git clone https://github.com/dallascourchene-commits/AuraOS.git && cd AuraOS

# 2. Start a node
python aura_node.py

# 3. Start the local state daemon
python aura_daemon.py

# 4. Start the swarm runner
python aura_swarm_runner.py
```

`aura_node.py` is present on the current repository line. `aura_daemon.py` and `aura_swarm_runner.py` are the normalized minimal-core entry points used by the streamlined substrate release and must be materialized with that release before those two commands are runnable.

## Scientific disclosure

> **Paper X — scientific disclosure**
>
> The architecture, research claims, evidence boundaries, and disclosure record for this substrate release are published in [`PAPER_X_ARXIV_DISCLOSURE.pdf`](PAPER_X_ARXIV_DISCLOSURE.pdf). Treat the paper as the scientific disclosure surface; executable source, tests, and receipts remain the implementation evidence.

## License

AuraOS is licensed under the **GNU Affero General Public License, version 3 (AGPLv3)**. Network-accessible modifications must preserve the license's corresponding-source obligations. See [`LICENSE`](LICENSE) for the full license text.

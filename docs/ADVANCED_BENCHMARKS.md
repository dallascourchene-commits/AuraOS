# Advanced Substrate Performance & Verification Metrics

These measurements are bounded host microbenchmarks. They do **not** by themselves establish production AuraOS, remote P2P mesh, or crash-injection performance.

| Measurement | Result | Verification boundary |
| :--- | :--- | :--- |
| Synthetic JSON state projection | `286 B → 78 B` (**72.73% fewer bytes**) | Byte serialization only; not tokenizer-measured token compression |
| UDP localhost unicast | **113,403.24 datagrams/s**, median RTT **7.080 µs**, p95 RTT **10.126 µs** | 200 synchronous loopback round trips; not multicast/remote hops |
| SQLite WAL clean reopen/checkpoint | **1.493 ms**, `500/500` rows, `integrity_check=ok` | Clean reopen/checkpoint; no crash/chaos injection |

## Reproduce

```bash
python3 scripts/aura_advanced_benchmark_runner.py
```

Machine-readable results are written to `advanced_benchmark_results.json`.

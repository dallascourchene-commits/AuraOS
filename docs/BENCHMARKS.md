# AuraOS Formal Benchmark Suite

Run with:

```bash
python3 scripts/aura_benchmark_suite.py
```

The suite is intentionally stdlib-only and writes the canonical human-readable run report to `BENCHMARK_RESULTS.md`.

## Workloads

1. **Six-slot FST transition kernel** — 100,000 deterministic accept/reject iterations over a bounded six-transition state machine. This is a transition-throughput microbenchmark; it is not a substitute for linguistic validation of a production morphological FST.
2. **Ternary Merkle aggregation** — 2,000 independent `3^n` rollups at `n=5` (243 leaves each), hashing leaf payloads and every internal ternary node.
3. **SQLite WAL scaling** — fixed-size ingestion trials from 1 through 25 concurrent workers, each with its own SQLite connection and one transaction per row.
4. **Peak RSS** — process high-water resident memory measured with `resource.getrusage(RUSAGE_SELF).ru_maxrss`.

## Interpretation

These are implementation microbenchmarks on the machine executing the suite. They are not hardware-independent performance guarantees. WAL scaling is expected to become contention-bound because SQLite serializes writers even in WAL mode; worker count is therefore a concurrency-stress axis, not an expectation of linear speedup.

## Latest observed summary

- FST: 1,366,040.46 iterations/s
- Merkle: 2,460.61 rollups/s
- Best WAL: 19,934.69 writes/s at 5 workers
- Peak RSS: 116.71 MiB

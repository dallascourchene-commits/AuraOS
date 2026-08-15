# AuraOS Benchmark Results

Generated: `2026-08-15T04:07:46Z`

## Scope

This run measures the pruned minimal AuraOS substrate. The FST result is a six-slot deterministic transition-kernel microbenchmark because the pruned workspace does not contain the historical production `aura_lexc` implementation. It measures transition throughput, not linguistic coverage or morphological accuracy.

## Summary

- FST: **1,366,040.46 iterations/s** (8,196,242.75 transitions/s), 100,000 iterations.
- Ternary Merkle: **2,460.61 rollups/s**, 2,000 rollups at depth 5 (243 leaves/rollup).
- Merkle hashing: **895,661.61 SHA-256 operations/s** across 728,000 leaf+internal hashes.
- SQLite WAL best: **19,934.69 writes/s at 5 workers** with 5,000 writes/trial.
- Peak RSS: **116.71 MiB**.

## FST Throughput

| Metric | Value |
|---|---:|
| Iterations | 100,000 |
| Slots per iteration | 6 |
| Accepted | 57,144 |
| Rejected | 42,856 |
| Elapsed | 0.073204 s |
| Iterations/s | 1,366,040.46 |
| Transitions/s | 8,196,242.75 |

## 3^n Merkle Aggregation

| Metric | Value |
|---|---:|
| Rollups | 2,000 |
| Depth n | 5 |
| Leaves per rollup (3^n) | 243 |
| Internal hashes per rollup | 121 |
| Total hashes | 728,000 |
| Elapsed | 0.812807 s |
| Rollups/s | 2,460.61 |
| Hashes/s | 895,661.61 |
| Aggregate witness | `220db7fe802a29350ee71ad08cc19b86dce79c8a384180860c24861a26a0c307` |

## SQLite WAL Ingestion Scaling

Each trial performs a fixed 5,000 one-row transactions into a fresh WAL database using separate SQLite connections per worker.

| Workers | Elapsed (s) | Writes/s | Speedup vs 1 | Lock retries |
|---:|---:|---:|---:|---:|
| 1 | 0.417927 | 11,963.81 | 1.000x | 0 |
| 2 | 0.295222 | 16,936.43 | 1.416x | 0 |
| 3 | 0.294159 | 16,997.64 | 1.421x | 0 |
| 4 | 0.290451 | 17,214.58 | 1.439x | 0 |
| 5 | 0.250819 | 19,934.69 | 1.666x | 0 |
| 6 | 0.327637 | 15,260.80 | 1.276x | 0 |
| 7 | 0.265051 | 18,864.28 | 1.577x | 0 |
| 8 | 0.291419 | 17,157.45 | 1.434x | 0 |
| 9 | 0.295006 | 16,948.78 | 1.417x | 0 |
| 10 | 0.278780 | 17,935.27 | 1.499x | 0 |
| 11 | 0.305256 | 16,379.70 | 1.369x | 0 |
| 12 | 0.342743 | 14,588.18 | 1.219x | 0 |
| 13 | 0.319218 | 15,663.27 | 1.309x | 0 |
| 14 | 0.332771 | 15,025.35 | 1.256x | 0 |
| 15 | 0.329248 | 15,186.10 | 1.269x | 0 |
| 16 | 0.303654 | 16,466.12 | 1.376x | 0 |
| 17 | 0.405730 | 12,323.45 | 1.030x | 0 |
| 18 | 0.415702 | 12,027.86 | 1.005x | 0 |
| 19 | 0.419770 | 11,911.29 | 0.996x | 0 |
| 20 | 0.468505 | 10,672.23 | 0.892x | 0 |
| 21 | 0.378863 | 13,197.39 | 1.103x | 0 |
| 22 | 0.424618 | 11,775.30 | 0.984x | 0 |
| 23 | 0.528131 | 9,467.35 | 0.791x | 0 |
| 24 | 0.359990 | 13,889.29 | 1.161x | 0 |
| 25 | 0.509279 | 9,817.80 | 0.821x | 0 |

## Memory

- Peak RSS: **122,376,192 bytes (116.71 MiB)**
- RSS measurement: `resource.getrusage(RUSAGE_SELF).ru_maxrss`

## Environment

- Python: `3.13.5 (main, Jul 15 2026, 20:25:40) [GCC 14.2.0]`
- Platform: `Linux-6.18.35-x86_64-with-glibc2.41`
- CPU count visible: `5`
- SQLite: `3.46.1`

## Validation

- FST valid/invalid transition assertions: **PASS**
- Merkle determinism assertion: **PASS**
- SQLite row count, WAL mode, and `PRAGMA integrity_check`: **PASS for workers 1..25**
- Suite status: **W_VALIDATED**

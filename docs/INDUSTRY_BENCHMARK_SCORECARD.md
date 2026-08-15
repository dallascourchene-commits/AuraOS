# AuraOS Industry Benchmark Validation Scorecard

**Work order:** `WO-FLEET-AUTONOMOUS-EXECUTE`  
**Source commit bound at run start:** `6c1dc7284eb019010fa4c091e4963e44d1f0e6ee`  
**Validation gates:** **15/15 passed**  
**Overall validation state:** **PASS**  

> This is an AuraOS repository-defined industry-readiness validation scorecard, not third-party certification and not an external percentile ranking. Performance rows are measured on the execution host; pass/fail gates are deterministic workload and correctness invariants rather than invented market thresholds.

## Performance measurements

| Surface | Measured result | Evidence boundary |
| :--- | :--- | :--- |
| FST deterministic routing | **1,366,040.46 iterations/s**, **8,196,242.75 transitions/s** over 100,000 iterations | six-slot deterministic transition microkernel; not linguistic/morphological accuracy |
| `3^n` Merkle aggregation | **2,460.61 rollups/s**, **895,661.61 hashes/s** | 2,000 rollups; depth n=5; 243 leaves/rollup |
| SQLite WAL best observed | **19,934.69 writes/s @ 5 workers** | 5,000 one-row transactions/trial; workers 1..25; row count + WAL + integrity verified |
| Peak RSS | **116.71 MiB** | process high-water mark |
| Synthetic JSON projection | **72.73% fewer serialized bytes** (`286 B → 78 B`) | byte serialization only; not tokenizer-measured token reduction |
| UDP localhost unicast | **113,403.24 datagrams/s**, median **7.080 µs**, p95 **10.126 µs** | 200 synchronous localhost unicast round trips; not remote mesh |
| SQLite WAL reopen/checkpoint | **1.493 ms** | clean reopen/checkpoint; 500/500 rows; integrity=ok |
| 25-slot daemon fleet | **25/25 exact-once DONE**, **0 duplicate fleet payloads** | process-spawned bounded workers; correctness-oriented; no throughput claim |

## Validation gates

| # | Gate | Result | Evidence |
|---:|:---|:---:|:---|
| 1 | Formal benchmark process | **PASS** | formal suite completed and wrote BENCHMARK_RESULTS.md |
| 2 | FST 100k verification | **PASS** | 100000 iterations; accepted=57144 rejected=42856; source assertions passed |
| 3 | 3^n Merkle 2k verification | **PASS** | 2000 rollups; depth=5; witness=220db7fe802a29350ee71ad08cc19b86dce79c8a384180860c24861a26a0c307 |
| 4 | SQLite WAL 1-25 verification | **PASS** | 25 worker-count trials; exact 5000 rows + WAL mode + integrity_check=ok in formal suite |
| 5 | Peak RSS captured | **PASS** | peak_rss_mib=116.71 |
| 6 | Advanced benchmark process | **PASS** | advanced benchmark completed |
| 7 | UDP loopback delivery | **PASS** | 200/200 synchronous localhost datagrams |
| 8 | WAL clean reopen integrity | **PASS** | 500/500 rows; integrity=ok |
| 9 | Python compile | **PASS** | dispatcher, daemon, formal runner, advanced runner compiled |
| 10 | 25-worker exact-once fleet | **PASS** | 25 DONE fleet tasks; unique_payloads=25; all payload indices 0..24 observed exactly once |
| 11 | Lease ownership fail-closed | **PASS** | wrong worker finish raised RuntimeError; owner completed task |
| 12 | Expired lease recovery | **PASS** | expired lease requeued, reclaimed by J_EXP_NEW, and completed |
| 13 | Unsupported shell task rejected | **PASS** | shell task status FAILED; unsupported_task_kind; marker not created |
| 14 | Benchmark dispatch via daemon | **PASS** | advanced_benchmark task completed through explicit daemon allowlist; returncode=0 |
| 15 | Dispatcher WAL integrity | **PASS** | journal_mode=wal; integrity_check=ok |

## Fleet state

- Dispatcher database: `journal_mode=wal`, `integrity_check=ok`.
- Final dispatcher task counts: `{"DONE": 28, "FAILED": 1}`.
- Lease ownership mismatch: rejected fail-closed.
- Expired lease: recovered by a different worker.
- Unsupported `shell` task: failed closed; marker payload was not executed.
- `advanced_benchmark` task: completed through the daemon explicit allowlist.

## Source bindings

| Path | Git blob SHA-1 | SHA-256 |
| :--- | :--- | :--- |
| `core/aura_task_dispatcher.py` | `68bb13f98031edfe374b3c74553cc3cdedfa7fa7` | `0b68ec8b8a2209184292d76be369b5b45511c4087618b9d4cba364018b3f7cbd` |
| `core/aura_worker_daemon.py` | `fd1a7f6e4e4ab6fce0a6a1ee24df16cceceb7835` | `fe75e41335be3c664882e97fe6ea8749e9ca5710f867191cea6cda7946fab307` |
| `scripts/aura_advanced_benchmark_runner.py` | `05d711a4594edcb2bc1d59705cdc2edc32882a47` | `82f16fc830aa9bc412d579ad7d589ae585c34237d8ac048db67820a055993f4b` |
| `scripts/aura_benchmark_suite.py` | `cb9ceeddee5ff2e9ce745cf9a76754ae6f26a169` | `e0bd8f8af38ecb857337191e5b4420de89c7f4c5167e2a5b3eb0c2c851bb30d9` |
| `scripts/aura_industry_benchmark_validation.py` | `c1c8f301e8698327a34a72d5817abb3fc8d1ad6e` | `47c35dbfd64228015318a7abd1b454e4288428b7f8cc0504f72c8ff731c61ecb` |

## Execution continuity

Composite validator exceeded the outer tool wall-clock after gate 13; its WAL state was preserved. Gate 14 was resumed from the pending dispatcher task and gate 15 was then verified against the same dispatcher generation. The timeout was orchestration-wall-clock, not a failed benchmark gate.

## Reproduce

```bash
python3 scripts/aura_industry_benchmark_validation.py --source-commit 6c1dc7284eb019010fa4c091e4963e44d1f0e6ee
```

The signed receipt is written to `aura_workspace/outbox/WO-FLEET-AUTONOMOUS-EXECUTE.receipt.json`. Its per-run Ed25519 public key is embedded in the receipt. That signature proves receipt payload integrity against the embedded key; it is **not** a human/organization identity signature or third-party certification.

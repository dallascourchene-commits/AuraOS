# AuraOS Industry Benchmark Validation Scorecard

**Work order:** `WO-FLEET-AUTONOMOUS-EXECUTE`  
**Source commit bound at run start:** `07a01763941998d93c192f467ea4930afbbb21fd`  
**Validation gates:** **15/15 passed**  
**Overall validation state:** **PASS**  

> This is an AuraOS industry-readiness validation scorecard, not third-party certification and not an external percentile ranking. Performance rows are measured on the execution host; pass/fail gates are deterministic workload and correctness invariants rather than invented market thresholds.

## Performance measurements

| Surface | Measured result | Evidence boundary |
| :--- | :--- | :--- |
| FST deterministic routing | **3,244,981.57 routes/s** over 100,000 routes | synthetic six-slot deterministic recognizer |
| 3^n Merkle aggregation | **16,904.98 rollups/s**, **2,045,503.01 hashes/s** | 2,000 rollups; depth n=4 |
| SQLite WAL 1 worker | **27,929.33 rows/s** | 200 rows, integrity verified |
| SQLite WAL best observed | **52,127.24 rows/s @ 2 workers** | host-local contention result |
| SQLite WAL 25 workers | **20,092.90 rows/s** | 5000 rows, integrity verified |
| Peak RSS | **115.95 MiB** | process high-water mark |
| Synthetic JSON projection | **72.73% fewer serialized bytes** | not tokenizer-measured token reduction |
| UDP localhost unicast | **309,622.45 datagrams/s**, median **2.834 µs**, p95 **3.144 µs** | localhost synchronous unicast, not remote mesh |
| SQLite WAL reopen/checkpoint | **0.300 ms** | clean reopen/checkpoint, 500/500 rows |
| 25-worker daemon fleet | **4.05 tasks/s**, **0 duplicates** | process-spawned one-shot workers; correctness-oriented |

## Validation gates

| # | Gate | Result | Evidence |
|---:|:---|:---:|:---|
| 1 | Formal benchmark process | PASS | formal suite exited 0 |
| 2 | FST 100k verification | PASS | checksum verified |
| 3 | 3^n Merkle 2k verification | PASS | hash count + aggregate root recorded |
| 4 | SQLite WAL 1-25 verification | PASS | 25 concurrency levels; exact rows + integrity |
| 5 | Peak RSS captured | PASS | process high-water mark recorded |
| 6 | Advanced benchmark process | PASS | advanced suite exited 0 |
| 7 | UDP loopback delivery | PASS | 200/200 synchronous localhost datagrams |
| 8 | WAL clean reopen integrity | PASS | 500/500 rows + integrity_check=ok |
| 9 | Python compile | PASS | dispatcher, daemon, formal and advanced runners |
| 10 | 25-worker exact-once fleet | PASS | 25 unique DONE tasks; zero duplicate payloads |
| 11 | Lease ownership fail-closed | PASS | wrong worker cannot finish leased task |
| 12 | Expired lease recovery | PASS | expired lease requeued and reclaimed |
| 13 | Unsupported shell task rejected | PASS | allowlist rejected shell; marker not created |
| 14 | Benchmark dispatch via daemon | PASS | advanced_benchmark allowlist path completed |
| 15 | Dispatcher WAL integrity | PASS | integrity_check=ok; WAL |

## Source bindings

| Path | Git blob SHA-1 calculated at run time |
| :--- | :--- |
| `core/aura_task_dispatcher.py` | `68bb13f98031edfe374b3c74553cc3cdedfa7fa7` |
| `core/aura_worker_daemon.py` | `fd1a7f6e4e4ab6fce0a6a1ee24df16cceceb7835` |
| `scripts/aura_advanced_benchmark_runner.py` | `05d711a4594edcb2bc1d59705cdc2edc32882a47` |
| `scripts/aura_benchmark_suite.py` | `a5d1f1105eb033466edd3077d6088f43f68f802c` |


## Fleet state

- Dispatcher database: `journal_mode=WAL`, `integrity_check=ok`.
- Final dispatcher task counts: `{"DONE": 28, "FAILED": 1}`.
- Lease ownership mismatch: rejected.
- Expired lease: recovered by a different worker.
- Unsupported `shell` task: failed closed; payload was not executed.
- `advanced_benchmark` task: completed through the daemon's explicit allowlist.

## Reproduce

```bash
python3 scripts/aura_industry_benchmark_validation.py --source-commit 07a01763941998d93c192f467ea4930afbbb21fd
```

The receipt in `aura_workspace/outbox/` is Ed25519-signed with a per-run ephemeral key whose public key is embedded in the receipt. That proves receipt integrity against the embedded key; it is **not** an identity signature from a pre-existing human or organization key.

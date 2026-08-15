#!/usr/bin/env python3
"""AuraOS formal benchmark suite.

Measures four bounded properties of the minimal substrate:
1) deterministic six-slot L0 FST transition throughput (100,000 iterations),
2) ternary 3^n Merkle aggregation throughput (2,000 rollups),
3) SQLite WAL ingestion scaling for 1..25 concurrent workers, and
4) peak resident-set size (RSS) of this benchmark process.

The FST test is intentionally a transition-kernel microbenchmark. The minimal
pruned substrate does not currently ship the historical production aura_lexc
implementation, so this benchmark does not claim morphological-quality or
language-coverage validation.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import resource
import sqlite3
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
RESULTS_MD = ROOT / "BENCHMARK_RESULTS.md"
DOCS_MD = ROOT / "docs" / "BENCHMARKS.md"

FST_ITERATIONS = 100_000
MERKLE_ROLLUPS = 2_000
MERKLE_DEPTH = 5  # 3^5 = 243 leaves per rollup
SQLITE_TOTAL_WRITES = 5_000
SQLITE_MAX_WORKERS = 25


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def now_ns() -> int:
    return time.perf_counter_ns()


def seconds_since(start_ns: int) -> float:
    return (time.perf_counter_ns() - start_ns) / 1_000_000_000.0


def peak_rss_bytes() -> int:
    # Linux ru_maxrss is KiB; macOS reports bytes. AuraOS benchmark target here
    # is Linux, but keep the conversion portable.
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        return value
    return value * 1024


def mib(n: int) -> float:
    return n / (1024.0 * 1024.0)


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# ---------------------------------------------------------------------------
# 1) Six-slot deterministic FST transition kernel
# ---------------------------------------------------------------------------
# Six ordered symbol classes stand in for the bounded six-slot L0 syntax
# boundary. This isolates transition overhead from tokenizer / I/O overhead.
SLOT_CLASSES = ("P", "R", "C", "M", "S", "E")
FST_TRANSITIONS = {(state, symbol): state + 1 for state, symbol in enumerate(SLOT_CLASSES)}
FST_ACCEPT_STATE = len(SLOT_CLASSES)

VALID_FORMS: tuple[tuple[str, ...], ...] = tuple(
    tuple(SLOT_CLASSES) for _ in range(8)
)
INVALID_FORMS: tuple[tuple[str, ...], ...] = tuple(
    tuple(list(SLOT_CLASSES[:i]) + ["X"] + list(SLOT_CLASSES[i + 1 :]))
    for i in range(len(SLOT_CLASSES))
)
FST_CORPUS = VALID_FORMS + INVALID_FORMS


def fst_accept(symbols: Sequence[str]) -> bool:
    state = 0
    for symbol in symbols:
        next_state = FST_TRANSITIONS.get((state, symbol))
        if next_state is None:
            return False
        state = next_state
    return state == FST_ACCEPT_STATE


def bench_fst(iterations: int = FST_ITERATIONS) -> dict:
    # correctness gate before timing
    if not fst_accept(SLOT_CLASSES):
        raise AssertionError("FST failed canonical valid form")
    for i in range(len(SLOT_CLASSES)):
        bad = list(SLOT_CLASSES)
        bad[i] = "X"
        if fst_accept(bad):
            raise AssertionError(f"FST accepted invalid form at slot {i}")

    # warm up interpreter caches
    for i in range(2_000):
        fst_accept(FST_CORPUS[i % len(FST_CORPUS)])

    accepted = 0
    start = now_ns()
    for i in range(iterations):
        accepted += int(fst_accept(FST_CORPUS[i % len(FST_CORPUS)]))
    elapsed = seconds_since(start)
    transitions = iterations * len(SLOT_CLASSES)
    return {
        "iterations": iterations,
        "slots_per_iteration": len(SLOT_CLASSES),
        "accepted": accepted,
        "rejected": iterations - accepted,
        "elapsed_s": elapsed,
        "iterations_per_s": iterations / elapsed,
        "transitions_per_s": transitions / elapsed,
        "scope": "six-slot deterministic L0 transition microkernel",
    }


# ---------------------------------------------------------------------------
# 2) 3^n ternary Merkle aggregation
# ---------------------------------------------------------------------------
def ternary_merkle_root(leaves: list[bytes]) -> tuple[bytes, int]:
    if not leaves:
        raise ValueError("leaves must be non-empty")
    level = leaves
    internal_hashes = 0
    while len(level) > 1:
        if len(level) % 3:
            raise ValueError("ternary level length must be divisible by 3")
        nxt: list[bytes] = []
        for i in range(0, len(level), 3):
            nxt.append(sha256_bytes(b"\x01" + level[i] + level[i + 1] + level[i + 2]))
            internal_hashes += 1
        level = nxt
    return level[0], internal_hashes


def bench_merkle(rollups: int = MERKLE_ROLLUPS, depth: int = MERKLE_DEPTH) -> dict:
    leaf_count = 3 ** depth
    # deterministic leaf material; each rollup perturbs the prefix to prevent
    # accidental constant-result optimization assumptions.
    base_payloads = [f"aura-leaf-{i}".encode() for i in range(leaf_count)]

    # correctness / determinism gate
    leaves0 = [sha256_bytes(b"0:" + p) for p in base_payloads]
    r1, internal = ternary_merkle_root(leaves0)
    r2, internal2 = ternary_merkle_root(leaves0)
    if r1 != r2 or internal != internal2:
        raise AssertionError("Merkle rollup is non-deterministic")

    roots: list[bytes] = []
    total_internal = 0
    start = now_ns()
    for n in range(rollups):
        prefix = n.to_bytes(4, "big") + b":"
        leaves = [sha256_bytes(prefix + p) for p in base_payloads]
        root, internal_hashes = ternary_merkle_root(leaves)
        roots.append(root)
        total_internal += internal_hashes
    elapsed = seconds_since(start)
    total_leaf_hashes = rollups * leaf_count
    total_hashes = total_leaf_hashes + total_internal
    aggregate_witness = hashlib.sha256(b"".join(roots)).hexdigest()
    return {
        "rollups": rollups,
        "depth": depth,
        "leaves_per_rollup": leaf_count,
        "internal_hashes_per_rollup": internal,
        "total_hashes": total_hashes,
        "elapsed_s": elapsed,
        "rollups_per_s": rollups / elapsed,
        "hashes_per_s": total_hashes / elapsed,
        "aggregate_witness_sha256": aggregate_witness,
    }


# ---------------------------------------------------------------------------
# 3) SQLite WAL scaling, 1..25 concurrent worker threads
# ---------------------------------------------------------------------------
def _wal_worker(db_path: str, worker_id: int, writes: int) -> tuple[int, int]:
    con = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
    try:
        con.execute("PRAGMA busy_timeout=30000")
        con.execute("PRAGMA synchronous=NORMAL")
        inserted = 0
        retries = 0
        for i in range(writes):
            payload = hashlib.sha256(f"{worker_id}:{i}".encode()).hexdigest()
            # One row per transaction is deliberate: measure serialized WAL
            # commit pressure rather than bulk-transaction throughput.
            for attempt in range(20):
                try:
                    con.execute(
                        "INSERT INTO events(worker_id, seq, payload) VALUES(?,?,?)",
                        (worker_id, i, payload),
                    )
                    inserted += 1
                    break
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower() or attempt == 19:
                        raise
                    retries += 1
                    time.sleep(min(0.0005 * (2 ** attempt), 0.05))
        return inserted, retries
    finally:
        con.close()


def _prepare_wal_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        mode = con.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            raise RuntimeError(f"failed to enable WAL mode: {mode}")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute(
            "CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER NOT NULL, seq INTEGER NOT NULL, payload TEXT NOT NULL, UNIQUE(worker_id,seq))"
        )
        con.commit()
    finally:
        con.close()


def bench_sqlite_scaling(total_writes: int = SQLITE_TOTAL_WRITES, max_workers: int = SQLITE_MAX_WORKERS) -> dict:
    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="aura-bench-wal-") as td:
        for workers in range(1, max_workers + 1):
            db_path = Path(td) / f"wal-{workers}.db"
            _prepare_wal_db(db_path)
            q, r = divmod(total_writes, workers)
            assignments = [q + (1 if wid < r else 0) for wid in range(workers)]

            start = now_ns()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_wal_worker, str(db_path), wid, n) for wid, n in enumerate(assignments)]
                results = [f.result() for f in futures]
            elapsed = seconds_since(start)

            inserted = sum(x[0] for x in results)
            retries = sum(x[1] for x in results)
            con = sqlite3.connect(db_path)
            try:
                count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
                journal_mode = con.execute("PRAGMA journal_mode").fetchone()[0]
            finally:
                con.close()
            if inserted != total_writes or count != total_writes or integrity != "ok" or str(journal_mode).lower() != "wal":
                raise AssertionError(
                    f"WAL validation failed workers={workers} inserted={inserted} count={count} integrity={integrity} mode={journal_mode}"
                )
            rows.append(
                {
                    "workers": workers,
                    "writes": total_writes,
                    "elapsed_s": elapsed,
                    "writes_per_s": total_writes / elapsed,
                    "lock_retries": retries,
                }
            )

    baseline = rows[0]["writes_per_s"]
    for row in rows:
        row["speedup_vs_1"] = row["writes_per_s"] / baseline
    best = max(rows, key=lambda r: r["writes_per_s"])
    return {
        "total_writes_per_trial": total_writes,
        "worker_range": [1, max_workers],
        "rows": rows,
        "best_workers": best["workers"],
        "best_writes_per_s": best["writes_per_s"],
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _fmt(x: float) -> str:
    return f"{x:,.2f}"


def render_results(result: dict) -> str:
    fst = result["fst"]
    merkle = result["merkle"]
    wal = result["sqlite_wal"]
    mem = result["memory"]
    lines = [
        "# AuraOS Benchmark Results",
        "",
        f"Generated: `{result['generated_utc']}`",
        "",
        "## Scope",
        "",
        "This run measures the pruned minimal AuraOS substrate. The FST result is a six-slot deterministic transition-kernel microbenchmark because the pruned workspace does not contain the historical production `aura_lexc` implementation. It measures transition throughput, not linguistic coverage or morphological accuracy.",
        "",
        "## Summary",
        "",
        f"- FST: **{_fmt(fst['iterations_per_s'])} iterations/s** ({_fmt(fst['transitions_per_s'])} transitions/s), {fst['iterations']:,} iterations.",
        f"- Ternary Merkle: **{_fmt(merkle['rollups_per_s'])} rollups/s**, {merkle['rollups']:,} rollups at depth {merkle['depth']} ({merkle['leaves_per_rollup']:,} leaves/rollup).",
        f"- Merkle hashing: **{_fmt(merkle['hashes_per_s'])} SHA-256 operations/s** across {merkle['total_hashes']:,} leaf+internal hashes.",
        f"- SQLite WAL best: **{_fmt(wal['best_writes_per_s'])} writes/s at {wal['best_workers']} workers** with {wal['total_writes_per_trial']:,} writes/trial.",
        f"- Peak RSS: **{mem['peak_rss_mib']:.2f} MiB**.",
        "",
        "## FST Throughput",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Iterations | {fst['iterations']:,} |",
        f"| Slots per iteration | {fst['slots_per_iteration']} |",
        f"| Accepted | {fst['accepted']:,} |",
        f"| Rejected | {fst['rejected']:,} |",
        f"| Elapsed | {fst['elapsed_s']:.6f} s |",
        f"| Iterations/s | {_fmt(fst['iterations_per_s'])} |",
        f"| Transitions/s | {_fmt(fst['transitions_per_s'])} |",
        "",
        "## 3^n Merkle Aggregation",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rollups | {merkle['rollups']:,} |",
        f"| Depth n | {merkle['depth']} |",
        f"| Leaves per rollup (3^n) | {merkle['leaves_per_rollup']:,} |",
        f"| Internal hashes per rollup | {merkle['internal_hashes_per_rollup']:,} |",
        f"| Total hashes | {merkle['total_hashes']:,} |",
        f"| Elapsed | {merkle['elapsed_s']:.6f} s |",
        f"| Rollups/s | {_fmt(merkle['rollups_per_s'])} |",
        f"| Hashes/s | {_fmt(merkle['hashes_per_s'])} |",
        f"| Aggregate witness | `{merkle['aggregate_witness_sha256']}` |",
        "",
        "## SQLite WAL Ingestion Scaling",
        "",
        f"Each trial performs a fixed {wal['total_writes_per_trial']:,} one-row transactions into a fresh WAL database using separate SQLite connections per worker.",
        "",
        "| Workers | Elapsed (s) | Writes/s | Speedup vs 1 | Lock retries |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in wal["rows"]:
        lines.append(
            f"| {row['workers']} | {row['elapsed_s']:.6f} | {_fmt(row['writes_per_s'])} | {row['speedup_vs_1']:.3f}x | {row['lock_retries']} |"
        )
    lines += [
        "",
        "## Memory",
        "",
        f"- Peak RSS: **{mem['peak_rss_bytes']:,} bytes ({mem['peak_rss_mib']:.2f} MiB)**",
        f"- RSS measurement: `{mem['method']}`",
        "",
        "## Environment",
        "",
        f"- Python: `{result['environment']['python']}`",
        f"- Platform: `{result['environment']['platform']}`",
        f"- CPU count visible: `{result['environment']['cpu_count']}`",
        f"- SQLite: `{result['environment']['sqlite_version']}`",
        "",
        "## Validation",
        "",
        "- FST valid/invalid transition assertions: **PASS**",
        "- Merkle determinism assertion: **PASS**",
        "- SQLite row count, WAL mode, and `PRAGMA integrity_check`: **PASS for workers 1..25**",
        "- Suite status: **W_VALIDATED**",
        "",
    ]
    return "\n".join(lines)


def render_docs(result: dict) -> str:
    return "\n".join(
        [
            "# AuraOS Formal Benchmark Suite",
            "",
            "Run with:",
            "",
            "```bash",
            "python3 scripts/aura_benchmark_suite.py",
            "```",
            "",
            "The suite is intentionally stdlib-only and writes the canonical human-readable run report to `BENCHMARK_RESULTS.md`.",
            "",
            "## Workloads",
            "",
            "1. **Six-slot FST transition kernel** — 100,000 deterministic accept/reject iterations over a bounded six-transition state machine. This is a transition-throughput microbenchmark; it is not a substitute for linguistic validation of a production morphological FST.",
            "2. **Ternary Merkle aggregation** — 2,000 independent `3^n` rollups at `n=5` (243 leaves each), hashing leaf payloads and every internal ternary node.",
            "3. **SQLite WAL scaling** — fixed-size ingestion trials from 1 through 25 concurrent workers, each with its own SQLite connection and one transaction per row.",
            "4. **Peak RSS** — process high-water resident memory measured with `resource.getrusage(RUSAGE_SELF).ru_maxrss`.",
            "",
            "## Interpretation",
            "",
            "These are implementation microbenchmarks on the machine executing the suite. They are not hardware-independent performance guarantees. WAL scaling is expected to become contention-bound because SQLite serializes writers even in WAL mode; worker count is therefore a concurrency-stress axis, not an expectation of linear speedup.",
            "",
            "## Latest observed summary",
            "",
            f"- FST: {result['fst']['iterations_per_s']:,.2f} iterations/s",
            f"- Merkle: {result['merkle']['rollups_per_s']:,.2f} rollups/s",
            f"- Best WAL: {result['sqlite_wal']['best_writes_per_s']:,.2f} writes/s at {result['sqlite_wal']['best_workers']} workers",
            f"- Peak RSS: {result['memory']['peak_rss_mib']:.2f} MiB",
            "",
        ]
    )


def run_suite() -> dict:
    suite_start = now_ns()
    rss_start = peak_rss_bytes()
    fst = bench_fst()
    merkle = bench_merkle()
    wal = bench_sqlite_scaling()
    elapsed = seconds_since(suite_start)
    peak = peak_rss_bytes()
    result = {
        "schema": "AURA_BENCHMARK_SUITE_V1",
        "status": "W_VALIDATED",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "suite_elapsed_s": elapsed,
        "fst": fst,
        "merkle": merkle,
        "sqlite_wal": wal,
        "memory": {
            "rss_at_start_bytes": rss_start,
            "peak_rss_bytes": peak,
            "peak_rss_mib": mib(peak),
            "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
        },
        "environment": {
            "python": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "sqlite_version": sqlite3.sqlite_version,
        },
    }
    RESULTS_MD.write_text(render_results(result), encoding="utf-8")
    DOCS_MD.parent.mkdir(parents=True, exist_ok=True)
    DOCS_MD.write_text(render_docs(result), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print machine-readable result")
    args = parser.parse_args()
    result = run_suite()
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(render_results(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

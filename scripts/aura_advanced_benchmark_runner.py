#!/usr/bin/env python3
"""Reproducible bounded host benchmark for WO-AUTONOMOUS-TAKEOVER-001.

Measures only:
- JSON byte-size reduction for a synthetic state projection,
- synchronous UDP localhost round-trip throughput/latency,
- SQLite WAL clean reopen/checkpoint time and integrity.

It does not claim network multicast performance, crash-injection recovery, or
production AuraOS end-to-end performance.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

ROOT = Path.cwd()
DOC = ROOT / "docs" / "ADVANCED_BENCHMARKS.md"
JSON_OUT = ROOT / "advanced_benchmark_results.json"


def pct(v: float) -> float:
    return round(v, 2)


def main() -> None:
    raw_history = {
        "turn": 14,
        "agent": "worker_ling",
        "msgs": [{"role": "user", "content": "Test EVA corpus"}] * 5,
    }
    raw_bytes = len(json.dumps(raw_history).encode("utf-8"))
    aura_state = {
        "slot_mask": 0b111000111,
        "h_inv": hashlib.sha256(b"test").hexdigest()[:16],
        "ts": int(time.time()),
        "status": 0x01,
    }
    aura_bytes = len(json.dumps(aura_state).encode("utf-8"))
    reduction = pct((1.0 - aura_bytes / raw_bytes) * 100.0)

    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 8421))
    rx.settimeout(0.5)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    lat_us: list[float] = []
    received = 0
    start = time.perf_counter()
    for i in range(200):
        t0 = time.perf_counter_ns()
        tx.sendto(hashlib.sha256(f"root_{i}".encode()).digest(), ("127.0.0.1", 8421))
        try:
            data, _ = rx.recvfrom(64)
            if len(data) == 32:
                received += 1
                lat_us.append((time.perf_counter_ns() - t0) / 1000.0)
        except socket.timeout:
            pass
    elapsed = time.perf_counter() - start
    rx.close()
    tx.close()
    udp_rate = received / elapsed if elapsed else 0.0
    lat_us_sorted = sorted(lat_us)
    p95_index = max(0, min(len(lat_us_sorted) - 1, int(0.95 * len(lat_us_sorted)) - 1))
    udp_median_us = statistics.median(lat_us_sorted) if lat_us_sorted else None
    udp_p95_us = lat_us_sorted[p95_index] if lat_us_sorted else None

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
    conn = sqlite3.connect(db_path)
    mode = conn.execute("PRAGMA journal_mode=WAL;").fetchone()[0]
    conn.execute("CREATE TABLE ledger (id INT, hash TEXT);")
    for i in range(500):
        conn.execute(
            "INSERT INTO ledger VALUES (?, ?);",
            (i, hashlib.sha256(str(i).encode()).hexdigest()),
        )
    conn.commit()
    conn.close()

    start_rec = time.perf_counter()
    r_conn = sqlite3.connect(db_path)
    r_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    rec_count = r_conn.execute("SELECT count(*) FROM ledger;").fetchone()[0]
    integrity = r_conn.execute("PRAGMA integrity_check;").fetchone()[0]
    r_conn.close()
    rec_time_ms = (time.perf_counter() - start_rec) * 1000.0
    for ext in ("", "-wal", "-shm"):
        try:
            os.remove(db_path + ext)
        except FileNotFoundError:
            pass

    results = {
        "scope": "bounded host microbenchmark",
        "json_projection": {
            "raw_bytes": raw_bytes,
            "projected_bytes": aura_bytes,
            "byte_reduction_pct": reduction,
            "note": "Synthetic JSON byte-size comparison; not tokenizer-measured token compression.",
        },
        "udp_loopback": {
            "packets_sent": 200,
            "packets_received": received,
            "datagrams_per_sec": round(udp_rate, 2),
            "median_round_trip_us": round(udp_median_us, 3) if udp_median_us is not None else None,
            "p95_round_trip_us": round(udp_p95_us, 3) if udp_p95_us is not None else None,
            "note": "Synchronous localhost UDP unicast round trips; not multicast or remote mesh hops.",
        },
        "sqlite_wal": {
            "journal_mode": mode,
            "rows_expected": 500,
            "rows_recovered": rec_count,
            "integrity_check": integrity,
            "reopen_checkpoint_ms": round(rec_time_ms, 3),
            "note": "Clean reopen + WAL checkpoint; not crash/chaos injection.",
        },
    }

    JSON_OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "# Advanced Substrate Performance & Verification Metrics\n\n"
        "These measurements are bounded host microbenchmarks. They do **not** by themselves establish production AuraOS, remote P2P mesh, or crash-injection performance.\n\n"
        "| Measurement | Result | Verification boundary |\n"
        "| :--- | :--- | :--- |\n"
        f"| Synthetic JSON state projection | `{raw_bytes} B → {aura_bytes} B` (**{reduction}% fewer bytes**) | Byte serialization only; not tokenizer-measured token compression |\n"
        f"| UDP localhost unicast | **{udp_rate:,.2f} datagrams/s**, median RTT **{udp_median_us:.3f} µs**, p95 RTT **{udp_p95_us:.3f} µs** | 200 synchronous loopback round trips; not multicast/remote hops |\n"
        f"| SQLite WAL clean reopen/checkpoint | **{rec_time_ms:.3f} ms**, `{rec_count}/500` rows, `integrity_check={integrity}` | Clean reopen/checkpoint; no crash/chaos injection |\n\n"
        "## Reproduce\n\n"
        "```bash\npython3 scripts/aura_advanced_benchmark_runner.py\n```\n\n"
        "Machine-readable results are written to `advanced_benchmark_results.json`.\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

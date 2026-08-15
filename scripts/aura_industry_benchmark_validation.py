#!/usr/bin/env python3
"""AuraOS bounded industry-readiness validation orchestrator.

This script composes repository-defined implementation microbenchmarks with
correctness, lease, fail-closed, and exact-once fleet checks. It does not claim
third-party certification, market percentile ranking, or hardware-independent
performance guarantees.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
SCRIPTS = ROOT / "scripts"
OUTBOX = ROOT / "aura_workspace" / "outbox"
RESULT_JSON = OUTBOX / "WO-FLEET-AUTONOMOUS-EXECUTE.industry-validation.json"
DB_PATH = ROOT / "aura_workspace" / "industry_validation_dispatcher.db"

sys.path.insert(0, str(CORE))
from aura_task_dispatcher import TaskDispatcher  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def clean_db(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(str(path) + suffix).unlink()
        except FileNotFoundError:
            pass


def run_json(command: list[str], timeout: float = 180.0) -> tuple[subprocess.CompletedProcess[str], dict]:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed {command}: {proc.stderr[-4000:]}")
    return proc, json.loads(proc.stdout)


def gate(gates: list[dict], number: int, name: str, ok: bool, evidence: str) -> None:
    gates.append({"number": number, "gate": name, "status": "PASS" if ok else "FAIL", "evidence": evidence})
    if not ok:
        raise AssertionError(f"gate {number} failed: {name}: {evidence}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", default="UNKNOWN")
    args = parser.parse_args()
    OUTBOX.mkdir(parents=True, exist_ok=True)
    gates: list[dict] = []

    formal_cmd = [sys.executable, str(SCRIPTS / "aura_benchmark_suite.py"), "--json"]
    formal_proc, formal = run_json(formal_cmd)
    gate(gates, 1, "Formal benchmark process", formal_proc.returncode == 0, "formal suite exited 0")
    gate(
        gates, 2, "FST 100k verification",
        formal.get("status") == "W_VALIDATED" and formal["fst"]["iterations"] == 100_000 and formal["fst"]["accepted"] + formal["fst"]["rejected"] == 100_000,
        f"iterations={formal['fst']['iterations']} accepted={formal['fst']['accepted']} rejected={formal['fst']['rejected']}",
    )
    merkle = formal["merkle"]
    gate(
        gates, 3, "3^n Merkle 2k verification",
        merkle["rollups"] == 2_000 and merkle["aggregate_witness_sha256"] and len(merkle["aggregate_witness_sha256"]) == 64,
        f"rollups={merkle['rollups']} depth={merkle['depth']} total_hashes={merkle['total_hashes']} witness={merkle['aggregate_witness_sha256']}",
    )
    wal = formal["sqlite_wal"]
    gate(
        gates, 4, "SQLite WAL 1-25 verification",
        wal["worker_range"] == [1, 25] and len(wal["rows"]) == 25 and all(r["writes"] == wal["total_writes_per_trial"] for r in wal["rows"]),
        f"trials={len(wal['rows'])} writes_per_trial={wal['total_writes_per_trial']} best={wal['best_writes_per_s']:.2f}@{wal['best_workers']}",
    )
    gate(gates, 5, "Peak RSS captured", formal["memory"]["peak_rss_bytes"] > 0, f"peak_rss_mib={formal['memory']['peak_rss_mib']:.2f}")

    advanced_cmd = [sys.executable, str(SCRIPTS / "aura_advanced_benchmark_runner.py")]
    advanced_proc, advanced = run_json(advanced_cmd)
    gate(gates, 6, "Advanced benchmark process", advanced_proc.returncode == 0, "advanced suite exited 0")
    udp = advanced["udp_loopback"]
    gate(gates, 7, "UDP loopback delivery", udp["packets_received"] == udp["packets_sent"] == 200, f"received={udp['packets_received']}/200")
    aw = advanced["sqlite_wal"]
    gate(gates, 8, "WAL clean reopen integrity", aw["rows_recovered"] == aw["rows_expected"] == 500 and aw["integrity_check"] == "ok" and str(aw["journal_mode"]).lower() == "wal", f"rows={aw['rows_recovered']}/500 integrity={aw['integrity_check']} mode={aw['journal_mode']}")

    compile_paths = [
        CORE / "aura_task_dispatcher.py",
        CORE / "aura_worker_daemon.py",
        SCRIPTS / "aura_benchmark_suite.py",
        SCRIPTS / "aura_advanced_benchmark_runner.py",
    ]
    for path in compile_paths:
        py_compile.compile(str(path), doraise=True)
    gate(gates, 9, "Python compile", True, "dispatcher, daemon, formal runner, advanced runner compiled")

    clean_db(DB_PATH)
    dispatcher = TaskDispatcher(DB_PATH)
    fleet_task_ids: list[str] = []
    for i in range(25):
        fleet_task_ids.append(dispatcher.enqueue("noop", {"fleet_index": i}))

    # Spawn one bounded one-shot daemon process per fleet slot in small batches.
    # This exercises concurrent claiming without creating a 25-process startup
    # lock storm around SQLite journal initialization. Exact-once semantics are
    # verified in the shared dispatcher database.
    fleet_outputs = []
    batch_size = 5
    for start_i in range(0, 25, batch_size):
        procs = [
            subprocess.Popen(
                [sys.executable, str(CORE / "aura_worker_daemon.py"), "--db", str(DB_PATH.relative_to(ROOT)), "--worker-id", f"J{i+1:02d}", "--once"],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            for i in range(start_i, min(start_i + batch_size, 25))
        ]
        for proc in procs:
            out, err = proc.communicate(timeout=60)
            fleet_outputs.append({"returncode": proc.returncode, "stdout": out[-2000:], "stderr": err[-2000:]})
    status = dispatcher.status()
    fleet_rows = [r for r in status if r["task_id"] in set(fleet_task_ids)]
    done = [r for r in fleet_rows if r["status"] == "DONE"]
    payload_indexes = []
    for row in done:
        result = json.loads(row["result_json"] or "{}")
        payload_indexes.append(result.get("echo", {}).get("fleet_index"))
    exact_once = len(done) == 25 and len(set(payload_indexes)) == 25 and set(payload_indexes) == set(range(25)) and all(p["returncode"] == 0 for p in fleet_outputs)
    gate(gates, 10, "25-worker exact-once fleet", exact_once, f"done={len(done)} unique_payloads={len(set(payload_indexes))} worker_processes={len(fleet_outputs)}")

    lease_task = dispatcher.enqueue("noop", {"case": "lease-owner"})
    lease = dispatcher.claim("J_OWNER", lease_seconds=60)
    wrong_owner_rejected = False
    try:
        dispatcher.finish(lease_task, "J_WRONG", ok=True, result={"ok": True})
    except RuntimeError:
        wrong_owner_rejected = True
    if lease is not None and lease["task_id"] == lease_task:
        dispatcher.finish(lease_task, "J_OWNER", ok=True, result={"ok": True, "case": "lease-owner"})
    gate(gates, 11, "Lease ownership fail-closed", wrong_owner_rejected, "wrong worker finish rejected")

    expiry_task = dispatcher.enqueue("noop", {"case": "expiry"})
    first = dispatcher.claim("J_EXP_OLD", lease_seconds=0.01)
    time.sleep(0.03)
    second = dispatcher.claim("J_EXP_NEW", lease_seconds=60)
    expiry_ok = first is not None and second is not None and first["task_id"] == expiry_task == second["task_id"] and second["leased_by"] == "J_EXP_NEW"
    if expiry_ok:
        dispatcher.finish(expiry_task, "J_EXP_NEW", ok=True, result={"ok": True, "case": "expiry-recovered"})
    gate(gates, 12, "Expired lease recovery", expiry_ok, "expired lease requeued and reclaimed by different worker")

    marker = ROOT / "aura_workspace" / "UNSUPPORTED_SHELL_MARKER"
    try:
        marker.unlink()
    except FileNotFoundError:
        pass
    shell_task = dispatcher.enqueue("shell", {"command": f"touch {marker}"})
    shell_proc = subprocess.run(
        [sys.executable, str(CORE / "aura_worker_daemon.py"), "--db", str(DB_PATH.relative_to(ROOT)), "--worker-id", "J_SHELL", "--once"],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    shell_row = next(r for r in dispatcher.status() if r["task_id"] == shell_task)
    shell_result = json.loads(shell_row["result_json"] or "{}")
    shell_ok = shell_proc.returncode == 0 and shell_row["status"] == "FAILED" and shell_result.get("error") == "unsupported_task_kind" and not marker.exists()
    gate(gates, 13, "Unsupported shell task rejected", shell_ok, f"status={shell_row['status']} marker_exists={marker.exists()}")

    adv_task = dispatcher.enqueue("advanced_benchmark", {"source": "industry-validation"})
    adv_daemon = subprocess.run(
        [sys.executable, str(CORE / "aura_worker_daemon.py"), "--db", str(DB_PATH.relative_to(ROOT)), "--worker-id", "J_ADV", "--once"],
        cwd=ROOT, text=True, capture_output=True, timeout=180,
    )
    adv_row = next(r for r in dispatcher.status() if r["task_id"] == adv_task)
    adv_result = json.loads(adv_row["result_json"] or "{}")
    adv_ok = adv_daemon.returncode == 0 and adv_row["status"] == "DONE" and adv_result.get("ok") is True and adv_result.get("returncode") == 0
    gate(gates, 14, "Benchmark dispatch via daemon", adv_ok, f"status={adv_row['status']} returncode={adv_result.get('returncode')}")

    con = sqlite3.connect(DB_PATH)
    try:
        mode = con.execute("PRAGMA journal_mode").fetchone()[0]
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        con.close()
    gate(gates, 15, "Dispatcher WAL integrity", str(mode).lower() == "wal" and integrity == "ok", f"journal_mode={mode} integrity_check={integrity}")

    final_status = dispatcher.status()
    counts = Counter(r["status"] for r in final_status)
    sources = {
        "core/aura_task_dispatcher.py": {"sha256": sha256(CORE / "aura_task_dispatcher.py"), "git_blob_sha1": git_blob_sha1(CORE / "aura_task_dispatcher.py")},
        "core/aura_worker_daemon.py": {"sha256": sha256(CORE / "aura_worker_daemon.py"), "git_blob_sha1": git_blob_sha1(CORE / "aura_worker_daemon.py")},
        "scripts/aura_advanced_benchmark_runner.py": {"sha256": sha256(SCRIPTS / "aura_advanced_benchmark_runner.py"), "git_blob_sha1": git_blob_sha1(SCRIPTS / "aura_advanced_benchmark_runner.py")},
        "scripts/aura_benchmark_suite.py": {"sha256": sha256(SCRIPTS / "aura_benchmark_suite.py"), "git_blob_sha1": git_blob_sha1(SCRIPTS / "aura_benchmark_suite.py")},
        "scripts/aura_industry_benchmark_validation.py": {"sha256": sha256(Path(__file__)), "git_blob_sha1": git_blob_sha1(Path(__file__))},
    }
    result = {
        "schema": "AURA_INDUSTRY_VALIDATION_V1",
        "work_order": "WO-FLEET-AUTONOMOUS-EXECUTE",
        "source_commit_bound_at_run_start": args.source_commit,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PASS" if all(g["status"] == "PASS" for g in gates) else "FAIL",
        "gates_passed": sum(g["status"] == "PASS" for g in gates),
        "gates_total": len(gates),
        "gates": gates,
        "formal": formal,
        "advanced": advanced,
        "fleet": {
            "processes": 25,
            "unique_done_payloads": len(set(payload_indexes)),
            "task_counts": dict(sorted(counts.items())),
            "dispatcher_journal_mode": mode,
            "dispatcher_integrity_check": integrity,
        },
        "source_bindings": sources,
        "qualification": "Repository-defined industry-readiness validation; not third-party certification, external percentile ranking, or hardware-independent guarantee.",
    }
    RESULT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    clean_db(DB_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

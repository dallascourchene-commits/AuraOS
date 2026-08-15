#!/usr/bin/env python3
"""AuraOS signed-trigger global benchmark polling daemon.

Fail-closed properties:
- trusts only a preconfigured Ed25519 public key;
- atomically leases trigger files before execution;
- never invents scores for unavailable external benchmark environments;
- --once provides a bounded execution mode suitable for CI/agent runtimes.

A long-running host can omit --once to poll continuously.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import platform
import resource
import shutil
import socket
import statistics
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

WORK_ORDER = "WO-UNIVERSAL-GLOBAL-BENCHMARK-DAEMON-EXHAUSTIVE"
COORDINATE = "AD:DAEMON:GLOBAL-EXHAUSTIVE-BENCHMARK:UNIVERSAL"

BENCHMARKS = [
    ("Coding & Software Engineering", "SWE-bench Verified", ["docker", "benchmark_harness", "model_adapter"]),
    ("Coding & Software Engineering", "SWE-bench Pro", ["docker", "benchmark_harness", "model_adapter"]),
    ("Coding & Software Engineering", "BigCodeBench", ["benchmark_harness", "dataset", "model_adapter"]),
    ("Coding & Software Engineering", "LiveCodeBench", ["benchmark_harness", "dataset", "model_adapter"]),
    ("Coding & Software Engineering", "Aider Polyglot", ["aider", "benchmark_harness", "model_adapter"]),
    ("Computer & OS Use", "Terminal-Bench 2.0", ["docker", "benchmark_harness", "model_adapter"]),
    ("Computer & OS Use", "OSWorld", ["desktop_vm_or_docker", "benchmark_harness", "model_adapter"]),
    ("Computer & OS Use", "AgentBench (OS/DB/Web)", ["benchmark_harness", "interactive_services", "model_adapter"]),
    ("Computer & OS Use", "AndroidWorld", ["adb", "android_emulator", "benchmark_harness", "model_adapter"]),
    ("Tool Calling & Protocol Efficiency", "BFCL v4", ["benchmark_harness", "dataset", "model_adapter"]),
    ("Tool Calling & Protocol Efficiency", "Toolathlon", ["benchmark_harness", "tool_services", "model_adapter"]),
    ("Tool Calling & Protocol Efficiency", "MCP-Atlas / Tool Use", ["benchmark_harness", "mcp_servers", "model_adapter"]),
    ("Web Navigation & Multi-Step Tasks", "GAIA", ["benchmark_harness", "dataset_or_gated_assets", "browser_or_tools", "model_adapter"]),
    ("Web Navigation & Multi-Step Tasks", "WebArena / WebArena Verified", ["benchmark_harness", "playwright", "webarena_services", "model_adapter"]),
    ("Web Navigation & Multi-Step Tasks", "τ²-Bench", ["benchmark_harness", "domain_simulator", "model_adapter"]),
    ("Web Navigation & Multi-Step Tasks", "BrowseComp", ["benchmark_harness", "browsing_agent", "model_adapter"]),
    ("Reasoning & Architecture Constraints", "ARC-AGI-2", ["benchmark_harness", "dataset", "model_adapter"]),
    ("Reasoning & Architecture Constraints", "ARC-AGI-3", ["benchmark_harness", "interactive_arc_env", "model_adapter"]),
    ("Reasoning & Architecture Constraints", "APEX-Agents", ["benchmark_harness", "professional_workflow_env", "model_adapter"]),
    ("Memory & Context", "LoCoMo", ["benchmark_harness", "dataset", "model_adapter"]),
    ("Memory & Context", "LongMemEval", ["benchmark_harness", "dataset", "model_adapter"]),
]


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def capability_snapshot(repo_root: Path) -> dict[str, Any]:
    env_names = [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
        "GEMINI_API_KEY", "HF_TOKEN", "HUGGINGFACE_HUB_TOKEN",
    ]
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "commands": {
            name: command_exists(name)
            for name in ["docker", "podman", "adb", "emulator", "vmrun", "aider", "playwright", "uv"]
        },
        "credential_presence": {name: bool(os.environ.get(name)) for name in env_names},
        "local_benchmark_dirs": sorted(
            str(p.relative_to(repo_root))
            for p in repo_root.glob("**/*")
            if p.is_dir() and any(token in p.name.lower() for token in (
                "swe-bench", "bigcodebench", "livecodebench", "terminal-bench",
                "osworld", "agentbench", "android_world", "bfcl", "toolathlon",
                "webarena", "tau2", "arc-agi", "locomo", "longmemeval",
            ))
        )[:200],
    }


def _requirement_available(req: str, caps: dict[str, Any]) -> bool:
    commands = caps["commands"]
    local_dirs = caps["local_benchmark_dirs"]
    if req == "docker":
        return commands.get("docker", False) or commands.get("podman", False)
    if req == "desktop_vm_or_docker":
        return commands.get("vmrun", False) or commands.get("docker", False) or commands.get("podman", False)
    if req == "adb":
        return commands.get("adb", False)
    if req == "android_emulator":
        return commands.get("emulator", False)
    if req == "aider":
        return commands.get("aider", False)
    if req == "playwright":
        return commands.get("playwright", False)
    if req == "benchmark_harness":
        return bool(local_dirs)
    if req in {"dataset", "dataset_or_gated_assets"}:
        return bool(local_dirs)
    if req == "model_adapter":
        return any(caps["credential_presence"].values())
    return False


def classify_benchmark(item: tuple[str, str, list[str]], caps: dict[str, Any], worker_id: str) -> dict[str, Any]:
    category, name, requirements = item
    missing = [r for r in requirements if not _requirement_available(r, caps)]
    return {
        "category": category,
        "benchmark": name,
        "worker": worker_id,
        "status": "SOURCE_RESOLVED_ENV_BLOCKED" if missing else "OFFICIAL_ADAPTER_REQUIRED",
        "score": None,
        "missing_requirements": missing,
        "claim_boundary": "No score is minted without the benchmark-specific execution path.",
    }


def udp_loopback_probe(iterations: int = 5000) -> dict[str, Any]:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    addr = server.getsockname()
    stop = threading.Event()

    def echo() -> None:
        server.settimeout(0.2)
        while not stop.is_set():
            try:
                data, peer = server.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            server.sendto(data, peer)

    thread = threading.Thread(target=echo, daemon=True)
    thread.start()
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(1.0)
    payload = b"AURA_GOSSIP_PROBE"
    samples_ns: list[int] = []
    try:
        for _ in range(100):
            client.sendto(payload, addr)
            client.recvfrom(65535)
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            client.sendto(payload, addr)
            got, _ = client.recvfrom(65535)
            t1 = time.perf_counter_ns()
            if got != payload:
                raise RuntimeError("udp echo payload mismatch")
            samples_ns.append(t1 - t0)
    finally:
        client.close()
        stop.set()
        server.close()
        thread.join(timeout=1.0)

    samples_us = sorted(x / 1000.0 for x in samples_ns)
    def pct(p: float) -> float:
        idx = min(len(samples_us) - 1, max(0, round((len(samples_us) - 1) * p)))
        return samples_us[idx]
    p95 = pct(0.95)
    return {
        "surface": "UDP localhost synchronous echo RTT",
        "iterations": len(samples_us),
        "median_us": round(statistics.median(samples_us), 3),
        "p95_us": round(p95, 3),
        "p99_us": round(pct(0.99), 3),
        "threshold_us": 500.0,
        "threshold_result": "PASS" if p95 < 500.0 else "FAIL",
        "boundary": "Loopback round-trip latency only; not a remote, WAN, or multi-node mesh proof.",
    }


def rss_probe() -> dict[str, Any]:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    mib = raw / (1024.0 if platform.system() != "Darwin" else 1024.0**2)
    return {
        "surface": "signed-trigger polling daemon process peak RSS",
        "peak_rss_mib": round(mib, 3),
        "threshold_mib": 95.0,
        "threshold_result": "PASS" if mib < 95.0 else "FAIL",
        "boundary": "Process high-water mark on this host; not a complete mobile-device system image measurement.",
    }


def l0_compression_probe(repo_root: Path) -> dict[str, Any]:
    patterns = ("l0 symbolic", "symbolic tensor", "tensor compression", "l0_tensor", "l0tensor")
    matches: list[str] = []
    for p in repo_root.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.suffix.lower() not in {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml"}:
            continue
        try:
            if p.stat().st_size > 2_000_000:
                continue
            text = p.read_text("utf-8", errors="ignore").lower()
        except OSError:
            continue
        if any(term in text for term in patterns):
            matches.append(str(p.relative_to(repo_root)))
    # Do not count this daemon's own specification text as an implementation.
    matches = [m for m in matches if m != "scripts/aura_global_benchmark_daemon.py"]
    return {
        "surface": "L0 symbolic tensor payload compression",
        "required_reduction_percent": 94.0,
        "measured_reduction_percent": None,
        "threshold_result": "UNVERIFIED_SOURCE_GAP",
        "source_candidates": sorted(set(matches)),
        "boundary": "No source-bound executable L0 symbolic-tensor compressor was found; generic serialization/compression is not substituted.",
    }


def verify_trigger(trigger: dict[str, Any], trusted_key: Ed25519PublicKey) -> dict[str, Any]:
    if set(trigger) != {"payload", "signature_b64"}:
        raise ValueError("trigger_schema_mismatch")
    payload = trigger["payload"]
    if payload.get("work_order") != WORK_ORDER:
        raise ValueError("work_order_mismatch")
    if payload.get("coordinate") != COORDINATE:
        raise ValueError("coordinate_mismatch")
    signature = base64.b64decode(trigger["signature_b64"], validate=True)
    trusted_key.verify(signature, canonical_json(payload))
    return payload


def execute(repo_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    caps = capability_snapshot(repo_root)
    workers = [f"J{i:02d}" for i in range(1, 26)]
    rows: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=25, thread_name_prefix="AURA-BENCH") as pool:
        futures = [
            pool.submit(classify_benchmark, item, caps, workers[idx % len(workers)])
            for idx, item in enumerate(BENCHMARKS)
        ]
        for future in futures:
            rows.append(future.result())
    rows.sort(key=lambda x: (x["category"], x["benchmark"]))

    udp = udp_loopback_probe()
    l0 = l0_compression_probe(repo_root)
    rss = rss_probe()
    ended = time.time()
    return {
        "schema": "AuraGlobalBenchmarkTelemetryV1",
        "work_order": WORK_ORDER,
        "coordinate": COORDINATE,
        "source_commit": payload.get("source_commit"),
        "trigger_nonce": payload.get("nonce"),
        "workers_available": 25,
        "workers_used": len(rows),
        "started_unix": started,
        "ended_unix": ended,
        "duration_seconds": round(ended - started, 6),
        "capabilities": caps,
        "benchmark_taxonomy": rows,
        "substrate": {
            "udp": udp,
            "rss": rss,
            "l0_symbolic_tensor_compression": l0,
        },
        "summary": {
            "taxonomy_entries": len(rows),
            "official_scores_minted": sum(1 for r in rows if r["score"] is not None),
            "blocked_or_adapter_required": sum(1 for r in rows if r["score"] is None),
            "substrate_all_confirmed": all(x.get("threshold_result") == "PASS" for x in (udp, rss, l0)),
        },
    }


def poll_once(repo_root: Path, inbox: Path, outbox: Path, trusted_key_path: Path) -> int:
    key = serialization.load_pem_public_key(trusted_key_path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("trusted_key_is_not_ed25519")
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    processed = inbox / "processed"
    rejected = inbox / "rejected"
    processed.mkdir(exist_ok=True)
    rejected.mkdir(exist_ok=True)

    candidates = sorted(inbox.glob("*.trigger.json"))
    if not candidates:
        return 2
    source = candidates[0]
    lease = inbox / f".leased.{source.name}.{uuid.uuid4().hex}"
    os.replace(source, lease)
    try:
        trigger = json.loads(lease.read_text("utf-8"))
        payload = verify_trigger(trigger, key)
        telemetry = execute(repo_root, payload)
        out_path = outbox / f"{WORK_ORDER}.telemetry.json"
        out_path.write_bytes(canonical_json(telemetry) + b"\n")
        os.replace(lease, processed / source.name)
        print(json.dumps({
            "status": "EXECUTED",
            "telemetry": str(out_path),
            "telemetry_sha256": sha256_bytes(out_path.read_bytes()),
        }, sort_keys=True))
        return 0
    except Exception as exc:
        target = rejected / source.name
        if lease.exists():
            os.replace(lease, target)
        print(json.dumps({
            "status": "REJECTED",
            "error": type(exc).__name__,
            "detail": str(exc),
        }, sort_keys=True))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--inbox", default="aura_workspace/inbox")
    parser.add_argument("--outbox", default="aura_workspace/outbox")
    parser.add_argument("--trusted-key", required=True)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    inbox = (root / args.inbox).resolve()
    outbox = (root / args.outbox).resolve()
    key = Path(args.trusted_key).resolve()
    if args.once:
        return poll_once(root, inbox, outbox, key)
    while True:
        rc = poll_once(root, inbox, outbox, key)
        if rc == 1:
            return rc
        time.sleep(max(0.05, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""AuraOS bounded local worker daemon.

The daemon polls the local dispatcher and executes only an explicit allowlist.
No arbitrary shell command task is supported.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from aura_task_dispatcher import TaskDispatcher


def execute_task(task: dict, repo_root: Path) -> dict:
    kind = task["kind"]
    payload = task.get("payload") or {}

    if kind == "noop":
        return {"ok": True, "kind": kind, "echo": payload}

    if kind == "advanced_benchmark":
        runner = repo_root / "scripts" / "aura_advanced_benchmark_runner.py"
        proc = subprocess.run(
            [sys.executable, str(runner)],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=120,
        )
        return {
            "ok": proc.returncode == 0,
            "kind": kind,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-8000:],
        }

    return {"ok": False, "kind": kind, "error": "unsupported_task_kind"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="aura_workspace/dispatcher.db")
    parser.add_argument("--worker-id", default="J01")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--lease-seconds", type=float, default=120.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    dispatcher = TaskDispatcher(repo_root / args.db)

    while True:
        task = dispatcher.claim(args.worker_id, args.lease_seconds)
        if task is None:
            if args.once:
                return 0
            time.sleep(max(0.05, args.poll_seconds))
            continue

        try:
            result = execute_task(task, repo_root)
        except Exception as exc:
            result = {"ok": False, "error": type(exc).__name__, "detail": str(exc)}
        dispatcher.finish(
            task["task_id"],
            args.worker_id,
            ok=bool(result.get("ok")),
            result=result,
        )
        print(json.dumps({"task_id": task["task_id"], **result}, sort_keys=True))
        if args.once:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

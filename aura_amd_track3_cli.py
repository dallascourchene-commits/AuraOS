"""CLI and tiny status server for the AMD Track 3 Crucible demo."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import time

from aura_amd_track3_worker import FixtureProvider, OpenAICompatibleProvider, load_tasks, run_task

DEFAULT_TASKS = ".aura/amd_track3_demo_tasks.json"
DEFAULT_CRYSTALS = ".aura/runtime/amd_track3/verified_crystals.jsonl"


def _provider(args):
    if args.provider == "fixture":
        return FixtureProvider()
    return OpenAICompatibleProvider(
        endpoint=args.endpoint or os.environ.get("AURA_TRACK3_ENDPOINT", "http://127.0.0.1:8000/v1"),
        model=args.model or os.environ.get("AURA_TRACK3_MODEL", "google/gemma-3-4b-it"),
        api_key=os.environ.get("AURA_TRACK3_API_KEY", ""),
    )


def _rows(path: str) -> list[dict]:
    source = Path(path)
    if not source.exists():
        return []
    return [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_cycle(args) -> dict:
    provider = _provider(args)
    tasks = load_tasks(args.tasks)
    results = [
        run_task(
            task=task,
            provider=provider,
            repo_root=args.repo_root,
            crystal_path=args.crystals,
            amd_backend=args.amd_backend,
        )
        for task in tasks
    ]
    return {
        "ok": all(item.get("ok") for item in results),
        "status": "CRUCIBLE_CYCLE_COMPLETED",
        "provider": provider.name,
        "model": provider.model,
        "amd_backend": args.amd_backend,
        "task_count": len(tasks),
        "verified_count": sum(1 for item in results if item.get("ok")),
        "results": results,
        "training_command": f"python aura_amd_track3_train.py --crystals {args.crystals}",
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def status(args) -> dict:
    rows = _rows(args.crystals)
    return {
        "ok": True,
        "status": "READY",
        "track": "AMD Hackathon Act II Track 3",
        "amd_backend": args.amd_backend,
        "crystal_count": len(rows),
        "latest_crystal": rows[-1] if rows else None,
        "main_code_path": "aura_amd_track3_cli.py -> aura_amd_track3_worker.py -> verified_crystals.jsonl",
        "c3_authority_preserved": True,
    }


def serve(args) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            payload = status(args)
            body = json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *values):
            return

    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aura AMD Track 3 operational Crucible demo")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--crystals", default=DEFAULT_CRYSTALS)
    parser.add_argument("--amd-backend", default=os.environ.get("AURA_AMD_BACKEND", "AMD ROCm / approved compute"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run-once", "run-loop"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--provider", choices=("fixture", "openai-compatible"), default="fixture")
        cmd.add_argument("--endpoint", default="")
        cmd.add_argument("--model", default="")
        if name == "run-loop":
            cmd.add_argument("--interval-seconds", type=int, default=60)
            cmd.add_argument("--cycles", type=int, default=0, help="0 means continue until interrupted")
    sub.add_parser("status")
    server = sub.add_parser("serve")
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=8080)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        result = status(args)
    elif args.command == "serve":
        serve(args)
        return 0
    elif args.command == "run-once":
        result = run_cycle(args)
    else:
        completed = 0
        result = {"ok": True, "status": "STOPPED"}
        while args.cycles == 0 or completed < args.cycles:
            try:
                result = run_cycle(args)
            except Exception as exc:
                result = {
                    "ok": False,
                    "status": "CYCLE_FAILED",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "cycle": completed + 1,
                }
            print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
            completed += 1
            if args.cycles == 0 or completed < args.cycles:
                time.sleep(max(1, args.interval_seconds))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

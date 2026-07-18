"""Command-line interface for Coding Waboose V1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from aura_coding_waboose import CodingWaboose


def _load_json(value: str) -> Any:
    path = Path(value)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Coding Waboose, Aura's graph-guided diagnostic code-review organ."
    )
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Compile a review contract and agent packet")
    prepare.add_argument("--request", required=True, help="JSON object or path to JSON file")

    run = sub.add_parser("run", help="Run deterministic scan and finalize without agent findings")
    run.add_argument("--request", required=True, help="JSON object or path to JSON file")

    packet = sub.add_parser("agent-packet", help="Emit a bounded packet for a coding agent")
    packet.add_argument("--review-id", required=True)
    packet.add_argument("--include-source", action="store_true")
    packet.add_argument("--max-files", type=int, default=24)
    packet.add_argument("--max-lines-per-file", type=int, default=120)

    submit = sub.add_parser("submit-findings", help="Submit structured coding-agent findings")
    submit.add_argument("--review-id", required=True)
    submit.add_argument("--findings", required=True, help="JSON array or path to JSON file")
    submit.add_argument("--agent-name", default="external_agent")

    finalize = sub.add_parser("finalize", help="Rank findings and compile Forge repair requests")
    finalize.add_argument("--review-id", required=True)

    status = sub.add_parser("status", help="Show in-process review status")
    status.add_argument("--review-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    arena = CodingWaboose(args.repo_root)

    try:
        if args.command == "prepare":
            result = arena.prepare(_load_json(args.request))
        elif args.command == "run":
            result = arena.run_once(_load_json(args.request))
        elif args.command == "agent-packet":
            result = arena.agent_packet(
                args.review_id,
                include_source=args.include_source,
                max_files=args.max_files,
                max_lines_per_file=args.max_lines_per_file,
            )
        elif args.command == "submit-findings":
            result = arena.submit_findings(
                args.review_id,
                _load_json(args.findings),
                agent_name=args.agent_name,
            )
        elif args.command == "finalize":
            result = arena.finalize(args.review_id)
        else:
            result = arena.status(args.review_id)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "ok": False,
            "version": "AURA_CODING_WABOOSE_V1",
            "error": str(exc),
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

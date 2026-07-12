"""CLI for the proposal-only Aura Arena Crucible."""
from __future__ import annotations

import argparse
import json
from typing import Any

from aura_arena_crucible import ArenaCrucibleService
from aura_crucible_types import CruciblePolicy


def _json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value or "{}")
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("policy must be a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aura Arena Crucible — proposal-only experience mining")
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show pause state, run count, and proposal count")
    pause = sub.add_parser("pause", help="Persistently pause future Crucible cycles")
    pause.add_argument("--reason", default="operator_pause")
    sub.add_parser("resume", help="Resume future Crucible cycles")

    run_once = sub.add_parser("run-once", help="Run one bounded read-only mining cycle")
    run_once.add_argument("--arena-id", default="")
    run_once.add_argument("--experience-limit", type=int, default=1000)
    run_once.add_argument("--policy", type=_json_object, default={})

    service = sub.add_parser("service", help="Run cooperative foreground cycles")
    service.add_argument("--arena-id", default="")
    service.add_argument("--interval", type=float, default=60.0)
    service.add_argument("--max-cycles", type=int, default=None)
    service.add_argument("--policy", type=_json_object, default={})

    proposals = sub.add_parser("proposals", help="List stored CRYSTALLIZATION_PROPOSED packets")
    proposals.add_argument("--arena-id", default="")
    proposals.add_argument("--limit", type=int, default=50)
    proposal = sub.add_parser("proposal", help="Read one proposal by ID")
    proposal.add_argument("proposal_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = ArenaCrucibleService(args.repo_root)
    try:
        if args.command == "status":
            result = service.status()
        elif args.command == "pause":
            result = service.pause(args.reason)
        elif args.command == "resume":
            result = service.resume()
        elif args.command == "run-once":
            result = service.run_once(arena_id=args.arena_id, policy=CruciblePolicy.from_dict(args.policy), experience_limit=args.experience_limit)
        elif args.command == "service":
            result = service.run_service(interval_seconds=args.interval, max_cycles=args.max_cycles, arena_id=args.arena_id, policy=CruciblePolicy.from_dict(args.policy))
        elif args.command == "proposals":
            rows = service.store.list_proposals(arena_id=args.arena_id, limit=args.limit)
            result = {"ok": True, "proposals": rows, "count": len(rows), "automatic_grammar_promotion": False}
        else:
            row = service.store.get_proposal(args.proposal_id)
            result = {"ok": bool(row), "proposal": row, "reason": "" if row else "proposal_not_found", "automatic_grammar_promotion": False}
    finally:
        service.close()
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

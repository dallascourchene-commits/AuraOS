"""Command-line control surface for Aura temporal persistence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY


def _json_mapping(text: str | None, name: str) -> dict[str, Any]:
    if not text:
        return {}
    path = Path(text)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{name} must be a readable JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{name} must contain a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aura-persistence",
        description="Inspect and assess Aura checkpoint state without applying it.",
    )
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify-registry")
    verify.set_defaults(handler="verify")

    listing = sub.add_parser("list")
    listing.add_argument("--arena-id")
    listing.add_argument("--session-id")
    listing.add_argument("--limit", type=int, default=100)
    listing.set_defaults(handler="list")

    show = sub.add_parser("show")
    show.add_argument("--checkpoint-id", required=True)
    show.add_argument("--include-payload", action="store_true")
    show.set_defaults(handler="show")

    assess = sub.add_parser("assess")
    assess.add_argument("--checkpoint-id", required=True)
    assess.add_argument("--repo-head", required=True)
    assess.add_argument("--invariants-json")
    assess.add_argument("--remaining-context-tokens", type=int, default=0)
    assess.add_argument("--surgeon-context-limit", type=int, default=0)
    assess.set_defaults(handler="assess")

    fork = sub.add_parser("fork")
    fork.add_argument("--checkpoint-id", required=True)
    fork.add_argument("--branch-name", required=True)
    fork.add_argument("--repo-head")
    fork.set_defaults(handler="fork")

    handoff = sub.add_parser("handoff")
    handoff.add_argument("--checkpoint-id", required=True)
    handoff.add_argument("--target-arena-id", required=True)
    handoff.add_argument("--repo-head", required=True)
    handoff.add_argument("--invariants-json")
    handoff.set_defaults(handler="handoff")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    coordinator = ArenaPersistenceCoordinator(args.repo_root)
    if args.handler == "verify":
        return coordinator.verify_registry()
    if args.handler == "list":
        return coordinator.list_checkpoints(
            arena_id=args.arena_id,
            session_id=args.session_id,
            limit=args.limit,
        )
    if args.handler == "show":
        checkpoint = coordinator.registry.load_checkpoint(args.checkpoint_id)
        if args.include_payload:
            result = checkpoint.to_dict()
            result["warning"] = "Payload inspection does not apply or authorize restored state."
            return result
        return coordinator.observatory_projection(args.checkpoint_id)
    if args.handler == "assess":
        return coordinator.assess(
            args.checkpoint_id,
            current_repo_head=args.repo_head,
            current_invariant_values=_json_mapping(args.invariants_json, "invariants-json"),
            remaining_context_tokens=args.remaining_context_tokens,
            surgeon_context_limit=args.surgeon_context_limit,
        )
    if args.handler == "fork":
        return coordinator.registry.fork_checkpoint(
            args.checkpoint_id,
            branch_name=args.branch_name,
            repo_head=args.repo_head,
        )
    if args.handler == "handoff":
        return coordinator.handoff_packet(
            args.checkpoint_id,
            target_arena_id=args.target_arena_id,
            current_repo_head=args.repo_head,
            current_invariant_values=_json_mapping(args.invariants_json, "invariants-json"),
        )
    raise SystemExit("unsupported command")


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except (KeyError, ValueError) as exc:
        result = {
            "ok": False,
            "error": str(exc),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())

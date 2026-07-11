"""Standalone CLI for Phase-A Arena guarded-WFST inspection and validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_arena_wfst_runtime import ArenaWFSTRuntime


def _json_arg(value: str) -> dict[str, Any]:
    if not value:
        return {}
    path = Path(value)
    text = path.read_text(encoding="utf-8") if path.exists() else value
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("JSON value must be an object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aura Arena guarded-WFST Phase A")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_parser = sub.add_parser("compile", help="validate and compile an Arena grammar manifest")
    compile_parser.add_argument("--manifest", required=True)

    project = sub.add_parser("project-human", help="project Human Agent transitions for a state")
    project.add_argument("--repo-root", default=".")
    project.add_argument("--state", required=True, choices=["FRAME", "GROUND", "PLAN", "ACT", "PROVE", "DECIDE"])
    project.add_argument("--input", default="")
    project.add_argument("--evidence-json", default="{}")
    project.add_argument("--context-json", default="{}")
    project.add_argument("--policy-json", default="{}")

    ledger = sub.add_parser("experience-status", help="show the local Arena experience ledger status")
    ledger.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "compile":
        result = load_and_compile_arena_grammar(args.manifest)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True, default=str))
        return 0 if result.ok else 2

    if args.command == "project-human":
        root = Path(args.repo_root).resolve()
        runtime = ArenaWFSTRuntime(repo_root=root)
        reports = [
            runtime.register_manifest(root / ".aura" / "arena_routes" / "human_agent.v1.json"),
            runtime.register_manifest(root / ".aura" / "arena_routes" / "meta.v1.json"),
        ]
        if not all(item.get("ok") for item in reports):
            print(json.dumps({"ok": False, "registration": reports}, indent=2, sort_keys=True))
            return 2
        result = runtime.route(
            arena_id="human_agent",
            current_state=args.state,
            input_text=args.input,
            evidence=_json_arg(args.evidence_json),
            context=_json_arg(args.context_json),
            policy=_json_arg(args.policy_json),
        )
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0 if result.get("ok") else 2

    if args.command == "experience-status":
        with ArenaExperienceLedger(args.repo_root) as ledger:
            print(json.dumps(ledger.status(), indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI for grounded CodeRabbit-to-Coding-Waboose learning."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from aura_waboose_learning import CodeRabbitLearningStore, DEFAULT_LEARNING_ROOT


def _load_json(value: str) -> Any:
    path = Path(value)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ground successful CodeRabbit findings against the reviewed head, "
            "then route them through Aura Connectome, DREAM-lite, and QDKT."
        )
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--learning-root",
        default=str(DEFAULT_LEARNING_ROOT),
        help="Persistent learning directory; defaults outside the repository.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="Ingest one successful CodeRabbit review payload")
    ingest.add_argument("--review", required=True, help="JSON object or JSON file")
    sub.add_parser("summary", help="Show grounded lesson and QDKT crystal counts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = CodeRabbitLearningStore(
            args.repo_root,
            learning_root=args.learning_root,
        )
        if args.command == "ingest":
            payload = _load_json(args.review)
            if not isinstance(payload, dict):
                raise ValueError("review payload must be an object")
            result = store.ingest_review(payload)
        else:
            result = store.summary()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "ok": False,
            "error": str(exc),
            "teacher_is_patch_authority": False,
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
        }
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

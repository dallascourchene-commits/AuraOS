"""Command-line entry point for Aura external discovery adapters."""
from __future__ import annotations

import argparse
import os
import sys

from tools.aura_external_discovery import DiscoveryError, discover, emit_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AuraOS source-bound external knowledge discovery")
    parser.add_argument("--provider", required=True, choices=(
        "ARXIV", "GITHUB", "HUGGING_FACE", "OPENALEX", "CROSSREF", "SEMANTIC_SCHOLAR", "GOOGLE_SCHOLAR"
    ))
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--token-env", default=None, help="Environment variable containing an optional provider token")
    parser.add_argument("--mailto", default=None, help="Optional Crossref polite-pool contact address")
    parser.add_argument("--repo-type", choices=("model", "dataset", "space"), default="model")
    parser.add_argument("--output", default=None, help="Optional UTF-8 JSON output path; stdout is always emitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit <= 0 or args.limit > 100:
        raise SystemExit("--limit must be between 1 and 100")
    token = os.environ.get(args.token_env) if args.token_env else None
    try:
        rows = discover(
            args.provider,
            args.query,
            limit=args.limit,
            token=token,
            mailto=args.mailto,
            repo_type=args.repo_type,
        )
    except DiscoveryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rendered = emit_json(rows)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.write("\n")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

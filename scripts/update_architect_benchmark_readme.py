"""Copy the committed benchmark README into a reproducible workflow artifact.

The benchmark is now documented directly in README.md and in
``docs/AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md``. CI uses this helper to retain
an exact README snapshot beside the generated benchmark evidence; it never writes
to a branch or changes source.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark-output/README.updated.md"),
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    readme = root / "README.md"
    target = args.output if args.output.is_absolute() else root / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(readme.read_text(encoding="utf-8"), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

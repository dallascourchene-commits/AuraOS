"""CLI for typed Coding Waboose review lessons and Crucible replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

from aura_coding_waboose_review_lessons import (
    DEFAULT_REGISTRY_PATH,
    ReviewLessonEngine,
    ReviewLessonError,
)


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source_path(repo_root: str, value: str) -> tuple[str, Path]:
    text = str(value or "").strip()
    posix = PurePosixPath(text)
    if (
        not text
        or posix.is_absolute()
        or "\\" in text
        or "//" in text
        or any(part in {"", ".", ".."} for part in posix.parts)
        or posix.as_posix() != text
    ):
        raise ReviewLessonError("scan-source file must be a canonical repository-relative path")
    root = Path(repo_root).resolve()
    path = (root / text).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ReviewLessonError("scan-source file escapes the repository root") from exc
    return text, path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coding Waboose typed review lessons")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary")

    replay = sub.add_parser("crucible")
    replay.add_argument("--detector", action="append", default=[])

    normalize = sub.add_parser("normalize")
    normalize.add_argument("payload")
    normalize.add_argument("--current-head", default="")
    normalize.add_argument("--store", action="store_true")

    detect = sub.add_parser("detect")
    detect.add_argument("detector_id")
    detect.add_argument("candidate")

    scan = sub.add_parser("scan-source")
    scan.add_argument("file")

    args = parser.parse_args(argv)
    try:
        engine = ReviewLessonEngine(
            args.repo_root,
            registry_path=args.registry,
        )
        if args.command == "summary":
            result = engine.summary()
        elif args.command == "crucible":
            result = engine.crucible(detector_ids=args.detector)
        elif args.command == "normalize":
            payload = _load_json(args.payload)
            result = (
                engine.ingest_review(payload, current_head=args.current_head)
                if args.store
                else engine.normalize_review(payload, current_head=args.current_head)
            )
        elif args.command == "detect":
            result = engine.detector(args.detector_id, _load_json(args.candidate))
        else:
            file, path = _source_path(args.repo_root, args.file)
            result = engine.scan_source(file=file, source=path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ReviewLessonError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

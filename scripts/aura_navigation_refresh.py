#!/usr/bin/env python3
"""Canonical Aura navigation refresh: CODEMAP first, source anchors second.

SOURCE_ANCHORS.md is a generated projection over CODEMAP. Normal navigation
refreshes source cards and symbol spans against Aura's already verified deep
topology; it does not silently recompile that separate generated graph.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_codebase_navigator import (
    DEFAULT_INDEX_PATH,
    DEFAULT_MARKDOWN_PATH,
    DEFAULT_TOPOLOGY_PATH,
    _iter_repo_files,
    refresh_codemap_for_paths,
)
from scripts.aura_source_anchor_map import DEFAULT_MANIFEST, DEFAULT_OUTPUT, generate


def _write_anchors(root: Path) -> Path:
    output = root / DEFAULT_OUTPUT
    rendered = generate(
        root=root,
        codemap_path=DEFAULT_INDEX_PATH,
        manifest_path=DEFAULT_MANIFEST,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    return output


def _is_generated_anchor_path(root: Path, value: str | Path) -> bool:
    """Return True when *value* resolves to the generated anchor projection."""
    candidate = Path(value)
    candidate = candidate if candidate.is_absolute() else root / candidate
    try:
        return candidate.resolve() == (root / DEFAULT_OUTPUT).resolve()
    except OSError:
        return False


def _source_changes_only(root: Path, changed: list[str]) -> list[str]:
    """Remove SOURCE_ANCHORS.md from caller-provided incremental source paths."""
    return [value for value in changed if not _is_generated_anchor_path(root, value)]


def _full_source_refresh_paths(root: Path) -> list[str]:
    """Return current + previously indexed paths so additions/deletions converge."""
    index_path = root / DEFAULT_INDEX_PATH
    if not index_path.exists():
        raise FileNotFoundError(
            f"Missing {index_path}; Aura source refresh requires the committed CODEMAP baseline"
        )
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("CODEMAP baseline must contain a JSON object")
    previous = {
        str(card.get("path") or "")
        for card in payload.get("files", [])
        if isinstance(card, dict) and str(card.get("path") or "")
    }
    current = {path.relative_to(root).as_posix() for path in _iter_repo_files(root)}
    return sorted(previous | current)


def _full_navigation_refresh(root: Path, *, include_topology: bool) -> Path:
    """Refresh every source card while preserving the verified topology plane.

    The previous source-anchor projection is restored if CODEMAP or anchor
    generation fails, so failed navigation refresh cannot silently delete the
    last known human/AI orientation aid.
    """
    anchor_path = root / DEFAULT_OUTPUT
    previous_anchor: bytes | None = anchor_path.read_bytes() if anchor_path.exists() else None
    try:
        refresh_codemap_for_paths(
            _full_source_refresh_paths(root),
            root=root,
            index_path=DEFAULT_INDEX_PATH,
            markdown_path=DEFAULT_MARKDOWN_PATH,
            include_topology=include_topology,
            topology_path=DEFAULT_TOPOLOGY_PATH,
            refresh_topology=False,
        )
        return _write_anchors(root)
    except BaseException:
        if anchor_path.exists():
            anchor_path.unlink()
        if previous_anchor is not None:
            anchor_path.parent.mkdir(parents=True, exist_ok=True)
            anchor_path.write_bytes(previous_anchor)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh Aura CODEMAP source cards and generated source anchors as one transaction."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--refresh",
        nargs="*",
        default=None,
        help="changed/deleted source paths for incremental refresh",
    )
    parser.add_argument("--no-topology", action="store_true")
    parser.add_argument(
        "--refresh-topology",
        action="store_true",
        help="fail closed: deep-topology recompilation is a separate owner operation",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.refresh_topology:
        raise SystemExit(
            "Deep topology has a separate owner. Recompile it explicitly with "
            "aura_topological_scanner.compile_topology_map(deep=True), then rerun "
            "this source-navigation refresh without --refresh-topology."
        )

    index = root / DEFAULT_INDEX_PATH
    if not index.exists():
        raise SystemExit(f"Missing {index}; restore/generate the canonical CODEMAP baseline first")

    if args.refresh is not None:
        changed = _source_changes_only(root, list(args.refresh))
        if changed:
            refresh_codemap_for_paths(
                changed,
                root=root,
                index_path=DEFAULT_INDEX_PATH,
                markdown_path=DEFAULT_MARKDOWN_PATH,
                include_topology=not args.no_topology,
                topology_path=DEFAULT_TOPOLOGY_PATH,
                refresh_topology=False,
            )
        output = _write_anchors(root)
    else:
        output = _full_navigation_refresh(root, include_topology=not args.no_topology)

    print(f"[+] CODEMAP source cards and source anchors synchronized; anchors={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

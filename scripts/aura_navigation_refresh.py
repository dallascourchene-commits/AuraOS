#!/usr/bin/env python3
"""Canonical Aura navigation refresh: CODEMAP first, source anchors second.

SOURCE_ANCHORS.md is a generated projection over CODEMAP. A full CODEMAP scan
must therefore hide that projection while scanning, otherwise navigation would
index its own derived output. Incremental refresh similarly ignores the anchor
output if a caller includes it in the changed-path set.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_codebase_navigator import (
    DEFAULT_INDEX_PATH,
    DEFAULT_MARKDOWN_PATH,
    DEFAULT_TOPOLOGY_PATH,
    build_navigation_system,
    refresh_codemap_for_paths,
    write_navigation_artifacts,
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


def _full_navigation_refresh(
    root: Path,
    *,
    include_topology: bool,
    refresh_topology: bool,
) -> Path:
    """Rebuild navigation without allowing SOURCE_ANCHORS to index itself.

    The previous projection is restored if CODEMAP or anchor generation fails,
    so a failed refresh does not silently delete the last known navigation aid.
    """
    anchor_path = root / DEFAULT_OUTPUT
    previous: bytes | None = None
    existed = anchor_path.exists()
    if existed:
        previous = anchor_path.read_bytes()
        anchor_path.unlink()
    try:
        payload = build_navigation_system(
            root,
            include_topology=include_topology,
            topology_path=DEFAULT_TOPOLOGY_PATH,
            refresh_topology=refresh_topology,
        )
        write_navigation_artifacts(
            payload,
            root / DEFAULT_INDEX_PATH,
            root / DEFAULT_MARKDOWN_PATH,
        )
        return _write_anchors(root)
    except BaseException:
        if anchor_path.exists():
            anchor_path.unlink()
        if existed and previous is not None:
            anchor_path.parent.mkdir(parents=True, exist_ok=True)
            anchor_path.write_bytes(previous)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh Aura CODEMAP and its generated source-anchor projection as one transaction."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--refresh",
        nargs="*",
        default=None,
        help="changed/deleted source paths for incremental refresh",
    )
    parser.add_argument("--no-topology", action="store_true")
    parser.add_argument("--refresh-topology", action="store_true")
    parser.add_argument("--reuse-topology-json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.refresh is not None:
        index = root / DEFAULT_INDEX_PATH
        if not index.exists():
            raise SystemExit(f"Missing {index}; run a full navigation refresh first")
        changed = _source_changes_only(root, list(args.refresh))
        if changed:
            refresh_codemap_for_paths(
                changed,
                root=root,
                index_path=DEFAULT_INDEX_PATH,
                markdown_path=DEFAULT_MARKDOWN_PATH,
                include_topology=not args.no_topology,
                topology_path=DEFAULT_TOPOLOGY_PATH,
                refresh_topology=args.refresh_topology,
            )
        output = _write_anchors(root)
    else:
        output = _full_navigation_refresh(
            root,
            include_topology=not args.no_topology,
            refresh_topology=not args.reuse_topology_json,
        )
    print(f"[+] CODEMAP and source anchors synchronized; anchors={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

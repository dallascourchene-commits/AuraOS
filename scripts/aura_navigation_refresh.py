#!/usr/bin/env python3
"""Canonical Aura navigation refresh: CODEMAP first, source anchors second."""
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
    rendered = generate(root=root, codemap_path=DEFAULT_INDEX_PATH, manifest_path=DEFAULT_MANIFEST)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh Aura CODEMAP and its generated source-anchor projection as one transaction."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--refresh", nargs="*", default=None, help="changed/deleted paths for incremental refresh")
    parser.add_argument("--no-topology", action="store_true")
    parser.add_argument("--refresh-topology", action="store_true")
    parser.add_argument("--reuse-topology-json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.refresh is not None:
        index = root / DEFAULT_INDEX_PATH
        if not index.exists():
            raise SystemExit(f"Missing {index}; run a full navigation refresh first")
        refresh_codemap_for_paths(
            args.refresh,
            root=root,
            index_path=DEFAULT_INDEX_PATH,
            markdown_path=DEFAULT_MARKDOWN_PATH,
            include_topology=not args.no_topology,
            topology_path=DEFAULT_TOPOLOGY_PATH,
            refresh_topology=args.refresh_topology,
        )
    else:
        payload = build_navigation_system(
            root,
            include_topology=not args.no_topology,
            topology_path=DEFAULT_TOPOLOGY_PATH,
            refresh_topology=not args.reuse_topology_json,
        )
        write_navigation_artifacts(payload, root / DEFAULT_INDEX_PATH, root / DEFAULT_MARKDOWN_PATH)
    output = _write_anchors(root)
    print(f"[+] CODEMAP and source anchors synchronized; anchors={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

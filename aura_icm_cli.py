"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9e2-[Q-SYS:ICM_CLI]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Human-Readable Control Surface)
DEPENDENCIES: __future__, argparse, json, pathlib, sys, aura_icm_workspace, aura_liquid_planning_arena, aura_qdkt
FUNCTIONS: main, export_cli, import_cli, list_cli
SYNOPSIS: Command-line interface for ICM workspace export and import. Provides human-readable filesystem control surface operations for Arena runs without replacing live routing or multi-agent orchestration.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _resolve_path(text: str) -> Path:
    return Path(text).expanduser().resolve()


def export_cli(args: argparse.Namespace) -> int:
    """Export an Arena transaction JSON into an ICM workspace."""
    from aura_icm_workspace import (
        ICMStageDescriptor,
        export_arena_transaction,
    )

    txn_path = _resolve_path(args.txn)
    if not txn_path.exists():
        print(f"[-] Transaction file not found: {txn_path}", file=sys.stderr)
        return 1

    txn = json.loads(txn_path.read_text(encoding="utf-8"))

    stages = None
    if args.stages:
        stages = [ICMStageDescriptor(**s) for s in json.loads(Path(args.stages).read_text(encoding="utf-8"))]

    qdkt = None
    if args.qdkt:
        from aura_qdkt import UnifiedQDKT
        qdkt = UnifiedQDKT()

    dream_candidates = None
    if args.dream_candidates:
        from aura_dream_retrieval import DreamCandidate
        dream_candidates = [
            DreamCandidate.from_any(c) for c in json.loads(Path(args.dream_candidates).read_text(encoding="utf-8"))
        ]

    ref = export_arena_transaction(
        txn,
        args.workspace_root,
        domain=args.domain or txn.get("domain", "generic"),
        arena_id=args.arena_id or txn.get("arena_id", "unknown"),
        arena_version=args.arena_version or txn.get("arena_version", "unknown"),
        stages=stages,
        qdkt=qdkt,
        dream_candidates=dream_candidates,
        dream_query=args.dream_query or "",
        dream_target_type=args.dream_target_type or "",
    )
    print(f"[+] ICM workspace exported: {ref.workspace_path}")
    print(f"    txn_id={ref.txn_id} domain={ref.domain} arena_id={ref.arena_id}")
    return 0


def import_cli(args: argparse.Namespace) -> int:
    """Import an ICM workspace and print its JSON representation."""
    from aura_icm_workspace import import_workspace

    ws_path = _resolve_path(args.workspace)
    if not ws_path.is_dir():
        print(f"[-] Not a directory: {ws_path}", file=sys.stderr)
        return 1

    exported = import_workspace(ws_path)
    payload = exported.to_dict()
    if args.out:
        out_path = _resolve_path(args.out)
        out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(f"[+] Imported workspace written to: {out_path}")
    else:
        print(json.dumps(payload, indent=2, default=str))
    return 0


def list_cli(args: argparse.Namespace) -> int:
    """List ICM workspaces under a root directory."""
    root = _resolve_path(args.workspace_root)
    if not root.exists():
        print(f"[-] Root not found: {root}", file=sys.stderr)
        return 1

    found = sorted(p for p in root.iterdir() if p.is_dir() and p.name[:3].isdigit())
    if not found:
        print("[-] No numbered workspaces found.")
        return 0

    for ws in found:
        meta_path = ws / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        print(
            f"{ws.name:<32} "
            f"domain={meta.get('domain', '?'):<12} "
            f"arena_id={meta.get('arena_id', '?'):<20} "
            f"stages={meta.get('stage_count', 0)}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aura ICM workspace CLI (audit/edit/review control surface)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # export
    p_export = sub.add_parser("export", help="Export an Arena transaction to an ICM workspace")
    p_export.add_argument("txn", help="Path to JSON transaction payload")
    p_export.add_argument("workspace_root", help="Base directory for numbered workspace folders")
    p_export.add_argument("--domain", default="", help="Override domain")
    p_export.add_argument("--arena-id", default="", help="Override arena ID")
    p_export.add_argument("--arena-version", default="", help="Override arena version")
    p_export.add_argument("--stages", default="", help="Path to JSON array of ICMStageDescriptor dicts")
    p_export.add_argument("--qdkt", action="store_true", help="Record QDKT export event")
    p_export.add_argument("--dream-candidates", default="", help="Path to JSON array of DreamCandidate dicts")
    p_export.add_argument("--dream-query", default="", help="DREAM-lite query string")
    p_export.add_argument("--dream-target-type", default="", help="DREAM-lite target type")
    p_export.set_defaults(func=export_cli)

    # import
    p_import = sub.add_parser("import", help="Import an ICM workspace back to JSON")
    p_import.add_argument("workspace", help="Path to ICM workspace directory")
    p_import.add_argument("--out", default="", help="Optional output JSON file (default: stdout)")
    p_import.set_defaults(func=import_cli)

    # list
    p_list = sub.add_parser("list", help="List numbered ICM workspaces under a root")
    p_list.add_argument("workspace_root", help="Base directory to scan")
    p_list.set_defaults(func=list_cli)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate/verify current source anchors from Aura's CODEMAP.

Stable identity is the CODEMAP semantic symbol identity + signature hash.
Line numbers are current projections and are regenerated after navigation refresh.
This file is navigation only: it never becomes source, patch, policy, or authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "AURA_SOURCE_ANCHOR_MAP_V1"
DEFAULT_CODEMAP = Path(".aura/CODEMAP.json")
DEFAULT_MANIFEST = Path(".aura/source_anchor_manifest.v1.json")
DEFAULT_OUTPUT = Path(".aura/SOURCE_ANCHORS.md")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _file_digest(codemap: dict[str, Any], path: str) -> str:
    for card in codemap.get("files", []):
        if isinstance(card, dict) and card.get("path") == path:
            return str(card.get("digest8") or "")
    return ""


def resolve_anchor(codemap: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    symbol = str(spec.get("symbol") or "").strip()
    path = str(spec.get("path") or "").strip()
    kind = str(spec.get("kind") or "").strip()
    if not symbol or not path:
        raise ValueError("every source anchor requires nonempty path and symbol")
    hits = codemap.get("symbol_index", {}).get(symbol, [])
    matches = [
        hit for hit in hits
        if isinstance(hit, dict)
        and hit.get("file") == path
        and (not kind or hit.get("kind") == kind)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"source anchor {spec.get('anchor_id') or symbol!r} resolved to {len(matches)} "
            f"CODEMAP symbols for {path}:{symbol}; expected exactly one"
        )
    hit = dict(matches[0])
    line = hit.get("line")
    end_line = hit.get("end_line", line)
    if type(line) is not int or type(end_line) is not int or line < 1 or end_line < line:
        raise ValueError(f"invalid CODEMAP line range for {path}:{symbol}")
    semantic_id = str(hit.get("semantic_id") or "")
    signature_hash = str(hit.get("signature_hash") or "")
    if not semantic_id or not signature_hash:
        raise ValueError(f"missing semantic identity for {path}:{symbol}; refresh CODEMAP first")
    return {
        **spec,
        "line": line,
        "end_line": end_line,
        "semantic_id": semantic_id,
        "signature_hash": signature_hash,
        "file_digest8": _file_digest(codemap, path),
    }


def resolve_manifest(codemap: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("version") != "AURA_SOURCE_ANCHOR_MANIFEST_V1":
        raise ValueError("unsupported source anchor manifest version")
    anchors = manifest.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        raise ValueError("source anchor manifest must contain a nonempty anchors list")
    ids: set[str] = set()
    resolved: list[dict[str, Any]] = []
    for raw in anchors:
        if not isinstance(raw, dict):
            raise ValueError("source anchor entries must be objects")
        anchor_id = str(raw.get("anchor_id") or "").strip()
        if not anchor_id or anchor_id in ids:
            raise ValueError("source anchor IDs must be nonempty and unique")
        ids.add(anchor_id)
        resolved.append(resolve_anchor(codemap, raw))
    return resolved


def render_markdown(resolved: list[dict[str, Any]], *, codemap_path: str) -> str:
    lines = [
        "# Aura Source Anchors",
        "",
        f"**Version:** `{VERSION}`  ",
        f"**Generated from:** `{codemap_path}` + `.aura/source_anchor_manifest.v1.json`  ",
        "**Authority:** navigation projection only; exact current source/tests/contracts remain authoritative.",
        "",
        "> **Do not use line numbers as durable identity.** CODEMAP `semantic_id` + `signature_hash` identify the selected symbol; `Lstart-Lend` is regenerated whenever navigation state is refreshed.",
        "",
        "| Mechanism | Symbol | Current source span | Semantic identity | Signature | Why it matters |",
        "|---|---|---|---|---|---|",
    ]
    for item in resolved:
        path = str(item["path"])
        start = int(item["line"])
        end = int(item["end_line"])
        label = f"{path}:L{start}-L{end}"
        link = f"../{path}#L{start}-L{end}"
        lines.append(
            "| {mechanism} | `{symbol}` | [{label}]({link}) | `{semantic}` | `{signature}` | {role} |".format(
                mechanism=str(item.get("mechanism") or item["anchor_id"]).replace("|", "\\|"),
                symbol=str(item["symbol"]),
                label=label,
                link=link,
                semantic=str(item["semantic_id"]).replace("|", "\\|"),
                signature=str(item["signature_hash"]),
                role=str(item.get("role") or "").replace("|", "\\|"),
            )
        )
    lines += [
        "",
        "## Refresh contract",
        "",
        "```text",
        "source changes",
        "→ refresh CODEMAP touched branches",
        "→ semantic IDs / signatures / line ranges regenerate",
        "→ regenerate SOURCE_ANCHORS.md",
        "→ stale/missing/ambiguous anchors fail closed",
        "```",
        "",
        "Use `python scripts/aura_navigation_refresh.py --refresh <changed paths...>` after bounded source writes, or run it without `--refresh` for a full navigation rebuild.",
        "",
    ]
    return "\n".join(lines)


def generate(*, root: Path, codemap_path: Path, manifest_path: Path) -> str:
    codemap_abs = codemap_path if codemap_path.is_absolute() else root / codemap_path
    manifest_abs = manifest_path if manifest_path.is_absolute() else root / manifest_path
    codemap = _load_json(codemap_abs)
    manifest = _load_json(manifest_abs)
    resolved = resolve_manifest(codemap, manifest)
    return render_markdown(resolved, codemap_path=codemap_path.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or verify Aura source anchors from CODEMAP")
    parser.add_argument("--root", default=".")
    parser.add_argument("--codemap", default=str(DEFAULT_CODEMAP))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write the generated anchor projection")
    mode.add_argument("--check", action="store_true", help="fail if the committed projection is stale")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_path = Path(args.output)
    output_abs = output_path if output_path.is_absolute() else root / output_path
    rendered = generate(
        root=root,
        codemap_path=Path(args.codemap),
        manifest_path=Path(args.manifest),
    )
    if args.check:
        if not output_abs.exists() or output_abs.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "SOURCE_ANCHORS.md is stale; run python scripts/aura_navigation_refresh.py "
                "or python scripts/aura_source_anchor_map.py --write"
            )
        print(f"[+] source anchors current: {output_abs}")
        return 0
    output_abs.parent.mkdir(parents=True, exist_ok=True)
    output_abs.write_text(rendered, encoding="utf-8")
    print(f"[+] wrote source anchors {output_abs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

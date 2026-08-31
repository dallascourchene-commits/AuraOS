#!/usr/bin/env python3
"""Admit Aura source anchors for exact ASTGE source hydration.

This is an interoperability membrane, not a second source-anchor resolver.
Aura's existing ``aura_source_anchor_map`` remains the owner of navigation-anchor
resolution. This module adds one separate requirement before an anchor may hydrate
source bytes: an externally supplied body/currentness witness must match the exact
current file length and SHA-256.

Navigation identity, body currentness, file-ID materialization, semantic truth, and
authority remain distinct planes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_source_anchor_map import resolve_manifest

VERSION = "AURA_ASTGE_ANCHOR_HYDRATION_V1"
WITNESS_VERSION = "AURA_ASTGE_SOURCE_BODY_WITNESS_V1"
CURRENT = "CURRENT"
STALE = "STALE"
UNKNOWN = "UNKNOWN"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _hex_sha256(value: Any, *, field: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{field} must be a 64-character SHA-256 hex digest")
    return text


def _nonnegative_int(value: Any, *, field: str, maximum: int | None = None) -> int:
    if type(value) is not int or value < 0 or (maximum is not None and value > maximum):
        suffix = f" <= {maximum}" if maximum is not None else ""
        raise ValueError(f"{field} must be an integer >= 0{suffix}")
    return value


def _nonempty_text(value: Any, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be nonempty")
    return text


def _validate_relative_path(path: str) -> None:
    if (
        not path
        or path.startswith("/")
        or path.endswith("/")
        or "\\" in path
        or ":" in path
        or any(ord(char) < 32 for char in path)
    ):
        raise ValueError(f"unsafe source-anchor path: {path!r}")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe source-anchor path: {path!r}")


def _read_exact_repo_file(root: Path, relative_path: str) -> bytes:
    """Read one repo-relative regular file without following symlink components."""
    _validate_relative_path(relative_path)
    current = root
    parts = relative_path.split("/")
    for index, component in enumerate(parts):
        current = current / component
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            raise ValueError(f"source-anchor path is missing: {relative_path}") from exc
        if current.is_symlink():
            raise ValueError(f"source-anchor path contains a symlink: {relative_path}")
        is_last = index + 1 == len(parts)
        if is_last:
            if not current.is_file():
                raise ValueError(f"source-anchor target is not a regular file: {relative_path}")
        elif not current.is_dir():
            raise ValueError(f"source-anchor parent is not a directory: {relative_path}")
    return current.read_bytes()


def _parse_witnesses(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if raw.get("version") != WITNESS_VERSION:
        raise ValueError("unsupported ASTGE source-body witness version")
    rows = raw.get("witnesses")
    if not isinstance(rows, list):
        raise ValueError("witness manifest requires a witnesses list")

    parsed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each source-body witness must be an object")
        anchor_id = _nonempty_text(row.get("anchor_id"), field="anchor_id")
        if anchor_id in parsed:
            raise ValueError(f"duplicate source-body witness for anchor {anchor_id!r}")
        parsed[anchor_id] = {
            "anchor_id": anchor_id,
            "file_id": _nonnegative_int(row.get("file_id"), field="file_id", maximum=(2**32 - 1)),
            "source_generation": _nonnegative_int(
                row.get("source_generation"), field="source_generation"
            ),
            "expected_byte_len": _nonnegative_int(
                row.get("expected_byte_len"), field="expected_byte_len"
            ),
            "expected_body_sha256": _hex_sha256(
                row.get("expected_body_sha256"), field="expected_body_sha256"
            ),
            "witness_ref": _nonempty_text(row.get("witness_ref"), field="witness_ref"),
            "checked_at": _nonempty_text(row.get("checked_at"), field="checked_at"),
        }
    return parsed


def compile_hydration_admission(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Resolve navigation anchors, then independently admit body currentness.

    The source-anchor owner is reused verbatim through ``resolve_manifest``. Any
    semantic/signature ambiguity or drift remains its hard failure. Missing body
    witnesses are UNKNOWN, body mismatches are STALE, and only exact matches may
    emit a D9-compatible SourceLocatorV1 projection.
    """
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be a directory")

    resolved = resolve_manifest(codemap, anchor_manifest)
    witnesses = _parse_witnesses(witness_manifest)
    known_anchor_ids = {str(item["anchor_id"]) for item in resolved}
    unknown_witnesses = sorted(set(witnesses) - known_anchor_ids)
    if unknown_witnesses:
        raise ValueError(f"witnesses reference unknown anchors: {unknown_witnesses}")

    # One physical source file may host several semantic anchors, but the mapping
    # from file_id <-> path/current body generation must be one-to-one and coherent.
    by_file_id: dict[int, tuple[str, int, int, str]] = {}
    by_path: dict[str, tuple[int, int, int, str]] = {}
    for item in resolved:
        anchor_id = str(item["anchor_id"])
        witness = witnesses.get(anchor_id)
        if witness is None:
            continue
        path = str(item["path"])
        binding = (
            witness["file_id"],
            witness["source_generation"],
            witness["expected_byte_len"],
            witness["expected_body_sha256"],
        )
        prior_path = by_file_id.get(witness["file_id"])
        expected_for_id = (
            path,
            witness["source_generation"],
            witness["expected_byte_len"],
            witness["expected_body_sha256"],
        )
        if prior_path is not None and prior_path != expected_for_id:
            raise ValueError(f"file_id {witness['file_id']} has conflicting source bindings")
        prior_binding = by_path.get(path)
        if prior_binding is not None and prior_binding != binding:
            raise ValueError(f"path {path!r} has conflicting source-body witnesses")
        by_file_id[witness["file_id"]] = expected_for_id
        by_path[path] = binding

    receipts: list[dict[str, Any]] = []
    locator_by_path: dict[str, dict[str, Any]] = {}
    for item in resolved:
        anchor_id = str(item["anchor_id"])
        path = str(item["path"])
        witness = witnesses.get(anchor_id)
        base = {
            "anchor_id": anchor_id,
            "path": path,
            "symbol": str(item["symbol"]),
            "kind": str(item.get("kind") or ""),
            "semantic_id": str(item["semantic_id"]),
            "signature_hash": str(item["signature_hash"]),
            "line": int(item["line"]),
            "end_line": int(item["end_line"]),
            "codemap_file_digest8": str(item.get("file_digest8") or ""),
            "anchor_projection_resolved": True,
            "codemap_digest8_currentness_authority": False,
            "semantic_identity_minted_by_bridge": False,
            "source_authority_minted": False,
            "project007_runtime_implemented": False,
        }
        if witness is None:
            receipts.append(
                {
                    **base,
                    "body_currentness_status": UNKNOWN,
                    "hydration_admitted": False,
                    "reason": "MISSING_SOURCE_BODY_WITNESS",
                    "locator": None,
                }
            )
            continue

        bytes_value = _read_exact_repo_file(root, path)
        observed_len = len(bytes_value)
        observed_sha256 = hashlib.sha256(bytes_value).hexdigest()
        locator = {
            "file_id": witness["file_id"],
            "relative_path": path,
            "source_generation": witness["source_generation"],
            "byte_len": observed_len,
            "sha256": observed_sha256,
        }
        witness_receipt = {
            "witness_ref": witness["witness_ref"],
            "checked_at": witness["checked_at"],
            "expected_byte_len": witness["expected_byte_len"],
            "observed_byte_len": observed_len,
            "expected_body_sha256": witness["expected_body_sha256"],
            "observed_body_sha256": observed_sha256,
        }
        if observed_len != witness["expected_byte_len"]:
            receipts.append(
                {
                    **base,
                    **witness_receipt,
                    "body_currentness_status": STALE,
                    "hydration_admitted": False,
                    "reason": "SOURCE_BODY_LENGTH_DRIFT",
                    "locator": None,
                }
            )
            continue
        if observed_sha256 != witness["expected_body_sha256"]:
            receipts.append(
                {
                    **base,
                    **witness_receipt,
                    "body_currentness_status": STALE,
                    "hydration_admitted": False,
                    "reason": "SOURCE_BODY_DIGEST_DRIFT",
                    "locator": None,
                }
            )
            continue

        receipts.append(
            {
                **base,
                **witness_receipt,
                "body_currentness_status": CURRENT,
                "hydration_admitted": True,
                "reason": "EXACT_SOURCE_BODY_WITNESS_MATCH",
                "locator": locator,
            }
        )
        locator_by_path[path] = locator

    counts = {CURRENT: 0, STALE: 0, UNKNOWN: 0}
    for receipt in receipts:
        counts[receipt["body_currentness_status"]] += 1

    return {
        "version": VERSION,
        "anchor_owner_reused": "scripts/aura_source_anchor_map.py",
        "source_body_witness_required": True,
        "unknown_or_stale_hydration_admitted": False,
        "codemap_digest8_currentness_authority": False,
        "source_authority_minted": False,
        "project007_runtime_implemented": False,
        "counts": counts,
        "anchor_receipts": receipts,
        "source_locators_v1": [locator_by_path[path] for path in sorted(locator_by_path)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve Aura source anchors and require independent body-currentness witnesses"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--codemap", default=".aura/CODEMAP.json")
    parser.add_argument("--anchors", default=".aura/source_anchor_manifest.v1.json")
    parser.add_argument("--witness", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = compile_hydration_admission(
        root=root,
        codemap=_load_json(root / args.codemap),
        anchor_manifest=_load_json(root / args.anchors),
        witness_manifest=_load_json(Path(args.witness)),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

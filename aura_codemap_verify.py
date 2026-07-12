"""Fail-closed verification for Aura's generated CODEMAP and deep topology."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

CODEMAP_VERIFY_VERSION = "AURA_CODEMAP_VERIFY_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
REQUIRED_PATHS = frozenset({
    "aura_arena_experience.py",
    "aura_arena_experience_ledger.py",
    "aura_arena_wfst_runtime.py",
    "aura_arena_crucible.py",
    "aura_crucible_types.py",
    "aura_crucible_miner.py",
    "aura_crucible_validation.py",
    "aura_crucible_store.py",
    "aura_crucible_cli.py",
    "aura_codemap_verify.py",
    "tests/test_aura_crucible_phase_b.py",
    "tests/test_aura_codemap_verify.py",
})
REQUIRED_SYMBOLS = frozenset({
    "OutcomeVector",
    "ArenaExperience",
    "ArenaCrucibleService",
    "CruciblePolicy",
    "validate_manifest_pin",
    "verify_codemap",
})


def verify_codemap(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    json_path = root / ".aura" / "CODEMAP.json"
    markdown_path = root / ".aura" / "CODEMAP.md"
    baseline_path = root / ".aura" / "topology_baseline.json"
    errors: list[str] = []
    warnings: list[str] = []
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _denial("codemap_json_missing", json_path=json_path)
    except (OSError, json.JSONDecodeError) as exc:
        return _denial(f"codemap_json_invalid:{type(exc).__name__}", json_path=json_path)
    if not isinstance(payload, dict):
        return _denial("codemap_json_not_object", json_path=json_path)

    summary = dict(payload.get("summary") or {})
    topology = dict(payload.get("topology") or {})
    nodes = _integer(summary.get("topology_nodes"))
    edges = _integer(summary.get("topology_edges"))
    source = str(summary.get("topology_source") or topology.get("source") or "unknown")
    if nodes <= 0:
        errors.append("topology_nodes_must_be_positive")
    if edges <= 0:
        errors.append("topology_edges_must_be_positive")
    if source != "compiled_deep_topology":
        errors.append("topology_source_must_be_compiled_deep_topology")
    file_index = topology.get("file_index")
    if not isinstance(file_index, dict) or not file_index:
        errors.append("topology_file_index_missing")

    file_cards = payload.get("files") or []
    indexed_paths = {
        str(card.get("path") or "") for card in file_cards if isinstance(card, dict)
    }
    missing_paths = sorted(REQUIRED_PATHS - indexed_paths)
    if missing_paths:
        errors.append("required_paths_missing")

    symbol_index = payload.get("symbol_index") or {}
    indexed_symbols = set(symbol_index) if isinstance(symbol_index, dict) else set()
    missing_symbols = sorted(REQUIRED_SYMBOLS - indexed_symbols)
    if missing_symbols:
        errors.append("required_symbols_missing")

    baseline: dict[str, Any] = {}
    if baseline_path.exists():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append("topology_baseline_invalid")
        if isinstance(baseline, dict):
            reference_nodes = _integer(baseline.get("topology_nodes"))
            reference_edges = _integer(baseline.get("topology_edges"))
            minimum_ratio = _ratio(baseline.get("minimum_ratio"), 0.90)
            if reference_nodes > 0 and nodes < int(reference_nodes * minimum_ratio):
                errors.append("topology_node_regression")
            if reference_edges > 0 and edges < int(reference_edges * minimum_ratio):
                errors.append("topology_edge_regression")
    else:
        warnings.append("topology_baseline_missing")

    markdown_summary: dict[str, Any] = {}
    try:
        markdown = markdown_path.read_text(encoding="utf-8")
        markdown_summary = {
            "topology_nodes": _markdown_integer(markdown, "topology_nodes"),
            "topology_edges": _markdown_integer(markdown, "topology_edges"),
            "topology_source": _markdown_text(markdown, "topology_source"),
        }
        if markdown_summary["topology_nodes"] != nodes:
            errors.append("markdown_topology_nodes_mismatch")
        if markdown_summary["topology_edges"] != edges:
            errors.append("markdown_topology_edges_mismatch")
        if markdown_summary["topology_source"] != source:
            errors.append("markdown_topology_source_mismatch")
    except FileNotFoundError:
        errors.append("codemap_markdown_missing")
    except OSError:
        errors.append("codemap_markdown_unreadable")

    return {
        "ok": not errors,
        "version": CODEMAP_VERIFY_VERSION,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "file_count": _integer(summary.get("file_count")),
            "topology_nodes": nodes,
            "topology_edges": edges,
            "topology_source": source,
            "topology_file_count": len(file_index) if isinstance(file_index, dict) else 0,
            "indexed_path_count": len(indexed_paths),
            "indexed_symbol_count": len(indexed_symbols),
        },
        "markdown_summary": markdown_summary,
        "baseline": baseline,
        "missing_paths": missing_paths,
        "missing_symbols": missing_symbols,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify Aura CODEMAP deep topology")
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = verify_codemap(args.repo_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def _markdown_integer(text: str, name: str) -> int:
    match = re.search(rf"\*\*{re.escape(name)}\*\*:\s*(\d+)", text)
    return int(match.group(1)) if match else -1


def _markdown_text(text: str, name: str) -> str:
    match = re.search(rf"\*\*{re.escape(name)}\*\*:\s*([^\r\n]+)", text)
    return match.group(1).strip() if match else ""


def _integer(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _ratio(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _denial(reason: str, *, json_path: Path) -> dict[str, Any]:
    return {
        "ok": False,
        "version": CODEMAP_VERIFY_VERSION,
        "errors": [reason],
        "warnings": [],
        "json_path": str(json_path),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


if __name__ == "__main__":
    raise SystemExit(main())

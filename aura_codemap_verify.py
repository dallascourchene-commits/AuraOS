"""Fail-closed verification for Aura's generated CODEMAP and deep topology."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

CODEMAP_VERIFY_VERSION = "AURA_CODEMAP_VERIFY_V4"
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
_VOLATILE_SUMMARY_FIELDS = frozenset({"elapsed_ms", "last_incremental_refresh_unix", "total_bytes", "text_tokens_est"})
_SELF_REFERENTIAL_GENERATED_DIGEST_PATHS = frozenset({"topology_map.json"})
_SOURCE_CARD_FIELDS = (
    "path",
    "role",
    "bytes",
    "lines",
    "tokens_est",
    "binary",
    "symbol_count",
    "commands",
    "command_lines",
    "digest8",
)


def verify_codemap(
    repo_root: str | Path = ".",
    *,
    compare_json_path: str | Path | None = None,
) -> dict[str, Any]:
    """Verify topology integrity and optionally compare stable regenerated content."""

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

    stable_comparison: dict[str, Any] | None = None
    if compare_json_path is not None:
        comparison_path = Path(compare_json_path)
        if not comparison_path.is_absolute():
            comparison_path = root / comparison_path
        try:
            reference_payload = json.loads(comparison_path.read_text(encoding="utf-8"))
            if not isinstance(reference_payload, dict):
                raise TypeError("comparison payload is not an object")
        except FileNotFoundError:
            errors.append("codemap_comparison_json_missing")
            stable_comparison = {"ok": False, "comparison_path": str(comparison_path)}
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            errors.append("codemap_comparison_json_invalid")
            stable_comparison = {
                "ok": False,
                "comparison_path": str(comparison_path),
                "error": type(exc).__name__,
            }
        else:
            stable_comparison = compare_codemap_payloads(reference_payload, payload)
            stable_comparison["comparison_path"] = str(comparison_path)
            if not stable_comparison["ok"]:
                errors.append("codemap_stable_structure_changed")

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
        "stable_comparison": stable_comparison,
        "missing_paths": missing_paths,
        "missing_symbols": missing_symbols,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def stable_codemap_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Return Aura's canonical repository structure for regeneration comparison.

    Exact source cards, commands, symbols, rings, aggregate topology counts, and
    per-file graph structure remain authoritative. Runtime metadata and redundant
    presentation rankings are excluded because they may vary across clean checkouts
    without changing repository or graph meaning. The generated ``topology_map.json``
    digest is self-referential and is normalized while its size, shape, role, and
    independently compiled graph metrics remain verified.
    """

    summary = {
        key: value
        for key, value in dict(payload.get("summary") or {}).items()
        if key not in _VOLATILE_SUMMARY_FIELDS
    }
    coverage = dict(payload.get("coverage") or {})
    stable_coverage = {
        key: coverage.get(key)
        for key in (
            "included_file_count",
            "included_policy",
            "excluded_generated_map_files",
            "all_included_paths_sorted",
        )
        if key in coverage
    }
    source_cards = []
    for raw in payload.get("files", []) or []:
        if not isinstance(raw, dict):
            continue
        card = {key: raw.get(key) for key in _SOURCE_CARD_FIELDS if key in raw}
        if str(card.get("path") or "") in _SELF_REFERENTIAL_GENERATED_DIGEST_PATHS:
            card["bytes"] = 0
            card["lines"] = 0
            card["tokens_est"] = 0
            card["digest8"] = "SELF_REFERENTIAL_GENERATED_ARTIFACT"
        source_cards.append(card)
    source_cards.sort(key=lambda item: str(item.get("path") or ""))

    topology = dict(payload.get("topology") or {})
    file_index = topology.get("file_index") if isinstance(topology.get("file_index"), dict) else {}
    stable_file_index = {
        str(file_name): _stable_topology_bucket(bucket)
        for file_name, bucket in sorted(file_index.items())
        if isinstance(bucket, dict)
    }
    return {
        "status": payload.get("status"),
        "generated_by": payload.get("generated_by"),
        "intent_packet": payload.get("intent_packet"),
        "navigation_protocol": payload.get("navigation_protocol"),
        "summary": summary,
        "coverage": stable_coverage,
        "rings": payload.get("rings"),
        "command_index": payload.get("command_index"),
        "symbol_index": payload.get("symbol_index"),
        "source_cards": source_cards,
        "topology": {
            "source": topology.get("source"),
            "file_index": stable_file_index,
        },
    }


def compare_codemap_payloads(reference: dict[str, Any], regenerated: dict[str, Any]) -> dict[str, Any]:
    """Compare canonical CODEMAP structure while ignoring runtime-only metadata."""

    left = stable_codemap_projection(reference)
    right = stable_codemap_projection(regenerated)
    differing_fields = sorted(
        key for key in set(left) | set(right) if left.get(key) != right.get(key)
    )
    return {
        "ok": not differing_fields,
        "reference_digest": _canonical_digest(left),
        "regenerated_digest": _canonical_digest(right),
        "differing_fields": differing_fields,
        "volatile_or_derived_fields_ignored": [
            "root",
            "generated_at_unix",
            "summary.elapsed_ms",
            "summary.last_incremental_refresh_unix",
            "summary.total_bytes/text_tokens_est (includes generated topology artifact)",
            "coverage.skipped_dir_file_counts",
            "files[*].vector",
            "files[*].topology.hub_rank",
            "topology_map.json bytes/lines/tokens_est/digest8 (generated artifact)",
            "hubs",
            "topology.diagnostics",
            "topology.meta",
            "topology.top_files_by_degree",
        ],
    }


def _stable_topology_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize one per-file topology bucket without presentation rank."""

    edge_kinds = bucket.get("edge_kinds") if isinstance(bucket.get("edge_kinds"), dict) else {}
    return {
        "node_count": _integer(bucket.get("node_count")),
        "edge_count": _integer(bucket.get("edge_count")),
        "degree": _integer(bucket.get("degree")),
        "symbols": sorted(str(item) for item in bucket.get("symbols", []) or []),
        "neighbor_files": sorted(str(item) for item in bucket.get("neighbor_files", []) or []),
        "edge_kinds": {str(key): _integer(value) for key, value in sorted(edge_kinds.items())},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify Aura CODEMAP deep topology")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--compare-json",
        default=None,
        help="Optional pre-regeneration CODEMAP JSON to compare structurally",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = verify_codemap(args.repo_root, compare_json_path=args.compare_json)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def _canonical_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


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

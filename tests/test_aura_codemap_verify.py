from __future__ import annotations

import json
from pathlib import Path

from aura_codemap_verify import (
    REQUIRED_PATHS,
    REQUIRED_SYMBOLS,
    compare_codemap_payloads,
    verify_codemap,
)


def _payload(*, nodes: int = 6000, edges: int = 12500,
             source: str = "compiled_deep_topology") -> dict:
    return {
        "status": "AURA_CODEMAP_ACTIVE",
        "generated_by": "aura_codebase_navigator",
        "generated_at_unix": 100,
        "root": "/tmp/checkout-a",
        "intent_packet": "[OP:NAVIGATE]",
        "coverage": {
            "included_file_count": len(REQUIRED_PATHS),
            "included_policy": "all repository files",
            "excluded_generated_map_files": [".aura/CODEMAP.json", ".aura/CODEMAP.md"],
            "skipped_dir_file_counts": {".git": 20, "__pycache__": 3},
        },
        "summary": {
            "file_count": len(REQUIRED_PATHS),
            "total_bytes": 1000,
            "text_tokens_est": 250,
            "role_counts": {"python_module": len(REQUIRED_PATHS)},
            "topology_nodes": nodes,
            "topology_edges": edges,
            "topology_source": source,
            "elapsed_ms": 125.5,
        },
        "navigation_protocol": ["Read CODEMAP first."],
        "rings": {"core": sorted(REQUIRED_PATHS)},
        "hubs": [{"path": "aura.py", "topology_degree": 2}],
        "command_index": {"!test": ["aura.py:1"]},
        "topology": {
            "source": source,
            "diagnostics": {"elapsed_ms": 10},
            "meta": {"generated_at": 100},
            "file_index": {"aura.py": {"degree": 2}},
            "top_files_by_degree": [{"file": "aura.py", "degree": 2}],
        },
        "files": [{"path": path} for path in sorted(REQUIRED_PATHS)],
        "symbol_index": {name: [{"file": "aura.py", "line": 1}] for name in REQUIRED_SYMBOLS},
    }


def _write_fixture(root: Path, *, nodes: int = 6000, edges: int = 12500,
                   source: str = "compiled_deep_topology") -> None:
    aura = root / ".aura"
    aura.mkdir(parents=True)
    payload = _payload(nodes=nodes, edges=edges, source=source)
    (aura / "CODEMAP.json").write_text(json.dumps(payload), encoding="utf-8")
    (aura / "CODEMAP.md").write_text(
        "# Aura Compact Code Map\n\n"
        f"- **topology_nodes**: {nodes}\n"
        f"- **topology_edges**: {edges}\n"
        f"- **topology_source**: {source}\n",
        encoding="utf-8",
    )
    (aura / "topology_baseline.json").write_text(json.dumps({
        "topology_nodes": 5914,
        "topology_edges": 12233,
        "minimum_ratio": 0.90,
    }), encoding="utf-8")


def test_valid_codemap_passes_deep_topology_contract(tmp_path: Path):
    _write_fixture(tmp_path)
    result = verify_codemap(tmp_path)
    assert result["ok"]
    assert result["summary"]["topology_source"] == "compiled_deep_topology"
    assert not result["missing_paths"]
    assert not result["missing_symbols"]


def test_zero_or_unknown_topology_fails_closed(tmp_path: Path):
    _write_fixture(tmp_path, nodes=0, edges=0, source="unknown")
    result = verify_codemap(tmp_path)
    assert not result["ok"]
    assert "topology_nodes_must_be_positive" in result["errors"]
    assert "topology_edges_must_be_positive" in result["errors"]
    assert "topology_source_must_be_compiled_deep_topology" in result["errors"]


def test_regression_and_markdown_mismatch_are_detected(tmp_path: Path):
    _write_fixture(tmp_path, nodes=100, edges=100)
    markdown = tmp_path / ".aura" / "CODEMAP.md"
    markdown.write_text(
        markdown.read_text().replace("100\n- **topology_edges**", "101\n- **topology_edges**"),
        encoding="utf-8",
    )
    result = verify_codemap(tmp_path)
    assert not result["ok"]
    assert "topology_node_regression" in result["errors"]
    assert "topology_edge_regression" in result["errors"]
    assert "markdown_topology_nodes_mismatch" in result["errors"]


def test_stable_comparison_ignores_runtime_only_fields():
    reference = _payload()
    regenerated = json.loads(json.dumps(reference))
    regenerated["generated_at_unix"] = 999
    regenerated["root"] = "/home/runner/work/AuraOS/AuraOS"
    regenerated["summary"]["elapsed_ms"] = 9999.9
    regenerated["coverage"]["skipped_dir_file_counts"] = {".git": 50, "__pycache__": 100}
    regenerated["topology"]["diagnostics"] = {"elapsed_ms": 400}
    regenerated["topology"]["meta"] = {"generated_at": 999}
    result = compare_codemap_payloads(reference, regenerated)
    assert result["ok"]
    assert result["reference_digest"] == result["regenerated_digest"]


def test_stable_comparison_detects_structural_change():
    reference = _payload()
    regenerated = json.loads(json.dumps(reference))
    regenerated["summary"]["topology_nodes"] += 1
    regenerated["files"].append({"path": "unexpected.py"})
    result = compare_codemap_payloads(reference, regenerated)
    assert not result["ok"]
    assert "summary" in result["differing_fields"]
    assert "files" in result["differing_fields"]


def test_verify_codemap_can_compare_pre_regeneration_snapshot(tmp_path: Path):
    _write_fixture(tmp_path)
    reference = _payload()
    reference["root"] = "/different/checkout"
    reference["generated_at_unix"] = 1
    reference["summary"]["elapsed_ms"] = 1.0
    comparison_path = tmp_path / "committed.json"
    comparison_path.write_text(json.dumps(reference), encoding="utf-8")
    result = verify_codemap(tmp_path, compare_json_path=comparison_path)
    assert result["ok"]
    assert result["stable_comparison"]["ok"]

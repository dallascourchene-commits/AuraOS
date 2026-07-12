from __future__ import annotations

import json
from pathlib import Path

from aura_codemap_verify import REQUIRED_PATHS, REQUIRED_SYMBOLS, verify_codemap


def _write_fixture(root: Path, *, nodes: int = 6000, edges: int = 12500,
                   source: str = "compiled_deep_topology") -> None:
    aura = root / ".aura"
    aura.mkdir(parents=True)
    payload = {
        "summary": {
            "file_count": len(REQUIRED_PATHS),
            "topology_nodes": nodes,
            "topology_edges": edges,
            "topology_source": source,
        },
        "topology": {
            "source": source,
            "file_index": {"aura.py": {"degree": 2}},
        },
        "files": [{"path": path} for path in sorted(REQUIRED_PATHS)],
        "symbol_index": {name: [{"file": "aura.py", "line": 1}] for name in REQUIRED_SYMBOLS},
    }
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

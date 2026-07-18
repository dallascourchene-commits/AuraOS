from __future__ import annotations

from pathlib import Path

import pytest

from aura_emergent_evidence_spine import (
    AuraEmergentEvidenceSpine,
    EmergentEvidenceRequest,
    _bounded_anchor,
    _expand_atomic_closure,
    _tests_for_nodes,
    build_atomic_function_inventory,
)
from aura_topological_context_anchor import CodeTopoAnchor


def _sources() -> dict[str, str]:
    return {
        "core.py": (
            "def helper(value):\n"
            "    return value * 2\n\n"
            "def compute(value):\n"
            "    return helper(value) + 1\n\n"
            "class Worker:\n"
            "    def run(self, value):\n"
            "        return compute(value)\n"
        ),
        "caller.py": (
            "from core import compute\n\n"
            "def use_compute(value):\n"
            "    return compute(value)\n"
        ),
        "tests/test_core.py": (
            "from core import compute\n\n"
            "def test_compute():\n"
            "    assert compute(2) == 5\n"
        ),
    }


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for relative, source in _sources().items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def _node(anchor: CodeTopoAnchor, symbol: str):
    return next(
        item
        for item in anchor.nodes.values()
        if item.symbol == symbol and item.kind != "module"
    )


def test_request_rejects_truthy_non_boolean_options() -> None:
    with pytest.raises(ValueError, match="boolean"):
        EmergentEvidenceRequest.from_value(
            {"objective": "inspect", "include_source": "false"}
        )


def test_inventory_filters_exact_qualified_method_identity(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    packet = build_atomic_function_inventory(
        root,
        target_symbols=["Worker.run"],
    )
    assert packet["ok"] is True
    assert [item["qualified_symbol"] for item in packet["atomic_functions"]] == [
        "Worker.run"
    ]


def test_inventory_honors_python_encoding_cookie(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    encoded = root / "encoded.py"
    encoded.write_bytes(
        b"# -*- coding: cp1252 -*-\n"
        b"def caf\xe9():\n"
        b"    return 'caf\xe9'\n"
    )
    packet = build_atomic_function_inventory(root)
    assert packet["ok"] is True
    assert any(item["symbol"] == "café" for item in packet["atomic_functions"])


def test_invalid_source_encoding_fails_closed_instead_of_partial_inventory(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    (root / "broken.py").write_bytes(
        b"# coding: definitely-not-an-encoding\ndef broken():\n    return 1\n"
    )
    packet = AuraEmergentEvidenceSpine(root).run({"objective": "inspect sources"})
    assert packet["ok"] is False
    assert packet["safe_to_patch"] is False
    assert "encoding" in packet["error"].lower() or "syntaxerror" in packet["error"].lower()


def test_bounded_closure_never_emits_edges_to_unselected_nodes() -> None:
    anchor = CodeTopoAnchor.build_from_files(_sources())
    compute = _node(anchor, "compute")
    selected, edges = _expand_atomic_closure(
        anchor,
        [compute.node_id],
        radius=3,
        max_nodes=1,
    )
    selected_ids = set(selected)
    assert len(selected_ids) == 1
    assert all(
        item["src_id"] in selected_ids and item["dst_id"] in selected_ids
        for item in edges
    )


def test_bounded_anchor_preserves_test_callable_and_test_edge(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    anchor = CodeTopoAnchor.build_from_files(_sources())
    compute = _node(anchor, "compute")
    tests = _tests_for_nodes(anchor, [compute.node_id], root)
    bounded = _bounded_anchor(anchor, [compute.node_id], tests)
    assert "tests/test_core.py" in tests
    assert any(node.symbol == "test_compute" for node in bounded.nodes.values())
    assert any(edge.edge_type == "test" for edge in bounded.edges)

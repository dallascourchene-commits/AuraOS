from __future__ import annotations

import ast

from aura_waboose_semantic_rules import scan_semantic_review_rules


def _rules(source: str) -> set[str]:
    return {
        item["rule"]
        for item in scan_semantic_review_rules(
            file="sample.py",
            source=source,
            tree=ast.parse(source),
        )
    }


def test_negative_endpoint_guard_proves_bounded_edge_consistency() -> None:
    source = '''
def _expand_atomic_closure(anchor, seed_ids, max_nodes):
    visited = []
    queue = list(seed_ids)
    admitted_edges = []
    while queue and len(visited) < max_nodes:
        visited.append(queue.pop(0))
    selected = set(visited)
    for edge in anchor.edges:
        if edge.src_id not in selected or edge.dst_id not in selected:
            continue
        admitted_edges.append(edge.to_dict())
    return visited, admitted_edges
'''
    assert "bounded-closure-emits-unselected-edge-endpoints" not in _rules(source)


def test_atomic_test_callable_admission_preserves_bounded_evidence() -> None:
    source = '''
def _bounded_anchor(anchor, atomic_ids, tests):
    include_ids = set(atomic_ids)
    include_files = set()
    include_files.update(tests)
    for node in anchor.nodes.values():
        if node.file_path in tests and node.kind in ATOMIC_KINDS:
            include_ids.add(node.node_id)
    bounded = object()
    bounded.nodes = {}
    bounded.edges = [
        edge
        for edge in anchor.edges
        if edge.src_id in bounded.nodes and edge.dst_id in bounded.nodes
    ]
    return bounded
'''
    assert "bounded-anchor-drops-test-callable-evidence" not in _rules(source)


def test_regression_test_embedded_bad_source_is_not_scanned_as_runtime_code() -> None:
    source = '''
def test_detects_bounded_anchor_problem():
    bad_source = """
    def _bounded_anchor(anchor, atomic_ids, tests):
        include_ids = set(atomic_ids)
        include_files = set()
        include_files.update(tests)
        bounded = object()
        bounded.nodes = {}
        bounded.edges = [
            edge for edge in anchor.edges
            if edge.src_id in bounded.nodes and edge.dst_id in bounded.nodes
        ]
        return bounded
    """
    assert bad_source
'''
    assert "bounded-anchor-drops-test-callable-evidence" not in _rules(source)

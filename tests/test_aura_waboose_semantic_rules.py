from __future__ import annotations

import ast

from aura_waboose_semantic_rules import (
    SEMANTIC_RULE_PACKS,
    directive_semantic_rule_packs,
    scan_semantic_review_rules,
)


def _rules(source: str) -> set[str]:
    return {
        item["rule"]
        for item in scan_semantic_review_rules(
            file="sample.py",
            source=source,
            tree=ast.parse(source),
        )
    }


def test_detects_truthy_boolean_option_coercion() -> None:
    source = '''
def parse(value):
    return bool(value.get("include_source", True))
'''
    assert "truthy-boolean-option-coercion" in _rules(source)


def test_strict_boolean_helper_is_not_flagged() -> None:
    source = '''
def strict_boolean(value, default=True):
    raw = value.get("include_source")
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    raise ValueError("expected boolean")
'''
    assert "truthy-boolean-option-coercion" not in _rules(source)


def test_detects_lossy_and_skipped_repository_source_ingestion() -> None:
    source = '''
def _repo_python_sources(root):
    files = {}
    for path in root.glob("**/*.py"):
        try:
            files[str(path)] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return files
'''
    rules = _rules(source)
    assert "lossy-repository-source-read" in rules
    assert "repository-source-failure-skipped" in rules


def test_exact_tokenize_source_ingestion_is_not_flagged() -> None:
    source = '''
import tokenize

def _repo_python_sources(root):
    files = {}
    for path in root.glob("**/*.py"):
        with tokenize.open(path) as handle:
            files[str(path)] = handle.read()
    return files
'''
    rules = _rules(source)
    assert "lossy-repository-source-read" not in rules
    assert "repository-source-failure-skipped" not in rules


def test_detects_bare_filter_when_qualified_identity_is_advertised() -> None:
    source = '''
def inventory(records, normalized_symbols):
    qualified_symbol = "Worker.run"
    return [record for record in records if record["symbol"] in normalized_symbols]
'''
    assert "qualified-symbol-filter-collapsed-to-bare-name" in _rules(source)


def test_detects_bare_node_match_at_exact_boundary() -> None:
    source = '''
def _select_seed_nodes(nodes, symbol):
    parent_symbol = "Worker"
    return [node for node in nodes if node.symbol == symbol]
'''
    assert "exact-node-match-uses-bare-symbol" in _rules(source)


def test_detects_edges_emitted_before_bounded_node_admission() -> None:
    source = '''
def _expand_atomic_closure(anchor, seed_ids, max_nodes):
    visited = []
    queue = list(seed_ids)
    admitted_edges = []
    while queue and len(visited) < max_nodes:
        node_id = queue.pop(0)
        visited.append(node_id)
        for edge in anchor.edges:
            admitted_edges.append(edge.to_dict())
            if len(visited) + len(queue) < max_nodes:
                queue.append(edge.dst_id)
    return visited, admitted_edges
'''
    assert "bounded-closure-emits-unselected-edge-endpoints" in _rules(source)


def test_post_filtered_bounded_edges_are_not_flagged() -> None:
    source = '''
def _expand_atomic_closure(anchor, seed_ids, max_nodes):
    visited = []
    queue = list(seed_ids)
    admitted_edges = []
    while queue and len(visited) < max_nodes:
        node_id = queue.pop(0)
        visited.append(node_id)
    selected = set(visited)
    admitted_edges = [
        edge.to_dict()
        for edge in anchor.edges
        if edge.src_id in selected and edge.dst_id in selected
    ]
    return visited, admitted_edges
'''
    assert "bounded-closure-emits-unselected-edge-endpoints" not in _rules(source)


def test_detects_bounded_anchor_that_drops_test_callable_nodes() -> None:
    source = '''
def _bounded_anchor(anchor, atomic_ids, tests):
    include_ids = set(atomic_ids)
    include_files = set()
    include_files.update(tests)
    bounded = object()
    bounded.nodes = {}
    bounded.edges = [
        edge
        for edge in anchor.edges
        if edge.src_id in bounded.nodes and edge.dst_id in bounded.nodes
    ]
    return bounded
'''
    assert "bounded-anchor-drops-test-callable-evidence" in _rules(source)


def test_bounded_anchor_that_admits_test_sources_is_not_flagged() -> None:
    source = '''
def _bounded_anchor(anchor, atomic_ids, tests):
    include_ids = set(atomic_ids)
    include_files = set()
    include_files.update(tests)
    for edge in anchor.edges:
        if edge.edge_type == "test":
            include_ids.add(edge.src_id)
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


def test_directives_map_only_to_explicitly_supported_semantic_packs() -> None:
    assert directive_semantic_rule_packs(
        {
            "name": "closure integrity",
            "question": "Are closure edge endpoints inside the bounded closure?",
        }
    ) == {"bounded_graph_integrity"}
    assert directive_semantic_rule_packs(
        {
            "name": "research authority",
            "question": "Can external research become patch authority?",
        }
    ) == set()
    assert len(SEMANTIC_RULE_PACKS) == 5

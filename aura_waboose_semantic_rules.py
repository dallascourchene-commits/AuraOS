"""Deterministic semantic-integrity rules for Coding Waboose.

These rules cover code-review defects that are not syntax errors and are often
missed by linters: permissive boolean parsing, lossy repository ingestion,
qualified-symbol identity collapse, bounded-graph edge leakage, and dropped test
evidence.  They are intentionally narrow, evidence-producing heuristics rather
than patch authority.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from typing import Any

SEMANTIC_RULES_VERSION = "AURA_WABOOSE_SEMANTIC_RULES_V1"
SEMANTIC_RULE_PACKS = frozenset(
    {
        "strict_input_types",
        "symbol_identity",
        "source_integrity",
        "bounded_graph_integrity",
        "test_evidence_preservation",
    }
)

_BOOLEAN_KEY_PREFIXES = (
    "allow_",
    "automatic_",
    "enable_",
    "include_",
    "is_",
    "require_",
    "run_",
    "use_",
)
_SOURCE_OWNER_TERMS = (
    "inventory",
    "repo_python_sources",
    "repository_sources",
    "source_collector",
    "source_inventory",
)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _constant_string(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _subscript_key(node: ast.AST) -> str:
    if not isinstance(node, ast.Subscript):
        return ""
    return _constant_string(node.slice)


def _exception_names(node: ast.AST | None) -> set[str]:
    if node is None:
        return set()
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {_call_name(node).split(".")[-1]}
    if isinstance(node, ast.Tuple):
        result: set[str] = set()
        for item in node.elts:
            result.update(_exception_names(item))
        return result
    return set()


def _only_skip_statements(body: Sequence[ast.stmt]) -> bool:
    return bool(body) and all(
        isinstance(item, (ast.Continue, ast.Pass))
        or (
            isinstance(item, ast.Expr)
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        )
        for item in body
    )


def _finding(
    *,
    file: str,
    node: ast.AST,
    rule: str,
    pack: str,
    severity: str,
    title: str,
    message: str,
    suggested_fix: str,
    confidence: float = 0.94,
) -> dict[str, Any]:
    line = int(getattr(node, "lineno", 1) or 1)
    return {
        "origin": "waboose_semantic",
        "rule": rule,
        "semantic_rule_pack": pack,
        "category": "correctness",
        "severity": severity,
        "confidence": confidence,
        "title": title,
        "message": message,
        "file": file,
        "line_start": line,
        "line_end": int(getattr(node, "end_lineno", line) or line),
        "suggested_fix": suggested_fix,
        "evidence": [
            {
                "kind": "semantic_ast",
                "source": SEMANTIC_RULES_VERSION,
                "rule_pack": pack,
                "line": line,
            }
        ],
        "status": "corroborated",
    }


class _SemanticVisitor(ast.NodeVisitor):
    def __init__(self, *, file: str, source: str) -> None:
        self.file = file
        self.source = source
        self.findings: list[dict[str, Any]] = []
        self._function_stack: list[str] = []
        self._module_has_qualified_symbol = "qualified_symbol" in source
        self._module_has_parent_symbol = "parent_symbol" in source

    @property
    def function_name(self) -> str:
        return self._function_stack[-1] if self._function_stack else ""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        self._check_truthy_boolean_option(node)
        self._check_lossy_source_read(node)
        self.generic_visit(node)

    def _check_truthy_boolean_option(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name) or node.func.id != "bool" or len(node.args) != 1:
            return
        inner = node.args[0]
        if not isinstance(inner, ast.Call) or not isinstance(inner.func, ast.Attribute):
            return
        if inner.func.attr != "get" or not inner.args:
            return
        key = _constant_string(inner.args[0])
        default_is_boolean = len(inner.args) > 1 and isinstance(inner.args[1], ast.Constant) and isinstance(
            inner.args[1].value, bool
        )
        boolean_key = key.startswith(_BOOLEAN_KEY_PREFIXES) or key.endswith(("_enabled", "_required"))
        if not key or not (default_is_boolean or boolean_key):
            return
        self.findings.append(
            _finding(
                file=self.file,
                node=node,
                rule="truthy-boolean-option-coercion",
                pack="strict_input_types",
                severity="high",
                title="Boolean option accepts truthy non-boolean values",
                message=(
                    f"bool(mapping.get({key!r}, ...)) treats strings such as 'false' as true, "
                    "which can silently enable disclosure, execution, or analysis options."
                ),
                suggested_fix=(
                    "Use a strict boolean parser that accepts bool values, preserves the default "
                    "when absent, and rejects strings and numbers."
                ),
                confidence=0.98,
            )
        )

    def _check_lossy_source_read(self, node: ast.Call) -> None:
        owner = self.function_name.lower()
        if not any(term in owner for term in _SOURCE_OWNER_TERMS):
            return
        name = _call_name(node.func)
        if not (name.endswith("read_text") or name in {"open", "io.open"}):
            return
        errors_value = ""
        for keyword in node.keywords:
            if keyword.arg == "errors":
                errors_value = _constant_string(keyword.value).lower()
        if errors_value not in {"ignore", "replace"}:
            return
        self.findings.append(
            _finding(
                file=self.file,
                node=node,
                rule="lossy-repository-source-read",
                pack="source_integrity",
                severity="high",
                title="Repository source inventory uses lossy decoding",
                message=(
                    f"Source collection uses errors={errors_value!r}; the resulting text and digest "
                    "can differ from the repository file while the inventory still appears complete."
                ),
                suggested_fix=(
                    "Read Python source with tokenize.open() so encoding cookies are honored, and "
                    "propagate read or decoding failures instead of mutating the source text."
                ),
                confidence=0.99,
            )
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        owner = self.function_name.lower()
        exceptions = _exception_names(node.type)
        source_errors = {
            "OSError",
            "UnicodeError",
            "UnicodeDecodeError",
            "LookupError",
            "SyntaxError",
        }
        if (
            any(term in owner for term in _SOURCE_OWNER_TERMS)
            and exceptions.intersection(source_errors)
            and _only_skip_statements(node.body)
        ):
            self.findings.append(
                _finding(
                    file=self.file,
                    node=node,
                    rule="repository-source-failure-skipped",
                    pack="source_integrity",
                    severity="high",
                    title="Repository source collection silently drops failed files",
                    message=(
                        "A source read or decoding failure is converted into continue/pass, so the "
                        "inventory can claim a stable digest over only a partial repository."
                    ),
                    suggested_fix=(
                        "Propagate the failure or return a structured fail-closed packet naming the "
                        "unreadable file; never silently omit it from a complete inventory."
                    ),
                    confidence=0.98,
                )
            )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        if self._module_has_qualified_symbol and isinstance(node.left, ast.Subscript):
            if _subscript_key(node.left) == "symbol" and any(isinstance(op, ast.In) for op in node.ops):
                comparator_names = {
                    item.id for item in node.comparators if isinstance(item, ast.Name)
                }
                if comparator_names.intersection({"normalized_symbols", "target_symbols", "symbols"}):
                    self.findings.append(
                        _finding(
                            file=self.file,
                            node=node,
                            rule="qualified-symbol-filter-collapsed-to-bare-name",
                            pack="symbol_identity",
                            severity="high",
                            title="Exact symbol filtering ignores the advertised qualified identity",
                            message=(
                                "The module exposes qualified_symbol but this exact-selection boundary "
                                "compares only the bare symbol, so Worker.run cannot be selected exactly "
                                "and same-named methods may be over-selected."
                            ),
                            suggested_fix=(
                                "Compare the target against both symbol and qualified_symbol through one "
                                "canonical node-identity helper."
                            ),
                            confidence=0.97,
                        )
                    )
        if self._module_has_parent_symbol and any(
            isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops
        ):
            owner = self.function_name.lower()
            exact_boundary = any(term in owner for term in ("select", "admit", "match", "inventory"))
            if exact_boundary and isinstance(node.left, ast.Attribute) and node.left.attr == "symbol":
                if any(isinstance(item, ast.Name) and item.id == "symbol" for item in node.comparators):
                    self.findings.append(
                        _finding(
                            file=self.file,
                            node=node,
                            rule="exact-node-match-uses-bare-symbol",
                            pack="symbol_identity",
                            severity="high",
                            title="Exact node matching collapses qualified symbols",
                            message=(
                                "An exact selection boundary compares node.symbol to a bare target while "
                                "parent_symbol is available, allowing collisions between same-named methods."
                            ),
                            suggested_fix=(
                                "Match against a canonical qualified identity such as Parent.symbol, with "
                                "bare-name matching only when it is provably unambiguous."
                            ),
                            confidence=0.94,
                        )
                    )
        self.generic_visit(node)


def _function_text(source_lines: Sequence[str], node: ast.AST) -> str:
    start = max(1, int(getattr(node, "lineno", 1) or 1))
    end = max(start, int(getattr(node, "end_lineno", start) or start))
    return "\n".join(source_lines[start - 1 : end])


def _graph_semantic_findings(*, file: str, source: str, tree: ast.AST) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = _function_text(lines, node)
        compact = " ".join(body.split())
        name = node.name.lower()
        closure_shape = (
            "closure" in name
            and "max_nodes" in body
            and "queue" in body
            and "visited" in body
            and "admitted_edges" in body
            and ".append(edge.to_dict())" in compact
            and "return visited, admitted_edges" in compact
        )
        endpoint_filter = (
            "edge.src_id in selected" in compact
            and "edge.dst_id in selected" in compact
        )
        if closure_shape and not endpoint_filter:
            findings.append(
                _finding(
                    file=file,
                    node=node,
                    rule="bounded-closure-emits-unselected-edge-endpoints",
                    pack="bounded_graph_integrity",
                    severity="high",
                    title="Bounded closure can emit edges to nodes outside the selected closure",
                    message=(
                        "Edges are appended during traversal before capacity decides whether the other "
                        "endpoint enters the bounded node set. Consumers can receive dependencies they "
                        "cannot inspect in selected nodes or source slices."
                    ),
                    suggested_fix=(
                        "Track queued IDs, finish node admission first, then deterministically emit only "
                        "edges whose source and destination are both selected."
                    ),
                    confidence=0.97,
                )
            )
        bounded_anchor_shape = (
            "bounded" in name
            and "anchor" in name
            and "include_files.update(tests)" in compact
            and "edge.src_id in bounded.nodes" in compact
            and "edge.dst_id in bounded.nodes" in compact
        )
        preserves_test_sources = (
            'edge.edge_type == "test"' in compact
            and "include_ids.add(edge.src_id)" in compact
        )
        if bounded_anchor_shape and not preserves_test_sources:
            findings.append(
                _finding(
                    file=file,
                    node=node,
                    rule="bounded-anchor-drops-test-callable-evidence",
                    pack="test_evidence_preservation",
                    severity="high",
                    title="Bounded audit anchor drops test callable nodes",
                    message=(
                        "The bounded anchor includes test-file modules but not the callable nodes that own "
                        "test edges, so later endpoint filtering removes the test evidence from the audit."
                    ),
                    suggested_fix=(
                        "Before filtering nodes and edges, add the source node of every relevant test edge "
                        "to the bounded node set."
                    ),
                    confidence=0.97,
                )
            )
    return findings


def scan_semantic_review_rules(
    *,
    file: str,
    source: str,
    tree: ast.AST | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic semantic findings for one exact Python source file."""

    parsed = tree if tree is not None else ast.parse(source, filename=file)
    visitor = _SemanticVisitor(file=file, source=source)
    visitor.visit(parsed)
    return [
        *visitor.findings,
        *_graph_semantic_findings(file=file, source=source, tree=parsed),
    ]


def directive_semantic_rule_packs(value: Mapping[str, Any]) -> set[str]:
    """Map a focus directive to deterministic semantic packs that truly execute it."""

    corpus = " ".join(
        [
            str(value.get("name") or ""),
            str(value.get("question") or ""),
            " ".join(str(item) for item in value.get("target_patterns", []) or []),
            " ".join(str(item) for item in value.get("required_evidence", []) or []),
        ]
    ).lower()
    packs: set[str] = set()
    if any(term in corpus for term in ("boolean", "flag", "option type", "strict type")):
        packs.add("strict_input_types")
    if any(term in corpus for term in ("qualified symbol", "symbol identity", "target binding", "same-named method")):
        packs.add("symbol_identity")
    if any(term in corpus for term in ("source inventory", "source digest", "source ingestion", "unreadable file", "decoding")):
        packs.add("source_integrity")
    if any(term in corpus for term in ("bounded closure", "closure edge", "edge endpoint", "graph closure")):
        packs.add("bounded_graph_integrity")
    if any(term in corpus for term in ("test callable", "test evidence", "test edge")):
        packs.add("test_evidence_preservation")
    return packs


__all__ = [
    "SEMANTIC_RULE_PACKS",
    "SEMANTIC_RULES_VERSION",
    "directive_semantic_rule_packs",
    "scan_semantic_review_rules",
]

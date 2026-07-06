"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9d7-[Q-SYS:TOPOLOGICAL_CONTEXT_ANCHOR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Exact Code Topology Before Patch Authority)
DEPENDENCIES: __future__, ast, collections, dataclasses, hashlib, math, pathlib, re, typing
FUNCTIONS: CodeTopoNode, CodeTopoEdge, CodeTopoQuery, CodeTopoResult, CodeTopoContextPacket, CodeTopoAnchor, index_python_source, build_from_files, render_builder_context
SYNOPSIS: Stdlib-only hybrid code-topology anchor for Coding Arena localization. Exact AST/source spans are patch authority; deterministic sketch similarity is advisory ranking only.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping


ANCHOR_VERSION = "AURA_TOPOLOGICAL_CONTEXT_ANCHOR_V1"
APPROX_WARNING = "approximate_similarity_not_patch_evidence"
PATCH_AUTHORITY_POLICY = "exact_source_spans_and_hashes_only"
SKETCH_DIMENSIONS = 256
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*", re.ASCII)
_LOCALIZE_STOPWORDS = {
    "and",
    "are",
    "builder",
    "code",
    "council",
    "error",
    "file",
    "fix",
    "for",
    "from",
    "issue",
    "patch",
    "symbol",
    "target",
    "test",
    "that",
    "the",
    "this",
    "with",
}

KNOWN_EXTERNAL_ROOTS = frozenset(
    {
        "anthropic",
        "httpx",
        "openai",
        "requests",
        "sqlite3",
        "subprocess",
    }
)

_BUILTIN_CALLS = frozenset(
    {
        "abs",
        "all",
        "any",
        "bool",
        "bytes",
        "dict",
        "enumerate",
        "float",
        "getattr",
        "hasattr",
        "int",
        "isinstance",
        "issubclass",
        "len",
        "list",
        "max",
        "min",
        "open",
        "print",
        "range",
        "round",
        "set",
        "setattr",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "zip",
    }
)


@dataclass
class CodeTopoNode:
    node_id: str
    file_path: str
    symbol: str
    kind: str
    start_line: int
    end_line: int
    source_hash: str
    imports: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    parent_symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodeTopoEdge:
    src_id: str
    dst_id: str
    edge_type: str
    evidence: str
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodeTopoQuery:
    query_type: str
    value: str
    radius: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodeTopoResult:
    query: CodeTopoQuery
    exact_hits: list[CodeTopoNode] = field(default_factory=list)
    ranked_neighbors: list[tuple[CodeTopoNode, float]] = field(default_factory=list)
    external_calls: list[dict[str, Any]] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    grounding_ok: bool = False
    route_diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "exact_hits": [node.to_dict() for node in self.exact_hits],
            "ranked_neighbors": [
                {"node": node.to_dict(), "score": score} for node, score in self.ranked_neighbors
            ],
            "external_calls": self.external_calls,
            "tests": self.tests,
            "warnings": self.warnings,
            "grounding_ok": self.grounding_ok,
            "route_diagnostics": self.route_diagnostics,
        }


@dataclass
class CodeTopoContextPacket:
    target_nodes: list[CodeTopoNode] = field(default_factory=list)
    source_spans: list[dict[str, Any]] = field(default_factory=list)
    neighbor_summaries: list[dict[str, Any]] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    hashes: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    token_estimate: int = 0
    route_diagnostics: dict[str, Any] = field(default_factory=dict)
    safety_policy: str = PATCH_AUTHORITY_POLICY

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_nodes": [node.to_dict() for node in self.target_nodes],
            "source_spans": self.source_spans,
            "neighbor_summaries": self.neighbor_summaries,
            "tests": self.tests,
            "hashes": self.hashes,
            "warnings": self.warnings,
            "token_estimate": self.token_estimate,
            "route_diagnostics": self.route_diagnostics,
            "safety_policy": self.safety_policy,
        }


@dataclass
class _IndexedSource:
    nodes: list[CodeTopoNode]
    warnings: list[str]
    imports: list[str]
    alias_map: dict[str, str]


class _SymbolIndexer(ast.NodeVisitor):
    def __init__(
        self,
        *,
        file_path: str,
        source: str,
        imports: list[str],
        alias_map: dict[str, str],
    ) -> None:
        self.file_path = _normalize_path(file_path)
        self.source = source
        self.lines = source.splitlines()
        self.file_hash = _hash_text(source)
        self.imports = imports
        self.alias_map = alias_map
        self.nodes: list[CodeTopoNode] = []
        self.parent_stack: list[tuple[str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._add_node(node, kind="class")
        self.parent_stack.append((node.name, "class"))
        self.generic_visit(node)
        self.parent_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._add_function(node, async_def=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._add_function(node, async_def=True)

    def _add_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, async_def: bool) -> None:
        parent = self.parent_stack[-1][0] if self.parent_stack else None
        if parent and self.parent_stack[-1][1] == "class":
            kind = "async_method" if async_def else "method"
        elif parent:
            kind = "async_nested_function" if async_def else "nested_function"
        else:
            kind = "async_function" if async_def else "function"
        self._add_node(node, kind=kind)
        self.parent_stack.append((node.name, "function"))
        self.generic_visit(node)
        self.parent_stack.pop()

    def _add_node(self, node: ast.AST, *, kind: str) -> None:
        name = str(getattr(node, "name", ""))
        if not name:
            return
        start = int(getattr(node, "lineno", 0) or 0)
        end = int(getattr(node, "end_lineno", start) or start)
        span_text = _source_slice(self.lines, start, end)
        calls = _collect_calls(node)
        decorators = _collect_decorators(node)
        assignments = _collect_assignments(node)
        parent_symbol = self.parent_stack[-1][0] if self.parent_stack else None
        node_id = _node_id(
            self.file_path,
            kind,
            name,
            start,
            end,
            parent_symbol=parent_symbol,
        )
        self.nodes.append(
            CodeTopoNode(
                node_id=node_id,
                file_path=self.file_path,
                symbol=name,
                kind=kind,
                start_line=start,
                end_line=end,
                source_hash=_hash_text(span_text),
                imports=list(self.imports),
                calls=_unique(call["name"] for call in calls),
                decorators=decorators,
                parent_symbol=parent_symbol,
                metadata={
                    "assignments": assignments,
                    "call_details": calls,
                    "file_source_hash": self.file_hash,
                    "source_line_count": len(self.lines),
                    "alias_map": dict(self.alias_map),
                },
            )
        )


@dataclass
class CodeTopoAnchor:
    nodes: dict[str, CodeTopoNode] = field(default_factory=dict)
    symbol_index: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    edges: list[CodeTopoEdge] = field(default_factory=list)
    outgoing: dict[str, list[CodeTopoEdge]] = field(default_factory=lambda: defaultdict(list))
    incoming: dict[str, list[CodeTopoEdge]] = field(default_factory=lambda: defaultdict(list))
    file_hashes: dict[str, str] = field(default_factory=dict)
    source_texts: dict[str, str] = field(default_factory=dict)
    module_nodes: dict[str, str] = field(default_factory=dict)
    import_aliases: dict[str, dict[str, str]] = field(default_factory=dict)
    call_records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def index_python_source(file_path: str, source: str) -> list[CodeTopoNode]:
        return index_python_source(file_path, source)

    @classmethod
    def build_from_files(cls, files: dict[str, str]) -> CodeTopoAnchor:
        anchor = cls()
        for raw_path, source in sorted(files.items(), key=lambda item: _normalize_path(item[0])):
            file_path = _normalize_path(raw_path)
            indexed = _index_python_source(file_path, source or "")
            anchor.warnings.extend(indexed.warnings)
            anchor.source_texts[file_path] = source or ""
            anchor.file_hashes[file_path] = _hash_text(source or "")
            anchor.import_aliases[file_path] = indexed.alias_map
            for node in indexed.nodes:
                anchor.nodes[node.node_id] = node
                if node.kind == "module":
                    anchor.module_nodes[file_path] = node.node_id
                else:
                    anchor.symbol_index.setdefault(node.symbol, []).append(node.node_id)
                for call in node.metadata.get("call_details", []) or []:
                    call_record = {
                        "node_id": node.node_id,
                        "caller_symbol": node.symbol,
                        "file_path": node.file_path,
                        "span": [node.start_line, node.end_line],
                        "source_hash": node.source_hash,
                        **call,
                    }
                    external_name = _external_call_name(str(call.get("name", "")), indexed.alias_map)
                    if external_name:
                        call_record["external_name"] = external_name
                    anchor.call_records.append(call_record)
        anchor._build_edges()
        anchor.metadata = {
            "version": ANCHOR_VERSION,
            "node_count": len(anchor.nodes),
            "edge_count": len(anchor.edges),
            "warning_count": len(anchor.warnings),
            "safety_policy": PATCH_AUTHORITY_POLICY,
        }
        return anchor

    def lookup_symbol(self, symbol: str) -> CodeTopoResult:
        query = CodeTopoQuery(query_type="symbol", value=str(symbol or ""))
        hit_ids = list(self.symbol_index.get(query.value, []))
        exact_hits = [self.nodes[node_id] for node_id in hit_ids if node_id in self.nodes]
        warnings: list[str] = []
        ranked: list[tuple[CodeTopoNode, float]] = []
        if not exact_hits:
            warnings.append("target_symbol_unresolved")
            ranked = self.rank_affinity(query.value, self._patchable_nodes())[:5]
            if ranked:
                warnings.append(APPROX_WARNING)
        result = CodeTopoResult(
            query=query,
            exact_hits=exact_hits,
            ranked_neighbors=ranked,
            tests=self._tests_for_nodes([node.node_id for node in exact_hits]),
            warnings=warnings,
            grounding_ok=bool(exact_hits),
        )
        result.route_diagnostics = self.explain_grounding(result)
        return result

    def lookup_external_call(self, name_or_pattern: str) -> CodeTopoResult:
        query = CodeTopoQuery(query_type="external_call", value=str(name_or_pattern or ""))
        external_calls: list[dict[str, Any]] = []
        hit_node_ids: list[str] = []
        for record in self.call_records:
            raw_name = str(record.get("name", ""))
            external_name = str(record.get("external_name", ""))
            if not external_name and not query.value:
                continue
            if external_name and _call_pattern_matches(query.value, external_name, raw_name):
                external_calls.append(self._external_evidence(record))
                hit_node_ids.append(str(record["node_id"]))
            elif query.value and _call_pattern_matches(query.value, raw_name, raw_name):
                external_calls.append(self._external_evidence(record))
                hit_node_ids.append(str(record["node_id"]))
        exact_hits = [self.nodes[node_id] for node_id in _unique(hit_node_ids) if node_id in self.nodes]
        warnings = [] if external_calls else ["external_call_unresolved"]
        result = CodeTopoResult(
            query=query,
            exact_hits=exact_hits,
            external_calls=external_calls,
            tests=self._tests_for_nodes(hit_node_ids),
            warnings=warnings,
            grounding_ok=bool(external_calls),
        )
        result.route_diagnostics = self.explain_grounding(result)
        return result

    def callers_of(self, symbol: str) -> CodeTopoResult:
        query = CodeTopoQuery(query_type="callers", value=str(symbol or ""))
        target_ids = list(self.symbol_index.get(query.value, []))
        targets = [self.nodes[node_id] for node_id in target_ids if node_id in self.nodes]
        callers: list[tuple[CodeTopoNode, float]] = []
        for target_id in target_ids:
            for edge in self.incoming.get(target_id, []):
                if edge.edge_type == "call" and edge.src_id in self.nodes:
                    callers.append((self.nodes[edge.src_id], edge.confidence))
        warnings = [] if targets else ["target_symbol_unresolved"]
        if targets and not callers:
            warnings.append("callers_not_found")
        result = CodeTopoResult(
            query=query,
            exact_hits=targets,
            ranked_neighbors=_dedupe_ranked(callers),
            tests=self._tests_for_nodes(target_ids),
            warnings=warnings,
            grounding_ok=bool(targets),
        )
        result.route_diagnostics = self.explain_grounding(result)
        return result

    def callees_of(self, symbol: str) -> CodeTopoResult:
        query = CodeTopoQuery(query_type="callees", value=str(symbol or ""))
        target_ids = list(self.symbol_index.get(query.value, []))
        targets = [self.nodes[node_id] for node_id in target_ids if node_id in self.nodes]
        callees: list[tuple[CodeTopoNode, float]] = []
        for source_id in target_ids:
            for edge in self.outgoing.get(source_id, []):
                if edge.edge_type == "call" and edge.dst_id in self.nodes:
                    callees.append((self.nodes[edge.dst_id], edge.confidence))
        warnings = [] if targets else ["target_symbol_unresolved"]
        if targets and not callees:
            warnings.append("callees_not_found")
        result = CodeTopoResult(
            query=query,
            exact_hits=targets,
            ranked_neighbors=_dedupe_ranked(callees),
            tests=self._tests_for_nodes(target_ids),
            warnings=warnings,
            grounding_ok=bool(targets),
        )
        result.route_diagnostics = self.explain_grounding(result)
        return result

    def nearest_context(self, symbol: str, radius: int = 1) -> CodeTopoContextPacket:
        radius = max(0, min(3, int(radius)))
        lookup = self.lookup_symbol(symbol)
        if not lookup.exact_hits:
            return CodeTopoContextPacket(
                warnings=list(dict.fromkeys([*lookup.warnings, *self.warnings])),
                route_diagnostics=lookup.route_diagnostics,
            )

        start_ids = [node.node_id for node in lookup.exact_hits]
        visited: set[str] = set()
        neighbor_edge: dict[str, CodeTopoEdge] = {}
        queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in start_ids)
        while queue and len(visited) < 24:
            node_id, distance = queue.popleft()
            if node_id in visited or distance > radius:
                continue
            visited.add(node_id)
            if distance == radius:
                continue
            for edge in [*self.outgoing.get(node_id, []), *self.incoming.get(node_id, [])]:
                other = edge.dst_id if edge.src_id == node_id else edge.src_id
                if other not in self.nodes or other in visited:
                    continue
                neighbor_edge.setdefault(other, edge)
                queue.append((other, distance + 1))

        target_set = set(start_ids)
        source_spans: list[dict[str, Any]] = []
        hashes: dict[str, str] = {}
        token_estimate = 0
        for node_id in [*start_ids, *sorted(visited - target_set)]:
            node = self.nodes.get(node_id)
            if not node:
                continue
            span = self._source_span_for_node(node, role="target" if node_id in target_set else "neighbor")
            if span:
                source_spans.append(span)
                token_estimate += _estimate_tokens(str(span.get("source", "")))
            hashes[node.node_id] = node.source_hash
            hashes.setdefault(node.file_path, self.file_hashes.get(node.file_path, ""))

        neighbor_summaries = []
        for node_id in sorted(visited - target_set):
            node = self.nodes[node_id]
            edge = neighbor_edge.get(node_id)
            neighbor_summaries.append(
                {
                    "node_id": node.node_id,
                    "file_path": node.file_path,
                    "symbol": node.symbol,
                    "kind": node.kind,
                    "span": [node.start_line, node.end_line],
                    "source_hash": node.source_hash,
                    "edge_type": edge.edge_type if edge else "neighbor",
                    "edge_evidence": edge.evidence if edge else "",
                    "confidence": edge.confidence if edge else 1.0,
                }
            )
        tests = self._tests_for_nodes(start_ids)
        diagnostics = {
            "route": "BUILDER_PATCH" if tests else "TEST_GAP_FILL",
            "reason": "exact_symbol_grounded" if tests else "exact_symbol_grounded_missing_tests",
            "patch_authority": PATCH_AUTHORITY_POLICY,
            "vsa_patch_authority": False,
        }
        return CodeTopoContextPacket(
            target_nodes=lookup.exact_hits,
            source_spans=source_spans,
            neighbor_summaries=neighbor_summaries[:16],
            tests=tests,
            hashes={key: value for key, value in hashes.items() if value},
            warnings=list(dict.fromkeys([*lookup.warnings, *self.warnings])),
            token_estimate=token_estimate,
            route_diagnostics=diagnostics,
        )

    def render_builder_context(self, packet: CodeTopoContextPacket) -> str:
        return render_builder_context(packet)

    def rank_affinity(
        self,
        query: str,
        candidates: list[CodeTopoNode],
    ) -> list[tuple[CodeTopoNode, float]]:
        query_vec = _sketch(str(query or ""))
        scored: list[tuple[CodeTopoNode, float]] = []
        for node in candidates:
            score = _cosine(query_vec, _sketch(_node_search_text(node)))
            scored.append((node, round(score, 6)))
        return sorted(scored, key=lambda item: (-item[1], item[0].file_path, item[0].symbol))

    def explain_grounding(self, result: CodeTopoResult) -> dict[str, Any]:
        warnings = list(dict.fromkeys([*self.warnings, *result.warnings]))
        reasons = list(warnings)
        route = "BUILDER_PATCH"
        if result.query.query_type == "affinity":
            route = "MUSIC_RANK_ONLY"
            reasons.append(APPROX_WARNING)
        elif not result.exact_hits and not result.external_calls:
            route = "LOCALIZE_FIRST"
            if "target_symbol_unresolved" not in reasons and result.query.query_type != "external_call":
                reasons.append("target_symbol_unresolved")
        elif result.query.query_type in {"symbol", "callers", "callees"} and not result.tests:
            route = "TEST_GAP_FILL"
            reasons.append("missing_tests_or_verifier_evidence")
        if any("syntax_error" in item for item in warnings):
            route = "BLOCKED_WITH_REASON" if not result.grounding_ok else route
        if APPROX_WARNING in warnings and not result.exact_hits and not result.external_calls:
            route = "MUSIC_RANK_ONLY"
        return {
            "version": ANCHOR_VERSION,
            "query_type": result.query.query_type,
            "query_value": result.query.value,
            "exact_hit_count": len(result.exact_hits),
            "external_call_count": len(result.external_calls),
            "test_count": len(result.tests),
            "grounding_ok": bool(result.grounding_ok),
            "route": route,
            "reasons": list(dict.fromkeys(reasons)),
            "patch_authority": PATCH_AUTHORITY_POLICY,
            "vsa_patch_authority": False,
        }

    def _build_edges(self) -> None:
        edge_keys: set[tuple[str, str, str, str]] = set()

        def add_edge(edge: CodeTopoEdge) -> None:
            key = (edge.src_id, edge.dst_id, edge.edge_type, edge.evidence)
            if key in edge_keys:
                return
            edge_keys.add(key)
            self.edges.append(edge)
            self.outgoing[edge.src_id].append(edge)
            self.incoming[edge.dst_id].append(edge)

        local_modules = {Path(path).stem: path for path in self.source_texts}
        for file_path, module_id in self.module_nodes.items():
            alias_map = self.import_aliases.get(file_path, {})
            imported_roots = _unique(_root_name(value) for value in alias_map.values())
            for root in imported_roots:
                imported_file = local_modules.get(root)
                if not imported_file or imported_file == file_path:
                    continue
                target_module = self.module_nodes.get(imported_file)
                if target_module:
                    add_edge(
                        CodeTopoEdge(
                            src_id=module_id,
                            dst_id=target_module,
                            edge_type="import",
                            evidence=f"{file_path} imports {root}",
                            confidence=1.0,
                        )
                    )

        for node in list(self.nodes.values()):
            if node.kind == "module":
                continue
            for call in node.metadata.get("call_details", []) or []:
                raw_call = str(call.get("name", ""))
                line = int(call.get("line", node.start_line) or node.start_line)
                targets = self._resolve_call_targets(raw_call, node)
                for target_id, confidence in targets:
                    add_edge(
                        CodeTopoEdge(
                            src_id=node.node_id,
                            dst_id=target_id,
                            edge_type="call",
                            evidence=f"{node.file_path}:{line} calls {raw_call}",
                            confidence=confidence,
                        )
                    )

        for file_path, module_id in self.module_nodes.items():
            if not _is_test_file(file_path):
                continue
            imported_targets = [
                edge.dst_id for edge in self.outgoing.get(module_id, []) if edge.edge_type == "import"
            ]
            for target_module in imported_targets:
                add_edge(
                    CodeTopoEdge(
                        src_id=module_id,
                        dst_id=target_module,
                        edge_type="test",
                        evidence=f"{file_path} imports tested module",
                        confidence=0.9,
                    )
                )
            convention_target = _test_convention_target(file_path, self.module_nodes)
            if convention_target:
                add_edge(
                    CodeTopoEdge(
                        src_id=module_id,
                        dst_id=convention_target,
                        edge_type="test",
                        evidence=f"{file_path} follows test_<module>.py convention",
                        confidence=1.0,
                    )
                )

    def _resolve_call_targets(self, raw_call: str, caller: CodeTopoNode) -> list[tuple[str, float]]:
        if not raw_call:
            return []
        parts = raw_call.split(".")
        names = _unique([raw_call, parts[-1]])
        if parts[0] in {"self", "cls"} and len(parts) > 1:
            names.insert(0, parts[-1])
        class_method_match: list[str] = []
        if len(parts) >= 2:
            parent, method = parts[-2], parts[-1]
            for node_id in self.symbol_index.get(method, []):
                node = self.nodes[node_id]
                if node.parent_symbol == parent:
                    class_method_match.append(node_id)
        if class_method_match:
            return [(node_id, 0.95) for node_id in _unique(class_method_match)]

        candidates: list[str] = []
        for name in names:
            candidates.extend(self.symbol_index.get(name, []))
        candidates = _unique(candidates)
        same_file = [node_id for node_id in candidates if self.nodes[node_id].file_path == caller.file_path]
        if len(same_file) == 1:
            return [(same_file[0], 1.0)]
        if caller.parent_symbol:
            same_parent = [
                node_id
                for node_id in same_file
                if self.nodes[node_id].parent_symbol == caller.parent_symbol
            ]
            if len(same_parent) == 1:
                return [(same_parent[0], 1.0)]
        if len(candidates) == 1:
            return [(candidates[0], 0.85)]
        return []

    def _tests_for_nodes(self, node_ids: Iterable[str]) -> list[str]:
        target_files = {
            self.nodes[node_id].file_path
            for node_id in node_ids
            if node_id in self.nodes
        }
        if not target_files:
            return []
        test_files: set[str] = set()
        target_module_ids = {self.module_nodes.get(file_path) for file_path in target_files}
        target_module_ids.discard(None)
        for edge in self.edges:
            if edge.edge_type != "test":
                continue
            if edge.dst_id in target_module_ids or (
                edge.dst_id in self.nodes and self.nodes[edge.dst_id].file_path in target_files
            ):
                if edge.src_id in self.nodes:
                    test_files.add(self.nodes[edge.src_id].file_path)
        for file_path in target_files:
            direct = _direct_test_path(file_path, self.source_texts)
            if direct:
                test_files.add(direct)
        return sorted(test_files)

    def _source_span_for_node(self, node: CodeTopoNode, *, role: str) -> dict[str, Any]:
        source = self.source_texts.get(node.file_path, "")
        lines = source.splitlines()
        text = _source_slice(lines, node.start_line, node.end_line)
        return {
            "role": role,
            "node_id": node.node_id,
            "file_path": node.file_path,
            "symbol": node.symbol,
            "kind": node.kind,
            "start_line": node.start_line,
            "end_line": node.end_line,
            "source_hash": node.source_hash,
            "file_source_hash": self.file_hashes.get(node.file_path, ""),
            "source": text,
        }

    def _external_evidence(self, record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "caller_node_id": str(record.get("node_id", "")),
            "caller_symbol": str(record.get("caller_symbol", "")),
            "file_path": str(record.get("file_path", "")),
            "call": str(record.get("name", "")),
            "resolved_call": str(record.get("external_name") or record.get("name", "")),
            "line": int(record.get("line", 0) or 0),
            "caller_span": list(record.get("span", []) or []),
            "source_hash": str(record.get("source_hash", "")),
        }

    def _patchable_nodes(self) -> list[CodeTopoNode]:
        return [node for node in self.nodes.values() if node.kind != "module"]


def index_python_source(file_path: str, source: str) -> list[CodeTopoNode]:
    """Index one Python source string into exact topology nodes."""
    return _index_python_source(file_path, source).nodes


def build_from_files(files: dict[str, str]) -> CodeTopoAnchor:
    return CodeTopoAnchor.build_from_files(files)


def render_builder_context(packet: CodeTopoContextPacket) -> str:
    lines = [
        "=== TOPOLOGICAL CONTEXT ANCHOR ===",
        f"version: {ANCHOR_VERSION}",
        f"safety_policy: {packet.safety_policy}",
        "patch_authority: exact source spans with source_hash only",
        "vsa_similarity: advisory ranking only; never patch evidence",
    ]
    if packet.route_diagnostics:
        lines.append(f"route: {packet.route_diagnostics.get('route', '')}")
        reasons = packet.route_diagnostics.get("reasons") or packet.route_diagnostics.get("reason")
        if reasons:
            lines.append("route_reasons: " + "; ".join(str(item) for item in _as_list(reasons)))
    if packet.warnings:
        lines.append("warnings: " + "; ".join(str(item) for item in packet.warnings))
    if packet.hashes:
        lines.append("--- hashes ---")
        for key in sorted(packet.hashes):
            lines.append(f"{key}: {packet.hashes[key]}")
    if packet.source_spans:
        lines.append("--- exact_source_spans ---")
        for span in packet.source_spans:
            lines.append(
                "exact_span: "
                f"{span.get('file_path')}:{span.get('start_line')}-{span.get('end_line')} "
                f"symbol={span.get('symbol')} kind={span.get('kind')} "
                f"source_hash={span.get('source_hash')}"
            )
            source = str(span.get("source", ""))
            if source:
                lines.append(source)
                lines.append("--- end_exact_span ---")
    if packet.neighbor_summaries:
        lines.append("--- one_hop_neighbors ---")
        for neighbor in packet.neighbor_summaries:
            lines.append(
                f"{neighbor.get('edge_type')} {neighbor.get('file_path')}:{neighbor.get('span')} "
                f"{neighbor.get('symbol')} confidence={neighbor.get('confidence')}"
            )
    if packet.tests:
        lines.append("--- test_neighbors ---")
        for test in packet.tests:
            lines.append(str(test))
    lines.append(f"token_estimate: {packet.token_estimate}")
    lines.append("=== END TOPOLOGICAL CONTEXT ANCHOR ===")
    return "\n".join(lines)


def _index_python_source(file_path: str, source: str) -> _IndexedSource:
    normalized = _normalize_path(file_path)
    try:
        tree = ast.parse(source or "", filename=normalized)
    except SyntaxError as exc:
        warning = f"syntax_error:{normalized}:line={exc.lineno or 0}:offset={exc.offset or 0}:{_safe_msg(exc.msg)}"
        return _IndexedSource(nodes=[], warnings=[warning], imports=[], alias_map={})
    imports, alias_map = _collect_imports(tree)
    lines = (source or "").splitlines()
    file_hash = _hash_text(source or "")
    module_node = CodeTopoNode(
        node_id=_node_id(normalized, "module", "<module>", 1, max(1, len(lines))),
        file_path=normalized,
        symbol="<module>",
        kind="module",
        start_line=1,
        end_line=max(1, len(lines)),
        source_hash=file_hash,
        imports=list(imports),
        calls=[],
        decorators=[],
        parent_symbol=None,
        metadata={
            "file_source_hash": file_hash,
            "source_line_count": len(lines),
            "alias_map": dict(alias_map),
        },
    )
    indexer = _SymbolIndexer(
        file_path=normalized,
        source=source or "",
        imports=list(imports),
        alias_map=dict(alias_map),
    )
    indexer.visit(tree)
    return _IndexedSource(nodes=[module_node, *indexer.nodes], warnings=[], imports=list(imports), alias_map=dict(alias_map))


def _collect_imports(tree: ast.AST) -> tuple[list[str], dict[str, str]]:
    imports: list[str] = []
    alias_map: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
                visible = alias.asname or alias.name.split(".", 1)[0]
                alias_map[visible] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = "." * int(node.level or 0) + (node.module or "")
            names = []
            for alias in node.names:
                names.append(alias.name + (f" as {alias.asname}" if alias.asname else ""))
                visible = alias.asname or alias.name
                alias_map[visible] = f"{module}.{alias.name}".strip(".")
            imports.append(f"from {module} import {', '.join(names)}")
    return _unique(imports), alias_map


def _collect_decorators(node: ast.AST) -> list[str]:
    decorators = getattr(node, "decorator_list", []) or []
    return _unique(_expr_name(item) for item in decorators if _expr_name(item))


def _collect_calls(node: ast.AST) -> list[dict[str, Any]]:
    class CallCollector(ast.NodeVisitor):
        def __init__(self, root: ast.AST) -> None:
            self.root = root
            self.calls: list[dict[str, Any]] = []

        def visit_FunctionDef(self, child: ast.FunctionDef) -> Any:
            if child is not self.root:
                return
            self.generic_visit(child)

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> Any:
            if child is not self.root:
                return
            self.generic_visit(child)

        def visit_ClassDef(self, child: ast.ClassDef) -> Any:
            if child is not self.root:
                return
            self.generic_visit(child)

        def visit_Call(self, child: ast.Call) -> Any:
            name = _call_name(child.func)
            if name and name.split(".")[-1] not in _BUILTIN_CALLS:
                self.calls.append(
                    {
                        "name": name,
                        "line": int(getattr(child, "lineno", 0) or 0),
                    }
                )
            self.generic_visit(child)

    collector = CallCollector(node)
    collector.visit(node)
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in collector.calls:
        key = (str(item.get("name", "")), int(item.get("line", 0) or 0))
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped


def _collect_assignments(node: ast.AST) -> list[str]:
    assignments: list[str] = []
    for child in ast.walk(node):
        if child is not node and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(child, ast.Assign):
            assignments.extend(_expr_name(target) for target in child.targets if _expr_name(target))
        elif isinstance(child, ast.AnnAssign):
            name = _expr_name(child.target)
            if name:
                assignments.append(name)
        elif isinstance(child, ast.AugAssign):
            name = _expr_name(child.target)
            if name:
                assignments.append(name)
    return _unique(assignments)


def _call_name(node: ast.AST) -> str:
    return _expr_name(node)


def _expr_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _expr_name(node.func)
    if isinstance(node, ast.Subscript):
        return _expr_name(node.value)
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Tuple):
        return ",".join(_expr_name(item) for item in node.elts)
    return ""


def _external_call_name(raw_call: str, alias_map: Mapping[str, str]) -> str | None:
    if not raw_call:
        return None
    parts = raw_call.split(".")
    root = parts[0]
    mapped = str(alias_map.get(root, root))
    mapped_parts = mapped.split(".")
    normalized_parts = [*mapped_parts, *parts[1:]]
    if normalized_parts and normalized_parts[0] in KNOWN_EXTERNAL_ROOTS:
        return ".".join(normalized_parts)
    return None


def _call_pattern_matches(pattern: str, resolved_name: str, raw_name: str) -> bool:
    token = str(pattern or "").strip().lower()
    haystacks = [str(resolved_name or "").lower(), str(raw_name or "").lower()]
    if not token:
        return bool(resolved_name)
    if "*" in token:
        regex = "^" + re.escape(token).replace("\\*", ".*") + "$"
        return any(re.match(regex, haystack) for haystack in haystacks)
    return any(token in haystack for haystack in haystacks)


def _node_id(
    file_path: str,
    kind: str,
    symbol: str,
    start_line: int,
    end_line: int,
    *,
    parent_symbol: str | None = None,
) -> str:
    parent = f"{parent_symbol}." if parent_symbol else ""
    material = f"{_normalize_path(file_path)}:{kind}:{parent}{symbol}:{start_line}:{end_line}"
    digest = hashlib.blake2b(material.encode("utf-8", errors="replace"), digest_size=8).hexdigest()
    return f"{_normalize_path(file_path)}#{kind}:{parent}{symbol}:{digest}"


def _source_slice(lines: list[str], start_line: int, end_line: int) -> str:
    if start_line <= 0 or end_line <= 0 or not lines:
        return ""
    start = max(1, start_line)
    end = min(len(lines), max(start, end_line))
    return "\n".join(lines[start - 1 : end])


def _node_search_text(node: CodeTopoNode) -> str:
    metadata = node.metadata or {}
    return " ".join(
        str(item)
        for item in (
            node.file_path,
            node.symbol,
            node.kind,
            node.parent_symbol or "",
            " ".join(node.imports),
            " ".join(node.calls),
            " ".join(node.decorators),
            " ".join(metadata.get("assignments", []) or []),
        )
        if item
    )


def _sketch(text: str, *, dimensions: int = SKETCH_DIMENSIONS) -> tuple[int, ...]:
    dims = max(16, int(dimensions))
    vector = [0] * dims
    tokens = [token.lower() for token in _TOKEN_RE.findall(str(text or ""))]
    if not tokens:
        tokens = ["empty"]
    for position, token in enumerate(tokens):
        digest = hashlib.blake2b(f"{position}:{token}".encode("utf-8", errors="replace"), digest_size=16).digest()
        bucket = int.from_bytes(digest[:4], "little") % dims
        sign = 1 if digest[4] & 1 else -1
        weight = 1 + min(3, len(token) // 8)
        vector[bucket] += sign * weight
    return tuple(vector)


def _cosine(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _estimate_tokens(text: str) -> int:
    tokens = _TOKEN_RE.findall(text or "")
    return max(0, len(tokens))


def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()


def _normalize_path(path: str | Path) -> str:
    normalized = str(path).replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _root_name(value: str) -> str:
    return str(value or "").split(".", 1)[0]


def _is_test_file(path: str) -> bool:
    parts = _normalize_path(path).split("/")
    name = parts[-1]
    return name.startswith("test_") or any(part == "tests" for part in parts)


def _test_convention_target(test_path: str, module_nodes: Mapping[str, str]) -> str | None:
    normalized = _normalize_path(test_path)
    path = Path(normalized)
    name = path.name
    if not name.startswith("test_"):
        return None
    target_name = name.removeprefix("test_")
    candidate = (path.parent / target_name).as_posix() if str(path.parent) != "." else target_name
    if candidate in module_nodes:
        return module_nodes[candidate]
    basename_matches = [node_id for file_path, node_id in module_nodes.items() if Path(file_path).name == target_name]
    return sorted(basename_matches)[0] if basename_matches else None


def _direct_test_path(file_path: str, sources: Mapping[str, str]) -> str | None:
    path = Path(_normalize_path(file_path))
    candidates = [
        (path.parent / f"test_{path.name}").as_posix() if str(path.parent) != "." else f"test_{path.name}",
        f"tests/test_{path.name}",
    ]
    for candidate in candidates:
        if candidate in sources:
            return candidate
    return None


def _unique(values: Iterable[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for value in values:
        if value in (None, ""):
            continue
        if value in seen:
            continue
        out.append(value)
        seen.add(value)
    return out


def _dedupe_ranked(items: list[tuple[CodeTopoNode, float]]) -> list[tuple[CodeTopoNode, float]]:
    best: dict[str, tuple[CodeTopoNode, float]] = {}
    for node, score in items:
        existing = best.get(node.node_id)
        if existing is None or score > existing[1]:
            best[node.node_id] = (node, score)
    return sorted(best.values(), key=lambda item: (-item[1], item[0].file_path, item[0].symbol))


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_msg(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_ .:-]", "_", str(value or "")).strip()


def query_terms(text: str) -> list[str]:
    return [
        token
        for token in _unique(item.lower() for item in _TOKEN_RE.findall(text or ""))
        if len(token) > 2 and token not in _LOCALIZE_STOPWORDS
    ]

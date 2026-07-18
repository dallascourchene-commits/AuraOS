"""Aura Emergent Evidence Spine.

The spine composes Aura's canonical owners instead of creating another planner:

* Capability Connectome / Capability Resolver choose the relevant Aura-native
  capability path.
* CodeTopoAnchor enumerates every atomic Python callable and binds exact source
  spans, hashes, calls, callers, imports, and tests.
* Emergent Capability Auditor runs only over the bounded atomic closure.
* Coding Research Lane plans advisory arXiv/research queries for unresolved gaps.
* Arena projections provide bounded evidence to Coding Arena, Coding Waboose,
  Human Agent, and external Agent Bridge clients.

All outputs are read-only and advisory until exact verifier evidence and human
review authorize a separate patch workflow.
"""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tokenize
from typing import Any

from aura_capability_connectome import build_capability_connectome
from aura_capability_connectome_v2 import enrich_connectome
from aura_capability_resolver_v2 import resolve_capabilities
from aura_coding_research_lane import (
    build_research_evidence_packet,
    plan_arxiv_forager_query,
)
from aura_emergent_capability_auditor import audit_emergent_capabilities
from aura_repo_localizer import EXCLUDE_DIRS
from aura_topological_context_anchor import (
    PATCH_AUTHORITY_POLICY,
    CodeTopoAnchor,
    CodeTopoNode,
)

EMERGENT_EVIDENCE_SPINE_VERSION = "AURA_EMERGENT_EVIDENCE_SPINE_V1"
ATOMIC_INVENTORY_VERSION = "AURA_ATOMIC_FUNCTION_INVENTORY_V1"
PATCH_AUTHORITY = PATCH_AUTHORITY_POLICY
VSA_PATCH_AUTHORITY = False
SUPPORTED_ARENAS = frozenset(
    {"coding_arena", "coding_waboose", "human_agent", "agent_bridge", "research"}
)
ATOMIC_KINDS = frozenset(
    {
        "function",
        "async_function",
        "method",
        "async_method",
        "nested_function",
        "async_nested_function",
    }
)
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", re.ASCII)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "code",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "use",
        "with",
    }
)


def _boolean(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError("expected a boolean")


@dataclass(frozen=True)
class EmergentEvidenceRequest:
    objective: str
    target_files: tuple[str, ...] = ()
    target_symbols: tuple[str, ...] = ()
    target_arena: str = "agent_bridge"
    radius: int = 1
    max_atomic_nodes: int = 48
    max_source_lines: int = 120
    include_source: bool = True
    include_future: bool = True
    include_research_plan: bool = True
    include_offline_research: bool = True

    @classmethod
    def from_value(cls, value: Mapping[str, Any] | EmergentEvidenceRequest) -> EmergentEvidenceRequest:
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise ValueError("emergent evidence request must be an object")
        objective = str(value.get("objective") or "").strip()
        if not objective:
            raise ValueError("objective is required")
        target_arena = str(value.get("target_arena") or "agent_bridge").strip().lower()
        if target_arena not in SUPPORTED_ARENAS:
            raise ValueError(f"unsupported target_arena: {target_arena}")
        return cls(
            objective=objective,
            target_files=_repo_paths(value.get("target_files") or ()),
            target_symbols=_strings(value.get("target_symbols") or ()),
            target_arena=target_arena,
            radius=max(0, min(3, int(value.get("radius", 1)))),
            max_atomic_nodes=max(1, min(200, int(value.get("max_atomic_nodes", 48)))),
            max_source_lines=max(8, min(300, int(value.get("max_source_lines", 120)))),
            include_source=_boolean(value.get("include_source"), default=True),
            include_future=_boolean(value.get("include_future"), default=True),
            include_research_plan=_boolean(
                value.get("include_research_plan"), default=True
            ),
            include_offline_research=_boolean(
                value.get("include_offline_research"), default=True
            ),
        )


class AuraEmergentEvidenceSpine:
    """Connectome-routed, atomic-function-grounded emergent evidence service."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()

    def atomic_inventory(
        self,
        *,
        query: str = "",
        target_files: Sequence[str] = (),
        target_symbols: Sequence[str] = (),
        limit: int | None = None,
        include_source: bool = False,
    ) -> dict[str, Any]:
        return build_atomic_function_inventory(
            self.repo_root,
            query=query,
            target_files=target_files,
            target_symbols=target_symbols,
            limit=limit,
            include_source=include_source,
        )

    def run(
        self,
        value: Mapping[str, Any] | EmergentEvidenceRequest,
    ) -> dict[str, Any]:
        try:
            request = EmergentEvidenceRequest.from_value(value)
            sources = _repo_python_sources(self.repo_root)
            anchor = CodeTopoAnchor.build_from_files(sources)
            inventory = _inventory_from_anchor(anchor, include_source=False)
            resolution = resolve_capabilities(
                request.objective,
                target_files=list(request.target_files),
                target_symbols=list(request.target_symbols),
                repo_root=self.repo_root,
                top_k=max(12, min(48, request.max_atomic_nodes)),
                token_budget=3200,
            )
            graph = enrich_connectome(build_capability_connectome(self.repo_root))
            seed_ids, seed_evidence, approximate_only = _select_seed_nodes(
                anchor,
                request,
                resolution,
                graph,
            )
            closure_ids, closure_edges = _expand_atomic_closure(
                anchor,
                seed_ids,
                radius=request.radius,
                max_nodes=request.max_atomic_nodes,
            )
            selected_nodes = [
                anchor.nodes[node_id]
                for node_id in closure_ids
                if node_id in anchor.nodes and anchor.nodes[node_id].kind in ATOMIC_KINDS
            ]
            selected_nodes.sort(key=lambda node: (node.file_path, node.start_line, node.symbol))
            source_slices = [
                _source_slice(
                    anchor,
                    node,
                    include_source=request.include_source,
                    max_lines=request.max_source_lines,
                )
                for node in selected_nodes
            ]
            source_slices = [item for item in source_slices if item]
            tests = _tests_for_nodes(anchor, closure_ids, self.repo_root)
            bounded_anchor = _bounded_anchor(anchor, closure_ids, tests)
            audit = audit_emergent_capabilities(
                bounded_anchor,
                query=request.objective,
                include_future=request.include_future,
                limit=min(20, request.max_atomic_nodes),
            ).to_dict()
            research = _research_projection(
                request,
                resolution,
                selected_nodes,
                audit,
                self.repo_root,
            )
            packet = _assemble_packet(
                request=request,
                repo_root=self.repo_root,
                anchor=anchor,
                inventory=inventory,
                resolution=resolution,
                connectome=graph,
                seed_evidence=seed_evidence,
                selected_nodes=selected_nodes,
                closure_edges=closure_edges,
                source_slices=source_slices,
                tests=tests,
                audit=audit,
                research=research,
                approximate_only=approximate_only,
            )
            return packet
        except (
            OSError,
            TypeError,
            ValueError,
            UnicodeError,
            SyntaxError,
            LookupError,
            json.JSONDecodeError,
        ) as exc:
            return _error(type(exc).__name__, str(exc))
        except Exception as exc:
            return _error(type(exc).__name__, "emergent evidence spine failed closed")


def build_atomic_function_inventory(
    repo_root: str | Path = ".",
    *,
    query: str = "",
    target_files: Sequence[str] = (),
    target_symbols: Sequence[str] = (),
    limit: int | None = None,
    include_source: bool = False,
) -> dict[str, Any]:
    """List Aura's complete atomic callable inventory with exact source identity.

    The complete inventory is always computed. ``limit`` only bounds emitted
    records; ``total_count`` and ``inventory_digest`` describe the full set.
    """

    root = Path(repo_root).resolve()
    anchor = CodeTopoAnchor.build_from_files(_repo_python_sources(root))
    full = _inventory_from_anchor(anchor, include_source=include_source)
    records = list(full["atomic_functions"])
    normalized_files = set(_repo_paths(target_files))
    normalized_symbols = set(_strings(target_symbols))
    query_tokens = _tokens(query)
    if normalized_files or normalized_symbols or query_tokens:
        scored: list[tuple[int, dict[str, Any]]] = []
        for record in records:
            score = 0
            if record["file_path"] in normalized_files:
                score += 100
            if normalized_symbols.intersection(
                {record["symbol"], record["qualified_symbol"]}
            ):
                score += 120
            searchable = " ".join(
                [
                    record["file_path"],
                    record["symbol"],
                    record["qualified_symbol"],
                    record.get("parent_symbol") or "",
                    " ".join(record.get("calls") or []),
                    " ".join(record.get("imports") or []),
                ]
            ).lower()
            score += sum(3 for token in query_tokens if token in searchable)
            if score:
                scored.append((score, record))
        scored.sort(key=lambda item: (-item[0], item[1]["file_path"], item[1]["start_line"]))
        records = [item[1] for item in scored]
    if limit is not None:
        records = records[: max(0, int(limit))]
    return {
        "ok": True,
        "version": ATOMIC_INVENTORY_VERSION,
        "repo_head": _repo_head(root),
        "total_count": full["total_count"],
        "emitted_count": len(records),
        "truncated": len(records) < full["total_count"],
        "inventory_digest": full["inventory_digest"],
        "atomic_functions": records,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "production_mutation": False,
    }


def _repo_python_sources(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.glob("**/*.py")):
        relative = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        with tokenize.open(path) as handle:
            files[relative.as_posix()] = handle.read()
    return files


def _inventory_from_anchor(anchor: CodeTopoAnchor, *, include_source: bool) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for node in sorted(
        anchor.nodes.values(),
        key=lambda item: (item.file_path, item.start_line, item.symbol),
    ):
        if node.kind not in ATOMIC_KINDS:
            continue
        record = {
            "node_id": node.node_id,
            "file_path": node.file_path,
            "symbol": node.symbol,
            "qualified_symbol": (
                f"{node.parent_symbol}.{node.symbol}" if node.parent_symbol else node.symbol
            ),
            "kind": node.kind,
            "start_line": node.start_line,
            "end_line": node.end_line,
            "source_hash": node.source_hash,
            "file_source_hash": anchor.file_hashes.get(node.file_path, ""),
            "parent_symbol": node.parent_symbol,
            "calls": list(node.calls),
            "imports": list(node.imports),
            "decorators": list(node.decorators),
        }
        if include_source:
            span = _source_slice(anchor, node, include_source=True, max_lines=300)
            record["source"] = span.get("source", "") if span else ""
        records.append(record)
    digest = _digest(
        [
            {
                "node_id": record["node_id"],
                "source_hash": record["source_hash"],
                "file_source_hash": record["file_source_hash"],
            }
            for record in records
        ]
    )
    return {
        "total_count": len(records),
        "inventory_digest": digest,
        "atomic_functions": records,
    }


def _qualified_symbol(node: CodeTopoNode) -> str:
    return f"{node.parent_symbol}.{node.symbol}" if node.parent_symbol else node.symbol


def _matches_symbol(node: CodeTopoNode, symbol: str) -> bool:
    return symbol in {node.symbol, _qualified_symbol(node)}


def _select_seed_nodes(
    anchor: CodeTopoAnchor,
    request: EmergentEvidenceRequest,
    resolution: Mapping[str, Any],
    connectome: Mapping[str, Any],
) -> tuple[list[str], list[dict[str, Any]], bool]:
    selected: list[str] = []
    evidence: list[dict[str, Any]] = []
    target_files = set(request.target_files)

    def admit(node: CodeTopoNode, reason: str, *, exact: bool = True, score: float = 1.0) -> None:
        if node.kind not in ATOMIC_KINDS or node.node_id in selected:
            return
        selected.append(node.node_id)
        evidence.append(
            {
                "node_id": node.node_id,
                "file_path": node.file_path,
                "symbol": node.symbol,
                "source_hash": node.source_hash,
                "reason": reason,
                "grounding_class": "EXACT" if exact else "ADVISORY_AFFINITY",
                "score": round(float(score), 6),
            }
        )

    for symbol in request.target_symbols:
        candidates = [
            node
            for node in anchor.nodes.values()
            if node.kind in ATOMIC_KINDS
            and _matches_symbol(node, symbol)
            and (not target_files or node.file_path in target_files)
        ]
        for node in candidates:
            admit(node, "explicit_target_symbol")

    if target_files:
        for node in anchor.nodes.values():
            if node.file_path in target_files:
                admit(node, "explicit_target_file")

    for item in resolution.get("exact_matches", []) or []:
        if not isinstance(item, Mapping):
            continue
        _admit_match(anchor, item, "capability_resolver_exact_match", admit)
    for item in resolution.get("related_functions", []) or []:
        if not isinstance(item, Mapping):
            continue
        _admit_match(anchor, item, "capability_resolver_related_function", admit)

    path = resolution.get("capability_connectome_path") or {}
    for detail in path.get("path_details", []) or []:
        if not isinstance(detail, Mapping):
            continue
        implemented = set(_repo_paths(detail.get("implemented_by") or ()))
        for symbol in _strings(detail.get("symbols") or ()):
            for node in anchor.nodes.values():
                if node.kind not in ATOMIC_KINDS or not _matches_symbol(node, symbol):
                    continue
                if implemented and node.file_path not in implemented:
                    continue
                admit(
                    node,
                    f"capability_connectome:{detail.get('id', '')}",
                )

    seed_cap = max(4, min(24, max(1, request.max_atomic_nodes // 2)))
    if selected:
        return selected[:seed_cap], evidence[:seed_cap], False

    candidates = [node for node in anchor.nodes.values() if node.kind in ATOMIC_KINDS]
    ranked = anchor.rank_affinity(request.objective, candidates)[: min(8, seed_cap)]
    for node, score in ranked:
        if score <= 0:
            continue
        admit(node, "objective_affinity_fallback", exact=False, score=score)
    return selected[:seed_cap], evidence[:seed_cap], True


def _admit_match(
    anchor: CodeTopoAnchor,
    item: Mapping[str, Any],
    reason: str,
    admit: Any,
) -> None:
    file_path = _normalize_repo_path(item.get("file") or item.get("file_path") or "")
    symbol = str(item.get("symbol") or "").strip()
    for node in anchor.nodes.values():
        if node.kind not in ATOMIC_KINDS:
            continue
        if file_path and node.file_path != file_path:
            continue
        if symbol and not _matches_symbol(node, symbol):
            continue
        admit(node, reason)


def _expand_atomic_closure(
    anchor: CodeTopoAnchor,
    seed_ids: Sequence[str],
    *,
    radius: int,
    max_nodes: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    visited: list[str] = []
    seen: set[str] = set()
    queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in seed_ids)
    queued: set[str] = set(seed_ids)
    while queue and len(visited) < max_nodes:
        node_id, distance = queue.popleft()
        node = anchor.nodes.get(node_id)
        if node is None or node.kind not in ATOMIC_KINDS or node_id in seen:
            continue
        seen.add(node_id)
        visited.append(node_id)
        if distance >= radius:
            continue
        edges = [*anchor.outgoing.get(node_id, []), *anchor.incoming.get(node_id, [])]
        for edge in sorted(
            edges,
            key=lambda item: (item.edge_type, item.src_id, item.dst_id, item.evidence),
        ):
            other = edge.dst_id if edge.src_id == node_id else edge.src_id
            other_node = anchor.nodes.get(other)
            if other_node is None or other_node.kind not in ATOMIC_KINDS:
                continue
            if (
                other not in seen
                and other not in queued
                and len(visited) + len(queue) < max_nodes
            ):
                queued.add(other)
                queue.append((other, distance + 1))
    selected = set(visited)
    admitted_edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()
    for edge in sorted(
        anchor.edges,
        key=lambda item: (item.edge_type, item.src_id, item.dst_id, item.evidence),
    ):
        if edge.src_id not in selected or edge.dst_id not in selected:
            continue
        key = (edge.src_id, edge.dst_id, edge.edge_type)
        if key in edge_keys:
            continue
        edge_keys.add(key)
        admitted_edges.append(edge.to_dict())
    return visited, admitted_edges


def _bounded_anchor(
    anchor: CodeTopoAnchor,
    atomic_ids: Sequence[str],
    tests: Sequence[str],
) -> CodeTopoAnchor:
    include_ids = set(atomic_ids)
    include_files = {
        anchor.nodes[node_id].file_path
        for node_id in atomic_ids
        if node_id in anchor.nodes
    }
    include_files.update(tests)
    selected_module_ids = {
        anchor.module_nodes.get(file_path) for file_path in include_files
    }
    selected_module_ids.discard(None)
    for node in anchor.nodes.values():
        if node.file_path in tests and node.kind in ATOMIC_KINDS:
            include_ids.add(node.node_id)
    test_targets = include_ids | selected_module_ids
    for edge in anchor.edges:
        if edge.edge_type == "test" and edge.dst_id in test_targets:
            include_ids.add(edge.src_id)
    for node in anchor.nodes.values():
        if node.kind == "module" and node.file_path in include_files:
            include_ids.add(node.node_id)
    bounded = CodeTopoAnchor()
    bounded.nodes = {
        node_id: anchor.nodes[node_id]
        for node_id in include_ids
        if node_id in anchor.nodes
    }
    bounded.symbol_index = defaultdict(list)
    bounded.module_nodes = {}
    for node in bounded.nodes.values():
        if node.kind == "module":
            bounded.module_nodes[node.file_path] = node.node_id
        else:
            bounded.symbol_index[node.symbol].append(node.node_id)
    bounded.edges = [
        edge
        for edge in anchor.edges
        if edge.src_id in bounded.nodes and edge.dst_id in bounded.nodes
    ]
    bounded.outgoing = defaultdict(list)
    bounded.incoming = defaultdict(list)
    for edge in bounded.edges:
        bounded.outgoing[edge.src_id].append(edge)
        bounded.incoming[edge.dst_id].append(edge)
    bounded.file_hashes = {
        path: digest
        for path, digest in anchor.file_hashes.items()
        if path in include_files
    }
    bounded.source_texts = {
        path: source
        for path, source in anchor.source_texts.items()
        if path in include_files
    }
    bounded.import_aliases = {
        path: aliases
        for path, aliases in anchor.import_aliases.items()
        if path in include_files
    }
    bounded.call_records = [
        record
        for record in anchor.call_records
        if str(record.get("node_id") or "") in bounded.nodes
    ]
    bounded.warnings = list(anchor.warnings)
    bounded.metadata = {
        "version": EMERGENT_EVIDENCE_SPINE_VERSION,
        "bounded": True,
        "atomic_node_count": len(atomic_ids),
        "node_count": len(bounded.nodes),
        "edge_count": len(bounded.edges),
    }
    return bounded


def _source_slice(
    anchor: CodeTopoAnchor,
    node: CodeTopoNode,
    *,
    include_source: bool,
    max_lines: int,
) -> dict[str, Any]:
    source = anchor.source_texts.get(node.file_path, "")
    lines = source.splitlines()
    if not lines:
        return {}
    start = max(1, int(node.start_line))
    exact_end = min(len(lines), max(start, int(node.end_line)))
    emitted_end = min(exact_end, start + max_lines - 1)
    packet = {
        "node_id": node.node_id,
        "file_path": node.file_path,
        "symbol": node.symbol,
        "qualified_symbol": (
            f"{node.parent_symbol}.{node.symbol}" if node.parent_symbol else node.symbol
        ),
        "kind": node.kind,
        "line_start": start,
        "line_end": exact_end,
        "emitted_line_end": emitted_end,
        "truncated": emitted_end < exact_end,
        "source_hash": node.source_hash,
        "file_source_hash": anchor.file_hashes.get(node.file_path, ""),
    }
    if include_source:
        packet["source"] = "\n".join(lines[start - 1 : emitted_end])
    return packet


def _tests_for_nodes(
    anchor: CodeTopoAnchor,
    node_ids: Sequence[str],
    repo_root: Path,
) -> list[str]:
    target_files = {
        anchor.nodes[node_id].file_path
        for node_id in node_ids
        if node_id in anchor.nodes
    }
    if not target_files:
        return []
    tests: set[str] = set()
    target_module_ids = {
        anchor.module_nodes.get(file_path)
        for file_path in target_files
    }
    target_module_ids.discard(None)
    for edge in anchor.edges:
        if edge.edge_type != "test":
            continue
        targets_selected_module = edge.dst_id in target_module_ids
        targets_selected_file = (
            edge.dst_id in anchor.nodes
            and anchor.nodes[edge.dst_id].file_path in target_files
        )
        if not (targets_selected_module or targets_selected_file):
            continue
        source = anchor.nodes.get(edge.src_id)
        if source is not None:
            tests.add(source.file_path)
    for file_path in target_files:
        path = PurePosixPath(file_path)
        candidates = (
            path.parent / f"test_{path.name}",
            PurePosixPath("tests") / f"test_{path.name}",
        )
        for candidate in candidates:
            candidate_text = candidate.as_posix()
            if candidate_text in anchor.source_texts or (repo_root / candidate).is_file():
                tests.add(candidate_text)
    return sorted(tests)


def _research_projection(
    request: EmergentEvidenceRequest,
    resolution: Mapping[str, Any],
    selected_nodes: Sequence[CodeTopoNode],
    audit: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if not request.include_research_plan:
        return {
            "enabled": False,
            "query_plans": [],
            "offline_evidence": {},
            "advisory_only": True,
        }
    capability_names = [
        str(item.get("name") or item.get("id") or "")
        for item in (
            resolution.get("capability_connectome_path", {}).get("path_details", [])
            or []
        )
        if isinstance(item, Mapping)
    ]
    symbols = [node.symbol for node in selected_nodes[:8]]
    queries = [request.objective]
    if capability_names:
        queries.append(
            f"{request.objective} {' '.join(capability_names[:5])} software architecture"
        )
    if symbols:
        queries.append(
            f"{request.objective} {' '.join(symbols)} dependency analysis verification"
        )
    query_plans = [plan_arxiv_forager_query(query) for query in dict.fromkeys(queries)]
    offline_evidence: dict[str, Any] = {}
    if request.include_offline_research:
        offline_evidence = build_research_evidence_packet(
            request.objective,
            repo_root=repo_root,
            offline=True,
        )
    return {
        "enabled": True,
        "query_plans": query_plans,
        "offline_evidence": offline_evidence,
        "audit_gap_count": len(audit.get("future_potentials", []) or []),
        "execute_with": "ArenaResearchBridge.search_arxiv",
        "external_evidence_is_patch_authority": False,
        "advisory_only": True,
    }


def _assemble_packet(
    *,
    request: EmergentEvidenceRequest,
    repo_root: Path,
    anchor: CodeTopoAnchor,
    inventory: Mapping[str, Any],
    resolution: Mapping[str, Any],
    connectome: Mapping[str, Any],
    seed_evidence: Sequence[Mapping[str, Any]],
    selected_nodes: Sequence[CodeTopoNode],
    closure_edges: Sequence[Mapping[str, Any]],
    source_slices: Sequence[Mapping[str, Any]],
    tests: Sequence[str],
    audit: Mapping[str, Any],
    research: Mapping[str, Any],
    approximate_only: bool,
) -> dict[str, Any]:
    selected_atomic = [
        {
            "node_id": node.node_id,
            "file_path": node.file_path,
            "symbol": node.symbol,
            "kind": node.kind,
            "line_start": node.start_line,
            "line_end": node.end_line,
            "source_hash": node.source_hash,
            "calls": list(node.calls),
            "imports": list(node.imports),
        }
        for node in selected_nodes
    ]
    exact_seeds = [
        item for item in seed_evidence if item.get("grounding_class") == "EXACT"
    ]
    grounding_ok = bool(selected_nodes and source_slices and exact_seeds and not approximate_only)
    findings = list(audit.get("findings") or [])
    future = list(audit.get("future_potentials") or [])
    research_gaps = _research_gaps(future, tests, resolution)
    waboose_directives = _waboose_directives(
        request,
        selected_nodes,
        findings,
        research_gaps,
    )
    target_files = sorted({node.file_path for node in selected_nodes})
    target_symbols = list(dict.fromkeys(node.symbol for node in selected_nodes))
    acceptance = [
        "Preserve exact source hashes for every selected atomic function.",
        "Verify all admitted caller/callee dependency edges before implementation.",
        "Keep emergent findings advisory until Coding Waboose and verifier evidence corroborate them.",
    ]
    if tests:
        acceptance.append("Run the selected dependency-related tests: " + ", ".join(tests[:8]))
    acceptance.extend(
        f"Close or explicitly defer emergent research gap: {gap['gap']}"
        for gap in research_gaps[:6]
    )
    risk_map = sorted(
        dict.fromkeys(
            [
                "emergent_capability_false_positive",
                "dependency_closure_incomplete",
                "advisory_evidence_misused_as_authority",
                *[str(item) for item in resolution.get("capability_risks", []) or []],
            ]
        )
    )
    packet_digest = _digest(
        {
            "objective": request.objective,
            "repo_head": _repo_head(repo_root),
            "inventory_digest": inventory.get("inventory_digest", ""),
            "selected": [node.node_id for node in selected_nodes],
            "capability_path_digest": resolution.get("capability_path_digest", ""),
            "audit": [item.get("finding_id") for item in findings],
        }
    )
    first_node = selected_nodes[0] if selected_nodes else None
    agent_capsule = {
        "objective": request.objective,
        "target_file": first_node.file_path if first_node else "",
        "target_symbol": first_node.symbol if first_node else "",
        "atomic_inventory_digest": inventory.get("inventory_digest", ""),
        "atomic_inventory_total": inventory.get("total_count", 0),
        "selected_atomic_functions": selected_atomic,
        "dependency_edges": list(closure_edges),
        "source_slices": list(source_slices),
        "tests": list(tests),
        "capability_path": resolution.get("capability_connectome_path", {}),
        "waboose_focus_directives": waboose_directives,
        "token_estimate": sum(
            max(1, len(str(item.get("source") or "")) // 4)
            for item in source_slices
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    projections = {
        "coding_arena": {
            "target_files": target_files,
            "target_symbols": target_symbols,
            "acceptance_criteria": acceptance,
            "risk_map": risk_map,
            "constraints": [
                "Use exact atomic source slices and hashes as authority.",
                "Do not create an implementation edge from an emergent finding without verification.",
                "Human authorization remains required for patch promotion.",
            ],
            "tests": list(tests),
            "waboose_focus_directives": waboose_directives,
        },
        "coding_waboose": {
            "focus_directives": waboose_directives,
            "invariants": acceptance[:3],
            "risk_map": risk_map,
            "changed_files": target_files,
        },
        "human_agent": {
            "selected_findings": findings,
            "future_potentials": future,
            "research_gaps": research_gaps,
            "review_questions": [
                "Which emergent capability edges should be tested rather than implemented?",
                "Which missing evidence would change the decision?",
                "Does the proposed combination preserve human and verifier authority?",
            ],
        },
        "agent_bridge": agent_capsule,
        "research": dict(research),
    }
    return {
        "ok": True,
        "version": EMERGENT_EVIDENCE_SPINE_VERSION,
        "packet_id": f"EMERGENT-{packet_digest[:20]}",
        "packet_digest": packet_digest,
        "status": (
            "GROUNDED_ATOMIC_CLOSURE"
            if grounding_ok
            else "ADVISORY_AFFINITY_ONLY"
            if selected_nodes
            else "NO_ATOMIC_MATCHES"
        ),
        "objective": request.objective,
        "target_arena": request.target_arena,
        "repo_head": _repo_head(repo_root),
        "grounding_ok": grounding_ok,
        "approximate_only": approximate_only,
        "atomic_inventory": {
            "version": ATOMIC_INVENTORY_VERSION,
            "total_count": inventory.get("total_count", 0),
            "inventory_digest": inventory.get("inventory_digest", ""),
            "selected_count": len(selected_atomic),
            "selected_atomic_functions": selected_atomic,
        },
        "capability_connectome": {
            "version": connectome.get("version", ""),
            "graph_digest": connectome.get("graph_digest", ""),
            "node_count": connectome.get("node_count", 0),
            "edge_count": connectome.get("edge_count", 0),
            "path": resolution.get("capability_connectome_path", {}),
        },
        "seed_evidence": list(seed_evidence),
        "dependency_edges": list(closure_edges),
        "source_slices": list(source_slices),
        "tests": list(tests),
        "audit_report": dict(audit),
        "selected_findings": findings,
        "future_potentials": future,
        "research_gaps": research_gaps,
        "research_evidence": dict(research),
        "required_tests": list(tests),
        "acceptance_criteria": acceptance,
        "risk_map": risk_map,
        "waboose_focus_directives": waboose_directives,
        "projections": projections,
        "active_projection": projections[request.target_arena],
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _waboose_directives(
    request: EmergentEvidenceRequest,
    selected_nodes: Sequence[CodeTopoNode],
    findings: Sequence[Mapping[str, Any]],
    research_gaps: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    directives: list[dict[str, Any]] = [
        {
            "name": "atomic_closure_integrity",
            "question": "Are all exact callers, callees, tests, and imports for the selected atomic functions represented?",
            "risk": "correctness",
            "direction": "both",
            "target_patterns": list(
                dict.fromkeys(
                    [node.symbol for node in selected_nodes[:8]]
                    + [node.file_path for node in selected_nodes[:8]]
                )
            ),
            "required_evidence": ["exact_source", "call_graph", "test_selection"],
            "suggested_tools": ["pytest"],
            "max_depth": request.radius,
            "max_nodes": request.max_atomic_nodes,
        },
        {
            "name": "emergent_authority_boundary",
            "question": "Can any advisory emergent finding bypass Waboose, verifier, or human authorization?",
            "risk": "authority",
            "direction": "both",
            "target_patterns": [
                "safe_to_patch",
                "patch_authority",
                "human_review_required",
                "automatic_merge",
            ],
            "required_evidence": ["contract_invariant", "exact_source"],
            "suggested_tools": ["pytest"],
            "max_depth": 1,
            "max_nodes": min(80, request.max_atomic_nodes),
        },
    ]
    for finding in findings[:6]:
        symbols = [
            item
            for item in finding.get("symbols", []) or []
            if isinstance(item, Mapping)
        ]
        patterns = list(
            dict.fromkeys(
                [str(item.get("symbol") or "") for item in symbols]
                + [str(item.get("file_path") or "") for item in symbols]
            )
        )
        directives.append(
            {
                "name": f"emergent_finding_{finding.get('finding_id', '')[:12]}",
                "question": str(finding.get("title") or "Verify the emergent capability finding."),
                "risk": "architecture",
                "direction": "both",
                "target_patterns": [item for item in patterns if item],
                "required_evidence": [
                    "exact_source",
                    "missing_edge_proof",
                    "regression_test",
                ],
                "suggested_tools": ["pytest"],
                "max_depth": request.radius,
                "max_nodes": request.max_atomic_nodes,
            }
        )
    if research_gaps:
        directives.append(
            {
                "name": "research_gap_non_authority",
                "question": "Are external research results kept advisory and separate from repository truth?",
                "risk": "research",
                "direction": "both",
                "target_patterns": ["research_evidence", "advisory_only", "metadata_truth"],
                "required_evidence": ["contract_invariant", "source_hash"],
                "suggested_tools": ["pytest"],
                "max_depth": 1,
                "max_nodes": min(60, request.max_atomic_nodes),
            }
        )
    return directives


def _research_gaps(
    future: Sequence[Mapping[str, Any]],
    tests: Sequence[str],
    resolution: Mapping[str, Any],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if not tests:
        gaps.append(
            {
                "gap": "No dependency-related tests were resolved for the selected atomic closure.",
                "kind": "verification_gap",
            }
        )
    for item in future[:8]:
        blockers = [str(value) for value in item.get("blockers", []) or []]
        gaps.append(
            {
                "gap": str(item.get("title") or "Future emergent capability requires evidence."),
                "kind": "future_potential",
                "blockers": blockers,
                "finding_id": str(item.get("finding_id") or ""),
            }
        )
    for missing in resolution.get("missing_capabilities", []) or []:
        if not isinstance(missing, Mapping):
            continue
        gaps.append(
            {
                "gap": str(missing.get("reason") or missing.get("capability") or "unresolved capability"),
                "kind": "capability_gap",
                "capability": str(missing.get("capability") or ""),
            }
        )
    return gaps[:16]


def _repo_paths(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        raw = str(value or "").strip()
        normalized = _normalize_repo_path(value)
        if raw and not normalized:
            raise ValueError("repository paths must be relative and may not escape the repository")
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)


def _normalize_repo_path(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        return ""
    return path.as_posix()


def _strings(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _sequence(value: Any) -> Sequence[Any]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)):
        return (value,)
    if isinstance(value, Sequence):
        return value
    if isinstance(value, Iterable) and not isinstance(value, Mapping):
        return tuple(value)
    raise ValueError("expected a sequence")


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in _TOKEN_RE.findall(str(text or ""))
        if token.lower() not in _STOPWORDS and len(token) > 1
    ]


def _repo_head(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    head = result.stdout.strip().lower()
    if len(head) != 40 or any(ch not in "0123456789abcdef" for ch in head):
        return ""
    return head


def _digest(value: Any) -> str:
    return hashlib.blake2b(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"),
        digest_size=20,
    ).hexdigest()


def _error(error_type: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "version": EMERGENT_EVIDENCE_SPINE_VERSION,
        "error": f"{error_type}:{message}",
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "ATOMIC_INVENTORY_VERSION",
    "EMERGENT_EVIDENCE_SPINE_VERSION",
    "AuraEmergentEvidenceSpine",
    "EmergentEvidenceRequest",
    "build_atomic_function_inventory",
]

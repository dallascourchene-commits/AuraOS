"""Topology-driven compatibility router for Aura code context.

``query_router`` preserves the historic return keys while making current
CODEMAP, the Capability Genome Resolver V2, and the Topological Context Anchor
the primary routing evidence.  The generated Markdown task table remains a
cold fallback only.

Exact source spans and hashes are authoritative.  Similarity and inferred
relationships are explicitly advisory and never grant patch authority.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping

ROUTER_INDEX_PATH = "AURA_AI_ROUTER.md"
AI_ROUTER_VERSION = "AURA_AI_ROUTER_DYNAMIC_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
DEFAULT_TOKEN_BUDGET = 2400

_INDEX_CACHE: dict[str, Any] | None = None
_INDEX_CACHE_MTIME: float | None = None
_INDEX_CACHE_PATH: str | None = None

_TASK_ROW = re.compile(
    r"^\|\s*`(?P<task>[^`]+)`\s*\|\s*`(?P<primary>[^`]+)`\s*\|"
    r"\s*(?P<secondary>.*?)\s*\|\s*(?P<functions>.*?)\s*\|\s*$"
)
_FILE_TOKEN = re.compile(
    r"(?<![\w./\\-])([\w./\\-]+\.(?:py|rs|js|ts|tsx|jsx|md|json|toml|yaml|yml))(?![\w./\\-])",
    re.IGNORECASE,
)
_SYMBOL_TOKEN = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`|\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)\b")
_SKIP_DIRS = frozenset({
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", "Aura_Memory", "Aura_Staging", "Aura_Sandbox", "aura_exports",
    "models", ".cargo", "llama.cpp",
})


def _normalize_path(value: str) -> str:
    token = str(value or "").strip().strip("`\"'").replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    return token.lstrip("/")


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(encoded.encode("utf-8"), digest_size=16).hexdigest()


def _estimate_tokens(value: str) -> int:
    return max(1, len(value) // 4) if value else 0


def _bounded_text(value: str, token_budget: int) -> str:
    maximum = max(0, int(token_budget)) * 4
    if len(value) <= maximum:
        return value
    suffix = "\n[TRUNCATED_AT_ROUTER_TOKEN_BUDGET]"
    return value[: max(0, maximum - len(suffix))] + suffix


def load_router_index(path: str = ROUTER_INDEX_PATH) -> dict[str, Any]:
    """Parse the generated Markdown fallback table.

    The Markdown is a read-only view, not authoritative topology.  Cache
    invalidation follows file mtime so regeneration remains backward compatible.
    """
    global _INDEX_CACHE, _INDEX_CACHE_MTIME, _INDEX_CACHE_PATH
    cache_path = str(Path(path).resolve())
    try:
        mtime = os.path.getmtime(cache_path)
    except OSError:
        return {"tasks": {}, "source": path, "authoritative": False}
    if _INDEX_CACHE is not None and _INDEX_CACHE_MTIME == mtime and _INDEX_CACHE_PATH == cache_path:
        return _INDEX_CACHE

    tasks: dict[str, dict[str, Any]] = {}
    try:
        lines = Path(cache_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        lines = []
    for line in lines:
        match = _TASK_ROW.match(line)
        if not match:
            continue
        secondary = re.findall(r"`([^`]+)`", match.group("secondary"))
        functions = [
            token.strip().rstrip("()")
            for token in re.split(r",\s*", re.sub(r"`", "", match.group("functions")))
            if token.strip()
        ]
        tasks[match.group("task").strip()] = {
            "primary": match.group("primary").strip(),
            "secondary": secondary,
            "key_functions": functions,
        }
    _INDEX_CACHE = {
        "tasks": tasks,
        "source": cache_path,
        "authoritative": False,
        "view_only": True,
    }
    _INDEX_CACHE_MTIME = mtime
    _INDEX_CACHE_PATH = cache_path
    return _INDEX_CACHE


def _static_fallback(task_description: str, *, path: str = ROUTER_INDEX_PATH) -> dict[str, Any]:
    index = load_router_index(path)
    tasks = index.get("tasks", {})
    query_words = set(re.findall(r"[a-z0-9_]+", task_description.lower()))
    best_name = ""
    best_score = 0.0
    for name in tasks:
        words = set(re.findall(r"[a-z0-9_]+", name.lower()))
        score = len(query_words & words) / max(1, len(words))
        if score > best_score:
            best_name, best_score = name, score
    if not best_name or best_score <= 0:
        return {
            "status": "not_found",
            "task": task_description,
            "available_tasks": list(tasks),
            "hint": "Run `python3 generate_ai_router.py` to refresh the non-authoritative fallback view.",
            "routing_source": "none",
        }
    info = tasks[best_name]
    return {
        "status": "found",
        "task": best_name,
        "primary_file": info["primary"],
        "secondary_files": list(info.get("secondary", [])),
        "key_functions": list(info.get("key_functions", [])),
        "confidence": round(best_score * 0.45, 4),
        "routing_source": "static_fallback",
        "advisory_only": True,
        "warnings": ["generated_markdown_fallback_is_not_patch_evidence"],
    }


def _explicit_targets(task: str) -> tuple[list[str], list[str]]:
    files = [_normalize_path(match.group(1)) for match in _FILE_TOKEN.finditer(task or "")]
    symbols: list[str] = []
    for match in _SYMBOL_TOKEN.finditer(task or ""):
        raw = match.group(1) or match.group(2) or ""
        symbol = raw.rsplit(".", 1)[-1]
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return list(dict.fromkeys(files)), symbols


def _path_detail_values(detail: Mapping[str, Any], names: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for name in names:
        raw = detail.get(name)
        if raw is None:
            continue
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, (list, tuple, set)):
            values.extend(str(item) for item in raw if str(item).strip())
    return values


def _resolution_targets(resolution: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
    files: list[str] = []
    symbols: list[str] = []
    tests: list[str] = []
    for item in resolution.get("exact_matches", []) or []:
        if not isinstance(item, Mapping):
            continue
        if item.get("file"):
            files.append(_normalize_path(str(item["file"])))
        if item.get("symbol") and item.get("grounding_class") == "EXACT":
            symbols.append(str(item["symbol"]))
    for item in resolution.get("related_functions", []) or []:
        if not isinstance(item, Mapping):
            continue
        if item.get("file"):
            files.append(_normalize_path(str(item["file"])))
        if item.get("symbol") and item.get("grounding_class") == "EXACT":
            symbols.append(str(item["symbol"]))
        tests.extend(str(value) for value in item.get("tests", []) or [])
    for item in resolution.get("reuse_plan", []) or []:
        if isinstance(item, Mapping):
            files.extend(_normalize_path(value) for value in item.get("implemented_by", []) or [])
    for detail in resolution.get("capability_path_details", []) or []:
        if not isinstance(detail, Mapping):
            continue
        files.extend(_normalize_path(value) for value in _path_detail_values(
            detail, ("implementing_files", "implemented_by", "files", "source_files")
        ))
        symbols.extend(_path_detail_values(detail, ("symbols", "functions", "primary_functions")))
        tests.extend(_path_detail_values(detail, ("tests", "test_files")))
    tests.extend(str(value) for value in resolution.get("tests", []) or [])
    return (
        list(dict.fromkeys(value for value in files if value)),
        list(dict.fromkeys(value for value in symbols if value)),
        list(dict.fromkeys(_normalize_path(value) for value in tests if value)),
    )


def _repo_python_sources(
    repo_root: str | Path,
    *,
    seed_files: list[str],
    max_files: int = 360,
    max_bytes: int = 5_000_000,
) -> dict[str, str]:
    root = Path(repo_root).resolve()
    candidates: list[Path] = []
    for value in seed_files:
        path = root / _normalize_path(value)
        if path.suffix == ".py" and path.is_file():
            candidates.append(path)
    candidates.extend(sorted(root.glob("*.py")))
    tests_root = root / "tests"
    if tests_root.exists():
        candidates.extend(sorted(tests_root.rglob("*.py")))

    sources: dict[str, str] = {}
    total = 0
    for path in candidates:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        key = relative.as_posix()
        if key in sources:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if len(sources) >= max_files or total + size > max_bytes:
            continue
        try:
            sources[key] = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        total += size
    return sources


def _node_summary(node: Any, *, confidence: float = 1.0, relationship: str = "exact") -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "file": node.file_path,
        "symbol": node.symbol,
        "kind": node.kind,
        "line_start": node.start_line,
        "line_end": node.end_line,
        "source_hash": node.source_hash,
        "confidence": round(float(confidence), 6),
        "relationship": relationship,
        "grounding_class": "EXACT" if confidence >= 1.0 else "ADVISORY",
    }


def _trim_context_packet(packet: dict[str, Any], token_budget: int) -> dict[str, Any]:
    packet = dict(packet)
    spans: list[dict[str, Any]] = []
    used = 0
    for raw in packet.get("source_spans", []) or []:
        span = dict(raw)
        source = str(span.get("source", ""))
        remaining = max(0, token_budget - used)
        if remaining <= 0:
            break
        source = _bounded_text(source, remaining)
        span["source"] = source
        used += _estimate_tokens(source)
        spans.append(span)
    packet["source_spans"] = spans[:12]
    packet["neighbor_summaries"] = list(packet.get("neighbor_summaries", []) or [])[:16]
    packet["tests"] = list(dict.fromkeys(packet.get("tests", []) or []))[:12]
    packet["token_estimate"] = used
    return packet


def _exact_context_packet(anchor: Any, node: Any, radius: int = 1) -> Any:
    from aura_topological_context_anchor import CodeTopoContextPacket

    radius = max(0, min(3, int(radius)))
    visited = {node.node_id}
    neighbor_edge: dict[str, Any] = {}
    queue = [(node.node_id, 0)]
    while queue and len(visited) < 24:
        node_id, distance = queue.pop(0)
        if distance >= radius:
            continue
        for edge in [*anchor.outgoing.get(node_id, []), *anchor.incoming.get(node_id, [])]:
            other = edge.dst_id if edge.src_id == node_id else edge.src_id
            if other not in anchor.nodes or other in visited:
                continue
            visited.add(other)
            neighbor_edge[other] = edge
            queue.append((other, distance + 1))

    source_spans = []
    hashes: dict[str, str] = {}
    token_estimate = 0
    ordered_ids = [node.node_id, *sorted(visited - {node.node_id})]
    for node_id in ordered_ids:
        current = anchor.nodes[node_id]
        span = anchor._source_span_for_node(
            current, role="target" if node_id == node.node_id else "neighbor"
        )
        if span:
            source_spans.append(span)
            token_estimate += _estimate_tokens(str(span.get("source", "")))
        hashes[current.node_id] = current.source_hash
        hashes.setdefault(current.file_path, anchor.file_hashes.get(current.file_path, ""))

    neighbor_summaries = []
    for node_id in sorted(visited - {node.node_id}):
        current = anchor.nodes[node_id]
        edge = neighbor_edge.get(node_id)
        neighbor_summaries.append({
            "node_id": current.node_id,
            "file_path": current.file_path,
            "symbol": current.symbol,
            "kind": current.kind,
            "span": [current.start_line, current.end_line],
            "source_hash": current.source_hash,
            "edge_type": edge.edge_type if edge else "neighbor",
            "edge_evidence": edge.evidence if edge else "",
            "confidence": edge.confidence if edge else 1.0,
        })
    tests = anchor._tests_for_nodes([node.node_id])
    return CodeTopoContextPacket(
        target_nodes=[node],
        source_spans=source_spans,
        neighbor_summaries=neighbor_summaries[:16],
        tests=tests,
        hashes={key: value for key, value in hashes.items() if value},
        warnings=list(dict.fromkeys(anchor.warnings)),
        token_estimate=token_estimate,
        route_diagnostics={
            "route": "BUILDER_PATCH" if tests else "TEST_GAP_FILL",
            "reason": "exact_node_grounded" if tests else "exact_node_grounded_missing_tests",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        },
    )


def _dynamic_route(
    task_description: str,
    *,
    repo_root: str | Path,
    target_files: list[str] | None,
    target_symbols: list[str] | None,
    token_budget: int,
    resolver: Callable[..., dict[str, Any]] | None,
) -> dict[str, Any]:
    from aura_capability_resolver_v2 import resolve_capabilities
    from aura_topological_context_anchor import CodeTopoAnchor, render_builder_context

    explicit_files, explicit_symbols = _explicit_targets(task_description)
    requested_files = list(dict.fromkeys([*(target_files or []), *explicit_files]))
    requested_symbols = list(dict.fromkeys([*(target_symbols or []), *explicit_symbols]))
    resolver_fn = resolver or resolve_capabilities
    resolution = resolver_fn(
        task_description,
        target_files=requested_files or None,
        target_symbols=requested_symbols or None,
        repo_root=repo_root,
        top_k=12,
        token_budget=max(800, token_budget),
    )
    resolved_files, resolved_symbols, resolved_tests = _resolution_targets(resolution)
    seed_files = list(dict.fromkeys([*requested_files, *resolved_files, *resolved_tests]))
    sources = _repo_python_sources(repo_root, seed_files=seed_files)
    anchor = CodeTopoAnchor.build_from_files(sources)

    candidate_symbols = list(dict.fromkeys([*requested_symbols, *resolved_symbols]))
    preferred_files = list(dict.fromkeys([*requested_files, *resolved_files]))
    preferred_rank = {_normalize_path(path): index for index, path in enumerate(preferred_files)}
    primary_requested = _normalize_path(requested_files[0]) if requested_files else ""
    selection_warnings: list[str] = []
    exact_nodes: list[Any] = []
    for symbol in candidate_symbols:
        lookup = anchor.lookup_symbol(symbol)
        hits = list(lookup.exact_hits)
        primary_hits = [node for node in hits if _normalize_path(node.file_path) == primary_requested]
        preferred_hits = [node for node in hits if _normalize_path(node.file_path) in preferred_rank]
        if primary_hits:
            hits = primary_hits
        elif len(preferred_hits) == 1:
            hits = preferred_hits
        elif len(preferred_hits) > 1 or len(hits) > 1:
            selection_warnings.append("ambiguous_exact_symbol_without_unique_file_target")
            continue
        hits.sort(key=lambda node: (preferred_rank.get(_normalize_path(node.file_path), 10**6), node.file_path, node.start_line))
        exact_nodes.extend(hits)
        if len(exact_nodes) >= 6:
            break
    deduped_nodes: list[Any] = []
    seen_node_ids: set[str] = set()
    for node in exact_nodes:
        if node.node_id not in seen_node_ids:
            seen_node_ids.add(node.node_id)
            deduped_nodes.append(node)
    exact_nodes = deduped_nodes[:6]

    advisory_nodes: list[tuple[Any, float]] = []
    if not exact_nodes:
        patchable = [node for node in anchor.nodes.values() if node.kind != "module"]
        advisory_nodes = anchor.rank_affinity(task_description, patchable)[:5]

    source_spans: list[dict[str, Any]] = []
    neighbors: list[dict[str, Any]] = []
    callers: list[dict[str, Any]] = []
    callees: list[dict[str, Any]] = []
    tests: list[str] = list(resolved_tests)
    hashes: dict[str, str] = {}
    dependencies: list[str] = []
    warnings: list[str] = list(selection_warnings)
    primary_packet = None
    for node in exact_nodes[:4]:
        packet = _exact_context_packet(anchor, node, radius=1)
        if primary_packet is None:
            primary_packet = packet
        source_spans.extend(packet.source_spans)
        neighbors.extend(packet.neighbor_summaries)
        tests.extend(packet.tests)
        hashes.update(packet.hashes)
        warnings.extend(packet.warnings)
        dependencies.extend(node.imports)
        callers.extend(
            _node_summary(anchor.nodes[edge.src_id], confidence=edge.confidence, relationship="caller")
            for edge in anchor.incoming.get(node.node_id, [])
            if edge.edge_type == "call" and edge.src_id in anchor.nodes
        )
        callees.extend(
            _node_summary(anchor.nodes[edge.dst_id], confidence=edge.confidence, relationship="callee")
            for edge in anchor.outgoing.get(node.node_id, [])
            if edge.edge_type == "call" and edge.dst_id in anchor.nodes
        )

    if advisory_nodes:
        warnings.append("approximate_similarity_not_patch_evidence")
        neighbors.extend(
            _node_summary(node, confidence=score, relationship="advisory_similarity")
            for node, score in advisory_nodes
        )

    exact_summaries = [_node_summary(node) for node in exact_nodes]
    context_packet = _trim_context_packet(
        {
            "version": AI_ROUTER_VERSION,
            "target_nodes": exact_summaries,
            "source_spans": source_spans,
            "neighbor_summaries": neighbors,
            "callers": callers[:16],
            "callees": callees[:16],
            "tests": list(dict.fromkeys(tests)),
            "dependencies": list(dict.fromkeys(dependencies))[:20],
            "hashes": hashes,
            "warnings": list(dict.fromkeys(warnings)),
            "safety_policy": PATCH_AUTHORITY,
        },
        token_budget,
    )

    # Render through the existing anchor contract when there is one exact packet;
    # otherwise emit a compact JSON advisory packet.
    router_context = ""
    if exact_nodes and primary_packet is not None:
        router_context = _bounded_text(render_builder_context(primary_packet), token_budget)
    elif advisory_nodes:
        router_context = _bounded_text(
            json.dumps({"advisory_neighbors": context_packet["neighbor_summaries"]}, sort_keys=True),
            token_budget,
        )

    primary_file = exact_nodes[0].file_path if exact_nodes else (
        requested_files[0] if requested_files else (resolved_files[0] if resolved_files else "")
    )
    secondary_files = list(dict.fromkeys(
        [
            *(node.file_path for node in exact_nodes[1:]),
            *(item.get("file", "") for item in callers),
            *(item.get("file", "") for item in callees),
            *resolved_files,
            *resolved_tests,
        ]
    ))
    secondary_files = [value for value in secondary_files if value and value != primary_file][:20]
    key_functions = [node.symbol for node in exact_nodes]
    if not key_functions:
        key_functions = [node.symbol for node, _score in advisory_nodes[:5]]

    topology_digest = _stable_digest({
        "anchor": anchor.metadata,
        "targets": exact_summaries,
        "hashes": hashes,
        "capability_graph_digest": resolution.get("capability_graph_digest", ""),
        "capability_path_digest": resolution.get("capability_path_digest", ""),
    })
    exact = bool(exact_nodes)
    found = bool(primary_file or exact_nodes)
    confidence = float(resolution.get("confidence") or 0.0)
    if exact:
        confidence = max(confidence, 0.9)
    elif advisory_nodes:
        confidence = min(max(confidence, float(advisory_nodes[0][1])), 0.59)

    return {
        "status": "found" if found else "not_found",
        "task": task_description,
        "primary_file": primary_file,
        "secondary_files": secondary_files,
        "key_functions": key_functions,
        "confidence": round(min(1.0, confidence), 4),
        "routing_source": "dynamic_topology" if exact else "dynamic_advisory" if found else "none",
        "exact_symbols": exact_summaries,
        "callers": callers[:16],
        "callees": callees[:16],
        "tests": context_packet["tests"],
        "dependencies": context_packet["dependencies"],
        "source_hashes": hashes,
        "topology_digest": topology_digest,
        "context_packet": context_packet,
        "router_context": router_context,
        "context_tokens": _estimate_tokens(router_context),
        "capability_resolution": resolution,
        "capability_graph_digest": str(resolution.get("capability_graph_digest") or ""),
        "capability_path_digest": str(resolution.get("capability_path_digest") or ""),
        "required_capability_ids": list(resolution.get("required_capability_ids", []) or []),
        "warnings": context_packet["warnings"],
        "approximate_relationships_advisory": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "version": AI_ROUTER_VERSION,
    }


def query_router(
    task_description: str,
    *,
    repo_root: str | Path = ".",
    target_files: list[str] | None = None,
    target_symbols: list[str] | None = None,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    static_fallback: bool = True,
    resolver: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return bounded, topology-grounded context for an arbitrary objective.

    Dynamic resolution is always attempted first.  The generated Markdown task
    table is consulted only when exact current evidence cannot identify a file.
    """
    objective = str(task_description or "").strip()
    if not objective:
        return {
            "status": "not_found",
            "task": "",
            "available_tasks": list(load_router_index().get("tasks", {})),
            "hint": "Provide a task description.",
            "routing_source": "none",
        }
    budget = max(200, min(12000, int(token_budget)))
    try:
        result = _dynamic_route(
            objective,
            repo_root=repo_root,
            target_files=target_files,
            target_symbols=target_symbols,
            token_budget=budget,
            resolver=resolver,
        )
    except Exception as exc:  # fail closed to a visibly advisory compatibility view
        result = {
            "status": "not_found",
            "task": objective,
            "routing_source": "dynamic_error",
            "warnings": [f"dynamic_router_error:{type(exc).__name__}"],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "version": AI_ROUTER_VERSION,
        }
    if result.get("status") == "found" and result.get("routing_source") == "dynamic_topology":
        return result
    if static_fallback:
        fallback_path = str(Path(repo_root) / ROUTER_INDEX_PATH)
        fallback = _static_fallback(objective, path=fallback_path)
        if fallback.get("status") == "found" and not result.get("primary_file"):
            fallback.update({
                "dynamic_attempt": result,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                "version": AI_ROUTER_VERSION,
            })
            return fallback
    return result


def get_router_context_for_func(filepath: str, func_name: str) -> str:
    """Return the exact current source span for one Python symbol."""
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filepath)
    except (OSError, SyntaxError):
        return ""
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == func_name:
            start = int(getattr(node, "lineno", 1))
            end = int(getattr(node, "end_lineno", start))
            return "\n".join(lines[start - 1:end])
    return ""


def ai_route_command(args: str) -> str:
    """REPL command handler for ``!ai_route <task description>``."""
    objective = args.strip()
    if not objective:
        tasks = list(load_router_index().get("tasks", {}))
        suffix = "\n" + "\n".join(f"  • {task}" for task in tasks) if tasks else ""
        return "Usage: !ai_route <task description>\nStatic fallback examples:" + suffix
    result = query_router(objective)
    if result.get("status") != "found":
        return f"[AI Router] No grounded mapping found for '{objective}'."
    lines = [
        f"[AI Router] Task: '{result['task']}'",
        f"  Routing source : {result.get('routing_source')}",
        f"  Primary file   : {result.get('primary_file')}",
        f"  Secondary files: {', '.join(result.get('secondary_files', []))}",
        f"  Key functions  : {', '.join(result.get('key_functions', []))}",
        f"  Confidence     : {float(result.get('confidence', 0.0)):.2f}",
        f"  Topology digest: {result.get('topology_digest', '')}",
    ]
    if result.get("warnings"):
        lines.append("  Warnings       : " + "; ".join(result["warnings"]))
    return "\n".join(lines)


def regenerate_router(quiet: bool = False) -> bool:
    """Regenerate the Markdown compatibility view without changing authority."""
    try:
        import generate_ai_router

        markdown = generate_ai_router.build_router_md()
        Path(generate_ai_router.OUTPUT_MD).write_text(markdown, encoding="utf-8")
        global _INDEX_CACHE, _INDEX_CACHE_MTIME, _INDEX_CACHE_PATH
        _INDEX_CACHE = None
        _INDEX_CACHE_MTIME = None
        _INDEX_CACHE_PATH = None
        if not quiet:
            print(f"[+] AURA_AI_ROUTER.md regenerated ({len(markdown.splitlines())} lines)")
        return True
    except Exception as exc:
        if not quiet:
            print(f"[-] AI Router regeneration failed: {exc}")
        return False

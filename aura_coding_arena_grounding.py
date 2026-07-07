"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9e1-[Q-SYS:CODING_ARENA_GROUNDING]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Pre-Planning Code Grounding Gate)
DEPENDENCIES: __future__, dataclasses, pathlib, re, typing, aura_emergent_capability_auditor, aura_repo_localizer, aura_topological_context_anchor
FUNCTIONS: ground_coding_arena_intent, query_coding_arena_external_calls, query_coding_arena_capability_audit
SYNOPSIS: Mandatory Coding Arena pre-planning grounding facade over the existing Topological Context Anchor. Exact spans and source hashes are patch authority; affinity and resonance remain advisory only.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import re
from typing import Any

from aura_repo_localizer import EXCLUDE_DIRS, topological_context_fallback_candidates
from aura_topological_context_anchor import (
    ANCHOR_VERSION,
    PATCH_AUTHORITY_POLICY,
    CodeTopoAnchor,
    CodeTopoContextPacket,
    CodeTopoNode,
    CodeTopoResult,
    KNOWN_EXTERNAL_ROOTS,
    render_builder_context,
)


GROUNDING_VERSION = "AURA_CODING_ARENA_GROUNDING_V1"
EXTERNAL_CALL_ROUTE = "EXTERNAL_CALL_CONTEXT"
CAPABILITY_AUDIT_ROUTE = "EMERGENT_CAPABILITY_AUDIT"
_EXTERNAL_QUERY_TERMS = {
    "api",
    "apis",
    "call",
    "calls",
    "client",
    "clients",
    "external",
    "http",
    "request",
    "requests",
    "subprocess",
}
_CAPABILITY_AUDIT_TERMS = {
    "audit",
    "auditor",
    "capability",
    "capabilities",
    "emergent",
    "future",
    "potential",
    "unwired",
    "wired",
}


def ground_coding_arena_intent(
    intent: str,
    repo_root: str | Path,
    target_symbol: str | None = None,
    external_call: str | None = None,
) -> dict[str, Any]:
    """Ground Coding Arena planning in exact repository topology before any Builder patch."""
    root = Path(repo_root).resolve()
    if not target_symbol and external_call is None and _asks_for_capability_audit(intent):
        return query_coding_arena_capability_audit(intent, root)

    anchor = _build_repo_anchor(root)
    warnings = list(anchor.warnings)
    external_result: CodeTopoResult | None = None
    symbol_result: CodeTopoResult | None = None
    context_packet: CodeTopoContextPacket | None = None
    candidate_files: list[dict[str, Any]] = []

    external_pattern = external_call
    if external_pattern is None:
        external_pattern = _external_pattern_from_intent(intent)
    if external_pattern is not None:
        external_result = anchor.lookup_external_call(external_pattern)
    elif _asks_for_external_calls(intent):
        external_result = anchor.lookup_external_call("")

    if target_symbol:
        symbol_result = anchor.lookup_symbol(target_symbol)
        context_packet = anchor.nearest_context(target_symbol, radius=1)

    if target_symbol and (symbol_result is None or not symbol_result.exact_hits):
        candidate_files = _fallback_candidates(intent, root)
    elif not target_symbol and external_result is None:
        candidate_files = _fallback_candidates(intent, root)

    route, route_reasons = _route_grounding(
        anchor=anchor,
        external_result=external_result,
        symbol_result=symbol_result,
        context_packet=context_packet,
        candidate_files=candidate_files,
        target_symbol=target_symbol,
    )
    warnings = _unique([*warnings, *_result_warnings(external_result), *_result_warnings(symbol_result)])

    exact_hits = _nodes_to_dict(_result_hits(external_result) + _result_hits(symbol_result))
    external_calls = list(external_result.external_calls if external_result else [])
    source_spans = _source_spans(anchor, context_packet, external_calls)
    tests = _unique([
        *(context_packet.tests if context_packet else []),
        *(external_result.tests if external_result else []),
        *(symbol_result.tests if symbol_result else []),
    ])
    hashes = dict(context_packet.hashes if context_packet else {})
    for span in source_spans:
        node_id = str(span.get("node_id") or "")
        source_hash = str(span.get("source_hash") or "")
        file_path = str(span.get("file_path") or "")
        file_hash = str(span.get("file_source_hash") or "")
        if node_id and source_hash:
            hashes[node_id] = source_hash
        if file_path and file_hash:
            hashes[file_path] = file_hash

    target_file = _target_file(source_spans, external_calls, candidate_files)
    resolved_target_symbol = target_symbol or _target_symbol(symbol_result)
    builder_context = render_builder_context(context_packet) if context_packet and context_packet.source_spans else ""
    grounding_ok = route in {"BUILDER_PATCH", "TEST_GAP_FILL", EXTERNAL_CALL_ROUTE, "LOCALIZE_FIRST"} and route != "BLOCKED_WITH_REASON"
    if route == "LOCALIZE_FIRST" and not (candidate_files or external_calls):
        grounding_ok = False

    packet = {
        "version": GROUNDING_VERSION,
        "anchor_version": ANCHOR_VERSION,
        "grounding_ok": grounding_ok,
        "route": route,
        "target_file": target_file,
        "target_symbol": resolved_target_symbol,
        "exact_hits": exact_hits,
        "external_calls": external_calls,
        "candidate_files": candidate_files[:5],
        "source_spans": source_spans,
        "tests": tests,
        "hashes": hashes,
        "warnings": warnings,
        "route_reasons": route_reasons,
        "builder_context": builder_context,
        "route_diagnostics": {
            "route": route,
            "reasons": route_reasons,
            "patch_authority": PATCH_AUTHORITY_POLICY,
            "vsa_patch_authority": False,
        },
        "safety_policy": PATCH_AUTHORITY_POLICY,
        "vsa_patch_authority": False,
    }
    return packet


def query_coding_arena_external_calls(
    pattern: str | None,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Return exact external-call evidence for known API/process calls."""
    query = "" if pattern is None else str(pattern)
    return ground_coding_arena_intent(
        f"external calls {query}".strip(),
        repo_root,
        external_call=query,
    )


def query_coding_arena_capability_audit(
    intent: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Return a read-only emergent capability audit for Coding Arena query intents."""
    from aura_emergent_capability_auditor import query_capability_audit

    return query_capability_audit(intent, repo_root)


def _build_repo_anchor(root: Path) -> CodeTopoAnchor:
    return CodeTopoAnchor.build_from_files(_repo_python_sources(root))


def _repo_python_sources(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.glob("**/*.py")):
        relative = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        try:
            files[relative.as_posix()] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return files


def _external_pattern_from_intent(intent: str) -> str | None:
    lowered = str(intent or "").lower()
    if not _asks_for_external_calls(lowered):
        return None
    known_roots = sorted(KNOWN_EXTERNAL_ROOTS, key=len, reverse=True)
    for root in known_roots:
        dotted = re.search(rf"\b{re.escape(root)}(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?\b", lowered)
        if dotted:
            return dotted.group(0)
    return None


def _asks_for_external_calls(intent: str) -> bool:
    lowered = str(intent or "").lower()
    tokens = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", lowered))
    patch_terms = {"add", "build", "create", "fix", "implement", "patch", "update", "wire", "write"}
    if tokens & patch_terms:
        return False
    if any(root in lowered for root in KNOWN_EXTERNAL_ROOTS):
        return True
    return bool(tokens & _EXTERNAL_QUERY_TERMS) and bool({"where", "list", "show", "find", "all"} & tokens)


def _asks_for_capability_audit(intent: str) -> bool:
    lowered = str(intent or "").lower()
    tokens = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", lowered))
    patch_terms = {"add", "build", "create", "fix", "implement", "patch", "update", "wire", "write"}
    if tokens & patch_terms:
        return False
    query_terms = {"audit", "auditor", "discover", "find", "list", "query", "report", "show"}
    if ("emergent capability" in lowered or "capability audit" in lowered) and tokens & query_terms:
        return True
    if ("future potential" in lowered or "future potentials" in lowered) and tokens & query_terms:
        return True
    capability_terms = _CAPABILITY_AUDIT_TERMS - {"audit", "auditor"}
    return bool(tokens & query_terms) and bool(tokens & capability_terms)


def _fallback_candidates(intent: str, root: Path) -> list[dict[str, Any]]:
    candidates = topological_context_fallback_candidates(intent, root, limit=5)
    return [asdict(item) for item in candidates[:5]]


def _route_grounding(
    *,
    anchor: CodeTopoAnchor,
    external_result: CodeTopoResult | None,
    symbol_result: CodeTopoResult | None,
    context_packet: CodeTopoContextPacket | None,
    candidate_files: list[dict[str, Any]],
    target_symbol: str | None,
) -> tuple[str, list[str]]:
    syntax_warnings = [item for item in anchor.warnings if "syntax_error" in item]
    if external_result is not None:
        if external_result.external_calls:
            return EXTERNAL_CALL_ROUTE, ["external_call_context", PATCH_AUTHORITY_POLICY]
        if syntax_warnings:
            return "BLOCKED_WITH_REASON", ["external_call_unresolved", *syntax_warnings]
        return "LOCALIZE_FIRST", ["external_call_unresolved"]

    if target_symbol:
        if symbol_result and symbol_result.exact_hits:
            tests = context_packet.tests if context_packet else symbol_result.tests
            if tests:
                return "BUILDER_PATCH", ["exact_symbol_grounded", "tests_exist", PATCH_AUTHORITY_POLICY]
            return "TEST_GAP_FILL", ["exact_symbol_grounded", "missing_tests_or_verifier_evidence", PATCH_AUTHORITY_POLICY]
        if syntax_warnings:
            return "BLOCKED_WITH_REASON", ["target_symbol_unresolved", *syntax_warnings]
        return "LOCALIZE_FIRST", ["target_symbol_unresolved"]

    if candidate_files:
        return "LOCALIZE_FIRST", ["fallback_candidates_from_topological_anchor"]
    if syntax_warnings:
        return "BLOCKED_WITH_REASON", ["unsafe_parse_diagnostics", *syntax_warnings]
    return "LOCALIZE_FIRST", ["no_exact_target_provided"]


def _source_spans(
    anchor: CodeTopoAnchor,
    context_packet: CodeTopoContextPacket | None,
    external_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if context_packet and context_packet.source_spans:
        return list(context_packet.source_spans)
    spans: list[dict[str, Any]] = []
    for call in external_calls[:24]:
        caller_span = list(call.get("caller_span", []) or [])
        if len(caller_span) != 2:
            continue
        file_path = str(call.get("file_path") or "")
        start, end = int(caller_span[0] or 0), int(caller_span[1] or 0)
        source = _slice_source(anchor.source_texts.get(file_path, ""), start, end)
        spans.append(
            {
                "role": "external_call",
                "node_id": str(call.get("caller_node_id") or ""),
                "file_path": file_path,
                "symbol": str(call.get("caller_symbol") or ""),
                "kind": "caller",
                "start_line": start,
                "end_line": end,
                "line": int(call.get("line", 0) or 0),
                "call": str(call.get("call") or ""),
                "resolved_call": str(call.get("resolved_call") or ""),
                "source_hash": str(call.get("source_hash") or ""),
                "file_source_hash": anchor.file_hashes.get(file_path, ""),
                "source": source,
            }
        )
    return spans


def _slice_source(source: str, start_line: int, end_line: int) -> str:
    lines = str(source or "").splitlines()
    if not lines or start_line <= 0 or end_line <= 0:
        return ""
    start = max(1, start_line)
    end = min(len(lines), max(start, end_line))
    return "\n".join(lines[start - 1 : end])


def _target_file(
    source_spans: list[dict[str, Any]],
    external_calls: list[dict[str, Any]],
    candidate_files: list[dict[str, Any]],
) -> str | None:
    for span in source_spans:
        file_path = str(span.get("file_path") or "")
        if file_path:
            return file_path
    for call in external_calls:
        file_path = str(call.get("file_path") or "")
        if file_path:
            return file_path
    for candidate in candidate_files:
        path = str(candidate.get("path") or "")
        if path:
            return path
    return None


def _target_symbol(symbol_result: CodeTopoResult | None) -> str | None:
    if not symbol_result or not symbol_result.exact_hits:
        return None
    return symbol_result.exact_hits[0].symbol


def _result_hits(result: CodeTopoResult | None) -> list[CodeTopoNode]:
    return list(result.exact_hits if result else [])


def _nodes_to_dict(nodes: list[CodeTopoNode]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for node in nodes:
        if node.node_id in seen:
            continue
        seen.add(node.node_id)
        output.append(node.to_dict())
    return output


def _result_warnings(result: CodeTopoResult | None) -> list[str]:
    return list(result.warnings if result else [])


def _unique(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for value in values:
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output

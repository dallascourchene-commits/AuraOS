"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9e7-[Q-SYS:EMERGENT_CAPABILITY_AUDIT]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Read-Only Capability Topology Audit)
DEPENDENCIES: __future__, dataclasses, hashlib, pathlib, re, typing, aura_repo_localizer, aura_topological_context_anchor
FUNCTIONS: CapabilitySymbol, CapabilityEdge, EmergentCapabilityFinding, FuturePotentialFinding, CapabilityAuditReport, audit_emergent_capabilities, find_unwired_capability_pairs, project_future_potentials, render_capability_audit_report, query_capability_audit
SYNOPSIS: Deterministic read-only audit over CodeTopoAnchor that finds complementary Aura capabilities which exist in the repo topology but are not directly wired.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from aura_repo_localizer import EXCLUDE_DIRS
from aura_topological_context_anchor import (
    PATCH_AUTHORITY_POLICY,
    CodeTopoAnchor,
    CodeTopoEdge,
    CodeTopoNode,
)


CAPABILITY_AUDIT_VERSION = "AURA_EMERGENT_CAPABILITY_AUDIT_V1"
AUDIT_ROUTE = "EMERGENT_CAPABILITY_AUDIT"

ROLE_ORDER = [
    "CAPABILITY_AUDIT",
    "TOPOLOGICAL_CONTEXT",
    "ST3GG_ENCODING",
    "VSA_ENCODING",
    "MUSIC_RANKING",
    "BUILDER_CONTEXT",
    "PATCH_STAGING",
    "VERIFICATION",
    "LOCALIZATION",
    "ROUTING",
    "RESEARCH_TRIAGE",
    "API_CALLING",
    "HOTSWAP",
]

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CAPABILITY_AUDIT": ("capability", "audit", "emergent", "unwired", "future_potential"),
    "TOPOLOGICAL_CONTEXT": ("topological", "topo", "context_anchor", "codetopo", "source_span", "source_hash"),
    "ST3GG_ENCODING": ("st3gg", "codec", "token_budget", "token", "base"),
    "VSA_ENCODING": ("vsa", "vector", "sketch", "similarity", "affinity"),
    "MUSIC_RANKING": ("music", "mitosis", "resonance", "ranking", "fusion"),
    "BUILDER_CONTEXT": ("builder_context", "buildercontext", "context_packet", "act worker", "prompt_section"),
    "PATCH_STAGING": ("patch", "stage_arena_patch", "preflight", "repair", "unified_diff"),
    "VERIFICATION": ("verify", "verification", "pytest", "test_gap", "quality_gate", "shadow"),
    "LOCALIZATION": ("localizer", "localize", "localized", "codemap", "grounding", "fallback_candidate"),
    "ROUTING": ("route", "router", "plan_intent", "select_plan", "deterministic_plan", "budget_route"),
    "RESEARCH_TRIAGE": ("research", "paper", "triage", "survey", "discovery"),
    "API_CALLING": ("requests", "httpx", "openai", "anthropic", "subprocess", "external_call", "api"),
    "HOTSWAP": ("hotswap", "hot_swap", "incubator", "rollback", "live_transaction"),
}

COMPLEMENTARY_ROLE_PAIRS = {
    frozenset(("ST3GG_ENCODING", "TOPOLOGICAL_CONTEXT")),
    frozenset(("VSA_ENCODING", "LOCALIZATION")),
    frozenset(("MUSIC_RANKING", "BUILDER_CONTEXT")),
    frozenset(("BUILDER_CONTEXT", "PATCH_STAGING")),
    frozenset(("PATCH_STAGING", "VERIFICATION")),
    frozenset(("API_CALLING", "VERIFICATION")),
    frozenset(("LOCALIZATION", "ROUTING")),
    frozenset(("RESEARCH_TRIAGE", "ROUTING")),
    frozenset(("CAPABILITY_AUDIT", "ROUTING")),
    frozenset(("TOPOLOGICAL_CONTEXT", "BUILDER_CONTEXT")),
    frozenset(("HOTSWAP", "VERIFICATION")),
}

SUBSYSTEM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "coding_arena": ("coding_arena", "architect", "act", "arena", "builder"),
    "music": ("music", "mitosis", "resonance"),
    "st3gg": ("st3gg", "codec", "token"),
    "vsa": ("vsa", "vector", "sketch", "similarity"),
    "builder": ("builder_context", "builder", "context_packet"),
    "verifier": ("verify", "verification", "test", "quality_gate", "preflight"),
    "hotswap": ("hotswap", "rollback", "incubator"),
    "repo_localizer": ("repo_localizer", "localizer", "localize", "codemap"),
    "research": ("research", "paper", "triage"),
    "external_api": ("external", "api", "requests", "httpx", "openai", "subprocess"),
    "capability_audit": ("capability", "audit", "emergent"),
}


@dataclass
class CapabilitySymbol:
    symbol_id: str
    role: str
    file_path: str
    symbol: str
    kind: str
    start_line: int
    end_line: int
    source_hash: str
    file_source_hash: str = ""
    role_tags: list[str] = field(default_factory=list)
    subsystem_tags: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityEdge:
    src_symbol_id: str
    dst_symbol_id: str
    edge_type: str
    evidence: str
    confidence: float = 1.0
    exists_now: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmergentCapabilityFinding:
    finding_id: str
    title: str
    subsystem: str
    symbols: list[CapabilitySymbol]
    proposed_edges: list[CapabilityEdge]
    missing_edges: list[dict[str, Any]]
    rationale: str
    evidence: list[dict[str, Any]]
    tests: list[str] = field(default_factory=list)
    confidence: float = 0.0
    safe_to_patch: bool = False
    route: str = AUDIT_ROUTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "subsystem": self.subsystem,
            "symbols": [symbol.to_dict() for symbol in self.symbols],
            "proposed_edges": [edge.to_dict() for edge in self.proposed_edges],
            "missing_edges": self.missing_edges,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "tests": self.tests,
            "confidence": self.confidence,
            "safe_to_patch": self.safe_to_patch,
            "route": self.route,
        }


@dataclass
class FuturePotentialFinding:
    finding_id: str
    title: str
    subsystem: str
    required_roles: list[str]
    present_symbols: list[CapabilitySymbol]
    rationale: str
    blockers: list[str] = field(default_factory=list)
    confidence: float = 0.0
    safe_to_patch: bool = False
    route: str = AUDIT_ROUTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "subsystem": self.subsystem,
            "required_roles": self.required_roles,
            "present_symbols": [symbol.to_dict() for symbol in self.present_symbols],
            "rationale": self.rationale,
            "blockers": self.blockers,
            "confidence": self.confidence,
            "safe_to_patch": self.safe_to_patch,
            "route": self.route,
        }


@dataclass
class CapabilityAuditReport:
    version: str
    route: str
    query: str
    subsystem: str
    symbol_count: int
    edge_count: int
    findings: list[EmergentCapabilityFinding] = field(default_factory=list)
    future_potentials: list[FuturePotentialFinding] = field(default_factory=list)
    direct_edges: list[CapabilityEdge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    safe_to_patch: bool = False
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "route": self.route,
            "query": self.query,
            "subsystem": self.subsystem,
            "symbol_count": self.symbol_count,
            "edge_count": self.edge_count,
            "findings": [finding.to_dict() for finding in self.findings],
            "future_potentials": [finding.to_dict() for finding in self.future_potentials],
            "direct_edges": [edge.to_dict() for edge in self.direct_edges],
            "warnings": self.warnings,
            "safe_to_patch": self.safe_to_patch,
            "summary": self.summary,
        }


def audit_emergent_capabilities(
    repo_root_or_anchor: str | Path | CodeTopoAnchor,
    *,
    subsystem: str | None = None,
    query: str = "",
    include_future: bool = True,
    limit: int = 20,
) -> CapabilityAuditReport:
    """Return a read-only capability audit over the current CodeTopoAnchor graph."""
    anchor = _coerce_anchor(repo_root_or_anchor)
    requested_subsystem = _normalize_subsystem(subsystem)
    symbols = _symbols_from_anchor(anchor)
    edges = _edges_from_anchor(anchor)
    findings = find_unwired_capability_pairs(
        symbols,
        edges,
        subsystem=requested_subsystem,
        query=query,
        limit=limit,
    )
    future_potentials = (
        project_future_potentials(symbols, edges, subsystem=requested_subsystem, limit=limit)
        if include_future
        else []
    )
    summary = {
        "finding_count": len(findings),
        "future_potential_count": len(future_potentials),
        "safe_to_patch": False,
        "patch_authority": PATCH_AUTHORITY_POLICY,
        "note": "Read-only audit. Findings identify candidate topology gaps only.",
    }
    return CapabilityAuditReport(
        version=CAPABILITY_AUDIT_VERSION,
        route=AUDIT_ROUTE,
        query=query,
        subsystem=requested_subsystem or "all",
        symbol_count=len(symbols),
        edge_count=len(edges),
        findings=findings,
        future_potentials=future_potentials,
        direct_edges=edges[:50],
        warnings=list(anchor.warnings),
        safe_to_patch=False,
        summary=summary,
    )


def find_unwired_capability_pairs(
    symbols_or_anchor: list[CapabilitySymbol] | CodeTopoAnchor,
    edges: list[CapabilityEdge] | None = None,
    *,
    subsystem: str | None = None,
    query: str = "",
    limit: int = 20,
) -> list[EmergentCapabilityFinding]:
    """Find complementary capability symbols that have no direct topology edge."""
    if isinstance(symbols_or_anchor, CodeTopoAnchor):
        symbols = _symbols_from_anchor(symbols_or_anchor)
        capability_edges = _edges_from_anchor(symbols_or_anchor)
    else:
        symbols = list(symbols_or_anchor)
        capability_edges = list(edges or [])
    requested_subsystem = _normalize_subsystem(subsystem)
    filtered = [symbol for symbol in symbols if _symbol_matches_subsystem(symbol, requested_subsystem)]
    direct_pairs = {
        frozenset((edge.src_symbol_id, edge.dst_symbol_id))
        for edge in capability_edges
        if edge.exists_now
    }
    findings: list[EmergentCapabilityFinding] = []
    for index, left in enumerate(filtered):
        for right in filtered[index + 1 :]:
            if not _roles_are_complementary(left, right):
                continue
            pair_key = frozenset((left.symbol_id, right.symbol_id))
            if pair_key in direct_pairs:
                continue
            confidence = _pair_confidence(left, right, query=query)
            edge = CapabilityEdge(
                src_symbol_id=left.symbol_id,
                dst_symbol_id=right.symbol_id,
                edge_type="candidate_bridge",
                evidence="No direct call/import/test edge exists in CodeTopoAnchor.",
                confidence=confidence,
                exists_now=False,
            )
            finding_subsystem = requested_subsystem or _shared_or_primary_subsystem(left, right)
            missing_edge = {
                "src_role": left.role,
                "dst_role": right.role,
                "reason": "complementary_roles_without_direct_topology_edge",
                "patch_authority": PATCH_AUTHORITY_POLICY,
            }
            finding = EmergentCapabilityFinding(
                finding_id=_stable_id("unwired", left.symbol_id, right.symbol_id, left.role, right.role),
                title=f"Unwired {left.role} + {right.role}: {left.symbol} <-> {right.symbol}",
                subsystem=finding_subsystem,
                symbols=[left, right],
                proposed_edges=[edge],
                missing_edges=[missing_edge],
                rationale=(
                    "Both capabilities are present with exact source spans, but the anchor has no direct topology edge "
                    "between them. Treat this as an audit lead, not patch approval."
                ),
                evidence=[left.evidence, right.evidence],
                tests=_unique([*left.tests, *right.tests]),
                confidence=confidence,
                safe_to_patch=False,
            )
            findings.append(finding)
    return sorted(
        findings,
        key=lambda item: (-item.confidence, item.subsystem, item.title, item.finding_id),
    )[: max(0, limit)]


def project_future_potentials(
    symbols_or_anchor: list[CapabilitySymbol] | CodeTopoAnchor,
    edges: list[CapabilityEdge] | None = None,
    *,
    subsystem: str | None = None,
    limit: int = 12,
) -> list[FuturePotentialFinding]:
    """Project safe read-only future capabilities from currently present role clusters."""
    if isinstance(symbols_or_anchor, CodeTopoAnchor):
        symbols = _symbols_from_anchor(symbols_or_anchor)
    else:
        symbols = list(symbols_or_anchor)
    requested_subsystem = _normalize_subsystem(subsystem)
    filtered = [symbol for symbol in symbols if _symbol_matches_subsystem(symbol, requested_subsystem)]
    by_role: dict[str, list[CapabilitySymbol]] = {}
    for symbol in filtered:
        for role in symbol.role_tags or [symbol.role]:
            by_role.setdefault(role, []).append(symbol)

    rules = [
        (
            "token_budget_context_benchmark",
            "ST3GG token budget benchmark from exact topological context",
            ["ST3GG_ENCODING", "TOPOLOGICAL_CONTEXT", "VERIFICATION"],
            "coding_arena",
            "ST3GG encoding, exact source spans, and verifier evidence can support a future benchmark harness.",
        ),
        (
            "music_builder_context_ranker",
            "MUSIC ranking can prioritize Builder context candidates",
            ["MUSIC_RANKING", "BUILDER_CONTEXT", "LOCALIZATION"],
            "coding_arena",
            "Music resonance and grounded Builder packets are both present but should remain advisory until explicitly wired.",
        ),
        (
            "external_call_policy_auditor",
            "External call policy auditor over verified API topology",
            ["API_CALLING", "TOPOLOGICAL_CONTEXT", "VERIFICATION"],
            "external_api",
            "External call evidence can be paired with tests to audit side-effect boundaries.",
        ),
        (
            "research_to_route_grounding",
            "Research triage to routing bridge",
            ["RESEARCH_TRIAGE", "ROUTING", "LOCALIZATION"],
            "research",
            "Research triage and deterministic routing can be inspected together before any planning change.",
        ),
        (
            "capability_audit_query_route",
            "Capability audit query route hardening",
            ["CAPABILITY_AUDIT", "ROUTING", "TOPOLOGICAL_CONTEXT"],
            "capability_audit",
            "Capability audit symbols and router symbols can support future read-only query diagnostics.",
        ),
    ]
    potentials: list[FuturePotentialFinding] = []
    for rule_id, title, roles, default_subsystem, rationale in rules:
        if requested_subsystem and default_subsystem != requested_subsystem:
            continue
        if not all(by_role.get(role) for role in roles):
            continue
        present: list[CapabilitySymbol] = []
        for role in roles:
            present.extend(by_role.get(role, [])[:2])
        blockers = [
            "read_only_audit",
            "requires_explicit_design_review",
            "safe_to_patch_false_until_exact_patch_scope_exists",
        ]
        confidence = round(0.55 + min(len(present), 6) * 0.05, 4)
        potentials.append(
            FuturePotentialFinding(
                finding_id=_stable_id("future", rule_id, *(symbol.symbol_id for symbol in present)),
                title=title,
                subsystem=default_subsystem,
                required_roles=list(roles),
                present_symbols=_dedupe_symbols(present)[:6],
                rationale=rationale,
                blockers=blockers,
                confidence=min(confidence, 0.9),
                safe_to_patch=False,
            )
        )
    return sorted(potentials, key=lambda item: (-item.confidence, item.title))[: max(0, limit)]


def record_capability_audit_trace_nodes(
    report: CapabilityAuditReport | dict[str, Any],
    memory_root: str | Path,
    *,
    task_id: str = "emergent_capability_audit",
) -> list[str]:
    """Store read-only findings/future potentials as symbolic trace nodes."""
    try:
        from aura_symbolic_trace_memory import record_trace_event
    except Exception:
        return []
    payload = report.to_dict() if isinstance(report, CapabilityAuditReport) else dict(report or {})
    atom_ids: list[str] = []
    entries = [
        ("emergent_capability_finding", item)
        for item in list(payload.get("findings", []) or [])
        if isinstance(item, dict)
    ]
    entries.extend(
        ("future_potential_finding", item)
        for item in list(payload.get("future_potentials", []) or [])
        if isinstance(item, dict)
    )
    for event_type, item in entries:
        finding_id = str(item.get("finding_id") or _stable_id(event_type, item.get("title", "")))
        symbols = item.get("symbols") or item.get("present_symbols") or []
        related_symbols = [
            str(symbol.get("symbol"))
            for symbol in symbols
            if isinstance(symbol, dict) and symbol.get("symbol")
        ]
        related_files = [
            str(symbol.get("file_path"))
            for symbol in symbols
            if isinstance(symbol, dict) and symbol.get("file_path")
        ]
        try:
            atom = record_trace_event(
                {
                    "event_type": event_type,
                    "task_id": task_id,
                    "node_id": finding_id,
                    "status": "proposed",
                    "route": payload.get("route", AUDIT_ROUTE),
                    "summary": str(item.get("title") or event_type),
                    "raw_text": json.dumps(item, indent=2, sort_keys=True, default=str),
                    "metadata": {
                        "subsystem": item.get("subsystem", payload.get("subsystem", "")),
                        "safe_to_patch": item.get("safe_to_patch", False),
                        "related_symbols": _unique(related_symbols),
                        "related_files": _unique(related_files),
                    },
                },
                memory_root,
            )
            atom_ids.append(atom.atom_id)
        except Exception:
            continue
    return atom_ids


def render_capability_audit_report(report: CapabilityAuditReport | dict[str, Any]) -> str:
    """Render a compact text report for query responses and PR review."""
    payload = report.to_dict() if isinstance(report, CapabilityAuditReport) else dict(report)
    lines = [
        "=== AURA EMERGENT CAPABILITY AUDIT ===",
        f"version: {payload.get('version', CAPABILITY_AUDIT_VERSION)}",
        f"route: {payload.get('route', AUDIT_ROUTE)}",
        f"subsystem: {payload.get('subsystem', 'all')}",
        f"safe_to_patch: {payload.get('safe_to_patch', False)}",
        f"symbols: {payload.get('symbol_count', 0)}",
        f"edges: {payload.get('edge_count', 0)}",
    ]
    findings = list(payload.get("findings", []) or [])
    futures = list(payload.get("future_potentials", []) or [])
    lines.append(f"unwired_findings: {len(findings)}")
    for finding in findings[:8]:
        symbols = finding.get("symbols", []) if isinstance(finding, dict) else []
        labels = [
            f"{symbol.get('role')}:{symbol.get('file_path')}:{symbol.get('symbol')}"
            for symbol in symbols[:2]
            if isinstance(symbol, dict)
        ]
        lines.append(f"- {finding.get('finding_id')}: {finding.get('title')}")
        if labels:
            lines.append("  evidence: " + " | ".join(labels))
        lines.append(f"  confidence: {finding.get('confidence', 0.0)} safe_to_patch=False")
    lines.append(f"future_potentials: {len(futures)}")
    for potential in futures[:6]:
        roles = ", ".join(str(role) for role in potential.get("required_roles", []) or [])
        lines.append(f"- {potential.get('finding_id')}: {potential.get('title')} roles=[{roles}] safe_to_patch=False")
    lines.append("patch_authority: exact source spans and hashes only; audit findings are not patch submissions")
    lines.append("=== END AURA EMERGENT CAPABILITY AUDIT ===")
    return "\n".join(lines)


def query_capability_audit(intent: str, repo_root: str | Path) -> dict[str, Any]:
    """Query entrypoint for Coding Arena intents that request emergent capability auditing."""
    subsystem = _subsystem_from_intent(intent)
    report = audit_emergent_capabilities(
        repo_root,
        subsystem=subsystem,
        query=str(intent or ""),
        include_future=True,
    )
    return {
        "version": CAPABILITY_AUDIT_VERSION,
        "route": AUDIT_ROUTE,
        "grounding_ok": True,
        "safe_to_patch": False,
        "target_file": None,
        "target_symbol": None,
        "report": report.to_dict(),
        "rendered": render_capability_audit_report(report),
        "route_reasons": ["read_only_emergent_capability_audit", PATCH_AUTHORITY_POLICY],
        "route_diagnostics": {
            "route": AUDIT_ROUTE,
            "reasons": ["read_only_emergent_capability_audit"],
            "patch_authority": PATCH_AUTHORITY_POLICY,
            "safe_to_patch": False,
            "vsa_patch_authority": False,
        },
        "safety_policy": PATCH_AUTHORITY_POLICY,
        "vsa_patch_authority": False,
    }


def _coerce_anchor(repo_root_or_anchor: str | Path | CodeTopoAnchor) -> CodeTopoAnchor:
    if isinstance(repo_root_or_anchor, CodeTopoAnchor):
        return repo_root_or_anchor
    root = Path(repo_root_or_anchor).resolve()
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


def _symbols_from_anchor(anchor: CodeTopoAnchor) -> list[CapabilitySymbol]:
    symbols: list[CapabilitySymbol] = []
    for node in sorted(anchor.nodes.values(), key=lambda item: (item.file_path, item.start_line, item.symbol)):
        if node.kind == "module":
            continue
        role_tags = _classify_roles(node, anchor)
        if role_tags == ["GENERAL_CODE"]:
            continue
        subsystem_tags = _classify_subsystems(node, role_tags)
        symbols.append(
            CapabilitySymbol(
                symbol_id=node.node_id,
                role=role_tags[0],
                file_path=node.file_path,
                symbol=node.symbol,
                kind=node.kind,
                start_line=node.start_line,
                end_line=node.end_line,
                source_hash=node.source_hash,
                file_source_hash=str(node.metadata.get("file_source_hash") or anchor.file_hashes.get(node.file_path, "")),
                role_tags=role_tags,
                subsystem_tags=subsystem_tags,
                tests=_tests_for_node(anchor, node.node_id),
                calls=list(node.calls),
                evidence=_node_evidence(anchor, node),
            )
        )
    return symbols


def _edges_from_anchor(anchor: CodeTopoAnchor) -> list[CapabilityEdge]:
    edges: list[CapabilityEdge] = []
    for edge in anchor.edges:
        if edge.src_id not in anchor.nodes or edge.dst_id not in anchor.nodes:
            continue
        if anchor.nodes[edge.src_id].kind == "module" or anchor.nodes[edge.dst_id].kind == "module":
            continue
        edges.append(_capability_edge(edge))
    return edges


def _capability_edge(edge: CodeTopoEdge) -> CapabilityEdge:
    return CapabilityEdge(
        src_symbol_id=edge.src_id,
        dst_symbol_id=edge.dst_id,
        edge_type=edge.edge_type,
        evidence=edge.evidence,
        confidence=edge.confidence,
        exists_now=True,
    )


def _classify_roles(node: CodeTopoNode, anchor: CodeTopoAnchor) -> list[str]:
    text = _node_search_text(node, anchor)
    roles = [
        role
        for role in ROLE_ORDER
        if any(keyword in text for keyword in ROLE_KEYWORDS.get(role, ()))
    ]
    return roles or ["GENERAL_CODE"]


def _classify_subsystems(node: CodeTopoNode, role_tags: list[str]) -> list[str]:
    text = " ".join([
        node.file_path,
        node.symbol,
        node.kind,
        " ".join(node.calls),
        " ".join(role_tags),
    ]).lower()
    tags = [
        subsystem
        for subsystem, keywords in SUBSYSTEM_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    if not tags:
        tags.append("general")
    return tags


def _node_search_text(node: CodeTopoNode, anchor: CodeTopoAnchor) -> str:
    source = _source_excerpt(anchor, node, max_lines=24)
    parts = [
        node.file_path,
        node.symbol,
        node.kind,
        node.parent_symbol or "",
        " ".join(node.imports),
        " ".join(node.calls),
        " ".join(node.decorators),
        source,
    ]
    return " ".join(parts).replace("-", "_").lower()


def _node_evidence(anchor: CodeTopoAnchor, node: CodeTopoNode) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "file_path": node.file_path,
        "symbol": node.symbol,
        "kind": node.kind,
        "start_line": node.start_line,
        "end_line": node.end_line,
        "source_hash": node.source_hash,
        "file_source_hash": anchor.file_hashes.get(node.file_path, ""),
        "source_excerpt": _source_excerpt(anchor, node, max_lines=8),
    }


def _source_excerpt(anchor: CodeTopoAnchor, node: CodeTopoNode, *, max_lines: int) -> str:
    source = anchor.source_texts.get(node.file_path, "")
    lines = source.splitlines()
    if not lines:
        return ""
    start = max(1, node.start_line)
    end = min(len(lines), max(start, node.end_line))
    selected = lines[start - 1 : min(end, start + max_lines - 1)]
    return "\n".join(selected)


def _tests_for_node(anchor: CodeTopoAnchor, node_id: str) -> list[str]:
    try:
        return list(anchor._tests_for_nodes([node_id]))  # noqa: SLF001 - CodeTopoAnchor has no public single-node test accessor.
    except Exception:
        return []


def _roles_are_complementary(left: CapabilitySymbol, right: CapabilitySymbol) -> bool:
    left_roles = set(left.role_tags or [left.role])
    right_roles = set(right.role_tags or [right.role])
    for left_role in left_roles:
        for right_role in right_roles:
            if frozenset((left_role, right_role)) in COMPLEMENTARY_ROLE_PAIRS:
                return True
    return False


def _pair_confidence(left: CapabilitySymbol, right: CapabilitySymbol, *, query: str = "") -> float:
    score = 0.52
    if set(left.subsystem_tags) & set(right.subsystem_tags):
        score += 0.16
    if left.tests or right.tests:
        score += 0.08
    if left.file_path == right.file_path:
        score += 0.08
    if query:
        query_tokens = set(_tokens(query))
        symbol_text = set(_tokens(" ".join([left.symbol, right.symbol, left.file_path, right.file_path])))
        if query_tokens & symbol_text:
            score += 0.06
    return round(min(score, 0.92), 4)


def _symbol_matches_subsystem(symbol: CapabilitySymbol, subsystem: str | None) -> bool:
    if not subsystem or subsystem == "all":
        return True
    return subsystem in symbol.subsystem_tags


def _shared_or_primary_subsystem(left: CapabilitySymbol, right: CapabilitySymbol) -> str:
    shared = sorted(set(left.subsystem_tags) & set(right.subsystem_tags))
    if shared:
        return shared[0]
    for symbol in (left, right):
        for tag in symbol.subsystem_tags:
            if tag != "general":
                return tag
    return "all"


def _subsystem_from_intent(intent: str) -> str | None:
    lowered = str(intent or "").replace("-", "_").lower()
    if "all" in _tokens(lowered):
        return "all"
    explicit_names = sorted(
        SUBSYSTEM_KEYWORDS,
        key=lambda item: (item.count("_"), len(item)),
        reverse=True,
    )
    phrase_text = lowered.replace("_", " ")
    for subsystem in explicit_names:
        if subsystem in lowered or subsystem.replace("_", " ") in phrase_text:
            return subsystem
    for subsystem, keywords in SUBSYSTEM_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return subsystem
    return "all"


def _normalize_subsystem(subsystem: str | None) -> str | None:
    if not subsystem:
        return None
    normalized = str(subsystem).replace("-", "_").lower().strip()
    if normalized in {"", "any", "all"}:
        return "all"
    return normalized


def _dedupe_symbols(symbols: Iterable[CapabilitySymbol]) -> list[CapabilitySymbol]:
    seen: set[str] = set()
    output: list[CapabilitySymbol] = []
    for symbol in symbols:
        if symbol.symbol_id in seen:
            continue
        seen.add(symbol.symbol_id)
        output.append(symbol)
    return output


def _unique(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for value in values:
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", str(text or "").lower())


def _stable_id(*parts: Any) -> str:
    body = "|".join(str(part) for part in parts)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=8).hexdigest()

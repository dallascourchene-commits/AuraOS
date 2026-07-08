"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f2-[Q-SYS:EMERGENT_POTENTIAL_REPL]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Read-Only Future Potential Audit)
DEPENDENCIES: __future__, dataclasses, hashlib, json, pathlib, shlex, typing, aura_emergent_capability_auditor, aura_repo_localizer, aura_topological_context_anchor
FUNCTIONS: AbilityAtom, EmergentConnection, FuturePotentialQuery, EmergentPotentialReport, build_demo_fixture_anchor, parse_emerge_command, audit_emergent_potential, render_emergent_potential_report, handle_emergent_potential_command, query_emergent_potential_packet, is_emergent_potential_intent
SYNOPSIS: Read-only REPL/audit surface for emergent properties and future potential. It reports unwired local capabilities and possible future combinations without generating patches or unified diffs.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
import shlex
from typing import Any, Iterable, Sequence

from aura_emergent_capability_auditor import (
    AUDIT_ROUTE,
    audit_emergent_capabilities,
)
from aura_repo_localizer import EXCLUDE_DIRS
from aura_topological_context_anchor import (
    PATCH_AUTHORITY_POLICY,
    CodeTopoAnchor,
    CodeTopoEdge,
    CodeTopoNode,
)


EMERGENT_POTENTIAL_VERSION = "AURA_EMERGENT_POTENTIAL_REPL_V1"
READ_ONLY_CONSTRAINTS = (
    "NO_PATCHES",
    "NO_CODE_WRITES",
    "NO_UNIFIED_DIFF",
    "NO_AUTOWIRING",
    "REPORT_ONLY",
)
STATUS_READY_TO_DOCUMENT = "READY_TO_DOCUMENT"
STATUS_READY_TO_TEST = "READY_TO_TEST"
STATUS_FUTURE_PATCHABLE = "FUTURE_PATCHABLE"
STATUS_NEEDS_GROUNDING = "NEEDS_GROUNDING"
STATUS_TOO_RISKY = "TOO_RISKY"
STATUS_DREAM_ONLY = "DREAM_ONLY"
VALID_STATUSES = {
    STATUS_READY_TO_DOCUMENT,
    STATUS_READY_TO_TEST,
    STATUS_FUTURE_PATCHABLE,
    STATUS_NEEDS_GROUNDING,
    STATUS_TOO_RISKY,
    STATUS_DREAM_ONLY,
}

COMMAND_ALIASES = {"emerge", "emergent", "future", "potential"}
PATCH_TERMS = {
    "add",
    "build",
    "change",
    "code",
    "create",
    "edit",
    "fix",
    "implement",
    "patch",
    "stage",
    "update",
    "wire",
    "write",
}
READ_ONLY_QUERY_TERMS = {
    "audit",
    "broad",
    "combine",
    "discover",
    "emergent",
    "find",
    "future",
    "overview",
    "potential",
    "properties",
    "report",
    "show",
    "unwired",
}
EMERGENT_PHRASES = (
    "find emergent",
    "emergent properties",
    "future potential",
    "future potentials",
    "unwired connections",
    "what abilities appear if",
    "combine new function with",
    "broad overview",
)

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "research_manifest": ("research_manifest", "research manifest", "implementation_lesson", "future_ingest"),
    "empirical_lab": ("empirical_software_lab", "empirical lab", "candidate_tree", "define_empirical", "ucb"),
    "coding_arena": ("coding_arena", "arena", "topology selection", "micro_arena", "canvas"),
    "capsule_compiler": ("capsule", "actcapsule", "action_capsule", "compile", "builder_context"),
    "model_router": ("model_router", "router", "route_model", "provider", "token cost"),
    "test_runner": ("pytest", "test_", "verification", "verifier", "quality_gate"),
    "topology": ("topology", "codemap", "codetopo", "source_span", "source_hash"),
    "localizer": ("localizer", "localize", "fallback_candidate", "fault localization"),
    "memory": ("memory", "ledger", "jsonl", "sqlite", "trace"),
    "external_api": ("requests", "httpx", "openai", "anthropic", "subprocess", "urlopen"),
    "hotswap": ("hotswap", "hot_swap", "rollback", "live_transaction"),
}

COMPLEMENTARY_ROLE_RULES: tuple[tuple[str, str, str, str], ...] = (
    (
        "research_manifest",
        "empirical_lab",
        "Research Manifest -> Empirical Software Lab",
        "research acceptance tests can become scorable empirical task scorecards",
    ),
    (
        "coding_arena",
        "capsule_compiler",
        "Coding Arena -> Capsule Compiler",
        "selected topology facts can become deterministic worker action capsules",
    ),
    (
        "topology",
        "capsule_compiler",
        "Topology Anchor -> Capsule Compiler",
        "exact source spans can constrain future capsule generation",
    ),
    (
        "localizer",
        "model_router",
        "Repo Localizer -> Model Router",
        "localized evidence can avoid broad prompt routing and premium-model overuse",
    ),
    (
        "research_manifest",
        "test_runner",
        "Research Manifest -> Test Runner",
        "acceptance tests can become deterministic local verifier tasks",
    ),
    (
        "coding_arena",
        "model_router",
        "Coding Arena -> Model Router",
        "operator-selected topology can inform local route scorecards",
    ),
    (
        "memory",
        "model_router",
        "Memory Ledger -> Model Router",
        "stored traces can shrink repeated model-routing context",
    ),
    (
        "external_api",
        "test_runner",
        "External API Surface -> Test Runner",
        "external side effects can be audited by deterministic no-network tests",
    ),
    (
        "hotswap",
        "test_runner",
        "Hot-Swap Capsule -> Test Runner",
        "deployment gates can be held behind verifier evidence",
    ),
)


@dataclass
class AbilityAtom:
    ability_id: str
    file: str
    symbol: str
    kind: str
    known_inputs: list[str] = field(default_factory=list)
    known_outputs: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FuturePotentialQuery:
    new_function_description: str = ""
    combine_with: list[str] = field(default_factory=list)
    focus: str = ""
    constraints: list[str] = field(default_factory=lambda: list(READ_ONLY_CONSTRAINTS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmergentConnection:
    connection_id: str
    source: dict[str, str]
    target: dict[str, str]
    missing_wire: str
    emergent_ability: str
    evidence: list[dict[str, Any]]
    confidence: float
    implementation_feasibility: float
    verifier_readiness: float
    token_reduction_potential: float
    safety_risk: str
    cost_risk: str
    status: str
    required_tests: list[str] = field(default_factory=list)
    future_patch_capsule_hint: dict[str, Any] | None = None
    emergence_score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmergentPotentialReport:
    version: str
    route: str
    constraints: list[str]
    summary: dict[str, Any]
    abilities: list[AbilityAtom]
    connections: list[EmergentConnection]
    future_query: FuturePotentialQuery | None = None
    evidence_sources: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    safe_to_patch: bool = False
    verified_clusters: list[dict[str, Any]] = field(default_factory=list)
    raw_candidate_count: int = 0
    suppressed_duplicate_count: int = 0
    rejected_candidate_count: int = 0
    jspace_summary: dict[str, Any] = field(default_factory=dict)
    st3gg_egress: dict[str, Any] = field(default_factory=dict)
    trace_atom_ids: list[str] = field(default_factory=list)
    verifier_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "route": self.route,
            "constraints": self.constraints,
            "summary": self.summary,
            "abilities": [ability.to_dict() for ability in self.abilities],
            "connections": [connection.to_dict() for connection in self.connections],
            "future_query": self.future_query.to_dict() if self.future_query else None,
            "evidence_sources": self.evidence_sources,
            "warnings": self.warnings,
            "safe_to_patch": self.safe_to_patch,
            "verified_clusters": self.verified_clusters,
            "raw_candidate_count": self.raw_candidate_count,
            "suppressed_duplicate_count": self.suppressed_duplicate_count,
            "rejected_candidate_count": self.rejected_candidate_count,
            "jspace_summary": self.jspace_summary,
            "st3gg_egress": self.st3gg_egress,
            "trace_atom_ids": self.trace_atom_ids,
            "verifier_summary": self.verifier_summary,
        }


@dataclass
class EmergentCommandOptions:
    top: int = 12
    as_json: bool = False
    focus: str = ""
    patchable_only: bool = False
    new_function_description: str = ""
    combine_with: list[str] = field(default_factory=list)


def parse_emerge_command(command: str | Sequence[str]) -> EmergentCommandOptions:
    """Parse `emerge`/`future` command flags without executing side effects."""
    if isinstance(command, str):
        tokens = shlex.split(command)
    else:
        tokens = list(command)
    if tokens:
        head = tokens[0].lstrip("!").lower()
        if head in COMMAND_ALIASES:
            tokens = tokens[1:]

    options = EmergentCommandOptions()
    loose_focus: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--json":
            options.as_json = True
            index += 1
        elif token == "--patchable-only":
            options.patchable_only = True
            index += 1
        elif token == "--top":
            if index + 1 >= len(tokens):
                raise ValueError("--top requires a positive integer")
            options.top = max(1, min(100, int(tokens[index + 1])))
            index += 2
        elif token == "--focus":
            value, index = _read_flag_value(tokens, index + 1)
            options.focus = value
        elif token == "--new":
            value, index = _read_flag_value(tokens, index + 1)
            options.new_function_description = value
        elif token == "--with":
            value, index = _read_flag_value(tokens, index + 1)
            options.combine_with = [part.strip() for part in value.split(",") if part.strip()]
        elif token.startswith("--"):
            raise ValueError(f"Unknown emerge option: {token}")
        else:
            loose_focus.append(token)
            index += 1
    if loose_focus and not options.focus:
        options.focus = " ".join(loose_focus)
    return options


def audit_emergent_potential(
    repo_root_or_anchor: str | Path | CodeTopoAnchor,
    *,
    top: int = 12,
    focus: str = "",
    patchable_only: bool = False,
    new_function_description: str = "",
    combine_with: Sequence[str] = (),
) -> EmergentPotentialReport:
    """Build a read-only emergent-potential report from local topology evidence."""
    anchor, root = _coerce_anchor(repo_root_or_anchor)
    atoms = _atoms_from_anchor(anchor)
    focus_text = str(focus or "")
    future_query = None
    if new_function_description or combine_with or focus_text:
        future_query = FuturePotentialQuery(
            new_function_description=str(new_function_description or ""),
            combine_with=list(combine_with or ()),
            focus=focus_text,
        )

    warnings = list(anchor.warnings)
    evidence_sources = _evidence_sources(root) if root else []
    connections: list[EmergentConnection] = []
    if new_function_description:
        connections.extend(
            _project_new_function_connections(
                atoms,
                description=new_function_description,
                combine_with=combine_with,
                focus=focus_text,
                limit=top,
            )
        )
    else:
        connections = _discover_connections(anchor, atoms, focus=focus_text, limit=max(top * 20, 100))
    connections = _dedupe_connections(connections)
    if patchable_only:
        connections = [item for item in connections if item.status == STATUS_FUTURE_PATCHABLE]
    connections = sorted(
        connections,
        key=lambda item: (-item.emergence_score, item.status, item.connection_id),
    )[: max(1, top)]

    status_counts = {status: 0 for status in sorted(VALID_STATUSES)}
    for connection in connections:
        status_counts[connection.status] = status_counts.get(connection.status, 0) + 1
    summary = {
        "total_abilities_scanned": len(atoms),
        "candidate_unwired_connections": len(connections),
        "future_patchable": status_counts.get(STATUS_FUTURE_PATCHABLE, 0),
        "needs_grounding": status_counts.get(STATUS_NEEDS_GROUNDING, 0),
        "too_risky": status_counts.get(STATUS_TOO_RISKY, 0),
        "status_counts": status_counts,
        "read_only": True,
        "patch_authority": PATCH_AUTHORITY_POLICY,
        "scoring_formula": (
            "usefulness + topology_affinity + implementation_feasibility + "
            "verifier_readiness + token_reduction_potential - safety_risk - "
            "cost_overhead - missing_evidence_penalty"
        ),
    }

    # Run the verifier pipeline
    from aura_emergent_result_verifier import (
        verify_emergent_connections,
        EmergentVerificationConfig,
    )
    trace_root = None
    if root:
        trace_root = str(root / "Aura_Memory")
    cfg = EmergentVerificationConfig(
        max_clusters=top,
        trace_memory_root=trace_root,
    )
    verified = verify_emergent_connections(connections, focus=focus_text, config=cfg)
    verified_clusters_list = [c.to_dict() for c in verified.clusters]

    return EmergentPotentialReport(
        version=EMERGENT_POTENTIAL_VERSION,
        route=AUDIT_ROUTE,
        constraints=list(READ_ONLY_CONSTRAINTS),
        summary=summary,
        abilities=atoms[: max(1, min(len(atoms), top * 3))],
        connections=connections,
        future_query=future_query,
        evidence_sources=evidence_sources,
        warnings=warnings,
        safe_to_patch=False,
        verified_clusters=verified_clusters_list,
        raw_candidate_count=verified.raw_count,
        suppressed_duplicate_count=verified.suppressed_duplicate_count,
        rejected_candidate_count=verified.rejected_count,
        jspace_summary=verified.jspace_summary,
        st3gg_egress=verified.st3gg_egress,
        trace_atom_ids=verified.trace_atom_ids,
        verifier_summary=verified.verifier_summary,
    )


def render_emergent_potential_report(report: EmergentPotentialReport | dict[str, Any]) -> str:
    """Render the default human-readable Markdown report."""
    payload = report.to_dict() if isinstance(report, EmergentPotentialReport) else dict(report)
    if payload.get("verified_clusters") or payload.get("clusters"):
        from aura_emergent_result_verifier import render_verified_emergent_report
        return render_verified_emergent_report(payload)
    summary = dict(payload.get("summary", {}) or {})
    connections = list(payload.get("connections", []) or [])
    lines = [
        "# Emergent Properties and Future Potential",
        "",
        "## Summary",
        f"- Total abilities scanned: {summary.get('total_abilities_scanned', 0)}",
        f"- Candidate unwired connections: {summary.get('candidate_unwired_connections', 0)}",
        f"- Future-patchable: {summary.get('future_patchable', 0)}",
        f"- Needs grounding: {summary.get('needs_grounding', 0)}",
        f"- Too risky: {summary.get('too_risky', 0)}",
        f"- Constraints: {', '.join(str(item) for item in payload.get('constraints', READ_ONLY_CONSTRAINTS))}",
        "",
        "## Top Candidates",
    ]
    if not connections:
        lines.append("")
        lines.append("No grounded candidates matched the current filters.")
    for index, connection in enumerate(connections, start=1):
        source = connection.get("source", {}) if isinstance(connection, dict) else {}
        target = connection.get("target", {}) if isinstance(connection, dict) else {}
        evidence = list(connection.get("evidence", []) or []) if isinstance(connection, dict) else []
        required_tests = list(connection.get("required_tests", []) or []) if isinstance(connection, dict) else []
        lines.extend(
            [
                "",
                f"### {index}. {connection.get('emergent_ability', 'Emergent candidate')}",
                f"- Existing pieces: {source.get('file', '')}:{source.get('symbol', '')} -> {target.get('file', '')}:{target.get('symbol', '')}",
                f"- Missing wire: {connection.get('missing_wire', '')}",
                f"- Evidence: {_render_evidence(evidence)}",
                f"- Required tests: {', '.join(required_tests) if required_tests else 'Add deterministic local integration test before wiring.'}",
                f"- Risk: safety={connection.get('safety_risk', 'low')}, cost={connection.get('cost_risk', 'low')}",
                f"- Status: {connection.get('status', STATUS_NEEDS_GROUNDING)}",
                f"- Score: {connection.get('emergence_score', 0.0)}",
            ]
        )
    lines.extend(
        [
            "",
            "## Safety",
            "- This audit is report-only. It does not write files, stage patches, call external APIs, or create patch capsules.",
            "- Connections without exact local evidence are marked NEEDS_GROUNDING.",
        ]
    )
    return "\n".join(lines)


def handle_emergent_potential_command(
    command: str | Sequence[str],
    repo_root: str | Path | CodeTopoAnchor | None = None,
) -> str:
    """REPL-safe command handler. Returns a report string and performs no writes."""
    options = parse_emerge_command(command)
    target = repo_root if repo_root is not None else Path.cwd()
    report = audit_emergent_potential(
        target,
        top=options.top,
        focus=options.focus,
        patchable_only=options.patchable_only,
        new_function_description=options.new_function_description,
        combine_with=options.combine_with,
    )
    if options.as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)
    return render_emergent_potential_report(report)


def query_emergent_potential_packet(intent: str, repo_root: str | Path) -> dict[str, Any]:
    """Coding Arena/Architect-safe packet for broad emergent-potential intents."""
    options = EmergentCommandOptions(focus=str(intent or ""))
    report = audit_emergent_potential(
        repo_root,
        top=12,
        focus=options.focus,
    )
    return {
        "version": EMERGENT_POTENTIAL_VERSION,
        "route": AUDIT_ROUTE,
        "grounding_ok": True,
        "safe_to_patch": False,
        "target_file": None,
        "target_symbol": None,
        "report": report.to_dict(),
        "rendered": render_emergent_potential_report(report),
        "route_reasons": ["read_only_emergent_potential_audit", PATCH_AUTHORITY_POLICY],
        "route_diagnostics": {
            "route": AUDIT_ROUTE,
            "reasons": ["read_only_emergent_potential_audit"],
            "patch_authority": PATCH_AUTHORITY_POLICY,
            "safe_to_patch": False,
            "vsa_patch_authority": False,
            "constraints": list(READ_ONLY_CONSTRAINTS),
        },
        "safety_policy": PATCH_AUTHORITY_POLICY,
        "vsa_patch_authority": False,
    }


def is_emergent_potential_intent(intent: str) -> bool:
    """Return True for broad future-potential requests that should not enter patch mode."""
    lowered = str(intent or "").strip().lower()
    if not lowered:
        return False
    tokens = set(_tokens(lowered))
    first = lowered.split(maxsplit=1)[0].lstrip("!")
    if first in COMMAND_ALIASES:
        return True
    if tokens & PATCH_TERMS and not {"what", "if", "potential", "emergent", "unwired"} <= tokens:
        return False
    if any(phrase in lowered for phrase in EMERGENT_PHRASES):
        return True
    audit_terms = {"abilities", "capabilities", "capability", "emergent", "potential", "properties", "unwired"}
    query_terms = {"audit", "combine", "discover", "find", "overview", "report", "show", "what"}
    if "future" in tokens and not tokens & {"potential", "abilities", "capabilities", "capability", "properties", "unwired"}:
        return False
    return bool(tokens & query_terms) and bool(tokens & audit_terms)


def build_demo_fixture_anchor() -> CodeTopoAnchor:
    """Return the deterministic fake topology required by the REPL audit tests."""
    files = {
        "aura_research_manifest.py": "\n".join(
            [
                "def load_research_manifest():",
                "    return {'acceptance_test': 'empirical lab scorecard'}",
            ]
        ),
        "aura_empirical_software_lab.py": "\n".join(
            [
                "def score_empirical_task():",
                "    return 'empirical candidate_tree scorecard metric'",
            ]
        ),
        "aura_coding_arena_3d.py": "\n".join(
            [
                "def select_coding_arena_node():",
                "    return {'topology': 'coding_arena selection'}",
            ]
        ),
        "aura_capsule_compiler.py": "\n".join(
            [
                "def compile_action_capsule():",
                "    return 'act capsule builder_context compiler'",
            ]
        ),
        "aura_model_router_scorecard.py": "\n".join(
            [
                "def route_model_scorecard():",
                "    return 'model_router provider token cost route scorecard'",
            ]
        ),
        "test_runner.py": "\n".join(
            [
                "def run_pytest_verifier():",
                "    return 'pytest verification quality_gate test_runner'",
            ]
        ),
        "test_empirical_lab.py": "\n".join(
            [
                "from aura_empirical_software_lab import score_empirical_task",
                "",
                "def test_score_empirical_task():",
                "    assert score_empirical_task()",
            ]
        ),
        "test_coding_arena.py": "\n".join(
            [
                "from aura_coding_arena_3d import select_coding_arena_node",
                "",
                "def test_select_coding_arena_node():",
                "    assert select_coding_arena_node()",
            ]
        ),
    }
    return CodeTopoAnchor.build_from_files(files)


def build_connection_for_atoms(
    source: AbilityAtom,
    target: AbilityAtom,
    *,
    missing_wire: str = "candidate_bridge_missing",
    emergent_ability: str = "Candidate emergent ability",
    role_pair: tuple[str, str] = ("general", "general"),
    confidence: float = 0.5,
) -> EmergentConnection:
    """Public test/helper constructor that applies the same transparent scoring."""
    return _make_connection(
        source,
        target,
        missing_wire=missing_wire,
        emergent_ability=emergent_ability,
        rule_roles=role_pair,
        confidence=confidence,
    )


def _read_flag_value(tokens: Sequence[str], index: int) -> tuple[str, int]:
    if index >= len(tokens):
        raise ValueError("Flag requires a value")
    values: list[str] = []
    while index < len(tokens) and not str(tokens[index]).startswith("--"):
        values.append(str(tokens[index]))
        index += 1
    if not values:
        raise ValueError("Flag requires a value")
    return " ".join(values).strip(), index


def _coerce_anchor(repo_root_or_anchor: str | Path | CodeTopoAnchor) -> tuple[CodeTopoAnchor, Path | None]:
    if isinstance(repo_root_or_anchor, CodeTopoAnchor):
        return repo_root_or_anchor, None
    root = Path(repo_root_or_anchor).resolve()
    return CodeTopoAnchor.build_from_files(_repo_python_sources(root)), root


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


def _atoms_from_anchor(anchor: CodeTopoAnchor) -> list[AbilityAtom]:
    atoms: list[AbilityAtom] = []
    tests_by_file = _tests_by_file(anchor)
    for node in sorted(anchor.nodes.values(), key=lambda item: (item.file_path, item.start_line, item.symbol)):
        if node.kind == "module":
            continue
        roles = _classify_ability_roles(node, anchor)
        if not roles:
            continue
        atoms.append(_atom_from_node(anchor, node, roles, tests=tests_by_file.get(node.file_path, [])))
    return atoms


def _atom_from_node(
    anchor: CodeTopoAnchor,
    node: CodeTopoNode,
    roles: Sequence[str],
    *,
    tests: Sequence[str] = (),
) -> AbilityAtom:
    incoming = [edge for edge in anchor.incoming.get(node.node_id, []) if edge.src_id in anchor.nodes]
    outgoing = [edge for edge in anchor.outgoing.get(node.node_id, []) if edge.dst_id in anchor.nodes]
    evidence = [
        {
            "file": node.file_path,
            "symbol": node.symbol,
            "kind": node.kind,
            "source_span": [node.start_line, node.end_line],
            "source_hash": node.source_hash,
            "file_source_hash": anchor.file_hashes.get(node.file_path, ""),
            "roles": list(roles),
        }
    ]
    return AbilityAtom(
        ability_id=node.node_id,
        file=node.file_path,
        symbol=node.symbol,
        kind=_ability_kind(node),
        known_inputs=_known_inputs(node),
        known_outputs=_known_outputs(node, roles),
        dependencies=_unique([*node.imports, *node.calls]),
        callers=_unique(anchor.nodes[edge.src_id].symbol for edge in incoming),
        callees=_unique(anchor.nodes[edge.dst_id].symbol for edge in outgoing),
        tests=list(tests),
        evidence=evidence,
    )


def _tests_by_file(anchor: CodeTopoAnchor) -> dict[str, list[str]]:
    nodes_by_file: dict[str, list[str]] = {}
    for node in anchor.nodes.values():
        nodes_by_file.setdefault(node.file_path, []).append(node.node_id)
    output: dict[str, list[str]] = {}
    for file_path, node_ids in nodes_by_file.items():
        try:
            output[file_path] = anchor._tests_for_nodes(node_ids)  # noqa: SLF001 - no public file-level test accessor.
        except Exception:
            output[file_path] = []
    return output


def _classify_ability_roles(node: CodeTopoNode, anchor: CodeTopoAnchor) -> list[str]:
    symbol_lower = node.symbol.lower()
    if "fixture" in symbol_lower or symbol_lower.startswith("test_"):
        return []
    text = " ".join(
        [
            node.file_path,
            node.symbol,
            node.kind,
            " ".join(node.imports),
            " ".join(node.calls),
            _source_excerpt(anchor, node, max_lines=12),
        ]
    ).replace("-", "_").lower()
    roles = [
        role
        for role, keywords in ROLE_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    return roles


def _discover_connections(
    anchor: CodeTopoAnchor,
    atoms: Sequence[AbilityAtom],
    *,
    focus: str = "",
    limit: int,
) -> list[EmergentConnection]:
    direct_pairs = {
        frozenset((edge.src_id, edge.dst_id))
        for edge in anchor.edges
        if edge.src_id in anchor.nodes and edge.dst_id in anchor.nodes
    }
    groups: dict[str, list[AbilityAtom]] = {}
    for atom in atoms:
        for role in _roles_for_atom(atom):
            groups.setdefault(role, []).append(atom)

    connections: list[EmergentConnection] = []
    seen_pairs: set[frozenset[str]] = set()
    per_rule_limit = max(8, limit // max(1, len(COMPLEMENTARY_ROLE_RULES)))
    for left_role, right_role, ability, missing_wire in COMPLEMENTARY_ROLE_RULES:
        left_items = _rank_role_atoms(groups.get(left_role, []), left_role)[:80]
        right_items = _rank_role_atoms(groups.get(right_role, []), right_role)[:80]
        rule_count = 0
        for left in left_items:
            for right in right_items:
                if rule_count >= per_rule_limit:
                    break
                if left.ability_id == right.ability_id:
                    continue
                pair = frozenset((left.ability_id, right.ability_id))
                if pair in seen_pairs or pair in direct_pairs:
                    continue
                if focus and not _matches_focus([left, right], focus):
                    continue
                seen_pairs.add(pair)
                confidence = _confidence_for_atoms(left, right, focus=focus)
                connections.append(
                    _make_connection(
                        left,
                        right,
                        missing_wire=missing_wire,
                        emergent_ability=ability,
                        rule_roles=(left_role, right_role),
                        confidence=confidence,
                    )
                )
                rule_count += 1
            if rule_count >= per_rule_limit:
                break
    return connections


def _rank_role_atoms(atoms: Sequence[AbilityAtom], role: str) -> list[AbilityAtom]:
    return sorted(atoms, key=lambda atom: (-_atom_role_priority(atom, role), atom.file, atom.symbol))


def _atom_role_priority(atom: AbilityAtom, role: str) -> float:
    text = " ".join([atom.file, atom.symbol, " ".join(atom.dependencies), " ".join(_roles_for_atom(atom))]).lower()
    score = 0.0
    if role in _roles_for_atom(atom):
        score += 1.0
    role_terms = [part for part in role.split("_") if part]
    score += 0.2 * sum(1 for term in role_terms if term in atom.symbol.lower())
    score += 0.1 * sum(1 for term in role_terms if term in atom.file.lower())
    if atom.symbol.lower() in {"to_dict", "from_dict", "__init__", "main"}:
        score -= 0.7
    if atom.symbol.startswith("_"):
        score -= 0.35
    if "fixture" in text or "demo" in atom.symbol.lower():
        score -= 1.0
    if atom.tests:
        score += 0.15
    return score


def _connections_from_legacy_audit(
    anchor: CodeTopoAnchor,
    *,
    focus: str,
    limit: int,
) -> list[EmergentConnection]:
    try:
        report = audit_emergent_capabilities(anchor, query=focus, limit=limit, include_future=False)
    except Exception:
        return []
    connections: list[EmergentConnection] = []
    for finding in report.findings[:limit]:
        if len(finding.symbols) < 2:
            continue
        left = _atom_from_capability_symbol(finding.symbols[0])
        right = _atom_from_capability_symbol(finding.symbols[1])
        if focus and not _matches_focus([left, right], focus):
            continue
        connections.append(
            _make_connection(
                left,
                right,
                missing_wire="legacy_capability_pair_without_direct_edge",
                emergent_ability=finding.title,
                rule_roles=(finding.symbols[0].role, finding.symbols[1].role),
                confidence=finding.confidence,
            )
        )
    return connections


def _project_new_function_connections(
    atoms: Sequence[AbilityAtom],
    *,
    description: str,
    combine_with: Sequence[str],
    focus: str,
    limit: int,
) -> list[EmergentConnection]:
    target_atoms = list(atoms)
    if combine_with:
        target_atoms = [atom for atom in target_atoms if _atom_matches_any_file(atom, combine_with)]
    elif focus:
        target_atoms = [atom for atom in target_atoms if _matches_focus([atom], focus)]
    target_atoms = sorted(target_atoms, key=lambda atom: (_new_function_affinity(atom, description), atom.file, atom.symbol), reverse=True)
    if not target_atoms:
        missing_target = AbilityAtom(
            ability_id=_stable_id("missing_target", description, ",".join(combine_with)),
            file="",
            symbol="",
            kind="module",
            evidence=[],
        )
        proposed = _proposed_atom(description)
        return [
            _make_connection(
                proposed,
                missing_target,
                missing_wire="new_function_has_no_grounded_existing_target",
                emergent_ability=f"New function potential: {description}",
                rule_roles=("proposed", "missing"),
                confidence=0.18,
            )
        ]

    proposed = _proposed_atom(description)
    connections: list[EmergentConnection] = []
    for target in target_atoms[:limit]:
        connections.append(
            _make_connection(
                proposed,
                target,
                missing_wire="proposed_function_requires_design_and_source_span_before_wiring",
                emergent_ability=f"{description} + {target.symbol}",
                rule_roles=("proposed", *_roles_for_atom(target)[:1]),
                confidence=min(0.68, 0.32 + _new_function_affinity(target, description)),
            )
        )
    return connections


def _make_connection(
    source: AbilityAtom,
    target: AbilityAtom,
    *,
    missing_wire: str,
    emergent_ability: str,
    rule_roles: Sequence[str],
    confidence: float,
) -> EmergentConnection:
    source_roles = _roles_for_atom(source)
    target_roles = _roles_for_atom(target)
    all_roles = set(source_roles + target_roles + list(rule_roles))
    implementation_feasibility = _implementation_feasibility(source, target)
    verifier_readiness = _verifier_readiness(source, target)
    token_reduction_potential = _token_reduction_potential(all_roles)
    safety_risk = _safety_risk(all_roles)
    cost_risk = _cost_risk(all_roles)
    usefulness = _usefulness(all_roles)
    topology_affinity = round(max(0.0, min(1.0, confidence)), 4)
    missing_evidence_penalty = 0.5 if not _has_exact_evidence(source) or not _has_exact_evidence(target) else 0.0
    safety_penalty = {"low": 0.05, "medium": 0.35, "high": 0.85}[safety_risk]
    cost_penalty = {"low": 0.02, "medium": 0.18, "high": 0.4}[cost_risk]
    breakdown = {
        "usefulness": usefulness,
        "topology_affinity": topology_affinity,
        "implementation_feasibility": implementation_feasibility,
        "verifier_readiness": verifier_readiness,
        "token_reduction_potential": token_reduction_potential,
        "safety_risk": safety_penalty,
        "cost_overhead": cost_penalty,
        "missing_evidence_penalty": missing_evidence_penalty,
    }
    score = round(
        usefulness
        + topology_affinity
        + implementation_feasibility
        + verifier_readiness
        + token_reduction_potential
        - safety_penalty
        - cost_penalty
        - missing_evidence_penalty,
        4,
    )
    status = _connection_status(
        source,
        target,
        safety_risk=safety_risk,
        implementation_feasibility=implementation_feasibility,
        verifier_readiness=verifier_readiness,
        confidence=confidence,
    )
    required_tests = _required_tests(source, target, status=status)
    hint = None
    if status == STATUS_FUTURE_PATCHABLE:
        hint = {
            "allowed_only_after_human_request": True,
            "suggested_first_step": "write a failing integration test for this candidate before wiring",
            "constraints": list(READ_ONLY_CONSTRAINTS),
        }
    return EmergentConnection(
        connection_id=_stable_id("connection", source.ability_id, target.ability_id, missing_wire),
        source={"file": source.file, "symbol": source.symbol},
        target={"file": target.file, "symbol": target.symbol},
        missing_wire=missing_wire,
        emergent_ability=emergent_ability,
        evidence=[*source.evidence, *target.evidence],
        confidence=round(confidence, 4),
        implementation_feasibility=implementation_feasibility,
        verifier_readiness=verifier_readiness,
        token_reduction_potential=token_reduction_potential,
        safety_risk=safety_risk,
        cost_risk=cost_risk,
        status=status,
        required_tests=required_tests,
        future_patch_capsule_hint=hint,
        emergence_score=score,
        score_breakdown=breakdown,
    )


def _connection_status(
    source: AbilityAtom,
    target: AbilityAtom,
    *,
    safety_risk: str,
    implementation_feasibility: float,
    verifier_readiness: float,
    confidence: float,
) -> str:
    if safety_risk == "high":
        return STATUS_TOO_RISKY
    if not _has_exact_evidence(source) or not _has_exact_evidence(target):
        return STATUS_NEEDS_GROUNDING
    if implementation_feasibility >= 0.75 and verifier_readiness >= 0.35:
        return STATUS_FUTURE_PATCHABLE
    if verifier_readiness > 0:
        return STATUS_READY_TO_TEST
    if confidence >= 0.5:
        return STATUS_READY_TO_DOCUMENT
    return STATUS_DREAM_ONLY


def _implementation_feasibility(source: AbilityAtom, target: AbilityAtom) -> float:
    score = 0.2
    if _has_exact_evidence(source):
        score += 0.25
    if _has_exact_evidence(target):
        score += 0.25
    if source.file and target.file and source.file != target.file:
        score += 0.1
    if source.dependencies or target.dependencies:
        score += 0.08
    if source.tests or target.tests:
        score += 0.12
    return round(min(score, 1.0), 4)


def _verifier_readiness(source: AbilityAtom, target: AbilityAtom) -> float:
    tests = _unique([*source.tests, *target.tests])
    if tests:
        return min(1.0, round(0.35 + 0.15 * min(len(tests), 4), 4))
    if source.kind == "test" or target.kind == "test":
        return 0.4
    return 0.0


def _token_reduction_potential(roles: set[str]) -> float:
    score = 0.0
    if roles & {"topology", "localizer", "coding_arena"}:
        score += 0.25
    if roles & {"capsule_compiler", "model_router", "memory"}:
        score += 0.25
    if roles & {"research_manifest", "empirical_lab"}:
        score += 0.1
    return round(min(score, 0.75), 4)


def _usefulness(roles: set[str]) -> float:
    if {"research_manifest", "empirical_lab"} <= roles:
        return 0.82
    if {"coding_arena", "capsule_compiler"} <= roles:
        return 0.86
    if "external_api" in roles:
        return 0.5
    return 0.62


def _safety_risk(roles: set[str]) -> str:
    if roles & {"external_api", "hotswap"}:
        return "high"
    if roles & {"model_router", "capsule_compiler"}:
        return "medium"
    return "low"


def _cost_risk(roles: set[str]) -> str:
    if "external_api" in roles:
        return "high"
    if "model_router" in roles:
        return "medium"
    return "low"


def _required_tests(source: AbilityAtom, target: AbilityAtom, *, status: str) -> list[str]:
    existing = _unique([*source.tests, *target.tests])
    if status == STATUS_NEEDS_GROUNDING:
        return ["ground exact source spans before test design"]
    if status == STATUS_TOO_RISKY:
        return ["no-network safety test", "explicit human approval gate"]
    if existing:
        return existing[:5]
    return [f"test_{_slug(source.symbol)}_to_{_slug(target.symbol)}_emergence"]


def _atom_from_capability_symbol(symbol: Any) -> AbilityAtom:
    evidence = dict(getattr(symbol, "evidence", {}) or {})
    roles = list(getattr(symbol, "role_tags", []) or [getattr(symbol, "role", "capability")])
    if roles:
        evidence.setdefault("roles", roles)
    evidence.setdefault("source_span", [getattr(symbol, "start_line", 0), getattr(symbol, "end_line", 0)])
    evidence.setdefault("source_hash", getattr(symbol, "source_hash", ""))
    return AbilityAtom(
        ability_id=str(getattr(symbol, "symbol_id", _stable_id("capability", getattr(symbol, "file_path", ""), getattr(symbol, "symbol", "")))),
        file=str(getattr(symbol, "file_path", "")),
        symbol=str(getattr(symbol, "symbol", "")),
        kind=_normalize_kind(str(getattr(symbol, "kind", "function"))),
        dependencies=list(getattr(symbol, "calls", []) or []),
        tests=list(getattr(symbol, "tests", []) or []),
        evidence=[evidence],
    )


def _proposed_atom(description: str) -> AbilityAtom:
    return AbilityAtom(
        ability_id=_stable_id("proposed", description),
        file="",
        symbol=str(description or "proposed function"),
        kind="function",
        known_inputs=["operator proposal"],
        known_outputs=["future potential only"],
        evidence=[
            {
                "proposal": str(description or ""),
                "source_span": [],
                "source_hash": "",
                "status": STATUS_NEEDS_GROUNDING,
                "roles": ["proposed"],
            }
        ],
    )


def _ability_kind(node: CodeTopoNode) -> str:
    if node.file_path.startswith("test_") or "/test_" in node.file_path or node.symbol.startswith("test_"):
        return "test"
    if "ledger" in node.file_path.lower():
        return "ledger"
    if "manifest" in node.file_path.lower():
        return "manifest"
    if "router" in node.file_path.lower() or "route" in node.symbol.lower():
        return "router"
    if "memory" in node.file_path.lower():
        return "memory"
    if node.file_path.endswith((".html", ".css", ".js")):
        return "ui"
    return _normalize_kind(node.kind)


def _normalize_kind(kind: str) -> str:
    lowered = str(kind or "").lower()
    if "class" in lowered:
        return "class"
    if "module" in lowered:
        return "module"
    if "test" in lowered:
        return "test"
    return "function"


def _known_inputs(node: CodeTopoNode) -> list[str]:
    assignments = list(node.metadata.get("assignments", []) or [])
    imports = [item for item in node.imports[:4]]
    return _unique([*imports, *assignments[:4]])


def _known_outputs(node: CodeTopoNode, roles: Sequence[str]) -> list[str]:
    outputs = list(roles)
    if node.symbol.startswith(("render", "build", "compile", "score", "route", "load")):
        outputs.append(node.symbol)
    return _unique(outputs)


def _roles_for_atom(atom: AbilityAtom) -> list[str]:
    roles: list[str] = []
    for item in atom.evidence:
        roles.extend(str(role) for role in item.get("roles", []) or [])
    if not roles:
        roles = _roles_from_text(" ".join([atom.file, atom.symbol, atom.kind, *atom.dependencies]))
    return _unique(roles)


def _roles_from_text(text: str) -> list[str]:
    lowered = str(text or "").replace("-", "_").lower()
    return [
        role
        for role, keywords in ROLE_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]


def _has_exact_evidence(atom: AbilityAtom) -> bool:
    if not atom.file or not atom.symbol:
        return False
    for item in atom.evidence:
        span = item.get("source_span")
        source_hash = str(item.get("source_hash") or "")
        if isinstance(span, list) and len(span) == 2 and all(int(value or 0) > 0 for value in span) and source_hash:
            return True
    return False


def _matches_focus(atoms: Sequence[AbilityAtom], focus: str) -> bool:
    focus_tokens = set(_tokens(focus))
    if not focus_tokens:
        return True
    text_tokens = set()
    for atom in atoms:
        text_tokens.update(_tokens(" ".join([atom.file, atom.symbol, atom.kind, " ".join(atom.dependencies), " ".join(_roles_for_atom(atom))])))
    return bool(focus_tokens & text_tokens)


def _confidence_for_atoms(source: AbilityAtom, target: AbilityAtom, *, focus: str) -> float:
    score = 0.46
    if set(_roles_for_atom(source)) & set(_roles_for_atom(target)):
        score += 0.08
    if Path(source.file).stem.split("_")[0:1] == Path(target.file).stem.split("_")[0:1]:
        score += 0.06
    if source.tests or target.tests:
        score += 0.12
    if set(source.dependencies) & set(target.dependencies):
        score += 0.08
    if focus and _matches_focus([source, target], focus):
        score += 0.08
    return round(min(score, 0.92), 4)


def _new_function_affinity(atom: AbilityAtom, description: str) -> float:
    query = set(_tokens(description))
    if not query:
        return 0.0
    target = set(_tokens(" ".join([atom.file, atom.symbol, " ".join(atom.dependencies), " ".join(_roles_for_atom(atom))])))
    return round(len(query & target) / max(1, len(query)), 4)


def _atom_matches_any_file(atom: AbilityAtom, candidates: Sequence[str]) -> bool:
    atom_path = atom.file.replace("\\", "/").lower()
    atom_name = Path(atom_path).name
    for candidate in candidates:
        normalized = str(candidate or "").replace("\\", "/").lower().strip()
        if not normalized:
            continue
        if atom_path == normalized or atom_path.endswith("/" + normalized) or atom_name == normalized:
            return True
    return False


def _dedupe_connections(connections: Iterable[EmergentConnection]) -> list[EmergentConnection]:
    best_by_key: dict[tuple[str, str, str, str], EmergentConnection] = {}
    for connection in connections:
        key = (
            connection.emergent_ability,
            connection.source.get("file", ""),
            connection.target.get("file", ""),
            connection.status,
        )
        current = best_by_key.get(key)
        if current is None or connection.emergence_score > current.emergence_score:
            best_by_key[key] = connection
    return list(best_by_key.values())


def _evidence_sources(root: Path) -> list[dict[str, Any]]:
    relative_paths = [
        ".aura/CODEMAP.json",
        ".aura/CODEMAP.md",
        ".aura/MODULE_MANIFEST.json",
        ".aura/RESEARCH_MANIFEST.json",
        ".aura/understand_graph.json",
        "Aura_Staging/empirical_candidate_tree.jsonl",
        "Aura_Memory/architect_loop_ledger.jsonl",
    ]
    output: list[dict[str, Any]] = []
    for relative in relative_paths:
        path = root / relative
        if not path.exists() or not path.is_file():
            output.append({"path": relative, "present": False})
            continue
        try:
            data = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            output.append({"path": relative, "present": True, "read_error": str(exc)})
            continue
        item: dict[str, Any] = {
            "path": relative,
            "present": True,
            "bytes": len(data.encode("utf-8", errors="replace")),
            "sha256": hashlib.sha256(data.encode("utf-8", errors="replace")).hexdigest(),
        }
        if relative.endswith(".json"):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    item["top_level_keys"] = sorted(str(key) for key in parsed.keys())[:12]
                    item["declared_nodes"] = _json_count(parsed, ("nodes", "symbols", "files", "papers"))
            except json.JSONDecodeError:
                item["json_error"] = "invalid_json"
        elif relative.endswith(".jsonl"):
            item["line_count"] = len([line for line in data.splitlines() if line.strip()])
        output.append(item)
    return output


def _json_count(payload: dict[str, Any], keys: Sequence[str]) -> int:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            return len(value)
    return 0


def _source_excerpt(anchor: CodeTopoAnchor, node: CodeTopoNode, *, max_lines: int) -> str:
    lines = anchor.source_texts.get(node.file_path, "").splitlines()
    if not lines:
        return ""
    start = max(1, node.start_line)
    end = min(len(lines), max(start, node.end_line))
    return "\n".join(lines[start - 1 : min(end, start + max_lines - 1)])


def _render_evidence(evidence: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for item in evidence[:4]:
        file_path = str(item.get("file") or item.get("file_path") or "")
        symbol = str(item.get("symbol") or "")
        span = item.get("source_span", "")
        source_hash = str(item.get("source_hash") or "")
        if file_path or symbol:
            rendered.append(f"{file_path}:{symbol} span={span} hash={source_hash[:10]}")
        elif item.get("proposal"):
            rendered.append("operator proposal; no source span yet")
    return " | ".join(rendered) if rendered else "NEEDS_GROUNDING"


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


def _slug(value: str) -> str:
    slug = "_".join(_tokens(value))[:64]
    return slug or "candidate"


def _stable_id(*parts: Any) -> str:
    body = "|".join(str(part) for part in parts)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=8).hexdigest()

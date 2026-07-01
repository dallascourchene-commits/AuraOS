"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b2-[Q-SYS:BUILDER_CONTEXT]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Grounded Builder Context)
DEPENDENCIES: __future__, ast, dataclasses, hashlib, json, pathlib, typing, aura_graphify_schema
FUNCTIONS: BuilderContextPacket, build_builder_context_packet, render_context_packet_prompt, _extract_source_excerpt, _extract_nearby_imports, _extract_callers_from_topology
SYNOPSIS: Constructs a grounded BuilderContextPacket from CODEMAP/Graphify before the Builder model is called. Provides exact source excerpts, symbol line ranges, nearby imports, callers/neighbors, nearby tests, acceptance criteria, forbidden actions, and source_refs — preventing the model from hallucinating file contents or hand-writing fragile hunk headers.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from aura_graphify_schema import SourceRef


@dataclass
class BuilderContextPacket:
    """Grounded context packet delivered to the Builder before patch generation.

    Research basis: SWE-agent/RepoGraph source grounding; GraphCoder graph-context;
    Context Engineering survey's "retrieve-then-ground" pattern.
    """

    target_file: str
    target_symbol: str | None = None
    symbol_start_line: int = 0
    symbol_end_line: int = 0
    source_excerpt: str = ""
    nearby_imports: list[str] = field(default_factory=list)
    callers: list[str] = field(default_factory=list)
    neighbors: list[str] = field(default_factory=list)
    nearby_tests: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    source_refs: list[dict[str, Any]] = field(default_factory=list)
    objective: str = ""
    task_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_prompt_section(self) -> str:
        return render_context_packet_prompt(self)


def _extract_source_excerpt(
    file_path: Path,
    start_line: int,
    end_line: int,
    *,
    context_padding: int = 3,
) -> str:
    """Extract the exact source lines for the target symbol with light padding."""
    if not file_path.exists() or start_line <= 0:
        return ""
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    if not lines:
        return ""
    pad_start = max(1, start_line - context_padding)
    pad_end = min(len(lines), end_line + context_padding) if end_line > 0 else min(len(lines), start_line + 20)
    excerpt_lines: list[str] = []
    for lineno in range(pad_start, pad_end + 1):
        if 1 <= lineno <= len(lines):
            marker = ">>>" if pad_start + context_padding <= lineno <= pad_end - context_padding else "   "
            excerpt_lines.append(f"{lineno:4d} {marker} {lines[lineno - 1]}")
    return "\n".join(excerpt_lines)


def _extract_nearby_imports(file_path: Path, *, max_imports: int = 20) -> list[str]:
    """Parse the target file's import statements via AST."""
    if not file_path.exists():
        return []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8", errors="replace"), filename=str(file_path))
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join(
                (alias.name + (f" as {alias.asname}" if alias.asname else ""))
                for alias in node.names
            )
            imports.append(f"from {module} import {names}")
        if len(imports) >= max_imports:
            break
    return imports[:max_imports]


def _extract_callers_from_topology(
    codemap: dict[str, Any] | None,
    target_file: str,
    target_symbol: str | None,
) -> tuple[list[str], list[str]]:
    """Extract callers and neighbor files from CODEMAP topology data."""
    callers: list[str] = []
    neighbors: list[str] = []
    if not codemap or not target_file:
        return callers, neighbors
    file_name = Path(target_file).name
    topology = codemap.get("topology", {})
    file_index = topology.get("file_index", {})
    file_entry = file_index.get(file_name, {})
    neighbors = list(file_entry.get("neighbor_files", []) or [])
    # Try to find callers from edges if available
    for edge in codemap.get("topology", {}).get("edges", []) or []:
        if not isinstance(edge, dict):
            continue
        edge_target = str(edge.get("target") or "")
        edge_source = str(edge.get("source") or "")
        edge_kind = str(edge.get("kind") or edge.get("type") or "")
        if target_symbol and target_symbol in edge_target and edge_kind in {"CALLS", "calls", "DEPENDS_ON"}:
            callers.append(edge_source)
    return callers[:15], neighbors[:15]


def build_builder_context_packet(
    *,
    target_file: str | None,
    target_symbol: str | None,
    grounding_evidence: dict[str, Any] | None,
    codemap: dict[str, Any] | None,
    repo_root: str | Path,
    objective: str = "",
    task_id: str = "",
    acceptance_criteria: list[str] | None = None,
    forbidden_actions: list[str] | None = None,
) -> BuilderContextPacket:
    """Construct a BuilderContextPacket from CODEMAP/Graphify grounding evidence.

    Gracefully degrades when CODEMAP or symbol hits are unavailable — returns
    a packet with empty optional fields rather than raising.
    """
    root = Path(repo_root)
    normalized_file = target_file or ""
    if normalized_file and not Path(normalized_file).is_absolute():
        file_path = root / normalized_file
    else:
        file_path = Path(normalized_file) if normalized_file else root

    # Extract symbol line range from grounding evidence
    start_line = 0
    end_line = 0
    symbol_hits: list[dict[str, Any]] = []
    nearby_tests: list[str] = []
    neighbors: list[str] = []

    if grounding_evidence:
        symbol_hits = list(grounding_evidence.get("codemap_symbol_hits", []) or [])
        nearby_tests = list(grounding_evidence.get("test_files", []) or [])
        neighbors = list(grounding_evidence.get("neighbor_files", []) or [])
        # Find the matching symbol hit for line range
        for hit in symbol_hits:
            if not isinstance(hit, dict):
                continue
            hit_name = str(hit.get("name") or "")
            if target_symbol and hit_name == target_symbol:
                start_line = int(hit.get("line", 0) or 0)
                end_line = int(hit.get("end_line", start_line) or start_line)
                break
        if start_line == 0 and symbol_hits:
            first_hit = symbol_hits[0]
            if isinstance(first_hit, dict):
                start_line = int(first_hit.get("line", 0) or 0)
                end_line = int(first_hit.get("end_line", start_line) or start_line)

    # If no line range from grounding, try CODEMAP symbol_index
    if start_line == 0 and codemap and target_symbol:
        symbol_index = codemap.get("symbol_index", {})
        hits = symbol_index.get(target_symbol, [])
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            hit_file = str(hit.get("file", ""))
            if Path(hit_file).name == Path(normalized_file).name or hit_file == normalized_file:
                start_line = int(hit.get("line", 0) or 0)
                end_line = int(hit.get("end_line", start_line) or start_line)
                break

    source_excerpt = _extract_source_excerpt(file_path, start_line, end_line)
    nearby_imports = _extract_nearby_imports(file_path)
    callers, topology_neighbors = _extract_callers_from_topology(codemap, normalized_file, target_symbol)

    # Merge neighbors from grounding and topology
    all_neighbors = list(dict.fromkeys([*neighbors, *topology_neighbors]))

    # Build source_refs for Graphify grounding
    source_refs: list[dict[str, Any]] = []
    if normalized_file and file_path.exists():
        source_refs.append(
            SourceRef(
                kind="source_file",
                path=str(file_path),
                key=f"file:{normalized_file}",
                hash=hashlib.blake2b(file_path.read_bytes(), digest_size=8).hexdigest(),
            ).to_dict()
        )
    if codemap:
        codemap_path = root / ".aura" / "CODEMAP.json"
        if codemap_path.exists():
            source_refs.append(
                SourceRef(
                    kind="codemap",
                    path=str(codemap_path),
                    key=f"file:{normalized_file}",
                ).to_dict()
            )
    for test_file in nearby_tests[:3]:
        test_path = root / test_file
        if test_path.exists():
            source_refs.append(
                SourceRef(
                    kind="test_file",
                    path=str(test_path),
                    key=f"test:{test_file}",
                ).to_dict()
            )

    default_forbidden = [
        "Do not write directly to production files.",
        "Do not modify files outside the declared target_file scope.",
        "Do not hand-write hunk headers — return a unified diff or a before/after replacement object.",
        "Do not include prose, explanations, or commentary in the patch output.",
        "Do not touch aura_incubator.py (legacy quarantine).",
    ]

    return BuilderContextPacket(
        target_file=normalized_file,
        target_symbol=target_symbol,
        symbol_start_line=start_line,
        symbol_end_line=end_line,
        source_excerpt=source_excerpt,
        nearby_imports=nearby_imports,
        callers=callers,
        neighbors=all_neighbors,
        nearby_tests=nearby_tests,
        acceptance_criteria=list(acceptance_criteria or [
            "Patch applies cleanly in the temporary workspace.",
            "Patch passes local verification (py_compile + pytest).",
            "Patch does not introduce topology regressions.",
        ]),
        forbidden_actions=list(forbidden_actions or default_forbidden),
        source_refs=source_refs,
        objective=objective,
        task_id=task_id,
    )


def render_context_packet_prompt(packet: BuilderContextPacket) -> str:
    """Render the context packet into a deterministic prompt section for the Builder."""
    lines: list[str] = [
        "=== BUILDER CONTEXT PACKET ===",
        f"target_file: {packet.target_file}",
    ]
    if packet.target_symbol:
        lines.append(f"target_symbol: {packet.target_symbol}")
    if packet.symbol_start_line > 0:
        lines.append(f"symbol_lines: {packet.symbol_start_line}-{packet.symbol_end_line}")
    lines.append("")

    if packet.source_excerpt:
        lines.append("--- source_excerpt (exact lines from repository) ---")
        lines.append(packet.source_excerpt)
        lines.append("--- end source_excerpt ---")
        lines.append("")

    if packet.nearby_imports:
        lines.append("--- nearby_imports ---")
        for imp in packet.nearby_imports:
            lines.append(f"  {imp}")
        lines.append("")

    if packet.callers:
        lines.append("--- callers ---")
        for caller in packet.callers:
            lines.append(f"  {caller}")
        lines.append("")

    if packet.neighbors:
        lines.append("--- neighbor_files ---")
        for neighbor in packet.neighbors:
            lines.append(f"  {neighbor}")
        lines.append("")

    if packet.nearby_tests:
        lines.append("--- nearby_tests ---")
        for test in packet.nearby_tests:
            lines.append(f"  {test}")
        lines.append("")

    if packet.acceptance_criteria:
        lines.append("--- acceptance_criteria ---")
        for criterion in packet.acceptance_criteria:
            lines.append(f"  - {criterion}")
        lines.append("")

    if packet.forbidden_actions:
        lines.append("--- forbidden_actions ---")
        for action in packet.forbidden_actions:
            lines.append(f"  - {action}")
        lines.append("")

    lines.append("=== OUTPUT FORMAT ===")
    lines.append("Return EITHER:")
    lines.append("  1. A full valid unified diff (with correct @@ hunk headers), OR")
    lines.append("  2. A JSON object: {\"before_text\": \"...\", \"after_text\": \"...\"} where before_text is the exact text to replace and after_text is the replacement.")
    lines.append("Do NOT include prose, explanations, or commentary.")
    lines.append("=== END BUILDER CONTEXT PACKET ===")

    return "\n".join(lines)
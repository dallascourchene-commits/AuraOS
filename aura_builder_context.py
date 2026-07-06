"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b2-[Q-SYS:BUILDER_CONTEXT]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Grounded Builder Context)
DEPENDENCIES: __future__, ast, dataclasses, hashlib, pathlib, typing, aura_graphify_schema, aura_st3gg_codec
FUNCTIONS: BuilderContextPacket, build_builder_context_packet, attach_st3gg_summary, render_context_packet_prompt, _extract_source_excerpt, _extract_nearby_imports, _extract_callers_from_topology
SYNOPSIS: Constructs a grounded BuilderContextPacket from CODEMAP/Graphify before the Builder model is called. Provides exact source excerpts, symbol line ranges, nearby imports, callers/neighbors, nearby tests, acceptance criteria, forbidden actions, and source_refs — preventing the model from hallucinating file contents or hand-writing fragile hunk headers.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from aura_graphify_schema import SourceRef
from aura_st3gg_codec import ST3GGCodec, ST3GGProfile, choose_profile_for_phase


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
    st3gg_context: dict[str, Any] = field(default_factory=dict)
    topological_context: dict[str, Any] = field(default_factory=dict)
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
            names = ", ".join((alias.name + (f" as {alias.asname}" if alias.asname else "")) for alias in node.names)
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


def _resolve_repo_python_file(root: Path, candidate: str | Path | None) -> tuple[str, Path] | None:
    if not candidate:
        return None
    raw = Path(str(candidate))
    file_path = raw if raw.is_absolute() else root / raw
    try:
        resolved_root = root.resolve()
        resolved_file = file_path.resolve()
        rel = resolved_file.relative_to(resolved_root).as_posix()
    except (OSError, ValueError):
        return None
    if resolved_file.suffix != ".py" or not resolved_file.exists():
        return None
    return rel, resolved_file


def _build_topological_context_payload(
    *,
    target_file: str,
    target_symbol: str | None,
    repo_root: Path,
    candidate_files: list[str],
) -> dict[str, Any]:
    """Attach a small exact topology packet without replacing source_excerpt."""
    try:
        from aura_topological_context_anchor import CodeTopoAnchor, render_builder_context
    except Exception as exc:
        return {
            "ok": False,
            "warnings": [f"topological_context_anchor_unavailable:{type(exc).__name__}"],
        }

    files: dict[str, str] = {}
    for candidate in [target_file, *candidate_files]:
        resolved = _resolve_repo_python_file(repo_root, candidate)
        if not resolved:
            continue
        rel, path = resolved
        if rel in files:
            continue
        try:
            files[rel] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(files) >= 10:
            break

    if not files:
        return {
            "ok": False,
            "warnings": ["topological_context_no_python_sources"],
        }

    anchor = CodeTopoAnchor.build_from_files(files)
    warnings = list(anchor.warnings)
    if not target_symbol:
        return {
            "ok": False,
            "version": anchor.metadata.get("version"),
            "warnings": [*warnings, "topological_context_target_symbol_missing"],
            "anchor_metadata": anchor.metadata,
        }

    packet = anchor.nearest_context(target_symbol, radius=1)
    return {
        "ok": bool(packet.target_nodes),
        "version": anchor.metadata.get("version"),
        "anchor_metadata": anchor.metadata,
        "packet": packet.to_dict(),
        "rendered": render_builder_context(packet),
        "warnings": list(dict.fromkeys([*warnings, *packet.warnings])),
    }


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
    topological_context = _build_topological_context_payload(
        target_file=normalized_file,
        target_symbol=target_symbol,
        repo_root=root,
        candidate_files=[*all_neighbors[:5], *nearby_tests[:4]],
    )

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
        topological_context=topological_context,
        nearby_imports=nearby_imports,
        callers=callers,
        neighbors=all_neighbors,
        nearby_tests=nearby_tests,
        acceptance_criteria=list(
            acceptance_criteria
            or [
                "Patch applies cleanly in the temporary workspace.",
                "Patch passes local verification (py_compile + pytest).",
                "Patch does not introduce topology regressions.",
            ]
        ),
        forbidden_actions=list(forbidden_actions or default_forbidden),
        source_refs=source_refs,
        objective=objective,
        task_id=task_id,
    )


def attach_st3gg_summary(
    packet: BuilderContextPacket,
    *,
    source: str | None = None,
    repo_root: str | Path | None = None,
    profile: ST3GGProfile | str | None = None,
) -> BuilderContextPacket:
    """Attach compact ST3GG context without replacing Builder's exact source excerpt."""
    selected_profile = (
        ST3GGProfile.coerce(profile) if profile is not None else choose_profile_for_phase("builder_patch")
    )
    source_text = source
    attach_warnings: list[str] = []

    if source_text is None and packet.target_file:
        root = Path(repo_root) if repo_root is not None else Path.cwd()
        target_path = Path(packet.target_file)
        file_path = target_path if target_path.is_absolute() else root / target_path
        # Path traversal check: ensure resolved file_path stays inside resolved root
        try:
            resolved_root = root.resolve()
            resolved_file = file_path.resolve()
            # Manual prefix check for cross-version compatibility (is_relative_to needs Python 3.9+)
            try:
                resolved_file.relative_to(resolved_root)
                path_is_safe = True
            except ValueError:
                path_is_safe = False
            if not path_is_safe:
                attach_warnings.append("st3gg_source_path_outside_repo_root")
            else:
                source_text = resolved_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            attach_warnings.append(f"st3gg_source_read_failed:{type(exc).__name__}")

    if source_text is None and packet.source_excerpt:
        source_text = packet.source_excerpt
        attach_warnings.append("st3gg_source_from_line_marked_excerpt")

    if source_text is None:
        packet.st3gg_context = {
            "version": "AURA_ST3GG_CODEC_V1",
            "profile": selected_profile.value,
            "source_file": packet.target_file,
            "target_symbol": packet.target_symbol,
            "encoded": "",
            "symbols": [],
            "spans": [],
            "metrics": {},
            "warnings": [*attach_warnings, "st3gg_attach_no_source"],
        }
        return packet

    frame = ST3GGCodec().encode_source(
        source_text,
        source_file=packet.target_file,
        target_symbol=packet.target_symbol,
        profile=selected_profile,
    )
    payload = frame.to_dict()
    if attach_warnings:
        payload["warnings"] = [*payload.get("warnings", []), *attach_warnings]
    packet.st3gg_context = payload
    return packet


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

    if packet.st3gg_context:
        st3gg = packet.st3gg_context
        metrics = st3gg.get("metrics", {}) if isinstance(st3gg.get("metrics", {}), dict) else {}
        lines.append("--- st3gg_compact_context (advisory; exact source_excerpt remains authoritative) ---")
        lines.append(f"profile: {st3gg.get('profile', '')}")
        lines.append(f"source_hash: {st3gg.get('source_hash', '')}")
        if metrics:
            lines.append(
                "metrics: "
                f"raw_tokens={metrics.get('raw_token_estimate', 0)} "
                f"encoded_tokens={metrics.get('encoded_token_estimate', 0)} "
                f"compression_ratio={metrics.get('compression_ratio', 0)} "
                f"fidelity={metrics.get('fidelity_score', 0)}"
            )
        warnings = list(st3gg.get("warnings", []) or [])
        if warnings:
            lines.append("warnings: " + "; ".join(str(item) for item in warnings))
        symbols = list(st3gg.get("symbols", []) or [])[:30]
        if symbols:
            symbol_line = "; ".join(
                f"{item.get('id')}={item.get('name')}#{item.get('count')}" for item in symbols if isinstance(item, dict)
            )
            if symbol_line:
                lines.append("symbols: " + symbol_line)
        encoded = str(st3gg.get("encoded", "") or "")
        if encoded:
            lines.append(encoded)
        spans = list(st3gg.get("spans", []) or [])[:8]
        if spans:
            lines.append("st3gg_exact_spans:")
            for span in spans:
                if not isinstance(span, dict):
                    continue
                lines.append(
                    f"  {span.get('id')} {span.get('kind')} {span.get('name', '')} "
                    f"lines={span.get('line_start', 0)}-{span.get('line_end', 0)}"
                )
                text = str(span.get("text", "") or "")
                if text:
                    lines.append(text)
        lines.append("--- end st3gg_compact_context ---")
        lines.append("")

    if packet.topological_context:
        rendered_topology = str(packet.topological_context.get("rendered") or "")
        if rendered_topology:
            lines.append(rendered_topology)
            lines.append("")
        else:
            warnings = list(packet.topological_context.get("warnings", []) or [])
            lines.append("--- topological_context_anchor ---")
            lines.append("status: unavailable")
            if warnings:
                lines.append("warnings: " + "; ".join(str(item) for item in warnings))
            lines.append("--- end topological_context_anchor ---")
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
    lines.append(
        '  2. A JSON object: {"before_text": "...", "after_text": "..."} where before_text is the exact text to replace and after_text is the replacement.'
    )
    lines.append("Do NOT include prose, explanations, or commentary.")
    lines.append("=== END BUILDER CONTEXT PACKET ===")

    return "\n".join(lines)

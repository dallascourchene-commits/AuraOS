"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa31-[Q-SYS:SYMBOLIC_TRACE_MEMORY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Traceable Symbolic Memory)
DEPENDENCIES: __future__, dataclasses, datetime, hashlib, json, pathlib, re, typing
FUNCTIONS: record_trace_event, offload_raw_evidence, build_trace_canvas, render_trace_canvas_for_prompt, lookup_trace_node, should_inject_canvas, score_replaceability, summarize_trace_memory
SYNOPSIS: Stdlib-only layered symbolic trace memory for Coding Arena evidence offload. Compact atoms/canvases are advisory and always retain raw_ref/source_hash drill-down back to Aura-local evidence.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


TRACE_MEMORY_VERSION = "AURA_SYMBOLIC_TRACE_MEMORY_V1"
TRACE_ATOMS_FILE = "trace_atoms.jsonl"
TRACE_REFS_DIR = "trace_refs"
TRACE_CANVASES_DIR = "trace_canvases"

_UNSAFE_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_UNSAFE_PATH_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_WHITESPACE_RE = re.compile(r"\s+")
_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(authorization)\s*[:=]\s*bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\s*[:=]\s*['\"]?[^'\"\s,}]+"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]


@dataclass
class AuraTraceRef:
    ref_id: str
    node_id: str
    kind: str
    path: str
    source_hash: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuraTraceRef":
        return cls(
            ref_id=str(data.get("ref_id", "")),
            node_id=str(data.get("node_id", "")),
            kind=str(data.get("kind", "raw")),
            path=str(data.get("path", "")),
            source_hash=str(data.get("source_hash", "")),
            created_at=str(data.get("created_at", "")),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass
class AuraTraceAtom:
    atom_id: str
    node_id: str
    event_type: str
    task_id: str
    summary: str
    raw_ref: str
    source_hash: str
    replaceability_score: float
    route: str
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuraTraceAtom":
        return cls(
            atom_id=str(data.get("atom_id", "")),
            node_id=str(data.get("node_id", "")),
            event_type=str(data.get("event_type", "trace_event")),
            task_id=str(data.get("task_id", "")),
            summary=str(data.get("summary", "")),
            raw_ref=str(data.get("raw_ref", "")),
            source_hash=str(data.get("source_hash", "")),
            replaceability_score=_clamp_float(data.get("replaceability_score", 0.0)),
            route=str(data.get("route", "")),
            status=str(data.get("status", "")),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass
class AuraTraceNode:
    node_id: str
    label: str
    status: str
    summary: str
    atom_ids: list[str] = field(default_factory=list)
    raw_refs: list[str] = field(default_factory=list)
    source_hashes: list[str] = field(default_factory=list)
    related_symbols: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)
    route: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuraTraceCanvas:
    canvas_id: str
    task_id: str
    title: str
    mermaid: str
    nodes: list[AuraTraceNode] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    token_estimate: int = 0
    raw_refs: list[str] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuraTraceMemoryConfig:
    mild_context_ratio: float = 0.50
    aggressive_context_ratio: float = 0.85
    emergency_context_ratio: float = 0.95
    canvas_max_token_ratio: float = 0.20
    max_atoms_per_canvas: int = 50
    max_raw_ref_chars: int = 200_000

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuraTraceMemoryReport:
    memory_root: str
    atom_count: int
    ref_count: int
    canvas_count: int
    node_count: int
    warnings: list[str] = field(default_factory=list)
    latest_canvas_id: str = ""
    raw_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def offload_raw_evidence(
    node_id: str,
    raw_text: str,
    memory_root: str | Path,
    kind: str = "raw",
) -> AuraTraceRef:
    """Persist L0 raw evidence as an Aura-local Markdown ref file."""
    base = _memory_base(memory_root)
    refs_dir = base / TRACE_REFS_DIR / _safe_filename(node_id or "node")
    refs_dir.mkdir(parents=True, exist_ok=True)
    original = "" if raw_text is None else str(raw_text)
    redacted = _redact_secrets(_sanitize_text(original))
    source_hash = _hash_text(redacted)
    safe_node = _safe_filename(node_id or _stable_id("node", source_hash))
    safe_kind = _safe_filename(kind or "raw")
    ref_id = f"{safe_node}-{source_hash[:16]}"
    ref_path = refs_dir / f"{ref_id}.md"
    created_at = _utc_now()
    was_redacted = redacted != _sanitize_text(original)
    body = [
        "---",
        f"ref_id: {ref_id}",
        f"node_id: {node_id}",
        f"kind: {safe_kind}",
        f"source_hash: {source_hash}",
        f"created_at: {created_at}",
        f"redacted: {str(was_redacted).lower()}",
        "---",
        "",
        "# Aura Trace Raw Evidence",
        "",
        redacted,
        "",
    ]
    ref_path.write_text("\n".join(body), encoding="utf-8")
    return AuraTraceRef(
        ref_id=ref_id,
        node_id=str(node_id),
        kind=safe_kind,
        path=_aura_local_path(base, ref_path),
        source_hash=source_hash,
        created_at=created_at,
        metadata={"version": TRACE_MEMORY_VERSION, "redacted": was_redacted},
    )


def record_trace_event(event: dict, memory_root: str | Path) -> AuraTraceAtom:
    """Append an L1 trace atom and offload full payload/raw text when needed."""
    payload = dict(event or {})
    event_type = _safe_inline(payload.get("event_type") or payload.get("type") or "trace_event", 80)
    task_id = _safe_inline(payload.get("task_id") or payload.get("workflow_id") or payload.get("phase") or "global", 120)
    provided_raw_ref = str(payload.get("raw_ref") or "")
    provided_source_hash = str(payload.get("source_hash") or "")
    raw_text = _event_raw_text(payload)
    fingerprint_body = raw_text or provided_source_hash or json.dumps(_sanitize_json(payload), sort_keys=True, default=str)
    node_id = _safe_inline(payload.get("node_id") or _stable_node_id(task_id, event_type, fingerprint_body), 160)

    raw_ref = provided_raw_ref
    source_hash = provided_source_hash
    ref: AuraTraceRef | None = None
    if raw_text and not raw_ref:
        ref = offload_raw_evidence(node_id, raw_text, memory_root, kind=event_type)
    elif not raw_ref and not source_hash:
        ref = offload_raw_evidence(
            node_id,
            json.dumps(_sanitize_json(payload), indent=2, sort_keys=True, default=str),
            memory_root,
            kind=event_type,
        )
    if ref is not None:
        raw_ref = ref.ref_id
        source_hash = ref.source_hash

    summary = _safe_inline(payload.get("summary") or _derive_summary(payload), 500)
    atom_id = str(payload.get("atom_id") or f"AT-{_stable_id(task_id, node_id, event_type, source_hash, summary)}")
    metadata = _trace_metadata(payload)
    metadata.setdefault("created_at", _utc_now())
    metadata.setdefault("version", TRACE_MEMORY_VERSION)
    if ref is not None:
        metadata.setdefault("raw_ref_path", ref.path)
    atom = AuraTraceAtom(
        atom_id=atom_id,
        node_id=node_id,
        event_type=event_type,
        task_id=task_id,
        summary=summary,
        raw_ref=raw_ref,
        source_hash=source_hash,
        replaceability_score=_clamp_float(payload.get("replaceability_score", score_replaceability(payload))),
        route=_safe_inline(payload.get("route") or payload.get("phase") or payload.get("event_route") or "", 120),
        status=_safe_inline(payload.get("status") or _status_from_event(payload), 80),
        metadata=metadata,
    )
    _append_atom(atom, memory_root)
    return atom


def build_trace_canvas(
    task_id: str,
    memory_root: str | Path,
    mode: str = "coding_arena",
) -> AuraTraceCanvas:
    """Consolidate L1 atoms into a compact L2 Mermaid canvas."""
    config = AuraTraceMemoryConfig()
    base = _memory_base(memory_root)
    atoms, warnings = _load_atoms(base / TRACE_ATOMS_FILE)
    wanted_task = str(task_id or "")
    if wanted_task:
        selected = [atom for atom in atoms if atom.task_id == wanted_task]
    else:
        selected = list(atoms)
    selected = selected[-config.max_atoms_per_canvas :]
    nodes = _nodes_from_atoms(selected)
    mermaid = _render_mermaid(nodes)
    raw_refs = _unique(ref for node in nodes for ref in node.raw_refs if ref)
    canvas_id = f"TC-{_stable_id(wanted_task, mode, mermaid, len(selected))}"
    canvas = AuraTraceCanvas(
        canvas_id=canvas_id,
        task_id=wanted_task,
        title=f"Aura trace canvas for {wanted_task or 'all tasks'}",
        mermaid=mermaid,
        nodes=nodes,
        warnings=[
            *warnings,
            "trace_summaries_are_advisory_not_patch_evidence",
            "exact_topological_source_spans_and_verifier_gates_remain_authoritative",
        ],
        token_estimate=_estimate_tokens(mermaid),
        raw_refs=raw_refs,
        updated_at=_utc_now(),
    )
    canvases_dir = base / TRACE_CANVASES_DIR
    canvases_dir.mkdir(parents=True, exist_ok=True)
    canvas_path = canvases_dir / f"{_safe_filename(wanted_task or 'all')}.json"
    canvas_path.write_text(json.dumps(_sanitize_json(canvas.to_dict()), indent=2, sort_keys=True), encoding="utf-8")
    return canvas


def render_trace_canvas_for_prompt(canvas: AuraTraceCanvas) -> str:
    """Render a compact L2 canvas for prompt injection."""
    if not canvas.nodes and not canvas.mermaid.strip():
        return ""
    lines = [
        "=== AURA SYMBOLIC TRACE CANVAS (ADVISORY) ===",
        f"canvas_id: {canvas.canvas_id}",
        f"task_id: {canvas.task_id}",
        "patch_authority: exact source spans/source_hashes from Topological Context Anchor and verifier evidence only",
        "drill_down: lookup_trace_node(node_id/source_hash/raw_ref) recovers Aura_Memory trace refs",
    ]
    if canvas.warnings:
        lines.append("warnings: " + "; ".join(_safe_inline(item, 140) for item in canvas.warnings[:6]))
    lines.extend(["```mermaid", canvas.mermaid, "```"])
    lines.append("nodes:")
    for node in canvas.nodes[:20]:
        refs = ",".join(node.raw_refs[:2]) or "none"
        hashes = ",".join(item[:16] for item in node.source_hashes[:2]) or "none"
        files = ",".join(node.related_files[:3])
        suffix = f" files={files}" if files else ""
        lines.append(
            f"- node_id={node.node_id} status={node.status} route={node.route or 'n/a'} "
            f"raw_ref={refs} source_hash={hashes}{suffix} summary={_safe_inline(node.summary, 160)}"
        )
    lines.append("=== END AURA SYMBOLIC TRACE CANVAS ===")
    return "\n".join(lines)


def lookup_trace_node(node_id: str, memory_root: str | Path) -> dict:
    """Recover atoms and L0 raw refs by node_id, source_hash, raw_ref, or atom_id."""
    base = _memory_base(memory_root)
    query = str(node_id or "")
    atoms, warnings = _load_atoms(base / TRACE_ATOMS_FILE)
    matches = [
        atom
        for atom in atoms
        if atom.node_id == query
        or atom.source_hash == query
        or atom.raw_ref == query
        or atom.atom_id == query
    ]
    if not matches:
        ref_match = _find_ref_by_key(base, query)
        if ref_match:
            raw_text = _read_text_limited(ref_match, AuraTraceMemoryConfig().max_raw_ref_chars)
            return {
                "query": query,
                "node": {},
                "atoms": [],
                "raw_refs": [query],
                "raw_evidence": {query: raw_text},
                "warnings": warnings,
            }
    nodes = _nodes_from_atoms(matches)
    raw_evidence: dict[str, str] = {}
    for raw_ref in _unique(atom.raw_ref for atom in matches if atom.raw_ref):
        ref_path = _find_ref_by_key(base, raw_ref)
        if ref_path:
            raw_evidence[raw_ref] = _read_text_limited(ref_path, AuraTraceMemoryConfig().max_raw_ref_chars)
    return {
        "query": query,
        "node": nodes[0].to_dict() if nodes else {},
        "atoms": [atom.to_dict() for atom in matches],
        "raw_refs": _unique(atom.raw_ref for atom in matches if atom.raw_ref),
        "raw_evidence": raw_evidence,
        "warnings": warnings,
    }


def should_inject_canvas(
    current_tokens: int,
    context_window: int,
    config: AuraTraceMemoryConfig,
) -> str:
    """Return none/mild/aggressive/emergency for canvas injection pressure."""
    if context_window <= 0:
        return "none"
    ratio = max(0.0, float(current_tokens)) / float(context_window)
    if ratio >= config.emergency_context_ratio:
        return "emergency"
    if ratio >= config.aggressive_context_ratio:
        return "aggressive"
    if ratio >= config.mild_context_ratio:
        return "mild"
    return "none"


def score_replaceability(event: dict) -> float:
    """Score whether compact memory can safely stand in for raw text."""
    payload = dict(event or {})
    event_type = str(payload.get("event_type") or payload.get("type") or "").lower()
    body = json.dumps(_sanitize_json(payload), sort_keys=True, default=str).lower()
    low_markers = [
        "source_excerpt",
        "exact_source",
        "source_span",
        "source_hash",
        "topological context anchor",
        "patch_authority",
        "diff --git",
        "unified diff",
        "@@ ",
        "before_text",
        "after_text",
        "extracted_diff",
        "verifier evidence",
    ]
    if any(marker in body for marker in low_markers) or any(
        marker in event_type for marker in ("patch", "diff", "source", "verifier")
    ):
        return 0.1
    if any(marker in event_type for marker in ("failure", "blocked", "preflight", "repair")):
        return 0.35
    if any(marker in event_type for marker in ("candidate", "summary", "judge", "capability", "finding")):
        return 0.7
    if "raw" in event_type:
        return 0.25
    return 0.55


def summarize_trace_memory(memory_root: str | Path) -> AuraTraceMemoryReport:
    base = _memory_base(memory_root)
    atoms, warnings = _load_atoms(base / TRACE_ATOMS_FILE)
    refs_dir = base / TRACE_REFS_DIR
    canvases_dir = base / TRACE_CANVASES_DIR
    refs = sorted(refs_dir.rglob("*.md")) if refs_dir.exists() else []
    canvases = sorted(canvases_dir.glob("*.json")) if canvases_dir.exists() else []
    latest_canvas_id = ""
    if canvases:
        try:
            latest = json.loads(canvases[-1].read_text(encoding="utf-8"))
            latest_canvas_id = str(latest.get("canvas_id", ""))
        except (OSError, json.JSONDecodeError):
            warnings.append(f"corrupt_canvas:{canvases[-1].name}")
    return AuraTraceMemoryReport(
        memory_root=str(base),
        atom_count=len(atoms),
        ref_count=len(refs),
        canvas_count=len(canvases),
        node_count=len({atom.node_id for atom in atoms}),
        warnings=warnings,
        latest_canvas_id=latest_canvas_id,
        raw_refs=[_aura_local_path(base, ref) for ref in refs[:50]],
    )


def _append_atom(atom: AuraTraceAtom, memory_root: str | Path) -> None:
    base = _memory_base(memory_root)
    base.mkdir(parents=True, exist_ok=True)
    path = base / TRACE_ATOMS_FILE
    line = json.dumps(_sanitize_json(atom.to_dict()), sort_keys=True, ensure_ascii=True, default=str)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _load_atoms(path: Path) -> tuple[list[AuraTraceAtom], list[str]]:
    atoms: list[AuraTraceAtom] = []
    warnings: list[str] = []
    if not path.exists():
        return atoms, warnings
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return atoms, [f"trace_atoms_read_failed:{type(exc).__name__}"]
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(_sanitize_text(stripped))
            atoms.append(AuraTraceAtom.from_dict(data))
        except (TypeError, json.JSONDecodeError, ValueError) as exc:
            warnings.append(f"corrupt_jsonl_line:{lineno}:{type(exc).__name__}")
    return atoms, warnings


def _nodes_from_atoms(atoms: list[AuraTraceAtom]) -> list[AuraTraceNode]:
    by_node: dict[str, list[AuraTraceAtom]] = {}
    for atom in atoms:
        by_node.setdefault(atom.node_id, []).append(atom)
    nodes: list[AuraTraceNode] = []
    for node_id, group in by_node.items():
        latest = group[-1]
        summaries = _unique(atom.summary for atom in group if atom.summary)
        related_symbols = _unique(
            value
            for atom in group
            for value in _as_list(atom.metadata.get("related_symbols") or atom.metadata.get("target_symbol"))
        )
        related_files = _unique(
            value
            for atom in group
            for value in _as_list(atom.metadata.get("related_files") or atom.metadata.get("target_file"))
        )
        node = AuraTraceNode(
            node_id=node_id,
            label=_label_from_atom(latest),
            status=_canvas_status(latest.status, latest.event_type),
            summary=_safe_inline(" | ".join(summaries[-3:]), 360),
            atom_ids=[atom.atom_id for atom in group],
            raw_refs=_unique(atom.raw_ref for atom in group if atom.raw_ref),
            source_hashes=_unique(atom.source_hash for atom in group if atom.source_hash),
            related_symbols=[str(item) for item in related_symbols],
            related_files=[str(item) for item in related_files],
            route=latest.route,
            confidence=round(max(0.1, min(0.95, 1.0 - latest.replaceability_score / 2)), 4),
        )
        nodes.append(node)
    return nodes


def _render_mermaid(nodes: list[AuraTraceNode]) -> str:
    lines = ["graph TD"]
    if not nodes:
        lines.append('    EMPTY["no trace atoms yet"]')
        return "\n".join(lines)
    aliases: dict[str, str] = {}
    for index, node in enumerate(nodes, start=1):
        alias = f"N{index}"
        aliases[node.node_id] = alias
        label = _mermaid_label(
            f"{node.node_id}<br/>{node.status}: {node.label}<br/>raw:{','.join(node.raw_refs[:1]) or 'source_hash'}"
        )
        lines.append(f'    {alias}["{label}"]')
    for left, right in zip(nodes, nodes[1:]):
        lines.append(f"    {aliases[left.node_id]} --> {aliases[right.node_id]}")
    lines.extend(
        [
            "    classDef done fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20",
            "    classDef doing fill:#e3f2fd,stroke:#1565c0,color:#0d47a1",
            "    classDef blocked fill:#ffebee,stroke:#c62828,color:#7f0000",
            "    classDef proposed fill:#fff8e1,stroke:#f9a825,color:#5f4300",
        ]
    )
    for node in nodes:
        status = _canvas_status(node.status, "")
        if status in {"done", "doing", "blocked", "proposed"}:
            lines.append(f"    class {aliases[node.node_id]} {status}")
    return "\n".join(lines)


def _trace_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    out = dict(metadata or {})
    for key in (
        "target_file",
        "target_symbol",
        "related_files",
        "related_symbols",
        "phase",
        "route",
        "status",
        "candidate_id",
        "critic_id",
        "workflow_id",
        "source",
    ):
        if key in payload and key not in out:
            out[key] = payload.get(key)
    out["event_keys"] = sorted(str(key) for key in payload.keys() if key not in {"raw_text", "raw", "raw_evidence"})
    return _sanitize_json(out)


def _event_raw_text(payload: dict[str, Any]) -> str:
    for key in ("raw_text", "raw", "raw_evidence", "raw_model_response", "builder_prompt", "extracted_diff"):
        if payload.get(key) not in (None, ""):
            return str(payload.get(key))
    return ""


def _derive_summary(payload: dict[str, Any]) -> str:
    parts = []
    for key in ("event_type", "status", "task_id", "target_file", "target_symbol", "candidate_id", "critic_id"):
        value = payload.get(key)
        if value not in (None, "", [], {}):
            parts.append(f"{key}={value}")
    if payload.get("objective"):
        parts.append(f"objective={payload.get('objective')}")
    if payload.get("rationale"):
        parts.append(f"rationale={payload.get('rationale')}")
    if parts:
        return "; ".join(str(part) for part in parts)
    slim = {key: value for key, value in payload.items() if key not in {"raw_text", "raw", "raw_evidence"}}
    return json.dumps(_sanitize_json(slim), sort_keys=True, default=str)[:240]


def _status_from_event(payload: dict[str, Any]) -> str:
    text = " ".join(str(payload.get(key, "")) for key in ("event_type", "type", "status", "summary")).lower()
    if any(term in text for term in ("fail", "blocked", "reject", "rollback", "missing", "no_response")):
        return "blocked"
    if any(term in text for term in ("running", "started", "prompt", "preflight")):
        return "doing"
    if any(term in text for term in ("candidate", "future", "finding", "proposed", "plan")):
        return "proposed"
    if any(term in text for term in ("pass", "ready", "staged", "done", "success", "selected")):
        return "done"
    return "proposed"


def _canvas_status(status: str, event_type: str) -> str:
    text = f"{status} {event_type}".lower()
    if any(term in text for term in ("blocked", "failed", "reject", "rollback", "missing", "no_response")):
        return "blocked"
    if any(term in text for term in ("doing", "running", "prompt", "preflight")):
        return "doing"
    if any(term in text for term in ("done", "passed", "ready", "staged", "success", "selected")):
        return "done"
    return "proposed"


def _label_from_atom(atom: AuraTraceAtom) -> str:
    label = atom.event_type.replace("_", " ").strip() or "trace"
    return _safe_inline(label, 80)


def _memory_base(memory_root: str | Path) -> Path:
    root = Path(memory_root)
    if root.name == "Aura_Memory":
        return root
    return root / "Aura_Memory"


def _aura_local_path(base: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve().parent).as_posix()
    except (OSError, ValueError):
        try:
            return path.resolve().relative_to(base.resolve()).as_posix()
        except (OSError, ValueError):
            return path.as_posix()


def _find_ref_by_key(base: Path, key: str) -> Path | None:
    if not key:
        return None
    direct = base.parent / key
    if direct.exists() and direct.is_file():
        return direct
    direct = base / key
    if direct.exists() and direct.is_file():
        return direct
    refs_dir = base / TRACE_REFS_DIR
    if not refs_dir.exists():
        return None
    safe_key = _safe_filename(key)
    for candidate in refs_dir.rglob("*.md"):
        name = candidate.stem
        if name == key or name == safe_key or key in name:
            return candidate
        try:
            head = candidate.read_text(encoding="utf-8", errors="replace")[:800]
        except OSError:
            continue
        if key in head:
            return candidate
    return None


def _read_text_limited(path: Path, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"<trace_ref_read_failed:{type(exc).__name__}>"
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n<trace_ref_truncated_for_lookup>"


def _sanitize_text(text: Any) -> str:
    return _UNSAFE_CONTROL_RE.sub("", str(text).replace("\r\n", "\n").replace("\r", "\n"))


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(_sanitize_text(key)): _sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, (str, bytes)):
        raw = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
        return _redact_secrets(_sanitize_text(raw))
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _redact_secrets(_sanitize_text(value))


def _redact_secrets(text: str) -> str:
    redacted = str(text)
    for pattern in _SECRET_PATTERNS:
        if "api" in pattern.pattern.lower() or "token" in pattern.pattern.lower() or "secret" in pattern.pattern.lower() or "password" in pattern.pattern.lower():
            redacted = pattern.sub(lambda match: f"{match.group(1)}=<redacted>" if match.groups() else "<redacted>", redacted)
        else:
            redacted = pattern.sub("<redacted>", redacted)
    return redacted


def _safe_filename(value: Any, limit: int = 120) -> str:
    text = _UNSAFE_PATH_RE.sub("_", _sanitize_text(value)).strip(" ._")
    text = re.sub(r"_+", "_", text)
    if not text:
        text = "trace"
    return text[:limit]


def _safe_inline(value: Any, limit: int = 240) -> str:
    text = _WHITESPACE_RE.sub(" ", _sanitize_text(value)).strip()
    return text[:limit]


def _mermaid_label(value: str) -> str:
    text = _sanitize_text(value).replace('"', "'").replace("[", "(").replace("]", ")")
    return text[:220]


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8", errors="replace")).hexdigest()


def _stable_id(*parts: Any) -> str:
    body = "|".join(str(part) for part in parts)
    return hashlib.blake2b(body.encode("utf-8", errors="replace"), digest_size=10).hexdigest()


def _stable_node_id(task_id: str, event_type: str, body: Any) -> str:
    return f"TN-{_stable_id(task_id, event_type, body)[:14]}"


def _estimate_tokens(text: str) -> int:
    return max(1, len(str(text)) // 4)


def _clamp_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _unique(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for value in values:
        if value in (None, ""):
            continue
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

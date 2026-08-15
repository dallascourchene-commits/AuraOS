"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, __future__, ast, aura_topological_scanner, re, argparse, aura_substrate, typing, os, pathlib, time, math, collections, dataclasses, hashlib
FUNCTIONS: _symbol_signature, _semantic_id, stable_unit_vector, cosine, _is_probably_binary, classify_file, _python_symbol_records, _iter_repo_files, _command_mentions, _command_locations, load_or_compile_topology, _node_file, _topology_file_index, scan_repository, _scan_file, _coverage_report, _navigation_rings, _symbol_index, _records_from_cards, _incremental_record_fingerprint, refresh_index_for_paths, _command_index, _top_hubs, _compact_file_cards, _attach_topology, build_navigation_system, search_index, write_navigation_artifacts, _load_json, _codemap_payload_hash, refresh_codemap_for_paths, main, _skip_part
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any

from aura_substrate import IntentCompressor, estimate_tokens, parse_master_key_header
from aura_topological_scanner import compile_topology_map

DEFAULT_SKIP_DIRS = frozenset({
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "Aura_Memory",
    "Aura_Sandbox",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".nox",
    "site-packages",
    "build",
    "dist",
    ".eggs",
    "*.egg-info",
    "runtime",
})
BINARY_SUFFIXES = frozenset({".bak", ".db", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".ttf", ".zip"})
TEXT_SUFFIXES = frozenset({"", ".c", ".cpp", ".css", ".html", ".js", ".json", ".lexc", ".md", ".py", ".rs", ".sh", ".tex", ".toml", ".txt", ".yml", ".yaml"})
DEFAULT_INDEX_PATH = Path(".aura/CODEMAP.json")
DEFAULT_MARKDOWN_PATH = Path(".aura/CODEMAP.md")
DEFAULT_TOPOLOGY_PATH = Path("Aura_Memory/live_topology_ast.json")
GENERATED_MAP_FILES = {DEFAULT_INDEX_PATH.as_posix(), DEFAULT_MARKDOWN_PATH.as_posix(), ".aura/SOURCE_ANCHORS.md", "topology_map.json"}
VECTOR_DIMS = 32
MAX_SYMBOLS_PER_FILE = 80


@dataclass(frozen=True)
class SymbolRecord:
    name: str
    kind: str
    line: int
    end_line: int
    semantic_id: str
    signature_hash: str


def _symbol_signature(node: ast.AST) -> str:
    """Return a stable semantic signature for a Python class/function node."""
    if isinstance(node, ast.ClassDef):
        bases = ",".join(ast.unparse(base) for base in node.bases)
        return f"class {node.name}({bases})"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}{ast.unparse(node.args)}"
    return type(node).__name__


def _semantic_id(path: str, kind: str, name: str, signature: str) -> str:
    """Create a short identity that survives line shifts inside the same file."""
    digest = hashlib.blake2b(f"{path}|{kind}|{name}|{signature}".encode("utf-8", errors="replace"), digest_size=8).hexdigest()
    return f"{path}#{kind}:{name}:{digest}"


def stable_unit_vector(seed_text: str, dims: int = VECTOR_DIMS) -> list[float]:
    """Create a deterministic small VSA-like unit vector for query/file resonance."""
    digest = hashlib.blake2b(seed_text.encode("utf-8", errors="replace"), digest_size=64).digest()
    values: list[float] = []
    counter = 0
    while len(values) < dims:
        block = hashlib.blake2b(digest + counter.to_bytes(2, "big"), digest_size=32).digest()
        values.extend((byte - 127.5) / 127.5 for byte in block)
        counter += 1
    values = values[:dims]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [round(v / norm, 6) for v in values]


def cosine(vec_a: list[float], vec_b: list[float]) -> float:
    """Return cosine resonance between two vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _is_probably_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\0" in sample


def classify_file(path: Path) -> str:
    """Classify a repository file into an Aura navigation role."""
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".py":
        return "python_module"
    if suffix in {".rs", ".c", ".cpp"}:
        return "native_accelerator"
    if suffix in {".md", ".tex", ".pdf", ".docx"}:
        return "knowledge_artifact"
    if suffix in {".json", ".toml", ".yml", ".yaml", ".lexc"}:
        return "schema_or_lexicon"
    if suffix == ".sh" or name.startswith("setup") or name.startswith("build"):
        return "operator_script"
    if suffix in {".html", ".css", ".js"}:
        return "interface_surface"
    if suffix in BINARY_SUFFIXES:
        return "binary_artifact"
    return "support_file"


def _python_symbol_records(text: str, rel_path: str = "") -> list[SymbolRecord]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    records: list[SymbolRecord] = []

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        if len(records) >= MAX_SYMBOLS_PER_FILE:
            return
        for child in ast.iter_child_nodes(node):
            child_scope = scope
            if isinstance(child, ast.ClassDef):
                signature = _symbol_signature(child)
                name = ".".join(scope + (child.name,)) if scope else child.name
                records.append(SymbolRecord(
                    name=name,
                    kind="class",
                    line=int(getattr(child, "lineno", 1) or 1),
                    end_line=int(getattr(child, "end_lineno", getattr(child, "lineno", 1)) or 1),
                    semantic_id=_semantic_id(rel_path, "class", name, signature),
                    signature_hash=hashlib.blake2b(signature.encode("utf-8"), digest_size=8).hexdigest(),
                ))
                child_scope = scope + (child.name,)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signature = _symbol_signature(child)
                kind = "method" if scope else "function"
                name = ".".join(scope + (child.name,)) if scope else child.name
                records.append(SymbolRecord(
                    name=name,
                    kind=kind,
                    line=int(getattr(child, "lineno", 1) or 1),
                    end_line=int(getattr(child, "end_lineno", getattr(child, "lineno", 1)) or 1),
                    semantic_id=_semantic_id(rel_path, kind, name, signature),
                    signature_hash=hashlib.blake2b(signature.encode("utf-8"), digest_size=8).hexdigest(),
                ))
                child_scope = scope + (child.name,)
            visit(child, child_scope)

    visit(tree, ())
    return records[:MAX_SYMBOLS_PER_FILE]


def _iter_repo_files(root: Path, skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS) -> list[Path]:
    files: list[Path] = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in skip_dirs and not name.endswith(".egg-info")]
        base_path = Path(base)
        for name in names:
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if rel in GENERATED_MAP_FILES or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            files.append(path)
    return sorted(files)


def _command_mentions(text: str) -> list[str]:
    """Extract executable CLI lines and Aura bang-command tokens deterministically."""
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\s*(python(?:3)?\s+-m\s+[A-Za-z0-9_\.]+|python(?:3)?\s+[A-Za-z0-9_./-]+\.py[^\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    for match in re.finditer(r"(?<!\w)![A-Za-z_][\w-]*", text):
        command = match.group(0)
        if command not in commands:
            commands.append(command)
    return commands[:20]


def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
    """Return stable 1-based source lines for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        if command.startswith("!"):
            hits = [
                index
                for index, line in enumerate(lines, start=1)
                if command in line
            ]
        else:
            hits = [
                index
                for index, line in enumerate(lines, start=1)
                if " ".join(line.strip().split()).startswith(needle)
            ]
        if hits:
            locations[command] = hits[:8]
    return locations


def load_or_compile_topology(
    root: Path,
    *,
    topology_path: Path | None = None,
    refresh: bool = False,
) -> tuple[dict[str, Any], str]:
    target = topology_path or DEFAULT_TOPOLOGY_PATH
    absolute = target if target.is_absolute() else root / target
    if absolute.exists() and not refresh:
        try:
            return json.loads(absolute.read_text(encoding="utf-8")), "existing"
        except (OSError, json.JSONDecodeError):
            pass

    # The deep compiler currently binds its scan root and output paths to the
    # process working directory. Run it from the requested repository root, then
    # restore the caller's cwd so library use remains side-effect bounded.
    previous_cwd = Path.cwd()
    try:
        os.chdir(root)
        topology = compile_topology_map(deep=True)
    finally:
        os.chdir(previous_cwd)

    generated_by = str((topology.get("meta") or {}).get("generated_by") or "")
    source = "compiled_deep_topology" if generated_by == "aura_topology_manager" else "compiled_standard_topology"
    return topology, source

def _node_file(node_id: str, node: dict[str, Any]) -> str:
    return str(node.get("file") or node_id.split("::", 1)[0])


def _topology_file_index(topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    per_file: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "node_count": 0,
        "edge_count": 0,
        "degree": 0,
        "out_edges": 0,
        "in_edges": 0,
        "edge_kinds": Counter(),
        "kinds": Counter(),
        "symbols": [],
        "neighbor_files": set(),
    })

    raw_nodes = topology.get("nodes", {})
    if isinstance(raw_nodes, dict):
        node_items = raw_nodes.items()
    elif isinstance(raw_nodes, list):
        node_items = (
            (str(node.get("id") or f"node_{index}"), node)
            for index, node in enumerate(raw_nodes)
            if isinstance(node, dict)
        )
    else:
        node_items = []

    node_to_file: dict[str, str] = {}
    for node_id, node in node_items:
        if not isinstance(node, dict):
            continue
        file_path = _node_file(str(node_id), node)
        if not file_path:
            continue
        node_to_file[str(node_id)] = file_path
        slot = per_file[file_path]
        slot["node_count"] += 1
        slot["kinds"][str(node.get("kind", "unknown"))] += 1
        symbol = str(node.get("symbol") or node.get("label") or "")
        if symbol and symbol != "global_scope" and len(slot["symbols"]) < 12 and symbol not in slot["symbols"]:
            slot["symbols"].append(symbol)

    for edge in topology.get("edges", []) or []:
        if not isinstance(edge, dict):
            continue
        source_id = str(edge.get("source") or edge.get("from") or "")
        target_id = str(edge.get("target") or edge.get("to") or "")
        source_file = node_to_file.get(source_id)
        target_file = node_to_file.get(target_id)
        edge_kind = str(edge.get("kind") or edge.get("type") or "unknown")
        if source_file:
            slot = per_file[source_file]
            slot["out_edges"] += 1
            slot["edge_count"] += 1
            slot["degree"] += 1
            slot["edge_kinds"][edge_kind] += 1
            if target_file and target_file != source_file:
                slot["neighbor_files"].add(target_file)
        if target_file:
            slot = per_file[target_file]
            slot["in_edges"] += 1
            slot["edge_count"] += 1
            slot["degree"] += 1
            slot["edge_kinds"][edge_kind] += 1
            if source_file and source_file != target_file:
                slot["neighbor_files"].add(source_file)

    out: dict[str, dict[str, Any]] = {}
    for file_path, payload in per_file.items():
        out[file_path] = {
            "node_count": int(payload["node_count"]),
            "edge_count": int(payload["edge_count"]),
            "degree": int(payload["degree"]),
            "symbols": list(payload["symbols"]),
            "neighbor_files": sorted(payload["neighbor_files"]),
            "edge_kinds": dict(sorted(payload["edge_kinds"].items())),
            # Compatibility fields consumed by the navigation ranking layer.
            "nodes": int(payload["node_count"]),
            "out_edges": int(payload["out_edges"]),
            "in_edges": int(payload["in_edges"]),
            "kinds": dict(sorted(payload["kinds"].items())),
        }
    return out

def scan_repository(root: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for path in _iter_repo_files(root):
        cards.append(_scan_file(root, path))
    return cards


def _scan_file(root: Path, path: Path) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    try:
        raw = path.read_bytes()
    except OSError:
        raw = b""
    digest8 = hashlib.blake2b(raw, digest_size=8).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    is_binary = _is_probably_binary(path)
    symbols = _python_symbol_records(text, rel) if path.suffix.lower() == ".py" and not is_binary else []
    commands = _command_mentions(text) if not is_binary else []
    master_key = parse_master_key_header(text) if not is_binary else {}
    return {
        "path": rel,
        "role": classify_file(path),
        "bytes": len(raw),
        "lines": text.count("\n") + (1 if text else 0),
        "tokens_est": estimate_tokens(text) if not is_binary else max(1, len(raw) // 4),
        "binary": is_binary,
        "symbols": [record.__dict__ for record in symbols],
        "commands": commands,
        "command_lines": _command_locations(text, commands) if commands else {},
        "master_key": master_key,
        "digest8": digest8,
        "vector": stable_unit_vector(f"{rel}\n{text[:12000]}") if not is_binary else [],
    }


def _coverage_report(cards: list[dict[str, Any]], topology: dict[str, Any] | None) -> dict[str, Any]:
    source_paths = {str(card.get("path")) for card in cards}
    missing_source_paths: list[str] = []
    unindexed_topology_files: list[str] = []
    if topology:
        topology_files = set(_topology_file_index(topology))
        python_sources = {path for path in source_paths if path.endswith(".py")}
        missing_source_paths = sorted(python_sources - topology_files)
        unindexed_topology_files = sorted(topology_files - source_paths)
    return {
        "repo_file_count": len(cards),
        "source_paths_without_topology": missing_source_paths[:100],
        "topology_paths_without_source_cards": unindexed_topology_files[:100],
        "coverage_complete_for_repo_scan": True,
    }


def _navigation_rings(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role_counts = Counter(str(card.get("role", "support_file")) for card in cards)
    total_bytes = sum(int(card.get("bytes", 0)) for card in cards)
    total_tokens = sum(int(card.get("tokens_est", 0)) for card in cards)
    return [
        {
            "ring": "repo",
            "files": len(cards),
            "bytes": total_bytes,
            "tokens_est": total_tokens,
            "roles": dict(sorted(role_counts.items())),
        },
        {
            "ring": "interfaces",
            "paths": [card["path"] for card in cards if card.get("role") == "interface_surface"][:200],
        },
        {
            "ring": "knowledge",
            "paths": [card["path"] for card in cards if card.get("role") == "knowledge_artifact"][:200],
        },
        {
            "ring": "code",
            "paths": [card["path"] for card in cards if card.get("role") in {"python_module", "native_accelerator"}][:400],
        },
    ]


def _symbol_index(cards: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        for symbol in card.get("symbols", []):
            if not isinstance(symbol, dict):
                continue
            index[str(symbol.get("name", ""))].append({
                "file": card.get("path"),
                "kind": symbol.get("kind"),
                "line": symbol.get("line"),
                "end_line": symbol.get("end_line"),
                "semantic_id": symbol.get("semantic_id"),
                "signature_hash": symbol.get("signature_hash"),
            })
    return dict(index)


def _records_from_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for card in cards:
        card_path = str(card.get("path") or "")
        card_digest = str(card.get("digest8") or "")
        for symbol in card.get("symbols", []):
            if not isinstance(symbol, dict):
                continue
            records.append({
                "semantic_id": str(symbol.get("semantic_id") or ""),
                "name": str(symbol.get("name") or ""),
                "kind": str(symbol.get("kind") or ""),
                "file": card_path,
                "line": int(symbol.get("line") or 1),
                "end_line": int(symbol.get("end_line") or symbol.get("line") or 1),
                "signature_hash": str(symbol.get("signature_hash") or ""),
                "file_digest8": card_digest,
            })
    return sorted(records, key=lambda item: (item["file"], item["semantic_id"]))


def _incremental_record_fingerprint(records: list[dict[str, Any]]) -> str:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def refresh_index_for_paths(
    payload: dict[str, Any],
    root: Path,
    changed_paths: list[str | Path],
    *,
    topology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Refresh changed/deleted file branches without rebuilding unrelated file cards."""
    cards = [dict(card) for card in payload.get("files", []) if isinstance(card, dict)]
    card_by_path = {str(card.get("path") or ""): card for card in cards if card.get("path")}
    changed_rel_paths: list[str] = []
    for raw_path in changed_paths:
        candidate = Path(raw_path)
        absolute = candidate if candidate.is_absolute() else root / candidate
        try:
            rel = absolute.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        if rel in GENERATED_MAP_FILES:
            continue
        changed_rel_paths.append(rel)
        if not absolute.exists() or not absolute.is_file() or absolute.suffix.lower() not in TEXT_SUFFIXES or _skip_part(absolute, root):
            card_by_path.pop(rel, None)
            continue
        card_by_path[rel] = _scan_file(root, absolute)
    refreshed_cards = sorted(card_by_path.values(), key=lambda card: str(card.get("path") or ""))
    topology_index = _topology_file_index(topology) if topology else {}
    if topology_index:
        for card in refreshed_cards:
            card["topology"] = topology_index.get(str(card.get("path") or ""), {})
    refreshed = dict(payload)
    refreshed["generated_at_unix"] = int(time.time())
    refreshed["coverage"] = _coverage_report(refreshed_cards, topology)
    refreshed["rings"] = _navigation_rings(refreshed_cards)
    refreshed["symbol_index"] = _symbol_index(refreshed_cards)
    refreshed["command_index"] = _command_index(refreshed_cards)
    refreshed["top_hubs"] = _top_hubs(refreshed_cards)
    refreshed["files"] = _compact_file_cards(refreshed_cards)
    records = _records_from_cards(refreshed_cards)
    refreshed["incremental_refresh"] = {
        "changed_paths": sorted(set(changed_rel_paths)),
        "records": records,
        "record_fingerprint": _incremental_record_fingerprint(records),
    }
    refreshed["summary"] = {
        "file_count": len(refreshed_cards),
        "total_bytes": sum(int(card.get("bytes", 0)) for card in refreshed_cards),
        "text_tokens_est": sum(int(card.get("tokens_est", 0)) for card in refreshed_cards),
        "role_counts": dict(sorted(Counter(str(card.get("role", "support_file")) for card in refreshed_cards).items())),
        "topology_nodes": len((topology or {}).get("nodes", {})),
        "topology_edges": len((topology or {}).get("edges", [])),
        "topology_source": str(payload.get("summary", {}).get("topology_source", "incremental")),
        "elapsed_ms": round(float(payload.get("summary", {}).get("elapsed_ms", 0.0)), 2),
    }
    refreshed["incremental_refresh"]["payload_hash"] = _codemap_payload_hash(refreshed)
    return refreshed


def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map commands to exact file:line source locators when available."""
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        path = str(card.get("path") or "")
        command_lines = card.get("command_lines", {}) or {}
        for command in card.get("commands", []):
            lines = command_lines.get(command, []) if isinstance(command_lines, dict) else []
            locators = [f"{path}:{int(line)}" for line in lines] if lines else [path]
            for locator in locators:
                if locator and locator not in out[command]:
                    out[command].append(locator)
    return {command: locations for command, locations in sorted(out.items())}


def _top_hubs(cards: list[dict[str, Any]], *, limit: int = 100) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for card in cards:
        topo = card.get("topology", {}) or {}
        score = float(topo.get("nodes", 0)) + float(topo.get("out_edges", 0)) + float(topo.get("in_edges", 0))
        if score <= 0:
            continue
        scored.append((score, {
            "path": card["path"],
            "score": score,
            "nodes": topo.get("nodes", 0),
            "out_edges": topo.get("out_edges", 0),
            "in_edges": topo.get("in_edges", 0),
            "symbols": topo.get("symbols", []),
        }))
    scored.sort(key=lambda item: (-item[0], item[1]["path"]))
    return [item[1] for item in scored[:limit]]


def _compact_file_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist enough source metadata for lossless incremental CODEMAP refreshes."""
    compact: list[dict[str, Any]] = []
    for card in cards:
        symbols = [dict(symbol) for symbol in card.get("symbols", []) if isinstance(symbol, dict)]
        compact.append({
            "path": card["path"],
            "role": card["role"],
            "bytes": card["bytes"],
            "lines": card["lines"],
            "tokens_est": card["tokens_est"],
            "binary": bool(card.get("binary", False)),
            "symbol_count": len(symbols),
            "symbols": symbols,
            "commands": card.get("commands", []),
            "command_lines": card.get("command_lines", {}),
            "topology": card.get("topology", {}),
            "digest8": card.get("digest8"),
            "vector": card.get("vector", []),
        })
    return compact


def _attach_topology(cards: list[dict[str, Any]], topology_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for card in cards:
        card["topology"] = topology_index.get(card["path"], {})
    return cards


def build_navigation_system(
    root: Path,
    *,
    include_topology: bool = True,
    topology_path: Path | None = None,
    refresh_topology: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    cards = scan_repository(root)
    topology: dict[str, Any] | None = None
    topology_source = "disabled"
    topology_index: dict[str, dict[str, Any]] = {}
    if include_topology:
        topology, topology_source = load_or_compile_topology(root, topology_path=topology_path, refresh=refresh_topology)
        topology_index = _topology_file_index(topology)
        cards = _attach_topology(cards, topology_index)
    payload = {
        "status": "AURA_CODEMAP_ACTIVE",
        "generated_by": "aura_codebase_navigator",
        "generated_at_unix": int(time.time()),
        "root": root.as_posix(),
        "intent_packet": "[OP:NAVIGATE][DOMAIN:TOPOLOGY][TARGET:CODEMAP][ENV:PYTHON][CONSTRAINT:TOKEN_SPARING]",
        "coverage": _coverage_report(cards, topology),
        "rings": _navigation_rings(cards),
        "symbol_index": _symbol_index(cards),
        "command_index": _command_index(cards),
        "top_hubs": _top_hubs(cards),
        "files": _compact_file_cards(cards),
        "topology": {
            "source": topology_source,
            "file_index": topology_index,
            "meta": dict((topology or {}).get("meta") or {}),
            "diagnostics": dict((topology or {}).get("diagnostics") or {}),
        },
        "summary": {
            "file_count": len(cards),
            "total_bytes": sum(int(card.get("bytes", 0)) for card in cards),
            "text_tokens_est": sum(int(card.get("tokens_est", 0)) for card in cards),
            "role_counts": dict(sorted(Counter(str(card.get("role", "support_file")) for card in cards).items())),
            "topology_nodes": len((topology or {}).get("nodes", {})),
            "topology_edges": len((topology or {}).get("edges", [])),
            "topology_source": topology_source,
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 2),
        },
        "navigation_protocol": [
            "Read .aura/CODEMAP.md first.",
            "Use .aura/CODEMAP.json for exact file/symbol/command references.",
            "Navigate repository -> role -> file -> symbol -> exact source region.",
            "Do not infer repository-wide behavior from a single file or paper.",
            "Treat topology and vectors as navigation aids only; exact source and tests remain authority.",
        ],
    }
    return payload


def search_index(index: dict[str, Any], query: str, *, top_n: int = 12) -> list[dict[str, Any]]:
    query_vector = stable_unit_vector(query)
    query_terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_]+", query) if len(term) >= 2}
    ranked: list[tuple[float, dict[str, Any]]] = []
    for card in index.get("files", []):
        path = str(card.get("path", ""))
        role = str(card.get("role", ""))
        symbols = " ".join(str(symbol) for symbol in (card.get("topology", {}) or {}).get("symbols", []))
        commands = " ".join(str(command) for command in card.get("commands", []))
        lexical_blob = f"{path} {role} {symbols} {commands}".lower()
        lexical_hits = sum(1 for term in query_terms if term in lexical_blob)
        semantic = cosine(query_vector, list(card.get("vector", [])))
        topology = card.get("topology", {}) or {}
        graph_bonus = math.log1p(float(topology.get("nodes", 0)) + float(topology.get("out_edges", 0)) + float(topology.get("in_edges", 0)))
        score = lexical_hits * 3.0 + semantic + graph_bonus * 0.05
        if lexical_hits > 0 or semantic > 0.15:
            ranked.append((score, card))
    ranked.sort(key=lambda item: (-item[0], item[1].get("path", "")))
    return [{"score": round(score, 4), **card} for score, card in ranked[:top_n]]


def write_navigation_artifacts(index: dict[str, Any], index_path: Path, markdown_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=False), encoding="utf-8")
    summary = index.get("summary", {})
    lines = [
        "# Aura CODEMAP",
        "",
        "Generated by `aura_codebase_navigator.py`.",
        "",
        "Canonical machine index: `.aura/CODEMAP.json`.",
        "",
        "Read this file before opening large repository documents or source trees. It is a navigation surface only; exact source and tests remain authority.",
        "",
        f"Intent packet: `{index.get('intent_packet', '')}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- **{key}**: {value}")
    lines.extend(["", "## Coverage", "", "```json", json.dumps(index.get("coverage", {}), indent=2), "```", "", "## Navigation rings", ""])
    for ring in index.get("rings", []):
        lines.extend([f"### {ring.get('ring', 'unknown')}", "", "```json", json.dumps(ring, indent=2), "```", ""])
    lines.extend(["## Highest-connectivity source files", ""])
    for hub in index.get("top_hubs", [])[:40]:
        lines.append(f"- `{hub['path']}` — score `{hub['score']}`; nodes `{hub['nodes']}`; out `{hub['out_edges']}`; in `{hub['in_edges']}`")
    lines.extend(["", "## Example usage", "", "```bash", "python aura_codebase_navigator.py", "python aura_codebase_navigator.py --search \"Council workspace intent\" --top 12", "python aura_codebase_navigator.py --search \"construction renderer\" --no-topology", "```", ""])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _codemap_payload_hash(payload: dict[str, Any]) -> str:
    """Hash logical navigation content, excluding generation/refresh bookkeeping."""
    canonical = json.loads(json.dumps(payload))
    canonical.pop("generated_at_unix", None)
    canonical.pop("incremental_refresh", None)
    summary = canonical.get("summary")
    if isinstance(summary, dict):
        summary.pop("elapsed_ms", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.blake2b(raw, digest_size=16).hexdigest()


def refresh_codemap_for_paths(
    changed_paths: list[str | Path],
    *,
    root: Path | None = None,
    index_path: Path = DEFAULT_INDEX_PATH,
    markdown_path: Path = DEFAULT_MARKDOWN_PATH,
    include_topology: bool = True,
    topology_path: Path | None = None,
    refresh_topology: bool = False,
) -> dict[str, Any]:
    repo_root = (root or Path(__file__).resolve().parent).resolve()
    absolute_index = index_path if index_path.is_absolute() else repo_root / index_path
    absolute_markdown = markdown_path if markdown_path.is_absolute() else repo_root / markdown_path
    if not absolute_index.exists():
        payload = build_navigation_system(
            repo_root,
            include_topology=include_topology,
            topology_path=topology_path,
            refresh_topology=refresh_topology,
        )
        write_navigation_artifacts(payload, absolute_index, absolute_markdown)
        return payload

    existing_payload = _load_json(absolute_index)
    topology = None
    if include_topology:
        topology, _ = load_or_compile_topology(
            repo_root,
            topology_path=topology_path,
            refresh=refresh_topology,
        )
    refreshed = refresh_index_for_paths(existing_payload, repo_root, changed_paths, topology=topology)
    if _codemap_payload_hash(refreshed) == _codemap_payload_hash(existing_payload):
        return existing_payload
    write_navigation_artifacts(refreshed, absolute_index, absolute_markdown)
    return refreshed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a token-sparing repository-wide Aura CODEMAP.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--markdown", default=str(DEFAULT_MARKDOWN_PATH))
    parser.add_argument("--topology", default=str(DEFAULT_TOPOLOGY_PATH))
    parser.add_argument("--refresh-topology", action="store_true")
    parser.add_argument("--no-topology", action="store_true")
    parser.add_argument("--search", default="")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--refresh", nargs="*", default=None, help="Incrementally refresh only these changed/deleted repository paths")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = root / index_path
    markdown_path = Path(args.markdown)
    if not markdown_path.is_absolute():
        markdown_path = root / markdown_path
    topology_path = Path(args.topology)
    if args.refresh is not None and index_path.exists():
        index = _load_json(index_path)
        topology = None
        topology_source = "disabled"
        if not args.no_topology:
            topology, topology_source = load_or_compile_topology(root, topology_path=topology_path, refresh=args.refresh_topology)
        index = refresh_index_for_paths(index, root, args.refresh, topology=topology)
        if isinstance(index.get("summary"), dict):
            index["summary"]["topology_source"] = topology_source
    else:
        index = build_navigation_system(
            root,
            include_topology=not args.no_topology,
            topology_path=topology_path,
            refresh_topology=args.refresh_topology,
        )
    write_navigation_artifacts(index, index_path, markdown_path)
    if args.search:
        for result in search_index(index, args.search, top_n=max(1, args.top)):
            topology = result.get("topology", {}) or {}
            print(f"{result['score']:>7}  {result['path']}  role={result['role']} nodes={topology.get('nodes', 0)}")
    else:
        print(f"[+] Wrote {index_path}")
        print(f"[+] Wrote {markdown_path}")
        print(f"[+] Indexed {index['summary']['file_count']} files across the repository")
        print(f"[+] Estimated text tokens: {index['summary']['text_tokens_est']}")
        print(f"[+] Deep topology nodes: {index['summary']['topology_nodes']}  edges: {index['summary']['topology_edges']}")
    return 0


def _skip_part(path: Path, root: Path) -> bool:
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except (OSError, ValueError):
        return True
    return any(part in DEFAULT_SKIP_DIRS or part.endswith(".egg-info") for part in parts)


if __name__ == "__main__":
    raise SystemExit(main())

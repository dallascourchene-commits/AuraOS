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
TEXT_SUFFIXES = frozenset({"", ".c", ".cpp", ".css", ".html", ".json", ".lexc", ".md", ".py", ".rs", ".sh", ".tex", ".toml", ".txt", ".yml", ".yaml"})
DEFAULT_INDEX_PATH = Path(".aura/CODEMAP.json")
DEFAULT_MARKDOWN_PATH = Path(".aura/CODEMAP.md")
DEFAULT_TOPOLOGY_PATH = Path("Aura_Memory/live_topology_ast.json")
GENERATED_MAP_FILES = {DEFAULT_INDEX_PATH.as_posix(), DEFAULT_MARKDOWN_PATH.as_posix()}
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
    if suffix in {".html", ".css"}:
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

    # Traverse with parent context to distinguish methods from module-level functions
    def _visit_node(node: ast.AST, parent_class: str = "") -> None:
        if isinstance(node, ast.ClassDef):
            signature = _symbol_signature(node)
            qualified_name = f"{parent_class}.{node.name}" if parent_class else node.name
            records.append(SymbolRecord(
                node.name,
                "class",
                node.lineno,
                getattr(node, "end_lineno", node.lineno) or node.lineno,
                _semantic_id(rel_path, "class", qualified_name, signature),
                hashlib.blake2b(signature.encode("utf-8", errors="replace"), digest_size=8).hexdigest(),
            ))
            # Visit class body with class context
            for child in node.body:
                _visit_node(child, parent_class=node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "method" if parent_class else ("async_function" if isinstance(node, ast.AsyncFunctionDef) else "function")
            signature = _symbol_signature(node)
            qualified_name = f"{parent_class}.{node.name}" if parent_class else node.name
            records.append(SymbolRecord(
                node.name,
                kind,
                node.lineno,
                getattr(node, "end_lineno", node.lineno) or node.lineno,
                _semantic_id(rel_path, kind, qualified_name, signature),
                hashlib.blake2b(signature.encode("utf-8", errors="replace"), digest_size=8).hexdigest(),
            ))
        else:
            # Visit other nodes without changing parent context
            for child in ast.iter_child_nodes(node):
                _visit_node(child, parent_class)

    for node in tree.body:
        _visit_node(node)

    return sorted(records, key=lambda item: (item.line, item.name))


def _iter_repo_files(root: Path, skip_dirs: frozenset[str]) -> list[Path]:
    paths: list[Path] = []

    def _skip_part(name: str) -> bool:
        return name in skip_dirs or any(
            pattern.startswith("*") and name.endswith(pattern[1:])
            for pattern in skip_dirs
        )

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not _skip_part(d))
        base = Path(dirpath)
        for filename in sorted(filenames):
            candidate = base / filename
            try:
                rel = candidate.relative_to(root).as_posix()
            except ValueError:
                rel = candidate.as_posix()
            # Skip CODEMAP artifacts, runtime databases, and files in excluded dirs
            if (rel in GENERATED_MAP_FILES or
                candidate.suffix == ".sqlite3" or
                any(_skip_part(part) for part in candidate.relative_to(root).parts)):
                continue
            paths.append(candidate)
    return paths


def _command_mentions(text: str) -> list[str]:
    return sorted(_command_locations(text))


def _command_locations(text: str) -> dict[str, list[int]]:
    locations: dict[str, set[int]] = defaultdict(set)
    for lineno, line in enumerate(text.splitlines(), start=1):
        for cmd in re.findall(r"![A-Za-z][A-Za-z0-9_:-]*", line):
            locations[cmd.rstrip(":,.;)]}")].add(lineno)
        for cmd in re.findall(r"\.startswith\([\"'](![^\"']+)[\"']\)", line):
            locations[cmd.strip().split()[0]].add(lineno)
    return {cmd: sorted(lines) for cmd, lines in sorted(locations.items()) if len(cmd) > 1}


def load_or_compile_topology(root: Path, *, include_topology: bool = True, topology_path: Path = DEFAULT_TOPOLOGY_PATH, refresh: bool = True) -> dict[str, Any]:
    """Load Aura's live !topology JSON, refreshing it first when requested.

    The CODEMAP should not treat topology as an unrelated side artifact.  By
    default it runs the same deep topology compiler used by `!topology deep`,
    which writes Aura_Memory/live_topology_ast.json, then reads that JSON back
    into the codemap pipeline.  If the compiler fails, it falls back to an
    existing topology JSON so stale files do not break map generation.
    """
    if not include_topology:
        return {"nodes": [], "edges": [], "diagnostics": {}, "meta": {"source": "disabled"}}

    topology_abs = topology_path if topology_path.is_absolute() else root / topology_path
    if refresh:
        cwd = Path.cwd()
        try:
            os.chdir(root)
            compiled = compile_topology_map(deep=True)
            if compiled:
                return {**compiled, "codemap_source": "compiled_deep_topology"}
        except Exception as exc:
            fallback = {"error": str(exc)}
        finally:
            os.chdir(cwd)
    else:
        fallback = {}

    if topology_abs.exists():
        payload = json.loads(topology_abs.read_text(encoding="utf-8"))
        payload.setdefault("meta", {})
        payload["codemap_source"] = "existing_topology_json"
        return payload

    return {"nodes": [], "edges": [], "diagnostics": fallback, "meta": {"source": "missing_topology_json"}}


def _node_file(node: dict[str, Any]) -> str:
    file_value = str(node.get("file") or "")
    if file_value:
        return Path(file_value).name
    node_id = str(node.get("id") or "")
    return Path(node_id.split("::", 1)[0]).name if "::" in node_id else ""


def _topology_file_index(topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Summarize topology graph data by source file for compact CODEMAP cards."""
    per_file: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "node_count": 0,
        "edge_count": 0,
        "degree": 0,
        "symbols": [],
        "neighbor_files": set(),
        "edge_kinds": Counter(),
    })
    node_to_file: dict[str, str] = {}
    for node in topology.get("nodes", []):
        file_name = _node_file(node)
        node_id = str(node.get("id") or "")
        if not file_name:
            continue
        node_to_file[node_id] = file_name
        bucket = per_file[file_name]
        bucket["node_count"] += 1
        label = str(node.get("label") or node_id.rsplit("::", 1)[-1])
        if label and label not in bucket["symbols"] and label != "global_scope":
            bucket["symbols"].append(label)

    for edge in topology.get("edges", []):
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        source_file = node_to_file.get(source) or (Path(source.split("::", 1)[0]).name if "::" in source else "")
        target_file = node_to_file.get(target) or (Path(target.split("::", 1)[0]).name if "::" in target else "")
        kind = str(edge.get("kind") or edge.get("type") or "edge")
        for file_name, other in ((source_file, target_file), (target_file, source_file)):
            if not file_name:
                continue
            bucket = per_file[file_name]
            bucket["edge_count"] += 1
            bucket["degree"] += 1
            bucket["edge_kinds"][kind] += 1
            if other and other != file_name:
                bucket["neighbor_files"].add(other)

    compact: dict[str, dict[str, Any]] = {}
    ranked = sorted(per_file.items(), key=lambda item: (item[1]["degree"], item[1]["node_count"], item[0]), reverse=True)
    for rank, (file_name, bucket) in enumerate(ranked, start=1):
        compact[file_name] = {
            "hub_rank": rank,
            "node_count": bucket["node_count"],
            "edge_count": bucket["edge_count"],
            "degree": bucket["degree"],
            "symbols": sorted(bucket["symbols"])[:20],
            "neighbor_files": sorted(bucket["neighbor_files"])[:20],
            "edge_kinds": dict(bucket["edge_kinds"].most_common(8)),
        }
    return compact


def scan_repository(root: Path, skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS) -> list[dict[str, Any]]:
    """Scan non-skipped files once and return compact file cards for map use."""
    records: list[dict[str, Any]] = []
    for path in _iter_repo_files(root, skip_dirs):
        records.append(_scan_file(root, path))
    return records


def _scan_file(root: Path, path: Path) -> dict[str, Any]:
    """Parse one file into the same compact card shape used by full scans."""
    rel = path.relative_to(root).as_posix()
    stat = path.stat()
    is_binary = _is_probably_binary(path)
    text = ""
    if not is_binary and path.suffix.lower() in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
    digest = hashlib.blake2b(path.read_bytes(), digest_size=8).hexdigest()
    header = parse_master_key_header(text) if text else {}
    symbols = _python_symbol_records(text, rel) if path.suffix.lower() == ".py" and text else []
    symbol_names = [symbol.name for symbol in symbols[:MAX_SYMBOLS_PER_FILE]]
    command_lines = _command_locations(text) if text else {}
    commands = sorted(command_lines)
    role = classify_file(path)
    seed = "|".join([rel, role, digest, " ".join(symbol_names), " ".join(commands), header.get("FUNCTIONS", "")])
    return {
        "path": rel,
        "role": role,
        "bytes": stat.st_size,
        "lines": text.count("\n") + 1 if text else 0,
        "tokens_est": estimate_tokens(text) if text else 0,
        "digest8": digest,
        "binary": is_binary,
        "header": {k: header[k] for k in ("PWFST_ALIGNMENT", "DIKWP_TIER", "DEPENDENCIES", "FUNCTIONS") if k in header},
        "symbols": [symbol.__dict__ for symbol in symbols[:MAX_SYMBOLS_PER_FILE]],
        "symbol_count": len(symbols),
        "commands": commands,
        "command_lines": command_lines,
        "vector": stable_unit_vector(seed),
    }



def _coverage_report(root: Path, records: list[dict[str, Any]], skip_dirs: frozenset[str]) -> dict[str, Any]:
    included = {rec["path"] for rec in records}
    generated = sorted(path for path in GENERATED_MAP_FILES if (root / path).exists())
    skipped_counts: dict[str, int] = {}
    for dirname in sorted(skip_dirs):
        base = root / dirname
        if base.exists() and base.is_dir():
            skipped_counts[dirname] = sum(1 for item in base.rglob("*") if item.is_file())
    return {
        "included_file_count": len(included),
        "included_policy": "all files under root except skipped runtime/cache dirs and generated CODEMAP outputs",
        "excluded_generated_map_files": generated,
        "skipped_dir_file_counts": skipped_counts,
        "all_included_paths_sorted": sorted(included),
    }

def _navigation_rings(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    rings = {
        "substrate_core": [],
        "cognition_and_memory": [],
        "mesh_and_routing": [],
        "topology_and_navigation": [],
        "security_and_validation": [],
        "interfaces_and_docs": [],
    }
    for rec in records:
        path = rec["path"]
        low = path.lower()
        target = "interfaces_and_docs"
        if "substrate" in low or low in {"gateway.py", "aura_node.py", "aura_core.py"}:
            target = "substrate_core"
        elif any(key in low for key in ("memory", "palace", "cognitive", "dream", "attention", "spectral")):
            target = "cognition_and_memory"
        elif any(key in low for key in ("mesh", "router", "routing", "liquid", "blockchain", "ledger")):
            target = "mesh_and_routing"
        elif any(key in low for key in ("topolog", "scanner", "navigator", "mapper")):
            target = "topology_and_navigation"
        elif any(key in low for key in ("security", "guard", "validation", "shield", "crypto", "heal", "audit")):
            target = "security_and_validation"
        rings[target].append(path)
    return {key: sorted(value) for key, value in rings.items() if value}


def _symbol_index(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        for symbol in rec.get("symbols", []):
            index[symbol["name"]].append({
                "file": rec["path"],
                "kind": symbol["kind"],
                "line": symbol["line"],
                "end_line": symbol["end_line"],
                "semantic_id": symbol.get("semantic_id", ""),
                "signature_hash": symbol.get("signature_hash", ""),
            })
    return dict(sorted(index.items()))


def _records_from_cards(payload: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    """Return mutable file records from a payload that may only contain compact cards."""
    records = [dict(card) for card in payload.get("files", [])]
    by_path = {record["path"]: record for record in records}
    for record in records:
        if "bytes" not in record and root is not None:
            try:
                record["bytes"] = (root / record["path"]).stat().st_size
            except OSError:
                record["bytes"] = 0
        else:
            record.setdefault("bytes", 0)
        record.setdefault("symbols", [])
    for name, hits in payload.get("symbol_index", {}).items():
        for hit in hits:
            record = by_path.get(hit.get("file", ""))
            if record is None:
                continue
            record.setdefault("symbols", []).append({
                "name": name,
                "kind": hit.get("kind", "function"),
                "line": hit.get("line", 0),
                "end_line": hit.get("end_line", hit.get("line", 0)),
                "semantic_id": hit.get("semantic_id", ""),
                "signature_hash": hit.get("signature_hash", ""),
            })
    for record in records:
        record["symbol_count"] = len(record.get("symbols", [])) or record.get("symbol_count", 0)
    return records


def _incremental_record_fingerprint(record: dict[str, Any]) -> dict[str, Any]:
    """Return the branch fields that determine whether a file card changed."""
    symbols = sorted(
        record.get("symbols", []),
        key=lambda item: (
            item.get("name", ""),
            item.get("kind", ""),
            item.get("line", 0),
            item.get("end_line", 0),
        ),
    )
    return {
        "card": _compact_file_cards([record])[0],
        "symbols": symbols,
    }


def refresh_index_for_paths(
    index_path: Path,
    changed_paths: list[Path],
    *,
    root: Path | None = None,
    include_topology: bool = True,
    topology_path: Path = DEFAULT_TOPOLOGY_PATH,
    refresh_topology: bool = False,
    write_index: bool = True,
) -> dict[str, Any]:
    """Closed-loop AST hook: update changed/deleted file branches in an existing map.

    Editors and coding agents can call this immediately after successful writes.
    The touched files are locally reparsed, semantic IDs/signature hashes and line
    ranges are regenerated for those branches, deletions are removed, and Aura's
    topology metadata is re-attached from either the existing topology JSON or a
    fresh deep topology refresh when requested.
    """
    # Early return if no changes to process
    if not changed_paths:
        return _load_json(index_path)

    payload = _load_json(index_path)
    root = (root or Path(payload.get("root", "."))).resolve()
    by_path = {record["path"]: record for record in _records_from_cards(payload, root=root)}
    refreshed: list[str] = []
    removed: list[str] = []

    for changed in changed_paths:
        path = changed if changed.is_absolute() else root / changed
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel in GENERATED_MAP_FILES or any(part in DEFAULT_SKIP_DIRS for part in Path(rel).parts):
            continue
        if path.exists() and path.is_file():
            scanned = _scan_file(root, path)
            existing = by_path.get(rel)
            if existing is None or _incremental_record_fingerprint(existing) != _incremental_record_fingerprint(scanned):
                by_path[rel] = scanned
                refreshed.append(rel)
        elif rel in by_path:
            by_path.pop(rel, None)
            removed.append(rel)

    if not refreshed and not removed:
        return payload

    topology = load_or_compile_topology(root, include_topology=include_topology, topology_path=topology_path, refresh=refresh_topology)
    records = [by_path[path] for path in sorted(by_path)]
    topology_by_file = _attach_topology(records, topology)
    roles = Counter(rec["role"] for rec in records)
    payload["coverage"] = _coverage_report(root, records, DEFAULT_SKIP_DIRS)
    payload["rings"] = _navigation_rings(records)
    payload["hubs"] = _top_hubs(records)
    payload["command_index"] = _command_index(records)
    payload["symbol_index"] = _symbol_index(records)
    payload["files"] = _compact_file_cards(records)
    payload["topology"] = {
        "source": topology.get("codemap_source", "disabled" if not include_topology else "unknown"),
        "diagnostics": topology.get("diagnostics", {}),
        "meta": topology.get("meta", {}),
        "file_index": topology_by_file,
        "top_files_by_degree": sorted(
            [{"file": file_name, **data} for file_name, data in topology_by_file.items()],
            key=lambda item: (item["degree"], item["node_count"], item["file"]),
            reverse=True,
        )[:30],
    }
    payload["summary"].update({
        "file_count": len(records),
        "total_bytes": sum(rec.get("bytes", 0) for rec in records),
        "text_tokens_est": sum(rec.get("tokens_est", 0) for rec in records),
        "role_counts": dict(sorted(roles.items())),
        "topology_nodes": len(topology.get("nodes", [])),
        "topology_edges": len(topology.get("edges", [])),
        "topology_source": topology.get("codemap_source", "disabled" if not include_topology else "unknown"),
        "last_incremental_refresh_unix": int(time.time()),
    })
    payload["last_refresh"] = {
        "mode": "incremental_ast_hook",
        "refreshed_paths": refreshed,
        "removed_paths": removed,
        "changed_path_count": len(refreshed) + len(removed),
        "topology_refreshed": refresh_topology,
    }
    if write_index:
        index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _command_index(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        for command in rec.get("commands", []):
            index[command].append(f"{rec['path']}:{rec.get('command_lines', {}).get(command, [1])[0]}")
    return {command: sorted(paths) for command, paths in sorted(index.items())}


def _top_hubs(records: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    ranked = sorted(records, key=lambda rec: (rec.get("topology", {}).get("degree", 0), rec.get("symbol_count", 0), rec.get("tokens_est", 0)), reverse=True)
    return [{
        "path": rec["path"],
        "role": rec["role"],
        "symbols": rec.get("symbol_count", 0),
        "tokens_est": rec["tokens_est"],
        "topology_degree": rec.get("topology", {}).get("degree", 0),
    } for rec in ranked[:limit]]


def _compact_file_cards(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for rec in records:
        cards.append({
            "path": rec["path"],
            "role": rec["role"],
            "bytes": rec["bytes"],
            "lines": rec["lines"],
            "tokens_est": rec["tokens_est"],
            "symbol_count": rec.get("symbol_count", 0),
            "commands": rec.get("commands", []),
            "command_lines": rec.get("command_lines", {}),
            "topology": rec.get("topology", {}),
            "digest8": rec["digest8"],
            "vector": rec["vector"],
        })
    return cards


def _attach_topology(records: list[dict[str, Any]], topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    topology_by_file = _topology_file_index(topology)
    for rec in records:
        rec["topology"] = topology_by_file.get(Path(rec["path"]).name, {})
    return topology_by_file


def build_navigation_system(root: Path, *, include_topology: bool = True, topology_path: Path = DEFAULT_TOPOLOGY_PATH, refresh_topology: bool = True) -> dict[str, Any]:
    """Build a compact map intended to be read instead of the whole codebase."""
    started = time.time()
    topology = load_or_compile_topology(root, include_topology=include_topology, topology_path=topology_path, refresh=refresh_topology)
    records = scan_repository(root)
    topology_by_file = _attach_topology(records, topology)
    roles = Counter(rec["role"] for rec in records)
    compressor = IntentCompressor()
    payload = {
        "status": "AURA_CODEMAP_ACTIVE",
        "generated_by": "aura_codebase_navigator",
        "generated_at_unix": int(time.time()),
        "root": str(root),
        "intent_packet": compressor.compress(
            "navigate AuraOS from a compact map before reading source files",
            explicit_tags=["OP:NAVIGATE", "DOMAIN:TOPOLOGY", "TARGET:CODEMAP", "ENV:PYTHON", "CONSTRAINT:TOKEN_SPARING"],
        ),
        "coverage": _coverage_report(root, records, DEFAULT_SKIP_DIRS),
        "summary": {
            "file_count": len(records),
            "total_bytes": sum(rec["bytes"] for rec in records),
            "text_tokens_est": sum(rec["tokens_est"] for rec in records),
            "role_counts": dict(sorted(roles.items())),
            "topology_nodes": len(topology.get("nodes", [])),
            "topology_edges": len(topology.get("edges", [])),
            "topology_source": topology.get("codemap_source", "disabled" if not include_topology else "unknown"),
            "elapsed_ms": round((time.time() - started) * 1000, 2),
        },
        "navigation_protocol": [
            "Read .aura/CODEMAP.md first.",
            "Use command_index for bang commands before opening the REPL monolith.",
            "Use symbol_index semantic_id/signature_hash entries first, then current line ranges.",
            "Open only the top query hits plus their topology.neighbor_files.",
            "After any successful file write, run --refresh on touched paths instead of rebuilding the whole map.",
        ],
        "rings": _navigation_rings(records),
        "hubs": _top_hubs(records),
        "command_index": _command_index(records),
        "symbol_index": _symbol_index(records),
        "files": _compact_file_cards(records),
        "topology": {
            "source": topology.get("codemap_source", "disabled" if not include_topology else "unknown"),
            "diagnostics": topology.get("diagnostics", {}),
            "meta": topology.get("meta", {}),
            "file_index": topology_by_file,
            "top_files_by_degree": sorted(
                [{"file": file_name, **data} for file_name, data in topology_by_file.items()],
                key=lambda item: (item["degree"], item["node_count"], item["file"]),
                reverse=True,
            )[:30],
        },
    }
    return payload


def search_index(payload: dict[str, Any], query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Rank compact file cards from an existing map without scanning source files."""
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_!:-]+", query)}
    qvec = stable_unit_vector(query)
    symbol_hits = payload.get("symbol_index", {})
    command_hits = payload.get("command_index", {})
    target_files: Counter[str] = Counter()
    for term in terms:
        if term in command_hits:
            target_files.update({str(path).split(":", 1)[0]: 12 for path in command_hits[term]})
        for symbol, hits in symbol_hits.items():
            if term == symbol.lower():
                target_files.update({hit["file"]: 10 for hit in hits})
    ranked: list[dict[str, Any]] = []
    for card in payload.get("files", []):
        topology = card.get("topology", {})
        haystack = " ".join([
            card["path"],
            card["role"],
            " ".join(card.get("commands", [])),
            " ".join(topology.get("neighbor_files", [])),
            " ".join(topology.get("edge_kinds", {}).keys()),
        ]).lower()
        lexical = sum(1 for term in terms if term in haystack)
        path_exact = sum(3 for term in terms if term and term in card["path"].lower())
        topology_boost = min(3, topology.get("degree", 0) / 100) if lexical else 0
        role_boost = 2 if card["role"] == "python_module" and target_files[card["path"]] else 0
        test_penalty = 4 if card["path"].startswith("test_") and target_files[card["path"]] else 0
        score = target_files[card["path"]] + role_boost + lexical + path_exact + topology_boost + cosine(qvec, card.get("vector", [])) - test_penalty
        if score > 0:
            result = {"score": round(score, 4), **{k: v for k, v in card.items() if k not in {"vector", "command_lines"}}}
            matched_commands = {term for term in terms if term in card.get("command_lines", {})}
            if matched_commands:
                result.pop("commands", None)
                result["matched_command_lines"] = {cmd: card["command_lines"][cmd] for cmd in sorted(matched_commands)}
            ranked.append(result)
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:limit]


def _atomic_write_text(path: Path, text: str) -> None:
    """Publish a text artifact atomically so concurrent readers never see truncation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_navigation_artifacts(
    payload: dict[str, Any],
    json_path: Path = DEFAULT_INDEX_PATH,
    md_path: Path = DEFAULT_MARKDOWN_PATH,
    *,
    write_json: bool = True,
) -> tuple[Path, Path]:
    """Write compact machine and human maps; do not emit full topology/file payloads in Markdown."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    if write_json:
        _atomic_write_text(json_path, json.dumps(payload, indent=2))
    lines = [
        "# Aura Compact Code Map",
        "",
        f"Status: `{payload['status']}`",
        f"Intent packet: `{payload['intent_packet']}`",
        "",
        "## Navigation Protocol",
        "",
    ]
    lines.extend(f"- {step}" for step in payload["navigation_protocol"])
    lines.extend(["", "## Summary", ""])
    for key, value in payload["summary"].items():
        lines.append(f"- **{key}**: {value}")
    coverage = payload.get("coverage", {})
    lines.extend(["", "## Coverage", ""])
    lines.append(f"- **included_file_count**: {coverage.get('included_file_count', 0)}")
    lines.append(f"- **policy**: {coverage.get('included_policy', '')}")
    if coverage.get("excluded_generated_map_files"):
        lines.append("- **excluded_generated_map_files**: " + ", ".join(f"`{path}`" for path in coverage["excluded_generated_map_files"]))
    if coverage.get("skipped_dir_file_counts"):
        skipped = ", ".join(f"`{name}`={count}" for name, count in coverage["skipped_dir_file_counts"].items())
        lines.append(f"- **skipped_dir_file_counts**: {skipped}")
    lines.extend(["", "## Command Index", ""])
    for command, paths in payload["command_index"].items():
        lines.append(f"- `{command}` -> {', '.join(f'`{path}`' for path in paths[:4])}")
    lines.extend(["", "## Navigation Rings", ""])
    for ring, paths in payload["rings"].items():
        lines.append(f"### {ring}")
        for path in paths[:12]:
            lines.append(f"- `{path}`")
        if len(paths) > 12:
            lines.append(f"- ... {len(paths) - 12} more; query CODEMAP.json for exact file cards")
        lines.append("")
    lines.extend(["## Hubs", ""])
    for hub in payload["hubs"][:12]:
        lines.append(f"- `{hub['path']}` ({hub['role']}): {hub['symbols']} symbols, degree {hub.get('topology_degree', 0)}, ~{hub['tokens_est']} tokens")
    topology = payload.get("topology", {})
    lines.extend(["", "## Topology Integration", ""])
    lines.append(f"- **source**: {topology.get('source', 'unknown')}")
    lines.append(f"- **nodes**: {payload['summary'].get('topology_nodes', 0)}")
    lines.append(f"- **edges**: {payload['summary'].get('topology_edges', 0)}")
    if topology.get("top_files_by_degree"):
        lines.append("- **top_files_by_degree**:")
        for item in topology["top_files_by_degree"][:12]:
            neighbors = ", ".join(f"`{name}`" for name in item.get("neighbor_files", [])[:4])
            lines.append(f"  - `{item['file']}` degree={item['degree']} nodes={item['node_count']} neighbors={neighbors}")
    lines.extend(["", "## High-Value Symbols", ""])
    for symbol in sorted(payload["symbol_index"])[:80]:
        hits = payload["symbol_index"][symbol]
        where = ", ".join(f"`{hit['file']}:{hit['line']}`" for hit in hits[:3])
        lines.append(f"- `{symbol}` -> {where}")
    _atomic_write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _codemap_payload_hash(payload: dict[str, Any]) -> str:
    """Create deterministic hash of codemap payload to detect content changes."""
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def refresh_codemap_for_paths(
    changed_paths: list[str | Path],
    *,
    root: Path | str | None = None,
    index_path: Path = DEFAULT_INDEX_PATH,
    markdown_path: Path = DEFAULT_MARKDOWN_PATH,
    include_topology: bool = True,
    topology_path: Path = DEFAULT_TOPOLOGY_PATH,
    refresh_topology: bool = False,
) -> dict[str, Any] | None:
    """Refresh CODEMAP branches and leave JSON/Markdown untouched on no-op scans."""
    repo_root = Path(root or ".").resolve()
    resolved_index = index_path if index_path.is_absolute() else repo_root / index_path
    resolved_markdown = markdown_path if markdown_path.is_absolute() else repo_root / markdown_path
    if not resolved_index.exists():
        return None
    before_payload = _load_json(resolved_index)
    before_hash = _codemap_payload_hash(before_payload)
    payload = refresh_index_for_paths(
        resolved_index,
        [Path(path) for path in changed_paths],
        root=repo_root,
        include_topology=include_topology,
        topology_path=topology_path,
        refresh_topology=refresh_topology,
        write_index=False,
    )
    after_hash = _codemap_payload_hash(payload)
    if before_hash == after_hash:
        return payload
    write_navigation_artifacts(payload, resolved_index, resolved_markdown)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/query Aura's compact code map.")
    parser.add_argument("--root", default=".", help="Repository root to scan when building")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH), help="Compact JSON map path")
    parser.add_argument("--markdown", default=str(DEFAULT_MARKDOWN_PATH), help="Compact Markdown map path")
    parser.add_argument("--query", default="", help="Query an existing compact map without scanning")
    parser.add_argument("--refresh", nargs="*", default=None, help="Incrementally refresh changed/deleted paths in an existing compact map")
    parser.add_argument("--limit", type=int, default=8, help="Maximum query hits")
    parser.add_argument("--no-topology", action="store_true", help="Skip deep topology scan for a faster codemap refresh")
    parser.add_argument("--topology-json", default=str(DEFAULT_TOPOLOGY_PATH), help="Aura !topology JSON path to load if refresh fails or is disabled")
    parser.add_argument("--reuse-topology-json", action="store_true", help="Do not run !topology/deep scan; import the existing topology JSON")
    parser.add_argument("--refresh-topology", action="store_true", help="With --refresh, also rerun Aura's deep topology scan")
    args = parser.parse_args()

    index_path = Path(args.index)
    if args.refresh is not None:
        if not index_path.exists():
            raise SystemExit(f"Missing {index_path}; build it first with python aura_codebase_navigator.py")
        payload = refresh_codemap_for_paths(
            args.refresh,
            root=Path(args.root).resolve(),
            index_path=index_path,
            markdown_path=Path(args.markdown),
            include_topology=not args.no_topology,
            topology_path=Path(args.topology_json),
            refresh_topology=args.refresh_topology,
        )
        print(json.dumps((payload or {}).get("last_refresh", {}), indent=2))
        return 0

    if args.query:
        if not index_path.exists():
            raise SystemExit(f"Missing {index_path}; build it first with python aura_codebase_navigator.py")
        hits = search_index(_load_json(index_path), args.query, limit=args.limit)
        print(json.dumps({"query": args.query, "hits": hits}, indent=2))
        return 0

    payload = build_navigation_system(
        Path(args.root).resolve(),
        include_topology=not args.no_topology,
        topology_path=Path(args.topology_json),
        refresh_topology=not args.reuse_topology_json,
    )
    json_path, md_path = write_navigation_artifacts(payload, index_path, Path(args.markdown))
    print(f"[+] wrote compact map {json_path}")
    print(f"[+] wrote human map {md_path}")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

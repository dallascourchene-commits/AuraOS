"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: ast, pathlib, spatial_mapper, aura_topology_manager, os, sys, numpy, re, collections, json
FUNCTIONS: _record_call, extract_ast_calls, scan_regex_signatures, compile_unified_graph, compile_topology_map, __init__, visit_If, visit_Try, resolve_call_target
SYNOPSIS: The `aura_analyzer` module integrates AST parsing (`ast`, `numpy`), filesystem traversal (`pathlib`, `os`, `sys`), topology mapping (`spatial_mapper`, `aura_topology_manager`), regex analysis (`re`), data structures (`collections`), and JSON I/O (`json`) to construct a unified dependency graph via `_record_call`, `extract_ast_calls`, `scan_regex_signatures`, `compile_unified_graph`, and `compile_topology_map`, while enforcing strict control-flow validation through `visit_If`, `visit_Try`, and `resolve_call_target` during static analysis.
[/AURA_MASTER_KEY]
"""
import os
import json
import ast
import sys
import re
import numpy as np
from collections import defaultdict
from pathlib import Path
from spatial_mapper import scan_and_vectorize, DirectoryCache

class LogicalGateVisitor(ast.NodeVisitor):
    def __init__(self):
        self.gates = []

    def visit_If(self, node):
        cond_str = ast.unparse(node.test) if hasattr(ast, 'unparse') else "dynamic_condition"
        if_calls = []
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    if_calls.append(n.func.id)
                elif isinstance(n.func, ast.Attribute):
                    if_calls.append(n.func.attr)
        self.gates.append({
            "gate_type": "conditional_branch",
            "precondition": cond_str,
            "consequent_calls": list(set(if_calls))
        })
        self.generic_visit(node)

    def visit_Try(self, node):
        handlers = []
        for h in node.handlers:
            handlers.append(ast.unparse(h.type) if (hasattr(ast, 'unparse') and h.type) else "Exception")
        self.gates.append({
            "gate_type": "exception_guard",
            "handlers": handlers
        })
        self.generic_visit(node)

# Pre-compiled regex patterns to scan for implicit dependencies
PORT_PATTERN = re.compile(r'(?:port\s*=\s*|connect\(\([^,]+,\s*)(\d{4})')
SQL_TABLE_PATTERN = re.compile(r'(?:FROM|INTO|UPDATE|TABLE|INDEX|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.IGNORECASE)
FILESYSTEM_PATTERN = re.compile(r'["\'](Aura_Memory|Aura_Staging|Aura_Staging/\S+|Aura_Memory/\S+)["\']')

# Known tables and ports to filter out standard SQL keywords/unrelated numbers
VALID_SQL_TABLES = {"traces", "causal_ledger", "morphemic_palace", "ojibwe_dkt_log", "dkt_holographic_log", "Voynich_Knowledge_Graph", "audit_cache"}
VALID_PORTS = {"8000", "8081", "4444", "8765"}

# Names that must not become cross-module graph edges (builtins / methods / stdlib)
_BUILTIN_CALL_NAMES = frozenset({
    "abs", "all", "any", "bool", "dict", "enumerate", "exp", "float", "get",
    "int", "isinstance", "issubclass", "len", "list", "max", "min", "open",
    "print", "range", "round", "set", "str", "strip", "sum", "super", "tuple",
    "type", "zip", "format", "join", "split", "append", "extend", "update",
    "clear", "pop", "getattr", "setattr", "hasattr", "bytes", "encode", "decode",
    "read", "write", "flush", "close", "sleep", "time", "parse", "compile",
    "walk", "exists", "path", "dump", "load", "loads", "dumps", "mean", "norm",
    "array", "reshape", "clip", "angle", "real", "imag", "conj", "astype",
})
_STDLIB_ROOT_NAMES = frozenset({
    "ast", "os", "sys", "json", "re", "time", "math", "asyncio", "sqlite3",
    "hashlib", "struct", "pathlib", "collections", "urllib", "subprocess",
    "numpy", "np", "websockets", "gc", "io", "shutil", "random", "socket",
    "ctypes", "importlib", "threading", "uuid", "tempfile", "contextlib",
})


def _record_call(func_calls: list, call_node: ast.Call) -> None:
    """Record a resolvable call target, skipping stdlib/builtin noise."""
    func = call_node.func
    if isinstance(func, ast.Name):
        name = func.id
        if name in _BUILTIN_CALL_NAMES:
            return
        func_calls.append(name)
    elif isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            if func.value.id in _STDLIB_ROOT_NAMES:
                return
            # Instance / node dispatch — not a free-function graph edge
            if func.value.id in ("self", "node", "cls"):
                return
        attr = func.attr
        if attr in _BUILTIN_CALL_NAMES:
            return
        func_calls.append(attr)


def extract_ast_calls(file_content: str, filename: str) -> dict:
    """Extracts explicit function and method calls inside a file using AST."""
    calls = defaultdict(list)
    try:
        tree = ast.parse(file_content, filename=filename)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                func_calls: list[str] = []
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, ast.Call):
                        _record_call(func_calls, sub_node)
                calls[func_name] = list(set(func_calls))
    except SyntaxError:
        pass
    return dict(calls)

def scan_regex_signatures(file_content: str) -> dict:
    """Scans for implicit, data-driven connections (shared SQLite tables, ports, and filesystems)."""
    ports = set(PORT_PATTERN.findall(file_content)) & VALID_PORTS
    tables = set(SQL_TABLE_PATTERN.findall(file_content)) & VALID_SQL_TABLES
    filesystems = {os.path.basename(p.strip('"\'')) for p in FILESYSTEM_PATTERN.findall(file_content)}
    
    return {
        "ports": list(ports),
        "tables": list(tables),
        "filesystems": list(filesystems)
    }

def compile_unified_graph():
    current_dir = getattr(sys.modules[__name__], 'current_dir', os.getcwd())
    # 1. Harvest base layout primitives safely avoiding NoneType allocations
    code_topology = scan_and_vectorize(current_dir) or []
    
    nodes_payload = []
    edges_payload = []
    
    shared_tables = defaultdict(list)
    port_sharers = defaultdict(list)
    file_ast_calls = {}
    
    # 2. Populate node graph configurations with Zero-Trust Type Guards.
    # scan_and_vectorize() returns {name, file, type, vector, line} — map to
    # the canonical {id, label, shape, color, vector, file} format so that the
    # edge-extraction step (which looks for "::" in node ids) can work.
    for raw in code_topology:
        if not raw or not isinstance(raw, dict):
            continue

        # Normalise: handle both the scan_and_vectorize schema and any
        # pre-formatted nodes that already carry "id" / "label" keys.
        if "name" in raw and "id" not in raw:
            # scan_and_vectorize format
            name      = raw.get("name", "unknown")
            file_path = raw.get("file", "")
            node_id   = f"{file_path}::{name}"
            label     = name
            shape     = "Cube" if raw.get("type") == "class" else "Sphere"
        else:
            # Pre-formatted format (kept for compatibility)
            node_id = raw.get("id") or raw.get("label") or f"node_{len(nodes_payload)}"
            label   = raw.get("label", "Unknown")
            shape   = raw.get("shape", "Sphere")
            file_path = raw.get("file", node_id.split("::")[0] if "::" in node_id else "")

        nodes_payload.append({
            "id":     node_id,
            "label":  label,
            "shape":  shape,
            "color":  raw.get("color", "#00E5FF"),
            "vector": raw.get("vector", [0.0, 0.0, 0.0]),
            "file":   file_path,
        })

    # Ensure global_scope anchor nodes exist for shared-resource edges.
    for file in {n["file"] for n in nodes_payload if n.get("file")}:
        gs_id = f"{file}::global_scope"
        if gs_id not in {n["id"] for n in nodes_payload}:
            nodes_payload.append({
                "id": gs_id,
                "label": "global_scope",
                "shape": "Octahedron",
                "color": "#9E9E9E",
                "vector": [0.0, 0.0, 0.0],
                "file": file,
            })

    node_ids_set = {n["id"] for n in nodes_payload}

    # 3. Activate Hidden Capabilities: Cross-reference via AST & Regex signatures.
    # Use nodes_payload (normalised, has "id" with "::" separator) not the raw
    # code_topology whose schema varies by producer.
    files = list({
        os.path.basename(n["id"].split("::")[0])
        for n in nodes_payload
        if n.get("id") and "::" in n["id"]
    })
    for file in sorted(files):
        if file.endswith(".py") and os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Active Integration: Extracting verified database and networking signals
                signatures = scan_regex_signatures(content)
                for table in signatures.get("tables", []):
                    shared_tables[table].append(file)
                for port in signatures.get("ports", []):
                    port_sharers[port].append(file)
                    
                # Active Integration: Extracting code block internal functional dependencies
                file_ast_calls[file] = extract_ast_calls(content, file)
            except Exception:
                pass

    # 4. Generate relationship links (Edges) Without Overwriting Architecture
    # Core Data Layer Links: Database Cross-References
    for table_name, files_sharing in shared_tables.items():
        if len(files_sharing) > 1:
            for i in range(len(files_sharing)):
                for j in range(i + 1, len(files_sharing)):
                    edges_payload.append({
                        "source": f"{files_sharing[i]}::global_scope",
                        "target": f"{files_sharing[j]}::global_scope",
                        "type": f"shared_table_{table_name}",
                        "color": "#4CAF50",
                        "strength": 0.8
                    })
                    
    # Core Network Layer Links: Shared Port Infrastructures
    for port, files_sharing in port_sharers.items():
        if len(files_sharing) > 1:
            for i in range(len(files_sharing)):
                for j in range(i + 1, len(files_sharing)):
                    edges_payload.append({
                        "source": f"{files_sharing[i]}::global_scope",
                        "target": f"{files_sharing[j]}::global_scope",
                        "type": f"shared_port_{port}",
                        "color": "#FFEB3B",
                        "strength": 0.9
                    })

    # Module-level import edges (structural morpheme resonance)
    local_stems = {os.path.basename(f).removesuffix(".py") for f in files}
    for file in files:
        if not os.path.exists(file):
            continue
        try:
            tree = ast.parse(open(file, encoding="utf-8").read(), filename=file)
        except SyntaxError:
            continue
        src_id = f"{file}::global_scope"
        if src_id not in node_ids_set:
            continue
        for node in tree.body:
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                targets = [node.module.split(".")[0]]
            for tgt in targets:
                if tgt in _STDLIB_ROOT_NAMES or tgt not in local_stems:
                    continue
                dst_id = next(
                    (
                        f"{n['file']}::global_scope"
                        for n in nodes_payload
                        if os.path.basename(n.get("file", "")) == f"{tgt}.py"
                    ),
                    None,
                )
                if dst_id and dst_id in node_ids_set:
                    edges_payload.append({
                        "source": src_id,
                        "target": dst_id,
                        "type": "import_module",
                        "color": "#FF9800",
                        "strength": 0.85,
                    })

    # Explicit Structural Links — resolve calls without ambiguous label collisions
    label_to_ids: dict[str, list[str]] = defaultdict(list)
    for n in nodes_payload:
        label_to_ids[n["label"]].append(n["id"])

    def resolve_call_target(file_path: str, called: str) -> str | None:
        """Prefer same-file targets; skip ambiguous cross-file label matches."""
        preferred = f"{file_path}::{called}"
        if preferred in node_ids_set:
            return preferred
        same_file = [m for m in label_to_ids.get(called, []) if m.startswith(f"{file_path}::")]
        if len(same_file) == 1:
            return same_file[0]
        matches = label_to_ids.get(called, [])
        if len(matches) == 1:
            return matches[0]
        return None

    for file, functions_dict in file_ast_calls.items():
        for func_name, internal_calls in functions_dict.items():
            source_id = f"{file}::{func_name}"
            if source_id not in node_ids_set:
                continue
            for called_element in internal_calls:
                if called_element == func_name:
                    continue
                target_id = resolve_call_target(file, called_element)
                if target_id:
                    edges_payload.append({
                        "source": source_id,
                        "target": target_id,
                        "type": "explicit_function_call",
                        "color": "#00E5FF",
                        "strength": 0.7
                    })

    unified_payload = {
        "status": "SYS_TOPOLOGY_ACTIVE",
        "nodes": nodes_payload,
        "edges": edges_payload
    }

    # 5. Commit state layout map safely back to disk
    target_path = "Aura_Memory/live_topology_ast.json"
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(unified_payload, f, indent=4)

    return unified_payload

def compile_topology_map(deep: bool = False) -> dict:
    """
    Topology scan with two modes:

    deep=False (default / !topology):
        Calls compile_unified_graph() — the existing regex+AST scanner.
        Fast, ~2-3 s on Termux.

    deep=True  (!topology deep):
        Calls aura_topology_manager.TopologyBuilder which adds:
          • Proper node ID normalisation (eliminates the ~352 unnamed '?' orphans
            in the standard scan caused by duplicate IDs across files)
          • Deduplication: nodes seen twice are merged rather than doubled
          • Import-level edges: every 'from X import Y' adds a module-level edge
            so isolated modules that are imported but call nothing still appear
            in the graph
          • Per-file constraint metrics: bytes, line count, async entry points
          • Inline diagnostics: isolated count, dead-end count, dangling edges,
            top-15 hub nodes by combined degree

        Writes the richer payload to topology_map.json (in addition to the
        standard live_topology_ast.json) so the AR visualiser can show both.

    Emergent connections revealed by the deep scan (from this codebase):
        aura_topology_manager  ←→  aura_topological_scanner  (now wired)
        pvm_memory_guard       →   async_palace               (now wired)
        aura_spectral_memory   →   aura_dream_engine          (now wired)
    """
    if not deep:
        return compile_unified_graph()

    try:
        # Intentional function-scoped import: aura_topology_manager imports this
        # module at file scope, so a top-level binding would create a circular import.
        from aura_topology_manager import TopologyBuilder, write_json, OUTPUT_PATH  # noqa: nested-import

        builder = TopologyBuilder(root=Path("."))
        payload  = builder.run()

        # Also write the deep map so downstream tools can read topology_map.json
        try:
            write_json(OUTPUT_PATH, payload)
        except Exception:
            pass

        # Patch standard live_topology_ast.json with the richer node list so the
        # AR visualiser (Port 8081) and active inference context reader both get
        # properly named nodes instead of '?' placeholders.
        target_path = "Aura_Memory/live_topology_ast.json"
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        live_compatible = {
            "status": "SYS_TOPOLOGY_DEEP_ACTIVE",
            "nodes": payload["nodes"],
            "edges": payload["edges"],
            "diagnostics": payload.get("diagnostics", {}),
            "meta": payload.get("meta", {}),
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(live_compatible, f, indent=4)

        return payload

    except Exception as exc:
        print(f"[!] TopologyBuilder unavailable ({exc}), falling back to standard scan")
        return compile_unified_graph()


if __name__ == "__main__":
    compile_unified_graph()
    print("[+] Refined dependency discovery complete. Map output written to Aura_Memory.")

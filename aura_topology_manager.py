"""
Architectural Header — aura_topology_manager
Role: AST-driven topological map generator for the PVM morpheme cluster.
Memory: O(files) scan; JSON output ~1–3 MB; zero-copy NumPy not used at scan time.
Edges: imports pvm_arch_checker, aura_topological_scanner, aura_topology_analyzer.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from aura_topological_scanner import compile_unified_graph as _compile_unified_graph
except ImportError:
    _compile_unified_graph = None  # type: ignore[assignment,misc]

try:
    from aura_topology_analyzer import diagnose_fractures as _diagnose_fractures
except ImportError:
    _diagnose_fractures = None  # type: ignore[assignment,misc]

ROOT = Path(".").resolve()


def _normalize_node_id(node_id: str) -> str:
    if "::" not in node_id:
        return Path(node_id).name
    file_part, symbol = node_id.rsplit("::", 1)
    return f"{Path(file_part).name}::{symbol}"
OUTPUT_PATH = Path("topology_map.json")
LIVE_TOPOLOGY_PATH = Path("Aura_Memory/live_topology_ast.json")

_STDLIB_ROOTS = frozenset({
    "abc", "ast", "asyncio", "builtins", "collections", "concurrent", "contextlib",
    "copy", "ctypes", "dataclasses", "datetime", "decimal", "enum", "functools",
    "gc", "glob", "hashlib", "heapq", "importlib", "inspect", "io", "itertools",
    "json", "keyword", "logging", "math", "mmap", "multiprocessing", "numbers",
    "operator", "os", "pathlib", "pickle", "platform", "queue", "random", "re",
    "select", "shlex", "shutil", "signal", "socket", "sqlite3", "ssl", "stat",
    "struct", "subprocess", "sys", "tempfile", "textwrap", "threading", "time",
    "traceback", "types", "typing", "unicodedata", "unittest", "urllib", "uuid",
    "warnings", "weakref", "xml", "zipfile", "zlib", "__future__",
})

_BUILTIN_CALLS = frozenset({
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "get", "int",
    "isinstance", "len", "list", "max", "min", "open", "print", "range", "round",
    "set", "str", "sum", "super", "tuple", "type", "zip", "format", "append",
    "extend", "update", "getattr", "setattr", "hasattr", "bytes", "encode",
    "decode", "read", "write", "flush", "close", "sleep", "parse", "compile",
    "walk", "exists", "dump", "load", "loads", "dumps", "mean", "norm", "array",
    "reshape", "clip", "angle", "real", "imag", "conj", "astype", "join", "split",
})


@dataclass
class TopologyBuilder:
    root: Path
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    constraints: dict[str, dict[str, Any]] = field(default_factory=dict)
    _node_ids: set[str] = field(default_factory=set)
    _label_index: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    _local_modules: set[str] = field(default_factory=set)

    def run(self) -> dict[str, Any]:
        py_files = sorted(self.root.glob("*.py"))
        self._local_modules = {p.stem for p in py_files}

        for path in py_files:
            self._scan_module(path)

        self._link_import_graph(py_files)
        diagnostics = self._compute_diagnostics()
        payload = {
            "meta": {
                "generated_by": "aura_topology_manager",
                "root": str(self.root),
                "module_count": len(py_files),
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
            },
            "nodes": self.nodes,
            "edges": self.edges,
            "constraints": self.constraints,
            "diagnostics": diagnostics,
        }
        return payload

    def _add_node(self, node: dict[str, Any]) -> None:
        node["id"] = _normalize_node_id(node["id"])
        if "file" in node:
            node["file"] = Path(node["file"]).name
        nid = node["id"]
        if nid in self._node_ids:
            return
        self._node_ids.add(nid)
        self.nodes.append(node)
        self._label_index[node["label"]].append(nid)

    def _add_edge(self, source: str, target: str, kind: str, **extra: Any) -> None:
        if source not in self._node_ids or target not in self._node_ids:
            return
        self.edges.append({"source": source, "target": target, "kind": kind, **extra})

    def _scan_module(self, path: Path) -> None:
        rel = path.name
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            self.constraints[rel] = {"parse_error": str(exc), "line": exc.lineno or 0}
            return

        file_bytes = path.stat().st_size
        line_count = source.count("\n") + 1
        async_entries: list[str] = []

        module_id = f"{rel}::global_scope"
        self._add_node({
            "id": module_id,
            "kind": "module",
            "label": "global_scope",
            "file": rel,
            "line": 1,
            "module": path.stem,
        })

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cid = f"{rel}::{node.name}"
                self._add_node({
                    "id": cid,
                    "kind": "class",
                    "label": node.name,
                    "file": rel,
                    "line": node.lineno,
                    "module": path.stem,
                })
                self._add_edge(module_id, cid, "defines")
            elif isinstance(node, ast.FunctionDef):
                parent = self._parent_name(tree, node)
                fid = f"{rel}::{parent}::{node.name}" if parent else f"{rel}::{node.name}"
                self._add_node({
                    "id": fid,
                    "kind": "method" if parent else "function",
                    "label": node.name,
                    "file": rel,
                    "line": node.lineno,
                    "module": path.stem,
                    "parent": parent,
                })
                if parent:
                    self._add_edge(f"{rel}::{parent}", fid, "defines")
                else:
                    self._add_edge(module_id, fid, "defines")
                self._extract_calls(rel, fid, node)
            elif isinstance(node, ast.AsyncFunctionDef):
                parent = self._parent_name(tree, node)
                aid = f"{rel}::{parent}::{node.name}" if parent else f"{rel}::{node.name}"
                self._add_node({
                    "id": aid,
                    "kind": "async_method" if parent else "async_function",
                    "label": node.name,
                    "file": rel,
                    "line": node.lineno,
                    "module": path.stem,
                    "parent": parent,
                    "is_async": True,
                })
                if parent:
                    self._add_edge(f"{rel}::{parent}", aid, "defines")
                else:
                    self._add_edge(module_id, aid, "defines")
                if node.name in {"main", "boot", "run", "serve"} or (
                    not parent and node.name.startswith(("async_", "run_"))
                ):
                    async_entries.append(node.name)
                self._extract_calls(rel, aid, node)

        if tree.body and isinstance(tree.body[-1], ast.If):
            last = tree.body[-1]
            if (
                isinstance(last.test, ast.Compare)
                and isinstance(last.test.left, ast.Name)
                and last.test.left.id == "__name__"
            ):
                for child in last.body:
                    if isinstance(child, ast.AsyncFunctionDef):
                        async_entries.append(child.name)

        self.constraints[rel] = {
            "bytes": file_bytes,
            "lines": line_count,
            "memory_tier_estimate_kb": max(1, file_bytes // 1024),
            "async_entry_points": sorted(set(async_entries)),
            "async_function_count": sum(
                1 for n in self.nodes if n.get("file") == rel and n.get("is_async")
            ),
        }

    @staticmethod
    def _parent_name(tree: ast.Module, node: ast.AST) -> str | None:
        for parent in ast.walk(tree):
            if not isinstance(parent, ast.ClassDef):
                continue
            if node in parent.body:
                return parent.name
        return None

    def _extract_calls(self, rel: str, source_id: str, fn_node: ast.AST) -> None:
        for sub in ast.walk(fn_node):
            if not isinstance(sub, ast.Call):
                continue
            target = self._resolve_call(rel, sub)
            if target:
                self._add_edge(source_id, target, "call", strength=0.7)

    def _resolve_call(self, rel: str, call: ast.Call) -> str | None:
        func = call.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
            if name in _BUILTIN_CALLS:
                return None
        elif isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id in ("self", "cls", "node"):
                return None
            name = func.attr
            if name in _BUILTIN_CALLS:
                return None
        if not name:
            return None

        preferred = f"{rel}::{name}"
        if preferred in self._node_ids:
            return preferred
        same_file = [m for m in self._label_index.get(name, []) if m.startswith(f"{rel}::")]
        if len(same_file) == 1:
            return same_file[0]
        matches = self._label_index.get(name, [])
        if len(matches) == 1:
            return matches[0]
        return None

    def _link_import_graph(self, py_files: list[Path]) -> None:
        for path in py_files:
            rel = path.name
            src_mod = f"{rel}::global_scope"
            if src_mod not in self._node_ids:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in tree.body:
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    targets = [node.module.split(".")[0]]
                for tgt in targets:
                    if tgt in _STDLIB_ROOTS or tgt == path.stem:
                        continue
                    if tgt not in self._local_modules:
                        continue
                    dst = f"{tgt}.py::global_scope"
                    if dst in self._node_ids:
                        self._add_edge(src_mod, dst, "import_module", strength=0.9)

    def _compute_diagnostics(self) -> dict[str, Any]:
        connected: set[str] = set()
        out_degree: dict[str, int] = defaultdict(int)
        in_degree: dict[str, int] = defaultdict(int)
        for edge in self.edges:
            connected.add(edge["source"])
            connected.add(edge["target"])
            out_degree[edge["source"]] += 1
            in_degree[edge["target"]] += 1

        isolated = [n["id"] for n in self.nodes if n["id"] not in connected]
        dead_ends = [n["id"] for n in self.nodes if out_degree.get(n["id"], 0) == 0]
        hubs = sorted(
            [(nid, in_degree[nid] + out_degree[nid]) for nid in connected],
            key=lambda x: x[1],
            reverse=True,
        )[:15]

        dangling = [
            e for e in self.edges
            if e["source"] not in self._node_ids or e["target"] not in self._node_ids
        ]

        return {
            "isolated_node_count": len(isolated),
            "dead_end_count": len(dead_ends),
            "dangling_edge_count": len(dangling),
            "top_hubs": [{"id": h[0], "degree": h[1]} for h in hubs],
            "isolated_sample": isolated[:20],
            "dead_end_sample": dead_ends[:20],
        }


def run_arch_checker(root: Path) -> tuple[bool, str]:
    checker = root / "pvm_arch_checker.py"
    if not checker.exists():
        return True, "SKIPPED (pvm_arch_checker.py missing)"
    proc = subprocess.run(
        [sys.executable, str(checker), "--path", str(root)],
        capture_output=True,
        text=True,
    )
    status = "PASSED" if proc.returncode == 0 else "FAILED"
    detail = proc.stdout.strip() or proc.stderr.strip()
    return proc.returncode == 0, f"{status}: {detail.splitlines()[-1] if detail else 'no output'}"


def refresh_live_topology() -> dict[str, Any] | None:
    if _compile_unified_graph is None:
        print("[!] live topology refresh failed: aura_topological_scanner unavailable")
        return None
    try:
        return _compile_unified_graph()
    except Exception as exc:
        print(f"[!] live topology refresh failed: {exc}")
        return None


def load_fracture_report() -> dict[str, Any]:
    if _diagnose_fractures is None:
        return {"error": "aura_topology_analyzer unavailable", "total": 0}
    try:
        return _diagnose_fractures()
    except Exception as exc:
        return {"error": str(exc), "total": 0}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="AURA PVM topological map manager")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSON path")
    parser.add_argument("--refresh-live", action="store_true", help="Also refresh live_topology_ast.json")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if arch check fails")
    args = parser.parse_args()

    ok, arch_status = run_arch_checker(ROOT)
    print(f"[*] pvm_arch_checker: {arch_status}")

    builder = TopologyBuilder(ROOT)
    payload = builder.run()
    payload["meta"]["arch_check"] = arch_status

    fractures = load_fracture_report()
    payload["diagnostics"]["fractures"] = fractures

    if args.refresh_live:
        live = refresh_live_topology()
        if live:
            payload["meta"]["live_topology_nodes"] = len(live.get("nodes", []))
            payload["meta"]["live_topology_edges"] = len(live.get("edges", []))

    out = Path(args.output)
    write_json(out, payload)
    print(f"[+] topology_map.json written: {len(payload['nodes'])} nodes, {len(payload['edges'])} edges")
    print(f"    isolated={payload['diagnostics']['isolated_node_count']}  "
          f"dead_ends={payload['diagnostics']['dead_end_count']}  "
          f"dangling={payload['diagnostics']['dangling_edge_count']}")
    if fractures.get("total"):
        print(f"[!] NeSy fractures detected: {fractures['total']} ({fractures.get('by_kind', {})})")

    if args.strict and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

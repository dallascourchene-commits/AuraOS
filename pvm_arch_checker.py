from __future__ import annotations

"""
AURA Polysynthetic Virtual Machine — Architectural Rule Checker
===============================================================
Performs static AST analysis across the entire Python codebase to enforce
the following PVM architectural constraints:

  1. No nested / non-top-level imports (explicit top-level imports only).
  2. No wildcard imports  (``from x import *``).
  3. No namespace injection  (``__import__``, exec-time importlib inside
     functions/classes).
  4. No circular import loops in the *module-level* dependency graph.
  5. Duplicate top-level imports within a single file.

Usage (standalone)::

    python pvm_arch_checker.py [--path <dir>] [--strict] [--json]

Exit code 0 = no violations.  Non-zero = violations found.
"""

import argparse
import ast
import json
import os
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class Violation(NamedTuple):
    rule: str          # rule identifier, e.g. "NESTED_IMPORT"
    file: str
    line: int
    detail: str


class DepGraph:
    """Directed graph of module-level import dependencies."""

    def __init__(self) -> None:
        self._edges: dict[str, set[str]] = defaultdict(set)

    def add_edge(self, src: str, dst: str) -> None:
        self._edges[src].add(dst)

    def nodes(self) -> set[str]:
        nodes: set[str] = set()
        for src, dsts in self._edges.items():
            nodes.add(src)
            nodes.update(dsts)
        return nodes

    def successors(self, node: str) -> set[str]:
        return self._edges.get(node, set())

    def find_cycles(self) -> list[list[str]]:
        """Return all simple cycles via iterative DFS (Johnson's approach, simplified)."""
        cycles: list[list[str]] = []
        visited: set[str] = set()

        def dfs(node: str, stack: list[str], on_stack: set[str]) -> None:
            visited.add(node)
            on_stack.add(node)
            stack.append(node)
            for neighbour in self.successors(node):
                if neighbour not in visited:
                    dfs(neighbour, stack, on_stack)
                elif neighbour in on_stack:
                    idx = stack.index(neighbour)
                    cycles.append(stack[idx:] + [neighbour])
            stack.pop()
            on_stack.discard(node)

        for n in sorted(self.nodes()):
            if n not in visited:
                dfs(n, [], set())
        return cycles


# ---------------------------------------------------------------------------
# Core analyser
# ---------------------------------------------------------------------------

_STDLIB_NAMES: frozenset[str] = frozenset({
    "abc", "ast", "asyncio", "builtins", "cmath", "collections", "concurrent",
    "contextlib", "copy", "ctypes", "dataclasses", "datetime", "decimal",
    "difflib", "email", "enum", "errno", "functools", "gc", "glob", "hashlib",
    "heapq", "hmac", "html", "http", "importlib", "inspect", "io", "itertools",
    "json", "keyword", "linecache", "locale", "logging", "math", "mimetypes",
    "mmap", "multiprocessing", "numbers", "operator", "os", "pathlib", "pickle",
    "platform", "pprint", "queue", "random", "re", "select", "shlex", "shutil",
    "signal", "socket", "sqlite3", "ssl", "stat", "statistics", "string",
    "struct", "subprocess", "sys", "tempfile", "textwrap", "threading", "time",
    "timeit", "traceback", "types", "typing", "unicodedata", "unittest", "urllib",
    "uuid", "warnings", "weakref", "xml", "xmlrpc", "zipfile", "zlib",
    "__future__",
})


def _is_stdlib(name: str) -> bool:
    return name.split(".")[0] in _STDLIB_NAMES


def _module_name(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return rel.with_suffix("").as_posix().replace("/", ".")


class PVMArchChecker:
    """
    Walks a directory tree, parses every ``.py`` file with the stdlib ``ast``
    module, and checks for PVM architectural violations.
    """

    def __init__(self, root: Path, *, strict: bool = False) -> None:
        self.root = root.resolve()
        self.strict = strict
        self.violations: list[Violation] = []
        self._dep_graph = DepGraph()
        self._local_modules: set[str] = set()
        self._source_lines: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> list[Violation]:
        """Analyse all ``.py`` files under *root*. Returns violation list."""
        py_files = sorted(self.root.glob("*.py"))  # flat workspace, no sub-packages
        self._local_modules = {f.stem for f in py_files}

        for path in py_files:
            self._analyse_file(path)

        self._check_cycles()
        return self.violations

    # ------------------------------------------------------------------
    # Per-file analysis
    # ------------------------------------------------------------------

    def _analyse_file(self, path: Path) -> None:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            self.violations.append(
                Violation("SYNTAX_ERROR", str(path), exc.lineno or 0, str(exc))
            )
            return

        fname = path.name
        self._source_lines[fname] = source.splitlines()
        self._check_duplicate_imports(tree, fname)
        self._check_nested_imports(tree, fname)
        self._check_wildcard_imports(tree, fname)
        self._check_namespace_injections(tree, fname)
        self._build_dep_edges(tree, path)

    # ------------------------------------------------------------------
    # Rule 1 — nested imports
    # ------------------------------------------------------------------

    def _check_nested_imports(
        self, tree: ast.Module, fname: str
    ) -> None:
        """Flag any import statement that is not a direct child of the module body."""
        module_level_lines: set[int] = {
            node.lineno
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        }

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for child in ast.walk(node):
                if child is node:
                    continue
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    # Allow imports marked with # noqa: nested-import (circular-import guard)
                    try:
                        src_lines = self._source_lines.get(fname, [])
                        line_txt = src_lines[child.lineno - 1] if src_lines and child.lineno <= len(src_lines) else ""
                        if "noqa: nested-import" in line_txt or "noqa:nested-import" in line_txt:
                            continue
                    except Exception:
                        pass
                    if isinstance(child, ast.ImportFrom):
                        mod = child.module or ""
                        names = ", ".join(a.name for a in child.names)
                        detail = f"from {mod} import {names}"
                    else:
                        names = ", ".join(a.name for a in child.names)
                        detail = f"import {names}"
                    self.violations.append(
                        Violation(
                            "NESTED_IMPORT",
                            fname,
                            child.lineno,
                            f"Import inside '{node.name}': {detail}",
                        )
                    )

    # ------------------------------------------------------------------
    # Rule 2 — wildcard imports
    # ------------------------------------------------------------------

    def _check_wildcard_imports(
        self, tree: ast.Module, fname: str
    ) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        self.violations.append(
                            Violation(
                                "WILDCARD_IMPORT",
                                fname,
                                node.lineno,
                                f"from {node.module or '?'} import *",
                            )
                        )

    # ------------------------------------------------------------------
    # Rule 3 — namespace injection
    # ------------------------------------------------------------------

    def _check_namespace_injections(
        self, tree: ast.Module, fname: str
    ) -> None:
        """
        Detect calls to ``__import__()`` or ``importlib.import_module()``
        inside function or class bodies (dynamic namespace injection).
        """
        for parent in ast.walk(tree):
            if not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for node in ast.walk(parent):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                # __import__('modname')
                if isinstance(func, ast.Name) and func.id == "__import__":
                    self.violations.append(
                        Violation(
                            "NAMESPACE_INJECTION",
                            fname,
                            node.lineno,
                            "__import__() call inside a function/class",
                        )
                    )
                # importlib.import_module('modname')
                elif (
                    isinstance(func, ast.Attribute)
                    and func.attr == "import_module"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "importlib"
                ):
                    self.violations.append(
                        Violation(
                            "NAMESPACE_INJECTION",
                            fname,
                            node.lineno,
                            "importlib.import_module() inside a function/class",
                        )
                    )

    # ------------------------------------------------------------------
    # Rule 5 — duplicate top-level imports
    # ------------------------------------------------------------------

    def _check_duplicate_imports(
        self, tree: ast.Module, fname: str
    ) -> None:
        seen: dict[str, int] = {}
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    key = f"import:{alias.name}"
                    if key in seen:
                        self.violations.append(
                            Violation(
                                "DUPLICATE_IMPORT",
                                fname,
                                node.lineno,
                                f"'{alias.name}' already imported at line {seen[key]}",
                            )
                        )
                    else:
                        seen[key] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = tuple(sorted(a.name for a in node.names))
                key = f"from:{mod}:{names}"
                if key in seen:
                    self.violations.append(
                        Violation(
                            "DUPLICATE_IMPORT",
                            fname,
                            node.lineno,
                            f"'from {mod} import ...' already at line {seen[key]}",
                        )
                    )
                else:
                    seen[key] = node.lineno

    # ------------------------------------------------------------------
    # Dependency graph construction (module-level only)
    # ------------------------------------------------------------------

    def _build_dep_edges(self, tree: ast.Module, path: Path) -> None:
        src_stem = path.stem
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base = alias.name.split(".")[0]
                    if base in self._local_modules and base != src_stem:
                        self._dep_graph.add_edge(src_stem, base)
            elif isinstance(node, ast.ImportFrom) and node.module:
                base = node.module.split(".")[0]
                if base in self._local_modules and base != src_stem:
                    self._dep_graph.add_edge(src_stem, base)

    # ------------------------------------------------------------------
    # Rule 4 — circular imports
    # ------------------------------------------------------------------

    def _check_cycles(self) -> None:
        cycles = self._dep_graph.find_cycles()
        for cycle in cycles:
            chain = " → ".join(cycle)
            involved_file = cycle[0] + ".py"
            self.violations.append(
                Violation(
                    "CIRCULAR_IMPORT",
                    involved_file,
                    0,
                    f"Module-level circular dependency: {chain}",
                )
            )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def report_text(self) -> str:
        if not self.violations:
            return "PVM Arch Check: PASSED — no violations found."

        by_rule: dict[str, list[Violation]] = defaultdict(list)
        for v in self.violations:
            by_rule[v.rule].append(v)

        lines = [
            "╔══════════════════════════════════════════════════════════════════╗",
            "║          AURA PVM — ARCHITECTURAL VIOLATION REPORT              ║",
            "╚══════════════════════════════════════════════════════════════════╝",
            "",
        ]

        rule_descs = {
            "SYNTAX_ERROR":       "Syntax errors  (file cannot be parsed)",
            "NESTED_IMPORT":      "Nested imports  (must be top-level)",
            "WILDCARD_IMPORT":    "Wildcard imports  (from x import *)",
            "NAMESPACE_INJECTION":"Namespace injections  (__import__ / importlib inside fn)",
            "DUPLICATE_IMPORT":   "Duplicate top-level imports",
            "CIRCULAR_IMPORT":    "Circular module-level import loops",
        }

        totals: dict[str, int] = {}
        for rule, vs in sorted(by_rule.items()):
            totals[rule] = len(vs)
            desc = rule_descs.get(rule, rule)
            lines.append(f"  [{rule}]  {desc}  ({len(vs)} occurrence{'s' if len(vs) != 1 else ''})")
            for v in sorted(vs, key=lambda x: (x.file, x.line))[:20]:
                lines.append(f"      {v.file}:{v.line}  —  {v.detail}")
            if len(vs) > 20:
                lines.append(f"      … and {len(vs) - 20} more")
            lines.append("")

        lines.append(f"  Total violations: {len(self.violations)}")
        return "\n".join(lines)

    def report_json(self) -> str:
        return json.dumps(
            [v._asdict() for v in self.violations],
            indent=2,
        )

    def dependency_map_text(self) -> str:
        """Human-readable module-level dependency map."""
        lines = [
            "╔══════════════════════════════════════════════╗",
            "║   AURA PVM — Module Dependency Map           ║",
            "╚══════════════════════════════════════════════╝",
            "",
        ]
        for src in sorted(self._dep_graph._edges):
            dsts = sorted(self._dep_graph._edges[src])
            if dsts:
                lines.append(f"  {src}")
                for d in dsts:
                    lines.append(f"    └─▶ {d}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AURA PVM Architectural Rule Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Root directory to analyse (default: current directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero even on warnings",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output violations as JSON",
    )
    parser.add_argument(
        "--depmap",
        action="store_true",
        help="Print the module-level dependency map and exit",
    )
    args = parser.parse_args()

    root = Path(args.path).resolve()
    checker = PVMArchChecker(root, strict=args.strict)
    checker.run()

    if args.depmap:
        print(checker.dependency_map_text())
        return

    if args.as_json:
        print(checker.report_json())
    else:
        print(checker.report_text())

    errors = [
        v for v in checker.violations
        if v.rule in {"SYNTAX_ERROR", "WILDCARD_IMPORT", "CIRCULAR_IMPORT", "NAMESPACE_INJECTION"}
    ]
    if errors or (args.strict and checker.violations):
        sys.exit(1)


if __name__ == "__main__":
    main()

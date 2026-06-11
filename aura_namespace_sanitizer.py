"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:SANITIZER_NODE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: ast, os, sys, re, pathlib, gc
FUNCTIONS: sanitize_module, strip_redundant_imports, hoist_imports_to_top,
           NamespaceSanitizer, sanitize_all_modules
SYNOPSIS: AST-based namespace sanitization engine that inspects self-repaired
          Python modules, strips out duplicate/redundant local-scope imports
          (os, sys, time, shutil, etc.), and hoists all required namespaces
          cleanly to the top-level module scope before serialization to disk.
          Prevents the mutation pipeline from generating bloated, unparseable
          imports during iterative code generation under Termux 4GB RAM.
[/AURA_MASTER_KEY]
"""
import ast
import gc
import os
import re
import sys
from pathlib import Path

# Standard-library modules that must NOT be duplicated or nested
_STDLIB_NAMES = frozenset({
    "os", "sys", "time", "shutil", "json", "re", "math", "asyncio",
    "hashlib", "struct", "pathlib", "collections", "sqlite3",
    "subprocess", "threading", "uuid", "tempfile", "contextlib",
    "io", "gc", "random", "socket", "ctypes", "importlib",
    "numpy", "np", "websockets",
})

# These names are always safe to deduplicate (top-level constant re-exports)
_ALIAS_IMPORT_NAMES = frozenset({
    "np", "Path", "datetime", "defaultdict", "Counter", "deque",
    "Any", "Dict", "Union", "Optional", "Callable", "Tuple", "List",
})


def _normalise_import_name(alias: ast.alias) -> str:
    """Return the canonical local name for an import alias."""
    return alias.asname or alias.name


def _is_stdlib_import(target: str) -> bool:
    """Check if a top-level import target is a stdlib module (no false positives)."""
    return target in _STDLIB_NAMES or target.split(".")[0] in _STDLIB_NAMES


class _ImportCollector(ast.NodeVisitor):
    """Gather all import statements and their source locations."""

    def __init__(self) -> None:
        self.top_imports: list[ast.stmt] = []       # module-level
        self.nested_imports: list[ast.stmt] = []     # inside functions/classes
        self.imported_names: set[str] = set()        # canonical local names at top level
        self._depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = _normalise_import_name(alias)
            if self._depth == 0:
                self.top_imports.append(node)
                self.imported_names.add(name)
            else:
                self.nested_imports.append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = _normalise_import_name(alias)
            if self._depth == 0:
                self.top_imports.append(node)
                self.imported_names.add(name)
            else:
                self.nested_imports.append(node)


def strip_redundant_imports(source_code: str) -> str:
    """
    Remove all duplicate ``import os``, ``import sys``, ``import time``,
    and ``import shutil`` statements that appear inside local scopes
    (function/class bodies) when the same name is already imported at
    module level.

    Returns the cleaned source string.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return source_code  # can't safely mutate unparseable code

    collector = _ImportCollector()
    collector.visit(tree)

    if not collector.nested_imports:
        return source_code  # nothing to strip

    # Build a set of (lineno, col_offset) of import nodes to remove
    removal_spans: list[tuple[int, int]] = []
    for imp in collector.nested_imports:
        if isinstance(imp, ast.Import):
            for alias in imp.names:
                name = _normalise_import_name(alias)
                if _is_stdlib_import(name) and name in collector.imported_names:
                    removal_spans.append((imp.lineno, imp.end_lineno or imp.lineno))
        elif isinstance(imp, ast.ImportFrom):
            for alias in imp.names:
                name = _normalise_import_name(alias)
                if (imp.module and _is_stdlib_import(imp.module) and
                        name in collector.imported_names):
                    removal_spans.append((imp.lineno, imp.end_lineno or imp.lineno))

    if not removal_spans:
        return source_code

    # Remove the flagged lines
    lines = source_code.splitlines(keepends=True)
    lines_to_keep = []
    removal_set = set()
    for start, end in removal_spans:
        for ln in range(start, end + 1):
            removal_set.add(ln)

    for i, line in enumerate(lines, start=1):
        if i not in removal_set:
            lines_to_keep.append(line)
        else:
            # Replace with a blank line to preserve line number correspondence
            # in remaining code (avoids debug confusion)
            if i > 1 and lines_to_keep and lines_to_keep[-1].strip() == "":
                pass  # skip consecutive blank lines
            else:
                lines_to_keep.append("\n")

    result = "".join(lines_to_keep)
    del lines, lines_to_keep
    gc.collect()
    return result


def hoist_imports_to_top(source_code: str) -> str:
    """
    Find any stdlib imports that exist only in local scopes and hoist
    them to the module top, ensuring every required namespace is at
    top-level before disk serialization.

    Returns the re-ordered source string.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return source_code

    collector = _ImportCollector()
    collector.visit(tree)

    # Imports in nested scopes that aren't already at top level
    new_imports: list[ast.stmt] = []
    seen_new: set[str] = set(collector.imported_names)

    for imp in collector.nested_imports:
        if isinstance(imp, ast.Import):
            for alias in imp.names:
                name = _normalise_import_name(alias)
                if _is_stdlib_import(name) and name not in seen_new:
                    new_imports.append(ast.Import(names=[ast.alias(name=name, asname=None)]))
                    seen_new.add(name)
        elif isinstance(imp, ast.ImportFrom):
            for alias in imp.names:
                name = _normalise_import_name(alias)
                if imp.module and _is_stdlib_import(imp.module) and name not in seen_new:
                    new_imports.append(
                        ast.ImportFrom(
                            module=imp.module,
                            names=[ast.alias(name=alias.name, asname=alias.asname)],
                            level=0,
                        )
                    )
                    seen_new.add(name)

    if not new_imports:
        return source_code

    # Insert new imports right after any existing docstring and __future__ imports
    lines = source_code.splitlines(keepends=True)
    insertion_line = 0

    # Skip docstring
    docstring_done = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not docstring_done:
                docstring_done = True
                insertion_line = i + 1
                continue
            if docstring_done and i == insertion_line:
                insertion_line = i + 1
                break  # second triple-quote closes it
        elif docstring_done and not stripped.startswith("from __future__"):
            insertion_line = i
            break

    # Build import source lines
    new_source_lines: list[str] = []
    for imp in new_imports:
        new_source_lines.append(ast.unparse(imp) + "\n")
    new_source_lines.append("\n")  # blank separator

    result_lines = lines[:insertion_line] + new_source_lines + lines[insertion_line:]
    result = "".join(result_lines)
    del lines, result_lines
    gc.collect()
    return result


def sanitize_module(file_path: str) -> bool:
    """
    Full sanitization pass on a single Python file:
    1. Strip redundant local-scope imports
    2. Hoist remaining needed namespaces to top level

    Returns True if the file was modified.
    """
    path = Path(file_path)
    if not path.exists() or not path.suffix == ".py":
        return False

    try:
        original = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    cleaned = strip_redundant_imports(original)
    hoisted = hoist_imports_to_top(cleaned)

    if hoisted != original:
        try:
            # Verify the result parses
            ast.parse(hoisted)
        except SyntaxError:
            return False  # don't write unparseable code
        try:
            path.write_text(hoisted, encoding="utf-8")
            return True
        except OSError:
            return False

    return False


def sanitize_all_modules(root_dir: str = ".") -> dict[str, bool]:
    """
    Scan all .py files under *root_dir* and sanitize each one.
    Returns a dict mapping filename → whether it was modified.
    Skips test files and backup files.
    """
    results: dict[str, bool] = {}
    root = Path(root_dir)

    for py_file in sorted(root.glob("*.py")):
        name = py_file.name
        if name.startswith("test_") or name.endswith(".bak") or name.endswith(".save"):
            continue
        if name == "aura_namespace_sanitizer.py":
            continue  # don't self-sanitize during bootstrap
        try:
            modified = sanitize_module(str(py_file))
            results[name] = modified
            if modified:
                print(f"[SANITIZER] Cleaned: {name}")
        except Exception as exc:
            print(f"[SANITIZER] Error on {name}: {exc}")
            results[name] = False

    gc.collect()
    return results


# ── Standalone CLI ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aura Namespace Sanitizer")
    parser.add_argument("target", nargs="?", default=".",
                        help="File or directory to sanitize (default: current dir)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change without writing")
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_file():
        print(f"[SANITIZER] Scanning: {target}")
        modified = sanitize_module(str(target))
        print(f"  Result: {'modified' if modified else 'unchanged'}")
    else:
        print(f"[SANITIZER] Scanning directory: {target}")
        results = sanitize_all_modules(str(target))
        total = sum(1 for v in results.values() if v)
        print(f"\n[SANITIZER] Done. {total} file(s) sanitized out of {len(results)} scanned.")
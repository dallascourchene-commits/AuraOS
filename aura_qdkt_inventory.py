"""Deterministic repository inventory for legacy QuantumMerkleDAG uses."""
from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from aura_event_contracts import canonical_json
from aura_qdkt_compatibility_types import (
    QDKTInventoryEntry,
    QDKTInventoryImpact,
    QDKTInventoryReadiness,
    QDKTInventoryReport,
    QDKTUseClass,
)

_TEXT_SUFFIXES = {".md", ".rst", ".txt", ".json", ".toml", ".yml", ".yaml"}
_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "Aura_Memory",
    "Aura_Sandbox",
    "__pycache__",
    "node_modules",
    "venv",
}
_EXCLUDED_FILES = {
    ".aura/CODEMAP.json",
    ".aura/CODEMAP.md",
    ".aura/understand_graph.json",
    "topology_map.json",
}
_QDKT_TERMS = ("QuantumMerkleDAG", "generate_epistemic_system_root", "quantum_dag")
_PERSISTENCE_METHODS = {
    "dump",
    "dumps",
    "execute",
    "executemany",
    "insert",
    "save",
    "store",
    "upsert",
    "write",
    "write_bytes",
    "write_text",
}
_DISPLAY_METHODS = {"display", "log", "print", "render", "show"}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_archival(path: str) -> bool:
    return path.endswith((".save", ".save.1", ".bak", ".backup")) or "/archive/" in f"/{path.lower()}/"


def _is_test(path: str) -> bool:
    name = Path(path).name
    return path.startswith("tests/") or name.startswith("test_") or name.endswith("_test.py")


def _is_generated_inventory(path: Path) -> bool:
    return path.name.startswith("qdkt-p6-2-inventory")


def _classify(path: str, use_class: QDKTUseClass) -> tuple[QDKTInventoryImpact, QDKTInventoryReadiness]:
    if _is_archival(path):
        return QDKTInventoryImpact.LOW, QDKTInventoryReadiness.ARCHIVAL_ONLY
    if _is_test(path):
        return QDKTInventoryImpact.LOW, QDKTInventoryReadiness.TEST_ONLY
    if use_class is QDKTUseClass.DOCUMENTATION or path.startswith("docs/"):
        return QDKTInventoryImpact.LOW, QDKTInventoryReadiness.DOCUMENTATION_ONLY
    if use_class is QDKTUseClass.GENERATOR_DEFINITION:
        return QDKTInventoryImpact.HIGH, QDKTInventoryReadiness.NO_MIGRATION_REQUIRED
    if use_class in (
        QDKTUseClass.ROOT_CONSUMER,
        QDKTUseClass.BELIEF_CONSUMER,
        QDKTUseClass.PERSISTENCE,
        QDKTUseClass.UNPARSED_REFERENCE,
    ):
        return QDKTInventoryImpact.HIGH, QDKTInventoryReadiness.DUAL_READ_CANDIDATE
    return QDKTInventoryImpact.MEDIUM, QDKTInventoryReadiness.DUAL_READ_CANDIDATE


def _entry(
    path: str,
    symbol: str,
    line: int,
    use_class: QDKTUseClass,
    detail: str,
) -> QDKTInventoryEntry:
    impact, readiness = _classify(path, use_class)
    return QDKTInventoryEntry.create(
        file_path=path,
        symbol=symbol,
        line=max(1, int(line)),
        use_class=use_class,
        impact=impact,
        readiness=readiness,
        detail=detail,
    )


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _name_is_qdkt_constructor(node: ast.AST, aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in aliases
    return isinstance(node, ast.Attribute) and node.attr == "QuantumMerkleDAG"


def _contains_result_reference(node: ast.AST, result_names: set[str]) -> bool:
    return any(isinstance(item, ast.Name) and item.id in result_names for item in ast.walk(node))


def _subscript_key(node: ast.Subscript) -> str:
    value = node.slice
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return ""


def _is_getattr_generator_method(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        return False
    if node.func.id != "getattr" or len(node.args) < 2:
        return False
    name = node.args[1]
    return isinstance(name, ast.Constant) and name.value == "generate_epistemic_system_root"


def _reference_entries(
    text: str,
    relative: str,
    use_class: QDKTUseClass,
    detail_prefix: str,
) -> list[QDKTInventoryEntry]:
    entries: list[QDKTInventoryEntry] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        terms = tuple(term for term in _QDKT_TERMS if term in line)
        if terms:
            entries.append(
                _entry(
                    relative,
                    "<unparsed>" if use_class is QDKTUseClass.UNPARSED_REFERENCE else "<document>",
                    line_number,
                    use_class,
                    f"{detail_prefix}" + ", ".join(terms),
                )
            )
    return entries


class _PythonInventory(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.entries: list[QDKTInventoryEntry] = []
        self.constructor_aliases = {"QuantumMerkleDAG"}
        self.generator_method_aliases: set[str] = set()
        self.result_names: set[str] = {"legacy_result"}
        self.scope: list[str] = ["<module>"]

    @property
    def symbol(self) -> str:
        return ".".join(self.scope)

    def add(self, node: ast.AST, use_class: QDKTUseClass, detail: str) -> None:
        self.entries.append(
            _entry(self.path, self.symbol, getattr(node, "lineno", 1), use_class, detail)
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        if node.name == "QuantumMerkleDAG":
            self.add(node, QDKTUseClass.GENERATOR_DEFINITION, "legacy generator class definition")
        previous_constructors = set(self.constructor_aliases)
        previous_methods = set(self.generator_method_aliases)
        previous_results = set(self.result_names)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()
        self.constructor_aliases = previous_constructors
        self.generator_method_aliases = previous_methods
        self.result_names = previous_results

    def _function_args(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterable[str]:
        arguments = (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
        for argument in arguments:
            yield argument.arg
        if node.args.vararg is not None:
            yield node.args.vararg.arg
        if node.args.kwarg is not None:
            yield node.args.kwarg.arg

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if node.name == "generate_epistemic_system_root":
            self.add(node, QDKTUseClass.GENERATOR_DEFINITION, "legacy result method definition")
        previous_constructors = set(self.constructor_aliases)
        previous_methods = set(self.generator_method_aliases)
        previous_results = set(self.result_names)
        self.result_names.update(
            name for name in self._function_args(node) if "legacy_result" in name.lower()
        )
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()
        self.constructor_aliases = previous_constructors
        self.generator_method_aliases = previous_methods
        self.result_names = previous_results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._visit_function(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.module == "quantum_dag":
            for alias in node.names:
                if alias.name == "QuantumMerkleDAG":
                    local = alias.asname or alias.name
                    self.constructor_aliases.add(local)
                    self.add(
                        node,
                        QDKTUseClass.IMPORT,
                        f"imports QuantumMerkleDAG as {local}",
                    )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            if alias.name == "quantum_dag":
                self.add(node, QDKTUseClass.IMPORT, "imports the legacy quantum_dag module")
        self.generic_visit(node)

    def _assignment_names(self, target: ast.AST) -> Iterable[str]:
        if isinstance(target, ast.Name):
            yield target.id
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                yield from self._assignment_names(item)

    def _is_generator_call(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Await):
            value = value.value
        if not isinstance(value, ast.Call):
            return False
        if isinstance(value.func, ast.Attribute):
            return value.func.attr == "generate_epistemic_system_root"
        return isinstance(value.func, ast.Name) and value.func.id in self.generator_method_aliases

    def _is_constructor_reference(self, value: ast.AST) -> bool:
        return _name_is_qdkt_constructor(value, self.constructor_aliases)

    def _track_assignment(self, target: ast.AST, value: ast.AST) -> None:
        names = tuple(self._assignment_names(target))
        if not names:
            return

        if _is_getattr_generator_method(value):
            self.generator_method_aliases.update(names)
            self.add(
                value,
                QDKTUseClass.METHOD_CALL,
                "resolves generate_epistemic_system_root through a compatibility facade",
            )
        else:
            self.generator_method_aliases.difference_update(names)

        if self._is_constructor_reference(value):
            self.constructor_aliases.update(names)
        else:
            self.constructor_aliases.difference_update(names)

        if self._is_generator_call(value) or _contains_result_reference(value, self.result_names):
            self.result_names.update(names)
        else:
            self.result_names.difference_update(names)

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            self._track_assignment(target, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if node.value is not None:
            self._track_assignment(node.target, node.value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        if _name_is_qdkt_constructor(node.func, self.constructor_aliases):
            self.add(node, QDKTUseClass.CONSTRUCTOR, "constructs the legacy QuantumMerkleDAG")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "generate_epistemic_system_root":
            self.add(node, QDKTUseClass.METHOD_CALL, "invokes the asynchronous legacy result method")
        elif isinstance(node.func, ast.Name) and node.func.id in self.generator_method_aliases:
            self.add(node, QDKTUseClass.METHOD_CALL, "invokes the resolved legacy result method")
        method = _call_name(node)
        if method in _PERSISTENCE_METHODS and any(
            _contains_result_reference(arg, self.result_names) for arg in node.args
        ):
            self.add(node, QDKTUseClass.PERSISTENCE, f"passes a legacy result to {method}")
        if method in _DISPLAY_METHODS and any(
            _contains_result_reference(arg, self.result_names) for arg in node.args
        ):
            self.add(node, QDKTUseClass.DISPLAY, f"passes a legacy result to {method}")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            if isinstance(node.func.value, ast.Name) and node.func.value.id in self.result_names:
                if node.args and isinstance(node.args[0], ast.Constant):
                    key = node.args[0].value
                    if key == "root":
                        self.add(node, QDKTUseClass.ROOT_CONSUMER, "reads legacy_result.get('root')")
                    elif key == "belief":
                        self.add(node, QDKTUseClass.BELIEF_CONSUMER, "reads legacy_result.get('belief')")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        if isinstance(node.value, ast.Name) and node.value.id in self.result_names:
            key = _subscript_key(node)
            if key == "root":
                self.add(node, QDKTUseClass.ROOT_CONSUMER, "reads legacy_result['root']")
            elif key == "belief":
                self.add(node, QDKTUseClass.BELIEF_CONSUMER, "reads legacy_result['belief']")
        self.generic_visit(node)


def _scan_python(path: Path, root: Path) -> list[QDKTInventoryEntry]:
    relative = _relative(path, root)
    try:
        source = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeError:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        return _reference_entries(
            source,
            relative,
            QDKTUseClass.UNPARSED_REFERENCE,
            "non-UTF-8 Python reference to ",
        )
    except OSError:
        return []
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError:
        return _reference_entries(
            source,
            relative,
            QDKTUseClass.UNPARSED_REFERENCE,
            "syntactically unparsed Python reference to ",
        )
    visitor = _PythonInventory(relative)
    visitor.visit(tree)
    entries = visitor.entries
    if entries and _is_test(relative):
        first_line = min(item.line for item in entries)
        entries.append(
            _entry(
                relative,
                "<module>",
                first_line,
                QDKTUseClass.TEST,
                "test or validation surface covering the legacy QDKT result",
            )
        )
    return entries


def _scan_text(path: Path, root: Path) -> list[QDKTInventoryEntry]:
    relative = _relative(path, root)
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeError:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
    except OSError:
        return []
    return _reference_entries(
        text,
        relative,
        QDKTUseClass.DOCUMENTATION,
        "references ",
    )


def _candidate_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink() or not path.is_file() or _is_generated_inventory(path):
            continue
        relative = _relative(path, root)
        relative_parts = Path(relative).parts
        if relative in _EXCLUDED_FILES or any(part in _EXCLUDED_DIRS for part in relative_parts):
            continue
        if path.suffix == ".py" or path.suffix in _TEXT_SUFFIXES or _is_archival(relative):
            yield path


def scan_qdkt_uses(root: str | Path = ".") -> QDKTInventoryReport:
    """Scan current files without importing or executing repository code."""
    base = Path(root).resolve()
    if not base.is_dir():
        raise ValueError("root must identify a directory")
    entries: list[QDKTInventoryEntry] = []
    scanned = 0
    ignored = 0
    for path in _candidate_files(base):
        scanned += 1
        if path.suffix == ".py" or _is_archival(_relative(path, base)):
            found = _scan_python(path, base)
        else:
            found = _scan_text(path, base)
        if not found:
            ignored += 1
        entries.extend(found)
    unique = {item.entry_id: item for item in entries}
    return QDKTInventoryReport(tuple(unique.values()), scanned, ignored)


def write_qdkt_inventory(report: QDKTInventoryReport, output: str | Path) -> Path:
    if not isinstance(report, QDKTInventoryReport):
        raise ValueError("report must be a QDKTInventoryReport")
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(report.to_dict()) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = scan_qdkt_uses(args.root)
    if args.output:
        write_qdkt_inventory(report, args.output)
    else:
        print(canonical_json(report.to_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["scan_qdkt_uses", "write_qdkt_inventory"]

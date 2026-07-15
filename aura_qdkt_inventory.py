"""Topology-backed inventory for legacy QuantumMerkleDAG ownership and callers."""
from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any

from aura_repo_localizer import EXCLUDE_DIRS
from aura_topological_context_anchor import CodeTopoAnchor

QDKT_INVENTORY_VERSION = "AURA_QDKT_INVENTORY_P6_2"
LEGACY_MODULE = "quantum_dag"
LEGACY_CLASS = "QuantumMerkleDAG"
LEGACY_METHOD = "generate_epistemic_system_root"

_TEXT_SUFFIXES = {".py", ".toml", ".md", ".json", ".save"}
_IGNORED_FILES = {
    ".aura/CODEMAP.json",
    ".aura/CODEMAP.md",
    "topology_map.json",
}


class QDKTUseClass(str, Enum):
    DEFINITION_OWNER = "DEFINITION_OWNER"
    RUNTIME_CALL = "RUNTIME_CALL"
    RUNTIME_IMPORT_ONLY = "RUNTIME_IMPORT_ONLY"
    COMPATIBILITY = "COMPATIBILITY"
    TEST = "TEST"
    ARCHIVE = "ARCHIVE"
    PACKAGING = "PACKAGING"
    VERIFICATION_CONFIG = "VERIFICATION_CONFIG"
    DOCUMENTATION = "DOCUMENTATION"


class QDKTMigrationReadiness(str, Enum):
    RETAIN = "RETAIN"
    READY_FOR_SEPARATE_CLEANUP = "READY_FOR_SEPARATE_CLEANUP"
    COMPATIBILITY_EVIDENCE_ONLY = "COMPATIBILITY_EVIDENCE_ONLY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class QDKTOwnershipDisposition(str, Enum):
    RETAIN_LEGACY = "RETAIN_LEGACY"
    BEGIN_SEPARATE_MIGRATION = "BEGIN_SEPARATE_MIGRATION"
    BLOCK_MIGRATION = "BLOCK_MIGRATION"


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="strict")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _normalized(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def _is_test(path: str) -> bool:
    name = Path(path).name
    return path.startswith("tests/") or name.startswith("test_")


def _is_archive(path: str) -> bool:
    lowered = path.lower()
    return path.endswith(".save") or ".save." in lowered or "backup" in lowered


def _is_compatibility(path: str) -> bool:
    name = Path(path).name
    return name.startswith("aura_qdkt_") and name != "aura_qdkt.py"


def _attribute_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _attribute_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


class _LegacyUseVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports_legacy = False
        self.constructs_legacy = False
        self.calls_generator = False
        self.consumes_root = False
        self.consumes_belief = False
        self.spans: list[tuple[int, int]] = []
        self._scope: list[str] = ["<module>"]
        self.symbols: set[str] = set()

    def _mark(self, node: ast.AST) -> None:
        start = int(getattr(node, "lineno", 0) or 0)
        end = int(getattr(node, "end_lineno", start) or start)
        self.spans.append((start, end))
        self.symbols.add(self._scope[-1])

    def visit_Import(self, node: ast.Import) -> Any:
        if any(alias.name == LEGACY_MODULE for alias in node.names):
            self.imports_legacy = True
            self._mark(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.module == LEGACY_MODULE and any(
            alias.name == LEGACY_CLASS for alias in node.names
        ):
            self.imports_legacy = True
            self._mark(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_Call(self, node: ast.Call) -> Any:
        called = _attribute_name(node.func)
        if called in {LEGACY_CLASS, f"{LEGACY_MODULE}.{LEGACY_CLASS}"}:
            self.constructs_legacy = True
            self._mark(node)
        if called.endswith(f".{LEGACY_METHOD}") or called == LEGACY_METHOD:
            self.calls_generator = True
            self._mark(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
            key = node.args[0]
            if isinstance(key, ast.Constant) and key.value in {"root", "belief"}:
                if key.value == "root":
                    self.consumes_root = True
                else:
                    self.consumes_belief = True
                self._mark(node)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        key = node.slice
        if isinstance(key, ast.Constant) and key.value in {"root", "belief"}:
            if key.value == "root":
                self.consumes_root = True
            else:
                self.consumes_belief = True
            self._mark(node)
        self.generic_visit(node)


@dataclass(frozen=True)
class QDKTCallerRecord:
    file_path: str
    symbol: str
    start_line: int
    end_line: int
    source_hash: str
    use_class: QDKTUseClass | str
    imports_legacy: bool
    constructs_legacy: bool
    calls_generator: bool
    consumes_root: bool
    consumes_belief: bool
    live_runtime: bool
    readiness: QDKTMigrationReadiness | str
    note: str

    def __post_init__(self) -> None:
        path = _normalized(self.file_path)
        if not path:
            raise ValueError("file_path must not be empty")
        if type(self.symbol) is not str or not self.symbol:
            raise ValueError("symbol must not be empty")
        if type(self.start_line) is not int or type(self.end_line) is not int:
            raise ValueError("line values must be integers")
        if self.start_line < 0 or self.end_line < self.start_line:
            raise ValueError("line range is invalid")
        if type(self.source_hash) is not str or len(self.source_hash) != 64:
            raise ValueError("source_hash must be a SHA-256 digest")
        try:
            use_class = (
                self.use_class
                if isinstance(self.use_class, QDKTUseClass)
                else QDKTUseClass(str(self.use_class))
            )
            readiness = (
                self.readiness
                if isinstance(self.readiness, QDKTMigrationReadiness)
                else QDKTMigrationReadiness(str(self.readiness))
            )
        except ValueError as exc:
            raise ValueError("caller classification is invalid") from exc
        for field_name in (
            "imports_legacy",
            "constructs_legacy",
            "calls_generator",
            "consumes_root",
            "consumes_belief",
            "live_runtime",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be a boolean")
        if type(self.note) is not str or not self.note.strip():
            raise ValueError("note must not be empty")
        if self.calls_generator and not self.constructs_legacy and not self.imports_legacy:
            if use_class not in {QDKTUseClass.COMPATIBILITY, QDKTUseClass.TEST}:
                raise ValueError("unbound generator call is not classified safely")
        object.__setattr__(self, "file_path", path)
        object.__setattr__(self, "use_class", use_class)
        object.__setattr__(self, "readiness", readiness)
        object.__setattr__(self, "note", self.note.strip())

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["use_class"] = self.use_class.value
        value["readiness"] = self.readiness.value
        return value


@dataclass(frozen=True)
class QDKTCallerInventory:
    records: tuple[QDKTCallerRecord, ...]
    unknown_hits: tuple[str, ...]
    topology_node_count: int
    topology_edge_count: int
    version: str = QDKT_INVENTORY_VERSION

    def __post_init__(self) -> None:
        if not all(isinstance(item, QDKTCallerRecord) for item in self.records):
            raise ValueError("records contains an invalid caller record")
        keys = [(item.file_path, item.symbol, item.start_line, item.use_class.value) for item in self.records]
        if len(keys) != len(set(keys)):
            raise ValueError("caller inventory contains duplicate records")
        if type(self.unknown_hits) is not tuple:
            raise ValueError("unknown_hits must be a tuple")
        if any(type(item) is not str or not item for item in self.unknown_hits):
            raise ValueError("unknown_hits contains an invalid path")
        for field_name in ("topology_node_count", "topology_edge_count"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.version != QDKT_INVENTORY_VERSION:
            raise ValueError("unsupported inventory version")

    @property
    def complete(self) -> bool:
        return not self.unknown_hits

    @property
    def live_runtime_calls(self) -> tuple[QDKTCallerRecord, ...]:
        return tuple(item for item in self.records if item.live_runtime and item.calls_generator)

    @property
    def live_import_only(self) -> tuple[QDKTCallerRecord, ...]:
        return tuple(
            item
            for item in self.records
            if item.live_runtime and item.imports_legacy and not item.calls_generator
        )

    @property
    def digest(self) -> str:
        return _digest_text(_canonical(self.to_dict()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [item.to_dict() for item in self.records],
            "unknown_hits": list(self.unknown_hits),
            "topology_node_count": self.topology_node_count,
            "topology_edge_count": self.topology_edge_count,
            "version": self.version,
            "complete": self.complete,
        }


@dataclass(frozen=True)
class QDKTOwnershipDecision:
    disposition: QDKTOwnershipDisposition | str
    reason: str
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]
    inventory_digest: str
    version: str = QDKT_INVENTORY_VERSION

    def __post_init__(self) -> None:
        try:
            disposition = (
                self.disposition
                if isinstance(self.disposition, QDKTOwnershipDisposition)
                else QDKTOwnershipDisposition(str(self.disposition))
            )
        except ValueError as exc:
            raise ValueError("ownership disposition is invalid") from exc
        if type(self.reason) is not str or not self.reason.strip():
            raise ValueError("reason must not be empty")
        if type(self.blockers) is not tuple or not self.blockers:
            raise ValueError("blockers must be a non-empty tuple")
        if type(self.evidence) is not tuple or not self.evidence:
            raise ValueError("evidence must be a non-empty tuple")
        if any(type(item) is not str or not item for item in self.blockers + self.evidence):
            raise ValueError("ownership evidence contains an invalid value")
        if type(self.inventory_digest) is not str or len(self.inventory_digest) != 64:
            raise ValueError("inventory_digest must be a SHA-256 digest")
        if self.version != QDKT_INVENTORY_VERSION:
            raise ValueError("unsupported ownership decision version")
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "reason", self.reason.strip())

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["disposition"] = self.disposition.value
        return value


def _classify(path: str, visitor: _LegacyUseVisitor, source: str) -> tuple[QDKTUseClass, bool, QDKTMigrationReadiness, str]:
    if path == "quantum_dag.py":
        return (
            QDKTUseClass.DEFINITION_OWNER,
            True,
            QDKTMigrationReadiness.RETAIN,
            "unchanged legacy result owner",
        )
    if _is_archive(path):
        return (
            QDKTUseClass.ARCHIVE,
            False,
            QDKTMigrationReadiness.NOT_APPLICABLE,
            "archival snapshot is not a live caller",
        )
    if _is_test(path):
        return (
            QDKTUseClass.TEST,
            False,
            QDKTMigrationReadiness.NOT_APPLICABLE,
            "test or fixture reference",
        )
    if _is_compatibility(path):
        return (
            QDKTUseClass.COMPATIBILITY,
            False,
            QDKTMigrationReadiness.COMPATIBILITY_EVIDENCE_ONLY,
            "additive compatibility evidence surface",
        )
    if path == "pyproject.toml":
        return (
            QDKTUseClass.PACKAGING,
            False,
            QDKTMigrationReadiness.RETAIN,
            "module remains part of the packaged compatibility surface",
        )
    if path == "verify_os.py":
        return (
            QDKTUseClass.VERIFICATION_CONFIG,
            False,
            QDKTMigrationReadiness.RETAIN,
            "repository verification still requires the legacy module",
        )
    if path.endswith(".md") or path.startswith("docs/"):
        return (
            QDKTUseClass.DOCUMENTATION,
            False,
            QDKTMigrationReadiness.NOT_APPLICABLE,
            "documentation reference",
        )
    if visitor.calls_generator or visitor.constructs_legacy:
        return (
            QDKTUseClass.RUNTIME_CALL,
            True,
            QDKTMigrationReadiness.RETAIN,
            "live runtime construction or generator call",
        )
    if visitor.imports_legacy:
        return (
            QDKTUseClass.RUNTIME_IMPORT_ONLY,
            True,
            QDKTMigrationReadiness.READY_FOR_SEPARATE_CLEANUP,
            "live import with no generator call proven",
        )
    if LEGACY_CLASS in source or LEGACY_METHOD in source or LEGACY_MODULE in source:
        return (
            QDKTUseClass.COMPATIBILITY,
            False,
            QDKTMigrationReadiness.COMPATIBILITY_EVIDENCE_ONLY,
            "non-calling compatibility reference",
        )
    raise ValueError("unclassified legacy QDKT reference")


def build_qdkt_inventory(files: Mapping[str, str]) -> QDKTCallerInventory:
    normalized_files = {
        _normalized(path): source
        for path, source in files.items()
        if _normalized(path) not in _IGNORED_FILES
    }
    python_files = {
        path: source for path, source in normalized_files.items() if path.endswith(".py")
    }
    anchor = CodeTopoAnchor.build_from_files(python_files)
    records: list[QDKTCallerRecord] = []
    unknown: list[str] = []

    for path, source in sorted(normalized_files.items()):
        if not any(token in source for token in (LEGACY_MODULE, LEGACY_CLASS, LEGACY_METHOD)):
            continue
        visitor = _LegacyUseVisitor()
        if path.endswith(".py"):
            try:
                visitor.visit(ast.parse(source, filename=path))
            except SyntaxError:
                unknown.append(path)
                continue
        try:
            use_class, live_runtime, readiness, note = _classify(path, visitor, source)
        except ValueError:
            unknown.append(path)
            continue
        spans = visitor.spans or [(0, 0)]
        symbols = sorted(visitor.symbols) or ["<file>"]
        start = min(item[0] for item in spans)
        end = max(item[1] for item in spans)
        symbol = ",".join(symbols)
        records.append(
            QDKTCallerRecord(
                file_path=path,
                symbol=symbol,
                start_line=start,
                end_line=end,
                source_hash=_digest_text(source),
                use_class=use_class,
                imports_legacy=visitor.imports_legacy,
                constructs_legacy=visitor.constructs_legacy,
                calls_generator=visitor.calls_generator,
                consumes_root=visitor.consumes_root,
                consumes_belief=visitor.consumes_belief,
                live_runtime=live_runtime,
                readiness=readiness,
                note=note,
            )
        )

    return QDKTCallerInventory(
        records=tuple(sorted(records, key=lambda item: (item.file_path, item.start_line, item.symbol))),
        unknown_hits=tuple(sorted(set(unknown))),
        topology_node_count=len(anchor.nodes),
        topology_edge_count=len(anchor.edges),
    )


def build_qdkt_inventory_from_repo(repo_root: str | Path) -> QDKTCallerInventory:
    root = Path(repo_root).resolve()
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        normalized = relative.as_posix()
        if normalized in _IGNORED_FILES:
            continue
        suffix = path.suffix.lower()
        if suffix not in _TEXT_SUFFIXES and not normalized.endswith((".save", ".save.1")):
            continue
        try:
            files[normalized] = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError):
            continue
    return build_qdkt_inventory(files)


def p6_2_ownership_decision(inventory: QDKTCallerInventory) -> QDKTOwnershipDecision:
    if not inventory.complete:
        return QDKTOwnershipDecision(
            disposition=QDKTOwnershipDisposition.BLOCK_MIGRATION,
            reason="unclassified legacy QDKT references remain",
            blockers=("unknown_inventory_hits",),
            evidence=(f"unknown_count:{len(inventory.unknown_hits)}",),
            inventory_digest=inventory.digest,
        )
    if inventory.live_runtime_calls:
        return QDKTOwnershipDecision(
            disposition=QDKTOwnershipDisposition.RETAIN_LEGACY,
            reason="live generator callers still depend on legacy ownership",
            blockers=("live_runtime_generator_callers",),
            evidence=(f"live_call_count:{len(inventory.live_runtime_calls)}",),
            inventory_digest=inventory.digest,
        )
    return QDKTOwnershipDecision(
        disposition=QDKTOwnershipDisposition.RETAIN_LEGACY,
        reason="no live generator caller is proven, but import, packaging, and verification compatibility remain",
        blockers=("import_or_package_compatibility_remains",),
        evidence=(
            f"live_call_count:{len(inventory.live_runtime_calls)}",
            f"live_import_only_count:{len(inventory.live_import_only)}",
            "legacy_owner_unchanged",
        ),
        inventory_digest=inventory.digest,
    )


def main() -> int:
    inventory = build_qdkt_inventory_from_repo(Path.cwd())
    payload = {
        "inventory": inventory.to_dict(),
        "ownership_decision": p6_2_ownership_decision(inventory).to_dict(),
    }
    print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if inventory.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())

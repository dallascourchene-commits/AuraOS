"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c3-[Q-SYS:REPO_LOCALIZER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Deterministic Fault Localization)
DEPENDENCIES: ast, dataclasses, json, pathlib, re, typing
FUNCTIONS: LocalizedFile, parse_traceback_targets, ast_symbol_index, localize_fault, run_agentless_fallback
SYNOPSIS: Analyzes the intent and repo structure deterministically without LLM queries
to localize target files. Used as the Agentless-style fallback loop when Council debate fails.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any


EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "Aura_Memory",
    "Aura_Sandbox",
    "node_modules",
    "venv",
    ".venv",
    "ojibwemorph_release",
}

GENERATED_HINTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".bak",
    ".save",
    "backup",
    "generated",
    "Aura_Memory",
}


@dataclass
class LocalizedFile:
    path: str
    score: float
    reasons: list[str]
    symbols: list[str]
    tests: list[str]


def _normalize_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def _repo_relative(path: str, root: Path) -> str:
    normalized = _normalize_path(path.strip())
    candidate = Path(normalized)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root).as_posix()
        except Exception:
            return candidate.name
    return normalized


def _load_codemap(root: Path) -> dict[str, Any] | None:
    codemap_path = root / ".aura" / "CODEMAP.json"
    if not codemap_path.exists():
        return None
    try:
        data = json.loads(codemap_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _codemap_file_entries(codemap: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not codemap:
        return []
    entries: list[dict[str, Any]] = []
    for key in ("files", "file_cards"):
        raw = codemap.get(key)
        if isinstance(raw, list):
            entries.extend(item for item in raw if isinstance(item, dict) and item.get("path"))
    return entries


def _tokenize_intent(intent: str) -> set[str]:
    words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", intent.lower())
    stopwords = {
        "with",
        "from",
        "that",
        "this",
        "files",
        "class",
        "function",
        "patch",
        "stage",
        "loop",
        "error",
        "issue",
        "failure",
        "fail",
        "traceback",
        "file",
        "line",
    }
    return {word for word in words if word not in stopwords}


def parse_traceback_targets(text: str) -> list[str]:
    """Extract Python file targets from tracebacks or traceback-like text."""
    targets: list[str] = []
    seen: set[str] = set()
    patterns = [
        r'File "([^"]+\.py)", line \d+',
        r"File '([^']+\.py)', line \d+",
        r"(?<![\w./\\-])([\w./\\-]+\.py):\d+",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text):
            normalized = _normalize_path(match)
            if normalized not in seen:
                targets.append(normalized)
                seen.add(normalized)
    return targets


def ast_symbol_index(repo_root: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Build a deterministic AST symbol index without relying on CODEMAP."""
    root = Path(repo_root).resolve()
    index: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(root.glob("**/*.py")):
        relative = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                index.setdefault(node.name, []).append(
                    {
                        "file": relative.as_posix(),
                        "kind": kind,
                        "line": getattr(node, "lineno", 0),
                        "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                    }
                )
    return index


def _tests_for_file(path: str, root: Path, file_entry: dict[str, Any] | None = None) -> list[str]:
    tests: list[str] = []
    relative = Path(path)
    direct = relative.parent / f"test_{relative.name}"
    if (root / direct).exists():
        tests.append(direct.as_posix())
    test_file = file_entry.get("test_file") if file_entry else None
    if isinstance(test_file, str) and (root / test_file).exists():
        tests.append(_normalize_path(test_file))
    topology = file_entry.get("topology", {}) if file_entry else {}
    if isinstance(topology, dict):
        for neighbor in topology.get("neighbor_files", []) or []:
            neighbor_path = _normalize_path(neighbor)
            if ("test_" in Path(neighbor_path).name or "/test_" in neighbor_path) and (root / neighbor_path).exists():
                tests.append(neighbor_path)
    return sorted(set(tests))


def _generated_penalty(path: str) -> float:
    lowered = path.lower()
    return -12.0 if any(hint.lower() in lowered for hint in GENERATED_HINTS) else 0.0


def _add_match(matches: dict[str, LocalizedFile], path: str, score: float, reason: str, *, symbol: str = "", tests: list[str] | None = None) -> None:
    path = _normalize_path(path)
    item = matches.get(path)
    if item is None:
        item = LocalizedFile(path=path, score=0.0, reasons=[], symbols=[], tests=[])
        matches[path] = item
    item.score += score
    if reason and reason not in item.reasons:
        item.reasons.append(reason)
    if symbol and symbol not in item.symbols:
        item.symbols.append(symbol)
    for test in tests or []:
        if test not in item.tests:
            item.tests.append(test)


def localize_fault(intent: str, repo_root: str | Path) -> list[LocalizedFile]:
    """
    Deterministically rank up to five likely repair target files.

    Scoring blends traceback targets, CODEMAP file/symbol evidence, AST fallback
    symbols, import-neighbor proximity, nearby tests, and generated-file penalties.
    """
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)
    file_entries = _codemap_file_entries(codemap)
    entry_by_path = {_normalize_path(entry.get("path", "")): entry for entry in file_entries}
    if not file_entries:
        for path in sorted(root.glob("**/*.py")):
            relative = path.relative_to(root)
            if any(part in EXCLUDE_DIRS for part in relative.parts):
                continue
            entry_by_path[relative.as_posix()] = {"path": relative.as_posix()}

    keywords = _tokenize_intent(intent)
    lowered_intent = intent.lower()
    traceback_targets = [_repo_relative(target, root) for target in parse_traceback_targets(intent)]
    matches: dict[str, LocalizedFile] = {}

    for path, entry in entry_by_path.items():
        if not path.endswith(".py"):
            continue
        if not (root / path).exists():
            continue
        tests = _tests_for_file(path, root, entry)
        score = _generated_penalty(path)
        reasons: list[str] = []
        lowered_path = path.lower()
        if any(path.endswith(target) or target.endswith(path) for target in traceback_targets):
            score += 30.0
            reasons.append("traceback_target")
        if path.lower() in lowered_intent:
            score += 14.0
            reasons.append(f"exact_path_match:{path}")
        for keyword in keywords:
            if keyword in lowered_path:
                score += 5.0
                reasons.append(f"path_keyword:{keyword}")
        synopsis = str(entry.get("synopsis") or entry.get("description") or entry.get("role") or "")
        for keyword in keywords:
            if keyword in synopsis.lower():
                score += 1.0
                reasons.append(f"codemap_text:{keyword}")
        if tests:
            score += 1.0
            reasons.append("nearby_tests")
        if score > 0:
            for reason in reasons:
                _add_match(matches, path, score if reason == reasons[0] else 0.0, reason, tests=tests)

    symbol_index: dict[str, list[dict[str, Any]]] = {}
    if codemap and isinstance(codemap.get("symbol_index"), dict):
        symbol_index = codemap["symbol_index"]
    else:
        symbol_index = ast_symbol_index(root)
    for symbol_name, occurrences in symbol_index.items():
        if symbol_name.lower() not in lowered_intent and symbol_name.lower() not in keywords:
            continue
        if not isinstance(occurrences, list):
            continue
        for occurrence in occurrences:
            file_path = _normalize_path(occurrence.get("file") or occurrence.get("path") or "")
            if not file_path or not file_path.endswith(".py"):
                continue
            if not (root / file_path).exists():
                continue
            _add_match(
                matches,
                file_path,
                11.0,
                f"symbol_match:{symbol_name}",
                symbol=symbol_name,
                tests=_tests_for_file(file_path, root, entry_by_path.get(file_path, {})),
            )

    scored_paths = [path for path, item in matches.items() if item.score > 0]
    for path in scored_paths:
        entry = entry_by_path.get(path, {})
        topology = entry.get("topology", {}) if isinstance(entry, dict) else {}
        neighbors = topology.get("neighbor_files", []) if isinstance(topology, dict) else []
        for neighbor in neighbors or []:
            neighbor_path = _normalize_path(neighbor)
            if neighbor_path.endswith(".py") and neighbor_path in entry_by_path and (root / neighbor_path).exists():
                _add_match(
                    matches,
                    neighbor_path,
                    2.0,
                    f"neighbor:{path}",
                    tests=_tests_for_file(neighbor_path, root, entry_by_path.get(neighbor_path, {})),
                )

    for item in matches.values():
        item.score += _generated_penalty(item.path)
        item.reasons = item.reasons[:8]
        item.symbols = sorted(set(item.symbols))[:8]
        item.tests = sorted(set(test for test in item.tests if (root / test).exists()))[:5]

    ranked = sorted(
        (item for item in matches.values() if item.score > 0),
        key=lambda item: (-item.score, item.path),
    )
    return ranked[:5]


def run_agentless_fallback(intent: str, repo_root: str | Path) -> dict[str, Any]:
    """Generate a structured fallback Act Capsule evidence packet when Council fails."""
    files = localize_fault(intent, repo_root)
    if not files:
        return {
            "ok": False,
            "message": "Localizer could not identify any candidate files.",
            "localized_files": [],
        }
    return {
        "ok": True,
        "localized_files": [asdict(item) for item in files],
        "suggested_task_id": "fallback_localize_repair",
        "objective": f"Resolve following issue: {intent} in {', '.join(item.path for item in files)}",
    }

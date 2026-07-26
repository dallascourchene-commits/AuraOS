"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c0-[Q-SYS:MODULE_MANIFEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Active Constraint / No Hallucinated Modules)
DEPENDENCIES: ast, hashlib, json, pathlib, __future__, typing
FUNCTIONS: generate_module_manifest, load_module_manifest, summarize_module_manifest, inject_manifest_constraint, module_exists, symbol_exists
SYNOPSIS: Generates .aura/MODULE_MANIFEST.json from the actual repo tree.
Provides a compact active constraint injected before Council runs.
Prevents planners from referencing modules that do not exist.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from hashlib import blake2b
import json
from pathlib import Path
from typing import Any


HIGH_PRIORITY_MODULES = [
    "aura_live_architect.py",
    "aura_architect_loop.py",
    "aura_node.py",
    "arxiv_forager.py",
    "aura_module_manifest.py",
    "aura_repo_localizer.py",
    "aura_repair_kg.py",
    "aura_hotswap_refactor.py",
    "aura_harness_evolver.py",
    "aura_test_selector.py",
]

EXCLUDE_DIRS = {
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    ".git",
    "Aura_Memory",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "Aura_Sandbox",
    "ojibwemorph_release",
    "travel_extractors",
}


def _normalize_manifest_path(path: str | Path) -> str:
    normalized = Path(str(path).replace("\\", "/")).as_posix()
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _manifest_hash(manifest: dict[str, Any]) -> str:
    return blake2b(
        json.dumps(manifest, sort_keys=True, default=str).encode("utf-8"),
        digest_size=8,
    ).hexdigest()


def generate_module_manifest(repo_root: str | Path) -> dict[str, Any]:
    """Scan the repository and generate the module manifest dict."""
    root = Path(repo_root).resolve()
    manifest: dict[str, Any] = {
        "manifest_version": "1.0",
        "modules": [],
    }

    for path in sorted(root.glob("**/*.py")):
        relative = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        if relative.name.startswith("test_") or relative.name.startswith("setup"):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)

            public_symbols: list[str] = []
            imports: list[str] = []

            has_all = False
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if not (isinstance(target, ast.Name) and target.id == "__all__"):
                        continue
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        try:
                            public_symbols = [str(ast.literal_eval(elt)) for elt in node.value.elts]
                            has_all = True
                        except Exception:
                            public_symbols = []

            if not has_all:
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if not node.name.startswith("_"):
                            public_symbols.append(node.name)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)

            test_file = f"test_{relative.name}"
            test_path = root / relative.parent / test_file
            has_test = test_path.exists()

            manifest["modules"].append(
                {
                    "path": relative.as_posix(),
                    "public_symbols": public_symbols,
                    "imports": sorted(set(imports)),
                    "test_file": relative.parent.joinpath(test_file).as_posix() if has_test else None,
                    "hotswap_risk": "high" if "threading" in content or "asyncio" in content else "low",
                }
            )
        except Exception:
            continue

    return manifest


def load_module_manifest(
    repo_root: str | Path,
    *,
    persist_if_missing: bool = True,
) -> dict[str, Any] | None:
    """Load the manifest, optionally generating a missing manifest in memory only.

    Read-only callers fail closed when an existing manifest is unreadable or invalid
    so they cannot report malformed evidence as a successful empty manifest. Legacy
    persistence callers retain the prior graceful ``None`` behavior.
    """
    root = Path(repo_root).resolve()
    manifest_path = root / ".aura" / "MODULE_MANIFEST.json"
    if not manifest_path.exists():
        manifest = generate_module_manifest(root)
        if persist_if_missing:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("module manifest must be a JSON object")
        return manifest
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        if not persist_if_missing:
            raise
        return None


def summarize_module_manifest(manifest: dict[str, Any], *, max_modules: int = 40) -> dict[str, Any]:
    """Return a compact deterministic summary suitable for prompt constraints."""
    modules = manifest.get("modules", []) or []
    paths = [_normalize_manifest_path(item.get("path", "")) for item in modules if item.get("path")]
    path_set = set(paths)
    prioritized = [path for path in HIGH_PRIORITY_MODULES if path in path_set]
    prioritized_set = set(prioritized)
    remaining = [path for path in paths if path not in prioritized_set]
    known = [*prioritized, *remaining[: max(0, max_modules - len(prioritized))]]
    return {
        "manifest_hash": _manifest_hash(manifest),
        "module_count": len(paths),
        "known_high_priority_modules": known[:max_modules],
        "omitted_count": max(0, len(paths) - min(len(paths), max_modules)),
    }


def module_exists(manifest: dict[str, Any], path: str) -> bool:
    """Return True when *path* is declared in MODULE_MANIFEST."""
    target = _normalize_manifest_path(path)
    for module in manifest.get("modules", []) or []:
        if _normalize_manifest_path(module.get("path", "")) == target:
            return True
    return False


def symbol_exists(manifest: dict[str, Any], path: str, symbol: str) -> bool:
    """Return True when *symbol* is exported by the declared module path."""
    target = _normalize_manifest_path(path)
    for module in manifest.get("modules", []) or []:
        if _normalize_manifest_path(module.get("path", "")) != target:
            continue
        symbols = module.get("public_symbols", []) or module.get("symbols", []) or []
        return str(symbol) in {str(item) for item in symbols}
    return False


def inject_manifest_constraint(repo_root: str | Path) -> str:
    """Get the active manifest constraint string for LLM prompts."""
    manifest = load_module_manifest(repo_root)
    if not manifest or not manifest.get("modules"):
        return ""

    summary = summarize_module_manifest(manifest)
    module_lines = "\n".join(f"- {path}" for path in summary["known_high_priority_modules"])
    return (
        "\n[MODULE_MANIFEST - ENFORCED]\n"
        f"manifest_hash: {summary['manifest_hash']}\n"
        f"module_count: {summary['module_count']}\n"
        "known_high_priority_modules:\n"
        f"{module_lines}\n"
        "RULES:\n"
        "1. You may only reference files present in MODULE_MANIFEST.\n"
        "2. Creating a new module requires a declared Act Capsule for that file.\n"
        "3. Do not invent imports, symbols, or file paths.\n"
        "[/MODULE_MANIFEST]\n"
    )

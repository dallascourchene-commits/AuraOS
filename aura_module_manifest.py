"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c0-[Q-SYS:MODULE_MANIFEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Active Constraint / No Hallucinated Modules)
DEPENDENCIES: ast, json, pathlib, __future__, typing
FUNCTIONS: generate_module_manifest, load_module_manifest, inject_manifest_constraint
SYNOPSIS: Generates .aura/MODULE_MANIFEST.json from the actual repo tree.
Provides a compact (<=400 token) active constraint injected before Council runs.
Prevents planners from referencing modules that do not exist.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def generate_module_manifest(repo_root: str | Path) -> dict[str, Any]:
    """Scan the repository and generate the module manifest dict."""
    root = Path(repo_root).resolve()
    manifest = {
        "manifest_version": "1.0",
        "modules": []
    }
    
    # Gather all Python files (excluding virtual environments, caches, tests, etc.)
    exclude_dirs = {
        "venv", ".venv", "node_modules", "__pycache__", ".git", 
        "Aura_Memory", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        "Aura_Sandbox", "ojibwemorph_release", "travel_extractors"
    }
    
    for path in root.glob("**/*.py"):
        # Check if any parent directory is in exclude_dirs
        relative = path.relative_to(root)
        if any(part in exclude_dirs for part in relative.parts):
            continue
        if relative.name.startswith("test_") or relative.name.startswith("setup"):
            continue
            
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
            
            public_symbols = []
            imports = []
            
            # Check for __all__ definition first
            has_all = False
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            if isinstance(node.value, (ast.List, ast.Tuple)):
                                public_symbols = [str(ast.literal_eval(elt)) for elt in node.value.elts]
                                has_all = True
                                
            # If no __all__, scan functions and classes
            if not has_all:
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if not node.name.startswith("_"):
                            public_symbols.append(node.name)
                            
            # Scan imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
            # Find a matching test file if it exists
            test_file = f"test_{relative.name}"
            test_path = root / relative.parent / test_file
            has_test = test_path.exists()
            
            manifest["modules"].append({
                "path": relative.as_posix(),
                "public_symbols": public_symbols[:10], # Limit to avoid manifest bloat
                "imports": list(set(imports))[:10],
                "test_file": relative.parent.joinpath(test_file).as_posix() if has_test else None,
                "hotswap_risk": "high" if "threading" in content or "asyncio" in content else "low"
            })
            
        except Exception:
            # Skip invalid syntax files
            continue
            
    return manifest


def load_module_manifest(repo_root: str | Path) -> dict[str, Any] | None:
    """Load the manifest, generating it if it doesn't exist."""
    root = Path(repo_root).resolve()
    manifest_path = root / ".aura" / "MODULE_MANIFEST.json"
    if not manifest_path.exists():
        manifest = generate_module_manifest(root)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def inject_manifest_constraint(repo_root: str | Path) -> str:
    """Get the active manifest constraint string for LLM prompts."""
    manifest = load_module_manifest(repo_root)
    if not manifest or not manifest.get("modules"):
        return ""
        
    known_paths = [m["path"] for m in manifest["modules"]]
    return (
        "\n[MODULE_MANIFEST — ENFORCED]\n"
        f"Known modules: {', '.join(known_paths)}\n"
        "RULE: You may ONLY reference modules in this list. Creating new modules requires a separate Act Capsule.\n"
        "[/MODULE_MANIFEST]\n"
    )

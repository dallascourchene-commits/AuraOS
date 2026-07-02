"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c3-[Q-SYS:REPO_LOCALIZER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Deterministic Fault Localization)
DEPENDENCIES: json, pathlib, re, typing
FUNCTIONS: localize_fault, run_agentless_fallback
SYNOPSIS: Analyzes the intent and traces repo structure deterministically without LLM queries
to localize target files. Used as the Agentless-style fallback loop when Council debate fails.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


def localize_fault(intent: str, repo_root: str | Path) -> list[str]:
    """
    Search the repository to find the most relevant files based on intent keyword matching.
    Returns a sorted list of up to 5 matching relative file paths.
    """
    root = Path(repo_root).resolve()
    
    # Extract keywords from intent
    words = re.findall(r"\b[a-zA-Z_]{4,}\b", intent.lower())
    # Exclude common stop words
    stopwords = {"with", "from", "that", "this", "files", "class", "function", "patch", "stage", "loop", "error", "issue", "failure", "fail"}
    keywords = {w for w in words if w not in stopwords}
    
    # Load CODEMAP if available
    codemap_path = root / ".aura" / "CODEMAP.json"
    codemap = None
    if codemap_path.exists():
        try:
            codemap = json.loads(codemap_path.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    matches: dict[str, float] = {}
    
    # 1. First scan CODEMAP file names and descriptions if available
    if codemap and "files" in codemap:
        for item in codemap["files"]:
            path_str = item.get("path", "")
            if not path_str:
                continue
            score = 0.0
            
            # Match keywords against path
            for kw in keywords:
                if kw in path_str.lower():
                    score += 5.0
                    
            # Match keywords against file synopsis/description
            synopsis = item.get("synopsis", "") or item.get("description", "")
            if synopsis:
                for kw in keywords:
                    if kw in synopsis.lower():
                        score += 1.0
                        
            if score > 0:
                matches[path_str] = score
                
    # 2. If CODEMAP is missing or yielded nothing, search the filesystem
    if not matches:
        exclude_dirs = {
            "venv", ".venv", "node_modules", "__pycache__", ".git", 
            "Aura_Memory", ".pytest_cache", ".mypy_cache", ".ruff_cache",
            "Aura_Sandbox", "ojibwemorph_release"
        }
        for path in root.glob("**/*.py"):
            relative = path.relative_to(root)
            if any(part in exclude_dirs for part in relative.parts):
                continue
            path_str = relative.as_posix()
            score = 0.0
            for kw in keywords:
                if kw in path_str.lower():
                    score += 1.0
            if score > 0:
                matches[path_str] = score
                
    # Sort files by match score
    sorted_files = sorted(matches.items(), key=lambda x: x[1], reverse=True)
    return [path for path, score in sorted_files[:5]]


def run_agentless_fallback(intent: str, repo_root: str | Path) -> dict[str, Any]:
    """Generate a minimal fallback Act Capsule when Council fails."""
    files = localize_fault(intent, repo_root)
    if not files:
        return {
            "ok": False,
            "message": "Localizer could not identify any candidate files."
        }
    return {
        "ok": True,
        "localized_files": files,
        "suggested_task_id": "fallback_localize_repair",
        "objective": f"Resolve following issue: {intent} in {', '.join(files)}"
    }

"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGIIN (Low-token, High-context AI Navigation)
DEPENDENCIES: json, re, pathlib, generate_ai_router
FUNCTIONS: load_router_index, query_router, ai_route_command, get_router_context_for_func
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

aura_ai_router.py – Query the AI Router for targeted LLM context.
==================================================================

Provides functions to query AURA_AI_ROUTER.md and return the minimal
file + function context an LLM needs for a given task. This dramatically
reduces token usage by giving agents only the relevant excerpt instead
of entire files.

REPL command: !ai_route <task description>
  Returns JSON with primary file, secondary files, and key functions.

Public API:
  query_router(task_description)      → dict with routing info
  get_router_context_for_func(file, func) → str with minimal context
  ai_route_command(node, args)        → str for REPL display
"""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

ROUTER_PATH = Path("AURA_AI_ROUTER.md")
_INDEX_CACHE: Optional[Dict[str, Any]] = None
_INDEX_MTIME: float = 0.0


# ── Index loader ──────────────────────────────────────────────────────────────

def load_router_index(force_reload: bool = False) -> Dict[str, Any]:
    """
    Parse AURA_AI_ROUTER.md into a structured dict. Results are cached in
    memory and invalidated when the file's mtime changes.

    Returns:
        {
          "tasks": {task_str: {"primary": str, "secondary": [...], "key_functions": [...]}},
          "files": {filename: {"purpose": str, "dependencies": [...], "functions": [...]}},
        }
    """
    global _INDEX_CACHE, _INDEX_MTIME

    if not ROUTER_PATH.exists():
        return {"tasks": {}, "files": {}}

    mtime = ROUTER_PATH.stat().st_mtime
    if not force_reload and _INDEX_CACHE is not None and mtime == _INDEX_MTIME:
        return _INDEX_CACHE

    result: Dict[str, Any] = {"tasks": {}, "files": {}}

    with open(ROUTER_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # ── Parse Task → File Mapping table ──────────────────────────────────────
    task_section = re.search(
        r"## Task → File Mapping\n(.*?)(?=\n## |\Z)", content, re.DOTALL
    )
    if task_section:
        table = task_section.group(1)
        for line in table.strip().split("\n"):
            if not line.startswith("|") or line.startswith("|--"):
                continue
            parts = [p.strip().strip("`") for p in line.split("|")[1:-1]]
            if len(parts) >= 4:
                task = parts[0]
                primary = parts[1]
                secondary = [s.strip().strip("`") for s in parts[2].split(",") if s.strip()]
                functions = [f.strip().strip("`") for f in parts[3].split(",") if f.strip()]
                result["tasks"][task] = {
                    "primary": primary,
                    "secondary": secondary,
                    "key_functions": functions,
                }

    # ── Parse File Index sections ─────────────────────────────────────────────
    file_sections = re.finditer(
        r"### `([^`]+)`\n(.*?)(?=\n### |\n## |\Z)", content, re.DOTALL
    )
    for m in file_sections:
        filename = m.group(1)
        body = m.group(2)
        info: Dict[str, Any] = {"purpose": "", "dependencies": [], "functions": []}
        purpose_m = re.search(r"\*\*Purpose\*\*:\s*(.+)", body)
        if purpose_m:
            info["purpose"] = purpose_m.group(1).strip()
        deps_m = re.search(r"\*\*Dependencies\*\*:\s*(.+)", body)
        if deps_m and "_auto" not in deps_m.group(1):
            info["dependencies"] = [d.strip().strip("`") for d in deps_m.group(1).split(",")]
        funcs = re.findall(r"-\s*`([^`]+)`", body)
        info["functions"] = [f.rstrip("()") for f in funcs]
        result["files"][filename] = info

    _INDEX_CACHE = result
    _INDEX_MTIME = mtime
    return result


# ── Query router ──────────────────────────────────────────────────────────────

def query_router(task_description: str) -> Dict[str, Any]:
    """
    Return routing info for a natural-language task description.

    Scoring: counts how many words in the task_description appear in each
    registered task key (case-insensitive). Falls back to a partial substring
    match if keyword scoring finds nothing.

    Returns:
        On success:
          {"status": "found", "task": str, "primary_file": str,
           "secondary_files": [...], "key_functions": [...],
           "confidence": float}
        On failure:
          {"status": "not_found", "task": str,
           "available_tasks": [...]}
    """
    idx = load_router_index()
    tasks = idx.get("tasks", {})

    if not tasks:
        return {
            "status": "not_found",
            "task": task_description,
            "available_tasks": [],
            "hint": "Run !topology or python3 generate_ai_router.py first.",
        }

    task_lower = task_description.lower()
    query_words = set(task_lower.split())

    best_task: Optional[str] = None
    best_score: float = 0.0

    for task_key in tasks:
        key_words = set(task_key.lower().split())
        # Word overlap score
        overlap = len(query_words & key_words)
        # Normalised by max possible overlap (union)
        union = len(query_words | key_words)
        score = overlap / max(union, 1)
        if score > best_score:
            best_score = score
            best_task = task_key

    # Fallback: substring containment
    if best_score == 0:
        for task_key in tasks:
            if task_key.lower() in task_lower or task_lower in task_key.lower():
                best_task = task_key
                best_score = 0.3
                break

    if best_task and best_score > 0:
        info = tasks[best_task]
        return {
            "status": "found",
            "task": best_task,
            "primary_file": info["primary"],
            "secondary_files": info["secondary"],
            "key_functions": info["key_functions"],
            "confidence": round(best_score, 3),
        }

    return {
        "status": "not_found",
        "task": task_description,
        "available_tasks": list(tasks.keys()),
    }


# ── Context extractor ─────────────────────────────────────────────────────────

def get_router_context_for_func(filepath: str, func_name: str,
                                 context_lines: int = 60) -> str:
    """
    Extract a minimal code context for a specific function from a file.

    Returns a string containing:
      - The PSML header (purpose + dependencies) from the router index
      - The function's source code (up to context_lines lines)

    This is what you pass as `router_context` to ExternalLLM.generate().
    """
    idx = load_router_index()
    file_info = idx.get("files", {}).get(filepath, {})

    header_lines: List[str] = []
    if file_info.get("purpose"):
        header_lines.append(f"# {filepath}")
        header_lines.append(f"# Purpose: {file_info['purpose']}")
    if file_info.get("dependencies"):
        header_lines.append(f"# Dependencies: {', '.join(file_info['dependencies'])}")
    header_lines.append("")

    # Extract the function source via AST
    func_src = _extract_function_source(filepath, func_name, max_lines=context_lines)
    if func_src:
        header_lines.append(func_src)
    else:
        header_lines.append(f"# WARNING: function '{func_name}' not found in {filepath}")

    return "\n".join(header_lines)


def _extract_function_source(filepath: str, func_name: str,
                              max_lines: int = 60) -> Optional[str]:
    """
    Return the source text of `func_name` in `filepath`, capped at max_lines.
    Uses ast.get_source_segment if available (Python 3.8+), else line slicing.
    """
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        lines = source.splitlines()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == func_name:
                    start = node.lineno - 1          # 0-indexed
                    end = getattr(node, "end_lineno", start + max_lines)
                    snippet = lines[start:min(end, start + max_lines)]
                    return "\n".join(snippet)
    except (SyntaxError, OSError):
        pass
    return None


# ── REPL command ──────────────────────────────────────────────────────────────

async def ai_route_command(node: Any, args: str) -> str:
    """
    REPL command handler for `!ai_route <task description>`.

    Usage examples:
        !ai_route forage new papers
        !ai_route self-optimize a function
        !ai_route route llm request
    """
    args = args.strip()
    if not args:
        idx = load_router_index()
        tasks = list(idx.get("tasks", {}).keys())
        if tasks:
            return ("Usage: !ai_route <task description>\n"
                    "Available tasks:\n" +
                    "\n".join(f"  • {t}" for t in tasks))
        return ("Usage: !ai_route <task description>\n"
                "No router index found. Run !topology or "
                "`python3 generate_ai_router.py` first.")

    result = query_router(args)

    if result["status"] == "found":
        lines = [
            f"[AI Router] Task: '{result['task']}'",
            f"  Primary file  : {result['primary_file']}",
            f"  Secondary files: {', '.join(result['secondary_files'])}",
            f"  Key functions : {', '.join(result['key_functions'])}",
            f"  Confidence    : {result['confidence']:.2f}",
        ]
        return "\n".join(lines)
    else:
        available = result.get("available_tasks", [])
        msg = f"[AI Router] No mapping found for '{args}'."
        if available:
            msg += "\nAvailable tasks:\n" + "\n".join(f"  • {t}" for t in available)
        hint = result.get("hint", "")
        if hint:
            msg += f"\n{hint}"
        return msg


def regenerate_router(quiet: bool = False) -> bool:
    """
    Trigger a fresh regeneration of AURA_AI_ROUTER.md by importing and calling
    generate_ai_router.build_router_md(). Safe to call from anywhere.

    Returns True on success, False on error.
    """
    try:
        import generate_ai_router  # noqa: PLC0415
        md = generate_ai_router.build_router_md()
        with open(generate_ai_router.OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(md)
        global _INDEX_CACHE  # invalidate cache
        _INDEX_CACHE = None
        if not quiet:
            print(f"[+] AURA_AI_ROUTER.md regenerated "
                  f"({len(md.splitlines())} lines)")
        return True
    except Exception as exc:  # noqa: BLE001
        if not quiet:
            print(f"[-] AI Router regeneration failed: {exc}")
        return False

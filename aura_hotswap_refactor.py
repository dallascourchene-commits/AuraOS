"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c2-[Q-SYS:HOTSWAP_REFACTOR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Stateless Software Update / Hotswap Safety)
DEPENDENCIES: ast, json, pathlib, typing
FUNCTIONS: classify_hotswap_safety, suggest_hotswap_refactoring
SYNOPSIS: Classifies code changes using AST check logic to determine if a patch can be safely reloaded
at runtime (via importlib.reload) or if it requires refactoring or a full system restart.
Provides refactoring guidelines when module-level mutable state or singleton threads are detected.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Tuple


def classify_hotswap_safety(file_path: str | Path, diff: str) -> tuple[str, list[str]]:
    """
    Analyze file and proposed diff via AST to check reload safety.
    
    Returns a tuple of: (classification, reasons)
    where classification is 'hotswap_safe', 'reload_requires_refactor', or 'restart_required'
    """
    path = Path(file_path)
    reasons = []
    
    if not path.exists():
        return "hotswap_safe", ["New file creation is always hotswap safe."]
        
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content)
        
        # Check for dangerous patterns:
        # 1. Module-level running threads or loops
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in {"start", "run", "Thread", "Process"}:
                        reasons.append(f"Module starts running thread/process directly: {node.func.attr}")
                elif isinstance(node.func, ast.Name):
                    if node.func.id in {"Thread", "Process", "run_forever"}:
                        reasons.append(f"Module starts active execution unit: {node.func.id}")
                        
            # 2. Module-level mutable state singletons
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    # Check if target is a global mutable container initialized at module level
                    if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
                        if not target.id.startswith("_") and target.id.isupper():
                            reasons.append(f"Public global mutable configuration container: {target.id}")
                            
        # 3. Changes in class hierarchy or metaclasses inside diff
        # (if diff contains class parent changes, reload can lead to type mismatch)
        if "class " in diff:
            reasons.append("Class definition changes detected. importlib.reload will not update instances.")
            
    except Exception as exc:
        return "restart_required", [f"AST parse failure: {exc}"]
        
    if reasons:
        # Check if any blocker requires full restart (like active threads or OS resources)
        if any("thread" in r.lower() or "process" in r.lower() or "active" in r.lower() for r in reasons):
            return "restart_required", reasons
        return "reload_requires_refactor", reasons
        
    return "hotswap_safe", []


def suggest_hotswap_refactoring(file_path: str | Path, reasons: list[str]) -> str:
    """Generate refactoring instructions to turn a non-hotswappable module into a reloadable one."""
    instructions = [
        "Your proposed patch was flagged as reload-unsafe for hot-swapping due to the following:",
        *[f"- {r}" for r in reasons],
        "\nTo support hot-swapping without restarting the system, refactor the code to:",
        "1. Avoid module-level mutable global variables. Wrap them in a registry or class instance getter.",
        "2. Do not start threads or run event loops directly on module load. Create start/stop functions.",
        "3. Keep class definitions stable. If changing class structures, support dynamic state migration.",
        "Please refactor the targets and resubmit the transaction."
    ]
    return "\n".join(instructions)

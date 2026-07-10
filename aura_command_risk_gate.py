"""
Aura Command Risk Gate — classify command-effect risk before agent execution.
Hard blocks risky commands unless human explicitly approves.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
RISK_GATE_VERSION = "AURA_COMMAND_RISK_GATE_V1"

_RISK_PATTERNS = [
    # Hard blocks first (higher priority)
    ("| sh", "external_script", True),
    ("| bash", "external_script", True),
    ("rm -rf /", "destructive_file_op", True),
    ("rm -rf ~", "destructive_file_op", True),
    ("git push --force", "git_history_rewrite", True),
    ("git push -f", "git_history_rewrite", True),
    ("eval(", "encoded_payload", True),
    ("base64 -d", "encoded_payload", True),
    ("| python", "encoded_payload", True),
    ("~/.ssh", "credential_access", True),
    (".env", "credential_access", True),
    # Soft flags (not blocked)
    ("curl", "external_script", False),
    ("wget", "external_script", False),
    ("dig txt", "dns_lookup", False),
    ("nslookup", "dns_lookup", False),
    ("npm install", "package_install", False),
    ("pip install", "package_install", False),
    ("uv pip install", "package_install", False),
    ("python setup.py", "external_script", False),
]

def classify_command_risk(command: str, repo_root: str | Path = ".") -> dict[str, Any]:
    cmd_lower = command.lower().strip()
    risk_category = "safe_read_only"
    blocked = False
    for pattern, category, hard_block in _RISK_PATTERNS:
        if pattern in cmd_lower:
            risk_category = category
            blocked = hard_block
            break
    if not blocked and risk_category == "safe_read_only":
        if any(w in cmd_lower for w in ["grep", "cat", "ls", "head", "tail", "find", "wc"]):
            risk_category = "safe_read_only"
        elif "pytest" in cmd_lower or "python -m pytest" in cmd_lower:
            risk_category = "repo_local_test"
        elif "git commit" in cmd_lower:
            risk_category = "git_commit"
            blocked = False
        elif "git push" in cmd_lower and "git push --force" not in cmd_lower and "git push -f" not in cmd_lower:
            risk_category = "git_push"
            blocked = False
        elif "git add" in cmd_lower:
            risk_category = "safe_read_only"
    human_approval = blocked or risk_category in ("git_commit", "git_push")
    return {"ok": True, "command": command, "risk_category": risk_category,
            "blocked": blocked, "human_approval_required": human_approval,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def classify_script_risk(path: str, repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    try:
        content = (root / path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"ok": True, "path": path, "risk_category": "unknown", "blocked": False,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    risks = []
    for pattern, category, hard_block in _RISK_PATTERNS:
        if pattern in content.lower():
            risks.append({"category": category, "blocked": hard_block})
    blocked = any(r["blocked"] for r in risks)
    return {"ok": True, "path": path, "risk_category": risks[0]["category"] if risks else "safe_read_only",
            "blocked": blocked, "risks": risks, "human_approval_required": blocked,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def scan_markdown_for_agent_instructions(path: str, repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    try:
        content = (root / path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"ok": True, "path": path, "instructions_found": [], "risk": "unknown",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    instructions = []
    for pattern in ["curl", "wget", "npm install", "pip install", "eval", "base64", "rm -rf", "git push --force"]:
        if pattern in content.lower():
            instructions.append(pattern)
    return {"ok": True, "path": path, "instructions_found": instructions,
            "risk": "high" if instructions else "safe",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def scan_package_hooks(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    hooks = []
    for name in ["setup.py", "pyproject.toml", "package.json", "requirements.txt"]:
        p = root / name
        if p.exists():
            hooks.append(name)
    return {"ok": True, "hooks": hooks, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def command_risk_packet(commands_or_paths: list[str], repo_root: str | Path = ".") -> dict[str, Any]:
    results = []
    for item in commands_or_paths:
        if item.endswith(".py") or item.endswith(".sh"):
            results.append(classify_script_risk(item, repo_root=repo_root))
        elif item.endswith(".md"):
            results.append(scan_markdown_for_agent_instructions(item, repo_root=repo_root))
        else:
            results.append(classify_command_risk(item, repo_root=repo_root))
    blocked = any(r.get("blocked") or r.get("risk") == "high" for r in results)
    return {"ok": True, "results": results, "any_blocked": blocked,
            "human_approval_required": blocked,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def require_human_approval_for_risky_commands(packet: dict) -> dict[str, Any]:
    blocked = packet.get("any_blocked", False)
    return {"ok": True, "approval_required": blocked, "blocked": blocked,
            "note": "Human approval required for risky commands." if blocked else "No risky commands detected.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

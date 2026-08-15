"""
Aura Hermes Arena Mode — Hermes operating contract layer for AuraOS.

This module provides a first-class "Hermes through Aura" operating mode so an
external coding agent such as Hermes can receive a normal user objective like
"refactor X and open a PR," but must execute through Aura's token-saving Agent
Arena architecture before reading, editing, testing, committing, or opening a
pull request.

This is NOT a new model provider. It is an Aura-native agent workflow layer
that forces external agents to use Aura's existing architecture:

  * Agent Arena Bridge
  * CODEMAP navigation
  * Affordance Directory
  * Concept Workspace
  * Node Inspector
  * read-slice instead of broad file reads
  * prepare/context micro-arena packets
  * Context Crusher / ST3GG / JSpace advisory packets where already available
  * patch staging / verification / repair packets
  * token savings reports
  * PR-safe Git workflow

Design constraints (enforced):
  * No hardcoded API keys. No provider API calls unless explicitly requested.
  * JSpace, VSA, ST3GG, screenshots, visual topology, and summaries are
    advisory only — never patch authority.
  * patch_authority: "exact_source_spans_and_hashes_only"
  * vsa_patch_authority: false
  * No `git add .` — only scoped file staging.
  * No commits to main.
  * No reads of .venv, node_modules, build artifacts, generated files, caches,
    nested AuraOS clones, Antigravity scratch folders, or Codex scratch folders.
  * All paths remain repo-relative.
  * Broad hub-file reads are blocked unless a specific symbol or line range is
    requested.

Four public capabilities:
  1. generate_hermes_contract()  — ready-to-paste Hermes system/operator prompt
  2. run_preflight()             — compact JSON preflight packet
  3. generate_token_savings_report() — raw vs Aura token usage comparison
  4. generate_pr_runbook()       — exact Git/Hermes workflow for a task

Dependencies: stdlib only (json, pathlib, re, typing, dataclasses).
Calls existing Aura internals rather than duplicating logic.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shlex
from typing import Any

# ---------------------------------------------------------------------------
# Constants and invariants
# ---------------------------------------------------------------------------

HERMES_MODE_VERSION = "AURA_HERMES_ARENA_MODE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# Files that are too large for direct reads — agents must use symbol search.
# Mirrored from aura_agent_arena_bridge._BLOCKED_HUB_FILES so this module can
# warn about them without importing the bridge (which has heavier deps).
_BLOCKED_HUB_FILES = frozenset({
    "aura_node.py",
    "aura_live_architect.py",
    "aura_coding_arena_3d.py",
    "aura_music_coding_arena.py",
    "aura_emergent_result_verifier.py",
    "aura_empirical_software_lab.py",
    "aura_efficiency_benchmark.py",
})

# Directories that must never be read.
_FORBIDDEN_DIRS = frozenset({
    ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".git", "build", "dist", ".tox", ".mypy_cache", ".ruff_cache",
    "Antigravity", "Codex",
})

# Safety rules that appear in every packet and contract.
_SAFETY_RULES = [
    "You are inside AuraOS.",
    "You must use the Aura Agent Arena Bridge before direct file reads.",
    "You must call digest first: python -m aura_agent_arena_cli digest",
    "You must call find-affordances before planning: python -m aura_agent_arena_cli find-affordances --objective \"...\"",
    "You must use CODEMAP search before opening files: python -m aura_agent_arena_cli search --query \"...\" --kind symbol",
    "You must use read-slice for exact source: python -m aura_agent_arena_cli read-slice --file <file> --symbol <symbol>",
    "You must produce token savings evidence before editing: python -m aura_agent_arena_cli token-report --objective \"...\" --files <files>",
    "You must use a feature branch and PR workflow. Never commit directly to main.",
    "You must NOT use git add . — stage only specific scoped files.",
    "You must NOT read hub files directly (aura_node.py, aura_live_architect.py, etc.). Use read-slice with --symbol.",
    "You must NOT treat advisory layers (JSpace, VSA, ST3GG, visual topology, summaries) as patch authority.",
    "You must NOT read .venv, node_modules, __pycache__, build artifacts, or generated files.",
    "All paths must remain repo-relative inside AuraOS.",
    "On Windows, use: python -m aura_agent_arena_cli <subcommand> (not bash-only scripts).",
]

# Windows-compatible command prefix.
_CMD_PREFIX = "python -m aura_agent_arena_cli"


def _quote_shell_arg(arg: str) -> str:
    """Quote a shell argument safely using shlex.quote."""
    return shlex.quote(arg)


def _validate_git_ref(ref: str) -> bool:
    """Validate that a git ref contains only safe characters.

    Returns True if the ref is safe to use in commands.
    """
    # Git refs should only contain alphanumeric, slash, dash, underscore, dot
    import string
    allowed = set(string.ascii_letters + string.digits + "/-_.")
    return all(c in allowed for c in ref)


def _validate_repo_relative_path(path: str) -> bool:
    """Validate that a path is repo-relative and contains no shell metacharacters.

    Returns True if the path is safe to use in commands.
    """
    # Reject absolute paths
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return False
    # Reject shell metacharacters
    unsafe_chars = set("$`;&|<>(){}[]!*?'\"\\")
    return not any(c in unsafe_chars for c in path)


# ---------------------------------------------------------------------------
# Token estimation (local, deterministic — chars / 4)
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    """Estimate tokens as len(text) // 4. Returns at least 1 for non-empty."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _file_char_count(repo_root: Path, file_path: str) -> int:
    """Return the character count of a repo-relative file, or 0 if unreadable."""
    try:
        resolved = (repo_root / file_path).resolve()
        # Ensure it stays inside repo root.
        resolved.relative_to(repo_root.resolve())
        if not resolved.exists() or not resolved.is_file():
            return 0
        return len(resolved.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return 0


def _is_forbidden_path(file_path: str) -> bool:
    """Check if a file path falls inside a forbidden directory.

    Uses case-insensitive component comparisons via casefold().
    """
    normalized = file_path.replace("\\", "/")
    for part in normalized.split("/"):
        if part.casefold() in {d.casefold() for d in _FORBIDDEN_DIRS}:
            return True
    return False


def _is_blocked_hub(file_path: str) -> bool:
    """Check if a file is a blocked hub file.

    Uses case-insensitive name comparison via casefold().
    """
    name = Path(file_path).name
    return name.casefold() in {f.casefold() for f in _BLOCKED_HUB_FILES}


# ---------------------------------------------------------------------------
# CODEMAP loader (lightweight, cached — does not import the bridge)
# ---------------------------------------------------------------------------

_CODEMAP_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CODEMAP_TTL = 120.0


def _load_codemap(repo_root: Path) -> dict[str, Any]:
    """Load CODEMAP.json with a simple TTL cache."""
    import time
    path = repo_root / ".aura" / "CODEMAP.json"
    key = str(path)
    now = time.time()
    if key in _CODEMAP_CACHE:
        ts, data = _CODEMAP_CACHE[key]
        if now - ts < _CODEMAP_TTL:
            return data
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        _CODEMAP_CACHE[key] = (now, data)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        # CODEMAP is optional — return empty dict if missing or unreadable.
        return {}


# ---------------------------------------------------------------------------
# Keyword extraction for objective → file/symbol inference
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "to", "for", "of", "in", "on", "and", "or",
    "with", "by", "from", "that", "this", "it", "as", "at", "be", "was",
    "will", "can", "could", "should", "would", "may", "might", "must",
    "shall", "do", "does", "did", "has", "have", "had", "not", "but",
    "about", "into", "out", "up", "down", "over", "under", "again",
    "more", "most", "some", "any", "all", "both", "each", "few",
})


def _extract_keywords(objective: str) -> list[str]:
    """Extract meaningful keywords from an objective string."""
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", objective.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _suggest_files_from_codemap(
    codemap: dict[str, Any],
    keywords: list[str],
    max_results: int = 10,
) -> list[str]:
    """Suggest likely files from CODEMAP based on keyword matching."""
    files = codemap.get("files", [])
    file_list = []
    if isinstance(files, list):
        file_list = [str(f.get("path", "")) for f in files if isinstance(f, dict) and f.get("path")]
    elif isinstance(files, dict):
        file_list = list(files.keys())

    scored: list[tuple[float, str]] = []
    for fp in file_list:
        if not fp or fp.endswith((".json", ".bak", ".save", ".txt", ".pdf", ".tex")):
            continue
        if _is_forbidden_path(fp):
            continue
        fp_lower = fp.lower()
        # Score by keyword matches in file path
        score = sum(1.0 for kw in keywords if kw in fp_lower)
        # Bonus for .py files
        if fp.endswith(".py"):
            score += 0.3
        if score > 0:
            scored.append((score, fp))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [fp for _, fp in scored[:max_results]]


def _suggest_symbols_from_codemap(
    codemap: dict[str, Any],
    keywords: list[str],
    max_results: int = 10,
) -> list[tuple[str, str | None]]:
    """Suggest likely symbols from CODEMAP symbol_index.

    Returns a list of (symbol_name, file_path | None) tuples, preserving
    CODEMAP file-to-symbol relationships. If a symbol's location cannot be
    determined, file_path will be None.
    """
    symbol_index = codemap.get("symbol_index", {})
    if not isinstance(symbol_index, dict):
        return []

    scored: list[tuple[float, str, str | None]] = []
    for sym_name, sym_data in symbol_index.items():
        sym_lower = sym_name.lower()
        score = sum(1.0 for kw in keywords if kw in sym_lower)
        if score > 0:
            # Extract file location from symbol data
            file_path: str | None = None
            if isinstance(sym_data, dict):
                file_path = sym_data.get("file") or sym_data.get("path")
            elif isinstance(sym_data, list) and len(sym_data) > 0:
                # Some CODEMAPs store locations as a list
                first_loc = sym_data[0]
                if isinstance(first_loc, dict):
                    file_path = first_loc.get("file") or first_loc.get("path")
            scored.append((score, sym_name, file_path))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(sym, fp) for _, sym, fp in scored[:max_results]]


def _suggest_searches(keywords: list[str]) -> list[str]:
    """Build suggested CODEMAP search commands from keywords."""
    if not keywords:
        return []
    top_kw = keywords[:3]
    searches = []
    for kw in top_kw:
        searches.append(f"{_CMD_PREFIX} search --query {_quote_shell_arg(kw)} --kind symbol")
    # Also a combined search
    combined = " ".join(top_kw)
    searches.append(f"{_CMD_PREFIX} search --query {_quote_shell_arg(combined)} --kind text")
    return searches


def _suggest_read_slices(
    likely_files: list[str],
    likely_symbols: list[tuple[str, str | None]],
) -> list[str]:
    """Build suggested read-slice commands.

    Preserves CODEMAP file-to-symbol relationships instead of combining
    independently ranked files and symbols. Uses each symbol's recorded
    location to generate only verified (file, symbol) read-slice commands,
    respecting the five-command limit. When a symbol lacks a verified file
    location, omits the guessed slice. Retains existing file-only fallback
    when no symbols are available at all.

    All arguments are validated and shell-quoted for safety.
    """
    slices: list[str] = []

    # Generate verified (file, symbol) pairs from CODEMAP relationships
    for sym_name, file_path in likely_symbols:
        if file_path and _validate_repo_relative_path(file_path):
            # Verified location from CODEMAP
            slices.append(
                f"{_CMD_PREFIX} read-slice --file {_quote_shell_arg(file_path)} "
                f"--symbol {_quote_shell_arg(sym_name)}"
            )
            if len(slices) >= 5:
                break

    # If we have files but no symbols, suggest file-level reads
    if not likely_symbols and likely_files:
        for fp in likely_files[:5]:
            if not _is_blocked_hub(fp) and _validate_repo_relative_path(fp):
                slices.append(f"{_CMD_PREFIX} read-slice --file {_quote_shell_arg(fp)}")
                if len(slices) >= 5:
                    break

    return slices[:5]


# ---------------------------------------------------------------------------
# 1. Hermes operating contract generator
# ---------------------------------------------------------------------------


def generate_hermes_contract(
    objective: str,
    mode: str = "pr",
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Generate a ready-to-paste Hermes system/operator prompt.

    Args:
        objective: The normal coding objective (e.g. "Refactor Fireworks egress").
        mode: Operating mode — only "pr" is supported (feature-branch workflow).
        repo_root: Repo root path.

    Returns:
        Dict with ok, contract (markdown text), objective, mode, and invariants.
    """
    # Validate mode: only "pr" is supported (feature-branch workflow)
    # Direct mode is not supported to enforce the feature-branch invariant
    if mode != "pr":
        return {
            "ok": False,
            "error": f"Unsupported mode: {mode}. Only 'pr' mode is supported. "
                     "Direct edits on main branch violate the feature-branch invariant.",
            "objective": objective,
            "mode": mode,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)
    codemap_active = bool(codemap)

    mode_label = "PR-safe feature branch workflow"

    contract_lines: list[str] = []
    contract_lines.append("# Hermes → Aura Operating Contract")
    contract_lines.append("")
    contract_lines.append(f"**Objective:** {objective}")
    contract_lines.append(f"**Mode:** {mode_label}")
    contract_lines.append(f"**Aura Version:** {HERMES_MODE_VERSION}")
    contract_lines.append(f"**CODEMAP:** {'ACTIVE' if codemap_active else 'MISSING — run CODEMAP generation first'}")
    contract_lines.append("")

    contract_lines.append("## Mandatory Aura-First Workflow Rules")
    contract_lines.append("")
    for rule in _SAFETY_RULES:
        contract_lines.append(f"- {rule}")
    contract_lines.append("")

    contract_lines.append("## Exact Commands to Run (in order)")
    contract_lines.append("")

    # Step 1: Git safety
    contract_lines.append("### Step 1: Confirm clean Git state")
    contract_lines.append("```bash")
    contract_lines.append("git status --porcelain")
    contract_lines.append("```")
    contract_lines.append("- If working tree is dirty, STOP. Either commit/stash or get explicit user approval before proceeding.")
    contract_lines.append("")

    # Step 2: Feature branch creation (mode is always "pr")
    contract_lines.append("### Step 2: Create feature branch from main")
    contract_lines.append("```bash")
    contract_lines.append("git fetch origin")
    contract_lines.append("git switch main")
    contract_lines.append("git pull --ff-only origin main")
    contract_lines.append("git switch -c feature/<descriptive-name>")
    contract_lines.append("```")
    contract_lines.append("- NEVER commit directly to main.")
    contract_lines.append("")
    step_offset = 3

    # Step 3: Repo digest
    contract_lines.append(f"### Step {step_offset}: Run Aura repo digest")
    contract_lines.append("```bash")
    contract_lines.append(f"{_CMD_PREFIX} digest")
    contract_lines.append("```")
    step_offset += 1

    # Step 4: Affordance preflight
    contract_lines.append(f"### Step {step_offset}: Run affordance preflight")
    contract_lines.append("```bash")
    contract_lines.append(f'{_CMD_PREFIX} find-affordances --objective {_quote_shell_arg(objective)}')
    contract_lines.append("```")
    step_offset += 1

    # Step 5: Preflight packet
    contract_lines.append(f"### Step {step_offset}: Generate preflight packet")
    contract_lines.append("```bash")
    contract_lines.append(f'{_CMD_PREFIX} preflight --objective {_quote_shell_arg(objective)}')
    contract_lines.append("```")
    step_offset += 1

    # Step 6: CODEMAP search
    contract_lines.append(f"### Step {step_offset}: Search CODEMAP for relevant files/symbols")
    contract_lines.append("```bash")
    keywords = _extract_keywords(objective)
    for search_cmd in _suggest_searches(keywords):
        contract_lines.append(search_cmd)
    contract_lines.append("```")
    contract_lines.append("- Refuse broad hub-file reads. Use read-slice with --symbol or --line-start/--line-end only.")
    step_offset += 1

    # Step 7: Read-slice
    contract_lines.append(f"### Step {step_offset}: Use read-slice for exact source")
    contract_lines.append("```bash")
    likely_files = _suggest_files_from_codemap(codemap, keywords)
    likely_symbols = _suggest_symbols_from_codemap(codemap, keywords)
    for slice_cmd in _suggest_read_slices(likely_files, likely_symbols):
        contract_lines.append(slice_cmd)
    if not likely_files:
        contract_lines.append("# (Replace with actual files found from search)")
        contract_lines.append(f"{_CMD_PREFIX} read-slice --file <file.py> --symbol <SymbolName>")
    contract_lines.append("```")
    step_offset += 1

    # Step 8: Token report
    contract_lines.append(f"### Step {step_offset}: Produce Token Savings Report before editing")
    contract_lines.append("```bash")
    files_arg = ",".join(likely_files[:3]) if likely_files else "<file1.py>,<file2.py>"
    contract_lines.append(
        f'{_CMD_PREFIX} token-report --objective {_quote_shell_arg(objective)} '
        f'--files {_quote_shell_arg(files_arg)} --include-preflight'
    )
    contract_lines.append("```")
    step_offset += 1

    # Step 9: Prepare arena task
    contract_lines.append(f"### Step {step_offset}: Prepare arena task")
    contract_lines.append("```bash")
    target_file = likely_files[0] if likely_files else "<target_file.py>"
    target_symbol = likely_symbols[0][0] if likely_symbols else "<TargetSymbol>"
    contract_lines.append(
        f'{_CMD_PREFIX} prepare --objective {_quote_shell_arg(objective)} '
        f'--target-file {_quote_shell_arg(target_file)} --target-symbol {_quote_shell_arg(target_symbol)}'
    )
    contract_lines.append("```")
    step_offset += 1

    # Step 10: Get micro-context
    contract_lines.append(f"### Step {step_offset}: Get micro-context packet")
    contract_lines.append("```bash")
    contract_lines.append(f"{_CMD_PREFIX} context --task-id A1 --format both")
    contract_lines.append("```")
    step_offset += 1

    # Step 11-14: Edit, stage, verify
    contract_lines.append(f"### Step {step_offset}: Edit only localized files")
    contract_lines.append("- Edit ONLY the files identified by CODEMAP search and micro-context.")
    contract_lines.append("- Do NOT read or edit hub files, .venv, node_modules, or generated files.")
    step_offset += 1

    contract_lines.append(f"### Step {step_offset}: Stage patch through Aura boundary")
    contract_lines.append("```bash")
    contract_lines.append(f"{_CMD_PREFIX} stage-patch --task-id A1 --diff-file <patch.diff> --affected-files <file1.py>,<file2.py>")
    contract_lines.append("```")
    step_offset += 1

    contract_lines.append(f"### Step {step_offset}: Run verifier/focused tests")
    contract_lines.append("```bash")
    contract_lines.append(f"{_CMD_PREFIX} verify --scope focused")
    contract_lines.append("```")
    step_offset += 1

    contract_lines.append(f"### Step {step_offset}: Produce repair packet if tests fail")
    contract_lines.append("```bash")
    contract_lines.append(f"{_CMD_PREFIX} repair-packet --task-id A1")
    contract_lines.append("```")
    contract_lines.append("- If tests fail twice, escalate instead of broadening scope.")
    step_offset += 1

    # Approval gate
    contract_lines.append(f"### Step {step_offset}: Wait for human approval before final commit/push")
    contract_lines.append("- If configured, STOP and wait for human approval before committing.")
    contract_lines.append("- Do not auto-commit or auto-push without explicit approval.")
    step_offset += 1

    # Commit, push, and PR steps (mode is always "pr")
    contract_lines.append(f"### Step {step_offset}: Commit only scoped files")
    contract_lines.append("```bash")
    contract_lines.append("git diff --stat")
    contract_lines.append("git add <specific_file1.py> <specific_file2.py>  # NEVER git add .")
    commit_msg = objective[:72].replace('"', "'")
    contract_lines.append(f'git commit -m {_quote_shell_arg(commit_msg)}')
    contract_lines.append("```")
    step_offset += 1

    contract_lines.append(f"### Step {step_offset}: Push feature branch")
    contract_lines.append("```bash")
    contract_lines.append("git push -u origin feature/<branch-name>")
    contract_lines.append("```")
    step_offset += 1

    contract_lines.append(f"### Step {step_offset}: Open a PR")
    contract_lines.append("```bash")
    contract_lines.append(
        f'gh pr create --title {_quote_shell_arg(commit_msg)} '
        f'--body {_quote_shell_arg("Refactor implemented through Aura Agent Arena Bridge. Token savings report and preflight packet attached.")} '
        f'--base main'
    )
    contract_lines.append("```")
    contract_lines.append("- If gh CLI is not available, print the exact gh command and the compare URL.")
    step_offset += 1

    # Invariants section
    contract_lines.append("")
    contract_lines.append("## Git Safety Rules")
    contract_lines.append("- Do NOT run `git add .` — stage only specific scoped files.")
    contract_lines.append("- Do NOT commit directly to main.")
    contract_lines.append("- Do NOT include untracked nested AuraOS folders or scratch directories.")
    contract_lines.append("- STOP if working tree is dirty before branch creation unless user explicitly approves.")
    contract_lines.append("- Use `git diff --stat` to verify exactly which files will be committed.")
    contract_lines.append("")

    contract_lines.append("## Patch Authority Invariant")
    contract_lines.append(f"- patch_authority: `{PATCH_AUTHORITY}`")
    contract_lines.append(f"- vsa_patch_authority: `{VSA_PATCH_AUTHORITY}`")
    contract_lines.append("- JSpace, VSA, ST3GG, screenshots, visual topology, and summaries are ADVISORY ONLY.")
    contract_lines.append("- Only exact source spans, hashes, CODEMAP facts, tests, and verifier gates are authority.")
    contract_lines.append("")

    contract_lines.append("## Token Savings Report Requirement")
    contract_lines.append("- You MUST produce a token savings report before editing.")
    contract_lines.append("- This proves you are using Aura's context reduction instead of raw file reads.")
    contract_lines.append("- The report is a local estimate (chars / 4), NOT provider billing telemetry.")
    contract_lines.append("")

    contract = "\n".join(contract_lines)

    return {
        "ok": True,
        "version": HERMES_MODE_VERSION,
        "objective": objective,
        "mode": mode,
        "codemap_active": codemap_active,
        "contract": contract,
        "safety_rules": list(_SAFETY_RULES),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# 2. Objective preflight packet
# ---------------------------------------------------------------------------


def run_preflight(
    objective: str,
    repo_root: str | Path = ".",
    target_files: list[str] | None = None,
    target_symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Accept a normal coding objective and return a compact JSON preflight packet.

    Calls existing Aura internals rather than duplicating logic:
      - aura_repo_digest (via bridge)
      - aura_find_affordances (via bridge or directory)
      - CODEMAP search for likely files/symbols
      - Concept Workspace where useful

    Returns a packet with: ok, objective, repo_digest summary,
    recommended_affordances, prompt_cards, likely_files, likely_symbols,
    suggested_searches, suggested_read_slices, suggested_prepare_command,
    safety_rules, patch_authority, vsa_patch_authority,
    estimated_token_baseline.
    """
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)

    if not codemap:
        return {
            "ok": False,
            "error": "CODEMAP.json is missing or unreadable. Run CODEMAP generation first.",
            "objective": objective,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # --- Repo digest summary (from CODEMAP, not full bridge call) ---
    coverage = codemap.get("coverage", {})
    summary = codemap.get("summary", {})
    file_count = int(
        summary.get("file_count")
        or coverage.get("included_file_count")
        or coverage.get("repo_file_count")
        or 0
    )
    all_paths = coverage.get("all_included_paths_sorted", []) or []
    if not file_count and all_paths:
        file_count = len(all_paths)
    if not file_count and isinstance(codemap.get("files"), list):
        file_count = len(codemap["files"])

    symbol_index = codemap.get("symbol_index", {})
    topology = codemap.get("topology", {})
    topology_nodes = 0
    topology_edges = 0
    if isinstance(topology, dict):
        topology_nodes = len(topology.get("nodes", []) or [])
        topology_edges = len(topology.get("edges", []) or [])

    repo_digest_summary = {
        "codemap_status": "AURA_CODEMAP_ACTIVE",
        "file_count": file_count,
        "symbol_count": len(symbol_index),
        "topology_nodes": topology_nodes,
        "topology_edges": topology_edges,
    }

    # --- Affordance lookup ---
    recommended_affordances: list[dict[str, Any]] = []
    prompt_cards: list[str] = []
    affordance_warning = ""
    try:
        from aura_affordance_directory import find_affordances as _find_affs
        aff_result = _find_affs(
            objective=objective,
            target_files=target_files,
            target_symbols=target_symbols,
            repo_root=root,
            top_k=7,
        )
        recommended_affordances = aff_result.get("recommended_affordances", [])
        prompt_cards = aff_result.get("prompt_cards", [])
    except Exception as exc:
        affordance_warning = f"Affordance lookup failed: {exc}"

    # --- Keyword extraction and file/symbol inference ---
    keywords = _extract_keywords(objective)

    # If target_files/symbols provided, validate and merge with CODEMAP suggestions
    # REJECT (not just warn) invalid, forbidden, or blocked paths
    likely_files: list[str] = []
    rejected_paths: list[str] = []

    if target_files:
        for fp in target_files:
            # Validate the path is repo-relative and safe
            try:
                resolved = (root / fp).resolve()
                resolved.relative_to(root.resolve())
                # REJECT forbidden and blocked paths
                if _is_forbidden_path(fp):
                    rejected_paths.append(f"{fp} (forbidden directory)")
                    continue
                if _is_blocked_hub(fp):
                    # Blocked hub files are allowed but will be warned later
                    pass
                likely_files.append(fp)
            except (ValueError, OSError):
                rejected_paths.append(f"{fp} (outside repository or invalid)")

    codemap_files = _suggest_files_from_codemap(codemap, keywords, max_results=10)
    for fp in codemap_files:
        if fp not in likely_files and not _is_forbidden_path(fp):
            likely_files.append(fp)
    likely_files = likely_files[:10]

    # Build symbol list with CODEMAP file-to-symbol relationships
    likely_symbols_with_files: list[tuple[str, str | None]] = []
    if target_symbols:
        # Convert plain target_symbols list to tuples (symbol, None)
        likely_symbols_with_files = [(sym, None) for sym in target_symbols]

    codemap_symbols = _suggest_symbols_from_codemap(codemap, keywords, max_results=10)
    for sym_name, file_path in codemap_symbols:
        if sym_name not in [s[0] for s in likely_symbols_with_files]:
            likely_symbols_with_files.append((sym_name, file_path))
    likely_symbols_with_files = likely_symbols_with_files[:10]

    suggested_searches = _suggest_searches(keywords)
    suggested_read_slices = _suggest_read_slices(likely_files, likely_symbols_with_files)

    # Suggested prepare command
    prep_file = likely_files[0] if likely_files else "<target_file.py>"
    prep_symbol = likely_symbols_with_files[0][0] if likely_symbols_with_files else "<TargetSymbol>"
    suggested_prepare_command = (
        f'{_CMD_PREFIX} prepare --objective {_quote_shell_arg(objective)} '
        f'--target-file {_quote_shell_arg(prep_file)} --target-symbol {_quote_shell_arg(prep_symbol)}'
    )

    # For backward compatibility, also include a simple symbol list in the result
    likely_symbols = [sym for sym, _ in likely_symbols_with_files]

    # --- Estimated token baseline ---
    # Estimate raw context: what it would cost to read the likely files raw.
    raw_char_count = sum(_file_char_count(root, fp) for fp in likely_files)
    estimated_token_baseline = _estimate_tokens("") if raw_char_count == 0 else raw_char_count // 4

    # Hub file warnings
    hub_warnings: list[str] = []
    for fp in likely_files:
        if _is_blocked_hub(fp):
            hub_warnings.append(
                f"WARNING: '{fp}' is a blocked hub file. Use read-slice with --symbol, never broad read."
            )
        if _is_forbidden_path(fp):
            hub_warnings.append(
                f"WARNING: '{fp}' is inside a forbidden directory. Do not read."
            )

    result: dict[str, Any] = {
        "ok": True,
        "version": HERMES_MODE_VERSION,
        "objective": objective,
        "repo_digest": repo_digest_summary,
        "recommended_affordances": recommended_affordances,
        "prompt_cards": prompt_cards,
        "likely_files": likely_files,
        "likely_symbols": likely_symbols,
        "suggested_searches": suggested_searches,
        "suggested_read_slices": suggested_read_slices,
        "suggested_prepare_command": suggested_prepare_command,
        "safety_rules": list(_SAFETY_RULES),
        "hub_file_warnings": hub_warnings,
        "affordance_warning": affordance_warning,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "estimated_token_baseline": estimated_token_baseline,
        "method": "local_chars_div_4_estimate",
    }

    # Include rejected paths if any were found
    if rejected_paths:
        result["rejected_paths"] = rejected_paths

    return result


# ---------------------------------------------------------------------------
# 3. Token Savings Report
# ---------------------------------------------------------------------------


def generate_token_savings_report(
    objective: str,
    files: list[str],
    repo_root: str | Path = ".",
    include_preflight: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    """Compare raw-context baseline to Aura-context usage.

    Args:
        objective: The coding objective.
        files: List of repo-relative file paths to consider.
        repo_root: Repo root path.
        include_preflight: If True, include the full preflight packet in the report.
        output_format: "json" (default) or "markdown".

    Returns:
        Dict with all required report fields. If output_format="markdown",
        also includes a "markdown" field with a formatted report string.
    """
    root = Path(repo_root).resolve()

    # --- Raw baseline: what it would cost to read these files wholesale ---
    # REJECT (not just warn) forbidden paths and paths outside repository
    raw_files_considered: list[str] = []
    raw_char_count = 0
    files_avoided: list[str] = []
    for fp in files:
        fp_stripped = fp.strip()
        if not fp_stripped:
            continue

        # Validate path is repo-relative and safe
        try:
            resolved = (root / fp_stripped).resolve()
            resolved.relative_to(root.resolve())
        except (ValueError, OSError):
            files_avoided.append(f"{fp_stripped} (outside repository or invalid)")
            continue

        # REJECT forbidden paths
        if _is_forbidden_path(fp_stripped):
            files_avoided.append(f"{fp_stripped} (forbidden directory)")
            continue

        raw_files_considered.append(fp_stripped)
        chars = _file_char_count(root, fp_stripped)
        raw_char_count += chars
        if chars == 0:
            # File doesn't exist or unreadable — note it
            files_avoided.append(f"{fp_stripped} (not found)")

    raw_token_estimate = max(1, raw_char_count // 4) if raw_char_count > 0 else 0

    # --- Aura context estimates ---
    # 1. Digest: typically ~800-1500 chars (compact summary packet)
    digest_chars = 1200  # Conservative estimate for the digest packet
    aura_digest_token_estimate = _estimate_tokens("x" * digest_chars)

    # 2. Search: CODEMAP search returns ~200-600 chars per result, max 10 results
    # Estimate based on keyword count
    keywords = _extract_keywords(objective)
    search_chars = min(len(keywords) * 300, 3000)
    aura_search_token_estimate = _estimate_tokens("x" * search_chars)

    # 3. Read-slice: max 120 lines, avg ~40 chars/line
    read_slice_chars = 120 * 40
    aura_read_slice_token_estimate = _estimate_tokens("x" * read_slice_chars)

    # 4. Micro-context: compressed context packet, typically 500-2000 tokens
    micro_context_chars = 2000
    aura_micro_context_token_estimate = _estimate_tokens("x" * micro_context_chars)

    # Total Aura token estimate
    total_aura_token_estimate = (
        aura_digest_token_estimate
        + aura_search_token_estimate
        + aura_read_slice_token_estimate
        + aura_micro_context_token_estimate
    )

    # Savings
    if raw_token_estimate > 0:
        estimated_tokens_saved = max(0, raw_token_estimate - total_aura_token_estimate)
        estimated_percent_saved = round(
            (estimated_tokens_saved / raw_token_estimate) * 100, 1
        ) if raw_token_estimate > 0 else 0.0
    else:
        estimated_tokens_saved = 0
        estimated_percent_saved = 0.0

    report: dict[str, Any] = {
        "ok": True,
        "version": HERMES_MODE_VERSION,
        "objective": objective,
        "raw_files_considered": raw_files_considered,
        "raw_char_count": raw_char_count,
        "raw_token_estimate": raw_token_estimate,
        "aura_digest_token_estimate": aura_digest_token_estimate,
        "aura_search_token_estimate": aura_search_token_estimate,
        "aura_read_slice_token_estimate": aura_read_slice_token_estimate,
        "aura_micro_context_token_estimate": aura_micro_context_token_estimate,
        "total_aura_token_estimate": total_aura_token_estimate,
        "estimated_tokens_saved": estimated_tokens_saved,
        "estimated_percent_saved": estimated_percent_saved,
        "files_avoided": files_avoided,
        "method": "local_chars_div_4_estimate",
        "warning": (
            "This is a local estimate using chars / 4, NOT provider billing telemetry. "
            "Actual token usage depends on the model tokenizer and prompt structure."
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

    if include_preflight:
        preflight = run_preflight(objective, repo_root=root, target_files=files)
        report["preflight"] = preflight

    # Markdown output
    if output_format == "markdown":
        md_lines: list[str] = []
        md_lines.append("# Aura Token Savings Report")
        md_lines.append("")
        md_lines.append(f"**Objective:** {objective}")
        md_lines.append(f"**Method:** {report['method']}")
        md_lines.append(f"**Warning:** {report['warning']}")
        md_lines.append("")
        md_lines.append("## Raw Context Baseline")
        md_lines.append(f"- Raw files considered: {len(raw_files_considered)}")
        md_lines.append(f"- Raw char count: {raw_char_count:,}")
        md_lines.append(f"- Raw token estimate: {raw_token_estimate:,}")
        md_lines.append("")
        md_lines.append("## Aura Context Usage")
        md_lines.append(f"- Digest token estimate: {aura_digest_token_estimate:,}")
        md_lines.append(f"- Search token estimate: {aura_search_token_estimate:,}")
        md_lines.append(f"- Read-slice token estimate: {aura_read_slice_token_estimate:,}")
        md_lines.append(f"- Micro-context token estimate: {aura_micro_context_token_estimate:,}")
        md_lines.append(f"- **Total Aura token estimate: {total_aura_token_estimate:,}**")
        md_lines.append("")
        md_lines.append("## Savings")
        md_lines.append(f"- Estimated tokens saved: {estimated_tokens_saved:,}")
        md_lines.append(f"- Estimated percent saved: {estimated_percent_saved}%")
        md_lines.append("")
        if files_avoided:
            md_lines.append("## Files Avoided")
            for fp in files_avoided:
                md_lines.append(f"- {fp}")
            md_lines.append("")
        md_lines.append("## Invariants")
        md_lines.append(f"- patch_authority: `{PATCH_AUTHORITY}`")
        md_lines.append(f"- vsa_patch_authority: `{VSA_PATCH_AUTHORITY}`")
        report["markdown"] = "\n".join(md_lines)

    return report


# ---------------------------------------------------------------------------
# 4. PR-safe runbook generator
# ---------------------------------------------------------------------------


def generate_pr_runbook(
    objective: str,
    branch: str,
    repo_root: str | Path = ".",
    files: list[str] | None = None,
) -> dict[str, Any]:
    """Print the exact Git/Hermes workflow for a task.

    Args:
        objective: The coding objective.
        branch: The feature branch name (e.g. "feature/fireworks-egress-refactor").
        repo_root: Repo root path.
        files: Optional list of files that will be modified.

    Returns:
        Dict with ok, runbook (markdown text), branch, and invariants.
    """
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)
    codemap_active = bool(codemap)
    keywords = _extract_keywords(objective)

    # Validate branch name (Git ref safety)
    if not _validate_git_ref(branch):
        return {
            "ok": False,
            "error": f"Invalid branch name: {branch}. Branch names must contain only alphanumeric, /, -, _, . characters.",
            "objective": objective,
            "branch": branch,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # Infer likely files if not provided
    if not files:
        files = _suggest_files_from_codemap(codemap, keywords, max_results=5)

    commit_msg = objective[:72].replace('"', "'")

    runbook_lines: list[str] = []
    runbook_lines.append("# PR-Safe Runbook")
    runbook_lines.append("")
    runbook_lines.append(f"**Objective:** {objective}")
    runbook_lines.append(f"**Branch:** {branch}")
    runbook_lines.append(f"**CODEMAP:** {'ACTIVE' if codemap_active else 'MISSING'}")
    runbook_lines.append("")

    runbook_lines.append("## Git Setup")
    runbook_lines.append("```bash")
    runbook_lines.append("git fetch origin")
    runbook_lines.append("git switch main")
    runbook_lines.append("git pull --ff-only origin main")
    runbook_lines.append(f"git switch -c {_quote_shell_arg(branch)}")
    runbook_lines.append("```")
    runbook_lines.append("")
    runbook_lines.append("**Safety checks:**")
    runbook_lines.append("- STOP if working tree is dirty before branch creation unless user explicitly approves.")
    runbook_lines.append("- Do NOT commit directly to main.")
    runbook_lines.append("- Do NOT include untracked nested AuraOS folders or scratch directories.")
    runbook_lines.append("")

    runbook_lines.append("## Aura Preflight")
    runbook_lines.append("```bash")
    runbook_lines.append(f"{_CMD_PREFIX} digest")
    runbook_lines.append(f'{_CMD_PREFIX} find-affordances --objective {_quote_shell_arg(objective)}')
    runbook_lines.append(f'{_CMD_PREFIX} preflight --objective {_quote_shell_arg(objective)}')
    runbook_lines.append("```")
    runbook_lines.append("")

    runbook_lines.append("## Aura Read-Slice / Context")
    runbook_lines.append("```bash")
    if files:
        for fp in files[:3]:
            if _validate_repo_relative_path(fp):
                if _is_blocked_hub(fp):
                    runbook_lines.append(f"# WARNING: {fp} is a hub file — use search + read-slice --symbol")
                    kw = keywords[0] if keywords else "target"
                    runbook_lines.append(f'{_CMD_PREFIX} search --query {_quote_shell_arg(kw)} --kind symbol')
                else:
                    runbook_lines.append(f"{_CMD_PREFIX} read-slice --file {_quote_shell_arg(fp)}")
    else:
        runbook_lines.append('# Replace with actual files from search')
        kw = keywords[0] if keywords else "target"
        runbook_lines.append(f"{_CMD_PREFIX} search --query {_quote_shell_arg(kw)} --kind symbol")
        runbook_lines.append(f"{_CMD_PREFIX} read-slice --file <file.py> --symbol <Symbol>")
    runbook_lines.append("```")
    runbook_lines.append("- Refuse broad hub-file reads. Use read-slice with --symbol or --line-start/--line-end.")
    runbook_lines.append("")

    runbook_lines.append("## Token Savings Report (before editing)")
    runbook_lines.append("```bash")
    files_arg = ",".join(files[:3]) if files else "<file1.py>,<file2.py>"
    runbook_lines.append(
        f'{_CMD_PREFIX} token-report --objective {_quote_shell_arg(objective)} '
        f'--files {_quote_shell_arg(files_arg)} --include-preflight'
    )
    runbook_lines.append("```")
    runbook_lines.append("")

    runbook_lines.append("## Prepare Arena Task")
    runbook_lines.append("```bash")
    target_file = files[0] if files else "<target_file.py>"
    runbook_lines.append(
        f'{_CMD_PREFIX} prepare --objective {_quote_shell_arg(objective)} '
        f'--target-file {_quote_shell_arg(target_file)}'
    )
    runbook_lines.append(f"{_CMD_PREFIX} context --task-id A1 --format both")
    runbook_lines.append("```")
    runbook_lines.append("")

    runbook_lines.append("## Edit (localized files only)")
    runbook_lines.append("- Edit ONLY the files identified by CODEMAP search and micro-context.")
    runbook_lines.append("- Do NOT read or edit hub files, .venv, node_modules, or generated files.")
    runbook_lines.append("")

    runbook_lines.append("## Stage Patch Through Aura")
    runbook_lines.append("```bash")
    runbook_lines.append(f"{_CMD_PREFIX} stage-patch --task-id A1 --diff-file <patch.diff> --affected-files {files_arg}")
    runbook_lines.append("```")
    runbook_lines.append("")

    runbook_lines.append("## Run Tests")
    runbook_lines.append("```bash")
    runbook_lines.append(f"{_CMD_PREFIX} verify --scope focused")
    runbook_lines.append("```")
    runbook_lines.append("- If tests fail, use: " + f"{_CMD_PREFIX} repair-packet --task-id A1")
    runbook_lines.append("- If tests fail twice, escalate instead of broadening scope.")
    runbook_lines.append("")

    runbook_lines.append("## Commit (scoped files only)")
    runbook_lines.append("```bash")
    runbook_lines.append("git diff --stat")
    if files:
        # Validate and quote each file path
        safe_files = [_quote_shell_arg(f) for f in files if _validate_repo_relative_path(f)]
        runbook_lines.append(f"git add {' '.join(safe_files)}")
    else:
        runbook_lines.append("git add <specific_file1.py> <specific_file2.py>")
    runbook_lines.append(f'git commit -m {_quote_shell_arg(commit_msg)}')
    runbook_lines.append("```")
    runbook_lines.append("")
    runbook_lines.append("**CRITICAL:**")
    runbook_lines.append("- Do NOT run `git add .` — stage only specific scoped files.")
    runbook_lines.append("- Do NOT include untracked nested AuraOS folders.")
    runbook_lines.append("- Use `git diff --stat` to verify exactly which files will be committed.")
    runbook_lines.append("")

    runbook_lines.append("## Push")
    runbook_lines.append("```bash")
    runbook_lines.append(f"git push -u origin {_quote_shell_arg(branch)}")
    runbook_lines.append("```")
    runbook_lines.append("")

    runbook_lines.append("## Open PR")
    runbook_lines.append("```bash")
    runbook_lines.append(
        f'gh pr create --title {_quote_shell_arg(commit_msg)} '
        f'--body {_quote_shell_arg("Refactor implemented through Aura Agent Arena Bridge. Token savings report and preflight packet attached.")} '
        f'--base main'
    )
    runbook_lines.append("```")
    runbook_lines.append("- If gh CLI is not available, print the exact gh command and the compare URL:")
    runbook_lines.append(f"  https://github.com/dallascourchene-commits/AuraOS/compare/main...{branch}")
    runbook_lines.append("")

    runbook_lines.append("## Invariants")
    runbook_lines.append(f"- patch_authority: `{PATCH_AUTHORITY}`")
    runbook_lines.append(f"- vsa_patch_authority: `{VSA_PATCH_AUTHORITY}`")
    runbook_lines.append("- JSpace, VSA, ST3GG, screenshots, visual topology, and summaries are ADVISORY ONLY.")
    runbook_lines.append("- On Windows, use: python -m aura_agent_arena_cli <subcommand>")
    runbook_lines.append("")

    runbook = "\n".join(runbook_lines)

    return {
        "ok": True,
        "version": HERMES_MODE_VERSION,
        "objective": objective,
        "branch": branch,
        "runbook": runbook,
        "files": files or [],
        "codemap_active": codemap_active,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# 5. Hermes session guard ruleset
# ---------------------------------------------------------------------------

HERMES_AURA_RULES_MD = """# Hermes → Aura Rules

You are inside AuraOS.

## Mandatory Rules

1. You must use the Aura Agent Arena Bridge before direct file reads.
2. You must call digest first: `python -m aura_agent_arena_cli digest`
3. You must call find-affordances before planning: `python -m aura_agent_arena_cli find-affordances --objective "..."`
4. You must use CODEMAP search before opening files: `python -m aura_agent_arena_cli search --query "..." --kind symbol`
5. You must use read-slice for exact source: `python -m aura_agent_arena_cli read-slice --file <file> --symbol <symbol>`
6. You must produce token savings evidence before editing: `python -m aura_agent_arena_cli token-report --objective "..." --files <files>`
7. You must use a feature branch and PR workflow. Never commit directly to main.
8. You must NOT use `git add .` — stage only specific scoped files.
9. You must NOT read hub files directly (aura_node.py, aura_live_architect.py, etc.). Use read-slice with `--symbol`.
10. You must NOT treat advisory layers (JSpace, VSA, ST3GG, visual topology, summaries) as patch authority.
11. You must NOT read .venv, node_modules, __pycache__, build artifacts, or generated files.
12. All paths must remain repo-relative inside AuraOS.
13. On Windows, use: `python -m aura_agent_arena_cli <subcommand>` (not bash-only scripts).

## Patch Authority

- patch_authority: `exact_source_spans_and_hashes_only`
- vsa_patch_authority: `false`
- Only exact source spans, hashes, CODEMAP facts, tests, and verifier gates are authority.
- JSpace, VSA, ST3GG, screenshots, visual topology, and summaries are advisory only.

## Git Safety

- Do NOT run `git add .`
- Do NOT commit directly to main
- Do NOT include untracked nested AuraOS folders or scratch directories
- STOP if working tree is dirty before branch creation unless user explicitly approves
- Use `git diff --stat` to verify exactly which files will be committed
"""


def write_hermes_aura_rules(repo_root: str | Path = ".") -> dict[str, Any]:
    """Write the .aura/HERMES_AURA_RULES.md guard file.

    Returns a dict with ok, path, and content.
    """
    root = Path(repo_root).resolve()
    rules_dir = root / ".aura"
    rules_path = rules_dir / "HERMES_AURA_RULES.md"

    try:
        rules_dir.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(HERMES_AURA_RULES_MD, encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "error": f"Cannot write guard file: {exc}",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    return {
        "ok": True,
        "path": str(rules_path.relative_to(root)).replace("\\", "/"),
        "content": HERMES_AURA_RULES_MD,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

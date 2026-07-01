"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b3-[Q-SYS:PATCH_QUALITY_GATE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Patch Preflight)
DEPENDENCIES: __future__, dataclasses, difflib, hashlib, json, pathlib, re, shutil, subprocess, tempfile, typing
FUNCTIONS: PatchPreflightResult, BeforeAfterReplacement, preflight_patch, generate_unified_diff_from_before_after, _is_prose_only, _validate_hunk_headers, _git_apply_check, _run_command
SYNOPSIS: Patch preflight checks (empty diff, prose-only, malformed hunk headers, git apply --check) and deterministic local unified diff generation from before/after replacement objects. Prevents malformed model-generated patches from reaching the premium patch judge.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any


# Regex for valid unified diff hunk headers: @@ -start,count +start,count @@
_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

# Markers that indicate actual diff content (not prose)
_DIFF_MARKERS = ("diff --git ", "--- ", "+++ ", "@@ ", "*** Begin Patch", "*** Update File: ", "*** Add File: ", "*** Delete File: ")


@dataclass
class PatchPreflightResult:
    """Result of running preflight checks on a candidate patch."""
    ok: bool
    rejections: list[str] = field(default_factory=list)
    git_check_result: dict[str, Any] | None = None
    diff: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BeforeAfterReplacement:
    """Structured before/after replacement object returned by the Builder.

    Instead of hand-writing fragile hunk headers, the model can return this
    structured object. The quality gate generates the unified diff locally
    with deterministic tooling (difflib).
    """
    target_file: str
    before_text: str
    after_text: str
    symbol_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BeforeAfterReplacement | None:
        """Attempt to parse a dict as a before/after replacement.

        Returns None if the dict doesn't have the required keys.
        """
        before = data.get("before_text") or data.get("before")
        after = data.get("after_text") or data.get("after")
        target_file = data.get("target_file") or data.get("file") or ""
        if before is None or after is None:
            return None
        return cls(
            target_file=str(target_file),
            before_text=str(before),
            after_text=str(after),
            symbol_hint=str(data.get("symbol_hint") or data.get("symbol") or ""),
        )


def _run_command(command: list[str], *, cwd: Path, stdin: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """Run a command and return a structured result."""
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return {"status": "error", "returncode": 1, "cmd": command, "error": str(exc), "stdout": "", "stderr": str(exc)}
    return {
        "status": "passed" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "cmd": command,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def _git_executable() -> str | None:
    found = shutil.which("git")
    if found:
        return found
    windows_git = Path("C:/Program Files/Git/cmd/git.exe")
    if windows_git.exists():
        return str(windows_git)
    return None


def _repo_copy_ignore(_directory: str, names: list[str]) -> set[str]:
    # .git IS ignored — we init a fresh git repo in the temp workspace instead
    # of copying .git internals (which can corrupt due to sockets/pipes/perms)
    ignored = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "venv",
        ".venv",
        "Aura_Memory",
        ".aura",
    }
    return {name for name in names if name in ignored}


def _is_prose_only(text: str) -> bool:
    """Check if the text is prose (natural language) with no diff markers."""
    body = str(text or "").strip()
    if not body:
        return False  # Empty is handled separately
    # If any diff marker is present, it's not prose-only
    for marker in _DIFF_MARKERS:
        if marker in body:
            return False
    # Check if it looks like natural language prose
    # Heuristic: has sentences (periods followed by spaces) and no @@ headers
    has_hunk = bool(_HUNK_HEADER_RE.search(body))
    if has_hunk:
        return False
    # If it has code-like structure (indented blocks, def/class), it might be raw code
    # but without diff markers, it's still not a valid diff
    lines = body.splitlines()
    if not lines:
        return True
    # Check for prose indicators: sentences with words
    prose_indicators = sum(
        1 for line in lines
        if re.search(r"[a-zA-Z]{4,}\s+[a-zA-Z]{4,}", line) and not line.startswith((" ", "\t", "#", "import ", "from ", "def ", "class "))
    )
    # If most lines look like prose and there are no diff markers, it's prose-only
    return prose_indicators >= max(1, len(lines) // 3)


def _validate_hunk_headers(diff: str) -> list[str]:
    """Validate that all hunk headers in the diff are well-formed.

    Returns a list of error messages for malformed headers.
    """
    errors: list[str] = []
    lines = str(diff or "").splitlines()
    has_hunk_headers = False
    for i, line in enumerate(lines, start=1):
        if line.startswith("@@"):
            has_hunk_headers = True
            if not _HUNK_HEADER_RE.match(line):
                errors.append(f"Malformed hunk header at line {i}: {line[:80]}")
    # If there are diff markers but no hunk headers, that's malformed
    has_diff_marker = any(line.startswith("diff --git ") or line.startswith("--- ") for line in lines)
    if has_diff_marker and not has_hunk_headers:
        errors.append("Diff has file headers but no @@ hunk headers.")
    return errors


def _git_apply_check(diff: str, *, repo_root: Path) -> dict[str, Any]:
    """Run git apply --check --whitespace=nowarn in a temp workspace copy."""
    git = _git_executable()
    if git is None:
        return {"status": "error", "returncode": 1, "error": "git executable unavailable", "stdout": "", "stderr": "git not found"}
    if not repo_root.exists():
        return {"status": "error", "returncode": 1, "error": f"repo_root does not exist: {repo_root}", "stdout": "", "stderr": "repo root missing"}

    temp_root = Path(tempfile.mkdtemp(prefix="aura_preflight_"))
    workspace = temp_root / "repo"
    try:
        shutil.copytree(repo_root, workspace, ignore=_repo_copy_ignore)
        # Initialize a fresh git repo in the temp workspace so git apply --check works
        _run_command([git, "init"], cwd=workspace, timeout=10)
        _run_command([git, "config", "user.email", "aura@preflight.local"], cwd=workspace, timeout=5)
        _run_command([git, "config", "user.name", "Aura Preflight"], cwd=workspace, timeout=5)
        _run_command([git, "add", "-A"], cwd=workspace, timeout=10)
        _run_command([git, "commit", "-m", "preflight baseline"], cwd=workspace, timeout=10)
        result = _run_command(
            [git, "apply", "--check", "--whitespace=nowarn", "-"],
            cwd=workspace,
            stdin=diff,
            timeout=15,
        )
        return result
    except Exception as exc:
        return {"status": "error", "returncode": 1, "error": str(exc), "stdout": "", "stderr": str(exc)}
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def preflight_patch(
    diff: str,
    *,
    repo_root: str | Path,
    run_git_check: bool = True,
) -> PatchPreflightResult:
    """Run preflight checks on a candidate patch before the premium patch judge.

    Checks (in order):
    1. Reject empty diff
    2. Reject prose-only output
    3. Reject malformed hunk headers
    4. Run git apply --check --whitespace=nowarn in temp workspace

    Research basis: Agentless's "patch validation" step; SWE-agent's format repair;
    PracRepair's preflight checks.
    """
    body = str(diff or "").strip()
    rejections: list[str] = []

    # 1. Empty diff
    if not body:
        return PatchPreflightResult(ok=False, rejections=["empty_diff"], diff=diff)

    # 2. Prose-only
    if _is_prose_only(body):
        rejections.append("prose_only_output")

    # 3. Malformed hunk headers
    hunk_errors = _validate_hunk_headers(body)
    if hunk_errors:
        rejections.extend(hunk_errors)

    # 4. git apply --check
    git_check_result: dict[str, Any] | None = None
    if run_git_check and not rejections:
        git_check_result = _git_apply_check(body, repo_root=Path(repo_root).resolve())
        if git_check_result.get("returncode") != 0:
            stderr = str(git_check_result.get("stderr") or git_check_result.get("error") or "")
            rejections.append(f"git_apply_check_failed: {stderr[:200]}")

    ok = not rejections
    return PatchPreflightResult(
        ok=ok,
        rejections=rejections,
        git_check_result=git_check_result,
        diff=diff,
    )


def generate_unified_diff_from_before_after(
    replacement: BeforeAfterReplacement,
    *,
    repo_root: str | Path,
) -> str:
    """Generate a proper unified diff locally from a before/after replacement.

    Uses Python's difflib.unified_diff to produce deterministic hunk headers
    — the model never hand-writes @@ headers.

    Research basis: SWE-agent's "do not rely on model for hunk headers";
    Agentless's local diff generation.
    """
    root = Path(repo_root).resolve()
    file_path = root / replacement.target_file

    if not file_path.exists():
        # For new files, generate an add-file diff
        after_lines = replacement.after_text.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            [],
            after_lines,
            fromfile="/dev/null",
            tofile=f"b/{replacement.target_file}",
        ))
        return "".join(diff_lines)

    original_text = file_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines(keepends=True)

    # Locate the before_text in the original file
    before_text = replacement.before_text
    if before_text in original_text:
        # Replace the exact before_text with after_text
        modified_text = original_text.replace(before_text, replacement.after_text, 1)
    else:
        # Try whitespace-normalized matching
        before_stripped = before_text.strip()
        # Find a block that matches when stripped
        original_lines_list = original_text.splitlines()
        before_lines_stripped = [line.strip() for line in before_stripped.splitlines()]
        match_start = -1
        for i in range(len(original_lines_list) - len(before_lines_stripped) + 1):
            window = [line.strip() for line in original_lines_list[i:i + len(before_lines_stripped)]]
            if window == before_lines_stripped:
                match_start = i
                break
        if match_start >= 0:
            match_end = match_start + len(before_lines_stripped)
            modified_lines = (
                original_lines_list[:match_start]
                + replacement.after_text.splitlines()
                + original_lines_list[match_end:]
            )
            modified_text = "\n".join(modified_lines)
            if original_text.endswith("\n"):
                modified_text += "\n"
        else:
            # Cannot locate before_text — return empty diff (will be rejected by preflight)
            return ""

    modified_lines = modified_text.splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{replacement.target_file}",
        tofile=f"b/{replacement.target_file}",
        lineterm="",
    ))

    # Ensure proper line endings
    result_lines: list[str] = []
    for line in diff_lines:
        if not line.endswith("\n"):
            result_lines.append(line + "\n")
        else:
            result_lines.append(line)
    return "".join(result_lines)


def parse_before_after_response(text: str) -> BeforeAfterReplacement | None:
    """Attempt to parse a model response as a before/after replacement object.

    Returns None if the response is not a before/after JSON object.
    """
    body = str(text or "").strip()
    # Strip code fences
    fenced = re.search(r"```(?:json)?\s*(.*?)```", body, re.DOTALL | re.IGNORECASE)
    if fenced:
        body = fenced.group(1).strip()

    # Try to find a JSON object
    match = re.search(r"\{.*\}", body, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return BeforeAfterReplacement.from_dict(data)
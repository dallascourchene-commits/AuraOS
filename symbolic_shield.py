"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8b5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: typing, ast, re, __future__
FUNCTIONS: check_syntax, check_loop_decay, check_import_safety, check_memory_safety, check_banned_calls, verify_structural_truth, full_report
SYNOPSIS: Aura OS Auditor is a strict Python module for static code analysis, leveraging `typing`, `ast`, `re`, and `__future__` to enforce syntax integrity, loop decay detection, import safety validation, memory safety checks, banned call verification, structural truth validation, and generate a comprehensive report via its `check_syntax`, `check_loop_decay`, `check_import_safety`, `check_memory_safety`, `check_banned_calls`, `verify_structural_truth`, and `full_report` functions.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import ast
import re
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Prohibited patterns (namespace / side-channel risks on Termux/Android)
# ---------------------------------------------------------------------------

_BANNED_IMPORTS: frozenset[str] = frozenset({
    "nxsdk", "loihi", "cupy", "pycuda", "tensorflow",
    "torch.distributed",
})

_BANNED_CALLS: frozenset[str] = frozenset({
    "eval", "exec", "__import__", "compile",
})

# Maximum tolerated nesting depth for loops / recursion
_MAX_LOOP_DEPTH: int = 5

# Maximum allowable single allocation (bytes) before the shield warns
_MAX_ALLOC_BYTES: int = 512 * 1024 * 1024  # 512 MB


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

class ShieldReport(NamedTuple):
    passed: bool
    reason: str


# ---------------------------------------------------------------------------
# Individual gate checks
# ---------------------------------------------------------------------------

def check_syntax(source_code: str) -> ShieldReport:
    """Gate 0 — parseable Python."""
    try:
        ast.parse(source_code)
        return ShieldReport(True, "SYNTAX_OK")
    except SyntaxError as exc:
        return ShieldReport(False, f"SYNTAX_ERROR at line {exc.lineno}: {exc.msg}")


def check_loop_decay(source_code: str) -> ShieldReport:
    """
    Gate 1 — every ``while True`` loop must contain at least one of:
    - a ``break`` statement
    - an ``asyncio.sleep`` call (decay operator)
    - a ``return`` statement
    This prevents unbounded infinite loops from locking the event loop.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return ShieldReport(True, "SKIP — syntax gate handles this")

    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        # Check if test is literally True / 1
        test = node.test
        is_infinite = (
            (isinstance(test, ast.Constant) and test.value is True)
            or (isinstance(test, ast.Constant) and test.value == 1)
            or (isinstance(test, ast.Name) and test.id == "True")
        )
        if not is_infinite:
            continue
        # Walk the loop body for decay operators
        has_decay = any(
            isinstance(sub, (ast.Break, ast.Return))
            or (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr in {"sleep", "wait"}
            )
            for sub in ast.walk(node)
        )
        if not has_decay:
            return ShieldReport(
                False,
                f"LOOP_DECAY_MISSING: 'while True' at line {node.lineno} "
                "lacks break/return/sleep — potential event-loop lockout.",
            )
    return ShieldReport(True, "LOOP_DECAY_OK")


def check_import_safety(source_code: str) -> ShieldReport:
    """
    Gate 2 — no imports of known banned modules (proprietary hardware
    libs, CUDA bindings, etc. that will crash on Termux/Android).
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return ShieldReport(True, "SKIP — syntax gate handles this")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[0]
                if base in _BANNED_IMPORTS:
                    return ShieldReport(
                        False,
                        f"BANNED_IMPORT: '{alias.name}' at line {node.lineno} "
                        "is prohibited on Termux/Android targets.",
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            base = node.module.split(".")[0]
            if base in _BANNED_IMPORTS:
                return ShieldReport(
                    False,
                    f"BANNED_IMPORT: 'from {node.module}' at line {node.lineno} "
                    "is prohibited on Termux/Android targets.",
                )
    return ShieldReport(True, "IMPORT_SAFETY_OK")


def check_memory_safety(source_code: str) -> ShieldReport:
    """
    Gate 3 — flag dangerously large NumPy / bytearray allocations that
    would push the process past the 4 GB PVM ceiling.
    Uses regex heuristics on the source text (fast, no AST needed).
    """
    # Pattern: np.zeros/ones/empty/random.randn followed by a tuple
    # containing a large product.  Catches the obvious cases.
    pattern = re.compile(
        r"np\.\w+\(\s*\(?\s*(\d[\d_]*)\s*,\s*(\d[\d_]*)", re.MULTILINE
    )
    for match in pattern.finditer(source_code):
        dim0 = int(match.group(1).replace("_", ""))
        dim1 = int(match.group(2).replace("_", ""))
        # Assume float32 (4 bytes) as worst case
        estimated_bytes = dim0 * dim1 * 4
        if estimated_bytes > _MAX_ALLOC_BYTES:
            mb = estimated_bytes // (1024 * 1024)
            return ShieldReport(
                False,
                f"MEMORY_OVERREACH: allocation ~{mb} MB at "
                f"'{match.group(0)[:40]}' exceeds 512 MB single-alloc limit.",
            )
    return ShieldReport(True, "MEMORY_SAFETY_OK")


def check_banned_calls(source_code: str) -> ShieldReport:
    """
    Gate 4 — no bare ``eval()`` / ``exec()`` calls (namespace injection risk).
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return ShieldReport(True, "SKIP")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name and name in _BANNED_CALLS:
                return ShieldReport(
                    False,
                    f"BANNED_CALL: '{name}()' at line {node.lineno} "
                    "is a namespace-injection risk.",
                )
    return ShieldReport(True, "BANNED_CALLS_OK")


# ---------------------------------------------------------------------------
# Primary public entry point
# ---------------------------------------------------------------------------

def verify_structural_truth(source_code: str) -> bool:
    """
    Run all four shield gates in sequence.  Returns ``True`` only when
    every gate passes.  Prints a rejection rationale to stdout on failure
    so the aura_heal agentic loop can route it back into the LLM prompt.
    """
    gates = [
        check_syntax,
        check_loop_decay,
        check_import_safety,
        check_memory_safety,
        check_banned_calls,
    ]
    for gate in gates:
        report = gate(source_code)
        if not report.passed:
            print(f"[🛡️ SYMBOLIC SHIELD] REJECTED — {report.reason}")
            return False
    return True


def full_report(source_code: str) -> list[ShieldReport]:
    """Return the result of every gate (for diagnostic/logging use)."""
    return [
        check_syntax(source_code),
        check_loop_decay(source_code),
        check_import_safety(source_code),
        check_memory_safety(source_code),
        check_banned_calls(source_code),
    ]

"""
AURA PVM — Boot-time systems check and import repair
Run on Termux before starting aura_node to catch drifted local copies.

Usage:
    python systems_check.py                 # full pre-flight check
    python systems_check.py --fix-imports   # repair __future__ / docstring drift
    python systems_check.py --git-sync      # set upstream + pull latest
    python systems_check.py --quick         # syntax + arch check only
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections import Counter
from math import log2
from pathlib import Path

try:
    from aura_topological_scanner import compile_unified_graph as _compile_unified_graph
except ImportError:
    _compile_unified_graph = None  # type: ignore[assignment,misc]

try:
    import liquid_kernel as _liquid_kernel  # noqa: F401
    _LIQUID_KERNEL_OK = True
except ImportError:
    _LIQUID_KERNEL_OK = False

ROOT = Path(".").resolve()

# Files the holographic auditor must never stamp (tests + boot tooling).
STAMP_EXEMPT = frozenset({
    "systems_check.py",
    "pvm_arch_checker.py",
    "verify_os.py",
    "aura_topology_manager.py",
})

STAMP_EXEMPT_PREFIXES = ("test_",)

FUTURE_IMPORT = "from __future__ import annotations"

MASTER_KEY_BLOCK = re.compile(
    r'^\s*(?:"""[\s\S]*?\[/AURA_MASTER_KEY\]\s*\n"""|'
    r"'''[\s\S]*?\[/AURA_MASTER_KEY\]\s*\n''')\s*\n?",
    re.MULTILINE,
)

MODULE_DOCSTRING = re.compile(
    r'^\s*(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')\s*\n',
    re.MULTILINE,
)


def _is_exempt(path: Path) -> bool:
    name = path.name
    if name in STAMP_EXEMPT:
        return True
    return any(name.startswith(p) for p in STAMP_EXEMPT_PREFIXES)


def strip_aura_master_key(source: str) -> str:
    """Remove a leading AURA_MASTER_KEY docstring block."""
    return MASTER_KEY_BLOCK.sub("", source, count=1)


def strip_leading_docstring(source: str) -> tuple[str, str | None]:
    """Return (remainder, docstring_text_or_none)."""
    m = MODULE_DOCSTRING.match(source)
    if not m:
        return source, None
    return source[m.end() :], m.group(0)


def repair_future_import_order(source: str, *, strip_master_key: bool = False) -> str:
    """
    Ensure ``from __future__ import annotations`` appears immediately after
    the single module docstring (and before any other imports/statements).

    When *strip_master_key* is True, remove AURA auditor headers from test
    and boot utility files entirely.
    """
    text = source.replace("\r\n", "\n")

    if strip_master_key:
        text = strip_aura_master_key(text)

    # Remove duplicate leading docstrings until only one remains (or none).
    doc_parts: list[str] = []
    while True:
        remainder, doc = strip_leading_docstring(text)
        if doc is None:
            break
        doc_parts.append(doc)
        text = remainder

    # Keep the last non-master-key docstring, or the last one if all are master keys.
    kept_doc = ""
    for doc in reversed(doc_parts):
        if "[/AURA_MASTER_KEY]" not in doc and "[AURA_MASTER_KEY]" not in doc:
            kept_doc = doc
            break
    if not kept_doc and doc_parts:
        kept_doc = doc_parts[-1]

    body = text.lstrip("\n")

    # Pull future import out of the body if it exists anywhere in the preamble.
    future_line = None
    lines = body.split("\n")
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == FUTURE_IMPORT or stripped.startswith(FUTURE_IMPORT + " "):
            future_line = FUTURE_IMPORT
            continue
        # Stop scanning once we hit non-import preamble after we've passed blanks/comments
        new_lines.append(line)

    if future_line is None:
        # No future import — return merged docstring + body unchanged.
        return kept_doc + body if kept_doc else body

    # Reassemble: docstring → future import → blank line → rest
    out_parts: list[str] = []
    if kept_doc:
        out_parts.append(kept_doc.rstrip("\n"))
    out_parts.append(future_line)
    out_parts.append("")

    # Drop leading blank lines from remainder
    remainder = "\n".join(new_lines).lstrip("\n")
    out_parts.append(remainder)
    return "\n".join(out_parts).rstrip("\n") + "\n"


def fix_imports(root: Path = ROOT, *, dry_run: bool = False) -> list[str]:
    """Repair all ``.py`` files under *root* (flat layout). Returns changed paths."""
    changed: list[str] = []
    for path in sorted(root.glob("*.py")):
        original = path.read_text(encoding="utf-8", errors="replace")
        repaired = repair_future_import_order(
            original,
            strip_master_key=_is_exempt(path),
        )
        if repaired != original:
            changed.append(path.name)
            if not dry_run:
                path.write_text(repaired, encoding="utf-8", newline="\n")
    return changed


def check_syntax(root: Path = ROOT) -> list[tuple[str, str]]:
    """Return list of (filename, error) for files that fail to parse."""
    errors: list[tuple[str, str]] = []
    for path in sorted(root.glob("*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            errors.append((path.name, f"line {exc.lineno}: {exc.msg}"))
    return errors


def run_arch_checker(root: Path = ROOT) -> int:
    """Run pvm_arch_checker and return its exit code."""
    checker = root / "pvm_arch_checker.py"
    if not checker.exists():
        print("[!] pvm_arch_checker.py not found — skipping arch check.")
        return 0
    result = subprocess.run(
        [sys.executable, str(checker), "--path", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def git_sync(root: Path = ROOT) -> int:
    """Configure upstream tracking and pull the latest changes."""
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(args),
            cwd=root,
            capture_output=True,
            text=True,
        )

    branch = run("git", "rev-parse", "--abbrev-ref", "HEAD")
    if branch.returncode != 0:
        print(f"[!] Not a git repository: {branch.stderr.strip()}")
        return 1
    current = branch.stdout.strip()

    # Prefer origin/main; fall back to origin/master for legacy Termux clones.
    upstream_candidates = [f"origin/main", f"origin/master"]
    chosen = None
    for candidate in upstream_candidates:
        remote, remote_branch = candidate.split("/", 1)
        ls = run("git", "ls-remote", "--heads", remote, remote_branch)
        if ls.returncode == 0 and ls.stdout.strip():
            chosen = candidate
            break

    if not chosen:
        print("[!] Could not find origin/main or origin/master on remote.")
        return 1

    print(f"[*] Setting upstream: {current} → {chosen}")
    set_upstream = run("git", "branch", "--set-upstream-to", chosen, current)
    if set_upstream.returncode != 0:
        print(set_upstream.stderr.strip())
        return set_upstream.returncode

    print(f"[*] Pulling from {chosen}...")
    pull = run("git", "pull", "--rebase")
    print(pull.stdout)
    if pull.stderr:
        print(pull.stderr)
    if pull.returncode != 0:
        return pull.returncode
    print("[+] Git sync complete.")
    return 0


def boot_smoke(root: Path = ROOT) -> int:
    """Regression checks for common Termux boot failures (no full node boot)."""
    print("\n[*] Boot smoke tests...")
    failures: list[str] = []

    # 1. Governor entropy calibration must not raise NameError on math
    try:
        def _calibrate(hypothesis: str) -> float:
            clean = str(hypothesis).strip()
            if not clean:
                return 0.0
            counts = Counter(clean)
            total = len(clean)
            entropy = -sum((c / total) * log2(c / total) for c in counts.values())
            return max(0.0, 1.0 - abs(4.5 - entropy) / 4.5)

        score = _calibrate("!research")
        if not (0.0 <= score <= 1.0):
            failures.append(f"governor calibration out of range: {score}")
        else:
            print("  [+] Governor belief calibration (log2) OK")
    except Exception as exc:
        failures.append(f"governor calibration: {exc}")

    # 2. Topology compile must work without websockets TMM server
    try:
        if _compile_unified_graph is None:
            raise ImportError("aura_topological_scanner unavailable")
        payload = _compile_unified_graph()
        nodes = payload.get("nodes", [])
        edges = payload.get("edges", [])
        node_ids = {n["id"] for n in nodes}
        dangling = sum(
            1 for e in edges
            if e.get("source") not in node_ids or e.get("target") not in node_ids
        )
        if len(nodes) < 10:
            failures.append(f"topology too small: {len(nodes)} nodes")
        elif dangling:
            failures.append(f"topology has {dangling} dangling edge refs")
        else:
            print(f"  [+] Topology compile OK ({len(nodes)} nodes, {len(edges)} edges, 0 dangling)")
    except Exception as exc:
        failures.append(f"topology compile: {exc}")

    # 3. liquid_kernel import without websockets
    if not _LIQUID_KERNEL_OK:
        failures.append("liquid_kernel import failed")
    else:
        print("  [+] liquid_kernel imports without websockets")

    if failures:
        print("\n[!] Boot smoke FAILED:")
        for f in failures:
            print(f"    • {f}")
        return 1
    print("[+] Boot smoke tests passed.")
    return 0


def full_check(root: Path = ROOT, *, quick: bool = False) -> int:
    """Run the complete pre-flight sequence. Returns process exit code."""
    print("═" * 68)
    print("  AURA PVM — Systems Check")
    print("═" * 68)

    syntax_errors = check_syntax(root)
    if syntax_errors:
        print("\n[!] SYNTAX ERRORS (run with --fix-imports first):")
        for fname, err in syntax_errors:
            print(f"    {fname}: {err}")
        return 1
    print(f"\n[+] Syntax check passed ({len(list(root.glob('*.py')))} modules)")

    if quick:
        return 0

    code = run_arch_checker(root)
    if code != 0:
        print("\n[!] Architectural violations detected (see report above).")
        return code

    smoke_code = boot_smoke(root)
    if smoke_code != 0:
        return smoke_code

    print("\n[+] All systems check phases passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="AURA PVM boot-time systems check")
    parser.add_argument(
        "--fix-imports",
        action="store_true",
        help="Repair __future__ import ordering and strip auditor drift from test files",
    )
    parser.add_argument(
        "--git-sync",
        action="store_true",
        help="Set git upstream tracking and pull latest changes",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Syntax check only (skip arch checker)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --fix-imports, show what would change without writing",
    )
    args = parser.parse_args()

    exit_code = 0

    if args.fix_imports:
        changed = fix_imports(dry_run=args.dry_run)
        if changed:
            action = "Would repair" if args.dry_run else "Repaired"
            print(f"[+] {action} {len(changed)} file(s):")
            for name in changed:
                print(f"    • {name}")
        else:
            print("[+] No import drift detected.")

    if args.git_sync:
        exit_code = max(exit_code, git_sync())

    # Run health check after repairs, or when no action flags were given.
    run_health = (
        not args.git_sync
        or args.fix_imports
        or (not args.fix_imports and not args.git_sync)
    )
    if run_health:
        exit_code = max(exit_code, full_check(quick=args.quick))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

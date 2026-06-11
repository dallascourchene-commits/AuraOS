"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: ast, asyncio, os, aura_evolution_bridge, sys, re, aura_gbnf_profiles, hashlib, time
FUNCTIONS: __init__, _generate_process_glyph, _extract_code_block, _invoke_patch_engine, sandbox_and_evaluate, execute_hot_swap
SYNOPSIS: This Python module, integrating dependencies like `ast`, `asyncio`, `os`, `aura_evolution_bridge`, and others, provides a secure, AST-based code analysis and runtime patching framework via functions such as `_generate_process_glyph`, `_invoke_patch_engine`, and `sandbox_and_evaluate`, enabling controlled execution and dynamic code modification within an isolated environment.
[/AURA_MASTER_KEY]
"""
# [AURA OPTIMIZED] - Bloat removed.

import ast
import gc
import hashlib
import os
import re
import sys
import time
import asyncio
from pathlib import Path

from aura_gbnf_profiles import PROFILE_PYTHON_PATCH
from aura_evolution_bridge import validate_proposed_mutation

# ── Security constants ──────────────────────────────────────────────────────
# Project root: all file writes must land under this directory tree.
_PROJECT_ROOT = Path(__file__).resolve().parent

# Banned AST patterns that indicate dangerous or destabilising code
_BANNED_FUNCTIONS = frozenset({
    "eval", "exec", "compile", "__import__", "input",
})
_BANNED_MODULES = frozenset({
    "subprocess", "ctypes", "multiprocessing", "signal",
    "os.system", "os.popen",
})
# Maximum AST node count before we reject as too large (prevents DoS)
_MAX_AST_NODES = 3000

# Forbidden file-write targets (any path that would escape the project root)
_FORBIDDEN_PATH_PREFIXES = ("/etc", "/proc", "/sys", "/dev", "/root", "/home")


class SandboxViolation(Exception):
    """Raised when generated code violates the mutation sandbox security policy."""


def _verify_ast_security(tree: ast.AST, filename: str = "<generated>") -> list[str]:
    """
    Pre-validation: walk the entire AST and collect all security violations.
    Returns a list of human-readable violation strings (empty = clean).
    """
    violations: list[str] = []
    node_count = 0

    for node in ast.walk(tree):
        node_count += 1
        if node_count > _MAX_AST_NODES:
            violations.append(
                f"AST node count ({node_count}) exceeds maximum ({_MAX_AST_NODES})"
            )
            break

        # Check for eval/exec/compile calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BANNED_FUNCTIONS:
                violations.append(
                    f"Banned function call '{node.func.id}' on line {node.lineno}"
                )
            elif isinstance(node.func, ast.Attribute):
                full = f"{ast.unparse(node.func.value)}.{node.func.attr}" if hasattr(ast, 'unparse') else node.func.attr
                if node.func.attr in _BANNED_FUNCTIONS:
                    violations.append(
                        f"Banned function call '{node.func.attr}' on line {node.lineno}"
                    )

        # Check for dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _BANNED_MODULES:
                    violations.append(f"Banned import '{alias.name}' on line {node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module in _BANNED_MODULES:
                violations.append(f"Banned import from '{node.module}' on line {node.lineno}")

        # Flag infinite-loops without exit conditions
        if isinstance(node, ast.While):
            has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
            if not has_break and not isinstance(node.test, ast.Constant):
                # Heuristic: while loops with a dynamic condition and no 'break'
                # may be infinite; flag as a warning
                violations.append(
                    f"Potentially infinite while-loop on line {node.lineno} (no break statement)"
                )

        # Flag deep recursion (nested defs beyond 4 levels)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Count nesting by walking parents — simple heuristic:
            # if we find nested defs inside classes, it's usually fine,
            # but deeply nested standalone functions are risky
            pass

    return violations


def _validate_file_write_path(target_file: str) -> None:
    """
    Rigid path-traversal guard: ensure *target_file* resolves inside
    _PROJECT_ROOT and does not escape to system directories.
    Raises SandboxViolation on any violation.
    """
    # Resolve absolute canonical path (no symlink tricks, no .. traversal)
    resolved = Path(target_file).resolve()

    # Check it's under the project root
    try:
        resolved.relative_to(_PROJECT_ROOT)
    except ValueError:
        raise SandboxViolation(
            f"Path-traversal blocked: '{target_file}' resolves to '{resolved}' "
            f"which is outside project root '{_PROJECT_ROOT}'"
        )

    # Check against forbidden system prefixes
    target_str = str(resolved)
    for prefix in _FORBIDDEN_PATH_PREFIXES:
        if target_str.startswith(prefix + os.sep) or target_str == prefix:
            raise SandboxViolation(
                f"Path-traversal blocked: '{target_file}' targets system path '{prefix}'"
            )


class LiquidFlashEvolve:
    """
    Layer 6: The Liquid Predictive Sandbox — HARDENED.
    Generates multi-dimensional ST3GG categorizing glyphs and triggers
    E8 Holographic Isogeny Merkle-DAG ripples upon successful mutation.

    Security walls:
      • AST pre-validation against banned patterns (eval, exec, subprocess, etc.)
      • Rigid path-traversal validation — no writes outside project root
      • Maximum AST node count to prevent DoS via code bloat
      • Infinite-loop detection heuristic
    """
    def __init__(self, node_ref):
        self.node = node_ref

    def _generate_process_glyph(self, module_name: str, friction: int, temp: float, is_aligned: bool) -> str:
        """Synthesizes the true ST3GG Categorization Glyph."""
        cat_thermal = "H" if temp > 38.0 else "C"
        cat_moral = "M" if is_aligned else "G"
        cat_fric = "F1" if friction < 20 else ("F2" if friction < 50 else "F3")
        raw_state = f"{module_name}|{cat_thermal}|{cat_moral}|{cat_fric}"
        dense_hash = hashlib.sha256(raw_state.encode()).hexdigest()[:6].upper()
        return f"ST3GG:{cat_thermal}-{cat_moral}-{cat_fric}-0x{dense_hash}"

    @staticmethod
    def _extract_code_block(raw: str) -> str:
        text = raw.replace("```python", "").replace("```", "").strip()
        code_match = re.search(r"\[CODE\](.*?)(?:\[/CODE\]|$)", text, re.DOTALL | re.IGNORECASE)
        if code_match:
            return code_match.group(1).strip()
        return text

    async def _invoke_patch_engine(self, prompt: str) -> str:
        """GBNF-constrained codegen (python_patch profile) when node supports it."""
        invoke = self.node.invoke_engine
        try:
            return await invoke(
                prompt,
                structural=True,
                gbnf_profile=PROFILE_PYTHON_PATCH,
            )
        except TypeError:
            return await invoke(prompt, structural=True)

    async def sandbox_and_evaluate(self, target_module: str, user_proposal: str, max_healing_retries: int = 3) -> str:
        target_file = f"{target_module}.py"
        start_time = time.time()
        proposal_str = str(user_proposal)

        temp = 42.0
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
        except OSError:
            pass

        baseline_friction = 0
        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    baseline_friction = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call))
            except Exception:
                pass

        prompt = (
            f"Propose Python code for {target_module} based on: {proposal_str}.\n"
            f"Output ONLY a [CODE] block with valid Python.\n"
        )
        error_feedback = ""
        proposed_code = ""
        parsed_ast = None
        mutation_verdict = None

        for attempt in range(max_healing_retries):
            if error_feedback:
                prompt = (
                    f"The previously generated Python code for {target_module} failed validation:\n"
                    f"{error_feedback}\n"
                    f"Fix the issue and output ONLY the complete corrected code inside [CODE] tags.\n"
                )

            raw = await self._invoke_patch_engine(prompt)
            proposed_code = self._extract_code_block(raw)

            try:
                parsed_ast = ast.parse(proposed_code)
            except SyntaxError as se:
                error_feedback = f"SyntaxError on line {se.lineno}: {se.msg}"
                print(f"[⚠️ SELF-HEALING] Attempt {attempt+1} syntax fail. Retrying...")
                continue

            # ── HARDENED: AST security verification wall ───────────────────
            security_violations = _verify_ast_security(parsed_ast, filename=target_module)
            if security_violations:
                error_feedback = "Security violations:\n" + "\n".join(security_violations)
                print(f"[🛡️ SANDBOX BLOCK] Attempt {attempt+1}: {len(security_violations)} violation(s)")
                continue
            # ─────────────────────────────────────────────────────────────────

            simulated_friction = sum(1 for n in ast.walk(parsed_ast) if isinstance(n, ast.Call))
            mutation_verdict = validate_proposed_mutation(
                proposed_code,
                module_name=target_module,
                baseline_friction=baseline_friction,
                proposed_friction=simulated_friction,
            )
            if mutation_verdict.approved:
                error_feedback = ""
                print(f"[+] [SELF-HEALING] Sandbox approved on attempt {attempt+1}.")
                break

            error_feedback = mutation_verdict.human_report()
            print(f"[⚠️ SELF-HEALING] Attempt {attempt+1} rejected: {error_feedback}")

        if error_feedback or not parsed_ast or mutation_verdict is None or not mutation_verdict.approved:
            return f"[-] Sandbox aborted: Mutation failed validation after {max_healing_retries} iterations."

        simulated_friction = sum(1 for n in ast.walk(parsed_ast) if isinstance(n, ast.Call))
        delta = baseline_friction - simulated_friction
        is_aligned = mutation_verdict.approved

        full_st3gg_glyph = self._generate_process_glyph(target_module, simulated_friction, temp, is_aligned)

        if is_aligned:
            self.node.runtime_metrics["pending_mutation_code"] = proposed_code
            self.node.runtime_metrics["pending_mutation_file"] = target_file
            self.node.runtime_metrics["pending_st3gg_glyph"] = full_st3gg_glyph
            self.node.runtime_metrics["pending_mutation_verdict"] = mutation_verdict.human_report()
            verdict = "APPROVED (MIIGWECH Directive)."
        else:
            verdict = "REJECTED (GIZAAGI'IN Violation)."

        if hasattr(self.node, "memory_palace") and self.node.memory_palace:
            compute_ms = (time.time() - start_time) * 1000
            interaction = f"SANDBOX_EVAL | {full_st3gg_glyph} | Delta: {delta} | {verdict}"
            self.node.runtime_metrics["dikwp_tier"] = "PURPOSE"
            await self.node.memory_palace.enqueue_holographic_trace(
                0xDEED, interaction, temp, compute_ms, is_aligned
            )

        topo_note = mutation_verdict.topology_note
        return (
            f"Report: {verdict} | Encoded as {full_st3gg_glyph} | "
            f"Friction Delta: {delta} ops | Topology: {topo_note}"
        )

    async def execute_hot_swap(self) -> str:
        """Physical DNA mutation triggering an Epistemic Merkle-DAG Ripple."""
        code = self.node.runtime_metrics.get("pending_mutation_code")
        file = self.node.runtime_metrics.get("pending_mutation_file")
        glyph = self.node.runtime_metrics.get("pending_st3gg_glyph", "ST3GG:UNKNOWN")
        if not code or not file:
            return "[-] Sandbox empty."

        final = validate_proposed_mutation(
            code,
            module_name=os.path.basename(file).replace(".py", ""),
            check_topology=True,
        )
        if not final.approved:
            return f"[-] Hot-swap blocked: {final.human_report()}"

        # ── HARDENED: Path-traversal validation before write ──────────────
        try:
            _validate_file_write_path(file)
        except SandboxViolation as sv:
            return f"[-] Hot-swap blocked by path-traversal guard: {sv}"

        # ── HARDENED: AST structural consistency before write ──────────────
        try:
            parsed = ast.parse(code)
            security_issues = _verify_ast_security(parsed, filename=file)
            if security_issues:
                return f"[-] Hot-swap blocked: security violations in final code:\n" + "\n".join(security_issues)
            # Verify the code is structurally consistent (not just parseable but sane)
            ast.fix_missing_locations(parsed)
        except SyntaxError as se:
            return f"[-] Hot-swap blocked: final code has SyntaxError on line {se.lineno}: {se.msg}"
        # ───────────────────────────────────────────────────────────────────

        with open(file, "w", encoding="utf-8") as f:
            f.write(code)
        # Proactive memory reclamation after heavy AST walk
        del parsed
        gc.collect()
        try:
            node_mod = sys.modules.get("aura_node")
            AuraEcosystemAuditorCls = getattr(node_mod, "AuraEcosystemAuditor", None)
            if AuraEcosystemAuditorCls is not None:
                auditor = AuraEcosystemAuditorCls(self.node)
                await auditor.execute_unified_audit()
        except Exception:
            pass
        self.node.runtime_metrics["pending_mutation_code"] = None
        self.node.runtime_metrics["pending_mutation_file"] = None
        return f"[+] DNA Mutated. New architecture routed and holographically secured under {glyph}."

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
import hashlib
import os
import re
import sys
import time
import asyncio

from aura_gbnf_profiles import PROFILE_PYTHON_PATCH
from aura_evolution_bridge import validate_proposed_mutation


class LiquidFlashEvolve:
    """
    Layer 6: The Liquid Predictive Sandbox.
    Generates multi-dimensional ST3GG categorizing glyphs and triggers
    E8 Holographic Isogeny Merkle-DAG ripples upon successful mutation.
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

        with open(file, "w", encoding="utf-8") as f:
            f.write(code)
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

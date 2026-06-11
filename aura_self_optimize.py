"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Governed Self-Repair)
DEPENDENCIES: argparse, aura_proxy_benchmark, aura_router, aura_matrix_benchmark
FUNCTIONS: build_fix_task, self_optimize
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Self-Optimize — self-repair through the optimal-routing pipeline.
=====================================================================

Replaces the old "free-form a vague refactor and call the cloud directly" path.
A self-improvement task is built as a scoped TestCase (one target function),
compressed by the substrate, routed to the best-available model (auto-router),
returned as a compact json_edit_plan / diff, **ASCII-sanitized**, verified
(AST parse, no fabricated files, no new deps, signature preserved, minimal
scope), and **retried with the verifier's error fed back** when a safety check
fails. The validated diff is returned for operator approval — it is NOT written
to disk or committed here (that stays a gated step).

Run:
    python3 aura_self_optimize.py --target-file aura_dream_engine.py \
        --target-func _compute_resonance \
        --instruction "Normalize both vectors to unit length in float64 and guard
                       zero norms before the dot product so resonance cannot overflow."
    python3 aura_self_optimize.py ... --model mistral      # force a model
    python3 aura_self_optimize.py ... --mock               # offline
"""

from __future__ import annotations

import argparse

from aura_proxy_benchmark import TestCase
from aura_router import AutoRouter
from aura_matrix_benchmark import MockEgress
from aura_llm_egress import ExternalLLM
AURA_CORE_GUARDRAILS = """
CRITICAL ARCHITECTURAL CONSTRAINTS FOR CODE GENERATION:
1. The Asynchronous Mandate: You are patching an asynchronous, event-loop-driven system. You MUST NOT introduce synchronous blocking I/O (like sqlite3, requests, or time.sleep()) inside async functions. Use aiosqlite, asyncio.sleep(), or offload to asyncio.to_thread.
2. Hardware & Memory Bounds: The target hardware is a Motorola Moto G Stylus running Termux (ARM64) with a strict 4GB RAM ceiling. You MUST prioritize zero-copy operations, use numpy arrays (with explicitly defined types like np.float32 or np.int8) over Python lists, and avoid heavy object instantiation in loops.
3. Compilation & Execution Targets: Core logic is Python. High-performance accelerators are written in Rust and compiled to WebAssembly (wasm32-wasi), executed via Wasmtime. DO NOT provide C/C++ or gcc compilation flags.
4. Topological Hygiene: Do not invent new standalone databases or loose files in the root directory. All persistent data MUST be routed to the Aura_Memory/ directory. Rely on existing native methods (e.g., logging_kit.log_report()) rather than writing standard Python logging boilerplate.
5. Output Format: You must output ONLY the raw, refactored code enclosed within exact [CODE] and [/CODE] delimiters so the GBNF parser can extract it cleanly. Do not use markdown code blocks.
"""

def build_fix_task(target_file: str, target_func: str, instruction: str,
                   task_type: str = "patch", op: str = "OP:PATCH",
                   termux_safe: bool = True) -> TestCase:
    """Build a scoped self-repair TestCase for one target function."""
    tags = ["ENV:PYTHON", op, f"TARGET:{target_func.upper()}",
            "CONSTRAINT:NO_NEW_DEPS", "CONSTRAINT:PRESERVE_PROTOCOL",
            "VERIFY:AST_PARSE", "OUTPUT:UNIFIED_DIFF"]
    if termux_safe:
        tags.insert(4, "CONSTRAINT:RUNS_ON_TERMUX_AARCH64")
    return TestCase(
        key=f"selfopt_{target_func}",
        human_prompt=instruction,
        target_file=target_file,
        target_func=target_func,
        output_format="unified_diff",
        packet_tags=tags,
        task_type=task_type,
    )


def self_optimize(target_file: str, target_func: str, instruction: str,
                  forced_model: str | None = None, mock: bool = False,
                  max_retries: int = 2) -> dict:
    """Route a scoped self-repair task through the optimal pipeline."""
    factory = (lambda p: MockEgress(provider=p)) if mock else (lambda p: ExternalLLM(provider=p))
    router = AutoRouter(egress_factory=factory)
    task = build_fix_task(target_file, target_func, instruction)
    return router.route_task(task, forced_model=forced_model, mock=mock,
                             aspect="self_optimize", max_retries=max_retries)
    # Inject core architectural guardrails into the prompt payload
    task_prompt += f"\n\n{AURA_CORE_GUARDRAILS}"

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aura self-optimize via optimal routing")
    p.add_argument("--target-file", required=True)
    p.add_argument("--target-func", required=True)
    p.add_argument("--instruction", required=True)
    p.add_argument("--model", default=None, help="force a specific model")
    p.add_argument("--mock", action="store_true")
    p.add_argument("--max-retries", type=int, default=2)
    args = p.parse_args(argv)

    res = self_optimize(args.target_file, args.target_func, args.instruction,
                        forced_model=args.model, mock=args.mock, max_retries=args.max_retries)
    if not res["ok"]:
        print(f"[-] self-optimize failed: {res['reason']}")
        return 1
    rec = res["record"]
    verdict = "ACCEPTED" if res["accepted"] else "NEEDS REVIEW (safety check failed)"
    print(f"[+] {verdict} | {rec['chosen_provider']}/{rec['style']}/{rec['output_mode']} "
          f"attempts={rec['attempts']} quality={rec['quality']}")
    print(f"    checks: {res['checks']}")
    if res["notes"]:
        print(f"    notes: {res['notes']}")
    print("\n--- proposed diff (NOT applied — operator approval required) ---")
    print(res["artifact"][:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

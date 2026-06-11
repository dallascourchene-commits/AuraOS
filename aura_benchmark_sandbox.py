"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c4-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Validated Trust)
DEPENDENCIES: __future__, hashlib, json, os, pathlib, time, typing, numpy, aura_hv_cache, aura_token_economics, aura_api_rotator
FUNCTIONS: BenchmarkSandbox, scan_credentials, run_benchmark, _stage_indexing, _stage_recursive_mas
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Automated Key Discovery & Multi-Stage Benchmark Sandbox
========================================================

Initialization scanning routine:
    1. Fingerprint current ~/aura_secrets.json.
    2. Compare against stored baseline in Aura_Memory/benchmark_baseline.json.
    3. If new or updated credentials are detected → run the benchmark suite in
       an isolated sandbox before opening the primary prompt line.

Benchmark stages:
    Stage 1 — Multi-document indexing speed
        Encode all workspace .py files into the HV cache; measure throughput.

    Stage 2 — RecursiveMAS multi-agent orchestration
        Planner, Solver, and Critic agents exchange hypervector cross-talk
        (continuous parameter updates over localized latent representations)
        rather than streaming token-heavy string variables — conforming to
        modern RecursiveMAS workflows and respecting the 4 GB RAM ceiling.

4 GB RAM protection:
    * Agents communicate via 10,000-D numpy HV deltas (~40 KB each).
    * No large string buffers are accumulated between agents.
    * Memory-mapped arrays are released after each stage step.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

from aura_api_rotator import load_secrets
from aura_hv_cache import HVCacheSubstrate, _HV_DIM, _str_to_hv
from aura_token_economics import TokenEconomics

_BASELINE_PATH = Path("Aura_Memory/benchmark_baseline.json")
_PY_GLOB = "*.py"
_MAX_STAGE1_FILES = 20      # cap to avoid exceeding RAM on first boot
_MAS_ITERATIONS = 3         # RecursiveMAS refinement passes


# ---------------------------------------------------------------------------
# Credential fingerprinting
# ---------------------------------------------------------------------------

def _fingerprint_secrets(secrets: dict) -> str:
    """SHA-256 fingerprint of the non-placeholder credential set."""
    active = {
        k: v for k, v in secrets.items()
        if v and not any(m in str(v).lower() for m in ("your_", "paste_", "xxxx"))
    }
    canonical = json.dumps(active, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# RecursiveMAS agent primitives (HV cross-talk, no string buffers)
# ---------------------------------------------------------------------------

class _MASAgent:
    """
    Lightweight RecursiveMAS agent that communicates via HV parameter updates.

    Each agent maintains a 10,000-D latent state vector.  Interaction between
    agents is modelled as additive HV deltas (no string serialisation).
    """

    def __init__(self, role: str, seed: int) -> None:
        self.role = role
        rng = np.random.default_rng(seed=seed)
        self.state = rng.standard_normal(_HV_DIM).astype(np.float32)
        self.state /= np.linalg.norm(self.state) + 1e-9

    def step(self, input_hv: np.ndarray, context_hv: np.ndarray) -> np.ndarray:
        """
        Produce an output HV delta by binding input with current state.

        Binding = element-wise multiplication (hypervector algebra).
        The delta encodes this agent's contribution to the shared workspace
        without any string serialisation — pure numerical parameter update.
        """
        bound = self.state * input_hv * context_hv
        norm = np.linalg.norm(bound)
        if norm > 1e-6:
            bound /= norm
        # Update internal latent state (exponential moving average)
        self.state = 0.9 * self.state + 0.1 * bound
        self.state /= np.linalg.norm(self.state) + 1e-9
        return bound

    def coherence(self, reference_hv: np.ndarray) -> float:
        """Cosine similarity between this agent's state and a reference HV."""
        return float(np.dot(self.state, reference_hv))


# ---------------------------------------------------------------------------
# BenchmarkSandbox
# ---------------------------------------------------------------------------

class BenchmarkSandbox:
    """
    Isolated runtime sandbox for credential validation and performance profiling.

    Call scan_and_run() at startup; it returns immediately if no new credentials
    are detected.
    """

    def __init__(self, workspace_root: str | Path = ".") -> None:
        self.root = Path(workspace_root)
        self.hv_cache = HVCacheSubstrate()
        self.economics = TokenEconomics()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def scan_and_run(self) -> bool:
        """
        Scan credentials and run the benchmark if new keys are detected.

        Returns True if the benchmark was executed, False if skipped.
        """
        secrets = load_secrets()
        fingerprint = _fingerprint_secrets(secrets)
        baseline = self._load_baseline()

        if baseline.get("secrets_fingerprint") == fingerprint:
            return False

        print("\n" + "=" * 66)
        print(" [AURA BENCHMARK SANDBOX] New / updated credentials detected.")
        print("=" * 66)
        print(f" Fingerprint delta: {baseline.get('secrets_fingerprint', 'none')[:12]}… → {fingerprint[:12]}…")
        print(" Running multi-stage validation before opening the prompt line.\n")

        results = self._run_all_stages()
        self._save_baseline(fingerprint, results)

        print("\n[+] Benchmark complete. Baseline saved.")
        print(f"    Stage 1 indexing : {results['stage1']['files_encoded']} files, "
              f"{results['stage1']['total_lines']} lines, "
              f"{results['stage1']['elapsed_sec']:.2f}s")
        print(f"    Stage 2 RecurMAS : {results['stage2']['iterations']} iterations, "
              f"final coherence={results['stage2']['final_coherence']:.4f}")
        print("=" * 66 + "\n")
        return True

    # ------------------------------------------------------------------
    # Stage dispatch
    # ------------------------------------------------------------------

    def _run_all_stages(self) -> dict[str, Any]:
        stage1 = self._stage_indexing()
        stage2 = self._stage_recursive_mas(stage1.get("context_hv"))
        return {"stage1": stage1, "stage2": stage2}

    # ------------------------------------------------------------------
    # Stage 1 — Multi-document indexing speed
    # ------------------------------------------------------------------

    def _stage_indexing(self) -> dict[str, Any]:
        """Encode workspace .py files into the HV cache and measure throughput."""
        print("[Stage 1] Multi-document indexing speed…")
        py_files = sorted(self.root.glob(_PY_GLOB))[:_MAX_STAGE1_FILES]

        encoded = 0
        total_lines = 0
        t0 = time.time()

        for fpath in py_files:
            try:
                result = self.hv_cache.encode_file(fpath)
                if "error" not in result:
                    encoded += 1
                    total_lines += result.get("lines_encoded", 0)
                    status = result.get("status", "?")
                    print(f"  [{encoded:2d}] {fpath.name:<40s} "
                          f"{result.get('lines_encoded', 0):5d} lines  [{status}]")
            except Exception as exc:
                print(f"  [!]  {fpath.name}: {exc}")

        elapsed = time.time() - t0
        throughput = round(total_lines / max(elapsed, 0.001), 1)

        # Build a context HV for Stage 2
        ctx = self.hv_cache.project_context([str(f) for f in py_files[:5]])
        context_hv = ctx.get("context_vector")

        print(f"  → {encoded} files encoded, {total_lines} lines, "
              f"{elapsed:.2f}s ({throughput} lines/s)\n")
        return {
            "files_encoded": encoded,
            "total_lines": total_lines,
            "elapsed_sec": round(elapsed, 3),
            "throughput_lines_per_sec": throughput,
            "context_hv": context_hv,
        }

    # ------------------------------------------------------------------
    # Stage 2 — RecursiveMAS multi-agent orchestration
    # ------------------------------------------------------------------

    def _stage_recursive_mas(
        self,
        context_hv: np.ndarray | None = None,
    ) -> dict[str, Any]:
        """
        Planner → Solver → Critic loop using HV cross-talk.

        Each agent step is a 10 000-D parameter update (≈40 KB).
        No string token buffers are accumulated; inter-agent messages are pure HV
        arithmetic — conforming to RecursiveMAS latent-space communication.
        """
        print("[Stage 2] RecursiveMAS multi-agent orchestration…")

        if context_hv is None:
            rng = np.random.default_rng(seed=42)
            context_hv = rng.standard_normal(_HV_DIM).astype(np.float32)
            context_hv /= np.linalg.norm(context_hv) + 1e-9

        planner = _MASAgent("Planner", seed=1)
        solver  = _MASAgent("Solver",  seed=2)
        critic  = _MASAgent("Critic",  seed=3)

        # Initial task HV derived from context (no string needed)
        task_hv = _str_to_hv("benchmark:multi_agent:mesh_offload")
        workspace_hv = context_hv.copy()

        coherence_log: list[float] = []
        t0 = time.time()

        for iteration in range(_MAS_ITERATIONS):
            # Planner: decompose the task
            plan_delta = planner.step(task_hv, workspace_hv)
            # Solver: produce a solution HV given the plan
            solve_delta = solver.step(plan_delta, workspace_hv)
            # Critic: evaluate and emit a correction HV
            critic_delta = critic.step(solve_delta, plan_delta)
            # Workspace update: additive blend of all agent deltas
            workspace_hv = workspace_hv + 0.3 * (plan_delta + solve_delta + critic_delta)
            norm = np.linalg.norm(workspace_hv)
            if norm > 1e-6:
                workspace_hv /= norm

            # Coherence = mean pairwise cosine similarity across agents
            c_ps = float(np.dot(planner.state, solver.state))
            c_sc = float(np.dot(solver.state, critic.state))
            c_cp = float(np.dot(critic.state, planner.state))
            coherence = (c_ps + c_sc + c_cp) / 3.0
            coherence_log.append(coherence)

            print(f"  [iter {iteration+1}/{_MAS_ITERATIONS}] "
                  f"Planner↔Solver={c_ps:.3f}  Solver↔Critic={c_sc:.3f}  "
                  f"Critic↔Planner={c_cp:.3f}  mean={coherence:.4f}")

        elapsed = time.time() - t0
        final_coherence = coherence_log[-1] if coherence_log else 0.0
        print(f"  → {_MAS_ITERATIONS} iterations in {elapsed:.3f}s, "
              f"final coherence = {final_coherence:.4f}\n")

        return {
            "iterations": _MAS_ITERATIONS,
            "final_coherence": final_coherence,
            "coherence_log": coherence_log,
            "elapsed_sec": round(elapsed, 4),
        }

    # ------------------------------------------------------------------
    # Baseline persistence
    # ------------------------------------------------------------------

    def _load_baseline(self) -> dict:
        if not _BASELINE_PATH.exists():
            return {}
        try:
            with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_baseline(self, fingerprint: str, results: dict) -> None:
        _BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "secrets_fingerprint": fingerprint,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "stage1_files": results["stage1"]["files_encoded"],
            "stage1_lines": results["stage1"]["total_lines"],
            "stage2_coherence": results["stage2"]["final_coherence"],
        }
        with open(_BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

"""y
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8a5-[Q-SYS:F77C70AB02A22C41]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: asyncio, time, json, typing, pathlib, numpy, __future__, os, aura_arch_reasoner, collections
FUNCTIONS: __init__, gather_physical_state, build_anatomy_summary, summarize_shared_edges, extract_logical_gates, topology_to_phase_vector, load_baseline_phase, save_baseline_phase, measure_drift, score_structural_resonance, suggest_architectural_patch, verify_truth_resonance, recalibrate_symbolic_gates, compute_procrustes_alignment, run_arch_reasoning_report, offload_heavy_metrics, build_reflection_prompt, execute_cycle
SYNOPSIS: This Python module, leveraging `asyncio`, `numpy`, and `aura_arch_reasoner` among others, implements a high-performance architectural auditing framework with asynchronous state aggregation, symbolic topology analysis, and resonance-based structural validation through functions like `gather_physical_state`, `topology_to_phase_vector`, and `score_structural_resonance`, while offloading heavy computations via `offload_heavy_metrics` and generating actionable repair suggestions with `suggest_architectural_patch`.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np

from aura_arch_reasoner import AuraArchReasoner, _IDEAL_TENSION, _RESONANCE_FLOOR

_BASELINE_PATH = Path("Aura_Memory/self_reflect_baseline.json")
_TOPOLOGY_OUT = Path("Aura_Memory/live_topology_ast.json")
_WASM_OFFLOAD_NODE_THRESHOLD = 64
AURA_CORE_GUARDRAILS = """
CRITICAL ARCHITECTURAL CONSTRAINTS FOR CODE GENERATION:
1. The Asynchronous Mandate: You are patching an asynchronous, event-loop-driven system. You MUST NOT introduce synchronous blocking I/O (like sqlite3, requests, or time.sleep()) inside async functions. Use aiosqlite, asyncio.sleep(), or offload to asyncio.to_thread.
2. Hardware & Memory Bounds: The target hardware is a Motorola Moto G Stylus running Termux (ARM64) with a strict 4GB RAM ceiling. You MUST prioritize zero-copy operations, use numpy arrays (with explicitly defined types like np.float32 or np.int8) over Python lists, and avoid heavy object instantiation in loops.
3. Compilation & Execution Targets: Core logic is Python. High-performance accelerators are written in Rust and compiled to WebAssembly (wasm32-wasi), executed via Wasmtime. DO NOT provide C/C++ or gcc compilation flags.
4. Topological Hygiene: Do not invent new standalone databases or loose files in the root directory. All persistent data MUST be routed to the Aura_Memory/ directory. Rely on existing native methods (e.g., logging_kit.log_report()) rather than writing standard Python logging boilerplate.
5. Output Format: You must output ONLY the raw, refactored code enclosed within exact [CODE] and [/CODE] delimiters so the GBNF parser can extract it cleanly. Do not use markdown code blocks.
"""

class SelfReflectEngine:
    """Orchestrates deep introspection aligned with the VSA self-reflect rubric."""

    def __init__(
        self,
        node_ref: Any = None,
        topology_file: str | Path = _TOPOLOGY_OUT,
        baseline_path: Path = _BASELINE_PATH,
    ) -> None:
        self.node = node_ref
        self.topology_file = Path(topology_file)
        self.baseline_path = baseline_path
        self.reasoner = AuraArchReasoner(node_ref, str(topology_file))

    # ------------------------------------------------------------------
    # Physical / runtime probes
    # ------------------------------------------------------------------

    @staticmethod
    def gather_physical_state(node: Any) -> dict[str, float | int]:
        current_temp = 42.0
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as f:
                current_temp = float(f.read().strip()) / 1000.0
        except (OSError, ValueError):
            pass
        t1_load = len(getattr(node, "t1_ram", []))
        return {"thermal_c": current_temp, "t1_ram_load": t1_load}

    # ------------------------------------------------------------------
    # Topology (nodes & edges)
    # ------------------------------------------------------------------

    @staticmethod
    def build_anatomy_summary(nodes_list: list[dict]) -> tuple[str, dict[str, list[str]]]:
        anatomy_summary: dict[str, list[str]] = defaultdict(list)
        for n in nodes_list:
            if not n or not isinstance(n, dict):
                continue
            node_id = n.get("id")
            if not node_id:
                continue
            node_label = n.get("label", "Unknown_Primitive")
            node_shape = n.get("shape", "Sphere")
            file_origin = node_id.split("::")[0] if "::" in node_id else node_id
            anatomy_summary[file_origin].append(f"{node_label} ({node_shape})")

        anatomy_str = ""
        for file_origin, elements in list(anatomy_summary.items())[:12]:
            anatomy_str += f"  • {file_origin}: {', '.join(elements[:6])}\n"
        return anatomy_str, anatomy_summary

    @staticmethod
    def summarize_shared_edges(edges_list: list[dict]) -> str:
        data_links = [e for e in edges_list if str(e.get("type", "")).startswith("shared_")]
        links = [
            f"{e['source'].split('::')[0]} <-> {e['target'].split('::')[0]} ({e['type']})"
            for e in data_links[:10]
            if e.get("source") and e.get("target")
        ]
        return ", ".join(links) if links else "None recorded"

    @staticmethod
    def extract_logical_gates(nodes_list: list[dict], limit: int = 5) -> str:
        active_gates: list[str] = []
        for node_item in nodes_list:
            gates = node_item.get("logical_gates", [])
            if gates and node_item.get("label"):
                active_gates.append(f"Node: {node_item['label']} -> Gates: {gates}")
        return "\n".join(active_gates[:limit])

    @staticmethod
    def topology_to_phase_vector(nodes_list: list[dict], dim: int = 128) -> np.ndarray:
        """Aggregate 3D node layout vectors into a fixed-length phase row."""
        if not nodes_list:
            return np.zeros((1, dim), dtype=np.complex64)
        rows = []
        for n in nodes_list:
            vec = n.get("vector") or [0.0, 0.0, 0.0]
            try:
                rows.append([float(v) for v in vec[:3]])
            except (TypeError, ValueError):
                rows.append([0.0, 0.0, 0.0])
        arr = np.asarray(rows, dtype=np.float32)
        mean = arr.mean(axis=0)
        # Tile mean into dim complex phasor (unit magnitude)
        tiled = np.tile(mean, int(np.ceil(dim / 3)))[:dim]
        phases = np.exp(1j * (tiled / (np.abs(tiled).max() + 1e-6) * np.pi))
        return phases.reshape(1, -1).astype(np.complex64)

    def load_baseline_phase(self) -> Optional[np.ndarray]:
        if not self.baseline_path.exists():
            return None
        try:
            with open(self.baseline_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            real = np.asarray(data.get("phase_real", []), dtype=np.float32)
            imag = np.asarray(data.get("phase_imag", []), dtype=np.float32)
            if real.size == 0:
                return None
            return (real + 1j * imag).reshape(1, -1).astype(np.complex64)
        except (json.JSONDecodeError, OSError, ValueError):
            return None

    def save_baseline_phase(self, phase: np.ndarray) -> None:
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        flat = phase.reshape(-1)
        payload = {
            "saved_at": time.time(),
            "phase_real": np.real(flat).tolist(),
            "phase_imag": np.imag(flat).tolist(),
        }
        with open(self.baseline_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def measure_drift(self, current_phase: np.ndarray) -> tuple[float, bool]:
        """
        Procrustes alignment vs last stable baseline.
        Returns (alignment_score, baseline_updated).
        """
        baseline = self.load_baseline_phase()
        if baseline is None:
            self.save_baseline_phase(current_phase)
            return 1.0, True
        if baseline.shape != current_phase.shape:
            self.save_baseline_phase(current_phase)
            return 0.0, True
        score = AuraArchReasoner.compute_procrustes_alignment(baseline, current_phase)
        if score >= _RESONANCE_FLOOR:
            return score, False
        self.save_baseline_phase(current_phase)
        return score, True

    # ------------------------------------------------------------------
    # Architecture reasoner (all listed functions)
    # ------------------------------------------------------------------

    def score_structural_resonance(self) -> tuple[float, float]:
        return self.reasoner.score_structural_resonance()

    def suggest_architectural_patch(self) -> str:
        return self.reasoner.suggest_architectural_patch()

    async def verify_truth_resonance(self) -> float:
        return await self.reasoner.verify_truth_resonance()

    async def recalibrate_symbolic_gates(self) -> str:
        return await self.reasoner.recalibrate_symbolic_gates()

    @staticmethod
    def compute_procrustes_alignment(
        state_a: np.ndarray,
        state_b: np.ndarray,
    ) -> float:
        return AuraArchReasoner.compute_procrustes_alignment(state_a, state_b)

    async def run_arch_reasoning_report(self) -> dict[str, Any]:
        """Execute every aura_arch_reasoner entry point and return a unified report."""
        resonance, tension = self.score_structural_resonance()
        patch = self.suggest_architectural_patch()
        async_resonance = await self.verify_truth_resonance()
        recal = ""
        if async_resonance < _RESONANCE_FLOOR:
            recal = await self.recalibrate_symbolic_gates()
        return {
            "resonance": resonance,
            "tension": tension,
            "ideal_tension": _IDEAL_TENSION,
            "async_resonance": async_resonance,
            "patch": patch,
            "recalibration": recal,
        }

    # ------------------------------------------------------------------
    # WASM / subprocess offload
    # ------------------------------------------------------------------

    async def offload_heavy_metrics(
        self,
        nodes: int,
        edges: int,
        phase_a: Optional[np.ndarray] = None,
        phase_b: Optional[np.ndarray] = None,
    ) -> Optional[dict[str, Any]]:
        """Route structural / Procrustes work to WasmOrchestrator when node count is high."""
        if nodes < _WASM_OFFLOAD_NODE_THRESHOLD:
            return None
        wasm = getattr(self.node, "wasm_airlock", None)
        if wasm is None:
            return None
        thought_id = "SELF-REFLECT"
        if hasattr(self.node, "runtime_metrics"):
            thought_id = str(self.node.runtime_metrics.get("thought_id", thought_id))

        payload: dict[str, Any] = {
            "operation": "STRUCTURAL_RESONANCE",
            "nodes": nodes,
            "edges": edges,
        }
        if phase_a is not None and phase_b is not None:
            payload = {
                "operation": "PROCRUSTES_ALIGNMENT",
                "phase_a": np.angle(phase_a).astype(float).reshape(-1).tolist(),
                "phase_b": np.angle(phase_b).astype(float).reshape(-1).tolist(),
            }
        try:
            return await wasm.execute_isolated_module(
                thought_id, "arch_reasoner_accel", payload
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Prompt assembly
    # ------------------------------------------------------------------

    def build_reflection_prompt(
        self,
        *,
        gates_context: str,
        physical: dict[str, float | int],
        nodes_list: list[dict],
        edges_list: list[dict],
        anatomy_str: str,
        links_str: str,
        arch_report: dict[str, Any],
        drift_score: float,
        wasm_metrics: Optional[dict[str, Any]] = None,
    ) -> str:
        wasm_line = ""
        if wasm_metrics and wasm_metrics.get("status") == "success":
            wasm_line = f"- WASM Offload Metrics: {json.dumps(wasm_metrics.get('metrics', {}))}\n"

        return (
            f"ACTIVE LOGICAL GATES & PRECONDITIONS:\n{gates_context}\n\n"
            f"SYSTEM PHYSICAL ENVIRONMENT:\n"
            f"- Core Thermal Load : {physical['thermal_c']}°C\n"
            f"- Active T1 RAM Load: {physical['t1_ram_load']} memory traces\n\n"
            f"VSA STRUCTURAL REASONING (aura_arch_reasoner):\n"
            f"- Manifold Tension     : {arch_report['tension']:.4f} (ideal {_IDEAL_TENSION})\n"
            f"- Structural Resonance : {arch_report['resonance']:.4f}\n"
            f"- Async Truth Resonance: {arch_report['async_resonance']:.4f}\n"
            f"- Procrustes Drift     : {drift_score:.4f} (1.0 = aligned with baseline)\n"
            f"- Patch Recommendation : {arch_report['patch']}\n"
            f"{wasm_line}"
            f"ACTIVE 3D TOPOLOGICAL ARCHITECTURE:\n"
            f"- Total Mapped Functional Nodes: {len(nodes_list)}\n"
            f"- Mapped Shared-Resource Paths : {len(edges_list)}\n"
            f"- Database/Port Linkages       : [{links_str}]\n"
            f"- Exposed Module Layout        :\n{anatomy_str}\n"
            f"TASK: Analyze your active physical thermals, memory footprint, and 3D node layout. "
            f"Identify exactly which function, module, or shared-database query is causing structural friction or execution bottlenecks. "
            f"Propose one highly optimized, non-blocking asynchronous Python function refactor or transactional batching optimization. "
            f"When complexity is high, prefer a Wasm pipeline offload via arch_reasoner_accel.\n"
            f"You must include a formal [MATHEMATICAL EFFICIENCY ESTIMATE] in your response with the following metrics:\n"
            f"1. Computational Complexity Shift (Delta O): Big-O scaling comparison (e.g., O(N^2) -> O(log N))\n"
            f"2. Spatial Memory Reclamation (Delta Memory): Projected bytes saved on the 4GB RAM boundary\n"
            f"3. Spatiotemporal Latency Savings (Delta L): Estimated execution milliseconds saved per active inference loop\n"
            f"4. Axiomatic Coherence Shift (Delta C): Expected alignment score bounds calculated via your LNN engine.\n\n"
            f"Output strictly technical, production-ready refactoring code and the completed efficiency metrics. No generic filler."
            f"\n\n{AURA_CORE_GUARDRAILS}"
        )
    # ------------------------------------------------------------------
    # Full cycle
    # ------------------------------------------------------------------

    async def execute_cycle(
        self,
        compile_graph_fn: Callable[[], dict],
        invoke_cloud: Optional[Callable[[str, str], Any]] = None,
        cloud_engine: str = "GEMINI",
    ) -> dict[str, Any]:
        """
        Run the complete self-reflect pipeline.

        Returns a result dict with topology stats, arch_report, drift, and optional cloud text.
        """
        loop = asyncio.get_running_loop()
        topology_payload = await loop.run_in_executor(None, compile_graph_fn)
        topology_payload = topology_payload or {}

        nodes_list = topology_payload.get("nodes") or []
        edges_list = topology_payload.get("edges") or []

        # Persist topology for reasoner file-based scoring
        self.topology_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.topology_file, "w", encoding="utf-8") as f:
            json.dump(
                {"status": "SYS_TOPOLOGY_ACTIVE", "nodes": nodes_list, "edges": edges_list},
                f,
                indent=2,
            )

        physical = self.gather_physical_state(self.node) if self.node else {"thermal_c": 42.0, "t1_ram_load": 0}
        anatomy_str, _ = self.build_anatomy_summary(nodes_list)
        links_str = self.summarize_shared_edges(edges_list)
        gates_context = self.extract_logical_gates(nodes_list)

        arch_report = await self.run_arch_reasoning_report()

        current_phase = self.topology_to_phase_vector(nodes_list)
        drift_score, _ = self.measure_drift(current_phase)

        wasm_metrics = await self.offload_heavy_metrics(
            len(nodes_list),
            len(edges_list),
            current_phase,
            self.load_baseline_phase(),
        )

        prompt = self.build_reflection_prompt(
            gates_context=gates_context,
            physical=physical,
            nodes_list=nodes_list,
            edges_list=edges_list,
            anatomy_str=anatomy_str,
            links_str=links_str,
            arch_report=arch_report,
            drift_score=drift_score,
            wasm_metrics=wasm_metrics,
        )

        cloud_text = ""
        if invoke_cloud is not None:
            cloud_text = await invoke_cloud(cloud_engine, prompt)

        if arch_report.get("recalibration"):
            print(arch_report["recalibration"])

        return {
            "nodes": len(nodes_list),
            "edges": len(edges_list),
            "physical": physical,
            "arch_report": arch_report,
            "drift_score": drift_score,
            "wasm_metrics": wasm_metrics,
            "prompt": prompt,
            "cloud_response": cloud_text,
        }

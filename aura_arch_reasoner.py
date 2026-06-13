"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa895-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: asyncio, os, numpy, __future__, json
FUNCTIONS: __init__, score_structural_resonance, suggest_architectural_patch, verify_truth_resonance, recalibrate_symbolic_gates, compute_procrustes_alignment
SYNOPSIS: The `AuraOS Auditor` Python module, leveraging `asyncio`, `os`, `numpy`, `__future__`, and `json`, implements a strict, resonance-based integrity framework via `__init__`, `score_structural_resonance`, `suggest_architectural_patch`, `verify_truth_resonance`, `recalibrate_symbolic_gates`, and `compute_procrustes_alignment` to dynamically audit and enforce symbolic coherence across system architectures.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import asyncio
import json
import os

import numpy as np

from aura_coordinated_solver import CoordinatedSolver, phasor_to_method

# Ideal edge-to-node ratio derived from VSA cognitive processing research.
# Cognitive efficiency peaks when the manifold tension sits at ~1.5
# (Bent et al., SPIE 2024; Furlong et al., AAAI).
_IDEAL_TENSION: float = 1.5
_RESONANCE_FLOOR: float = 0.85        # Below this → recalibration required
_TOPOLOGY_PATH: str = "Aura_Memory/live_topology_ast.json"


class AuraArchReasoner:
    """
    Architecture reasoner implementing the VSA cognitive processing rubric.

    Treats ``live_topology_ast.json`` as a logic manifold.  Scores the
    current architecture against the ideal manifold tension and proposes
    surgical patches when resonance drops below the stability floor.
    """

    def __init__(self, node_ref=None, topology_file: str = _TOPOLOGY_PATH) -> None:
        self.node = node_ref
        self.topology_file = topology_file
        self._last_resonance: float = 1.0
        self._last_tension: float = _IDEAL_TENSION

    # ------------------------------------------------------------------
    # Core scoring
    # ------------------------------------------------------------------

    def score_structural_resonance(self) -> tuple[float, float]:
        """
        Load the live topology and compute manifold tension + resonance.

        Returns
        -------
        (resonance, tension)
            resonance ∈ (0, 1] — higher is better.
            tension   = edges / nodes — ideal is ~1.5.
        """
        try:
            with open(self.topology_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return 1.0, _IDEAL_TENSION

        nodes = max(len(data.get("nodes", [])), 1)
        edges = len(data.get("edges", []))
        tension = edges / nodes
        # Resonance: 1 / (1 + |ideal − current|)  — from VSA rubric
        resonance = 1.0 / (1.0 + abs(_IDEAL_TENSION - tension))
        self._last_resonance = resonance
        self._last_tension = tension
        return resonance, tension

    def suggest_architectural_patch(self) -> str:
        """Return a human-readable refactoring recommendation."""
        resonance, tension = self.score_structural_resonance()
        if resonance < _RESONANCE_FLOOR:
            if tension > _IDEAL_TENSION:
                return (
                    f"REFACTOR_REQUIRED: Manifold is over-dense "
                    f"(tension={tension:.2f} > ideal {_IDEAL_TENSION}). "
                    "Prune redundant cross-module dependencies."
                )
            return (
                f"REFACTOR_REQUIRED: Manifold is under-connected "
                f"(tension={tension:.2f} < ideal {_IDEAL_TENSION}). "
                "Introduce bridging interfaces for isolated modules."
            )
        return f"STABLE: Resonance {resonance:.4f} — manifold tension optimal ({tension:.2f})."

    # ------------------------------------------------------------------
    # Async truth resonance (used by !meta_reason)
    # ------------------------------------------------------------------

    async def verify_truth_resonance(self) -> float:
        """
        Asynchronous wrapper for structural resonance scoring.
        Logs the result to the node's runtime metrics if available.
        """
        resonance, tension = await asyncio.to_thread(self.score_structural_resonance)
        if self.node is not None and hasattr(self.node, "runtime_metrics"):
            self.node.runtime_metrics["arch_resonance"] = resonance
            self.node.runtime_metrics["manifold_tension"] = tension
        return resonance

    async def recalibrate_symbolic_gates(self) -> str:
        """
        Runs a symbolic recalibration sweep when resonance < _RESONANCE_FLOOR.

        Strategy (SATURN-inspired):
        1. Re-read topology from disk.
        2. Identify the top-3 most over-connected nodes (highest degree).
        3. Suggest removing the lowest-strength edges from each.
        """
        try:
            with open(self.topology_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return "Recalibration skipped — topology file unavailable."

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Count out-degree per node (skip module anchors — high degree is expected)
        degree: dict[str, int] = {}
        for edge in edges:
            src = edge.get("source", "")
            if src.endswith("::global_scope"):
                continue
            degree[src] = degree.get(src, 0) + 1

        hotspots = sorted(degree.items(), key=lambda kv: -kv[1])[:3]
        report_lines = ["[RECALIBRATION] Top over-connected nodes:"]
        for node_id, deg in hotspots:
            short_id = node_id.split("/")[-1] if "/" in node_id else node_id
            report_lines.append(f"  {short_id} → degree {deg}")

        report_lines.append(self.suggest_architectural_patch())
        return "\n".join(report_lines)

    async def coordinated_multi_strategy_patches(
        self,
        K: int = 4,
        method_dim: int = 64,
    ) -> dict:
        """
        [Coordinated Pass@K Architecture] Generate K alternative refactoring
        strategies in parallel and select the best via coordinated solver.
        
        Returns top-K architectural patches ranked by resonance improvement.
        """
        print(f"[⚡ COORDINATED ARCH] Generating {K} alternative refactoring strategies...")
        
        # Step 1: Load topology and compute current state
        try:
            with open(self.topology_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "success": False,
                "error": "Topology file unavailable",
                "patches": [],
            }
        
        resonance, tension = self.score_structural_resonance()
        
        # Step 2: Generate K strategy vectors representing different refactoring approaches
        # Each strategy encodes a different architectural transformation
        planner_output = []
        rng = np.random.default_rng(seed=0xA1A)
        
        for k in range(K):
            # Create diverse strategy vectors based on architectural metrics
            strategy_vec = rng.normal(
                loc=tension,  # Center around current tension
                scale=0.5,     # Variance in refactoring approaches
                size=method_dim,
            ).astype(np.float64)
            # Normalize to unit sphere for stability
            strategy_vec = strategy_vec / (np.linalg.norm(strategy_vec) + 1e-9)
            planner_output.append(strategy_vec)
        
        # Step 3: Evaluate strategies via coordinated solver
        solver = CoordinatedSolver(K=K, method_dim=method_dim, node_ref=self.node)
        result = await solver.coordinated_pass_k(planner_output)
        
        # Step 4: Translate top strategies into human-readable patches
        patches = []
        for idx, (method, reward) in enumerate(zip(result["top_methods"], result["top_rewards"])):
            # Decode strategy vector into refactoring recommendation
            avg_value = float(np.mean(method))
            
            if avg_value > tension:
                patch_type = "densification"
                description = "Add bridging interfaces between isolated modules"
            else:
                patch_type = "pruning"
                description = "Remove redundant cross-module dependencies"
            
            patches.append({
                "rank": idx + 1,
                "type": patch_type,
                "description": description,
                "reward": reward,
                "projected_tension": float(avg_value),
                "projected_resonance": 1.0 / (1.0 + abs(_IDEAL_TENSION - avg_value)),
            })
        
        result["patches"] = patches
        result["current_resonance"] = resonance
        result["current_tension"] = tension
        
        print(f"[+] Generated {len(patches)} ranked architectural patches (best reward: {result['top_rewards'][0] if result['top_rewards'] else 0:.3f})")
        return result

    # ------------------------------------------------------------------
    # Resonance as a phasor distance metric (VSA binding)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_procrustes_alignment(
        state_a: np.ndarray,
        state_b: np.ndarray,
    ) -> float:
        """
        Orthogonal Procrustes alignment score between two phasor state matrices.
        Returns a similarity in [0, 1] — 1.0 means perfect alignment.

        Used by !self_reflect to measure how far the current code state
        has drifted from the last verified-stable state.
        """
        if state_a.shape != state_b.shape or state_a.size == 0:
            return 0.0
        # Project both to flat tangent space (log-map)
        phase_a = np.angle(state_a).astype(np.float32)
        phase_b = np.angle(state_b).astype(np.float32)
        M = phase_a.T @ phase_b
        try:
            U, _, Vt = np.linalg.svd(M, full_matrices=False)
        except np.linalg.LinAlgError:
            return 0.0
        R = U @ Vt
        aligned = phase_a @ R
        residual = float(np.linalg.norm(aligned - phase_b, "fro"))
        norm_b = float(np.linalg.norm(phase_b, "fro"))
        if norm_b == 0:
            return 1.0
        return float(np.clip(1.0 - residual / norm_b, 0.0, 1.0))

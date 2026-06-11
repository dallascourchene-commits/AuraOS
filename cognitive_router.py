"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MIIGWECH (Extension-Based Storage)
DEPENDENCIES: sqlite3, shutil, pathlib, contextlib, os, numpy
FUNCTIONS: __new__, __init__, wave_scan, quantum_multiclass_intent_classifier, mitigate_barren_plateaus, astar_bis_score, astar_prune_gate, simulate_with_astar_pruning, calculate_hamming, _cos
SYNOPSIS: This Python module integrates **sqlite3** for persistent quantum state caching, **shutil**/**pathlib**/**os** for filesystem operations, **contextlib** for resource management, **numpy** for numerical optimization, and implements a **wave_scan**-based quantum state initializer, a **quantum_multiclass_intent_classifier** with **mitigate_barren_plateaus** gradient stabilization, **astar_bis_score**/**astar_prune_gate** for gate pruning via A* search, **simulate_with_astar_pruning** for hybrid quantum-classical simulation, **calculate_hamming** for state fidelity metrics, and **_cos** for quantum kernel computations, all instantiated via **__new__**/**__init__** with strict type enforcement.
[/AURA_MASTER_KEY]
"""
import numpy as np
import sqlite3
import contextlib
import shutil
import os
from pathlib import Path

class CognitiveRouter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CognitiveRouter, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.db_path = Path.home() / ".mempalace" / "aura_memory.db"
            self._initialized = True

    def wave_scan(self, prompt_hv: np.ndarray, limit: int = 3) -> str:
        """Vectorized Hamming distance scan directly against the SQLite BLOB matrix."""
        prompt_blob = prompt_hv.astype(np.uint8).tobytes()

        def calculate_hamming(blob1, blob2):
            if blob2 is None: 
                return 9999
            
            # Reconstruct byte views dynamically without copying underlying allocations
            vec1 = np.frombuffer(blob1, dtype=np.uint8)
            vec2 = np.frombuffer(blob2, dtype=np.uint8)
            
            # If lengths mismatch due to heterogeneous database storage profiles, 
            # slice arrays symmetrically to ensure safe vector operations
            if len(vec1) != len(vec2):
                target_boundary = min(len(vec1), len(vec2))
                vec1 = vec1[:target_boundary]
                vec2 = vec2[:target_boundary]
            
            # Pure numpy XOR reduce for speed
            return int(np.sum(np.bitwise_xor(vec1, vec2)))

        resonant_memories = []
        for _attempt in range(2):
            try:
                with contextlib.closing(sqlite3.connect(str(self.db_path))) as conn:
                    conn.create_function("HAMMING", 2, calculate_hamming)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT content, timestamp FROM traces
                        WHERE vector_blob IS NOT NULL
                        ORDER BY HAMMING(?, vector_blob) ASC LIMIT ?
                    """, (prompt_blob, limit))
                    for row in cursor.fetchall():
                        resonant_memories.append(f"[{row[1]}] {row[0]}")
                break  # success
            except sqlite3.DatabaseError as dbe:
                if _attempt == 0 and ("malformed" in str(dbe).lower() or "corrupt" in str(dbe).lower()):
                    # Corrupt DB — silently move so it gets rebuilt by the background worker
                    try:
                        bak = str(self.db_path) + ".corrupt.bak"
                        shutil.move(str(self.db_path), bak)
                    except Exception:
                        try:
                            Path(self.db_path).unlink(missing_ok=True)
                        except Exception:
                            pass
                    continue  # retry with fresh file
                break  # other DB error, skip gracefully
            except Exception:
                break  # non-DB error, skip

        return "\n".join(resonant_memories) if resonant_memories else "No prior resonant context found."

    def quantum_multiclass_intent_classifier(self, prompt_vec: np.ndarray, class_matrix: dict) -> str:
        """Vectorized cosine similarity for intent routing without iterative loops."""
        p_norm = np.linalg.norm(prompt_vec)
        if p_norm == 0:
            return "[Aura OS] > State collapse: Zero-vector prompt."
        
        p_unit = prompt_vec / p_norm
        
        # Extract dictionary into parallel numpy arrays
        class_names = list(class_matrix.keys())
        class_vectors = np.array(list(class_matrix.values()), dtype=float)
        
        # Single-pass matrix multiplication (The Cloud Brain's optimization)
        class_norms = np.linalg.norm(class_vectors, axis=1)
        valid_mask = class_norms > 0
        
        if not np.any(valid_mask):
            return "[Aura OS] > No quantum overlap detected across intent states."
            
        class_units = np.zeros_like(class_vectors)
        class_units[valid_mask] = class_vectors[valid_mask] / class_norms[valid_mask][:, np.newaxis]
        
        # F = |<psi|phi>|^2 computed for all classes simultaneously
        overlaps = np.dot(class_units, p_unit)
        expectations = overlaps ** 2
        total_expectation = np.sum(expectations)

        if total_expectation == 0:
            return "[Aura OS] > No quantum overlap detected."

        superposition_dist = expectations / total_expectation
        dominant_idx = np.argmax(superposition_dist)
        dominant_class = class_names[dominant_idx]
        dominant_score = superposition_dist[dominant_idx] * 100

        return f"[Aura OS] > Superposition Collapsed. Dominant Intent: [{dominant_class}] at {dominant_score:.1f}% expectation."

    def mitigate_barren_plateaus(self, raw_distances: list) -> list:
        """Sharpens gradient landscapes to prevent AI plateauing using pure NumPy."""
        if not raw_distances:
            return []
            
        dist_array = np.array(raw_distances, dtype=float)
        EXPECTED_ORTHOGONALITY = 5000.0
        
        # Vectorized noise floor clipping
        dist_array = np.where(dist_array < 50.0, 0.0, dist_array)
        
        # Vectorized drift amplification
        normalized_drift = (dist_array - EXPECTED_ORTHOGONALITY) / EXPECTED_ORTHOGONALITY
        amplified_drift = np.sign(normalized_drift) * (np.abs(normalized_drift) ** 3.0)
        
        sharpened_distances = EXPECTED_ORTHOGONALITY + (amplified_drift * EXPECTED_ORTHOGONALITY)
        sharpened_distances = np.clip(sharpened_distances, 0.0, 10000.0)
        
        return [float(np.round(d, 2)) for d in sharpened_distances]

    # ------------------------------------------------------------------
    # A*-Thought Bidirectional Importance Score (arXiv:2505.24550)
    # ------------------------------------------------------------------

    def astar_bis_score(
        self,
        step_vec: np.ndarray,
        question_vec: np.ndarray,
        answer_vec: np.ndarray,
        alpha: float = 0.5,
    ) -> float:
        """
        Bidirectional Importance Score for a reasoning step.

        BIS = α · cos(step, question) + (1−α) · cos(step, answer)

        A step is important if it is simultaneously relevant to the
        original question (forward) and the known/target answer (backward).
        Used to prune unaligned code-generation trajectories before routing
        to Port 8081, keeping inference within the 4 GB RAM boundary.

        Parameters
        ----------
        step_vec      : phasor embedding of the reasoning step.
        question_vec  : phasor embedding of the original question.
        answer_vec    : phasor embedding of the target/current answer state.
        alpha         : forward/backward balance (default 0.5).

        Returns
        -------
        BIS ∈ [−1, 1] — higher is more important.
        """
        def _cos(a: np.ndarray, b: np.ndarray) -> float:
            na, nb = np.linalg.norm(a), np.linalg.norm(b)
            if na < 1e-9 or nb < 1e-9:
                return 0.0
            return float(np.dot(np.real(a), np.real(b)) / (na * nb))

        fwd = _cos(step_vec, question_vec)
        bwd = _cos(step_vec, answer_vec)
        return alpha * fwd + (1.0 - alpha) * bwd

    def astar_prune_gate(
        self,
        step_vec: np.ndarray,
        target_vec: np.ndarray,
        threshold: float = 0.45,
    ) -> bool:
        """
        A*-Thought prune gate (arXiv:2505.24550 eq. for prune criterion).

        Returns True (keep) when phasor cosine similarity ≥ threshold.
        Returns False (prune) when the trajectory is diverging from the
        target state.

        Threshold 0.45 is taken directly from the spec §4.2 prune gate.
        """
        psi_n = np.real(step_vec).astype(np.float32)
        psi_t = np.real(target_vec).astype(np.float32)
        n_n = np.linalg.norm(psi_n)
        n_t = np.linalg.norm(psi_t)
        if n_n < 1e-9 or n_t < 1e-9:
            return True  # cannot judge — keep by default
        similarity = float(np.dot(psi_n, psi_t) / (n_n * n_t))
        return similarity >= threshold

    def simulate_with_astar_pruning(
        self,
        thought_steps: list[np.ndarray],
        question_vec: np.ndarray,
        target_vec: np.ndarray,
        alpha: float = 0.5,
        prune_threshold: float = 0.45,
    ) -> list[np.ndarray]:
        """
        Filter a list of reasoning step vectors, retaining only those
        that pass the A*-Thought prune gate AND have above-median BIS.

        Used by the !simulate pipeline to prune redundant code-generation
        trajectories before routing to Port 8081.
        """
        if not thought_steps:
            return []

        bis_scores = [
            self.astar_bis_score(s, question_vec, target_vec, alpha)
            for s in thought_steps
        ]
        median_bis = float(np.median(bis_scores))

        kept = []
        for step, bis in zip(thought_steps, bis_scores):
            passes_gate = self.astar_prune_gate(step, target_vec, prune_threshold)
            above_median = bis >= median_bis
            if passes_gate and above_median:
                kept.append(step)

        return kept if kept else thought_steps[:1]   # always keep at least one step

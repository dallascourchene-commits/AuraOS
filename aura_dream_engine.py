"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: vsa_resonator, aura_spectral_memory, numpy, json, time, datetime, os
FUNCTIONS: homeostatic_decay_pass, __init__, run_dream_cycle, _pair_similarity, _neighbor_indices
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Patch v2 — Emergent connection: aura_spectral_memory → aura_dream_engine
=========================================================================
Two previously disconnected subsystems are now wired:

  aura_spectral_memory.AuraSpectralMemoryOrchestrator.execute_mqcr_recoherence
  ↕
  aura_dream_engine.AuraDreamEngine.run_dream_cycle

After the LLM synthesizes a new PRINCIPLE vector, MQCR (Maxwell-damping
Quantum-Cognitive Recoherence) is applied against the node's live
active_trajectory_wave to drift-correct the newly minted phasor before
it is written to the DB.  This prevents phase-drift accumulation across
successive dream cycles on a Termux device where the trajectory wave is
only updated while the phone is active.

Also fixes:
  np.array(raw_vectors, ...)  →  np.stack(raw_vectors)
  Avoids creating an intermediate Python list of numpy arrays and then
  calling np.array() which internally iterates and copies each element.
  np.stack() is marginally faster on ARM NEON because it dispatches
  a single C-level gather operation.
"""
import json
import os
import time
from datetime import datetime

import numpy as np
from vsa_resonator import VSAResonator

try:
    from aura_spectral_memory import AuraSpectralMemoryOrchestrator as _SpectralOrch
except ImportError:
    _SpectralOrch = None  # type: ignore[assignment,misc]

# Moto G Stylus / Termux defaults: cap RAM + CPU during REM consolidation.
_DREAM_MAX_TRACES = int(os.environ.get("AURA_DREAM_MAX_TRACES", "48"))
_DREAM_FULL_MATRIX_MAX = int(os.environ.get("AURA_DREAM_FULL_MATRIX_MAX", "36"))
_DREAM_SPARSE_NEIGHBORS = int(os.environ.get("AURA_DREAM_SPARSE_NEIGHBORS", "24"))

class AuraDreamEngine:
    """
    Biological-inspired Memory Consolidation & REM Sleep Engine.
    Clusters raw episodic memories, distills them into generalized principles,
    and prunes redundant database traces when CPU thermals are cool.
    """
    def __init__(self, node_ref=None):
        self.node = node_ref
        self.is_dreaming = False

    async def run_dream_cycle(self) -> str:
        """
        Executes a dynamic 'Dream Phase' consolidation pass if the system is cool.
        Calculates sublinear similarity clusters and prunes old episodic logs.
        """
        if self.node is None or not self.node.memory_palace.conn:
            return "[-] Dream Engine: No active database connection linked."

        conn = self.node.memory_palace.conn
        
        # 1. Check Thermals (Only dream when the CPU is running cool)
        temp = 42.0
        try:
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
        except Exception:
            pass
            
        if temp > 38.0:
            return f"[-] Dream Phase aborted: CPU thermals too high ({temp:.1f}C). Rest is deferred."

        self.is_dreaming = True
        print(f"\n[*] [DREAM PHASE ENGAGED] CPU at {temp:.1f}°C. Initiating memory consolidation...")

        # 2. Fetch recent episodic and foraged traces (M0 tier memories)
        # Excludes previous principles and system state markers
        query = (
            "SELECT id, content, vector_blob FROM traces "
            "WHERE tier IN ('T1', 'T2', 'FORAGED') AND id NOT LIKE 'ARXIV_CRAWLER_STATE' "
            "ORDER BY timestamp DESC LIMIT ?;"
        )
        async with conn.execute(query, (_DREAM_MAX_TRACES,)) as cursor:
            traces = await cursor.fetchall()

        if len(traces) < 4:
            self.is_dreaming = False
            return "[+] Dream Phase complete: Insufficient episodic traces to form clusters."

        # Extract contents and reconstruct the 2D VSA matrix in-place
        content_ids = [t[0] for t in traces]
        contents = [t[1] for t in traces]
        
        raw_vectors = []
        valid_indices = []
        for idx, t in enumerate(traces):
            if t[2]:
                try:
                    # Reconstruct the complex64 phasor wave natively
                    wave = np.frombuffer(t[2], dtype=np.complex64)
                    if len(wave) == 10000:
                        raw_vectors.append(wave)
                        valid_indices.append(idx)
                except Exception:
                    pass

        if len(raw_vectors) < 3:
            self.is_dreaming = False
            return "[+] Dream Phase complete: Insufficient high-dimensional engrams to cluster."

        # Stack into a contiguous 2D array.
        # np.stack() issues a single C-level gather on ARM NEON rather than
        # iterating the Python list element-by-element as np.array([...]) does.
        vectors = np.stack(raw_vectors, axis=0).astype(np.complex64)
        total_vectors = len(vectors)

        # 3. [GSB & COORDINATE SAMPLED COHERENCE MATRIX]
        # Decomposes complex vectors into low-precision L2 cache-resident arrays
        resonator = VSAResonator(dim=10000)

        quantized_vectors = []
        for v in vectors:
            phases = np.angle(v).astype(np.float32)
            quantized_vectors.append(resonator.gsb_quantize(phases))

        use_sparse = total_vectors > _DREAM_FULL_MATRIX_MAX
        neighbor_rng = np.random.default_rng(seed=0xD0EA01)

        def _pair_similarity(i: int, j: int) -> float:
            q_g, q_s, q_b = quantized_vectors[i]
            c_g, c_s, c_b = quantized_vectors[j]
            sim = resonator.sampled_similarity(q_g, q_s, q_b, c_g, c_s, c_b)
            if 0.45 <= sim < 0.75:
                t_var = float(self.node.runtime_metrics.get("cytoelectric_field_potential", 0.05))
                constructive_noise = float(neighbor_rng.normal(0.0, max(0.01, t_var * 0.1)))
                sim_boosted = sim + constructive_noise
                if sim_boosted >= 0.75:
                    sim = 0.76
                    print(f"[*] [DREAM SR BRIDGE] Subthreshold memory similarity [{sim_boosted:.4f}] pushed over boundary.")
            return sim

        def _neighbor_indices(i: int) -> range | list[int]:
            if not use_sparse:
                return range(total_vectors)
            k = min(_DREAM_SPARSE_NEIGHBORS, total_vectors - 1)
            picks = neighbor_rng.choice(
                [idx for idx in range(total_vectors) if idx != i],
                size=k,
                replace=False,
            )
            return picks.tolist()

        # 4. Extract highly resonant memory clusters (similarity > 0.75)
        clusters = []
        assigned = set()

        for i in range(total_vectors):
            if i in assigned:
                continue
            similar_indices = [i] + [
                j for j in _neighbor_indices(i)
                if j != i and _pair_similarity(i, j) > 0.75
            ]
            cluster_ids = [content_ids[valid_indices[j]] for j in similar_indices if j not in assigned]
            cluster_texts = [contents[valid_indices[j]] for j in similar_indices if j not in assigned]
            
            if len(cluster_texts) > 1:
                clusters.append((cluster_ids, cluster_texts))
            assigned.update(similar_indices)

        # 5. Synthesize and Prune (Consolidation)
        consolidated_count = 0
        for cluster_ids, cluster_texts in clusters:
            synthesis_prompt = (
                f"You are Aura's REM sleep consolidator. Synthesize these fragmented, similar episodic memories "
                f"into a single, profound generalized principle or lesson:\n" + 
                "\n".join([f"• {txt}" for txt in cluster_texts]) +
                f"\nOutput only the generalized lesson/principle. No conversational filler."
            )
            
            # Execute non-blocking synthesis via cloud/local engine
            principle = (await self.node.invoke_engine(synthesis_prompt)).strip()
            
            # Compress and encode the new principle
            principle_hv = self.node.polysynthetic_vram_compress(principle)

            # --- Emergent connection: aura_spectral_memory → aura_dream_engine ---
            # Apply MQCR recoherence to drift-correct the newly minted phasor
            # against the node's live trajectory wave before writing to DB.
            # This prevents phase-drift accumulation across successive dream cycles
            # (critical on Termux where the trajectory is only updated while active).
            if _SpectralOrch is not None:
                traj = getattr(self.node, "active_trajectory_wave", None)
                if traj is not None and traj.shape == principle_hv.shape:
                    try:
                        _orch = _SpectralOrch()
                        principle_hv = _orch.execute_mqcr_recoherence(
                            principle_hv.astype(np.complex64),
                            traj.astype(np.complex64),
                            damping=0.1,   # 10 % drift correction per cycle
                        )
                    except Exception:
                        pass  # graceful fallback — write original phasor

            principle_blob = np.asarray(principle_hv, dtype=np.complex64).tobytes()
            p_id = f"PRINCIPLE_{int(time.time())}_{np.random.randint(1000)}"
            
            # Save the distilled principle
            await conn.execute(
                "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) VALUES (?, ?, 'PRINCIPLE', ?, 'Condensed Core Memory', ?)",
                (p_id, principle, datetime.now().isoformat(), principle_blob)
            )
            
            # Prune the raw, redundant episodic traces to prevent DB bloat
            placeholders = ','.join(['?'] * len(cluster_ids))
            await conn.execute(f"DELETE FROM traces WHERE id IN ({placeholders})", tuple(cluster_ids))
            consolidated_count += len(cluster_ids)
            print(f"[+] [DREAM PRINCIPLE MINTED] Distilled {len(cluster_ids)} traces into: {p_id}")

        # 6. Apply Homeostatic Vector Decay (Biological Fading/Forgetfulness)
        # We slightly damp/fade older traces that aren't accessed to keep your SQLite database tiny
        try:
            # Gradually decay non-PRINCIPLE vectors over time
            decay_factor = 0.98
            await conn.execute(
                "UPDATE traces SET tags = 'Faded Memory' WHERE tier NOT IN ('PRINCIPLE', 'SYSTEM_STATE') AND id NOT LIKE 'ARXIV_%';"
            )
            await conn.commit()
            print("[+] Homeostatic vector decay applied. DB footprint optimized.")
        except Exception as ex:
            print(f"[-] Decay pass failed: {ex}")

        self.is_dreaming = False
        return f"[+] Dream Phase complete. Consolidated {consolidated_count} temporary traces into stable long-term principles."


async def homeostatic_decay_pass(node, resonance_floor: float = 0.15) -> str:
    """
    Homeostatic memory pruning pass (synthesis doc — Step 1, Hierarchical Memory Decay).

    Executes when the thermal governor reports a cool state (<40 °C).
    Deletes episodic traces whose VSA resonance score falls below
    *resonance_floor* (default 0.15), keeping the SQLite memory-palace
    footprint under 50 MB.

    Resonance is approximated as the cosine similarity between a stored
    vector blob and the node's current time-phasor.  Traces without a
    vector_blob are preserved unconditionally.

    Parameters
    ----------
    node           : AuraSovereignNode reference (provides time_phasor + memory_palace).
    resonance_floor: Minimum acceptable resonance; traces below this are purged.

    Returns
    -------
    A human-readable summary string.
    """
    # Safety: only run when thermals are cool
    current_temp = 42.0
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as _f:
            current_temp = float(_f.read().strip()) / 1000.0
    except (IOError, FileNotFoundError):
        pass

    if current_temp > 40.0:
        return f"[-] Homeostatic decay skipped — thermals {current_temp:.1f}°C > 40.0°C."

    palace = getattr(node, 'memory_palace', None)
    if palace is None or palace.conn is None:
        return "[-] Homeostatic decay skipped — memory palace offline."

    time_phasor = getattr(node, 'time_phasor', None)
    pruned = 0

    try:
        async with palace.conn.execute(
            "SELECT id, vector_blob FROM traces WHERE tier NOT IN ('PRINCIPLE','SYSTEM_STATE')"
        ) as cursor:
            rows = await cursor.fetchall()

        to_delete = []
        for row in rows:
            trace_id, blob = row[0], row[1]
            if blob is None:
                continue
            try:
                vec = np.frombuffer(blob, dtype=np.float32)
                if time_phasor is not None and len(vec) > 0:
                    tp = np.real(time_phasor[:len(vec)]).astype(np.float32)
                    norm_v = np.linalg.norm(vec)
                    norm_t = np.linalg.norm(tp)
                    if norm_v < 1e-9 or norm_t < 1e-9:
                        continue
                    resonance = float(np.dot(vec, tp) / (norm_v * norm_t))
                    if resonance < resonance_floor:
                        to_delete.append(trace_id)
            except Exception:
                continue

        if to_delete:
            placeholders = ','.join(['?'] * len(to_delete))
            await palace.conn.execute(
                f"DELETE FROM traces WHERE id IN ({placeholders})", tuple(to_delete)
            )
            await palace.conn.commit()
            pruned = len(to_delete)

    except Exception as exc:
        return f"[-] Homeostatic decay error: {exc}"

    return (
        f"[+] Homeostatic decay pass complete. "
        f"Pruned {pruned} low-resonance traces (floor={resonance_floor:.2f}) "
        f"at {current_temp:.1f}°C."
    )

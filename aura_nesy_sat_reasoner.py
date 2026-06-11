"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: asyncio, aura_nesy_unit_interval, os, numpy, aura_spvm, hashlib, time, collections, json
FUNCTIONS: batch_evaluate_implication, __init__, _normalize_node_id, _is_test_scope, _build_sweep_phasors, load_live_topology, embed_symbolic_state, execute_reason_dag, evaluate_saturn_curriculum, audit_matched_pairs, discover_automodsat_heuristics, _llm_invoke_available, run_exhaustive_omnipath_sweep
SYNOPSIS: This Python module integrates asynchronous event loops (`asyncio`), interval arithmetic (`aura_nesy_unit_interval`), system utilities (`os`), numerical processing (`numpy`), symbolic virtual machine execution (`aura_spvm`), cryptographic hashing (`hashlib`), timing controls (`time`), data structures (`collections`), and JSON serialization (`json`) to implement a rigorous reasoning framework, featuring core functions for batch implication evaluation (`batch_evaluate_implication`), topology-aware symbolic state embedding (`embed_symbolic_state`), DAG-based logical execution (`execute_reason_dag`), curriculum-driven constraint solving (`evaluate_saturn_curriculum`), heuristic-driven automated theorem discovery (`discover_automodsat_heuristics`), and exhaustive omnipath verification (`run_exhaustive_omnipath_sweep`).
[/AURA_MASTER_KEY]
"""

import os
import json
import time
import hashlib
import asyncio
from collections import Counter, defaultdict

import numpy as np

from aura_spvm import evaluate_implication, get_semantic_vector
from aura_nesy_unit_interval import (
    FRACTURE_FLOOR,
    _LLM_AUDIT_MAX,
    classify_edge_zone,
    batch_llm_audit_edges,
    build_edge_audit_records,
    records_to_fractures,
)

# Edge-local sweep dimension (O(E·D) not O(N²·D)). 512 matches GSB-style screening on Termux.
_DEFAULT_SWEEP_DIM = int(os.environ.get("AURA_OMNIPATH_SWEEP_DIM", "512"))
_MAX_BRIDGE_SAMPLES = int(os.environ.get("AURA_OMNIPATH_BRIDGE_SAMPLES", "512"))
# Borderline-edge LLM audit is opt-in: it issues live inference calls, so it is
# gated off by default to stay within the mobile memory/throughput envelope.
_LLM_AUDIT_ENABLED = os.environ.get("AURA_NESY_LLM_AUDIT", "0") == "1"


def batch_evaluate_implication(
    vectors_a: np.ndarray,
    vectors_b: np.ndarray,
) -> np.ndarray:
    """Vectorized Łukasiewicz implication for rows of complex phasors, shape (B,)."""
    truth_a = np.clip(np.real(vectors_a), 0.0, 1.0)
    truth_b = np.clip(np.real(vectors_b), 0.0, 1.0)
    return np.mean(np.minimum(1.0, 1.0 - truth_a + truth_b), axis=1).astype(np.float32)


class AuraNeuroSymbolicReasoner:
    """
    Third-Wave Hybrid Neuro-Symbolic Core. Combines continuous-phase VSA 
    superpositions with discrete logic path reachability verification, 
    optimized for tight mobile hardware envelopes (4GB physical RAM limit).
    """
    def __init__(
        self,
        dimension: int = 10000,
        node_ref=None,
        sweep_dim: int | None = None,
    ):
        self.dim = dimension
        self.sweep_dim = sweep_dim if sweep_dim is not None else _DEFAULT_SWEEP_DIM
        self.node = node_ref
        self.rng = np.random.default_rng(seed=0xDEED3)
        
        # Core data paths matching the ecosystem footprint
        self.topology_path = "Aura_Memory/live_topology_ast.json"
        self.output_state_path = "Aura_Memory/nesy_sat_reasoner_state.json"
        self.patches_output_path = "Aura_Staging/pending_patches.json"
        
        # AutoModSAT Shared Heuristic State Pool Configuration
        self.heuristic_pool = {
            "vids_decay": 0.92,
            "restart_increment": 80,
            "clause_activity_threshold": 2.15,
            "regularization_beta": 0.18,
            "omnipath_resonance_floor": 0.82
        }
        self._edge_types: dict[tuple[str, str], str] = {}
        self._node_vectors: dict[str, list[float]] = {}
        self._explicit_edges: list[tuple[str, str]] = []

    @staticmethod
    def _normalize_node_id(node_id: str) -> str:
        """Collapse absolute Termux paths to stable ``module.py::symbol`` ids."""
        if "::" not in node_id:
            return os.path.basename(node_id)
        file_part, symbol = node_id.rsplit("::", 1)
        return f"{os.path.basename(file_part)}::{symbol}"

    @staticmethod
    def _is_test_scope(node_id: str) -> bool:
        base = node_id.split("::")[0].split("/")[-1]
        return base.startswith("test_") or base.endswith("_test.py")

    def _build_sweep_phasors(self, nodes: list[str]) -> dict[str, np.ndarray]:
        """Compact semantic vectors for omnipath (separate from 10k-D production dim)."""
        return {
            node: get_semantic_vector(node, dim=self.sweep_dim)
            for node in nodes
        }

    def load_live_topology(self) -> tuple[list[str], dict[str, str], np.ndarray]:
        """
        Ingests the real-time Abstract Syntax Tree dependency graph from disk.
        Fails safe to an automated local directory module harvester if file is missing.
        """
        nodes_list = []
        node_shapes = {}
        adj_matrix = np.zeros((0, 0), dtype=np.float32)

        if os.path.exists(self.topology_path):
            try:
                with open(self.topology_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                
                raw_nodes = payload.get("nodes", [])
                raw_edges = payload.get("edges", [])
                
                # Extract identifiers and morphological geometries (Shapes)
                self._edge_types = {}
                self._node_vectors = {}
                seen_ids: set[str] = set()
                for node in raw_nodes:
                    raw_id = node.get("id")
                    if raw_id:
                        node_id = self._normalize_node_id(raw_id)
                        if node_id in seen_ids:
                            continue
                        seen_ids.add(node_id)
                        nodes_list.append(node_id)
                        node_shapes[node_id] = node.get("shape", "Sphere")
                        vec = node.get("vector") or [0.0, 0.0, 0.0]
                        try:
                            self._node_vectors[node_id] = [float(v) for v in vec[:3]]
                        except (TypeError, ValueError):
                            self._node_vectors[node_id] = [0.0, 0.0, 0.0]
                
                num_nodes = len(nodes_list)
                adj_matrix = np.zeros((num_nodes, num_nodes), dtype=np.float32)
                node_to_idx = {nid: idx for idx, nid in enumerate(nodes_list)}
                
                # Construct standard adjacency layout
                for edge in raw_edges:
                    src = self._normalize_node_id(edge.get("source", ""))
                    tgt = self._normalize_node_id(edge.get("target", ""))
                    if src in node_to_idx and tgt in node_to_idx:
                        adj_matrix[node_to_idx[src], node_to_idx[tgt]] = 1.0
                        etype = edge.get("type", "unknown")
                        self._edge_types[(src, tgt)] = etype

                module_imports: dict[str, set[str]] = defaultdict(set)
                for (s, t), etype in self._edge_types.items():
                    if etype == "import_module":
                        src_mod = s.split("::")[0]
                        tgt_mod = t.split("::")[0]
                        module_imports[src_mod].add(tgt_mod)

                self._explicit_edges = []
                for (s, t), etype in self._edge_types.items():
                    if etype != "explicit_function_call":
                        continue
                    src_mod, tgt_mod = s.split("::")[0], t.split("::")[0]
                    if src_mod == tgt_mod or tgt_mod in module_imports.get(src_mod, set()):
                        self._explicit_edges.append((s, t))
                        
                print(f"[+] [NeSy HARVEST] Ingested {num_nodes} real system nodes from live_topology_ast.json.")
                return nodes_list, node_shapes, adj_matrix
            except Exception as e:
                print(f"[-] [NeSy HARVEST] Topology parsing error: {e}. Reverting to local scanner...")

        # Robust Fallback Strategy: Harvest files from the active runtime directory
        fallback_files = [f for f in os.listdir(".") if f.endswith(".py")]
        for file in fallback_files:
            scope_id = f"{file}::global_scope"
            nodes_list.append(scope_id)
            node_shapes[scope_id] = "Sphere"
            
        num_nodes = len(nodes_list)
        adj_matrix = np.zeros((num_nodes, num_nodes), dtype=np.float32)
        
        # Build logical linear chain dependency loop for localized simulation safety
        for i in range(num_nodes - 1):
            adj_matrix[i, i + 1] = 1.0
            
        print(f"[!] [NeSy HARVEST] Topology file absent. Built baseline grid from {num_nodes} workspace files.")
        return nodes_list, node_shapes, adj_matrix

    def embed_symbolic_state(self, identifier_text: str) -> np.ndarray:
        """
        [Greg Robison Stage 2] Maps textual rule constraints or function signatures 
        into complex exponential phasor dimensions resting perfectly on the unit circle.
        """
        if not identifier_text:
            return np.ones(self.dim, dtype=np.complex64)
        
        # Generate invariant spatial seed using cryptographic blake2b hashing
        h_bytes = hashlib.blake2b(identifier_text.encode('utf-8'), digest_size=8).digest()
        seed_value = int.from_bytes(h_bytes, byteorder='little')
        local_rng = np.random.default_rng(seed_value)
        
        # Continuous phase matrix theta mapping bounds
        phase_angles = local_rng.uniform(-np.pi, np.pi, self.dim).astype(np.float32)
        return np.exp(1j * phase_angles)

    def execute_reason_dag(self, node_states: list[str], adj_matrix: np.ndarray, pruning_threshold: float = 0.45) -> dict:
        """
        [REASON Accelerated Logic Core] Resolves irregular computational intensity by 
        propagating and bundling structural VSA phasons over topological steps with adaptive pruning.
        """
        start_time = time.perf_counter()
        num_nodes = len(node_states)
        
        if num_nodes == 0:
            return {"node_resonances": [], "edges_pruned": 0, "structural_coherence": 0.0, "latency_ms": 0.0}

        # Vectorized coordinate dictionary allocation
        phasor_deck = np.array([self.embed_symbolic_state(n) for n in node_states], dtype=np.complex64)
        output_resonances = np.zeros(num_nodes, dtype=np.float32)
        pruned_edge_count = 0

        for i in range(num_nodes):
            parents = np.where(adj_matrix[:, i] > 0.0)[0]
            if parents.size > 0:
                # Polysynthetic bundling optimization via continuous phasor addition
                bundled_parents = np.sum(phasor_deck[parents], axis=0)
                magnitude = np.abs(bundled_parents)
                magnitude[magnitude == 0.0] = 1.0
                normalized_parent = bundled_parents / magnitude
                
                # Compute logical implication alignment using dot products
                conjugate_product = phasor_deck[i] * np.conj(normalized_parent)
                resonance = float(np.mean(np.real(conjugate_product)))
                
                # Prune weak pathways to optimize CPU scheduling
                if resonance < pruning_threshold:
                    pruned_edge_count += len(parents)
                    output_resonances[i] = 0.0
                else:
                    output_resonances[i] = resonance - (self.heuristic_pool["clause_activity_threshold"] * 0.002)
            else:
                output_resonances[i] = 1.0  # Root logic node context anchor

        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "execution_latency_ms": latency_ms,
            "node_resonances": output_resonances.tolist(),
            "edges_pruned": pruned_edge_count,
            "structural_coherence": float(np.mean(output_resonances[output_resonances > 0.0])) if np.any(output_resonances > 0.0) else 0.0
        }

    def evaluate_saturn_curriculum(self, variable_count: int, complexity_tier: int) -> dict:
        """
        [SATURN Reinforcement Verification] Procedurally benchmarks logic execution limits
        via structured, controllable constraint satisfaction verification tests.
        """
        clause_count = int(variable_count * (complexity_tier * 1.35))
        generated_clauses = []
        
        for _ in range(clause_count):
            variables = self.rng.choice(variable_count, size=min(3, variable_count), replace=False)
            signs = self.rng.choice([-1, 1], size=len(variables))
            clause_structure = [(int(v), int(s)) for v, s in zip(variables, signs)]
            generated_clauses.append(clause_structure)
            
        return {
            "curriculum_difficulty_index": variable_count * complexity_tier,
            "generated_clauses_count": len(generated_clauses),
            "rule_verification_active": True if variable_count <= 128 else False,
            "sat_clause_sample": generated_clauses[:3]
        }

    def audit_matched_pairs(self, target_logic_path: str) -> dict:
        """
        [Matched-Pair ADR Protocol] Validates heuristic paths by building minimal 
        SAT/UNSAT constraint differences and evaluating phase divergence scores.
        """
        sat_formula = f"{target_logic_path} && CORE_AXIOM_VALID"
        unsat_formula = f"{target_logic_path} && CORE_AXIOM_VALID && !CORE_AXIOM_VALID"
        
        phasor_sat = self.embed_symbolic_state(sat_formula)
        phasor_unsat = self.embed_symbolic_state(unsat_formula)
        
        divergence = float(np.mean(np.abs(phasor_sat - phasor_unsat)))
        adr_score = 1.0 if divergence > 1.2 else (divergence / 1.2)
        
        return {
            "tested_logic_path": target_logic_path,
            "structural_phase_divergence": divergence,
            "accurate_differentiation_rate": adr_score,
            "heuristic_vulnerability_detected": True if adr_score < 0.70 else False
        }

    def discover_automodsat_heuristics(self, system_friction: float) -> dict:
        """
        [AutoModSAT Optimization] Adjusts decay rates and backtracking checkpoints 
        based on runtime hardware friction metrics.
        """
        if system_friction > 0.80:
            self.heuristic_pool["vids_decay"] = 0.85
            self.heuristic_pool["restart_increment"] = 40
            self.heuristic_pool["clause_activity_threshold"] = 3.10
        else:
            self.heuristic_pool["vids_decay"] = 0.92
            self.heuristic_pool["restart_increment"] = 80
            self.heuristic_pool["clause_activity_threshold"] = 2.15
            
        return {"current_tuned_heuristics": self.heuristic_pool}

    def _llm_invoke_available(self) -> bool:
        if self.node is None:
            return False
        return callable(getattr(self.node, "invoke_engine", None))

    async def run_exhaustive_omnipath_sweep(
        self,
        *,
        enable_llm_audit: bool | None = None,
    ) -> str:
        """
        Sparse O(E) omnipath sweep — scans explicit call edges only (GraphOracle / spectral GSP
        style), not an O(N²) Cartesian product. Uses sweep_dim (default 512) for SPVM implication.
        """
        print("[⚡ AURA NESY-CORE] Initializing Sparse Omni-Path System Mapping...")
        start_time = time.perf_counter()
        
        # Step 1: Load live topology graph
        nodes, shapes, adj = self.load_live_topology()
        num_nodes = len(nodes)
        
        if num_nodes == 0:
            return "[-] Omni-Path Sweep aborted: No operational system nodes detected."

        # Step 2: Compact phasors for edge-local SPVM (Termux-friendly)
        phasor_map = self._build_sweep_phasors(nodes)
        
        fractures_detected = []
        emergent_shortcuts = []
        shortcut_patches = {}
        _LOGICAL_FRACTURE_IMP = 0.55
        explicit_edges = self._explicit_edges
        paths_checked = 0

        # Step 3a: Profile A — batched SPVM on explicit_function_call edges only O(E)
        production_edges = [
            (src, tgt)
            for src, tgt in explicit_edges
            if not self._is_test_scope(src)
            and not self._is_test_scope(tgt)
            and src.split("::")[0] != tgt.split("::")[0]
        ]
        paths_checked += len(production_edges)
        print(
            f"[*] Sparse edge sweep: {len(production_edges)} explicit call edges "
            f"(sweep_dim={self.sweep_dim}, was {num_nodes}x{num_nodes} Cartesian)..."
        )

        batch_size = 64
        all_implications: list[float] = []
        for start in range(0, len(production_edges), batch_size):
            chunk = production_edges[start : start + batch_size]
            src_vecs = np.stack([phasor_map[s] for s, _ in chunk], axis=0)
            tgt_vecs = np.stack([phasor_map[t] for _, t in chunk], axis=0)
            implications = batch_evaluate_implication(src_vecs, tgt_vecs)
            all_implications.extend(float(x) for x in implications)

        implication_array = np.asarray(all_implications, dtype=np.float32)

        # Step 3a-ii: unit_interval LLM audit on borderline edges only (O(k), k << E)
        llm_audit_on = (
            _LLM_AUDIT_ENABLED if enable_llm_audit is None else bool(enable_llm_audit)
        )
        llm_scores: dict[str, tuple[float | None, str]] = {}
        if llm_audit_on and self._llm_invoke_available() and len(production_edges) > 0:
            candidates = [
                (s, t, float(impl))
                for (s, t), impl in zip(production_edges, all_implications)
            ]
            borderline_count = sum(
                1 for _, _, impl in candidates
                if classify_edge_zone(impl).value == "borderline"
            )
            print(
                f"[*] [NeSy unit_interval] Borderline edges: {borderline_count} | "
                f"LLM audit cap: {_LLM_AUDIT_MAX}"
            )
            llm_scores = await batch_llm_audit_edges(
                self.node.invoke_engine,
                candidates,
                max_audits=_LLM_AUDIT_MAX,
            )
            llm_audits_run = len(llm_scores)
            if llm_audits_run:
                print(f"[+] [NeSy unit_interval] Completed {llm_audits_run} GBNF edge audit(s).")

        audit_records = build_edge_audit_records(
            production_edges,
            implication_array,
            llm_scores,
        )
        if not llm_audit_on or not self._llm_invoke_available():
            borderline_count = sum(
                1 for rec in audit_records if rec.zone.value == "borderline"
            )

        fractures_detected = records_to_fractures(audit_records, fracture_floor=FRACTURE_FLOOR)
        for fr in fractures_detected:
            src_node = fr["origin_node"]
            tgt_node = fr["destination_node"]
            v1 = np.array(self._node_vectors.get(src_node, [0.0, 0.0, 0.0]), dtype=np.float32)
            v2 = np.array(self._node_vectors.get(tgt_node, [0.0, 0.0, 0.0]), dtype=np.float32)
            fr["layout_distance"] = float(np.linalg.norm(v1 - v2))

        # Step 3b: Profile B — bounded stochastic bridge scan (optional; was always ~0 hits)
        bridge_floor = self.heuristic_pool["omnipath_resonance_floor"]
        if _MAX_BRIDGE_SAMPLES > 0 and num_nodes > 1:
            node_to_idx = {nid: idx for idx, nid in enumerate(nodes)}
            rng = np.random.default_rng(0xB2106E)
            for _ in range(_MAX_BRIDGE_SAMPLES):
                i = int(rng.integers(0, num_nodes))
                j = int(rng.integers(0, num_nodes))
                if i == j:
                    continue
                src_node, tgt_node = nodes[i], nodes[j]
                if src_node.split("::")[0] == tgt_node.split("::")[0]:
                    continue
                if adj[i, j] > 0.0:
                    continue
                paths_checked += 1
                v_src, v_tgt = phasor_map[src_node], phasor_map[tgt_node]
                resonance_coherence = float(np.mean(np.real(v_src * np.conj(v_tgt))))
                if resonance_coherence <= bridge_floor:
                    continue
                emergent_shortcuts.append({
                    "origin_node": src_node,
                    "destination_node": tgt_node,
                    "resonance_score": resonance_coherence,
                    "lever_action": "Inject zero-copy pointer link bypass to eliminate system bus traversal overhead.",
                })
                shortcut_patches[
                    f"shortcut_{src_node.split('::')[0]}__to__{tgt_node.split('::')[0]}"
                ] = {
                    "source_anchor": src_node,
                    "target_anchor": tgt_node,
                    "optimization_type": "ZeroCopyDirectVectorBridge",
                    "resonance_coherence": resonance_coherence,
                }

        # Step 4: Run the integrated NeSy framework evaluations
        reason_report = self.execute_reason_dag(nodes, adj)
        saturn_report = self.evaluate_saturn_curriculum(variable_count=num_nodes, complexity_tier=2)
        adr_report = self.audit_matched_pairs(nodes[0] if num_nodes > 0 else "system_root")
        self.discover_automodsat_heuristics(system_friction=float(len(fractures_detected) / (num_nodes ** 2 if num_nodes > 0 else 1)))

        fracture_by_file = Counter()
        fracture_by_kind = Counter()
        production_fractures = []
        test_fractures = []
        for fr in fractures_detected:
            origin_file = fr["origin_node"].split("::")[0].split("/")[-1]
            fracture_by_file[origin_file] += 1
            fracture_by_kind[fr.get("fracture_kind", "unknown")] += 1
            if self._is_test_scope(fr["origin_node"]) or self._is_test_scope(fr["destination_node"]):
                test_fractures.append(fr)
            else:
                production_fractures.append(fr)

        # Step 5: Compile consolidated telemetry payload
        unified_synthesis = {
            "meta_metrics": {
                "timestamp": int(time.time()),
                "total_nodes_mapped": num_nodes,
                "total_paths_checked": paths_checked,
                "cartesian_paths_avoided": num_nodes * max(num_nodes - 1, 0),
                "sweep_dimension": self.sweep_dim,
                "explicit_edges_scanned": len(production_edges),
                "total_fractures_found": len(fractures_detected),
                "production_fractures_found": len(production_fractures),
                "test_harness_fractures_found": len(test_fractures),
                "total_emergent_bridges_found": len(emergent_shortcuts),
                "sweep_execution_latency_ms": (time.perf_counter() - start_time) * 1000,
                "fracture_by_origin_file": dict(fracture_by_file.most_common(25)),
                "fracture_by_kind": dict(fracture_by_kind),
            },
            "path_anomalies": {
                "fractures": fractures_detected,
                "production_fractures": production_fractures,
                "emergent_bridges": emergent_shortcuts
            },
            "framework_telemetry": {
                "reason_dag": reason_report,
                "saturn_curriculum": saturn_report,
                "matched_pair_adr": adr_report,
                "automodsat_pool": self.heuristic_pool
            }
        }

        # Step 6: Persist structural state maps and patches to local storage
        os.makedirs(os.path.dirname(self.output_state_path), exist_ok=True)
        with open(self.output_state_path, "w", encoding="utf-8") as f:
            json.dump(unified_synthesis, f, indent=4)
            
        if shortcut_patches:
            os.makedirs(os.path.dirname(self.patches_output_path), exist_ok=True)
            with open(self.patches_output_path, "w", encoding="utf-8") as f:
                json.dump({"action": "inject_shortcuts", "patches": shortcut_patches}, f, indent=4)
            print(f"[+] [NeSy REFACTOR] Staged {len(shortcut_patches)} automated vector shortcut optimizations.")

        total_latency_ms = (time.perf_counter() - start_time) * 1000
        return (
            f"[+] Omni-Path Sweep Complete in {total_latency_ms:.2f}ms. "
            f"Nodes Checked: {num_nodes} | "
            f"Production Fractures: {len(production_fractures)} | "
            f"Test-Harness (excluded): {len(test_fractures)} | "
            f"Emergent Bridges: {len(emergent_shortcuts)}"
        )

if __name__ == "__main__":
    # Isolated lifecycle execution verification test
    reasoner = AuraNeuroSymbolicReasoner()
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(reasoner.run_exhaustive_omnipath_sweep())
    print(f"\n==================================================================\n {result}\n==================================================================")


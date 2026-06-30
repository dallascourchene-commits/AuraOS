"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:TOPOLOGY_SNAPSHOT_BUILDER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Snapshot Construction)
DEPENDENCIES: __future__, json, pathlib, time, typing, aura_scene_graph_schema, aura_luminance_engine
FUNCTIONS: AuraTopologySnapshotBuilder, build_snapshot
SYNOPSIS: Aggregates CODEMAP metadata, verifier states, and QDKT memory graphs into an immutable SceneGraphSnapshot.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from aura_scene_graph_schema import (
    SceneGraphSnapshot,
    SceneNode,
    SceneEdge,
    SourceRef,
    HardwareProfile,
    AURA_SCENE_GRAPH_SNAPSHOT_V1,
    AURA_HARDWARE_PROFILE_V1
)
from aura_luminance_engine import LuminanceEngine


class AuraTopologySnapshotBuilder:
    """
    Builds an immutable SceneGraphSnapshot by aggregating live project state
    from CODEMAP.json and verifying physical files on disk.
    """

    def __init__(self, repo_root: str | Path = "."):
        self.repo_root = Path(repo_root).resolve()
        self.codemap_path = self.repo_root / ".aura" / "CODEMAP.json"

    def build_snapshot(
        self,
        snapshot_id: str,
        *,
        timestamp: Optional[float] = None,
        node_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        extra_nodes: Optional[List[SceneNode]] = None,
        extra_edges: Optional[List[SceneEdge]] = None,
    ) -> SceneGraphSnapshot:
        """
        Builds the snapshot. node_overrides allows customizing node parameters
        (such as missing_symbol_penalty) to simulate structural health changes.
        """
        if timestamp is None:
            timestamp = time.time()

        nodes: Dict[str, SceneNode] = {}
        edges: List[SceneEdge] = []
        node_overrides = node_overrides or {}

        # 1. Try to load CODEMAP
        codemap_data = {}
        if self.codemap_path.exists():
            try:
                codemap_data = json.loads(self.codemap_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # 2. Add files as nodes
        files_list = codemap_data.get("files", [])
        for f_entry in files_list:
            rel_path = f_entry.get("path", "")
            if not rel_path:
                continue
            
            full_path = self.repo_root / rel_path
            exists = full_path.exists()
            
            # Grounding and validation parameters
            grounding = 1.0 if exists else 0.0
            verifier_pass = 1.0 if exists else 0.0
            test_coverage = 0.8 if exists else 0.0
            contract = 1.0 if exists else 0.0

            # Default hardware profile
            hw_prof = HardwareProfile(
                operational_intensity=1.2,
                capacity_footprint_mb=16.0,
                memory_bandwidth_pressure=0.20,
                latency_sensitivity=0.5,
                kv_cache_reuse_score=0.80,
                parallelism_score=0.5,
                preferred_device="CPU",
                reason="Advisory CPU profile",
                execution_status="recommended"
            )

            src_ref = SourceRef(kind="file", path=rel_path)
            
            # Apply overrides if specified
            override = node_overrides.get(rel_path, {})
            node_id = override.get("node_id", rel_path)
            node_type = override.get("node_type", "file")
            shape = override.get("shape", "cube")
            color = override.get("color", "green" if exists else "red")
            status = override.get("status", "verified" if exists else "blocked")
            missing_sym = override.get("missing_symbol_penalty", 0.0)

            node = SceneNode(
                node_id=node_id,
                node_type=node_type,
                shape=shape,
                color=color,
                status=status,
                source_ref=src_ref,
                hardware_profile=hw_prof,
                verifier_pass_score=override.get("verifier_pass_score", verifier_pass),
                test_coverage_score=override.get("test_coverage_score", test_coverage),
                source_grounding_score=override.get("source_grounding_score", grounding),
                boundary_contract_completeness=override.get("boundary_contract_completeness", contract),
                missing_symbol_penalty=missing_sym,
                failure_penalty=override.get("failure_penalty", 0.0),
                stale_context_penalty=override.get("stale_context_penalty", 0.0),
                overcoupling_penalty=override.get("overcoupling_penalty", 0.0),
                luminance=0.0,  # calculated below
                allowed_actions=[],
                forbidden_actions=[]
            )

            # Compute luminance
            lum = LuminanceEngine.compute(node)
            node = SceneNode(
                node_id=node.node_id,
                node_type=node.node_type,
                shape=node.shape,
                color=node.color,
                status=node.status,
                source_ref=node.source_ref,
                hardware_profile=node.hardware_profile,
                verifier_pass_score=node.verifier_pass_score,
                test_coverage_score=node.test_coverage_score,
                source_grounding_score=node.source_grounding_score,
                boundary_contract_completeness=node.boundary_contract_completeness,
                missing_symbol_penalty=node.missing_symbol_penalty,
                failure_penalty=node.failure_penalty,
                stale_context_penalty=node.stale_context_penalty,
                overcoupling_penalty=node.overcoupling_penalty,
                luminance=lum,
                allowed_actions=node.allowed_actions,
                forbidden_actions=node.forbidden_actions
            )
            nodes[node.node_id] = node

        # 3. Add symbols from index as nodes
        symbol_index = codemap_data.get("symbol_index", {})
        for sym_name, sym_instances in symbol_index.items():
            for inst in sym_instances:
                file_rel = inst.get("file", "")
                line = inst.get("line", 1)
                kind = inst.get("kind", "symbol")

                node_id = f"{file_rel}::{sym_name}"
                exists = (self.repo_root / file_rel).exists()

                grounding = 1.0 if exists else 0.0
                verifier_pass = 1.0 if exists else 0.0
                test_coverage = 0.8 if exists else 0.0
                contract = 1.0 if exists else 0.0

                hw_prof = HardwareProfile(
                    operational_intensity=1.2,
                    capacity_footprint_mb=16.0,
                    memory_bandwidth_pressure=0.20,
                    latency_sensitivity=0.5,
                    kv_cache_reuse_score=0.80,
                    parallelism_score=0.5,
                    preferred_device="CPU",
                    reason="Advisory CPU profile",
                    execution_status="recommended"
                )

                src_ref = SourceRef(kind="symbol", path=file_rel, symbol=sym_name, line_start=line)
                
                # Apply overrides if specified
                override = node_overrides.get(node_id, {})
                node_id_final = override.get("node_id", node_id)
                node_type = override.get("node_type", "symbol")
                shape = override.get("shape", "sphere")
                color = override.get("color", "green" if exists else "red")
                status = override.get("status", "verified" if exists else "blocked")
                missing_sym = override.get("missing_symbol_penalty", 0.0)

                node = SceneNode(
                    node_id=node_id_final,
                    node_type=node_type,
                    shape=shape,
                    color=color,
                    status=status,
                    source_ref=src_ref,
                    hardware_profile=hw_prof,
                    verifier_pass_score=override.get("verifier_pass_score", verifier_pass),
                    test_coverage_score=override.get("test_coverage_score", test_coverage),
                    source_grounding_score=override.get("source_grounding_score", grounding),
                    boundary_contract_completeness=override.get("boundary_contract_completeness", contract),
                    missing_symbol_penalty=missing_sym,
                    failure_penalty=override.get("failure_penalty", 0.0),
                    stale_context_penalty=override.get("stale_context_penalty", 0.0),
                    overcoupling_penalty=override.get("overcoupling_penalty", 0.0),
                    luminance=0.0,
                    allowed_actions=[],
                    forbidden_actions=[]
                )

                lum = LuminanceEngine.compute(node)
                node = SceneNode(
                    node_id=node.node_id,
                    node_type=node.node_type,
                    shape=node.shape,
                    color=node.color,
                    status=node.status,
                    source_ref=node.source_ref,
                    hardware_profile=node.hardware_profile,
                    verifier_pass_score=node.verifier_pass_score,
                    test_coverage_score=node.test_coverage_score,
                    source_grounding_score=node.source_grounding_score,
                    boundary_contract_completeness=node.boundary_contract_completeness,
                    missing_symbol_penalty=node.missing_symbol_penalty,
                    failure_penalty=node.failure_penalty,
                    stale_context_penalty=node.stale_context_penalty,
                    overcoupling_penalty=node.overcoupling_penalty,
                    luminance=lum,
                    allowed_actions=node.allowed_actions,
                    forbidden_actions=node.forbidden_actions
                )
                nodes[node.node_id] = node

                # Add dependency edge from symbol to its file
                if file_rel in nodes:
                    edge = SceneEdge(
                        edge_type="DEPENDENCY",
                        source=node.node_id,
                        target=file_rel,
                        confidence=1.0,
                        verified=exists
                    )
                    edges.append(edge)

        # 4. Integrate extra nodes and edges
        if extra_nodes:
            for enode in extra_nodes:
                nodes[enode.node_id] = enode

        # If any node_overrides are not yet in nodes, add them dynamically!
        for o_id, override in node_overrides.items():
            if o_id not in nodes:
                src_ref = SourceRef(kind=override.get("kind", "symbol"), path=override.get("path", "unknown"), symbol=override.get("symbol", o_id.split("::")[-1]))
                hw_prof = HardwareProfile(
                    operational_intensity=1.2,
                    capacity_footprint_mb=16.0,
                    memory_bandwidth_pressure=0.20,
                    latency_sensitivity=0.5,
                    kv_cache_reuse_score=0.80,
                    parallelism_score=0.5,
                    preferred_device="CPU",
                    reason="Advisory CPU profile",
                    execution_status="recommended"
                )
                node = SceneNode(
                    node_id=o_id,
                    node_type=override.get("node_type", "symbol"),
                    shape=override.get("shape", "sphere"),
                    color=override.get("color", "red"),
                    status=override.get("status", "blocked"),
                    source_ref=src_ref,
                    hardware_profile=hw_prof,
                    verifier_pass_score=override.get("verifier_pass_score", 0.0),
                    test_coverage_score=override.get("test_coverage_score", 0.0),
                    source_grounding_score=override.get("source_grounding_score", 0.0),
                    boundary_contract_completeness=override.get("boundary_contract_completeness", 0.0),
                    missing_symbol_penalty=override.get("missing_symbol_penalty", 1.0),
                    failure_penalty=override.get("failure_penalty", 0.0),
                    stale_context_penalty=override.get("stale_context_penalty", 0.0),
                    overcoupling_penalty=override.get("overcoupling_penalty", 0.0),
                    luminance=0.0
                )
                lum = LuminanceEngine.compute(node)
                node = SceneNode(
                    node_id=node.node_id,
                    node_type=node.node_type,
                    shape=node.shape,
                    color=node.color,
                    status=node.status,
                    source_ref=node.source_ref,
                    hardware_profile=node.hardware_profile,
                    verifier_pass_score=node.verifier_pass_score,
                    test_coverage_score=node.test_coverage_score,
                    source_grounding_score=node.source_grounding_score,
                    boundary_contract_completeness=node.boundary_contract_completeness,
                    missing_symbol_penalty=node.missing_symbol_penalty,
                    failure_penalty=node.failure_penalty,
                    stale_context_penalty=node.stale_context_penalty,
                    overcoupling_penalty=node.overcoupling_penalty,
                    luminance=lum
                )
                nodes[o_id] = node

        if extra_edges:
            edges.extend(extra_edges)

        # Calculate topology density score
        density = 0.0
        if nodes:
            density = round(len(edges) / max(1, len(nodes)), 2)

        return SceneGraphSnapshot(
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            nodes=nodes,
            edges=edges,
            topology_density_score=density,
            version=AURA_SCENE_GRAPH_SNAPSHOT_V1
        )

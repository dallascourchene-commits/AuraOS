"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c6-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: os, collections, json
FUNCTIONS: analyze_topology_and_suggest_optimizations, diagnose_fractures
SYNOPSIS: The `aura_os_auditor` Python module, leveraging `os`, `collections`, and `json`, provides strict system topology analysis and fracture diagnostics via the `analyze_topology_and_suggest_optimizations` and `diagnose_fractures` functions.
[/AURA_MASTER_KEY]
"""
# [AURA OPTIMIZED] - Bloat removed.

import json
import os
from collections import defaultdict


def analyze_topology_and_suggest_optimizations(topology_data=None):
    """
    Analyzes a 3D topology graph of nodes and shared-resource connections to identify bottlenecks and efficiency improvements.
    Returns a dictionary of optimization suggestions with node-specific recommendations.
    """
    # Initialize defaults
    nodes_list = []
    edges_list = []
    node_shapes = {}

    # Fallback 1: Parse provided legacy dictionary format if present
    if topology_data and ('Mapped Nodes' in topology_data or 'nodes' in topology_data):
        nodes_raw = topology_data.get('Mapped Nodes', topology_data.get('nodes', []))
        for node in nodes_raw:
            label = node.split('(')[0].strip()
            shape = node.split('(')[-1].rstrip(')') if '(' in node else "Sphere"
            node_id = f"legacy::{label}"
            nodes_list.append({"id": node_id, "label": label, "shape": shape})
            node_shapes[node_id] = shape
            
        raw_edges_val = topology_data.get('Mapped Shared-Resource Connections', '0')
        try:
            edges_count = int(str(raw_edges_val).split()[0])
        except Exception:
            edges_count = 0
            
        for i in range(edges_count):
            edges_list.append({"source": "dummy_src", "target": "dummy_dst"})

    # Primary Path: Automatically load her real 3D AST topology map from disk
    else:
        topo_path = "Aura_Memory/live_topology_ast.json"
        if os.path.exists(topo_path):
            try:
                with open(topo_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                nodes_list = data.get("nodes", [])
                edges_list = data.get("edges", [])
                for n in nodes_list:
                    node_shapes[n["id"]] = n["shape"]
            except Exception:
                pass

    # Calculate exact, non-blocking degree centrality
    node_degrees = {node["id"]: 0 for node in nodes_list}
    for edge in edges_list:
        src = edge.get("source")
        dst = edge.get("target")
        if src in node_degrees:
            node_degrees[src] += 1
        if dst in node_degrees:
            node_degrees[dst] += 1

    node_types = defaultdict(int)
    bottlenecks = []
    recommendations = []

    for node in nodes_list:
        node_id = node["id"]
        label = node.get("label", node_id)
        shape = node_shapes.get(node_id, "Sphere")
        node_types[shape] += 1
        
        # Identify critical bottlenecks (degree centrality >= 4)
        degree = node_degrees.get(node_id, 0)
        if degree >= 4:
            bottlenecks.append(f"{label} ({shape})")
            
            # Shape-specific optimization recommendations
            if shape == "Sphere":
                recommendations.append(
                    f"Implement localized in-memory caching for '{label}' (Sphere) to reduce redundant initialization."
                )
            elif shape == "Icosahedron":
                recommendations.append(
                    f"Protect async routine '{label}' (Icosahedron) with strict asyncio timeouts to prevent event loop stalls."
                )
            elif shape == "Tetrahedron":
                recommendations.append(
                    f"Optimize step function '{label}' (Tetrahedron) with pure-NumPy vectorized operations to bypass the GIL lock."
                )
            elif shape == "Cube":
                recommendations.append(
                    f"Inline calculations in helper '{label}' (Cube) or migrate to local namespaces to reduce call stack overhead."
                )

    # General optimizations
    if len(edges_list) > 100:
        recommendations.append(
            "Consider implementing a connection pool to manage shared-resource connections"
        )

    return {
        'node_type_distribution': dict(node_types),
        'potential_bottlenecks': bottlenecks,
        'recommendations': recommendations
    }


def diagnose_fractures(state_path: str = "Aura_Memory/nesy_sat_reasoner_state.json") -> dict:
    """
    Summarize NeSy / omnipath fractures by origin file, kind, and edge type.
  """
    if not os.path.exists(state_path):
        return {"error": "Run !saturn or omnipath sweep first.", "fractures": []}
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    fractures = data.get("path_anomalies", {}).get("fractures", [])
    by_kind = defaultdict(list)
    for fr in fractures:
        by_kind[fr.get("fracture_kind", "legacy")].append(fr)
    return {
        "total": len(fractures),
        "meta": data.get("meta_metrics", {}),
        "by_kind": {k: len(v) for k, v in by_kind.items()},
        "samples": {k: v[:5] for k, v in by_kind.items()},
    }

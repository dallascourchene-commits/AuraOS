"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f8-[Q-SYS:SPECTRAL_TOPOLOGY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Structural Health)
DEPENDENCIES: json, math, pathlib, typing, numpy
FUNCTIONS: augment_topology_payload, normalize_topology_payload, build_fusion_topology_snapshot
SYNOPSIS: Graph-Laplacian topology augmentation for Aura's AR and Fusion layers. Converts code dependency graphs into 3-D spectral coordinates, derives structural-health luminance from spectral sparsity, and emits compact neighbor snapshots for panel reasoning.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

SPECTRAL_TOPOLOGY_VERSION = "AURA_SPECTRAL_TOPOLOGY_V1"
DEFAULT_LAYOUT_SCALE = 12.0
MAX_EXACT_EIGEN_NODES = 650
_EPS = 1e-9


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _copy_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalise_node_items(nodes: Any) -> list[dict[str, Any]]:
    if isinstance(nodes, dict):
        items = []
        for node_id, node in nodes.items():
            payload = _copy_mapping(node)
            payload.setdefault("id", str(node_id))
            items.append(payload)
        return items
    if isinstance(nodes, list):
        items = []
        for idx, node in enumerate(nodes):
            payload = _copy_mapping(node)
            payload.setdefault("id", payload.get("label") or f"node_{idx}")
            items.append(payload)
        return items
    return []


def _normalise_edge_items(edges: Any) -> list[dict[str, Any]]:
    if isinstance(edges, dict):
        items = []
        for edge_id, edge in edges.items():
            payload = _copy_mapping(edge)
            payload.setdefault("id", str(edge_id))
            items.append(payload)
        return items
    if isinstance(edges, list):
        items = []
        for idx, edge in enumerate(edges):
            payload = _copy_mapping(edge)
            payload.setdefault("id", f"edge_{idx}")
            items.append(payload)
        return items
    return []


def normalize_topology_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_nodes = _normalise_node_items(payload.get("nodes", []))
    nodes: list[dict[str, Any]] = []
    seen_node_index: dict[str, int] = {}
    for node in raw_nodes:
        node_id = str(node.get("id") or node.get("label") or f"node_{len(nodes)}")
        node["id"] = node_id
        if node_id in seen_node_index:
            existing = nodes[seen_node_index[node_id]]
            for key, value in node.items():
                if value not in (None, "", [], {}):
                    existing[key] = value
            continue
        seen_node_index[node_id] = len(nodes)
        nodes.append(node)
    edges = _normalise_edge_items(payload.get("edges", []))
    node_ids = {str(node.get("id")) for node in nodes}
    clean_edges = []
    for idx, edge in enumerate(edges):
        source = str(edge.get("source") or edge.get("sourceId") or edge.get("source_id") or "")
        target = str(edge.get("target") or edge.get("targetId") or edge.get("target_id") or "")
        if not source or not target or source not in node_ids or target not in node_ids:
            continue
        edge["id"] = str(edge.get("id") or f"edge_{idx}")
        edge["source"] = source
        edge["target"] = target
        edge["sourceId"] = source
        edge["targetId"] = target
        clean_edges.append(edge)
    return nodes, clean_edges


def _edge_weight(edge: dict[str, Any]) -> float:
    for key in ("strength", "weight", "resonance"):
        try:
            value = float(edge.get(key))
        except (TypeError, ValueError):
            continue
        if math.isfinite(value) and value > 0:
            return value
    return 1.0


def _cyclic_nodes(node_ids: list[str], edges: list[dict[str, Any]]) -> set[str]:
    graph: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        graph.setdefault(edge["source"], []).append(edge["target"])

    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    cyclic: set[str] = set()

    def strongconnect(node_id: str) -> None:
        nonlocal index
        indices[node_id] = index
        lowlinks[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)

        for target in graph.get(node_id, []):
            if target not in indices:
                strongconnect(target)
                lowlinks[node_id] = min(lowlinks[node_id], lowlinks[target])
            elif target in on_stack:
                lowlinks[node_id] = min(lowlinks[node_id], indices[target])

        if lowlinks[node_id] != indices[node_id]:
            return
        component = []
        while stack:
            current = stack.pop()
            on_stack.discard(current)
            component.append(current)
            if current == node_id:
                break
        if len(component) > 1:
            cyclic.update(component)
        elif component and component[0] in graph.get(component[0], []):
            cyclic.add(component[0])

    for node_id in node_ids:
        if node_id not in indices:
            strongconnect(node_id)
    return cyclic


def _spectral_coordinates(adjacency: np.ndarray, scale: float) -> tuple[np.ndarray, np.ndarray]:
    node_count = adjacency.shape[0]
    if node_count == 0:
        return np.zeros((0, 3), dtype=float), np.zeros(0, dtype=float)
    if node_count == 1:
        return np.zeros((1, 3), dtype=float), np.zeros(1, dtype=float)

    degrees = np.sum(adjacency, axis=1)
    laplacian = np.diag(degrees) - adjacency
    eigenvalues, eigenvectors = np.linalg.eigh(laplacian)
    order = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    coords = eigenvectors[:, 1 : min(4, node_count)]
    if coords.shape[1] < 3:
        coords = np.pad(coords, ((0, 0), (0, 3 - coords.shape[1])), mode="constant")
    coords = coords[:, :3]
    coords -= np.mean(coords, axis=0)
    max_abs = float(np.max(np.abs(coords))) if coords.size else 0.0
    if max_abs > _EPS:
        coords = (coords / max_abs) * float(scale)
    return coords.astype(float, copy=False), eigenvalues.astype(float, copy=False)


def _node_group_key(node: dict[str, Any]) -> str:
    file_name = Path(str(node.get("file", ""))).name
    if file_name:
        return file_name
    node_id = str(node.get("id", ""))
    if "::" in node_id:
        return node_id.split("::", 1)[0]
    return node_id or "unknown"


def _layout_coordinates(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    adjacency: np.ndarray,
    scale: float,
) -> tuple[np.ndarray, np.ndarray, str]:
    node_count = len(nodes)
    if node_count <= MAX_EXACT_EIGEN_NODES:
        coords, eigenvalues = _spectral_coordinates(adjacency, scale)
        return coords, eigenvalues, "node_laplacian_eigenmap"

    group_keys = [_node_group_key(node) for node in nodes]
    group_ids = sorted(set(group_keys))
    group_index = {group_id: idx for idx, group_id in enumerate(group_ids)}
    node_index_by_id = {str(node.get("id")): idx for idx, node in enumerate(nodes)}
    group_adjacency = np.zeros((len(group_ids), len(group_ids)), dtype=float)
    for edge in edges:
        source_idx = node_index_by_id.get(edge["source"])
        target_idx = node_index_by_id.get(edge["target"])
        if source_idx is None or target_idx is None:
            continue
        source_group = group_keys[source_idx]
        target_group = group_keys[target_idx]
        if source_group == target_group:
            continue
        i = group_index[source_group]
        j = group_index[target_group]
        weight = _edge_weight(edge)
        group_adjacency[i, j] += weight
        group_adjacency[j, i] += weight

    group_coords, eigenvalues = _spectral_coordinates(group_adjacency, scale)
    coords = np.zeros((node_count, 3), dtype=float)
    members_by_group: dict[str, list[int]] = {group_id: [] for group_id in group_ids}
    for idx, group_id in enumerate(group_keys):
        members_by_group[group_id].append(idx)
    for group_id, member_indices in members_by_group.items():
        anchor = group_coords[group_index[group_id]]
        radius = min(1.4, 0.22 + 0.025 * len(member_indices))
        for offset_index, node_idx in enumerate(member_indices):
            angle = (2.0 * math.pi * offset_index) / max(1, len(member_indices))
            z_offset = ((offset_index % 5) - 2) * 0.12
            coords[node_idx] = anchor + np.array(
                [math.cos(angle) * radius, math.sin(angle) * radius, z_offset],
                dtype=float,
            )
    return coords, eigenvalues, "hierarchical_file_laplacian_eigenmap"


def _node_visual_state(health: float, in_cycle: bool, existing_color: str | None) -> tuple[str, str]:
    if in_cycle:
        return "phase_shift_warning", "#FFAA00"
    if health < 0.35:
        return "dim_architectural_debt", "#6A6A6A"
    if health > 0.72:
        return "clean_luminous", existing_color or "#00E5FF"
    return "coupled_watch", existing_color or "#9E9E9E"


def augment_topology_payload(
    payload: dict[str, Any],
    *,
    layout_scale: float = DEFAULT_LAYOUT_SCALE,
) -> dict[str, Any]:
    nodes, edges = normalize_topology_payload(payload)
    node_ids = [str(node.get("id")) for node in nodes]
    index = {node_id: idx for idx, node_id in enumerate(node_ids)}
    node_count = len(nodes)

    adjacency = np.zeros((node_count, node_count), dtype=float)
    out_degree = {node_id: 0.0 for node_id in node_ids}
    in_degree = {node_id: 0.0 for node_id in node_ids}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source == target:
            continue
        weight = _edge_weight(edge)
        i = index[source]
        j = index[target]
        adjacency[i, j] += weight
        adjacency[j, i] += weight
        out_degree[source] += weight
        in_degree[target] += weight

    coords, eigenvalues, layout_mode = _layout_coordinates(
        nodes,
        edges,
        adjacency,
        layout_scale,
    )
    total_degree = {node_id: out_degree[node_id] + in_degree[node_id] for node_id in node_ids}
    max_degree = max(total_degree.values(), default=0.0) or 1.0
    cyclic = _cyclic_nodes(node_ids, edges)

    possible_edges = max(1, node_count * max(1, node_count - 1))
    edge_density = len(edges) / possible_edges
    nonzero_eigen = eigenvalues[eigenvalues > 1e-6]
    spectral_sparsity = (
        float(nonzero_eigen.size) / max(1, node_count - 1)
        if node_count > 1
        else 0.0
    )
    cycle_ratio = len(cyclic) / max(1, node_count)
    global_friction = _clamp(
        0.45 * spectral_sparsity + 0.35 * edge_density + 0.20 * cycle_ratio
    )
    global_health = _clamp(1.0 - global_friction, 0.05, 1.0)

    health_by_id: dict[str, float] = {}
    for node, coord in zip(nodes, coords):
        node_id = str(node.get("id"))
        degree_norm = _clamp(total_degree[node_id] / max_degree)
        cycle_penalty = 1.0 if node_id in cyclic else 0.0
        isolated_penalty = 0.35 if total_degree[node_id] == 0 and node_count > 1 else 0.0
        sink_penalty = 0.15 if out_degree[node_id] == 0 and in_degree[node_id] > 0 else 0.0
        friction = _clamp(
            0.55 * degree_norm + 0.35 * cycle_penalty + isolated_penalty + sink_penalty
        )
        health = _clamp(1.0 - friction, 0.05, 1.0)
        state, color = _node_visual_state(health, node_id in cyclic, node.get("color"))
        health_by_id[node_id] = health
        coordinate = [round(float(value), 6) for value in coord.tolist()]

        node["position"] = coordinate
        node["spectral_coordinate"] = coordinate
        node["luminance"] = round(health, 6)
        node["structural_health"] = round(health, 6)
        node["integrity_resonance"] = round(health, 6)
        node["phaseShiftWarning"] = bool(node_id in cyclic)
        node["validationState"] = state
        node["color"] = color
        node.setdefault("type", node.get("shape", "Sphere"))
        node["spectral"] = {
            "version": SPECTRAL_TOPOLOGY_VERSION,
            "degree": round(total_degree[node_id], 6),
            "in_degree": round(in_degree[node_id], 6),
            "out_degree": round(out_degree[node_id], 6),
            "spectral_sparsity": round(spectral_sparsity, 6),
            "structural_health": round(health, 6),
            "phase_shift_warning": bool(node_id in cyclic),
            "validation_state": state,
        }

    max_weight = max((_edge_weight(edge) for edge in edges), default=1.0) or 1.0
    for idx, edge in enumerate(edges):
        source = edge["source"]
        target = edge["target"]
        edge_health = _clamp((health_by_id.get(source, global_health) + health_by_id.get(target, global_health)) / 2)
        weight_norm = _clamp(_edge_weight(edge) / max_weight)
        edge["id"] = str(edge.get("id") or f"edge_{idx}")
        edge["sourceId"] = source
        edge["targetId"] = target
        edge["luminance"] = round(edge_health, 6)
        edge["resonance"] = round(edge_health, 6)
        edge["width"] = round(0.05 + 0.2 * weight_norm, 6)
        if source in cyclic and target in cyclic:
            edge["color"] = "#FFAA00"
            edge["phaseShiftWarning"] = True
        else:
            edge["color"] = edge.get("color") or "#00E5FF"
            edge["phaseShiftWarning"] = False

    spectral_meta = {
        "version": SPECTRAL_TOPOLOGY_VERSION,
        "laplacian": "L = D - A",
        "embedding_dimensions": 3,
        "node_count": node_count,
        "edge_count": len(edges),
        "spectral_sparsity": round(spectral_sparsity, 6),
        "edge_density": round(edge_density, 6),
        "cycle_node_count": len(cyclic),
        "global_health": round(global_health, 6),
        "layout_scale": float(layout_scale),
        "layout_mode": layout_mode,
        "max_exact_eigen_nodes": MAX_EXACT_EIGEN_NODES,
    }
    meta = dict(payload.get("meta", {}) or {})
    meta.update({
        "spectral_layout": True,
        "spectral_sparsity": spectral_meta["spectral_sparsity"],
        "global_health": spectral_meta["global_health"],
    })

    augmented = dict(payload)
    augmented["nodes"] = nodes
    augmented["edges"] = edges
    augmented["meta"] = meta
    augmented["spectral_topology"] = spectral_meta
    return augmented


def _load_topology_payload(repo_root: str | Path) -> dict[str, Any] | None:
    root = Path(repo_root)
    for rel in ("Aura_Memory/live_topology_ast.json", "topology_map.json"):
        path = root / rel
        if not path.exists():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _matches_target(node: dict[str, Any], target_file: str | None, target_symbol: str | None) -> bool:
    file_name = Path(target_file).name if target_file else ""
    node_file = Path(str(node.get("file", ""))).name
    node_id = str(node.get("id", ""))
    label = str(node.get("label") or node.get("name") or "")
    file_match = not file_name or node_file == file_name or node_id.startswith(f"{file_name}::")
    symbol_match = not target_symbol or label == target_symbol or node_id.endswith(f"::{target_symbol}")
    return file_match and symbol_match


def _snapshot_node(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id"),
        "file": node.get("file"),
        "label": node.get("label") or node.get("name"),
        "position": node.get("position"),
        "luminance": node.get("luminance"),
        "validation_state": node.get("validationState"),
    }


def build_fusion_topology_snapshot(
    *,
    repo_root: str | Path,
    target_file: str | None = None,
    target_symbol: str | None = None,
    max_neighbors: int = 8,
) -> dict[str, Any] | None:
    payload = _load_topology_payload(repo_root)
    if not payload:
        return None
    augmented = augment_topology_payload(payload)
    nodes, edges = normalize_topology_payload(augmented)
    node_by_id = {str(node.get("id")): node for node in nodes}
    targets = [
        node for node in nodes
        if _matches_target(node, target_file, target_symbol)
    ]
    if not targets and target_file:
        file_name = Path(target_file).name
        targets = [node for node in nodes if Path(str(node.get("file", ""))).name == file_name]

    target_ids = {str(node.get("id")) for node in targets}
    neighbor_ids: set[str] = set()
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source in target_ids:
            neighbor_ids.add(target)
        if target in target_ids:
            neighbor_ids.add(source)

    neighbors = [
        node_by_id[node_id]
        for node_id in sorted(neighbor_ids)
        if node_id in node_by_id and node_id not in target_ids
    ][: max(0, int(max_neighbors))]
    spectral = augmented.get("spectral_topology", {})
    return {
        "version": SPECTRAL_TOPOLOGY_VERSION,
        "target_file": Path(target_file).name if target_file else None,
        "target_symbol": target_symbol,
        "targets": [_snapshot_node(node) for node in targets[: max(1, int(max_neighbors))]],
        "neighbors": [_snapshot_node(node) for node in neighbors],
        "spectral_sparsity": spectral.get("spectral_sparsity"),
        "global_health": spectral.get("global_health"),
        "cycle_node_count": spectral.get("cycle_node_count"),
    }

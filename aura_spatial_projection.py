"""Domain adapters that project canonical Aura records into spatial scene snapshots.

This module reuses the Coding Arena micro-arena selector. It does not scan the
repository, create a second topology, infer patch authority, or mutate code.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

from aura_coding_arena_3d import select_micro_arena
from aura_event_contracts import canonical_json, stable_digest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialLink,
    SpatialTruthClass,
)
from aura_spatial_scene import compile_spatial_scene

SPATIAL_PROJECTION_VERSION = "AURA_SPATIAL_PROJECTION_V1"
MAX_SPATIAL_NODES = 128
MAX_SPATIAL_LINKS = 320


def project_coding_topology_to_scene(
    topology: dict[str, Any],
    selected_node_ids: Iterable[str],
    *,
    human_instruction: str = "inspect selected code topology",
    depth: int = 1,
    scene_id: str = "coding-topology-scene",
    token_budget: int = 8192,
):
    """Project one bounded Coding Arena neighborhood into an immutable scene."""
    if not isinstance(topology, dict):
        raise ValueError("topology must be an object")
    requested = tuple(
        dict.fromkeys(
            str(item).strip()
            for item in selected_node_ids
            if str(item).strip()
        )
    )
    if not requested:
        raise ValueError("selected_node_ids must not be empty")
    known_node_ids = {
        str(item.get("id"))
        for item in topology.get("nodes", [])
        if isinstance(item, dict) and item.get("id")
    }
    missing = [item for item in requested if item not in known_node_ids]
    if missing:
        raise ValueError(f"unknown selected topology nodes: {missing}")
    micro = select_micro_arena(
        topology,
        requested,
        depth=max(0, min(2, int(depth))),
        human_instruction=human_instruction,
        token_budget=max(1, int(token_budget)),
    )
    returned_selected = tuple(micro.get("selected_node_ids", []))
    if returned_selected != requested:
        raise ValueError(
            "Coding Arena projection changed the exact requested selection"
        )
    raw_nodes = [
        item
        for item in micro.get("nodes", [])
        if isinstance(item, dict) and item.get("id")
    ]
    raw_links = [
        item for item in micro.get("links", []) if isinstance(item, dict)
    ]
    selected_set = set(returned_selected)
    raw_nodes.sort(
        key=lambda item: (
            0 if str(item.get("id")) in selected_set else 1,
            str(item.get("id") or ""),
        )
    )
    raw_nodes = raw_nodes[:MAX_SPATIAL_NODES]
    allowed_node_ids = {str(item["id"]) for item in raw_nodes}
    if not selected_set.issubset(allowed_node_ids):
        raise ValueError("selected topology nodes exceeded the spatial node cap")
    raw_links = [
        item
        for item in raw_links
        if str(item.get("source")) in allowed_node_ids
        and str(item.get("target")) in allowed_node_ids
    ][:MAX_SPATIAL_LINKS]
    if not raw_nodes:
        raise ValueError(
            "coding topology projection requires at least one grounded node"
        )

    root_frame = CoordinateFrame(
        frame_id="aura-coding-root",
        parent_frame_id=None,
        source_refs=("owner:aura_coding_arena_3d.select_micro_arena",),
        truth_class=SpatialTruthClass.DERIVED,
        projection_only=True,
    )
    scene_frame = CoordinateFrame(
        frame_id="coding-micro-arena",
        parent_frame_id=root_frame.frame_id,
        source_refs=(
            "owner:aura_coding_arena_3d.select_micro_arena",
            f"micro_arena:{stable_digest(micro, digest_size=16)}",
        ),
        truth_class=SpatialTruthClass.PRESENTATION,
        projection_only=True,
    )

    node_to_entity: dict[str, str] = {}
    entities: list[SpatialEntity] = []
    positions: list[tuple[float, float, float]] = []
    for index, node in enumerate(raw_nodes):
        node_id = str(node["id"])
        entity_id = _stable_identifier("coding-node", node_id)
        node_to_entity[node_id] = entity_id
        position = _node_position(node, index=index)
        positions.append(position)
        file_path = str(node.get("file_path") or "").strip()
        symbol = str(node.get("symbol") or "").strip()
        line_range = (
            node.get("line_range")
            if isinstance(node.get("line_range"), list)
            else []
        )
        source_refs = [f"topology:{node_id}"]
        if file_path:
            source_ref = f"source:{file_path}"
            if line_range:
                source_ref += "#L" + "-L".join(
                    str(value) for value in line_range[:2]
                )
            if symbol:
                source_ref += f"::{symbol}"
            source_refs.append(source_ref)
        metadata = {
            "domain_owner": "aura_coding_arena_3d",
            "domain_node_id": node_id,
            "node_type": str(
                node.get("node_type")
                or node.get("type")
                or node.get("kind")
                or "unknown"
            ),
            "file_path": file_path,
            "symbol": symbol,
            "line_range": line_range,
            "selected": node_id in selected_set,
            "projection_truth": (
                "CODEMAP_PROJECTED"
                if bool(
                    (node.get("metadata") or {}).get(
                        "visual_projection_only"
                    )
                )
                else "EXACT_TOPOLOGY"
            ),
            "original_color": str(node.get("color") or ""),
            "status": str(node.get("status") or "normal"),
            "tokens_est": int(node.get("tokens_est") or 0),
        }
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=str(node.get("label") or node.get("name") or node_id),
                frame_id=scene_frame.frame_id,
                source_refs=tuple(source_refs),
                position=position,
                truth_class=SpatialTruthClass.DERIVED,
                selectable=True,
                projection_only=True,
                patch_authority=False,
                metadata=metadata,
            )
        )

    links: list[SpatialLink] = []
    for index, link in enumerate(raw_links):
        source_id = str(link.get("source"))
        target_id = str(link.get("target"))
        if source_id == target_id:
            continue
        relation = _relation(
            link.get("type") or link.get("link_type") or "related"
        )
        links.append(
            SpatialLink(
                link_id=_stable_identifier(
                    "coding-link",
                    {
                        "index": index,
                        "source": source_id,
                        "target": target_id,
                        "relation": relation,
                    },
                ),
                source_entity_id=node_to_entity[source_id],
                target_entity_id=node_to_entity[target_id],
                relation=relation,
                source_refs=(
                    f"topology-edge:{source_id}->{target_id}:{relation}",
                ),
                truth_class=SpatialTruthClass.DERIVED,
                directed=True,
                projection_only=True,
                metadata={
                    "domain_owner": "aura_coding_arena_3d",
                    "domain_edge": dict(link),
                },
            )
        )

    micro_bytes = canonical_json(micro).encode("utf-8")
    bounds_min, bounds_max = _bounds(positions)
    graph_asset = SpatialAssetManifest(
        asset_id=_stable_identifier("coding-graph-asset", micro),
        asset_type=SpatialAssetType.TOPOLOGY_GRAPH,
        uri=(
            "aura://coding/micro-arena/"
            f"{stable_digest(micro, digest_size=16)}"
        ),
        media_type="application/vnd.aura.coding-topology+json",
        content_digest="sha256:" + hashlib.sha256(micro_bytes).hexdigest(),
        byte_length=len(micro_bytes),
        frame_id=scene_frame.frame_id,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        source_refs=(
            "owner:aura_coding_arena_3d.select_micro_arena",
            f"micro_arena:{stable_digest(micro, digest_size=32)}",
        ),
        truth_class=SpatialTruthClass.DERIVED,
        immutable=True,
        metadata={
            "embedded_payload": False,
            "node_count": len(raw_nodes),
            "link_count": len(links),
            "truncated": (
                len(micro.get("nodes", [])) > len(raw_nodes)
                or len(micro.get("links", [])) > len(raw_links)
            ),
        },
    )

    purpose_digest = stable_digest(
        {
            "instruction": human_instruction,
            "selected_node_ids": list(
                micro.get("selected_node_ids", [])
            ),
            "micro_digest": stable_digest(micro, digest_size=32),
        },
        digest_size=32,
    )
    return compile_spatial_scene(
        scene_id=_stable_identifier("scene", scene_id),
        purpose_digest=purpose_digest,
        root_frame_id=root_frame.frame_id,
        frames=(root_frame, scene_frame),
        assets=(graph_asset,),
        entities=entities,
        links=links,
        source_refs=(
            "owner:aura_coding_arena_3d",
            (
                "projection:aura_spatial_projection."
                "project_coding_topology_to_scene"
            ),
        ),
        renderer_hints={
            "preferred_representation": "TOPOLOGY_GRAPH",
            "mandatory_fallback": "2D_ACCESSIBLE_GRAPH",
            "renderer_is_replaceable": True,
            "selection_is_advisory": True,
            "version": SPATIAL_PROJECTION_VERSION,
        },
    )


def project_showcase_workspace_to_scene(
    workspace_packet: dict[str, Any],
    *,
    scene_id: str = "showcase-spatial-workspace",
):
    """Compatibility adapter for ``aura_showcase_spatial`` workspace packets."""
    if (
        not isinstance(workspace_packet, dict)
        or workspace_packet.get("ok") is not True
    ):
        raise ValueError(
            "workspace_packet must be a successful showcase workspace"
        )
    workspace = workspace_packet.get("workspace")
    if not isinstance(workspace, dict):
        raise ValueError("workspace_packet.workspace must be an object")
    return project_coding_topology_to_scene(
        {
            "nodes": list(workspace.get("nodes", [])),
            "links": list(workspace.get("links", [])),
            "meta": {"source": "aura_showcase_spatial"},
        },
        workspace.get("selected_node_ids", []),
        human_instruction=str(
            ((workspace_packet.get("task") or {}).get("spatial_command"))
            or workspace.get("human_instruction")
            or "inspect showcase spatial workspace"
        ),
        depth=0,
        scene_id=scene_id,
    )


def _stable_identifier(prefix: str, value: Any) -> str:
    clean = (
        re.sub(r"[^A-Za-z0-9._:/-]+", "-", str(prefix)).strip("-.")
        or "spatial"
    )
    return f"{clean}:{stable_digest(value, digest_size=12)}"


def _relation(value: Any) -> str:
    clean = re.sub(
        r"[^A-Za-z0-9._:/-]+",
        "_",
        str(value or "related"),
    ).strip("_.")
    return clean[:96] or "related"


def _node_position(
    node: dict[str, Any],
    *,
    index: int,
) -> tuple[float, float, float]:
    raw = (node.get("x"), node.get("y"), node.get("z"))
    try:
        position = tuple(float(item) for item in raw)
        if all(
            item == item and abs(item) != float("inf")
            for item in position
        ):
            return (position[0], position[1], position[2])
    except (TypeError, ValueError):
        pass
    digest = bytes.fromhex(
        stable_digest(
            {"node": node.get("id"), "index": index},
            digest_size=12,
        )
    )
    result = tuple(
        (int.from_bytes(digest[offset : offset + 4], "big") / 2**32 - 0.5)
        * 20.0
        for offset in (0, 4, 8)
    )
    return (result[0], result[1], result[2])


def _bounds(
    positions: list[tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if not positions:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    minimum = tuple(
        min(item[index] for item in positions) for index in range(3)
    )
    maximum = tuple(
        max(item[index] for item in positions) for index in range(3)
    )
    return (
        (minimum[0], minimum[1], minimum[2]),
        (maximum[0], maximum[1], maximum[2]),
    )


__all__ = [
    "MAX_SPATIAL_LINKS",
    "MAX_SPATIAL_NODES",
    "SPATIAL_PROJECTION_VERSION",
    "project_coding_topology_to_scene",
    "project_showcase_workspace_to_scene",
]

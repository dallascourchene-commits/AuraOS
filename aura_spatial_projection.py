"""Bounded projection adapters for Aura's canonical Coding Arena topology."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import hashlib
from pathlib import PurePosixPath
import math
import re
from typing import Any

from aura_coding_arena_3d import select_micro_arena
from aura_event_contracts import canonical_json, stable_digest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialLink,
    SpatialSceneSnapshot,
    SpatialTruthClass,
)
from aura_spatial_scene import compile_spatial_scene

SPATIAL_PROJECTION_VERSION = "AURA_SPATIAL_PROJECTION_V1"
MAX_SPATIAL_NODES = 128
MAX_SPATIAL_LINKS = 320
MAX_PROJECTION_BYTES = 1_048_576


def project_coding_topology_to_scene(
    topology: dict[str, Any],
    selected_node_ids: Iterable[str],
    *,
    human_instruction: str = "inspect selected code topology",
    depth: int = 1,
    scene_id: str = "coding-topology-scene",
    token_budget: int = 8192,
) -> SpatialSceneSnapshot:
    nodes_input = _array(topology, "nodes")
    _array(topology, "links")
    requested = tuple(
        dict.fromkeys(
            _selected_id(item)
            for item in selected_node_ids
            if str(item).strip()
        )
    )
    if not requested or len(requested) > MAX_SPATIAL_NODES:
        raise ValueError("selected_node_ids must contain 1-128 identifiers")
    known = {
        str(item.get("id"))
        for item in nodes_input
        if isinstance(item, Mapping) and item.get("id")
    }
    missing = [item for item in requested if item not in known]
    if missing:
        raise ValueError(f"unknown selected topology nodes: {missing}")
    instruction = _text(human_instruction, 4096)
    if not instruction:
        raise ValueError("human_instruction must not be empty")
    try:
        bounded_depth = max(0, min(2, int(depth)))
        bounded_budget = max(1, min(131_072, int(token_budget)))
    except (TypeError, ValueError) as exc:
        raise ValueError("depth and token_budget must be integers") from exc

    micro = select_micro_arena(
        topology,
        requested,
        depth=bounded_depth,
        human_instruction=instruction,
        token_budget=bounded_budget,
    )
    if not isinstance(micro, Mapping):
        raise ValueError("Coding Arena returned an invalid micro-arena")
    selected = tuple(str(item) for item in micro.get("selected_node_ids", []))
    if selected != requested:
        raise ValueError("Coding Arena projection changed the exact requested selection")

    source_nodes = _records(micro.get("nodes", []), "micro.nodes")
    nodes = [_bounded_node(item) for item in source_nodes if item.get("id")]
    selected_set = set(selected)
    nodes.sort(key=lambda item: (str(item["id"]) not in selected_set, str(item["id"])))
    nodes = nodes[:MAX_SPATIAL_NODES]
    allowed = {str(item["id"]) for item in nodes}
    if not selected_set.issubset(allowed):
        raise ValueError("selected topology nodes exceeded the spatial node cap")

    source_links = _records(micro.get("links", []), "micro.links")
    normalized_links = [_bounded_link(item) for item in source_links]
    links_raw = [
        item
        for item in normalized_links
        if str(item.get("source")) in allowed
        and str(item.get("target")) in allowed
        and str(item.get("source")) != str(item.get("target"))
    ]
    links_raw.sort(
        key=lambda item: (
            str(item.get("source")),
            str(item.get("target")),
            str(item.get("type") or item.get("link_type") or ""),
            canonical_json(item),
        )
    )
    links_raw = links_raw[:MAX_SPATIAL_LINKS]

    bounded = {
        "version": _text(micro.get("version"), 128),
        "selected_node_ids": list(selected),
        "nodes": nodes,
        "links": links_raw,
        "depth": _nonnegative_int(micro.get("depth")),
        "human_instruction": _text(
            micro.get("human_instruction") or instruction,
            4096,
        ),
        "token_cost": _nonnegative_int(micro.get("token_cost")),
    }
    encoded = canonical_json(bounded).encode("utf-8")
    if len(encoded) > MAX_PROJECTION_BYTES:
        raise ValueError("bounded micro-arena exceeds the spatial byte budget")
    bounded_digest = stable_digest(bounded, digest_size=32)

    root = CoordinateFrame(
        frame_id="aura-coding-root",
        source_refs=("owner:aura_coding_arena_3d.select_micro_arena",),
        truth_class=SpatialTruthClass.DERIVED,
    )
    frame = CoordinateFrame(
        frame_id="coding-micro-arena",
        parent_frame_id=root.frame_id,
        source_refs=(f"bounded_micro_arena:{bounded_digest}",),
        truth_class=SpatialTruthClass.PRESENTATION,
    )

    entity_ids: dict[str, str] = {}
    entities: list[SpatialEntity] = []
    positions: list[tuple[float, float, float]] = []
    for index, node in enumerate(nodes):
        node_id = str(node["id"])
        entity_id = _id("coding-node", node_id)
        entity_ids[node_id] = entity_id
        position = _position(node, index)
        positions.append(position)
        path = str(node.get("file_path") or "")
        symbol = str(node.get("symbol") or "")
        line_range = tuple(node.get("line_range", []))
        refs = [f"topology:{node_id}"]
        if path:
            anchor = f"source:{path}"
            if line_range:
                anchor += "#L" + "-L".join(map(str, line_range))
            if symbol:
                anchor += f"::{symbol}"
            refs.append(anchor)
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=str(node.get("label") or node.get("name") or node_id),
                frame_id=frame.frame_id,
                source_refs=tuple(sorted(refs)),
                position=position,
                truth_class=SpatialTruthClass.DERIVED,
                metadata={
                    "domain_owner": "aura_coding_arena_3d",
                    "domain_node_id": node_id,
                    "file_path": path,
                    "symbol": symbol,
                    "line_range": list(line_range),
                    "selected": node_id in selected_set,
                    "projection_truth": node["projection_truth"],
                    "tokens_est": node["tokens_est"],
                },
            )
        )

    links: list[SpatialLink] = []
    for index, edge in enumerate(links_raw):
        source = str(edge["source"])
        target = str(edge["target"])
        relation = _relation(edge.get("type") or edge.get("link_type"))
        links.append(
            SpatialLink(
                link_id=_id(
                    "coding-link",
                    {
                        "index": index,
                        "source": source,
                        "target": target,
                        "relation": relation,
                    },
                ),
                source_entity_id=entity_ids[source],
                target_entity_id=entity_ids[target],
                relation=relation,
                source_refs=(f"topology-edge:{source}->{target}:{relation}",),
                truth_class=SpatialTruthClass.DERIVED,
                metadata={
                    "domain_owner": "aura_coding_arena_3d",
                    "source_node_id": source,
                    "target_node_id": target,
                    "source_edge_id": edge.get("id", ""),
                },
            )
        )

    bounds_min, bounds_max = _bounds(positions)
    asset = SpatialAssetManifest(
        asset_id=_id("coding-graph-asset", bounded),
        asset_type=SpatialAssetType.TOPOLOGY_GRAPH,
        uri=f"aura://coding/micro-arena/{bounded_digest[:32]}",
        media_type="application/vnd.aura.coding-topology+json",
        content_digest="sha256:" + hashlib.sha256(encoded).hexdigest(),
        byte_length=len(encoded),
        frame_id=frame.frame_id,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        source_refs=(f"bounded_micro_arena:{bounded_digest}",),
        metadata={
            "embedded_payload": False,
            "node_count": len(nodes),
            "link_count": len(links),
            "source_node_count": len(source_nodes),
            "source_link_count": len(source_links),
            "serialized_byte_length": len(encoded),
            "serialized_byte_limit": MAX_PROJECTION_BYTES,
            "truncated": len(source_nodes) > len(nodes) or len(source_links) > len(links),
        },
    )
    return compile_spatial_scene(
        scene_id=_id("scene", scene_id),
        purpose_digest=stable_digest(
            {
                "instruction": instruction,
                "selected": list(selected),
                "bounded": bounded_digest,
            },
            digest_size=32,
        ),
        root_frame_id=root.frame_id,
        frames=(root, frame),
        assets=(asset,),
        entities=entities,
        links=links,
        source_refs=(
            "owner:aura_coding_arena_3d",
            "projection:aura_spatial_projection.project_coding_topology_to_scene",
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
) -> SpatialSceneSnapshot:
    if not isinstance(workspace_packet, dict) or workspace_packet.get("ok") is not True:
        raise ValueError("workspace_packet must be a successful showcase workspace")
    workspace = workspace_packet.get("workspace")
    if not isinstance(workspace, dict):
        raise ValueError("workspace_packet.workspace must be an object")
    return project_coding_topology_to_scene(
        {"nodes": _array(workspace, "nodes"), "links": _array(workspace, "links")},
        workspace.get("selected_node_ids", []),
        human_instruction=str(
            ((workspace_packet.get("task") or {}).get("spatial_command"))
            or workspace.get("human_instruction")
            or "inspect showcase spatial workspace"
        ),
        depth=0,
        scene_id=scene_id,
    )


def _array(value: Mapping[str, Any], key: str) -> Sequence[Any]:
    if not isinstance(value, Mapping):
        raise ValueError("topology must be an object")
    result = value.get(key, [])
    if not isinstance(result, Sequence) or isinstance(result, (str, bytes, bytearray)):
        raise ValueError(f"{key} must be an array")
    return result


def _records(value: Any, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be an array")
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _bounded_node(node: Mapping[str, Any]) -> dict[str, Any]:
    metadata = node.get("metadata") if isinstance(node.get("metadata"), Mapping) else {}
    file_path = _source_path(node.get("file_path"))
    symbol = _source_symbol(node.get("symbol")) if file_path else ""
    line_range = _line_range(node.get("line_range")) if file_path else ()
    return {
        "id": _selected_id(node.get("id")),
        "label": _text(node.get("label"), 512),
        "name": _text(node.get("name"), 512),
        "node_type": _text(
            node.get("node_type") or node.get("type") or node.get("kind"),
            128,
        ),
        "file_path": file_path,
        "symbol": symbol,
        "line_range": list(line_range),
        "x": _finite_or_none(node.get("x")),
        "y": _finite_or_none(node.get("y")),
        "z": _finite_or_none(node.get("z")),
        "tokens_est": _nonnegative_int(node.get("tokens_est")),
        "projection_truth": (
            "CODEMAP_PROJECTED"
            if metadata.get("visual_projection_only")
            else "EXACT_TOPOLOGY"
        ),
    }


def _bounded_link(link: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(link.get("id"), 256),
        "source": _selected_id(link.get("source")),
        "target": _selected_id(link.get("target")),
        "type": _text(link.get("type"), 128),
        "link_type": _text(link.get("link_type"), 128),
    }


def _selected_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 512 or any(ord(char) < 32 for char in text):
        raise ValueError("topology identifier is invalid")
    return text


def _text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if any(ord(char) < 32 for char in text):
        raise ValueError("topology text contains control characters")
    return text[:limit]


def _source_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 1024:
        return ""
    if any(ord(char) < 32 for char in text) or "\\" in text:
        return ""
    if text.startswith("/") or "//" in text or ":" in text:
        return ""
    path = PurePosixPath(text)
    if (
        any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != text
        or not re.fullmatch(r"[A-Za-z0-9._/-]+", text)
    ):
        return ""
    return text


def _source_symbol(value: Any) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,511}", text):
        return ""
    return text


def _line_range(value: Any) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    result = tuple(item for item in value[:2] if type(item) is int and item > 0)
    return () if len(result) == 2 and result[0] > result[1] else result


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, min(int(value or 0), 2_147_483_647))
    except (TypeError, ValueError):
        return 0


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _relation(value: Any) -> str:
    return (
        re.sub(r"[^A-Za-z0-9._:/-]+", "_", str(value or "related"))
        .strip("_.")[:96]
        or "related"
    )


def _id(prefix: str, value: Any) -> str:
    clean = re.sub(r"[^A-Za-z0-9._:/-]+", "-", prefix).strip("-.") or "spatial"
    return f"{clean}:{stable_digest(value, digest_size=12)}"


def _position(node: Mapping[str, Any], index: int) -> tuple[float, float, float]:
    values = tuple(node.get(axis) for axis in ("x", "y", "z"))
    if all(
        isinstance(item, (int, float)) and math.isfinite(float(item))
        for item in values
    ):
        return (float(values[0]), float(values[1]), float(values[2]))
    raw = bytes.fromhex(
        stable_digest({"node": node.get("id"), "index": index}, digest_size=12)
    )
    result = tuple(
        (int.from_bytes(raw[offset : offset + 4], "big") / 2**32 - 0.5) * 20
        for offset in (0, 4, 8)
    )
    return (result[0], result[1], result[2])


def _bounds(
    values: list[tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if not values:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    minimum = tuple(min(item[index] for item in values) for index in range(3))
    maximum = tuple(max(item[index] for item in values) for index in range(3))
    return (
        (minimum[0], minimum[1], minimum[2]),
        (maximum[0], maximum[1], maximum[2]),
    )


__all__ = [
    "MAX_PROJECTION_BYTES",
    "MAX_SPATIAL_LINKS",
    "MAX_SPATIAL_NODES",
    "SPATIAL_PROJECTION_VERSION",
    "project_coding_topology_to_scene",
    "project_showcase_workspace_to_scene",
]

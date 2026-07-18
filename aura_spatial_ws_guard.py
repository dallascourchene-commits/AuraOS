"""Fail-closed adapter from legacy AR shape requests to Aura spatial intents.

The adapter hashes and redacts the proposed function payload, binds the request to
one exact current topology shape, and produces a review-only Forge handoff packet.
It never executes the proposal, refreshes topology as though it succeeded, or
broadcasts the proposal to unrelated clients.
"""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from aura_event_contracts import sanitize_payload, stable_digest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
    SpatialTruthClass,
)
from aura_spatial_interaction import compile_hotswap_request_guard
from aura_spatial_scene import compile_spatial_scene

SPATIAL_WS_GUARD_VERSION = "AURA_SPATIAL_WS_GUARD_V1"


def compile_ar_hotswap_handoff(
    *,
    target_id: str,
    new_function: Any,
    shapes: Mapping[str, Any],
    actor_ref: str,
) -> dict[str, Any]:
    """Compile one legacy hotswap request into a non-executing review packet."""
    target = str(target_id or "").strip()
    if not target:
        raise ValueError("target_id is required")
    if not isinstance(shapes, Mapping):
        raise ValueError("shapes must be a mapping")
    if target not in shapes:
        raise KeyError(f"shape {target!r} not found")
    if new_function is None or new_function == "":
        raise ValueError("new_function is required")

    shape = shapes[target]
    metadata = _shape_mapping(shape, "metadata")
    ast_data = metadata.get("ast_data")
    if not isinstance(ast_data, Mapping):
        ast_data = {}

    source_refs = [f"topology:{target}"]
    source_anchor = _source_anchor(ast_data)
    if source_anchor:
        source_refs.append(source_anchor)

    entity_id = "ar-shape:" + stable_digest(target, digest_size=12)
    root_frame = CoordinateFrame(
        frame_id="aura-ar-review-root",
        source_refs=("owner:aura_topology_ws_bridge",),
        truth_class=SpatialTruthClass.DERIVED,
        projection_only=True,
    )
    entity = SpatialEntity(
        entity_id=entity_id,
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label=str(getattr(shape, "label", None) or ast_data.get("label") or target),
        frame_id=root_frame.frame_id,
        source_refs=tuple(source_refs),
        position=_position(shape),
        truth_class=SpatialTruthClass.DERIVED,
        selectable=True,
        projection_only=True,
        patch_authority=False,
        metadata={
            "domain_owner": "aura_topology_ws_bridge",
            "legacy_shape_id": target,
            "node_type": str(
                getattr(shape, "node_type", None)
                or ast_data.get("node_type")
                or ast_data.get("kind")
                or "unknown"
            ),
            "source_anchor_present": bool(source_anchor),
        },
    )
    proposal = sanitize_payload(new_function)
    proposal_digest = stable_digest(
        {
            "target_id": target,
            "proposal": proposal,
        },
        digest_size=32,
    )
    scene = compile_spatial_scene(
        scene_id="ar-hotswap-review:" + stable_digest(target, digest_size=12),
        purpose_digest=stable_digest(
            {
                "op": "PREPARE_REPAIR_REQUEST",
                "target_id": target,
                "proposal_digest": proposal_digest,
            },
            digest_size=32,
        ),
        root_frame_id=root_frame.frame_id,
        frames=(root_frame,),
        entities=(entity,),
        source_refs=tuple(source_refs),
        renderer_hints={
            "legacy_bridge": True,
            "requesting_client_only": True,
            "broadcast_prohibited": True,
        },
    )
    packet = compile_hotswap_request_guard(
        scene,
        target_entity_ids=(entity_id,),
        proposed_change_digest=proposal_digest,
        actor_ref=actor_ref,
    )
    return {
        **packet,
        "targetId": target,
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "proposal_digest": proposal_digest,
        "source_anchor_present": bool(source_anchor),
        "raw_proposal_retained": False,
        "requesting_client_only": True,
        "broadcast": False,
        "version": SPATIAL_WS_GUARD_VERSION,
    }


def _shape_mapping(shape: Any, attribute: str) -> dict[str, Any]:
    value = getattr(shape, attribute, None)
    if value is None and isinstance(shape, Mapping):
        value = shape.get(attribute)
    return dict(value) if isinstance(value, Mapping) else {}


def _position(shape: Any) -> tuple[float, float, float]:
    value = getattr(shape, "position", None)
    if value is None and isinstance(shape, Mapping):
        value = shape.get("position")
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return (0.0, 0.0, 0.0)
    try:
        result = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        return (0.0, 0.0, 0.0)
    if not all(item == item and abs(item) != float("inf") for item in result):
        return (0.0, 0.0, 0.0)
    return (result[0], result[1], result[2])


def _source_anchor(ast_data: Mapping[str, Any]) -> str:
    raw_path = str(
        ast_data.get("file_path")
        or ast_data.get("file")
        or ast_data.get("path")
        or ""
    ).strip().replace("\\", "/")
    if not raw_path or raw_path.startswith("/") or ".." in raw_path.split("/"):
        return ""
    if not re.fullmatch(r"[A-Za-z0-9._/\-]+", raw_path):
        return ""
    anchor = f"source:{raw_path}"
    line_range = ast_data.get("line_range")
    if isinstance(line_range, (list, tuple)) and line_range:
        values: list[int] = []
        for item in line_range[:2]:
            if type(item) is int and item > 0:
                values.append(item)
        if values:
            anchor += "#L" + "-L".join(str(item) for item in values)
    symbol = str(ast_data.get("symbol") or "").strip()
    if symbol and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", symbol):
        anchor += f"::{symbol}"
    return anchor


__all__ = [
    "SPATIAL_WS_GUARD_VERSION",
    "compile_ar_hotswap_handoff",
]

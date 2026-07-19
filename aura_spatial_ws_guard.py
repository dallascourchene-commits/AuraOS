"""Fail-closed adapter from legacy AR hotswap requests to spatial intents."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
import re
from typing import Any

from aura_event_contracts import canonical_json, sanitize_payload, stable_digest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
    SpatialTruthClass,
)
from aura_spatial_interaction import compile_hotswap_request_guard
from aura_spatial_scene import compile_spatial_scene

SPATIAL_WS_GUARD_VERSION = "AURA_SPATIAL_WS_GUARD_V1"
MAX_PROPOSAL_BYTES = 262_144
MAX_TARGET_CHARS = 512


def compile_ar_hotswap_handoff(
    *,
    target_id: str,
    new_function: Any,
    shapes: Mapping[str, Any],
    actor_ref: str,
) -> dict[str, Any]:
    """Compile one legacy hotswap request into a non-executing review packet."""
    target = str(target_id or "").strip()
    if (
        not target
        or len(target) > MAX_TARGET_CHARS
        or any(ord(char) < 32 for char in target)
    ):
        raise ValueError("target_id is invalid")
    if not isinstance(shapes, Mapping):
        raise ValueError("shapes must be a mapping")
    if target not in shapes:
        raise KeyError(f"shape {target!r} not found")
    if new_function is None or new_function == "":
        raise ValueError("new_function is required")

    proposal = sanitize_payload(new_function)
    proposal_bytes = canonical_json(proposal).encode("utf-8")
    if not proposal_bytes or len(proposal_bytes) > MAX_PROPOSAL_BYTES:
        raise ValueError(
            "new_function exceeds the bounded review payload limit"
        )

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
    label = str(
        getattr(shape, "label", None)
        or ast_data.get("label")
        or target
    ).strip()[:512]
    entity = SpatialEntity(
        entity_id=entity_id,
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label=label or entity_id,
        frame_id=root_frame.frame_id,
        source_refs=tuple(sorted(set(source_refs))),
        position=_position(shape),
        truth_class=SpatialTruthClass.DERIVED,
        selectable=True,
        projection_only=True,
        patch_authority=False,
        metadata={
            "domain_owner": "aura_topology_ws_bridge",
            "legacy_shape_digest": stable_digest(target, digest_size=12),
            "node_type": str(
                getattr(shape, "node_type", None)
                or ast_data.get("node_type")
                or ast_data.get("kind")
                or "unknown"
            )[:128],
            "source_anchor_present": bool(source_anchor),
        },
    )
    proposal_digest = stable_digest(
        {
            "target_id": target,
            "proposal": proposal,
        },
        digest_size=32,
    )
    scene = compile_spatial_scene(
        scene_id=(
            "ar-hotswap-review:" + stable_digest(target, digest_size=12)
        ),
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
        "proposal_byte_length": len(proposal_bytes),
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
    if not all(
        item == item and abs(item) != float("inf")
        for item in result
    ):
        return (0.0, 0.0, 0.0)
    return (result[0], result[1], result[2])


def _source_anchor(ast_data: Mapping[str, Any]) -> str:
    raw_path = str(
        ast_data.get("file_path")
        or ast_data.get("file")
        or ast_data.get("path")
        or ""
    ).strip()
    if (
        not raw_path
        or len(raw_path) > 1024
        or raw_path.startswith("/")
        or "\\" in raw_path
        or "//" in raw_path
        or not re.fullmatch(r"[A-Za-z0-9._/\-]+", raw_path)
    ):
        return ""
    path = PurePosixPath(raw_path)
    if (
        any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != raw_path
    ):
        return ""
    anchor = f"source:{raw_path}"
    line_range = ast_data.get("line_range")
    if isinstance(line_range, (list, tuple)) and line_range:
        values = [
            item
            for item in line_range[:2]
            if type(item) is int and item > 0
        ]
        if len(values) == 2 and values[0] > values[1]:
            values = []
        if values:
            anchor += "#L" + "-L".join(str(item) for item in values)
    symbol = str(ast_data.get("symbol") or "").strip()
    if symbol and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", symbol):
        anchor += f"::{symbol[:512]}"
    return anchor


__all__ = [
    "MAX_PROPOSAL_BYTES",
    "SPATIAL_WS_GUARD_VERSION",
    "compile_ar_hotswap_handoff",
]

"""Compatibility Spatial scene construction for the Pascal presentation organ."""
from __future__ import annotations

from collections.abc import Mapping

from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
    SpatialSceneSnapshot,
    SpatialTruthClass,
)

from aura_pascal_spatial_presentation_part1 import (
    PascalBridgeAction,
    PascalPresentationError,
    _identifier,
)
from aura_pascal_spatial_presentation_part2 import (
    AuraPascalCoordinateReceipt,
    PascalSceneArtifactManifest,
)


def build_spatial_scene(
    manifest: PascalSceneArtifactManifest,
    coordinate_receipt: AuraPascalCoordinateReceipt,
) -> SpatialSceneSnapshot:
    """Build the deterministic projection-only Aura scene for the pinned fixture."""
    entities = tuple(
        SpatialEntity(
            entity_id=item.aura_entity_id,
            entity_type=SpatialEntityType.DOMAIN_NODE,
            label=item.node_id,
            frame_id=coordinate_receipt.aura_frame_id,
            source_refs=(
                item.aura_target_ref,
                f"pascal:{manifest.artifact_id}#{manifest.artifact_digest}",
            ),
            truth_class=SpatialTruthClass.PRESENTATION,
            selectable=item.selectable,
            projection_only=True,
            patch_authority=False,
            metadata={
                "pascal_node_id": item.node_id,
                "pascal_node_kind": item.node_kind,
                "storey_id": item.storey_id,
                "presentation_only": True,
            },
        )
        for item in manifest.node_bindings
    )
    return SpatialSceneSnapshot(
        scene_id=f"pascal-scene:{manifest.artifact_id}",
        purpose_digest=manifest.artifact_digest,
        root_frame_id=coordinate_receipt.aura_frame_id,
        frames=(
            CoordinateFrame(
                frame_id=coordinate_receipt.aura_frame_id,
                source_refs=(f"coordinate-receipt:{coordinate_receipt.receipt_id}",),
                truth_class=SpatialTruthClass.DERIVED,
                projection_only=True,
            ),
        ),
        assets=(),
        entities=entities,
        source_refs=(
            f"pascal:{manifest.repository}@{manifest.commit}",
            f"pascal-artifact:{manifest.artifact_id}#{manifest.artifact_digest}",
            f"coordinate-receipt:{coordinate_receipt.receipt_id}",
        ),
        renderer_hints={
            "preferred": ["WEBGPU", "WEBGL2", "ACCESSIBLE_2D"],
            "network_allowed": False,
            "presentation_only": True,
        },
    )


def target_entity_ids(
    manifest: PascalSceneArtifactManifest,
    action: PascalBridgeAction,
    payload: Mapping[str, object],
) -> tuple[str, ...]:
    """Resolve one admitted Aura entity without turning presentation IDs into authority."""
    node_id = str(payload.get("node_id") or payload.get("selected_node_id") or "").strip()
    storey_id = str(payload.get("storey_id") or "").strip()
    if node_id:
        binding = manifest.binding_for_node(node_id)
        if (
            not binding.selectable
            and action
            in {PascalBridgeAction.SET_SELECTION, PascalBridgeAction.SELECTION_CHANGED}
        ):
            raise PascalPresentationError("selected Pascal node is not selectable")
        return (binding.aura_entity_id,)
    if storey_id:
        storey = _identifier(storey_id, "payload.storey_id")
        if storey not in manifest.storey_ids:
            raise PascalPresentationError(
                "requested storey is not admitted by the artifact manifest"
            )
        return (manifest.first_selectable_on_storey(storey).aura_entity_id,)
    return (manifest.root_binding().aura_entity_id,)


__all__ = ["build_spatial_scene", "target_entity_ids"]

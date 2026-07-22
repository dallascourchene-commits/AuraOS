"""Project an admitted Construction demo asset pack into canonical Spatial records.

The returned records are immutable presentation inputs.  They do not own project
state, source geometry truth, survey coordinates, renderer decisions, or physical
authority.
"""
from __future__ import annotations

from typing import Iterable

from aura_construction_demo_contracts import (
    ConstructionDemoAssetBinding,
    ConstructionDemoAssetPack,
    ConstructionDemoRepresentation,
)
from aura_event_contracts import stable_digest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialLink,
    SpatialTruthClass,
)

CONSTRUCTION_DEMO_SPATIAL_ASSETS_VERSION = "AURA_CONSTRUCTION_DEMO_SPATIAL_ASSETS_V1"
CONSTRUCTION_SITE_ROOT_FRAME_ID = "construction-site-root"

_REPRESENTATION_TYPES = {
    ConstructionDemoRepresentation.MESH_GLB.value: SpatialAssetType.MESH,
    ConstructionDemoRepresentation.FLOOR_PLAN_SVG.value: SpatialAssetType.PLANE,
    ConstructionDemoRepresentation.GAUSSIAN_PLY.value: SpatialAssetType.POINT_CLOUD,
    ConstructionDemoRepresentation.GAUSSIAN_SPZ.value: SpatialAssetType.GAUSSIAN_SPLAT,
    ConstructionDemoRepresentation.IFC_SOURCE.value: SpatialAssetType.MESH,
}


def _id(prefix: str, value: object) -> str:
    return f"{prefix}-{stable_digest(value, digest_size=16)}"


def _spatial_asset(
    binding: ConstructionDemoAssetBinding,
    *,
    frame_id: str,
) -> SpatialAssetManifest:
    if type(binding) is not ConstructionDemoAssetBinding:
        raise ValueError("binding must be an exact ConstructionDemoAssetBinding")
    asset_type = _REPRESENTATION_TYPES.get(str(binding.representation))
    if asset_type is None:
        raise ValueError(f"unsupported Construction demo representation: {binding.representation}")
    return SpatialAssetManifest(
        asset_id=binding.asset_id,
        asset_type=asset_type,
        uri=binding.uri,
        media_type=binding.media_type,
        content_digest=f"sha256:{binding.content_digest}",
        byte_length=binding.byte_length,
        frame_id=frame_id,
        bounds_min=binding.bounds_min,
        bounds_max=binding.bounds_max,
        source_refs=tuple(
            sorted(
                {
                    *binding.source_refs,
                    f"construction-demo-asset:{binding.asset_id}",
                    f"construction-representation:{binding.representation_digest}",
                }
            )
        ),
        truth_class=SpatialTruthClass.PRESENTATION,
        metadata={
            "construction_asset_id": binding.asset_id,
            "construction_storey_id": binding.storey_id,
            "representation": str(binding.representation),
            "representation_digest": binding.representation_digest,
            "import_receipt_digest": binding.import_receipt_digest,
            "coordinate_system": binding.coordinate_system,
            "unit_scale_meters": binding.unit_scale_meters,
            "survey_authority": False,
            "person_level_data_included": False,
            "projection_only": True,
        },
    )


def project_construction_demo_asset_foundation(
    asset_pack: ConstructionDemoAssetPack,
) -> tuple[
    tuple[CoordinateFrame, ...],
    tuple[SpatialAssetManifest, ...],
    tuple[SpatialEntity, ...],
    tuple[SpatialLink, ...],
]:
    """Return canonical frames, assets, entities, and containment links."""
    if type(asset_pack) is not ConstructionDemoAssetPack:
        raise ValueError("asset_pack must be an exact ConstructionDemoAssetPack")
    asset_pack.__post_init__()
    storeys = tuple(sorted(asset_pack.storeys, key=lambda item: (item.ordinal, item.storey_id)))
    storey_by_id = {item.storey_id: item for item in storeys}

    root = CoordinateFrame(
        frame_id=CONSTRUCTION_SITE_ROOT_FRAME_ID,
        source_refs=(
            f"construction-demo-source:{asset_pack.source_manifest.source_manifest_digest}",
        ),
        truth_class=SpatialTruthClass.DERIVED,
    )
    building_frame = CoordinateFrame(
        frame_id=asset_pack.building_frame_id,
        parent_frame_id=root.frame_id,
        source_refs=(
            f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
            f"construction-hierarchy:{asset_pack.hierarchy_digest}",
        ),
        truth_class=SpatialTruthClass.PRESENTATION,
    )
    storey_frames = tuple(
        CoordinateFrame(
            frame_id=storey.frame_id,
            parent_frame_id=building_frame.frame_id,
            translation=(0.0, float(storey.elevation_m), 0.0),
            source_refs=(
                *storey.source_refs,
                f"construction-storey:{storey.storey_digest}",
            ),
            truth_class=SpatialTruthClass.PRESENTATION,
        )
        for storey in storeys
    )
    frames = (root, building_frame, *storey_frames)

    spatial_assets = tuple(
        sorted(
            (
                _spatial_asset(binding, frame_id=storey_by_id[binding.storey_id].frame_id)
                for binding in asset_pack.assets
            ),
            key=lambda item: item.asset_id,
        )
    )
    assets_by_storey: dict[str, list[str]] = {item.storey_id: [] for item in storeys}
    for binding in asset_pack.assets:
        assets_by_storey[binding.storey_id].append(binding.asset_id)

    building_entity_id = _id("construction-building", asset_pack.building_id)
    building_entity = SpatialEntity(
        entity_id=building_entity_id,
        entity_type=SpatialEntityType.REGION,
        label="Synthetic Construction demo building",
        frame_id=building_frame.frame_id,
        source_refs=(
            f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
        ),
        truth_class=SpatialTruthClass.PRESENTATION,
        metadata={
            "building_ref": stable_digest(asset_pack.building_id, digest_size=16),
            "asset_pack_digest": asset_pack.asset_pack_digest,
            "storey_count": len(storeys),
            "fictional_source": True,
            "survey_authority": False,
            "person_level_data_included": False,
            "projection_only": True,
        },
    )
    storey_entities = tuple(
        SpatialEntity(
            entity_id=_id("construction-storey", storey.storey_id),
            entity_type=SpatialEntityType.ASSET_INSTANCE,
            label=storey.name,
            frame_id=storey.frame_id,
            asset_ids=tuple(sorted(assets_by_storey[storey.storey_id])),
            source_refs=(
                *storey.source_refs,
                f"construction-storey:{storey.storey_digest}",
            ),
            truth_class=SpatialTruthClass.PRESENTATION,
            metadata={
                "storey_id": storey.storey_id,
                "storey_digest": storey.storey_digest,
                "ordinal": storey.ordinal,
                "source_elevation_m": storey.elevation_m,
                "survey_authority": False,
                "status_overlay_separate": True,
                "source_geometry_mutated": False,
                "projection_only": True,
            },
        )
        for storey in storeys
    )
    containment_links = tuple(
        SpatialLink(
            link_id=_id(
                "construction-link",
                {
                    "relation": "CONTAINS_STOREY",
                    "building": building_entity_id,
                    "storey": entity.entity_id,
                },
            ),
            source_entity_id=building_entity_id,
            target_entity_id=entity.entity_id,
            relation="CONTAINS_STOREY",
            source_refs=(
                f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
            ),
            truth_class=SpatialTruthClass.DERIVED,
            metadata={"projection_only": True},
        )
        for entity in storey_entities
    )
    return (
        tuple(frames),
        spatial_assets,
        (building_entity, *storey_entities),
        containment_links,
    )


__all__ = [
    "CONSTRUCTION_DEMO_SPATIAL_ASSETS_VERSION",
    "CONSTRUCTION_SITE_ROOT_FRAME_ID",
    "project_construction_demo_asset_foundation",
]

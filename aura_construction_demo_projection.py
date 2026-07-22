"""G5 Construction Spatial Projection V2 scene composition."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from aura_construction_demo_fixture import ConstructionDemoProjectFixture
from aura_construction_demo_runtime import build_construction_demo_runtime_packet
from aura_construction_demo_spatial_assets import (
    CONSTRUCTION_SITE_ROOT_FRAME_ID,
    project_construction_demo_asset_foundation,
)
from aura_construction_demo_spatial_overlays import project_construction_demo_overlays
from aura_event_contracts import stable_digest
from aura_spatial_arena import SpatialPrivacyClass
from aura_spatial_construction import project_construction_state_to_scene
from aura_spatial_contracts import SpatialLink, SpatialSceneSnapshot, SpatialTruthClass
from aura_spatial_scene import compile_spatial_scene, verify_spatial_scene

CONSTRUCTION_DEMO_PROJECTION_VERSION = "AURA_CONSTRUCTION_DEMO_PROJECTION_V2"


def _id(prefix: str, value: object) -> str:
    return f"{prefix}-{stable_digest(value, digest_size=16)}"


def project_construction_demo_to_scene(
    fixture: ConstructionDemoProjectFixture,
    runtime_packet: Mapping[str, Any] | None = None,
    *,
    privacy_class: SpatialPrivacyClass | str = SpatialPrivacyClass.PROJECT,
) -> SpatialSceneSnapshot:
    """Compose the canonical Construction projector, admitted assets, and overlays."""
    if type(fixture) is not ConstructionDemoProjectFixture:
        raise ValueError("fixture must be an exact ConstructionDemoProjectFixture")
    fixture.__post_init__()
    privacy = (
        privacy_class
        if isinstance(privacy_class, SpatialPrivacyClass)
        else SpatialPrivacyClass(str(privacy_class))
    )
    if privacy in {SpatialPrivacyClass.RESTRICTED, SpatialPrivacyClass.SENSITIVE}:
        raise ValueError(
            "restricted or sensitive Construction scenes cannot expose demo geometry"
        )
    packet = (
        build_construction_demo_runtime_packet(fixture)
        if runtime_packet is None
        else dict(runtime_packet)
    )
    evaluation = packet.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise ValueError("runtime_packet evaluation must be a mapping")
    purpose_digest = stable_digest(
        {
            "version": CONSTRUCTION_DEMO_PROJECTION_VERSION,
            "fixture_digest": fixture.fixture_digest,
            "asset_pack_digest": fixture.asset_pack.asset_pack_digest,
            "state_digest": fixture.state.state_digest,
            "evaluation_digest": evaluation.get("evaluation_digest"),
            "privacy_class": privacy.value,
        },
        digest_size=32,
    )

    canonical_construction_scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest=purpose_digest,
        privacy_class=privacy,
        scene_id="construction-demo-runtime-summary",
    )
    frames, assets, asset_entities, asset_links = project_construction_demo_asset_foundation(
        fixture.asset_pack
    )
    overlay_entities, overlay_links = project_construction_demo_overlays(fixture, packet)

    canonical_frames = tuple(
        replace(frame, parent_frame_id=CONSTRUCTION_SITE_ROOT_FRAME_ID)
        if frame.frame_id == canonical_construction_scene.root_frame_id
        else frame
        for frame in canonical_construction_scene.frames
    )
    canonical_project_entity = next(
        (
            entity
            for entity in canonical_construction_scene.entities
            if entity.to_dict().get("metadata", {}).get("domain_owner")
            == "aura_construction_state"
        ),
        None,
    )
    building_entity = next(
        (
            entity
            for entity in asset_entities
            if entity.to_dict().get("metadata", {}).get("asset_pack_digest")
            == fixture.asset_pack.asset_pack_digest
        ),
        None,
    )
    if canonical_project_entity is None or building_entity is None:
        raise ValueError("Construction scene composition lacks its canonical project anchors")
    bridge = SpatialLink(
        link_id=_id(
            "construction-link",
            {
                "building": building_entity.entity_id,
                "runtime_summary": canonical_project_entity.entity_id,
                "relation": "HAS_RUNTIME_SUMMARY",
            },
        ),
        source_entity_id=building_entity.entity_id,
        target_entity_id=canonical_project_entity.entity_id,
        relation="HAS_RUNTIME_SUMMARY",
        source_refs=(
            f"construction-state:{fixture.state.state_digest}",
            f"construction-demo-fixture:{fixture.fixture_digest}",
        ),
        truth_class=SpatialTruthClass.DERIVED,
        metadata={
            "raw_event_payloads_included": False,
            "person_level_data_included": False,
            "projection_only": True,
        },
    )

    scene = compile_spatial_scene(
        scene_id=_id("construction-demo-scene", fixture.fixture_digest),
        purpose_digest=purpose_digest,
        root_frame_id=CONSTRUCTION_SITE_ROOT_FRAME_ID,
        frames=(*frames, *canonical_frames),
        assets=(*assets, *canonical_construction_scene.assets),
        entities=(
            *asset_entities,
            *overlay_entities,
            *canonical_construction_scene.entities,
        ),
        links=(
            *asset_links,
            *overlay_links,
            *canonical_construction_scene.links,
            bridge,
        ),
        source_refs=(
            "owner:aura_construction_state.ConstructionProjectState",
            "owner:aura_construction_adapter.ConstructionArenaAdapter",
            "projection:aura_spatial_construction.project_construction_state_to_scene",
            "projection:aura_construction_demo_projection.project_construction_demo_to_scene",
            f"construction-state:{fixture.state.state_digest}",
            f"construction-demo-fixture:{fixture.fixture_digest}",
            f"construction-demo-asset-pack:{fixture.asset_pack.asset_pack_digest}",
            f"construction-evaluation:{evaluation.get('evaluation_digest')}",
        ),
        renderer_hints={
            "version": CONSTRUCTION_DEMO_PROJECTION_VERSION,
            "preferred_representation": "HYBRID_MESH_GAUSSIAN",
            "mandatory_fallback": "ACCESSIBLE_2D",
            "supported_modes": ["MESH_ONLY", "SPLATS_ONLY", "HYBRID"],
            "floor_isolation": True,
            "exploded_view": True,
            "floor_plan_overlay": True,
            "work_status_overlay": True,
            "timeline_projection": True,
            "budget_projection": True,
            "synthetic_rule_projection": True,
            "renderer_is_replaceable": True,
            "geometry_is_non_survey": True,
            "runtime_external_fetch": False,
            "projection_only": True,
        },
    )
    report = verify_spatial_scene(scene)
    if not report.ok:
        raise ValueError("Construction demo scene failed canonical Spatial verification")
    return scene


__all__ = [
    "CONSTRUCTION_DEMO_PROJECTION_VERSION",
    "project_construction_demo_to_scene",
]

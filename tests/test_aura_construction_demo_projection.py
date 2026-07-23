from __future__ import annotations

from typing import Any

import pytest

from aura_construction_demo_contracts import (
    CC_BY_4_0,
    CC_BY_4_0_URL,
    TU_WIEN_DOI,
    TU_WIEN_PUBLISHED_MD5,
    TU_WIEN_SOURCE_FILENAME,
    TU_WIEN_SOURCE_ID,
    ConstructionDemoAssetBinding,
    ConstructionDemoAssetPack,
    ConstructionDemoRepresentation,
    ConstructionDemoSourceManifest,
    ConstructionDemoStorey,
    ConstructionDemoTruthClass,
)
from aura_construction_demo_fixture_builder import (
    build_construction_demo_project_fixture,
    build_construction_demo_runtime_packet,
)
from aura_construction_demo_projection import project_construction_demo_to_scene
from aura_event_contracts import stable_digest
from aura_spatial_arena import SpatialPrivacyClass
from aura_spatial_contracts import SpatialAssetType, SpatialEntityType
from aura_spatial_scene import validate_spatial_scene_payload


def _pack() -> ConstructionDemoAssetPack:
    manifest = ConstructionDemoSourceManifest(
        source_id=TU_WIEN_SOURCE_ID,
        title="Custom Test Model for Escape Route Analysis in IFC format",
        creators=("Fischer", "Pfeiffer", "Schranz", "Urban", "Zdanowicz"),
        publisher="TU Wien Research Data",
        doi=TU_WIEN_DOI,
        source_filename=TU_WIEN_SOURCE_FILENAME,
        source_byte_length=7_100_000,
        published_md5=TU_WIEN_PUBLISHED_MD5,
        observed_sha256="a" * 64,
        license_id=CC_BY_4_0,
        license_url=CC_BY_4_0_URL,
        downloaded_at="2026-07-22T10:00:00Z",
    )
    storeys = []
    assets = []
    media_types = {
        ConstructionDemoRepresentation.MESH_GLB: "model/gltf-binary",
        ConstructionDemoRepresentation.FLOOR_PLAN_SVG: "image/svg+xml",
        ConstructionDemoRepresentation.GAUSSIAN_SPZ: "application/vnd.aura.spz",
    }
    suffixes = {
        ConstructionDemoRepresentation.MESH_GLB: "glb",
        ConstructionDemoRepresentation.FLOOR_PLAN_SVG: "svg",
        ConstructionDemoRepresentation.GAUSSIAN_SPZ: "spz",
    }
    for ordinal in range(5):
        storey_id = f"storey-{ordinal:02d}"
        storeys.append(
            ConstructionDemoStorey(
                storey_id=storey_id,
                ifc_global_id=f"ifc-global-id-{ordinal:02d}",
                name=f"Storey {ordinal:02d}",
                elevation_m=float(ordinal * 4),
                ordinal=ordinal,
                source_ifc_ref=f"demo_assets/construction_tuwien/generated/storeys/{storey_id}/{storey_id}.ifc",
                mesh_asset_id=f"asset-{storey_id}-glb",
                floor_plan_asset_id=f"asset-{storey_id}-svg",
                gaussian_asset_id=f"asset-{storey_id}-spz",
                bounds_min=(-10.0, 0.0, -10.0),
                bounds_max=(10.0, 4.0, 10.0),
                frame_id=f"{storey_id}-frame",
                source_refs=(f"ifc:storey:{storey_id}",),
            )
        )
        for representation in (
            ConstructionDemoRepresentation.MESH_GLB,
            ConstructionDemoRepresentation.FLOOR_PLAN_SVG,
            ConstructionDemoRepresentation.GAUSSIAN_SPZ,
        ):
            suffix = suffixes[representation]
            assets.append(
                ConstructionDemoAssetBinding(
                    asset_id=f"asset-{storey_id}-{suffix}",
                    storey_id=storey_id,
                    representation=representation,
                    uri=f"demo_assets/construction_tuwien/generated/storeys/{storey_id}/{storey_id}.{suffix}",
                    media_type=media_types[representation],
                    content_digest=stable_digest({"storey": storey_id, "suffix": suffix}, digest_size=32),
                    byte_length=4096,
                    coordinate_system="RIGHT_HANDED_Y_UP_METERS",
                    unit_scale_meters=1.0,
                    bounds_min=(-10.0, 0.0, -10.0),
                    bounds_max=(10.0, 4.0, 10.0),
                    source_refs=(f"ifc:storey:{storey_id}",),
                    import_receipt_digest=stable_digest({"import": storey_id, "suffix": suffix}, digest_size=32),
                    representation_digest=stable_digest(
                        {"representation": storey_id, "suffix": suffix}, digest_size=32
                    ),
                    truth_class=ConstructionDemoTruthClass.DERIVED_PRESENTATION,
                )
            )
    return ConstructionDemoAssetPack(
        source_manifest=manifest,
        building_id="construction-demo-building",
        building_frame_id="construction-demo-building-frame",
        storeys=tuple(storeys),
        assets=tuple(sorted(assets, key=lambda item: item.asset_id)),
        element_index_digest="e" * 32,
        hierarchy_digest="f" * 32,
        generator_version="construction-demo-generator-v1",
        generator_request_digest="1" * 32,
    )


def _scene(privacy: SpatialPrivacyClass = SpatialPrivacyClass.PROJECT):
    fixture = build_construction_demo_project_fixture(_pack())
    packet = build_construction_demo_runtime_packet(fixture)
    return fixture, project_construction_demo_to_scene(
        fixture,
        packet,
        purpose_digest="9" * 64,
        privacy_class=privacy,
    )


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def test_g5_projection_is_deterministic_canonical_and_storey_complete() -> None:
    fixture, first = _scene()
    _fixture, second = _scene()

    assert first.scene_digest == second.scene_digest
    assert validate_spatial_scene_payload(first.to_dict()) == first
    frame_ids = {item.frame_id for item in first.frames}
    assert {item.frame_id for item in fixture.asset_pack.storeys}.issubset(frame_ids)
    assert len(first.frames) == len(fixture.asset_pack.storeys) + 2

    assets_by_id = {item.asset_id: item for item in first.assets}
    entities = [item for item in first.entities if item.entity_type is SpatialEntityType.ASSET_INSTANCE]
    assert len(entities) == len(fixture.asset_pack.storeys)
    for storey in fixture.asset_pack.storeys:
        entity = next(item for item in entities if item.frame_id == storey.frame_id)
        assert set(entity.asset_ids) == {
            storey.mesh_asset_id,
            storey.floor_plan_asset_id,
            storey.gaussian_asset_id,
        }
        assert assets_by_id[storey.mesh_asset_id].asset_type is SpatialAssetType.MESH
        assert assets_by_id[storey.floor_plan_asset_id].asset_type is SpatialAssetType.PLANE
        gaussian_asset = assets_by_id[storey.gaussian_asset_id]
        assert gaussian_asset.asset_type is SpatialAssetType.GAUSSIAN_SPLAT
        gaussian_metadata = gaussian_asset.to_dict()["metadata"]
        assert gaussian_metadata["representation_digest_version"] == "AURA_GAUSSIAN_REPRESENTATION_V1"
        assert gaussian_metadata["representation_bytes_per_splat"] == 60
        assert gaussian_metadata["gaussian_sh_degree"] == 0
        assert gaussian_metadata["gaussian_color_space"] == "SPZ_INTERNAL_WIDE_RGB"


def test_g5_projection_contains_required_domain_links_and_separate_status_overlays() -> None:
    fixture, scene = _scene()
    relations = {item.relation for item in scene.links}
    assert {
        "CONTAINS_STOREY",
        "CONTAINS_ZONE",
        "HAS_WORK_PACKAGE",
        "LOCATED_ON_STOREY",
        "DEPENDS_ON",
        "BLOCKED_BY",
        "COMPLETED_IN",
        "VISITED_BY_TRADE",
        "REQUIRES_EVIDENCE",
        "REQUIRES_INSPECTION",
        "REQUIRES_PROFESSIONAL_RELEASE",
        "REQUIRES_SYNTHETIC_RULE",
        "USES_CRANE_WINDOW",
        "AFFECTS_SCHEDULE",
        "AFFECTS_BUDGET",
        "HAS_PROPOSAL_OPTION",
        "HAS_BLOCKED_PROPOSAL",
    }.issubset(relations)

    package_entities = [
        item.to_dict()
        for item in scene.entities
        if item.entity_type is SpatialEntityType.DOMAIN_NODE and "status_overlay" in item.to_dict()["metadata"]
    ]
    assert package_entities
    assert {item["metadata"]["status_overlay"] for item in package_entities}.issuperset(
        {item.status for item in fixture.work_packages}
    )
    for storey_entity in (
        item.to_dict() for item in scene.entities if item.entity_type is SpatialEntityType.ASSET_INSTANCE
    ):
        assert "status_overlay" not in storey_entity["metadata"]
        assert storey_entity["metadata"]["source_transform"] != {}
        assert storey_entity["metadata"]["presentation_transform"] != {}


def test_g5_projection_excludes_raw_people_events_consent_and_sensor_payloads() -> None:
    fixture, scene = _scene()
    payload = scene.to_dict()
    serialized_tokens = {str(item).lower() for item in _walk(payload)}
    for forbidden in (
        "actor_id",
        "claimant_id",
        "consent_refs",
        "raw_event",
        "sensor_value",
        "worker_id",
        "exact_worker_location",
    ):
        assert forbidden not in serialized_tokens
    assert scene.execution_authority is False
    assert scene.vsa_patch_authority is False
    assert f"construction-state:{fixture.state.state_digest}" in scene.source_refs
    assert fixture.state.state_digest == build_construction_demo_project_fixture(_pack()).state.state_digest


def test_g5_public_projection_hashes_domain_identifiers() -> None:
    fixture, scene = _scene(SpatialPrivacyClass.PUBLIC)
    payload = scene.to_dict()
    labels = " ".join(item["label"] for item in payload["entities"])
    assert fixture.state.project_id not in labels
    assert fixture.focus_scope.zone_id not in labels
    assert fixture.focus_scope.work_package_id not in labels

    all_source_refs = []
    for frame in payload.get("frames", []):
        all_source_refs.extend(frame.get("source_refs", []))
    for asset in payload.get("assets", []):
        all_source_refs.extend(asset.get("source_refs", []))
    for entity in payload.get("entities", []):
        all_source_refs.extend(entity.get("source_refs", []))
    for link in payload.get("links", []):
        all_source_refs.extend(link.get("source_refs", []))
    all_source_refs.extend(payload.get("source_refs", []))

    assert payload["source_refs"]
    assert all(len(ref) == 16 and set(ref) <= set("0123456789abcdef") for ref in payload["source_refs"])

    source_refs_str = " ".join(all_source_refs)
    assert fixture.state.project_id not in source_refs_str
    assert fixture.focus_scope.zone_id not in source_refs_str
    assert fixture.focus_scope.work_package_id not in source_refs_str
    for storey in fixture.asset_pack.storeys:
        assert storey.storey_id not in source_refs_str
        assert storey.ifc_global_id not in source_refs_str


def test_g5_package_owned_overlays_use_package_storey_frames() -> None:
    fixture, scene = _scene()
    entities = scene.to_dict()["entities"]
    storey_frames = {item.storey_id: item.frame_id for item in fixture.asset_pack.storeys}
    package_frames = {item.work_package_id: storey_frames[item.storey_id] for item in fixture.work_packages}

    for activity in fixture.work_history:
        matches = [item for item in entities if item["metadata"].get("activity_ref") == activity.activity_id]
        assert len(matches) == 1
        assert matches[0]["frame_id"] == package_frames[activity.work_package_id]
    for budget in fixture.budget_lines:
        matches = [item for item in entities if item["metadata"].get("budget_line_ref") == budget.budget_line_id]
        assert len(matches) == 1
        assert matches[0]["frame_id"] == package_frames[budget.work_package_id]
    for inspection in fixture.inspections:
        matches = [item for item in entities if item["metadata"].get("inspection_ref") == inspection.inspection_id]
        assert len(matches) == 1
        assert matches[0]["frame_id"] == package_frames[inspection.work_package_id]
    for hazard in fixture.hazards:
        matches = [item for item in entities if item["metadata"].get("hazard_ref") == hazard.hazard_id]
        assert len(matches) == 1
        assert matches[0]["frame_id"] == package_frames[hazard.work_package_id]
    for rule in fixture.rules:
        actual_frames = sorted(
            item["frame_id"] for item in entities if item["metadata"].get("rule_ref") == rule.rule_id
        )
        expected_frames = sorted(package_frames[package_id] for package_id in rule.applies_to_work_package_ids)
        assert actual_frames == expected_frames


def test_g5_rejects_restricted_or_sensitive_geometry_projection() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    packet = build_construction_demo_runtime_packet(fixture)
    for privacy in (SpatialPrivacyClass.RESTRICTED, SpatialPrivacyClass.SENSITIVE):
        with pytest.raises(ValueError, match="cannot expose geometry"):
            project_construction_demo_to_scene(
                fixture,
                packet,
                purpose_digest="9" * 64,
                privacy_class=privacy,
            )

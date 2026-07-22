from __future__ import annotations

from dataclasses import replace

import pytest

from aura_construction_demo_contracts import (
    CC_BY_4_0,
    CC_BY_4_0_URL,
    ConstructionDemoAssetBinding,
    ConstructionDemoAssetPack,
    ConstructionDemoRepresentation,
    ConstructionDemoSourceManifest,
    ConstructionDemoStorey,
    ConstructionDemoTruthClass,
    TU_WIEN_DOI,
    TU_WIEN_PUBLISHED_MD5,
    TU_WIEN_SOURCE_FILENAME,
    TU_WIEN_SOURCE_ID,
)
from aura_construction_demo_fixture import (
    CONSTRUCTION_DEMO_REQUIRED_TRADES,
    CONSTRUCTION_DEMO_WORK_STATES,
)
from aura_construction_demo_fixture_builder import build_construction_demo_project_fixture
from aura_construction_demo_projection import project_construction_demo_to_scene
from aura_construction_demo_runtime import build_construction_demo_runtime_packet
from aura_spatial_arena import SpatialPrivacyClass
from aura_spatial_scene import verify_spatial_scene


def _manifest() -> ConstructionDemoSourceManifest:
    return ConstructionDemoSourceManifest(
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


def _asset(storey_id: str, suffix: str, representation: ConstructionDemoRepresentation) -> ConstructionDemoAssetBinding:
    media_types = {
        ConstructionDemoRepresentation.MESH_GLB: "model/gltf-binary",
        ConstructionDemoRepresentation.FLOOR_PLAN_SVG: "image/svg+xml",
        ConstructionDemoRepresentation.GAUSSIAN_SPZ: "application/vnd.aura.spz",
    }
    digest_chars = {
        "glb": ("a", "b"),
        "spz": ("c", "d"),
        "svg": ("e", "f"),
    }
    content_char, receipt_char = digest_chars[suffix]
    return ConstructionDemoAssetBinding(
        asset_id=f"asset-{storey_id}-{suffix}",
        storey_id=storey_id,
        representation=representation,
        uri=f"demo_assets/construction_tuwien/generated/storeys/{storey_id}/{storey_id}.{suffix}",
        media_type=media_types[representation],
        content_digest=content_char * 64,
        byte_length=4096,
        coordinate_system="RIGHT_HANDED_Y_UP_METERS",
        unit_scale_meters=1.0,
        bounds_min=(-10.0, 0.0, -10.0),
        bounds_max=(10.0, 4.0, 10.0),
        source_refs=(f"ifc:storey:{storey_id}",),
        import_receipt_digest=receipt_char * 32,
        representation_digest=receipt_char * 32,
        truth_class=ConstructionDemoTruthClass.DERIVED_PRESENTATION,
    )


def _pack(storey_count: int = 5) -> ConstructionDemoAssetPack:
    storeys = []
    assets = []
    for ordinal in range(storey_count):
        storey_id = f"storey-{ordinal + 1:02d}"
        storeys.append(
            ConstructionDemoStorey(
                storey_id=storey_id,
                ifc_global_id=f"ifc-global-id-{ordinal + 1:02d}",
                name=f"Storey {ordinal + 1}",
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
        assets.extend(
            (
                _asset(storey_id, "glb", ConstructionDemoRepresentation.MESH_GLB),
                _asset(storey_id, "spz", ConstructionDemoRepresentation.GAUSSIAN_SPZ),
                _asset(storey_id, "svg", ConstructionDemoRepresentation.FLOOR_PLAN_SVG),
            )
        )
    return ConstructionDemoAssetPack(
        source_manifest=_manifest(),
        building_id="construction-demo-building",
        building_frame_id="construction-demo-building-frame",
        storeys=tuple(storeys),
        assets=tuple(sorted(assets, key=lambda item: item.asset_id)),
        element_index_digest="e" * 32,
        hierarchy_digest="f" * 32,
        generator_version="construction-demo-generator-v1",
        generator_request_digest="1" * 32,
    )


def _metadata_keys(value: object) -> set[str]:
    keys: set[str] = set()
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            keys.update(str(key) for key in current)
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return keys


def test_g4_fixture_is_deterministic_storey_bound_and_canonical() -> None:
    pack = _pack()
    first = build_construction_demo_project_fixture(pack)
    second = build_construction_demo_project_fixture(pack)

    assert first.fixture_digest == second.fixture_digest
    assert first.state == second.state
    assert first.state.project_id == pack.building_id
    assert {item.trade_id for item in first.trades} == CONSTRUCTION_DEMO_REQUIRED_TRADES
    assert {item.status for item in first.work_packages} == CONSTRUCTION_DEMO_WORK_STATES
    assert {item.scope.zone_id for item in first.work_packages}.issubset(
        {item.storey_id for item in pack.storeys}
    )
    assert first.blocked_package_id in {item.package_id for item in first.work_packages}
    assert first.recommended_candidate_id in {item.candidate_id for item in first.candidates}
    assert all(item.truth_class == "SYNTHETIC_DEMO_RULE" for item in first.rules)
    assert all(item.legal_authority is False for item in first.rules)
    assert first.project_state_owner is False
    assert first.financial_truth_owner is False
    assert first.renderer_authority is False
    assert first.production_mutation is False
    assert first.human_review_required is True


def test_g4_runtime_packet_preserves_hard_blockers_and_authority() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    packet = build_construction_demo_runtime_packet(fixture)
    evaluation = packet["evaluation"]
    assessments = {
        item["candidate_id"]: item for item in evaluation["assessments"]
    }
    unsafe = max(fixture.candidates, key=lambda item: item.safety_risk)

    assert packet["state_digest"] == fixture.state.state_digest
    assert packet["source_records_mutated"] is False
    assert packet["proposal_only"] is True
    assert packet["physical_work_authorized"] is False
    assert packet["payment_released"] is False
    assert packet["access_controlled"] is False
    assert assessments[unsafe.candidate_id]["admissible"] is False
    assert assessments[unsafe.candidate_id]["blockers"]
    assert evaluation["recommended_candidate_id"] in {
        item.candidate_id for item in fixture.candidates
    }


def test_g5_scene_is_complete_deterministic_and_privacy_minimized() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    first = project_construction_demo_to_scene(fixture)
    second = project_construction_demo_to_scene(fixture)
    report = verify_spatial_scene(first)
    payload = first.to_dict()

    assert report.ok is True
    assert first.scene_digest == second.scene_digest
    assert first.execution_authority is False
    assert first.vsa_patch_authority is False
    assert {item.frame_id for item in fixture.asset_pack.storeys}.issubset(
        {item.frame_id for item in first.frames}
    )
    assert {item.asset_id for item in fixture.asset_pack.assets}.issubset(
        {item.asset_id for item in first.assets}
    )
    assert {item.source_entity_id for item in first.links}.issubset(
        {item.entity_id for item in first.entities}
    )
    assert {item.target_entity_id for item in first.links}.issubset(
        {item.entity_id for item in first.entities}
    )
    metadata_keys = _metadata_keys(payload)
    assert "actor_id" not in metadata_keys
    assert "claimant_id" not in metadata_keys
    assert "consent_ref" not in metadata_keys
    assert "sensor_value" not in metadata_keys
    assert "raw_event_payload" not in metadata_keys
    package_metadata = [
        item["metadata"]
        for item in payload["entities"]
        if "package_ref" in item["metadata"]
    ]
    assert package_metadata
    assert all(item["status_overlay"] is True for item in package_metadata)
    assert all(item["base_geometry_mutated"] is False for item in package_metadata)
    assert all(item["physical_work_authorized"] is False for item in package_metadata)
    assert payload["renderer_hints"]["supported_modes"] == [
        "MESH_ONLY",
        "SPLATS_ONLY",
        "HYBRID",
    ]
    assert payload["renderer_hints"]["runtime_external_fetch"] is False


def test_g5_scene_rejects_restricted_geometry_projection() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    with pytest.raises(ValueError, match="cannot expose demo geometry"):
        project_construction_demo_to_scene(
            fixture,
            privacy_class=SpatialPrivacyClass.RESTRICTED,
        )


def test_g4_fixture_rejects_insufficient_storeys() -> None:
    with pytest.raises(ValueError, match="at least four"):
        build_construction_demo_project_fixture(_pack(storey_count=3))


def test_g4_fixture_rejects_authority_escalation() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    with pytest.raises(ValueError, match="authority boundary"):
        replace(fixture, renderer_authority=True, fixture_digest="")

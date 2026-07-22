from __future__ import annotations

import copy

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


def _asset(
    asset_id: str,
    representation: ConstructionDemoRepresentation,
    uri: str,
) -> ConstructionDemoAssetBinding:
    media_types = {
        ConstructionDemoRepresentation.MESH_GLB: "model/gltf-binary",
        ConstructionDemoRepresentation.FLOOR_PLAN_SVG: "image/svg+xml",
        ConstructionDemoRepresentation.GAUSSIAN_SPZ: "application/vnd.aura.spz",
    }
    return ConstructionDemoAssetBinding(
        asset_id=asset_id,
        storey_id="storey-01",
        representation=representation,
        uri=uri,
        media_type=media_types[representation],
        content_digest="b" * 64,
        byte_length=4096,
        coordinate_system="RIGHT_HANDED_Y_UP_METERS",
        unit_scale_meters=1.0,
        bounds_min=(-10.0, 0.0, -10.0),
        bounds_max=(10.0, 4.0, 10.0),
        source_refs=("ifc:storey:global-id",),
        import_receipt_digest="c" * 32,
        representation_digest="d" * 32,
        truth_class=ConstructionDemoTruthClass.DERIVED_PRESENTATION,
    )


def _pack() -> ConstructionDemoAssetPack:
    storey = ConstructionDemoStorey(
        storey_id="storey-01",
        ifc_global_id="ifc-global-id-01",
        name="Ground Floor",
        elevation_m=0.0,
        ordinal=0,
        source_ifc_ref="demo_assets/construction_tuwien/generated/storeys/storey-01/storey-01.ifc",
        mesh_asset_id="asset-storey-01-glb",
        floor_plan_asset_id="asset-storey-01-svg",
        gaussian_asset_id="asset-storey-01-spz",
        bounds_min=(-10.0, 0.0, -10.0),
        bounds_max=(10.0, 4.0, 10.0),
        frame_id="storey-01-frame",
        source_refs=("ifc:storey:global-id",),
    )
    assets = tuple(
        sorted(
            (
                _asset(
                    "asset-storey-01-glb",
                    ConstructionDemoRepresentation.MESH_GLB,
                    "demo_assets/construction_tuwien/generated/storeys/storey-01/storey-01.glb",
                ),
                _asset(
                    "asset-storey-01-spz",
                    ConstructionDemoRepresentation.GAUSSIAN_SPZ,
                    "demo_assets/construction_tuwien/generated/storeys/storey-01/storey-01.spz",
                ),
                _asset(
                    "asset-storey-01-svg",
                    ConstructionDemoRepresentation.FLOOR_PLAN_SVG,
                    "demo_assets/construction_tuwien/generated/storeys/storey-01/storey-01.svg",
                ),
            ),
            key=lambda item: item.asset_id,
        )
    )
    return ConstructionDemoAssetPack(
        source_manifest=_manifest(),
        building_id="construction-demo-building",
        building_frame_id="construction-demo-building-frame",
        storeys=(storey,),
        assets=assets,
        element_index_digest="e" * 32,
        hierarchy_digest="f" * 32,
        generator_version="construction-demo-generator-v1",
        generator_request_digest="1" * 32,
    )


def test_source_manifest_is_deterministic_and_round_trips() -> None:
    manifest = _manifest()
    restored = ConstructionDemoSourceManifest.from_dict(manifest.to_dict())
    assert restored == manifest
    assert len(manifest.source_manifest_digest) == 32
    assert manifest.fictional_source is True
    assert manifest.survey_authority is False
    assert manifest.person_level_data_included is False
    assert manifest.external_fetch_required_at_runtime is False


def test_source_manifest_rejects_wrong_license_or_runtime_fetch() -> None:
    data = _manifest().to_dict()
    data["license_id"] = "OTHER"
    with pytest.raises(ValueError, match="CC BY 4.0"):
        ConstructionDemoSourceManifest.from_dict(data)

    data = _manifest().to_dict()
    data["external_fetch_required_at_runtime"] = True
    with pytest.raises(ValueError, match="must be false"):
        ConstructionDemoSourceManifest.from_dict(data)


def test_source_manifest_rejects_tampered_digest() -> None:
    data = _manifest().to_dict()
    data["title"] = "Tampered title"
    with pytest.raises(ValueError, match="source_manifest_digest"):
        ConstructionDemoSourceManifest.from_dict(data)


def test_asset_binding_rejects_network_uri_and_survey_authority() -> None:
    data = _asset(
        "asset-storey-01-glb",
        ConstructionDemoRepresentation.MESH_GLB,
        "demo_assets/construction_tuwien/generated/storey.glb",
    ).to_dict()
    data["uri"] = "https://example.invalid/storey.glb"
    with pytest.raises(ValueError, match="network-addressed"):
        ConstructionDemoAssetBinding.from_dict(data)

    data = _asset(
        "asset-storey-01-glb",
        ConstructionDemoRepresentation.MESH_GLB,
        "demo_assets/construction_tuwien/generated/storey.glb",
    ).to_dict()
    data["survey_authority"] = True
    with pytest.raises(ValueError, match="must be false"):
        ConstructionDemoAssetBinding.from_dict(data)


def test_asset_binding_rejects_source_truth_on_derived_representation() -> None:
    data = _asset(
        "asset-storey-01-spz",
        ConstructionDemoRepresentation.GAUSSIAN_SPZ,
        "demo_assets/construction_tuwien/generated/storey.spz",
    ).to_dict()
    data["truth_class"] = ConstructionDemoTruthClass.FICTIONAL_SOURCE_GEOMETRY.value
    with pytest.raises(ValueError, match="derived presentation"):
        ConstructionDemoAssetBinding.from_dict(data)


def test_asset_pack_round_trips_and_denies_truth_ownership() -> None:
    pack = _pack()
    restored = ConstructionDemoAssetPack.from_dict(pack.to_dict())
    assert restored == pack
    assert len(pack.asset_pack_digest) == 32
    assert pack.construction_project_state_owner is False
    assert pack.schedule_truth_owner is False
    assert pack.financial_truth_owner is False
    assert pack.regulatory_truth_owner is False
    assert pack.professional_release_owner is False
    assert pack.renderer_authority is False
    assert pack.physical_location_truth_owner is False
    assert pack.production_mutation is False
    assert pack.automatic_merge is False
    assert pack.human_review_required is True


def test_asset_pack_rejects_unknown_storey_asset_and_authority_escalation() -> None:
    data = _pack().to_dict()
    data["storeys"][0]["mesh_asset_id"] = "asset-missing"
    data["storeys"][0]["storey_digest"] = ""
    data["asset_pack_digest"] = ""
    with pytest.raises(ValueError, match="unknown required asset"):
        ConstructionDemoAssetPack.from_dict(data)

    data = _pack().to_dict()
    data["renderer_authority"] = True
    data["asset_pack_digest"] = ""
    with pytest.raises(ValueError, match="must be false"):
        ConstructionDemoAssetPack.from_dict(data)


def test_asset_pack_rejects_tampered_nested_manifest_digest() -> None:
    data = copy.deepcopy(_pack().to_dict())
    data["source_manifest"]["publisher"] = "Tampered publisher"
    data["asset_pack_digest"] = ""
    with pytest.raises(ValueError, match="source_manifest_digest"):
        ConstructionDemoAssetPack.from_dict(data)

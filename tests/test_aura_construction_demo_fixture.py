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


def test_g4_fixture_rejects_insufficient_storeys() -> None:
    with pytest.raises(ValueError, match="at least four"):
        build_construction_demo_project_fixture(_pack(storey_count=3))


def test_g4_fixture_rejects_authority_escalation() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    with pytest.raises(ValueError, match="authority boundary"):
        replace(fixture, renderer_authority=True, fixture_digest="")

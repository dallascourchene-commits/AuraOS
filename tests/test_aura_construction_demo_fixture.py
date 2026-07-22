from __future__ import annotations

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
    MINIMUM_TRADE_NAMES,
    ConstructionDemoProjectFixture,
    ConstructionDemoWorkStatus,
)
from aura_construction_demo_fixture_builder import (
    build_construction_demo_project_fixture,
    build_construction_demo_runtime_packet,
)
from aura_construction_state import query_claim_readiness


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
    storey_id: str,
    representation: ConstructionDemoRepresentation,
    suffix: str,
) -> ConstructionDemoAssetBinding:
    media_types = {
        ConstructionDemoRepresentation.MESH_GLB: "model/gltf-binary",
        ConstructionDemoRepresentation.FLOOR_PLAN_SVG: "image/svg+xml",
        ConstructionDemoRepresentation.GAUSSIAN_SPZ: "application/vnd.aura.spz",
    }
    return ConstructionDemoAssetBinding(
        asset_id=f"asset-{storey_id}-{suffix}",
        storey_id=storey_id,
        representation=representation,
        uri=f"demo_assets/construction_tuwien/generated/storeys/{storey_id}/{storey_id}.{suffix}",
        media_type=media_types[representation],
        content_digest=(suffix[0] if suffix[0] in "abcdef" else "b") * 64,
        byte_length=4096,
        coordinate_system="RIGHT_HANDED_Y_UP_METERS",
        unit_scale_meters=1.0,
        bounds_min=(-10.0, 0.0, -10.0),
        bounds_max=(10.0, 4.0, 10.0),
        source_refs=(f"ifc:storey:{storey_id}",),
        import_receipt_digest="c" * 32,
        representation_digest="d" * 32,
        truth_class=ConstructionDemoTruthClass.DERIVED_PRESENTATION,
    )


def _pack(count: int = 5) -> ConstructionDemoAssetPack:
    storeys = []
    assets = []
    for ordinal in range(count):
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
        assets.extend(
            (
                _asset(storey_id, ConstructionDemoRepresentation.MESH_GLB, "glb"),
                _asset(storey_id, ConstructionDemoRepresentation.FLOOR_PLAN_SVG, "svg"),
                _asset(storey_id, ConstructionDemoRepresentation.GAUSSIAN_SPZ, "spz"),
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


def test_g4_fixture_is_deterministic_complete_and_asset_bound() -> None:
    pack = _pack()
    first = build_construction_demo_project_fixture(pack)
    second = build_construction_demo_project_fixture(pack)

    assert type(first) is ConstructionDemoProjectFixture
    assert first == second
    assert first.fixture_digest == second.fixture_digest
    assert {item.name for item in first.trades} == MINIMUM_TRADE_NAMES
    assert {item.status for item in first.work_packages} == {
        item.value for item in ConstructionDemoWorkStatus
    }
    assert {item.storey_id for item in first.work_packages}.issubset(
        {item.storey_id for item in pack.storeys}
    )
    assert all(item.scope.project_id == first.state.project_id for item in first.work_packages)
    assert all(item.scope.zone_id == item.zone_id for item in first.work_packages)
    assert len(first.budget_lines) == len(first.work_packages)
    assert {item.work_package_id for item in first.budget_lines} == {
        item.work_package_id for item in first.work_packages
    }


def test_g4_blocked_clearance_and_safe_alternative_remain_review_only() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    readiness = query_claim_readiness(
        fixture.state,
        claim_id=fixture.blocked_clearance_claim_id,
        now=30.0,
    )
    assert readiness.ready is False
    assert "non_dispositive_evidence_only" in readiness.blockers

    unsafe = next(
        item for item in fixture.alternatives
        if item.alternative_id == "alternative-continue-drilling"
    )
    safe = next(
        item for item in fixture.alternatives
        if item.alternative_id == "alternative-shift-preparation"
    )
    assert unsafe.admissible is False
    assert unsafe.automatic_execution is False
    assert safe.admissible is True
    assert safe.recommended_for_human_review is True
    assert safe.automatic_execution is False
    assert fixture.physical_work_authority is False
    assert fixture.financial_authority is False
    assert fixture.regulatory_authority is False
    assert fixture.automatic_execution is False
    assert fixture.human_review_required is True


def test_g4_runtime_packet_hard_blocks_unsafe_candidate() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    packet = build_construction_demo_runtime_packet(fixture)
    unsafe_id = next(
        item.candidate_id for item in fixture.candidates
        if item.title == "Continue upper-floor drilling"
    )
    assessment = next(
        item for item in packet["evaluation"]["assessments"]
        if item["candidate_id"] == unsafe_id
    )

    assert packet["state_digest"] == fixture.state.state_digest
    assert packet["proposal_only"] is True
    assert packet["physical_work_authorized"] is False
    assert packet["payment_released"] is False
    assert packet["access_controlled"] is False
    assert assessment["admissible"] is False
    assert assessment["blockers"]
    assert packet["evaluation"]["recommended_candidate_id"] != unsafe_id


def test_g4_rejects_asset_pack_without_five_storeys() -> None:
    with pytest.raises(ValueError, match="at least five"):
        build_construction_demo_project_fixture(_pack(4))


def test_g4_rules_are_explicitly_synthetic_and_non_authoritative() -> None:
    fixture = build_construction_demo_project_fixture(_pack())
    assert fixture.rules
    for rule in fixture.rules:
        assert rule.truth_class == "SYNTHETIC_DEMO_RULE"
        assert rule.legal_authority is False
        assert rule.regulatory_authority is False
        assert rule.jurisdiction_claimed == "none"

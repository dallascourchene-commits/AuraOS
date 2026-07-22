from __future__ import annotations

from aura_construction_demo_spatial_assets import (
    CONSTRUCTION_SITE_ROOT_FRAME_ID,
    project_construction_demo_asset_foundation,
)
from aura_spatial_contracts import SpatialTruthClass
from tests.test_aura_construction_demo_fixture import _pack


def test_g5_asset_foundation_is_deterministic_and_storey_bound() -> None:
    pack = _pack()
    first = project_construction_demo_asset_foundation(pack)
    second = project_construction_demo_asset_foundation(pack)

    assert first == second
    frames, assets, entities, links = first
    assert frames[0].frame_id == CONSTRUCTION_SITE_ROOT_FRAME_ID
    assert len(frames) == len(pack.storeys) + 2
    assert len(assets) == len(pack.assets)
    assert len(entities) == len(pack.storeys) + 1
    assert len(links) == len(pack.storeys)
    assert {asset.asset_id for asset in assets} == {
        binding.asset_id for binding in pack.assets
    }
    assert all(asset.truth_class is SpatialTruthClass.PRESENTATION for asset in assets)
    assert all(asset.metadata["projection_only"] is True for asset in assets)
    assert all(asset.metadata["survey_authority"] is False for asset in assets)
    assert all(
        asset.metadata["person_level_data_included"] is False for asset in assets
    )
    assert all(entity.metadata["projection_only"] is True for entity in entities)
    assert all(link.metadata["projection_only"] is True for link in links)


def test_g5_asset_foundation_keeps_status_separate_from_geometry() -> None:
    pack = _pack()
    _frames, assets, entities, _links = project_construction_demo_asset_foundation(pack)
    storey_entities = [entity for entity in entities if "storey_id" in entity.metadata]

    assert len(storey_entities) == len(pack.storeys)
    assert all(entity.metadata["status_overlay_separate"] is True for entity in storey_entities)
    assert all(entity.metadata["source_geometry_mutated"] is False for entity in storey_entities)
    assert all("status" not in asset.metadata for asset in assets)

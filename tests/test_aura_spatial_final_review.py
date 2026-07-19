"""Final regressions from the last manual and Codex review pass."""
from __future__ import annotations

from copy import deepcopy

import pytest

from aura_spatial_contracts import (
    CoordinateFrame,
    MAX_SPATIAL_METADATA_BYTES,
    SpatialEntity,
    SpatialEntityType,
)
from aura_spatial_scene import (
    compile_spatial_scene,
    validate_spatial_scene_payload,
)


def _two_entity_scene():
    root = CoordinateFrame(frame_id="root")
    first = SpatialEntity(
        entity_id="entity:a",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="A",
        frame_id="root",
        source_refs=("source:a.py",),
    )
    second = SpatialEntity(
        entity_id="entity:b",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="B",
        frame_id="root",
        source_refs=("source:b.py",),
    )
    return compile_spatial_scene(
        scene_id="final-review-scene",
        purpose_digest="purpose:final-review",
        root_frame_id="root",
        frames=(root,),
        entities=(second, first),
        source_refs=("source:b.py", "source:a.py"),
    )


def test_contract_rejects_oversized_metadata_before_digesting():
    with pytest.raises(ValueError, match="byte limit"):
        SpatialEntity(
            entity_id="entity:large-metadata",
            entity_type=SpatialEntityType.DOMAIN_NODE,
            label="Large metadata",
            frame_id="root",
            metadata={
                "payload": "x" * (MAX_SPATIAL_METADATA_BYTES + 1)
            },
        )


def test_interchange_rejects_noncanonical_record_order():
    payload = _two_entity_scene().to_dict()
    assert [item["entity_id"] for item in payload["entities"]] == [
        "entity:a",
        "entity:b",
    ]
    noncanonical = deepcopy(payload)
    noncanonical["entities"].reverse()
    with pytest.raises(ValueError, match="uniquely sorted by entity_id"):
        validate_spatial_scene_payload(noncanonical)


def test_interchange_rejects_noncanonical_set_like_references():
    payload = _two_entity_scene().to_dict()
    noncanonical = deepcopy(payload)
    noncanonical["source_refs"].reverse()
    with pytest.raises(ValueError, match="scene.source_refs must be uniquely sorted"):
        validate_spatial_scene_payload(noncanonical)

    nested = deepcopy(payload)
    nested["entities"][0]["source_refs"] = [
        "source:z.py",
        "source:a.py",
    ]
    with pytest.raises(
        ValueError,
        match=r"scene.entities\[0\]\.source_refs must be uniquely sorted",
    ):
        validate_spatial_scene_payload(nested)

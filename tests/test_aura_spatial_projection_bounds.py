"""Retained-payload and source-anchor bounds for Aura spatial projection."""
from __future__ import annotations

import aura_spatial_projection as projection


def _project(
    monkeypatch,
    *,
    node_metadata,
    edge_metadata,
    file_path="pkg/selected.py",
    symbol="selected",
    line_range=(1, 2),
):
    nodes = [
        {
            "id": "node:selected",
            "label": "Selected",
            "node_type": "function",
            "file_path": file_path,
            "symbol": symbol,
            "line_range": list(line_range),
            "metadata": node_metadata,
        },
        {
            "id": "node:target",
            "label": "Target",
            "node_type": "function",
            "metadata": {},
        },
    ]
    links = [
        {
            "id": "edge:selected-target",
            "source": "node:selected",
            "target": "node:target",
            "type": "calls",
            "metadata": edge_metadata,
        }
    ]

    def fake_selector(_topology, selected, **_kwargs):
        return {
            "version": "test",
            "selected_node_ids": list(selected),
            "nodes": nodes,
            "links": links,
            "depth": 1,
            "human_instruction": "inspect",
            "token_cost": 1,
        }

    monkeypatch.setattr(
        projection,
        "select_micro_arena",
        fake_selector,
    )
    return projection.project_coding_topology_to_scene(
        {"nodes": nodes, "links": links},
        ("node:selected",),
    )


def _selected_entity(scene):
    return next(
        entity
        for entity in scene.entities
        if entity.to_dict()["metadata"]["domain_node_id"]
        == "node:selected"
    )


def test_large_retained_node_metadata_is_omitted_from_evidence(monkeypatch):
    scene = _project(
        monkeypatch,
        node_metadata={
            "visual_projection_only": True,
            "unbounded_blob": "x" * 2_000_000,
        },
        edge_metadata={},
    )
    asset = scene.assets[0]
    assert asset.byte_length < 100_000
    assert asset.byte_length <= projection.MAX_PROJECTION_BYTES
    entity_metadata = _selected_entity(scene).to_dict()["metadata"]
    assert "unbounded_blob" not in entity_metadata
    assert entity_metadata["projection_truth"] == "CODEMAP_PROJECTED"


def test_large_retained_edge_metadata_is_omitted_from_evidence(monkeypatch):
    scene = _project(
        monkeypatch,
        node_metadata={},
        edge_metadata={"unbounded_blob": "x" * 2_000_000},
    )
    asset = scene.assets[0]
    assert asset.byte_length < 100_000
    assert asset.byte_length <= projection.MAX_PROJECTION_BYTES
    link_metadata = scene.links[0].to_dict()["metadata"]
    assert "unbounded_blob" not in link_metadata
    assert set(link_metadata) == {
        "domain_owner",
        "source_node_id",
        "target_node_id",
        "source_edge_id",
    }


def test_unsafe_topology_source_anchor_is_omitted(monkeypatch):
    scene = _project(
        monkeypatch,
        node_metadata={},
        edge_metadata={},
        file_path="../../outside.py",
        symbol="unsafe.symbol",
        line_range=(10, 20),
    )
    entity = _selected_entity(scene)
    metadata = entity.to_dict()["metadata"]
    assert metadata["file_path"] == ""
    assert metadata["symbol"] == ""
    assert metadata["line_range"] == []
    assert entity.source_refs == ("topology:node:selected",)

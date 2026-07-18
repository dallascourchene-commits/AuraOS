"""One-shot Council V3 cost-lane repair for Aura Spatial S0-S2."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(relative_path: str, old: str, new: str) -> None:
    path = ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{relative_path}: expected one exact replacement target, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(relative_path: str, marker: str, addition: str) -> None:
    path = ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + addition.rstrip() + "\n", encoding="utf-8")


replace_once(
    "aura_spatial_projection.py",
    '''    if not raw_nodes:\n        raise ValueError(\n            "coding topology projection requires at least one grounded node"\n        )\n\n    root_frame = CoordinateFrame(\n''',
    '''    if not raw_nodes:\n        raise ValueError(\n            "coding topology projection requires at least one grounded node"\n        )\n\n    bounded_micro = {\n        "version": micro.get("version"),\n        "selected_node_ids": list(returned_selected),\n        "nodes": raw_nodes,\n        "links": raw_links,\n        "depth": micro.get("depth"),\n        "human_instruction": micro.get("human_instruction"),\n        "token_cost": micro.get("token_cost"),\n    }\n    bounded_micro_digest = stable_digest(bounded_micro, digest_size=32)\n\n    root_frame = CoordinateFrame(\n''',
)

replace_once(
    "aura_spatial_projection.py",
    'f"micro_arena:{stable_digest(micro, digest_size=16)}",',
    'f"bounded_micro_arena:{bounded_micro_digest}",',
)

replace_once(
    "aura_spatial_projection.py",
    '''    micro_bytes = canonical_json(micro).encode("utf-8")\n    bounds_min, bounds_max = _bounds(positions)\n    graph_asset = SpatialAssetManifest(\n        asset_id=_stable_identifier("coding-graph-asset", micro),\n''',
    '''    micro_bytes = canonical_json(bounded_micro).encode("utf-8")\n    bounds_min, bounds_max = _bounds(positions)\n    graph_asset = SpatialAssetManifest(\n        asset_id=_stable_identifier("coding-graph-asset", bounded_micro),\n''',
)

replace_once(
    "aura_spatial_projection.py",
    '''            "aura://coding/micro-arena/"\n            f"{stable_digest(micro, digest_size=16)}"\n''',
    '''            "aura://coding/micro-arena/"\n            f"{bounded_micro_digest[:32]}"\n''',
)

replace_once(
    "aura_spatial_projection.py",
    'f"micro_arena:{stable_digest(micro, digest_size=32)}",',
    'f"bounded_micro_arena:{bounded_micro_digest}",',
)

replace_once(
    "aura_spatial_projection.py",
    '''            "node_count": len(raw_nodes),\n            "link_count": len(links),\n            "truncated": (\n''',
    '''            "node_count": len(raw_nodes),\n            "link_count": len(links),\n            "source_node_count": len(micro.get("nodes", [])),\n            "source_link_count": len(micro.get("links", [])),\n            "truncated": (\n''',
)

replace_once(
    "aura_spatial_projection.py",
    '"micro_digest": stable_digest(micro, digest_size=32),',
    '"bounded_micro_digest": bounded_micro_digest,',
)

replace_once(
    "docs/AURA_SPATIAL_COMPUTING.md",
    '''- creates a content-addressed topology-graph asset manifest;\n- prioritizes exact selected nodes before applying the bounded node cap;\n''',
    '''- creates a content-addressed topology-graph asset manifest from the same bounded node/link projection, never the unbounded pre-truncation neighborhood;\n- records pre-bound source counts and explicit truncation without serializing discarded topology into the asset evidence;\n- prioritizes exact selected nodes before applying the bounded node cap;\n''',
)

append_once(
    "tests/test_aura_spatial_substrate.py",
    "def test_topology_asset_evidence_excludes_discarded_large_nodes():",
    '''def test_topology_asset_evidence_excludes_discarded_large_nodes():\n    selected_id = "node:129"\n    nodes = [\n        {\n            "id": f"node:{index:03d}",\n            "label": f"Node {index}",\n            "node_type": "function",\n            "file_path": f"pkg/module_{index}.py",\n            "symbol": f"function_{index}",\n            "line_range": [1, 2],\n            "metadata": (\n                {"discarded_blob": "x" * 2_000_000}\n                if index == 128\n                else {}\n            ),\n        }\n        for index in range(130)\n    ]\n    links = [\n        {\n            "source": selected_id,\n            "target": f"node:{index:03d}",\n            "type": "calls",\n        }\n        for index in range(129)\n    ]\n    scene = project_coding_topology_to_scene(\n        {"nodes": nodes, "links": links},\n        (selected_id,),\n        depth=1,\n    )\n    asset = scene.assets[0]\n    metadata = asset.to_dict()["metadata"]\n    assert metadata["truncated"] is True\n    assert metadata["source_node_count"] == 130\n    assert metadata["source_link_count"] == 129\n    assert metadata["node_count"] == 128\n    assert asset.byte_length < 250_000\n''',
)

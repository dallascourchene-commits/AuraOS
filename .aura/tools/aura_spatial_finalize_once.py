"""One-shot exact-source finalizer for Aura Spatial S0-S2.

Every transformation is an exact single-match operation. The accompanying workflow
runs the focused spatial circuit and regenerates CODEMAP before committing results.
"""
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
    "aura_spatial_contracts.py",
    "from aura_event_contracts import canonical_json, stable_digest",
    "from aura_event_contracts import canonical_json, sanitize_payload, stable_digest",
)

replace_once(
    "aura_spatial_contracts.py",
    '''    if not isinstance(value, Mapping):\n        raise ValueError(f"{field_name} must be an object")\n    frozen = _freeze_json(value, field_name)\n''',
    '''    if not isinstance(value, Mapping):\n        raise ValueError(f"{field_name} must be an object")\n    value = sanitize_payload(value)\n    frozen = _freeze_json(value, field_name)\n''',
)

replace_once(
    "aura_spatial_contracts.py",
    '''        object.__setattr__(\n            self,\n            "projection_only",\n            _strict_bool(self.projection_only, "frame.projection_only"),\n        )\n\n\n@dataclass(frozen=True)\nclass SpatialAssetManifest''',
    '''        object.__setattr__(\n            self,\n            "projection_only",\n            _strict_bool(self.projection_only, "frame.projection_only"),\n        )\n        if not self.projection_only:\n            raise ValueError("coordinate frames must remain projection-only")\n\n\n@dataclass(frozen=True)\nclass SpatialAssetManifest''',
)

replace_once(
    "aura_spatial_contracts.py",
    '''        object.__setattr__(\n            self,\n            "projection_only",\n            _strict_bool(self.projection_only, "entity.projection_only"),\n        )\n        object.__setattr__(\n            self,\n            "patch_authority",''',
    '''        object.__setattr__(\n            self,\n            "projection_only",\n            _strict_bool(self.projection_only, "entity.projection_only"),\n        )\n        if not self.projection_only:\n            raise ValueError("spatial entities must remain projection-only")\n        object.__setattr__(\n            self,\n            "patch_authority",''',
)

replace_once(
    "aura_spatial_contracts.py",
    '''        object.__setattr__(\n            self,\n            "projection_only",\n            _strict_bool(self.projection_only, "link.projection_only"),\n        )\n        object.__setattr__(\n            self,\n            "metadata",''',
    '''        object.__setattr__(\n            self,\n            "projection_only",\n            _strict_bool(self.projection_only, "link.projection_only"),\n        )\n        if not self.projection_only:\n            raise ValueError("spatial links must remain projection-only")\n        object.__setattr__(\n            self,\n            "metadata",''',
)

replace_once(
    "aura_spatial_projection.py",
    '''    raw_links = [\n        item for item in micro.get("links", []) if isinstance(item, dict)\n    ]\n    raw_nodes = raw_nodes[:MAX_SPATIAL_NODES]\n    allowed_node_ids = {str(item["id"]) for item in raw_nodes}\n''',
    '''    raw_links = [\n        item for item in micro.get("links", []) if isinstance(item, dict)\n    ]\n    selected_set = set(returned_selected)\n    raw_nodes.sort(\n        key=lambda item: (\n            0 if str(item.get("id")) in selected_set else 1,\n            str(item.get("id") or ""),\n        )\n    )\n    raw_nodes = raw_nodes[:MAX_SPATIAL_NODES]\n    allowed_node_ids = {str(item["id"]) for item in raw_nodes}\n    if not selected_set.issubset(allowed_node_ids):\n        raise ValueError("selected topology nodes exceeded the spatial node cap")\n''',
)

replace_once(
    "aura_spatial_projection.py",
    '''    positions: list[tuple[float, float, float]] = []\n    selected_set = set(micro.get("selected_node_ids", []))\n    for index, node in enumerate(raw_nodes):\n''',
    '''    positions: list[tuple[float, float, float]] = []\n    for index, node in enumerate(raw_nodes):\n''',
)

replace_once(
    "aura_spatial_ws_guard.py",
    '''    target = str(target_id or "").strip()\n    if not target:\n        raise ValueError("target_id is required")\n    if target not in shapes:\n        raise KeyError(f"shape {target!r} not found")\n    if new_function is None or new_function == "":\n        raise ValueError("new_function is required")\n    if not isinstance(shapes, Mapping):\n        raise ValueError("shapes must be a mapping")\n''',
    '''    target = str(target_id or "").strip()\n    if not target:\n        raise ValueError("target_id is required")\n    if not isinstance(shapes, Mapping):\n        raise ValueError("shapes must be a mapping")\n    if target not in shapes:\n        raise KeyError(f"shape {target!r} not found")\n    if new_function is None or new_function == "":\n        raise ValueError("new_function is required")\n''',
)

replace_once(
    "docs/AURA_SPATIAL_COMPUTING.md",
    '''- duplicate frame IDs;\n- missing parents;\n- cycles;''',
    '''- duplicate frame IDs;\n- any attempt to set `projection_only=false`;\n- missing parents;\n- cycles;''',
)

replace_once(
    "docs/AURA_SPATIAL_COMPUTING.md",
    '''- preserves only links whose endpoints remain inside the bounded node closure;\n- marks every entity `patch_authority=false`;''',
    '''- prioritizes exact selected nodes before applying the bounded node cap;\n- preserves only links whose endpoints remain inside the bounded node closure;\n- marks every entity `projection_only=true` and `patch_authority=false`;''',
)

replace_once(
    "docs/AURA_SPATIAL_COMPUTING.md",
    '''Every snapshot carries:\n''',
    '''Metadata is sanitized through Aura's canonical event sanitizer: secret-shaped fields are redacted and private-reasoning fields are rejected before scene hashing.\n\nEvery snapshot carries:\n''',
)

append_once(
    "tests/test_aura_spatial_substrate.py",
    "def test_projection_only_contracts_fail_closed():",
    '''def test_projection_only_contracts_fail_closed():\n    with pytest.raises(ValueError, match="projection-only"):\n        CoordinateFrame(frame_id="frame:not-projection", projection_only=False)\n    with pytest.raises(ValueError, match="projection-only"):\n        SpatialEntity(\n            entity_id="entity:not-projection",\n            entity_type=SpatialEntityType.DOMAIN_NODE,\n            label="Not projection",\n            frame_id="root",\n            projection_only=False,\n        )\n    with pytest.raises(ValueError, match="projection-only"):\n        SpatialLink(\n            link_id="link:not-projection",\n            source_entity_id="entity:one",\n            target_entity_id="entity:two",\n            relation="related",\n            projection_only=False,\n        )\n\n\ndef test_selected_node_survives_spatial_node_cap():\n    selected_id = "node:129"\n    nodes = [\n        {\n            "id": f"node:{index}",\n            "label": f"Node {index}",\n            "node_type": "function",\n            "file_path": f"pkg/module_{index}.py",\n            "symbol": f"function_{index}",\n            "line_range": [1, 2],\n            "metadata": {},\n        }\n        for index in range(130)\n    ]\n    links = [\n        {\n            "source": selected_id,\n            "target": f"node:{index}",\n            "type": "calls",\n        }\n        for index in range(129)\n    ]\n    scene = project_coding_topology_to_scene(\n        {"nodes": nodes, "links": links},\n        (selected_id,),\n        depth=1,\n    )\n    assert len(scene.entities) == 128\n    assert any(\n        f"topology:{selected_id}" in entity.source_refs\n        for entity in scene.entities\n    )\n\n\ndef test_spatial_metadata_redacts_secrets_and_rejects_private_reasoning():\n    entity = SpatialEntity(\n        entity_id="entity:sanitized",\n        entity_type=SpatialEntityType.DOMAIN_NODE,\n        label="Sanitized",\n        frame_id="root",\n        metadata={"api_key": "sk-secret-value-12345678901234567890"},\n    )\n    assert entity.to_dict()["metadata"]["api_key"] == "[REDACTED]"\n    with pytest.raises(ValueError, match="private reasoning field"):\n        SpatialEntity(\n            entity_id="entity:private-reasoning",\n            entity_type=SpatialEntityType.DOMAIN_NODE,\n            label="Private reasoning",\n            frame_id="root",\n            metadata={"chain_of_thought": "not allowed"},\n        )\n''',
)

"""One-shot exact-source transformer for the Spatial S0-S2 pull request.

The script is deliberately narrow and fail-closed: every replacement must match
exactly once. It exists only to apply reviewed changes to larger source files from
a repository-native checkout, where the complete files and their current hashes
are available. It grants no runtime or merge authority.
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
    '''class CanonicalSpatialRecord:\n    def to_dict(self) -> dict[str, Any]:\n        result: dict[str, Any] = {}\n        for field in fields(self):\n            value = getattr(self, field.name)\n            if isinstance(value, Enum):\n                result[field.name] = value.value\n            elif isinstance(value, tuple):\n                result[field.name] = _thaw_json(value)\n            elif isinstance(value, CanonicalSpatialRecord):\n                result[field.name] = value.to_dict()\n            else:\n                result[field.name] = value\n        return result\n''',
    '''class CanonicalSpatialRecord:\n    def to_dict(self) -> dict[str, Any]:\n        result: dict[str, Any] = {}\n        mapping_fields = {"metadata", "intent_slots", "renderer_hints"}\n        for field in fields(self):\n            value = getattr(self, field.name)\n            if isinstance(value, Enum):\n                result[field.name] = value.value\n            elif isinstance(value, CanonicalSpatialRecord):\n                result[field.name] = value.to_dict()\n            elif isinstance(value, tuple) and field.name in mapping_fields:\n                result[field.name] = _thaw_json(value)\n            elif isinstance(value, tuple):\n                result[field.name] = [_record_value(item) for item in value]\n            else:\n                result[field.name] = value\n        return result\n\n\ndef _record_value(value: Any) -> Any:\n    if isinstance(value, Enum):\n        return value.value\n    if isinstance(value, CanonicalSpatialRecord):\n        return value.to_dict()\n    if isinstance(value, tuple):\n        return [_record_value(item) for item in value]\n    return value\n''',
)

replace_once(
    "aura_spatial_asset_registry.py",
    '_ALLOWED_LOCAL_SCHEMES = frozenset({"", "file", "aura"})',
    '_ALLOWED_LOCAL_SCHEMES = frozenset({"", "aura"})',
)

replace_once(
    "aura_spatial_projection.py",
    '''    if not isinstance(topology, dict):\n        raise ValueError("topology must be an object")\n    micro = select_micro_arena(\n        topology,\n        tuple(str(item) for item in selected_node_ids),\n        depth=max(0, min(2, int(depth))),\n        human_instruction=human_instruction,\n        token_budget=max(1, int(token_budget)),\n    )\n''',
    '''    if not isinstance(topology, dict):\n        raise ValueError("topology must be an object")\n    requested = tuple(\n        dict.fromkeys(\n            str(item).strip()\n            for item in selected_node_ids\n            if str(item).strip()\n        )\n    )\n    if not requested:\n        raise ValueError("selected_node_ids must not be empty")\n    known_node_ids = {\n        str(item.get("id"))\n        for item in topology.get("nodes", [])\n        if isinstance(item, dict) and item.get("id")\n    }\n    missing = [item for item in requested if item not in known_node_ids]\n    if missing:\n        raise ValueError(f"unknown selected topology nodes: {missing}")\n    micro = select_micro_arena(\n        topology,\n        requested,\n        depth=max(0, min(2, int(depth))),\n        human_instruction=human_instruction,\n        token_budget=max(1, int(token_budget)),\n    )\n    returned_selected = tuple(micro.get("selected_node_ids", []))\n    if returned_selected != requested:\n        raise ValueError(\n            "Coding Arena projection changed the exact requested selection"\n        )\n''',
)

replace_once(
    "schemas/aura_spatial_scene.schema.json",
    '''    "vec3": {\n      "type": "array",\n      "prefixItems": [''',
    '''    "vec3": {\n      "type": "array",\n      "minItems": 3,\n      "maxItems": 3,\n      "prefixItems": [''',
)
replace_once(
    "schemas/aura_spatial_scene.schema.json",
    '''    "quat": {\n      "type": "array",\n      "prefixItems": [''',
    '''    "quat": {\n      "type": "array",\n      "minItems": 4,\n      "maxItems": 4,\n      "prefixItems": [''',
)

replace_once(
    "aura_topology_ws_bridge.py",
    '''try:\n    from aura_spectral_topology import augment_topology_payload, normalize_topology_payload\nexcept ImportError:\n    augment_topology_payload = None  # type: ignore[assignment]\n    normalize_topology_payload = None  # type: ignore[assignment]\n''',
    '''try:\n    from aura_spectral_topology import augment_topology_payload, normalize_topology_payload\nexcept ImportError:\n    augment_topology_payload = None  # type: ignore[assignment]\n    normalize_topology_payload = None  # type: ignore[assignment]\n\ntry:\n    from aura_spatial_ws_guard import compile_ar_hotswap_handoff\nexcept ImportError:\n    compile_ar_hotswap_handoff = None  # type: ignore[assignment]\n''',
)

replace_once(
    "aura_topology_ws_bridge.py",
    '''    async def _handle_hotswap_request(self, session: _ARSession, data: dict) -> None:\n        target_id    = data.get("targetId")\n        new_function = data.get("newFunction")\n        if not target_id or not new_function:\n            raise ValueError("targetId and newFunction required")\n\n        # Forward to node hotswap if available (set via node reference)\n        result = {"status": "success", "targetId": target_id, "message": "Hotswap queued"}\n        await self._broadcast_message({\n            "type": "HOTSWAP_COMPLETE",\n            "targetId": target_id,\n            "result": result,\n        })\n        _ar_logger.info("Hotswap queued for %s", target_id)\n        await self._refresh_topology()\n''',
    '''    async def _handle_hotswap_request(self, session: _ARSession, data: dict) -> None:\n        target_id = data.get("targetId")\n        new_function = data.get("newFunction")\n        if not target_id or not new_function:\n            raise ValueError("targetId and newFunction required")\n\n        if compile_ar_hotswap_handoff is None:\n            result = {\n                "ok": False,\n                "status": "SPATIAL_GUARD_UNAVAILABLE",\n                "error": "spatial_hotswap_guard_unavailable",\n                "targetId": target_id,\n                "queued": False,\n                "success": False,\n                "production_mutation": False,\n                "automatic_commit": False,\n                "automatic_push": False,\n                "automatic_merge": False,\n            }\n        else:\n            result = compile_ar_hotswap_handoff(\n                target_id=str(target_id),\n                new_function=new_function,\n                shapes=self._shapes,\n                actor_ref=f"ar-session:{session.session_id}",\n            )\n\n        await session.websocket.send(_json_ar.dumps({\n            "type": "HOTSWAP_REVIEW_REQUIRED",\n            "targetId": target_id,\n            "result": result,\n        }))\n        _ar_logger.info(\n            "Hotswap review handoff compiled for %s; no mutation executed",\n            target_id,\n        )\n''',
)

replace_once(
    "docs/AURA_SPATIAL_COMPUTING.md",
    "Bridge integration is a bounded S2 change: the bridge must call this guard using a current immutable scene and must stop before Forge preparation unless exact source evidence is available.",
    "The legacy AR bridge now calls the guard against its current bounded shape state, returns `HOTSWAP_REVIEW_REQUIRED` only to the requesting session, retains only a redacted proposal digest, and does not broadcast success or refresh topology as though a mutation occurred.",
)

replace_once(
    "tests/test_aura_spatial_ws_guard.py",
    "from __future__ import annotations\n\nfrom types import SimpleNamespace",
    "from __future__ import annotations\n\nimport inspect\nfrom types import SimpleNamespace",
)

append_once(
    "tests/test_aura_spatial_ws_guard.py",
    "def test_legacy_bridge_handler_uses_private_spatial_guard():",
    '''def test_legacy_bridge_handler_uses_private_spatial_guard():\n    from aura_topology_ws_bridge import AuraARWebSocketServer\n\n    source = inspect.getsource(AuraARWebSocketServer._handle_hotswap_request)\n    assert "compile_ar_hotswap_handoff" in source\n    assert "HOTSWAP_REVIEW_REQUIRED" in source\n    assert "_broadcast_message" not in source\n    assert "_refresh_topology" not in source\n    assert "Hotswap queued" not in source\n''',
)

append_once(
    "tests/test_aura_spatial_substrate.py",
    "def test_empty_sequence_contract_fields_serialize_as_arrays():",
    '''def test_empty_sequence_contract_fields_serialize_as_arrays():\n    frame = CoordinateFrame(frame_id="root")\n    entity = SpatialEntity(\n        entity_id="entity:empty",\n        entity_type=SpatialEntityType.DOMAIN_NODE,\n        label="Empty",\n        frame_id="root",\n    )\n    assert frame.to_dict()["source_refs"] == []\n    assert entity.to_dict()["asset_ids"] == []\n    assert entity.to_dict()["source_refs"] == []\n    assert entity.to_dict()["metadata"] == {}\n\n\ndef test_unknown_coding_selection_fails_closed():\n    with pytest.raises(ValueError, match="unknown selected topology nodes"):\n        project_coding_topology_to_scene(\n            _topology(),\n            ("missing:node",),\n        )\n\n\ndef test_file_asset_uri_is_not_admitted():\n    manifest = _asset()\n    file_uri = SpatialAssetManifest(\n        **{\n            **manifest.to_dict(),\n            "asset_id": "asset:file-uri",\n            "uri": "file:///tmp/scene.glb",\n            "metadata": {},\n        }\n    )\n    report = validate_asset_manifest(file_uri)\n    assert report.ok is False\n    assert report.findings[0]["code"] == "UNSUPPORTED_ASSET_URI_SCHEME"\n''',
)

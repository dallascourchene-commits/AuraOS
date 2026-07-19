from __future__ import annotations

import base64
import json
from pathlib import Path
import struct

from jsonschema import Draft202012Validator
import pytest

from aura_spatial_contracts import PATCH_AUTHORITY
from aura_spatial_importers.contracts import validate_spatial_import_receipt_payload
from aura_spatial_importers.gltf import import_gltf_bytes, import_gltf_file

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/spatial/gltf/triangle.gltf"


def test_gltf_import_is_bounded_deterministic_and_schema_valid():
    first = import_gltf_file(FIXTURE, provenance_refs=("fixture:gltf",), root=ROOT)
    second = import_gltf_bytes(FIXTURE.read_bytes(), provenance_refs=("fixture:gltf", "local-file:triangle.gltf"))
    assert first.receipt.derived_asset_digest == second.receipt.derived_asset_digest
    assert first.receipt.source_format.value == "GLTF"
    assert first.positions == ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    assert first.indices == (0, 1, 2)
    payload = first.receipt.to_dict()
    assert payload["network_fetch_performed"] is False
    assert payload["scripts_executed"] is False
    assert payload["shaders_executed"] is False
    assert payload["patch_authority"] == PATCH_AUTHORITY
    schema = json.loads((ROOT / "schemas/aura_spatial_import_receipt.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert validate_spatial_import_receipt_payload(payload) == first.receipt


def test_glb_import_uses_declared_local_bin_chunk():
    document = json.loads(FIXTURE.read_text())
    data_uri = document["buffers"][0].pop("uri")
    binary = base64.b64decode(data_uri.split(",", 1)[1])
    json_chunk = json.dumps(document, separators=(",", ":")).encode()
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    binary += b"\x00" * ((4 - len(binary) % 4) % 4)
    length = 12 + 8 + len(json_chunk) + 8 + len(binary)
    glb = (
        b"glTF"
        + struct.pack("<II", 2, length)
        + struct.pack("<II", len(json_chunk), 0x4E4F534A)
        + json_chunk
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )
    result = import_gltf_bytes(glb, provenance_refs=("fixture:glb",))
    assert result.receipt.source_format.value == "GLB"
    assert result.indices == (0, 1, 2)


def test_gltf_rejects_remote_uri_duplicate_keys_and_executable_surfaces():
    document = json.loads(FIXTURE.read_text())
    document["buffers"][0]["uri"] = "https://example.invalid/mesh.bin"
    with pytest.raises(ValueError, match="data URI"):
        import_gltf_bytes(json.dumps(document).encode(), provenance_refs=("fixture",))
    with pytest.raises(ValueError, match="duplicate"):
        import_gltf_bytes(b'{"asset":{"version":"2.0"},"asset":{}}', provenance_refs=("fixture",))
    unsafe = json.loads(FIXTURE.read_text())
    unsafe["extras"] = {"script": "alert(1)"}
    with pytest.raises(ValueError, match="prohibited"):
        import_gltf_bytes(json.dumps(unsafe).encode(), provenance_refs=("fixture",))


def test_gltf_rejects_extensions_and_undecoded_attributes():
    extension = json.loads(FIXTURE.read_text())
    extension["extensionsUsed"] = ["KHR_draco_mesh_compression"]
    with pytest.raises(ValueError, match="extensions"):
        import_gltf_bytes(json.dumps(extension).encode(), provenance_refs=("fixture",))

    attribute = json.loads(FIXTURE.read_text())
    attribute["meshes"][0]["primitives"][0]["attributes"]["NORMAL"] = 0
    with pytest.raises(ValueError, match="POSITION"):
        import_gltf_bytes(json.dumps(attribute).encode(), provenance_refs=("fixture",))


def test_local_gltf_read_rejects_identity_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import os

    path = tmp_path / "mesh.gltf"
    path.write_bytes(FIXTURE.read_bytes())
    real_fstat = os.fstat
    calls = 0

    def mutate_before_final_identity_check(descriptor: int):
        nonlocal calls
        calls += 1
        if calls == 2:
            path.write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
        return real_fstat(descriptor)

    monkeypatch.setattr(os, "fstat", mutate_before_final_identity_check)
    with pytest.raises(ValueError, match="changed while being read"):
        import_gltf_file(path, provenance_refs=("fixture",), root=tmp_path)


def test_import_receipt_runtime_validation_rejects_nested_key_drift():
    result = import_gltf_file(FIXTURE, provenance_refs=("fixture:gltf",), root=ROOT)
    payload = result.receipt.to_dict()
    payload["primitives"][0]["unexpected"] = True
    with pytest.raises(ValueError, match=r"primitive.*keys mismatch"):
        validate_spatial_import_receipt_payload(payload)

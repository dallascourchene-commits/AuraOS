from __future__ import annotations

import base64
import json
import math
import struct

import pytest

from aura_spatial_importers.gaussian_gltf import (
    KHR_GAUSSIAN_PROFILE,
    import_gaussian_gltf_bytes,
)


def gaussian_gltf(
    *,
    include_color: bool = True,
    required: list[str] | None = None,
    mode: int = 0,
    scale: tuple[float, float, float] = (1.0, 2.0, 3.0),
    position: tuple[float, float, float] = (1.0, 2.0, 3.0),
    extension: dict | None = None,
) -> bytes:
    chunks: list[bytes] = []
    views: list[dict] = []
    accessors: list[dict] = []

    def add(data: bytes, *, component: int, count: int, kind: str, normalized: bool = False) -> int:
        offset = sum(len(item) for item in chunks)
        chunks.append(data)
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data)})
        accessor = {
            "bufferView": len(views) - 1,
            "componentType": component,
            "count": count,
            "type": kind,
        }
        if normalized:
            accessor["normalized"] = True
        accessors.append(accessor)
        return len(accessors) - 1

    attrs = {
        "POSITION": add(struct.pack("<3f", *position), component=5126, count=1, kind="VEC3"),
        "KHR_gaussian_splatting:ROTATION": add(
            struct.pack("<4b", 0, 0, 0, 127), component=5120, count=1, kind="VEC4", normalized=True
        ),
        "KHR_gaussian_splatting:SCALE": add(struct.pack("<3f", *scale), component=5126, count=1, kind="VEC3"),
        "KHR_gaussian_splatting:OPACITY": add(b"\x80", component=5121, count=1, kind="SCALAR", normalized=True),
        "KHR_gaussian_splatting:SH_DEGREE_0_COEF_0": add(
            struct.pack("<3f", 0.1, 0.2, 0.3), component=5126, count=1, kind="VEC3"
        ),
    }
    if include_color:
        attrs["COLOR_0"] = add(bytes((255, 128, 0, 255)), component=5121, count=1, kind="VEC4", normalized=True)
    buffer = b"".join(chunks)
    ext = extension or {
        "kernel": "ellipse",
        "colorSpace": "lin_rec709_display",
        "projection": "perspective",
        "sortingMethod": "cameraDistance",
    }
    document = {
        "asset": {"version": "2.0"},
        "extensionsUsed": ["KHR_gaussian_splatting"],
        "extensionsRequired": required if required is not None else ["KHR_gaussian_splatting"],
        "buffers": [
            {
                "byteLength": len(buffer),
                "uri": "data:application/octet-stream;base64," + base64.b64encode(buffer).decode("ascii"),
            }
        ],
        "bufferViews": views,
        "accessors": accessors,
        "meshes": [
            {
                "primitives": [
                    {
                        "mode": mode,
                        "attributes": attrs,
                        "extensions": {"KHR_gaussian_splatting": ext},
                    }
                ]
            }
        ],
    }
    return json.dumps(document, separators=(",", ":"), allow_nan=True).encode()


def test_gaussian_gltf_release_candidate_profile_and_declared_point_fallback() -> None:
    result = import_gaussian_gltf_bytes(gaussian_gltf(), provenance_refs=("fixture:khr",))
    assert result.receipt.asset_type == "GAUSSIAN_SPLATS"
    assert result.positions == ((1.0, 2.0, 3.0),)
    assert result.colors_rgba == ((255, 128, 0, 255),)
    assert result.gaussian_splats is not None
    assert result.gaussian_splats.rotations_xyzw[0] == pytest.approx((0.0, 0.0, 0.0, 1.0))
    assert result.gaussian_splats.scales_xyz == ((1.0, 2.0, 3.0),)
    assert result.gaussian_splats.opacities == pytest.approx((128 / 255.0,))
    assert result.metadata["extension_profile"] == KHR_GAUSSIAN_PROFILE
    assert result.metadata["fallback_modes"] == ("DECLARED_COLOR_0",)
    assert result.metadata["gaussian_color_space"] == "lin_rec709_display"
    assert len(result.metadata["representation_digest"]) == 64
    assert result.metadata["representation_bytes_per_splat"] == 60
    assert result.metadata["sh_degree"] == 0
    assert result.receipt.training_invoked is False


def test_gaussian_gltf_derives_bounded_placeholder_fallback_from_sh0() -> None:
    result = import_gaussian_gltf_bytes(gaussian_gltf(include_color=False), provenance_refs=("fixture",))
    assert result.metadata["fallback_modes"] == ("BOUNDED_SH0_PLACEHOLDER",)
    assert len(result.colors_rgba) == 1
    assert any("derived from SH" in warning for warning in result.receipt.warnings)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"required": ["KHR_gaussian_splatting", "EXT_unknown"]}, "unknown mandatory"),
        ({"mode": 4}, "POINTS"),
        ({"scale": (-1.0, 1.0, 1.0)}, "non-negative"),
        ({"position": (math.nan, 0.0, 0.0)}, "finite"),
        ({"extension": {"kernel": "box", "colorSpace": "lin_rec709_display"}}, "kernel"),
        ({"extension": {"kernel": "ellipse", "colorSpace": "unknown"}}, "colorSpace"),
        (
            {
                "extension": {
                    "kernel": "ellipse",
                    "colorSpace": "lin_rec709_display",
                    "extensions": {"EXT_unknown": {}},
                }
            },
            "nested",
        ),
    ],
)
def test_gaussian_gltf_rejects_unnegotiated_or_invalid_semantics(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        import_gaussian_gltf_bytes(gaussian_gltf(**kwargs), provenance_refs=("fixture",))


def test_gaussian_gltf_rejects_runtime_expansion_before_accessor_read() -> None:
    document = json.loads(gaussian_gltf())
    for accessor in document["accessors"]:
        accessor["count"] = 60_000
    with pytest.raises(ValueError, match="runtime allocation"):
        import_gaussian_gltf_bytes(
            json.dumps(document, separators=(",", ":")).encode(),
            provenance_refs=("fixture",),
        )


def test_gaussian_gltf_rejects_unknown_profile_before_decode() -> None:
    with pytest.raises(ValueError, match="compatibility profile"):
        import_gaussian_gltf_bytes(
            gaussian_gltf(),
            provenance_refs=("fixture",),
            extension_profile="future",
        )


def test_gaussian_gltf_rejects_material_and_mesh_extension_semantics() -> None:
    material_document = json.loads(gaussian_gltf())
    material_document["materials"] = [{"name": "not-admitted"}]
    with pytest.raises(ValueError, match="materials"):
        import_gaussian_gltf_bytes(json.dumps(material_document).encode(), provenance_refs=("fixture",))

    mesh_extension_document = json.loads(gaussian_gltf())
    mesh_extension_document["meshes"][0]["extensions"] = {"EXT_unknown": {}}
    with pytest.raises(ValueError, match="mesh-level"):
        import_gaussian_gltf_bytes(json.dumps(mesh_extension_document).encode(), provenance_refs=("fixture",))

    primitive_material_document = json.loads(gaussian_gltf())
    primitive_material_document["meshes"][0]["primitives"][0]["material"] = 0
    with pytest.raises(ValueError, match="unmaterialed"):
        import_gaussian_gltf_bytes(json.dumps(primitive_material_document).encode(), provenance_refs=("fixture",))


def test_gaussian_gltf_rejects_mixed_primitive_color_spaces() -> None:
    document = json.loads(gaussian_gltf())
    second = json.loads(json.dumps(document["meshes"][0]["primitives"][0]))
    second["extensions"]["KHR_gaussian_splatting"]["colorSpace"] = "srgb_rec709_display"
    document["meshes"][0]["primitives"].append(second)
    with pytest.raises(ValueError, match="common colorSpace"):
        import_gaussian_gltf_bytes(json.dumps(document).encode(), provenance_refs=("fixture",))

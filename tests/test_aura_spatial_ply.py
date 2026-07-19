from __future__ import annotations

from pathlib import Path
import struct

import pytest

from aura_spatial_coordinate_frames import apply_coordinate_conversion, compile_coordinate_conversion_matrix
from aura_spatial_importers.contracts import CoordinateConversion
from aura_spatial_importers.ply import import_ply_bytes, import_ply_file

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/spatial/ply/points_ascii.ply"


def test_ascii_ply_requires_explicit_basis_and_imports_point_cloud():
    conversion = CoordinateConversion("RIGHT_HANDED", "Z_UP", 0.01)
    result = import_ply_file(FIXTURE, provenance_refs=("fixture:ply",), coordinate_conversion=conversion, root=ROOT)
    assert result.receipt.source_format.value == "PLY_ASCII"
    assert result.receipt.asset_type == "POINT_CLOUD"
    assert result.positions[1] == (0.01, 0.0, 0.0)
    assert result.positions[2] == (0.0, 0.0, -0.01)
    assert result.colors_rgba[0] == (255, 0, 255, 255)
    assert result.receipt.network_fetch_performed is False


def test_binary_little_endian_ply_is_bounded_and_deterministic():
    header = b"ply\nformat binary_little_endian 1.0\nelement vertex 2\nproperty float x\nproperty float y\nproperty float z\nend_header\n"
    payload = struct.pack("<6f", 0, 0, 0, 1, 2, 3)
    conversion = CoordinateConversion("RIGHT_HANDED", "Y_UP", 1.0)
    result = import_ply_bytes(
        header + payload, provenance_refs=("fixture:binary-ply",), coordinate_conversion=conversion
    )
    assert result.receipt.source_format.value == "PLY_BINARY_LE"
    assert result.positions[-1] == (1.0, 2.0, 3.0)


def test_ply_rejects_faces_nan_and_implicit_conversion():
    face = b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\nproperty float z\nelement face 1\nproperty list uchar int vertex_indices\nend_header\n0 0 0\n3 0 0 0\n"
    conversion = CoordinateConversion("RIGHT_HANDED", "Y_UP", 1.0)
    with pytest.raises(ValueError, match="point-cloud"):
        import_ply_bytes(face, provenance_refs=("fixture",), coordinate_conversion=conversion)
    nan = b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\nproperty float z\nend_header\nnan 0 0\n"
    with pytest.raises(ValueError, match="finite"):
        import_ply_bytes(nan, provenance_refs=("fixture",), coordinate_conversion=conversion)
    with pytest.raises(ValueError, match="explicit"):
        import_ply_bytes(FIXTURE.read_bytes(), provenance_refs=("fixture",), coordinate_conversion=None)  # type: ignore[arg-type]


def test_ply_rejects_non_uint8_color_properties():
    source = b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\nproperty float z\nproperty float red\nproperty float green\nproperty float blue\nend_header\n0 0 0 1 0 1\n"
    conversion = CoordinateConversion("RIGHT_HANDED", "Y_UP", 1.0)
    with pytest.raises(ValueError, match="unsigned 8-bit"):
        import_ply_bytes(
            source,
            provenance_refs=("fixture",),
            coordinate_conversion=conversion,
        )


def test_x_up_conversion_maps_source_up_to_positive_y():
    matrix = compile_coordinate_conversion_matrix(
        source_handedness="RIGHT_HANDED",
        source_up_axis="X_UP",
        source_meters_per_unit=1.0,
    )
    assert apply_coordinate_conversion((1.0, 0.0, 0.0), matrix) == (0.0, 1.0, 0.0)

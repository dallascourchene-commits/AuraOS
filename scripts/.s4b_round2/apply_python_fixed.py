from pathlib import Path

contracts = Path("aura_spatial_importers/contracts.py")
s = contracts.read_text(encoding="utf-8")
needle = '_GAUSSIAN_RENDER_DIGEST_VERSION = b"AURA_GAUSSIAN_RENDER_PROJECTION_V1\\0"\n\n\n'
insert = '''_GAUSSIAN_RENDER_DIGEST_VERSION = b"AURA_GAUSSIAN_RENDER_PROJECTION_V1\\0"\n\n\ndef _strict_digest_tuple(values: Sequence[Any], length: int, field_name: str) -> tuple[float, ...]:\n    if isinstance(values, (str, bytes, bytearray)) or len(values) != length:\n        raise ValueError(f"{field_name} must contain {length} finite numbers")\n    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in values):\n        raise ValueError(f"{field_name} must contain numeric values without coercion")\n    result = tuple(float(item) for item in values)\n    if not all(math.isfinite(item) for item in result):\n        raise ValueError(f"{field_name} must contain finite numbers")\n    return result\n\n\n'''
if needle not in s:
    raise SystemExit("digest version marker missing")
s = s.replace(needle, insert, 1)
s = s.replace(
    '_finite_tuple(positions[index], 3, f"gaussian digest position {index}")',
    '_strict_digest_tuple(positions[index], 3, f"gaussian digest position {index}")',
)
s = s.replace(
    '_finite_tuple(rotations_xyzw[index], 4, f"gaussian digest rotation {index}")',
    '_strict_digest_tuple(rotations_xyzw[index], 4, f"gaussian digest rotation {index}")',
)
s = s.replace(
    '_finite_tuple(scales_xyz[index], 3, f"gaussian digest scale {index}")',
    '_strict_digest_tuple(scales_xyz[index], 3, f"gaussian digest scale {index}")',
)
s = s.replace(
    '''        opacity = float(opacities[index])
        if not math.isfinite(opacity) or not 0.0 <= opacity <= 1.0:
''',
    '''        raw_opacity = opacities[index]
        if isinstance(raw_opacity, bool) or not isinstance(raw_opacity, (int, float)):
            raise ValueError("gaussian digest opacity must be numeric without coercion")
        opacity = float(raw_opacity)
        if not math.isfinite(opacity) or not 0.0 <= opacity <= 1.0:
''',
    1,
)
s = s.replace(
    '''        color = tuple(int(value) for value in colors_rgba[index])
        if len(color) != 4 or any(value < 0 or value > 255 for value in color):
''',
    '''        raw_color = colors_rgba[index]
        if (
            isinstance(raw_color, (str, bytes, bytearray))
            or len(raw_color) != 4
            or any(isinstance(value, bool) or not isinstance(value, int) for value in raw_color)
        ):
            raise ValueError("gaussian digest colors must be RGBA8 integers without coercion")
        color = tuple(raw_color)
        if any(value < 0 or value > 255 for value in color):
''',
    1,
)
contracts.write_text(s, encoding="utf-8")

py_test = Path("tests/test_aura_spatial_gaussian_gltf.py")
t = py_test.read_text(encoding="utf-8")
marker = "test_gaussian_render_digest_rejects_cross_language_numeric_coercion"
if marker in t:
    raise SystemExit("Python coercion regression already present")
t += '''\n\n@pytest.mark.parametrize(\n    ("field", "replacement"),\n    [\n        ("positions", ((True, 0.0, 0.0),)),\n        ("rotations_xyzw", ((0.0, 0.0, 0.0, "1.0"),)),\n        ("scales_xyz", ((1.0, False, 1.0),)),\n        ("opacities", (True,)),\n        ("colors_rgba", ((255.0, 0, 255, 255),)),\n    ],\n)\ndef test_gaussian_render_digest_rejects_cross_language_numeric_coercion(field: str, replacement) -> None:\n    values = {\n        "positions": ((0.0, 0.0, 0.0),),\n        "rotations_xyzw": ((0.0, 0.0, 0.0, 1.0),),\n        "scales_xyz": ((1.0, 1.0, 1.0),),\n        "opacities": (1.0,),\n        "colors_rgba": ((255, 0, 255, 255),),\n    }\n    values[field] = replacement\n    with pytest.raises(ValueError, match=r"without coercion|RGBA8"):\n        gaussian_render_representation_digest(**values)\n'''
py_test.write_text(t, encoding="utf-8")

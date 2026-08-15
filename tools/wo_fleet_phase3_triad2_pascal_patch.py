from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_pascal_spatial_presentation_part5.py"

ANCHOR = '''    scene = _load_json_object(scene_path, "Pascal fixture scene")
    manifest = PascalSceneArtifactManifest.from_mapping(
        _load_json_object(manifest_path, "Pascal artifact manifest")
    )
    coordinate = AuraPascalCoordinateReceipt.from_mapping(
        _load_json_object(coordinate_path, "Pascal coordinate receipt")
    )
'''

REPLACEMENT = '''    scene = _load_json_object(scene_path, "Pascal fixture scene")
    manifest = PascalSceneArtifactManifest.from_mapping(
        _load_json_object(manifest_path, "Pascal artifact manifest")
    )
    coordinate_mapping = _load_json_object(
        coordinate_path, "Pascal coordinate receipt"
    )
    # Cross-artifact authority is checked before the receipt's self-digest so a
    # tampered binding fails at the contract boundary it violates.  Receipt
    # construction still performs the independent self-digest validation next.
    if coordinate_mapping.get("pascal_artifact_digest") != manifest.artifact_digest:
        raise PascalPresentationError(
            "coordinate receipt pascal_artifact_digest does not match manifest artifact_digest"
        )
    coordinate = AuraPascalCoordinateReceipt.from_mapping(coordinate_mapping)
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"Pascal coordinate validation-order anchor expected once, found {count}")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    print("Phase-3 Pascal cross-artifact validation-order repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import copy
import json
from pathlib import Path

from tools.arena.k27_memory_city_spatial_seam.k27_memory_city_spatial_seam import (
    SCENE_SOURCE_SHA256,
    SeamDisposition,
    validate_spatial_seam,
)

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / ".aura" / "arena_routes" / "spatial.v1.json"


def _manifest():
    return {
        "files": {
            "k27_memory/cold_sources/MC-SRC-O1O9.md": {
                "sha256": SCENE_SOURCE_SHA256,
            }
        }
    }


def _route():
    return json.loads(ROUTE.read_text(encoding="utf-8"))


def _binding(route):
    return next(
        t for t in route["transitions"]
        if t["transition_id"] == "SPATIAL.GROUND.COMPILE_SCENE"
    )["memory_city_binding"]


def _validate_with_nonfinite(value):
    route = copy.deepcopy(_route())
    # Replace a normally string-valued governed field so the binding keyset stays exact;
    # permissive JSON serialization would otherwise emit NaN/Infinity here.
    _binding(route)["scene_schema"] = value
    encoded = json.dumps(route, separators=(",", ":"), allow_nan=True).encode()
    return validate_spatial_seam(encoded, _manifest())


def test_nan_binding_holds_without_canonical_root():
    receipt = _validate_with_nonfinite(float("nan"))
    assert receipt.disposition is SeamDisposition.HOLD
    assert "BINDING_CANONICALIZATION_INVALID" in receipt.reasons
    assert receipt.binding_root is None
    assert receipt.authority_minted is False
    assert receipt.gate10 is False


def test_positive_infinity_binding_holds_without_canonical_root():
    receipt = _validate_with_nonfinite(float("inf"))
    assert receipt.disposition is SeamDisposition.HOLD
    assert "BINDING_CANONICALIZATION_INVALID" in receipt.reasons
    assert receipt.binding_root is None


def test_negative_infinity_binding_holds_without_canonical_root():
    receipt = _validate_with_nonfinite(float("-inf"))
    assert receipt.disposition is SeamDisposition.HOLD
    assert "BINDING_CANONICALIZATION_INVALID" in receipt.reasons
    assert receipt.binding_root is None

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import unittest

from k27_memory_city_spatial_seam import (
    ADAPTERS,
    ARCHIVE_SHA256,
    READ_APIS,
    SCENE_SCHEMA,
    SCENE_SOURCE_SHA256,
    SeamDisposition,
    validate_spatial_seam,
)

ROOT = Path(__file__).resolve().parents[3]
ROUTE = ROOT / ".aura" / "arena_routes" / "spatial.v1.json"


def load_route():
    return json.loads(ROUTE.read_text(encoding="utf-8"))


def load_manifest():
    return {"files":{"k27_memory/cold_sources/MC-SRC-O1O9.md":{"sha256":SCENE_SOURCE_SHA256}}}


def compile_transition(route):
    return next(t for t in route["transitions"] if t["transition_id"] == "SPATIAL.GROUND.COMPILE_SCENE")


def decision(route, manifest=None):
    return validate_spatial_seam(
        json.dumps(route, separators=(",", ":")).encode(),
        load_manifest() if manifest is None else manifest,
    )


class SpatialSeamTests(unittest.TestCase):
    def test_candidate_route_is_ready_for_independent_review(self):
        r = validate_spatial_seam(ROUTE.read_bytes(), load_manifest())
        self.assertEqual(r.disposition, SeamDisposition.READY_FOR_INDEPENDENT_REVIEW)
        self.assertEqual(r.reasons, ())
        self.assertFalse(r.authority_minted)
        self.assertFalse(r.gate10)

    def test_exact_three_adapter_contract(self):
        r = validate_spatial_seam(ROUTE.read_bytes(), load_manifest())
        self.assertEqual(r.adapters, ADAPTERS)
        self.assertEqual(r.adapters, ("desktop_webgl", "webxr", "openxr"))

    def test_exact_six_review_only_apis(self):
        b = compile_transition(load_route())["memory_city_binding"]
        self.assertEqual(set(b["read_apis"]), set(READ_APIS))
        self.assertTrue(all(v == "REVIEW_ONLY" for v in b["read_apis"].values()))

    def test_scene_schema_is_pinned(self):
        self.assertEqual(compile_transition(load_route())["memory_city_binding"]["scene_schema"], SCENE_SCHEMA)

    def test_archive_digest_is_pinned(self):
        self.assertEqual(compile_transition(load_route())["memory_city_binding"]["provenance_archive_sha256"], ARCHIVE_SHA256)

    def test_scene_source_digest_matches_manifest(self):
        manifest = load_manifest()
        self.assertEqual(manifest["files"]["k27_memory/cold_sources/MC-SRC-O1O9.md"]["sha256"], SCENE_SOURCE_SHA256)

    def test_missing_binding_holds(self):
        route = load_route(); compile_transition(route).pop("memory_city_binding")
        self.assertEqual(decision(route).disposition, SeamDisposition.HOLD)

    def test_wrong_source_root_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["source_root"] = "outputs/other/"
        self.assertIn("SOURCE_ROOT_MISMATCH", decision(route).reasons)

    def test_wrong_archive_digest_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["provenance_archive_sha256"] = "0" * 64
        self.assertIn("ARCHIVE_DIGEST_MISMATCH", decision(route).reasons)

    def test_wrong_scene_source_digest_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["scene_source_sha256"] = "0" * 64
        self.assertIn("SCENE_SOURCE_DIGEST_MISMATCH", decision(route).reasons)

    def test_wrong_scene_schema_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["scene_schema"] = "OTHER"
        self.assertIn("SCENE_SCHEMA_MISMATCH", decision(route).reasons)

    def test_adapter_loss_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["adapters"] = ["desktop_webgl", "webxr"]
        self.assertIn("ADAPTER_SET_OR_ORDER_MISMATCH", decision(route).reasons)

    def test_adapter_substitution_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["adapters"][2] = "openvr"
        self.assertIn("ADAPTER_SET_OR_ORDER_MISMATCH", decision(route).reasons)

    def test_adapter_reordering_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["adapters"].reverse()
        self.assertIn("ADAPTER_SET_OR_ORDER_MISMATCH", decision(route).reasons)

    def test_projection_law_loss_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["projection_laws"].pop()
        self.assertIn("PROJECTION_LAWS_MISMATCH", decision(route).reasons)

    def test_unknown_api_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["read_apis"]["CITY_EXECUTE"] = "REVIEW_ONLY"
        self.assertIn("READ_API_SET_MISMATCH", decision(route).reasons)

    def test_api_escalation_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["read_apis"]["CITY_ROUTE"] = "EXECUTE"
        self.assertIn("CITY_ROUTE_NOT_REVIEW_ONLY", decision(route).reasons)

    def test_projection_only_false_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["projection_only"] = False
        self.assertIn("PROJECTION_ONLY_REQUIRED", decision(route).reasons)

    def test_binding_execution_authority_true_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["execution_authority"] = True
        self.assertIn("BINDING_EXECUTION_AUTHORITY_MUST_BE_FALSE", decision(route).reasons)

    def test_binding_effect_authority_true_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["effect_authority"] = True
        self.assertIn("BINDING_EFFECT_AUTHORITY_MUST_BE_FALSE", decision(route).reasons)

    def test_binding_renderer_authority_true_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["renderer_authority"] = True
        self.assertIn("BINDING_RENDERER_AUTHORITY_MUST_BE_FALSE", decision(route).reasons)

    def test_gate10_true_holds(self):
        route = load_route(); compile_transition(route)["memory_city_binding"]["gate10"] = True
        self.assertIn("BINDING_GATE10_MUST_BE_FALSE", decision(route).reasons)

    def test_route_execution_authority_true_holds(self):
        route = load_route(); route["authority"]["execution_authority"] = True
        self.assertIn("ROUTE_EXECUTION_AUTHORITY_MUST_BE_FALSE", decision(route).reasons)

    def test_route_renderer_authority_true_holds(self):
        route = load_route(); route["authority"]["renderer_authority"] = True
        self.assertIn("ROUTE_RENDERER_AUTHORITY_MUST_BE_FALSE", decision(route).reasons)

    def test_route_auto_merge_true_holds(self):
        route = load_route(); route["authority"]["automatic_merge"] = True
        self.assertIn("ROUTE_AUTOMATIC_MERGE_MUST_BE_FALSE", decision(route).reasons)

    def test_route_vsa_patch_authority_true_holds(self):
        route = load_route(); route["authority"]["vsa_patch_authority"] = True
        self.assertIn("ROUTE_VSA_PATCH_AUTHORITY_MUST_BE_FALSE", decision(route).reasons)

    def test_route_patch_authority_drift_holds(self):
        route = load_route(); route["authority"]["patch_authority"] = "anything"
        self.assertIn("ROUTE_PATCH_AUTHORITY_MISMATCH", decision(route).reasons)

    def test_route_unknown_authority_fields_hold(self):
        for key, value in (("effect_authority",False),("gate10",False),("authority_minted",False)):
            with self.subTest(key=key):
                route = load_route(); route["authority"][key] = value
                self.assertIn("ROUTE_AUTHORITY_KEYSET_MISMATCH", decision(route).reasons)

    def test_route_missing_authority_field_holds(self):
        route = load_route(); route["authority"].pop("automatic_merge")
        self.assertIn("ROUTE_AUTHORITY_KEYSET_MISMATCH", decision(route).reasons)

    def test_provenance_manifest_drift_holds(self):
        manifest = deepcopy(load_manifest())
        manifest["files"]["k27_memory/cold_sources/MC-SRC-O1O9.md"]["sha256"] = "f" * 64
        self.assertIn("PROVENANCE_SCENE_SOURCE_NOT_PINNED", decision(load_route(), manifest).reasons)

    def test_invalid_route_json_holds(self):
        r = validate_spatial_seam(b"{", load_manifest())
        self.assertEqual(r.disposition, SeamDisposition.HOLD)
        self.assertIn("ROUTE_JSON_INVALID", r.reasons)


if __name__ == "__main__":
    unittest.main()

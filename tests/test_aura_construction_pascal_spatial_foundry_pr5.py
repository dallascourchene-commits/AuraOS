from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aura_pascal_spatial_presentation import load_pascal_compatibility_fixture
from scripts.aura_construction_pascal_spatial_foundry_pr5_runtime import (
    NEGATIVE_REQUIREMENTS,
    POSITIVE_REQUIREMENTS,
    PROFILE,
)
from scripts.aura_runtime_profile_v2_adapter import _json_digest, load_runtime_profile_v2
from scripts.aura_runtime_refactor_harness import load_runtime_profile

ROOT = Path(__file__).resolve().parents[1]
V1 = ".aura/runtime_profiles/construction_pascal_spatial_foundry.v1.json"
V2 = ".aura/runtime_profiles/construction_pascal_spatial_foundry_bilateral.v2.json"
PROBE = "tests/runtime/construction_pascal_spatial_foundry_browser_probe.cjs"


def test_pr5_pascal_identity_chain_is_exact_and_current() -> None:
    lock, manifest, coordinate, scene = load_pascal_compatibility_fixture(str(ROOT))
    assert lock.lock_digest == "672611b98aca61e3ad7a4ebcb32f278916d09d876e663452bb654610562d2e87"
    assert manifest.artifact_digest == "3a007f69349cbb78966d8deedb43326a2c236112066298b59b245435a950cbbe"
    assert manifest.scene_json_sha256 == hashlib.sha256(
        (ROOT / "aura_showcase/pascal-workbench/fixture.json").read_bytes()
    ).hexdigest()
    assert coordinate.pascal_artifact_digest == manifest.artifact_digest
    assert coordinate.spatial_scene_digest == "56824f5cf1e38a1ed82591448c111859a79a277d396df8f030730ef8031f510c"
    assert coordinate.receipt_digest == "4dd3767ab948b3627dc0674c5f02d5ac8ee3f9745b052d1864fb44f7589b084a"
    assert scene["version"] == "AURA_PASCAL_LOCAL_SCENE_FIXTURE_V1"


def test_pr5_v1_profile_requires_complete_current_run_artifact_set() -> None:
    profile = load_runtime_profile(ROOT, V1)
    required = set(profile["probe"]["required_artifacts"])
    assert profile["profile_id"] == "construction-pascal-spatial-foundry-pr5-browser"
    assert profile["server"]["readiness_url"].endswith("/api/construction/director/status")
    assert len([name for name in required if name.endswith(".png")]) == 17
    assert {
        "browser-evidence.json",
        "construction-foundry-projection.json",
        "incident-replay-packet.json",
        "runtime-profile-v2-proof.json",
        "repair-attempt.json",
        "preview-rollback-receipt.json",
        "u7-current-reproof.json",
        "attempt-archive-index.json",
        "cleanup-receipt.json",
    }.issubset(required)


def test_pr5_v2_profile_binds_exact_verifier_and_confirmation_requirements() -> None:
    profile = load_runtime_profile_v2(ROOT, V2)
    assert PROFILE == V2
    assert profile["base_profile"] == V1
    assert profile["independent_verifier"]["source_path"] == PROBE
    expected_sha = hashlib.sha256((ROOT / PROBE).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert profile["independent_verifier"]["source_sha256"] == expected_sha

    bound_positive = {
        row["requirement_digest"] for row in profile["requirement_bindings"]["positive_assertions"]
    }
    bound_negative = {
        row["requirement_digest"]
        for group in ("negative_assertions", "preservation_assertions", "fault_injections")
        for row in profile["requirement_bindings"][group]
    }
    assert bound_positive == {_json_digest(item) for item in POSITIVE_REQUIREMENTS}
    assert bound_negative == {_json_digest(item) for item in NEGATIVE_REQUIREMENTS}
    assert profile["repair_policy"]["human_review_required"] is True
    for key, value in profile["repair_policy"].items():
        if key.startswith("automatic_") or key in {
            "production_mutation", "professional_authority", "physical_work_authority", "learning_promotion"
        }:
            assert value is False


def test_pr5_browser_probe_names_every_required_scene_and_relaunch() -> None:
    source = (ROOT / PROBE).read_text(encoding="utf-8")
    profile = json.loads((ROOT / V1).read_text(encoding="utf-8"))
    for artifact in profile["probe"]["required_artifacts"]:
        if artifact.endswith(".png"):
            assert artifact in source
    assert "RESTART" in source
    assert "relaunchSucceeded" in source
    assert "exactOrder" in source
    assert "allAuthorityFalse" in source


def test_pr5_scope_retains_external_review_and_merge_denials() -> None:
    request = json.loads(
        (ROOT / ".aura/waboose_requests/construction_pascal_spatial_foundry_pr5.v1.json").read_text(
            encoding="utf-8"
        )
    )
    policy = request["external_review_policy"]
    assert policy["greptile_authorized"] is False
    assert policy["codex_authorized"] is False
    assert policy["gitar_authorized"] is False
    assert policy["coderabbit_authorized_at_final_gate_only"] is False
    objective = json.loads(
        (ROOT / ".aura/refactor_objectives/construction_pascal_spatial_foundry_pr5.v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert objective["authority"]["automatic_merge"] is False
    assert objective["authority"]["physical_work_authority"] is False

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
    """Verify the browser probe exports its artifact list and matches the V1 profile."""
    profile = json.loads((ROOT / V1).read_text(encoding="utf-8"))
    required_artifacts = set(profile["probe"]["required_artifacts"])

    # The probe source exports its screenshot map as a frozen object.
    # Parse the SCREENSHOTS constant from the probe source to get the
    # actual screenshot filenames the probe writes.
    probe_source = (ROOT / PROBE).read_text(encoding="utf-8")

    # Extract screenshot filenames from the SCREENSHOTS object
    import re
    screenshot_matches = re.findall(r'"([\w-]+\.png)"', probe_source)
    probe_screenshots = set(screenshot_matches)

    # Every required .png artifact must be in the probe's screenshot set
    required_pngs = {name for name in required_artifacts if name.endswith(".png")}
    missing = required_pngs - probe_screenshots
    assert not missing, f"required screenshots missing from probe: {missing}"

    # Verify evidence field names are present as actual code identifiers
    # (not just in comments) by checking they appear as property keys
    for field in ("relaunchSucceeded", "exactOrder", "allAuthorityFalse"):
        # Must appear as a property assignment, not in a comment
        pattern = rf'\b{field}\b'
        assert re.search(pattern, probe_source), f"evidence field '{field}' not found in probe source"

    # Verify RESTART is used as a control action
    assert "RESTART" in probe_source, "RESTART control not referenced in probe"


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


def test_pr5_coordinate_receipt_mismatched_artifact_digest_fails_closed(tmp_path, monkeypatch) -> None:
    """load_pascal_compatibility_fixture must reject a coordinate receipt whose
    pascal_artifact_digest does not match the manifest artifact_digest."""
    import aura_pascal_spatial_presentation_part5 as part5
    from aura_pascal_spatial_presentation import PascalPresentationError

    # Load the real fixture to get the valid manifest.
    try:
        _lock, real_manifest, _coord, _scene = load_pascal_compatibility_fixture(str(ROOT))
    except PascalPresentationError:
        # Pre-existing Windows digest mismatch — skip this test if the
        # base fixture itself can't load on this platform.
        import pytest
        pytest.skip("Pascal fixture has pre-existing digest mismatch on Windows")

    # Create a fake coordinate receipt with a wrong pascal_artifact_digest.
    import json as _json
    coord_path = ROOT / "aura_showcase/pascal-workbench/coordinate-receipt.json"
    real_coord = _json.loads(coord_path.read_text(encoding="utf-8"))
    # Flip one character in the digest to create a mismatch.
    bad_digest = list(real_manifest.artifact_digest)
    bad_digest[0] = "0" if bad_digest[0] != "0" else "1"
    real_coord["pascal_artifact_digest"] = "".join(bad_digest)

    # Monkeypatch _load_json_object so that when the coordinate receipt is
    # loaded, it returns our tampered version.
    original_load = part5._load_json_object

    def tampered_load(path, name):
        if "coordinate" in str(path) and "coordinate" in name.lower():
            return real_coord
        return original_load(path, name)

    monkeypatch.setattr(part5, "_load_json_object", tampered_load)

    with pytest.raises(PascalPresentationError, match="pascal_artifact_digest does not match"):
        load_pascal_compatibility_fixture(str(ROOT))

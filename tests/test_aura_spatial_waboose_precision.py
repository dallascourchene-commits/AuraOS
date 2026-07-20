from __future__ import annotations

import ast
from dataclasses import replace

import pytest

from aura_coding_waboose_review_learning import scan_python_review_lessons
from aura_review_lessons_security import (
    detect_protected_metadata_overrides,
    detect_uri_alias_encoding,
)
from aura_spatial_construction import project_construction_state_to_scene
from tests.test_aura_spatial_s6_construction import _fixture_packet, _floor_asset


def test_review_lesson_uri_detector_ignores_canonical_scheme_prefix_tokens() -> None:
    assert detect_uri_alias_encoding("aura://") == []
    assert detect_uri_alias_encoding("file://") == []
    assert detect_uri_alias_encoding("aura:////forged")
    assert detect_uri_alias_encoding("aura://construction/%2fsecret")


def test_review_lesson_authority_detector_accepts_typed_spatial_no_authority_envelope() -> None:
    envelope = {
        "projection_only": True,
        "renderer_authority": False,
        "execution_authority": False,
        "patch_authority": False,
        "production_mutation": False,
    }
    assert detect_protected_metadata_overrides(envelope) == []
    assert detect_protected_metadata_overrides({**envelope, "patch_authority": "full_repository"})
    source = "packet = " + repr(envelope)
    findings = scan_python_review_lessons(file="tests/fixture.py", source=source, tree=ast.parse(source))
    assert not any(item.get("rule") == "detect_protected_metadata_overrides" for item in findings)


@pytest.mark.parametrize(
    "uri",
    [
        "aura:////construction/floor-plan",
        "aura://construction//floor-plan",
        "aura://construction/%2fsecret",
        "aura://construction/../floor-plan",
        "aura://user@construction/floor-plan",
        "aura://construction/floor-plan?token=secret",
        "file://remote-host/tmp/floor.glb",
        "https://example.test/floor.glb",
    ],
)
def test_construction_projection_rejects_noncanonical_floor_asset_uris(uri: str) -> None:
    fixture, packet = _fixture_packet()
    with pytest.raises(ValueError, match=r"(?:URI|local or Aura-addressed|remote host)"):
        project_construction_state_to_scene(
            fixture.state,
            packet,
            purpose_digest="6" * 64,
            floor_plan_assets=(_floor_asset(uri=uri),),
        )


def test_construction_projection_accepts_canonical_aura_and_local_file_uris() -> None:
    fixture, packet = _fixture_packet()
    aura_scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest="7" * 64,
        floor_plan_assets=(_floor_asset(),),
    )
    file_asset = replace(_floor_asset(), uri="file:///tmp/aura/floor.glb")
    file_scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest="8" * 64,
        floor_plan_assets=(file_asset,),
    )
    assert len(aura_scene.assets) == 2
    assert len(file_scene.assets) == 2

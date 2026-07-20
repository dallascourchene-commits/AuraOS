from __future__ import annotations

from dataclasses import replace
import json

import pytest

from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
)
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_event_contracts import stable_digest
from aura_spatial_arena import SpatialPrivacyClass
from aura_spatial_construction import project_construction_state_to_scene
from aura_spatial_contracts import SpatialAssetManifest, SpatialAssetType


def _fixture_packet():
    fixture = build_sco_construction_demo_fixture()
    packet = ConstructionArenaAdapter().build_runtime_packet(
        objective="coordinate safe alternative work",
        state=fixture.state,
        scope=fixture.focus_scope,
        candidates=fixture.candidates,
        now=10.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=fixture.probabilistic_signals,
    )
    return fixture, packet


def _floor_asset(*, privacy: str = "PROJECT", uri: str = "aura://construction/floor-plan") -> SpatialAssetManifest:
    return SpatialAssetManifest(
        asset_id="construction-floor-plan",
        asset_type=SpatialAssetType.MESH,
        uri=uri,
        media_type="model/gltf-binary",
        content_digest="sha256:" + "a" * 64,
        byte_length=1024,
        frame_id="construction-abstract-project",
        bounds_min=(-1.0, 0.0, -1.0),
        bounds_max=(1.0, 0.0, 1.0),
        source_refs=("fixture:construction-floor-plan",),
        metadata={
            "spatial_privacy_class": privacy,
            "survey_authority": False,
            "person_level_data_included": False,
        },
    )


def test_construction_projection_contains_only_abstract_digest_bound_domain_views() -> None:
    fixture, packet = _fixture_packet()
    scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest="b" * 64,
        privacy_class=SpatialPrivacyClass.PROJECT,
    )
    payload = scene.to_dict()
    encoded = json.dumps(payload, sort_keys=True)
    assert f"domain-state:{fixture.state.state_digest}" in payload["source_refs"]
    assert payload["execution_authority"] is False
    assert payload["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert all(item["projection_only"] is True for item in payload["entities"])
    assert all(item["patch_authority"] is False for item in payload["entities"])
    assert "actor_id" not in encoded
    assert "claimant_id" not in encoded
    assert "consent_refs" not in encoded
    assert all("source_ref" not in item["metadata"] for item in payload["entities"])
    assert all("source_ref" not in item["metadata"] for item in payload["assets"])
    assert "payload_digest" not in encoded
    assert "observed_at" not in encoded
    assert "exact_coordinates" not in encoded
    assert 'survey_authority": true' not in encoded.lower()
    assert any(item["metadata"].get("admissible") is False for item in payload["entities"])
    assert any(item["metadata"].get("admissible") is True for item in payload["entities"])


def test_public_projection_hashes_scope_and_candidate_identifiers() -> None:
    fixture, packet = _fixture_packet()
    scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest="c" * 64,
        privacy_class=SpatialPrivacyClass.PUBLIC,
    )
    encoded = json.dumps(scene.to_dict(), sort_keys=True)
    assert fixture.focus_scope.zone_id not in encoded
    assert fixture.focus_scope.work_package_id not in encoded
    for candidate in fixture.candidates:
        assert candidate.candidate_id not in encoded


def test_restricted_projection_is_abstract_and_refuses_floor_plan_geometry() -> None:
    fixture, packet = _fixture_packet()
    scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest="d" * 64,
        privacy_class=SpatialPrivacyClass.RESTRICTED,
    )
    encoded = json.dumps(scene.to_dict(), sort_keys=True)
    assert fixture.state.project_id not in encoded
    assert fixture.focus_scope.zone_id not in encoded
    with pytest.raises(ValueError, match="cannot expose floor-plan geometry"):
        project_construction_state_to_scene(
            fixture.state,
            packet,
            purpose_digest="d" * 64,
            privacy_class=SpatialPrivacyClass.RESTRICTED,
            floor_plan_assets=(_floor_asset(privacy="RESTRICTED"),),
        )


def test_project_floor_plan_asset_requires_local_uri_privacy_and_non_survey_boundary() -> None:
    fixture, packet = _fixture_packet()
    scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest="e" * 64,
        floor_plan_assets=(_floor_asset(),),
    )
    assert len(scene.assets) == 2
    with pytest.raises(ValueError, match="local or Aura-addressed"):
        project_construction_state_to_scene(
            fixture.state,
            packet,
            purpose_digest="e" * 64,
            floor_plan_assets=(_floor_asset(uri="https://private.example/floor.glb"),),
        )
    with pytest.raises(ValueError, match="survey authority"):
        project_construction_state_to_scene(
            fixture.state,
            packet,
            purpose_digest="e" * 64,
            floor_plan_assets=(
                replace(
                    _floor_asset(),
                    metadata={
                        "spatial_privacy_class": "PROJECT",
                        "survey_authority": True,
                        "person_level_data_included": False,
                    },
                ),
            ),
        )


def test_stale_or_authority_crossing_construction_packets_fail_closed() -> None:
    fixture, packet = _fixture_packet()
    stale = dict(packet)
    stale["state_digest"] = "f" * 32
    with pytest.raises(ValueError, match="stale"):
        project_construction_state_to_scene(fixture.state, stale, purpose_digest="f" * 64)
    authority = dict(packet)
    authority["physical_work_authorized"] = True
    with pytest.raises(ValueError, match="physical_work_authorized"):
        project_construction_state_to_scene(fixture.state, authority, purpose_digest="f" * 64)


def test_projection_is_deterministic_for_identical_state_and_evaluation() -> None:
    fixture, packet = _fixture_packet()
    first = project_construction_state_to_scene(fixture.state, packet, purpose_digest="1" * 64)
    second = project_construction_state_to_scene(fixture.state, packet, purpose_digest="1" * 64)
    assert first == second
    assert first.scene_digest == second.scene_digest


def test_public_projection_also_hashes_project_identifier() -> None:
    fixture, packet = _fixture_packet()
    scene = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest="2" * 64,
        privacy_class=SpatialPrivacyClass.PUBLIC,
    )
    assert fixture.state.project_id not in json.dumps(scene.to_dict(), sort_keys=True)


def test_nested_construction_contract_authority_tampering_fails_closed() -> None:
    fixture, packet = _fixture_packet()
    action_tamper = dict(packet)
    action_tamper["action_capsule"] = {
        **dict(packet["action_capsule"]),
        "metadata": {**dict(packet["action_capsule"]["metadata"]), "proposal_only": False},
    }
    with pytest.raises(ValueError, match="action capsule"):
        project_construction_state_to_scene(fixture.state, action_tamper, purpose_digest="3" * 64)

    lease_tamper = dict(packet)
    lease_tamper["arena_lease"] = {**dict(packet["arena_lease"]), "mode": "exclusive_write"}
    with pytest.raises(ValueError, match="lease"):
        project_construction_state_to_scene(fixture.state, lease_tamper, purpose_digest="3" * 64)

    evaluation_tamper = dict(packet)
    evaluation_tamper["evaluation"] = {**dict(packet["evaluation"]), "route_class": "TAMPERED"}
    with pytest.raises(ValueError, match="digest"):
        project_construction_state_to_scene(fixture.state, evaluation_tamper, purpose_digest="3" * 64)


def _with_evaluation(packet: dict, **changes) -> dict:
    updated = dict(packet)
    evaluation = {**dict(packet["evaluation"]), **changes}
    evaluation.pop("evaluation_digest", None)
    evaluation.pop("evaluation_id", None)
    evaluation["evaluation_digest"] = stable_digest(evaluation)
    updated["evaluation"] = evaluation
    return updated


def test_construction_projection_preflights_candidate_and_blocker_counts() -> None:
    fixture, packet = _fixture_packet()
    first = dict(packet["evaluation"]["assessments"][0])
    too_many = _with_evaluation(packet, assessments=[first] * 65)
    with pytest.raises(ValueError, match="candidate projection exceeds"):
        project_construction_state_to_scene(fixture.state, too_many, purpose_digest="4" * 64)

    malformed = {**first, "blockers": "not-a-sequence-contract"}
    bad_blockers = _with_evaluation(packet, assessments=[malformed])
    with pytest.raises(ValueError, match="blockers must be a bounded sequence"):
        project_construction_state_to_scene(fixture.state, bad_blockers, purpose_digest="4" * 64)

    oversized = {**first, "blockers": ["blocked"] * 257}
    too_many_blockers = _with_evaluation(packet, assessments=[oversized])
    with pytest.raises(ValueError, match="blocker count exceeds"):
        project_construction_state_to_scene(fixture.state, too_many_blockers, purpose_digest="4" * 64)


def test_construction_floor_assets_are_bounded_during_iteration() -> None:
    fixture, packet = _fixture_packet()

    def assets():
        for index in range(33):
            yield replace(_floor_asset(), asset_id=f"construction-floor-plan-{index}")

    with pytest.raises(ValueError, match="bounded asset cap"):
        project_construction_state_to_scene(
            fixture.state,
            packet,
            purpose_digest="5" * 64,
            floor_plan_assets=assets(),
        )

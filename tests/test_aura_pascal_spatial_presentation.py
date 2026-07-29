from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator
import pytest

import aura_pascal_spatial_presentation_part4 as session_module
from aura_pascal_spatial_presentation import (
    AuraPascalBridgeMessage,
    AuraPascalCoordinateReceipt,
    BridgeDirection,
    MAX_BRIDGE_DEPTH,
    MAX_BRIDGE_PAYLOAD_BYTES,
    PASCAL_COMMIT,
    PASCAL_LICENSE,
    PASCAL_REPOSITORY,
    PascalBridgeAction,
    PascalPresentationError,
    PascalPresentationRegistry,
    PascalPresentationSession,
    PascalPresentationState,
    PascalSceneArtifactManifest,
    PascalSourceLock,
    bridge_sha256,
    canonical_json,
    load_pascal_compatibility_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIGESTS = {
    "lock": "7c0830edc42139cf43b61c7365996b33abb86ccb54b3389761418b73b9fced08",
    "artifact": "fd4b7ba44de4394cc7670c98be8f46885c7b0f7788d57d025cae4e09f4e10ce7",
    "scene": "ec57cec9cfac1c6d2dc8d3206e9479bad54bcb5161d852d21e357b5d90c623db",
    "coordinate": "5597b217243c5cdbbcc473b5ac673d478ef264b28d346c8f77fc0a8db1c80157",
}
ORIGIN = "http://127.0.0.1:8000"


def fixture():
    return load_pascal_compatibility_fixture(str(ROOT))


def session(*, session_id: str = "PPS-test") -> PascalPresentationSession:
    _, manifest, coordinate, _ = fixture()
    return PascalPresentationSession(
        manifest=manifest,
        coordinate_receipt=coordinate,
        spatial_scene_digest=coordinate.spatial_scene_digest,
        render_plan_digest=hashlib.sha256(b"render-plan").hexdigest(),
        expected_origin=ORIGIN,
        session_id=session_id,
    )


def child_message(active, action, payload, *, sequence, nonce):
    return AuraPascalBridgeMessage.build(
        session_id=active.session_id,
        sequence=sequence,
        spatial_scene_digest=active.spatial_scene_digest,
        render_plan_digest=active.render_plan_digest,
        pascal_artifact_digest=active.manifest.artifact_digest,
        coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
        state_binding_digest=active.state_binding_digest,
        direction=BridgeDirection.PASCAL_TO_PARENT,
        action=action,
        payload=payload,
        nonce=nonce,
        message_id=f"PBM-{nonce}",
    )


def ready(active):
    return active.accept(
        child_message(
            active,
            PascalBridgeAction.READY,
            {
                "renderer_kind": "LOCAL_CANVAS_PASCAL_COMPATIBILITY",
                "external_requests": 0,
                "working_copy_only": True,
            },
            sequence=1,
            nonce="ready",
        ),
        origin=active.expected_origin,
    )


def load(active):
    _, manifest, _, scene = fixture()
    command = active.issue_parent_message(
        PascalBridgeAction.LOAD_ARTIFACT,
        {
            "scene": scene,
            "artifact_manifest": manifest.to_dict(),
            "initial_view": "2D",
            "dimensions_visible": True,
        },
    )
    receipt = child_message(
        active,
        PascalBridgeAction.LOAD_RECEIPT,
        {
            "command_message_digest": command.message_digest,
            "loaded": True,
            "view": "2D",
            "storey_id": "L1",
            "node_id": manifest.root_node_id,
            "dimensions_visible": True,
            "node_count": len(manifest.node_bindings),
            "external_requests": 0,
        },
        sequence=2,
        nonce="load",
    )
    return command, active.accept(receipt, origin=active.expected_origin)


def test_exact_pinned_pascal_fixture_and_spatial_scene_are_valid():
    lock, manifest, coordinate, scene = fixture()
    assert (lock.repository, lock.commit, lock.license) == (
        PASCAL_REPOSITORY,
        PASCAL_COMMIT,
        PASCAL_LICENSE,
    )
    assert lock.lock_digest == FIXTURE_DIGESTS["lock"]
    assert manifest.artifact_digest == FIXTURE_DIGESTS["artifact"]
    assert coordinate.spatial_scene_digest == FIXTURE_DIGESTS["scene"]
    assert coordinate.receipt_digest == FIXTURE_DIGESTS["coordinate"]
    assert scene["external_asset_fetch"] is False
    assert scene["persistent_canonical_storage"] is False
    assert {item.name: item.version for item in lock.packages} == {
        "@pascal-app/core": "0.9.2",
        "@pascal-app/viewer": "0.9.2",
        "@pascal-app/editor": "0.9.2",
        "@pascal-app/nodes": "0.1.1",
    }


@pytest.mark.parametrize(
    "schema_name,document_path",
    [
        ("aura_pascal_source_lock_v1.schema.json", "third_party/pascal/pascal-lock.json"),
        (
            "aura_pascal_scene_artifact_manifest_v1.schema.json",
            "aura_showcase/pascal-workbench/artifact-manifest.json",
        ),
        (
            "aura_pascal_coordinate_receipt_v1.schema.json",
            "aura_showcase/pascal-workbench/coordinate-receipt.json",
        ),
    ],
)
def test_committed_pascal_contracts_validate_against_schemas(
    schema_name,
    document_path,
):
    schema = json.loads((ROOT / "schemas" / schema_name).read_text())
    document = json.loads((ROOT / document_path).read_text())
    Draft202012Validator(schema).validate(document)


def test_scene_asset_tampering_fails_closed(tmp_path):
    copy = tmp_path / "repo"
    shutil.copytree(ROOT / "third_party", copy / "third_party")
    shutil.copytree(
        ROOT / "aura_showcase/pascal-workbench",
        copy / "aura_showcase/pascal-workbench",
    )
    for name in (
        "pascal-construction-foundry.js",
        "pascal-construction-foundry.css",
    ):
        shutil.copy2(
            ROOT / "aura_showcase" / name,
            copy / "aura_showcase" / name,
        )
    (copy / "aura_showcase/pascal-workbench/fixture.json").write_text(
        '{"tampered":true}\n'
    )
    with pytest.raises(PascalPresentationError, match="digest mismatch"):
        load_pascal_compatibility_fixture(str(copy))


def test_source_lock_rejects_recomputed_but_unapproved_package_identity():
    raw = json.loads((ROOT / "third_party/pascal/pascal-lock.json").read_text())
    raw["packages"][0]["version"] = "999.0.0"
    body = {key: value for key, value in raw.items() if key != "lock_digest"}
    raw["lock_digest"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
    with pytest.raises(PascalPresentationError, match="approved source lock"):
        PascalSourceLock.from_mapping(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("storey_ids", 7),
        ("node_bindings", {"bad": "shape"}),
    ],
)
def test_manifest_structural_type_errors_fail_as_contract_errors(field, value):
    raw = json.loads(
        (ROOT / "aura_showcase/pascal-workbench/artifact-manifest.json").read_text()
    )
    raw[field] = value
    with pytest.raises(PascalPresentationError):
        PascalSceneArtifactManifest.from_mapping(raw)


def test_cross_runtime_bridge_number_digest_vector_is_stable():
    vector = {
        "small": 1e-7,
        "negative_zero": -0.0,
        "integer": 42,
        "text": "é",
        "nested": [True, None, 0.5],
    }
    assert bridge_sha256(vector) == (
        "ae7ac10cc242d18afe68d4a911cdb6a28de1739e2acc0fe7c31f8b5f803ce3cf"
    )


@pytest.mark.parametrize("delta", [1, 16])
def test_bridge_payload_byte_ceiling_is_enforced(delta):
    active = session()
    with pytest.raises(PascalPresentationError, match="MAX_BRIDGE_PAYLOAD_BYTES"):
        AuraPascalBridgeMessage.build(
            session_id=active.session_id,
            sequence=1,
            spatial_scene_digest=active.spatial_scene_digest,
            render_plan_digest=active.render_plan_digest,
            pascal_artifact_digest=active.manifest.artifact_digest,
            coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
            state_binding_digest=active.state_binding_digest,
            direction=BridgeDirection.PARENT_TO_PASCAL,
            action=PascalBridgeAction.LOAD_ARTIFACT,
            payload={"data": "x" * (MAX_BRIDGE_PAYLOAD_BYTES + delta)},
        )


def test_bridge_payload_depth_and_non_mapping_are_rejected():
    active = session()
    deep = {}
    cursor = deep
    for _ in range(MAX_BRIDGE_DEPTH + 2):
        cursor["level"] = {}
        cursor = cursor["level"]
    with pytest.raises(PascalPresentationError, match="MAX_BRIDGE_DEPTH"):
        AuraPascalBridgeMessage.build(
            session_id=active.session_id,
            sequence=1,
            spatial_scene_digest=active.spatial_scene_digest,
            render_plan_digest=active.render_plan_digest,
            pascal_artifact_digest=active.manifest.artifact_digest,
            coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
            state_binding_digest=active.state_binding_digest,
            direction=BridgeDirection.PARENT_TO_PASCAL,
            action=PascalBridgeAction.LOAD_ARTIFACT,
            payload=deep,
        )
    with pytest.raises(PascalPresentationError, match="mapping"):
        AuraPascalBridgeMessage.build(
            session_id=active.session_id,
            sequence=1,
            spatial_scene_digest=active.spatial_scene_digest,
            render_plan_digest=active.render_plan_digest,
            pascal_artifact_digest=active.manifest.artifact_digest,
            coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
            state_binding_digest=active.state_binding_digest,
            direction=BridgeDirection.PARENT_TO_PASCAL,
            action=PascalBridgeAction.LOAD_ARTIFACT,
            payload=["not", "a", "mapping"],
        )


def test_ready_is_required_and_actual_origin_is_exact():
    active = session()
    with pytest.raises(PascalPresentationError, match="not_admitted"):
        active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {})
    message = child_message(
        active,
        PascalBridgeAction.READY,
        {"renderer_kind": "test", "external_requests": 0, "working_copy_only": True},
        sequence=1,
        nonce="wrong-origin",
    )
    with pytest.raises(PascalPresentationError, match="origin"):
        active.accept(message, origin="http://localhost:8000")
    result = active.accept(message, origin=active.expected_origin)
    assert result["state"] == "READY"
    assert set(result["spatial_interaction"]["intent_slots"]) == {
        "DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM",
    }


def test_parent_sequence_advances_only_after_exact_postcondition():
    active = session()
    ready(active)
    _, manifest, _, scene = fixture()
    command = active.issue_parent_message(
        PascalBridgeAction.LOAD_ARTIFACT,
        {
            "scene": scene,
            "artifact_manifest": manifest.to_dict(),
            "initial_view": "2D",
            "dimensions_visible": True,
        },
    )
    contradictory = child_message(
        active,
        PascalBridgeAction.LOAD_RECEIPT,
        {
            "command_message_digest": command.message_digest,
            "loaded": True,
            "view": "3D",
            "storey_id": "L1",
            "node_id": manifest.root_node_id,
            "dimensions_visible": True,
            "node_count": len(manifest.node_bindings),
            "external_requests": 0,
        },
        sequence=2,
        nonce="contradictory",
    )
    with pytest.raises(PascalPresentationError, match="differs"):
        active.accept(contradictory, origin=active.expected_origin)
    exact = child_message(
        active,
        PascalBridgeAction.LOAD_RECEIPT,
        {
            "command_message_digest": command.message_digest,
            "loaded": True,
            "view": "2D",
            "storey_id": "L1",
            "node_id": manifest.root_node_id,
            "dimensions_visible": True,
            "node_count": len(manifest.node_bindings),
            "external_requests": 0,
        },
        sequence=2,
        nonce="exact",
    )
    assert active.accept(exact, origin=active.expected_origin)["state"] == "ACTIVE"


def test_rejected_parent_command_can_retry_without_sequence_desynchronization():
    active = session()
    ready(active)
    _, manifest, _, scene = fixture()
    first = active.issue_parent_message(
        PascalBridgeAction.LOAD_ARTIFACT,
        {
            "scene": scene,
            "artifact_manifest": manifest.to_dict(),
            "initial_view": "2D",
            "dimensions_visible": True,
        },
    )
    error = child_message(
        active,
        PascalBridgeAction.PRESENTATION_ERROR,
        {
            "error": "child rejected before validation",
            "validated_command": False,
            "rejected_sequence": first.sequence,
        },
        sequence=2,
        nonce="rejected",
    )
    active.accept(error, origin=active.expected_origin)
    retry = active.issue_parent_message(
        PascalBridgeAction.LOAD_ARTIFACT,
        {
            "scene": scene,
            "artifact_manifest": manifest.to_dict(),
            "initial_view": "2D",
            "dimensions_visible": True,
        },
    )
    assert retry.sequence == first.sequence


@pytest.mark.parametrize(
    "authority_key",
    [
        "automatic_fix",
        "authority_decision",
        "capability_lease",
        "renderer_input_is_authority",
        "verifier_receipt",
    ],
)
def test_all_canonical_authority_aliases_fail_closed(authority_key):
    active = session()
    ready(active)
    with pytest.raises(PascalPresentationError, match="authority field"):
        active.issue_parent_message(
            PascalBridgeAction.LOAD_ARTIFACT,
            {authority_key: True},
        )


def test_view_storey_selection_and_dimension_postconditions_are_exact():
    active = session()
    ready(active)
    load(active)
    command = active.issue_parent_message(
        PascalBridgeAction.SET_STOREY,
        {"storey_id": "L2"},
    )
    wrong = child_message(
        active,
        PascalBridgeAction.VIEW_STATE,
        {
            "command_message_digest": command.message_digest,
            "view": "2D",
            "storey_id": "L1",
            "node_id": "room-retail-l1",
            "dimensions_visible": True,
        },
        sequence=3,
        nonce="wrong-storey",
    )
    with pytest.raises(PascalPresentationError, match="issued storey"):
        active.accept(wrong, origin=active.expected_origin)
    exact = child_message(
        active,
        PascalBridgeAction.VIEW_STATE,
        {
            "command_message_digest": command.message_digest,
            "view": "2D",
            "storey_id": "L2",
            "node_id": "room-mechanical-l2",
            "dimensions_visible": True,
        },
        sequence=3,
        nonce="storey-l2",
    )
    active.accept(exact, origin=active.expected_origin)
    assert active.selected_storey == "L2"


def test_nonce_history_is_not_evicted_and_session_is_bounded(monkeypatch):
    monkeypatch.setattr(session_module, "MAX_SESSION_MESSAGES", 3)
    active = session()
    ready(active)
    _, manifest, _, scene = fixture()
    command = active.issue_parent_message(
        PascalBridgeAction.LOAD_ARTIFACT,
        {
            "scene": scene,
            "artifact_manifest": manifest.to_dict(),
            "initial_view": "2D",
            "dimensions_visible": True,
        },
    )
    receipt = child_message(
        active,
        PascalBridgeAction.LOAD_RECEIPT,
        {
            "command_message_digest": command.message_digest,
            "loaded": True,
            "view": "2D",
            "storey_id": "L1",
            "node_id": manifest.root_node_id,
            "dimensions_visible": True,
            "node_count": len(manifest.node_bindings),
            "external_requests": 0,
        },
        sequence=2,
        nonce="load",
    )
    active.accept(receipt, origin=active.expected_origin)
    replay = child_message(
        active,
        PascalBridgeAction.VIEW_STATE,
        {
            "command_message_digest": "0" * 64,
            "view": "2D",
            "storey_id": "L1",
            "node_id": manifest.root_node_id,
            "dimensions_visible": True,
        },
        sequence=3,
        nonce="load",
    )
    with pytest.raises(PascalPresentationError, match="nonce"):
        active.accept(replay, origin=active.expected_origin)
    with pytest.raises(PascalPresentationError, match="message ceiling"):
        active.issue_parent_message(PascalBridgeAction.SET_VIEW_3D, {})


def test_registry_never_evicts_active_or_incomplete_dissolution():
    _, manifest, coordinate, _ = fixture()
    registry = PascalPresentationRegistry(
        manifest=manifest,
        coordinate_receipt=coordinate,
        max_sessions=1,
    )
    first = registry.create(
        spatial_scene_digest=coordinate.spatial_scene_digest,
        render_plan_digest="1" * 64,
        expected_origin=ORIGIN,
    )
    with pytest.raises(PascalPresentationError, match="session ceiling"):
        registry.create(
            spatial_scene_digest=coordinate.spatial_scene_digest,
            render_plan_digest="2" * 64,
            expected_origin=ORIGIN,
        )
    first.state = PascalPresentationState.DISSOLVED
    first.dissolution_receipt = {"iframe_removed": False}
    with pytest.raises(PascalPresentationError, match="session ceiling"):
        registry.create(
            spatial_scene_digest=coordinate.spatial_scene_digest,
            render_plan_digest="2" * 64,
            expected_origin=ORIGIN,
        )
    first.dissolution_receipt = {"iframe_removed": True}
    second = registry.create(
        spatial_scene_digest=coordinate.spatial_scene_digest,
        render_plan_digest="2" * 64,
        expected_origin=ORIGIN,
    )
    assert registry.get(second.session_id) is second


@pytest.mark.parametrize(
    "incomplete_field",
    [
        "renderer_released",
        "listeners_released",
        "timers_released",
        "buffers_cleared",
        "indexeddb_deleted",
        "network_guards_restored",
    ],
)
def test_dissolution_requires_exact_cleanup_and_iframe_finalization(incomplete_field):
    active = session()
    ready(active)
    load(active)
    command = active.issue_parent_message(PascalBridgeAction.DISSOLVE, {})
    complete_payload = {
        "command_message_digest": command.message_digest,
        "renderer_released": True,
        "listeners_released": True,
        "timers_released": True,
        "buffers_cleared": True,
        "indexeddb_deleted": True,
        "network_guards_restored": True,
        "external_requests": 0,
    }
    incomplete_payload = complete_payload.copy()
    incomplete_payload[incomplete_field] = False
    incomplete = child_message(
        active,
        PascalBridgeAction.DISSOLUTION_RECEIPT,
        incomplete_payload,
        sequence=3,
        nonce=f"incomplete-{incomplete_field}",
    )
    with pytest.raises(PascalPresentationError):
        active.accept(incomplete, origin=active.expected_origin)
    assert active.state is not PascalPresentationState.DISSOLVED
    receipt = child_message(
        active,
        PascalBridgeAction.DISSOLUTION_RECEIPT,
        complete_payload,
        sequence=3,
        nonce="dissolve",
    )
    active.accept(receipt, origin=active.expected_origin)
    assert active.state is PascalPresentationState.DISSOLVED
    assert active.status()["dissolution_complete"] is False
    assert active.mark_iframe_removed()["iframe_removed"] is True
    assert active.status()["dissolution_complete"] is True
    with pytest.raises(PascalPresentationError, match="post-dissolution"):
        active.accept(receipt, origin=active.expected_origin)


def test_static_workbench_has_exact_cleanup_3d_dimensions_and_no_remote_dependencies():
    index = (ROOT / "aura_showcase/pascal-workbench/index.html").read_text()
    child = (ROOT / "aura_showcase/pascal-workbench/pascal-workbench.js").read_text()
    parent = (ROOT / "aura_showcase/pascal-construction-foundry.js").read_text()
    combined = index + child + parent
    assert "https://" not in combined
    assert "http://" not in combined
    assert "import(" not in combined
    assert 'window.removeEventListener("resize", onResize)' in child
    assert "network_guards_restored: true" in child
    assert "dimensionsVisible" in child and "draw3D" in child
    assert "Pascal is unavailable; PR 1 remains active" in parent

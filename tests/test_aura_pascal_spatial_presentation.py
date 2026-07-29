from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator
import pytest

from aura_pascal_spatial_presentation import (
    AuraPascalBridgeMessage,
    AuraPascalCoordinateReceipt,
    BridgeDirection,
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
    load_pascal_compatibility_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIGESTS = {
    "lock": "15fd3dae4d0d5ed5a52122af9ba5f62454947f56a7e19f218cd395caa563a2f7",
    "artifact": "ac48f68fdec52ae0d78a1f533cfa4cc92005b11fdd62076200f5f779239fe630",
    "scene": "9442daedbe96f88f07c0668ca88d6a93ed22ffa09152e380b79828e7c760b096",
    "coordinate": "f77f862ba001366ff650b8a9dcb12fb61c2abcfb757446fbc69daca9d278310d",
}


def fixture():
    return load_pascal_compatibility_fixture(str(ROOT))


def session(*, session_id: str = "PPS-test") -> PascalPresentationSession:
    _, manifest, coordinate, _ = fixture()
    return PascalPresentationSession(
        manifest=manifest,
        coordinate_receipt=coordinate,
        spatial_scene_digest=coordinate.spatial_scene_digest,
        render_plan_digest=hashlib.sha256(b"render-plan").hexdigest(),
        expected_origin="http://127.0.0.1:8000",
        session_id=session_id,
    )


def child_message(active, action, payload, *, sequence, nonce):
    return AuraPascalBridgeMessage.build(
        session_id=active.session_id, sequence=sequence,
        spatial_scene_digest=active.spatial_scene_digest,
        render_plan_digest=active.render_plan_digest,
        pascal_artifact_digest=active.manifest.artifact_digest,
        coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
        state_binding_digest=active.state_binding_digest,
        direction=BridgeDirection.PASCAL_TO_PARENT, action=action,
        payload=payload, nonce=nonce, message_id=f"PBM-{nonce}",
    )


def ready(active):
    return active.accept(child_message(active, PascalBridgeAction.READY, {"renderer_kind": "LOCAL_CANVAS_PASCAL_COMPATIBILITY", "external_requests": 0, "working_copy_only": True}, sequence=1, nonce="ready"), origin=active.expected_origin)


def load(active):
    _, manifest, _, scene = fixture()
    command = active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {"scene": scene, "artifact_manifest": manifest.to_dict(), "initial_view": "2D", "dimensions_visible": True})
    receipt = child_message(active, PascalBridgeAction.LOAD_RECEIPT, {"command_message_digest": command.message_digest, "loaded": True, "view": "2D", "node_count": len(manifest.node_bindings), "external_requests": 0}, sequence=2, nonce="load")
    return command, active.accept(receipt, origin=active.expected_origin)


def test_exact_pinned_pascal_fixture_and_spatial_scene_are_valid():
    lock, manifest, coordinate, scene = fixture()
    assert (lock.repository, lock.commit, lock.license) == (PASCAL_REPOSITORY, PASCAL_COMMIT, PASCAL_LICENSE)
    assert lock.lock_digest == FIXTURE_DIGESTS["lock"]
    assert manifest.artifact_digest == FIXTURE_DIGESTS["artifact"]
    assert coordinate.spatial_scene_digest == FIXTURE_DIGESTS["scene"]
    assert coordinate.receipt_digest == FIXTURE_DIGESTS["coordinate"]
    assert scene["external_asset_fetch"] is False and scene["persistent_canonical_storage"] is False
    assert {item.name: item.version for item in lock.packages} == {"@pascal-app/core": "0.9.2", "@pascal-app/viewer": "0.9.2", "@pascal-app/editor": "0.9.2", "@pascal-app/nodes": "0.1.1"}


@pytest.mark.parametrize("schema_name,document_path", [
    ("aura_pascal_source_lock_v1.schema.json", "third_party/pascal/pascal-lock.json"),
    ("aura_pascal_scene_artifact_manifest_v1.schema.json", "aura_showcase/pascal-workbench/artifact-manifest.json"),
    ("aura_pascal_coordinate_receipt_v1.schema.json", "aura_showcase/pascal-workbench/coordinate-receipt.json"),
])
def test_committed_pascal_contracts_validate_against_schemas(schema_name, document_path):
    Draft202012Validator(json.loads((ROOT / "schemas" / schema_name).read_text())).validate(json.loads((ROOT / document_path).read_text()))


def test_scene_asset_tampering_fails_closed(tmp_path):
    copy = tmp_path / "repo"
    shutil.copytree(ROOT / "third_party", copy / "third_party")
    shutil.copytree(ROOT / "aura_showcase/pascal-workbench", copy / "aura_showcase/pascal-workbench")
    shutil.copy2(ROOT / "aura_showcase/pascal-construction-foundry.js", copy / "aura_showcase/pascal-construction-foundry.js")
    (copy / "aura_showcase/pascal-workbench/fixture.json").write_text('{"tampered":true}\n')
    with pytest.raises(PascalPresentationError, match="digest mismatch"):
        load_pascal_compatibility_fixture(str(copy))


def test_manifest_and_coordinate_tampering_fail_closed():
    raw = json.loads((ROOT / "aura_showcase/pascal-workbench/artifact-manifest.json").read_text()); raw["root_node_id"] = "different-root"
    with pytest.raises(PascalPresentationError, match="artifact digest|root_node_id"): PascalSceneArtifactManifest.from_mapping(raw)
    raw = json.loads((ROOT / "aura_showcase/pascal-workbench/coordinate-receipt.json").read_text()); raw["transform_matrix"][12] = 100.0
    with pytest.raises(PascalPresentationError, match="receipt digest"): AuraPascalCoordinateReceipt.from_mapping(raw)


def test_source_lock_rejects_malformed_rows_instead_of_silently_dropping_them():
    raw = json.loads((ROOT / "third_party/pascal/pascal-lock.json").read_text()); raw["local_assets"].append("not-an-object")
    with pytest.raises(PascalPresentationError, match="rows must be objects"): PascalSourceLock.from_mapping(raw)


def test_ready_is_required_and_origin_is_exact():
    active = session()
    with pytest.raises(PascalPresentationError, match="not_admitted"): active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {})
    message = child_message(active, PascalBridgeAction.READY, {"renderer_kind": "test", "external_requests": 0, "working_copy_only": True}, sequence=1, nonce="wrong-origin")
    with pytest.raises(PascalPresentationError, match="origin"): active.accept(message, origin="http://localhost:8000")
    Draft202012Validator(json.loads((ROOT / "schemas/aura_pascal_presentation_bridge_v1.schema.json").read_text())).validate(message.to_dict())
    result = active.accept(message, origin=active.expected_origin)
    assert result["state"] == "READY" and set(result["spatial_interaction"]["intent_slots"]) == {"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"}


def test_pending_parent_command_blocks_parallel_command_and_requires_exact_receipt():
    active = session(); ready(active); command = active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {"fixture": "bounded"})
    with pytest.raises(PascalPresentationError, match="pending_parent_command"): active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {"fixture": "second"})
    wrong = child_message(active, PascalBridgeAction.LOAD_RECEIPT, {"command_message_digest": "f" * 64, "loaded": True, "view": "2D", "external_requests": 0}, sequence=2, nonce="wrong-command")
    with pytest.raises(PascalPresentationError, match="another parent command"): active.accept(wrong, origin=active.expected_origin)
    exact = child_message(active, PascalBridgeAction.LOAD_RECEIPT, {"command_message_digest": command.message_digest, "loaded": True, "view": "2D", "external_requests": 0}, sequence=2, nonce="right-command")
    assert active.accept(exact, origin=active.expected_origin)["state"] == "ACTIVE"


def test_sequence_nonce_replay_and_message_digest_tampering_fail_closed():
    active = session(); message = child_message(active, PascalBridgeAction.READY, {"renderer_kind": "test", "external_requests": 0, "working_copy_only": True}, sequence=1, nonce="one"); active.accept(message, origin=active.expected_origin)
    with pytest.raises(PascalPresentationError, match="not_admitted|sequence|replay"): active.accept(message, origin=active.expected_origin)
    tampered = message.to_dict(); tampered["payload"]["external_requests"] = 1
    with pytest.raises(PascalPresentationError, match="message digest"): AuraPascalBridgeMessage.from_mapping(tampered)


def test_view_storey_selection_and_render_receipts_are_deterministic():
    active = session(); ready(active); load(active)
    command = active.issue_parent_message(PascalBridgeAction.SET_STOREY, {"storey_id": "L2"})
    view = child_message(active, PascalBridgeAction.VIEW_STATE, {"command_message_digest": command.message_digest, "view": "2D", "storey_id": "L2", "node_id": "room-office-l2", "dimensions_visible": True}, sequence=3, nonce="storey-l2")
    active.accept(view, origin=active.expected_origin); assert active.selected_storey == "L2" and active.selected_node_id == "room-office-l2"
    select = active.issue_parent_message(PascalBridgeAction.SET_SELECTION, {"node_id": "room-retail-l1"})
    hidden = child_message(active, PascalBridgeAction.SELECTION_CHANGED, {"command_message_digest": select.message_digest, "node_id": "room-retail-l1"}, sequence=4, nonce="hidden")
    with pytest.raises(PascalPresentationError, match="hidden-storey"): active.accept(hidden, origin=active.expected_origin)


def test_authority_like_payloads_fail_closed_but_explicit_false_boundaries_survive():
    active = session(); ready(active)
    with pytest.raises(PascalPresentationError, match="authority field"): active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {"automatic_execution": True})
    assert active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {"construction_truth": False, "survey_authority": False, "professional_approval": False}).payload["construction_truth"] is False


def test_dissolution_is_exact_post_dissolution_fails_and_registry_relaunches():
    active = session(); ready(active); load(active); command = active.issue_parent_message(PascalBridgeAction.DISSOLVE, {})
    receipt = child_message(active, PascalBridgeAction.DISSOLUTION_RECEIPT, {"command_message_digest": command.message_digest, "renderer_released": True, "listeners_released": True, "timers_released": True, "buffers_cleared": True, "indexeddb_deleted": True, "external_requests": 0}, sequence=3, nonce="dissolve")
    active.accept(receipt, origin=active.expected_origin); assert active.state is PascalPresentationState.DISSOLVED and active.status()["dissolution_complete"] is False
    assert active.mark_iframe_removed()["iframe_removed"] is True
    with pytest.raises(PascalPresentationError, match="post-dissolution"): active.accept(receipt, origin=active.expected_origin)
    _, manifest, coordinate, _ = fixture(); registry = PascalPresentationRegistry(manifest=manifest, coordinate_receipt=coordinate, max_sessions=1)
    first = registry.create(spatial_scene_digest=coordinate.spatial_scene_digest, render_plan_digest="1" * 64, expected_origin="http://127.0.0.1:8000"); first.state = PascalPresentationState.DISSOLVED
    second = registry.create(spatial_scene_digest=coordinate.spatial_scene_digest, render_plan_digest="2" * 64, expected_origin="http://127.0.0.1:8000")
    assert registry.get(second.session_id) is second


def test_static_workbench_has_no_remote_dependencies_and_retains_pr1_fallback_contract():
    index = (ROOT / "aura_showcase/pascal-workbench/index.html").read_text(); child = (ROOT / "aura_showcase/pascal-workbench/pascal-workbench.js").read_text(); parent = (ROOT / "aura_showcase/pascal-construction-foundry.js").read_text(); combined = index + child + parent
    assert "https://" not in combined and "http://" not in combined and "import(" not in combined
    assert "XMLHttpRequest disabled" in child and "WebSocket disabled" in child
    assert "Pascal is unavailable; PR 1 remains active" in parent and "sandbox" in parent

from pascal_spatial_presentation_test_support import (
    ROOT,
    ORIGIN,
    fixture,
    session,
    child_message,
    ready,
    load,
)
import aura_pascal_spatial_presentation_part4 as session_module
from aura_pascal_spatial_presentation import (
    PascalBridgeAction,
    PascalPresentationError,
    PascalPresentationRegistry,
    PascalPresentationState,
)

import pytest


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

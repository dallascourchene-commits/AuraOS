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
    "lock": "672611b98aca61e3ad7a4ebcb32f278916d09d876e663452bb654610562d2e87",
    "artifact": "3a007f69349cbb78966d8deedb43326a2c236112066298b59b245435a950cbbe",
    "scene": "56824f5cf1e38a1ed82591448c111859a79a277d396df8f030730ef8031f510c",
    "coordinate": "4dd3767ab948b3627dc0674c5f02d5ac8ee3f9745b052d1864fb44f7589b084a",
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

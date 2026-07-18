"""Regression tests for the legacy AR bridge spatial handoff guard."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from aura_spatial_ws_guard import compile_ar_hotswap_handoff


def _shapes() -> dict:
    return {
        "function:compile_scene": SimpleNamespace(
            label="compile_scene",
            node_type="function",
            position=[1.0, 2.0, 3.0],
            metadata={
                "ast_data": {
                    "file_path": "aura_spatial_scene.py",
                    "symbol": "compile_spatial_scene",
                    "line_range": [30, 65],
                    "kind": "function",
                }
            },
        )
    }


def test_ar_hotswap_handoff_is_private_redacted_and_nonexecuting():
    packet = compile_ar_hotswap_handoff(
        target_id="function:compile_scene",
        new_function={
            "name": "compile_scene_v2",
            "body": "return 2",
            "api_key": "sk-this-must-not-survive-1234567890",
        },
        shapes=_shapes(),
        actor_ref="human:test-session",
    )
    assert packet["ok"] is False
    assert packet["queued"] is False
    assert packet["success"] is False
    assert packet["status"] == "REQUIRES_GOVERNED_REPAIR_HANDOFF"
    assert packet["next_owner"] == "aura_forge"
    assert packet["raw_proposal_retained"] is False
    assert packet["requesting_client_only"] is True
    assert packet["broadcast"] is False
    assert packet["source_anchor_present"] is True
    assert packet["proposal_digest"]
    assert packet["intent"]["execution_authority"] is False
    assert packet["intent"]["patch_authority"] is False
    assert "sk-this-must-not-survive" not in repr(packet)


def test_ar_hotswap_handoff_fails_closed_for_unknown_shape():
    with pytest.raises(KeyError, match="not found"):
        compile_ar_hotswap_handoff(
            target_id="missing",
            new_function={"body": "return 1"},
            shapes=_shapes(),
            actor_ref="human:test-session",
        )


def test_ar_hotswap_handoff_does_not_invent_source_anchor():
    shapes = {
        "visual-only": SimpleNamespace(
            label="visual-only",
            node_type="function",
            position=[0.0, 0.0, 0.0],
            metadata={"ast_data": {"file_path": "../outside.py"}},
        )
    }
    packet = compile_ar_hotswap_handoff(
        target_id="visual-only",
        new_function={"body": "return 1"},
        shapes=shapes,
        actor_ref="human:test-session",
    )
    assert packet["source_anchor_present"] is False
    assert packet["success"] is False
    assert packet["next_owner"] == "aura_forge"

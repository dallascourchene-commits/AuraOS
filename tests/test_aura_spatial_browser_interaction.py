from __future__ import annotations

from copy import deepcopy

import pytest

from aura_spatial_contracts import CoordinateFrame, SpatialEntity, SpatialEntityType
from aura_spatial_interaction import compile_browser_spatial_interaction
from aura_spatial_scene import compile_spatial_scene


def _scene():
    return compile_spatial_scene(
        scene_id="browser-scene",
        purpose_digest="purpose:browser",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
        assets=(),
        entities=(
            SpatialEntity(
                entity_id="entity:a",
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label="A",
                frame_id="root",
                source_refs=("source:a",),
            ),
        ),
        source_refs=("source:browser",),
    )


def _packet(scene):
    return {
        "version": "AURA_SPATIAL_BROWSER_INTERACTION_V1",
        "session_id": "spatial-session:test",
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "action": "SELECT",
        "target_entity_ids": ["entity:a"],
        "actor_ref": "human:local",
        "input_source": "MOUSE",
        "intent_slots": {
            "DIR": "scene",
            "ASP": "inspect",
            "CLASS": "spatial_selection",
            "SUBJ": "domain_projection",
            "VOICE": "select",
            "STEM": "bind_selection",
        },
        "metadata": {
            "input_source": "MOUSE",
            "renderer_input_is_authority": False,
        },
        "review_only": True,
        "requires_forge": False,
        "projection_only": True,
        "renderer_authority": False,
        "execution_authority": False,
        "patch_authority": False,
        "production_mutation": False,
        "automatic_merge": False,
        "human_review_required": True,
    }


def test_browser_interaction_reuses_retained_six_slot_compiler():
    scene = _scene()
    intent = compile_browser_spatial_interaction(scene, _packet(scene))
    assert intent.review_only is True
    assert intent.execution_authority is False
    assert intent.patch_authority is False
    assert intent.intent_slots == (
        ("ASP", "inspect"),
        ("CLASS", "spatial_selection"),
        ("DIR", "scene"),
        ("STEM", "bind_selection"),
        ("SUBJ", "domain_projection"),
        ("VOICE", "select"),
    )


def test_browser_interaction_rejects_stale_scene_and_authority_aliases():
    scene = _scene()
    stale = _packet(scene)
    stale["scene_digest"] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        compile_browser_spatial_interaction(scene, stale)

    unsafe = _packet(scene)
    unsafe["metadata"] = {"automaticCommit": True}
    with pytest.raises(ValueError, match="authority"):
        compile_browser_spatial_interaction(scene, unsafe)

    wrong_slots = deepcopy(_packet(scene))
    wrong_slots["intent_slots"]["STEM"] = "execute_patch"
    with pytest.raises(ValueError, match="six-slot"):
        compile_browser_spatial_interaction(scene, wrong_slots)

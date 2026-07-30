from __future__ import annotations

import hashlib

import pytest

from aura_construction_foundry_director import (
    ConstructionFoundryDirector,
    DirectorControl,
    RequiredAsset,
    build_default_manifest,
)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def manifest():
    assets = (
        RequiredAsset(".aura/runtime_profiles/construction_demo_bilateral.v2.json", sha("profile")),
        RequiredAsset(".aura/runtime_profiles/construction_foundry_p4.confirmation.json", sha("confirmation")),
        RequiredAsset("aura_showcase/construction-foundry-director.js", sha("js")),
    )
    return build_default_manifest(
        assets,
        runtime_profile_path=assets[0].path,
        confirmation_packet_path=assets[1].path,
    )


def initial_evidence():
    return {
        "p3_available": True,
        "construction_identity_bound": True,
        "pascal_artifact_bound": True,
        "coordinate_receipt_bound": True,
        "as_built_scene_bound": True,
        "renderers_synchronized": True,
        "construction_candidates_bound": True,
        "domain_decision_bound": True,
        "identity_current": True,
        "operator_authorized": True,
        "fault_fixture_bound": True,
        "required_assets_bound": True,
        "rollback_adapter_ready": True,
        "u7_bridge_ready": True,
        "construction_state_unchanged": True,
        "resources_dissolved": True,
    }


def test_manifest_is_exact_offline_chain():
    item = manifest()
    payload = item.to_dict()
    assert payload["chapters"][0]["from_state"] == "FRAME"
    assert payload["chapters"][-1]["to_state"] == "DISSOLVED"
    assert payload["offline_deterministic"] is True
    assert payload["external_model_required"] is False
    assert payload["authority"]["physical_work_authority"] is False
    assert len(payload["manifest_digest"]) == 64
    assert len({row["chapter_id"] for row in payload["chapters"]}) == len(payload["chapters"])


def test_director_blocks_missing_evidence_then_commits_exact_receipt():
    item = manifest()
    director = ConstructionFoundryDirector(item)
    session = director.start_session(
        identity_digest=sha("identity"),
        construction_state_digest=sha("state"),
        initial_evidence={"p3_available": True},
    )
    blocked = director.project_next(session["session_id"])
    assert blocked["admitted"] is False
    assert blocked["missing_evidence"] == ["construction_identity_bound"]

    director.update_evidence(
        session["session_id"],
        {"construction_identity_bound": True},
    )
    admitted = director.project_next(session["session_id"])
    result = director.commit_next(
        session["session_id"],
        transition_digest=admitted["transition_digest"],
        effect_receipt={"ok": True, "effect": "FRAME_CONSTRUCTION"},
    )
    assert result["receipt"]["construction_state_unchanged"] is True
    assert result["receipt"]["authority"]["construction_truth"] is False
    assert result["session"]["current_state"] == "CONSTRUCTION_GROUNDED"


def test_navigation_cannot_skip_or_reexecute_consequential_chapters():
    item = manifest()
    director = ConstructionFoundryDirector(item)
    session = director.start_session(
        identity_digest=sha("identity"),
        construction_state_digest=sha("state"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    with pytest.raises(ValueError, match="cannot execute or skip"):
        director.control(session_id, control=DirectorControl.JUMP, chapter_id="RUN_RUNTIME_V2")

    first = director.project_next(session_id)
    director.commit_next(
        session_id,
        transition_digest=first["transition_digest"],
        effect_receipt={"ok": True},
    )
    director.control(session_id, control="PREVIOUS")
    assert director.require_session(session_id).executed_index == 0
    assert director.require_session(session_id).selected_index == -1


def test_complete_tour_requires_each_derived_evidence_gate_and_restart_after_dissolution():
    item = manifest()
    director = ConstructionFoundryDirector(item)
    started = director.start_session(
        identity_digest=sha("identity"),
        construction_state_digest=sha("state"),
        initial_evidence=initial_evidence(),
    )
    session_id = started["session_id"]
    evidence_by_effect = {
        "START_CAPTURE": {"capture_active": True},
        "MARK_INCIDENT": {"incident_marker_present": True},
        "FINALIZE_CAPTURE": {"capture_dissolved": True, "replay_packet_retained": True},
        "RUN_RUNTIME_REPLAY": {"runtime_proof_retained": True},
        "RECORD_REPAIR_ATTEMPT": {"repair_attempt_retained": True},
        "PREVIEW_DEGRADED": {"rollback_receipt_retained": True},
        "PREVIEW_SUCCESS": {"successful_preview_retained": True},
        "RUN_GOVERNED_U7": {"human_disposition_retained": True},
    }
    for chapter in item.chapters:
        projected = director.project_next(session_id)
        assert projected["admitted"] is True, (chapter.chapter_id, projected)
        director.commit_next(
            session_id,
            transition_digest=projected["transition_digest"],
            effect_receipt={"ok": True, "chapter": chapter.chapter_id},
            evidence_updates=evidence_by_effect.get(chapter.effect),
        )
    final = director.require_session(session_id)
    assert final.dissolved is True
    assert final.current_state == "DISSOLVED"
    assert len(director.receipts(session_id)) == len(item.chapters)

    restarted = director.control(session_id, control="RESTART")
    assert restarted["session"]["current_state"] == "FRAME"
    assert restarted["session"]["receipt_count"] == 0

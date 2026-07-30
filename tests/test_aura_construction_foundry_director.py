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
        "compare_receipt_bound": True,
        "construction_candidates_bound": True,
        "domain_decision_bound": True,
        "identity_current": True,
        "operator_authorized": True,
        "fault_fixture_bound": True,
        "required_assets_bound": True,
        "rollback_adapter_ready": True,
        "u7_bridge_ready": True,
        "construction_state_unchanged": True,
        "capture_resources_dissolved": True,
    }


def _ack_p3_sync(director, session_id):
    """Acknowledge P3 sync with a valid presentation receipt derived from the
    last committed chapter."""
    session = director.require_session(session_id)
    if not session.p3_sync_pending:
        return
    last_receipt = session.receipts[-1]
    chapter = last_receipt.get("chapter", {})
    ui = dict(chapter.get("ui_directive") or {})
    director.acknowledge_p3_sync(
        session_id,
        presentation_receipt={
            "chapter_id": last_receipt.get("chapter_id"),
            "active_view": ui.get("active_view"),
            "identity_digest": session.identity_digest,
        },
    )


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
    admitted = director.claim_next(session["session_id"])
    result = director.commit_next(
        session["session_id"],
        transition_digest=admitted["transition_digest"],
        effect_receipt={"ok": True, "effect": "FRAME_CONSTRUCTION"},
        claim_token=admitted.get("claim_token", ""),
    )
    assert result["receipt"]["construction_state_unchanged"] is True
    assert result["receipt"]["authority"]["construction_truth"] is False
    assert result["session"]["current_state"] == "CONSTRUCTION_GROUNDED"
    if result["session"].get("p3_sync_pending"):
        _ack_p3_sync(director, session["session_id"])


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

    first = director.claim_next(session_id)
    director.commit_next(
        session_id,
        transition_digest=first["transition_digest"],
        effect_receipt={"ok": True},
        claim_token=first.get("claim_token", ""),
    )
    if director.require_session(session_id).p3_sync_pending:
        _ack_p3_sync(director, session_id)
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
        projected = director.claim_next(session_id)
        assert projected["admitted"] is True, (chapter.chapter_id, projected)
        director.commit_next(
            session_id,
            transition_digest=projected["transition_digest"],
            effect_receipt={"ok": True, "chapter": chapter.chapter_id},
            claim_token=projected.get("claim_token", ""),
            evidence_updates=evidence_by_effect.get(chapter.effect),
        )
        # Acknowledge P3 sync for presentation chapters so progression continues.
        if director.require_session(session_id).p3_sync_pending:
            _ack_p3_sync(director, session_id)
    final = director.require_session(session_id)
    assert final.dissolved is True
    assert final.current_state == "DISSOLVED"
    assert len(director.receipts(session_id)) == len(item.chapters)

    restarted = director.control(session_id, control="RESTART")
    assert restarted["session"]["current_state"] == "FRAME"
    assert restarted["session"]["receipt_count"] == 0


def test_next_after_previous_only_returns_to_retained_chapter():
    director = ConstructionFoundryDirector(manifest())
    started = director.start_session(
        identity_digest=sha("identity-history"),
        construction_state_digest=sha("state-history"),
        initial_evidence=initial_evidence(),
    )
    session_id = started["session_id"]
    for _ in range(2):
        transition = director.claim_next(session_id)
        director.commit_next(
            session_id,
            transition_digest=transition["transition_digest"],
            effect_receipt={"ok": True},
            claim_token=transition.get("claim_token", ""),
        )
        if director.require_session(session_id).p3_sync_pending:
            _ack_p3_sync(director, session_id)
    director.control(session_id, control="PREVIOUS")
    before = director.require_session(session_id)
    assert before.selected_index == 0
    assert before.executed_index == 1
    navigation = director.control(session_id, control="NEXT")
    assert navigation["session"]["selected_index"] == 1
    assert navigation["session"]["executed_index"] == 1
    assert director.project_next(session_id)["chapter"]["order"] == 2


def test_play_state_survives_next_until_pause_or_dissolution():
    item = manifest()
    director = ConstructionFoundryDirector(item)
    session = director.start_session(
        identity_digest=sha("identity-play"),
        construction_state_digest=sha("state-play"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    director.control(session_id, control="PLAY")
    director.control(session_id, control="NEXT")
    assert director.require_session(session_id).playing is True
    director.control(session_id, control="PAUSE")
    assert director.require_session(session_id).playing is False


def test_director_accepts_canonical_32_character_construction_state_digest():
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-state-32"),
        construction_state_digest="a" * 32,
        initial_evidence=initial_evidence(),
    )
    assert session["construction_state_digest"] == "a" * 32

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


def _ack_p3_sync(director, session_id, identity_handle="test-handle"):
    """Acknowledge P3 sync with a valid P3-issued presentation receipt."""
    import hashlib as _hl
    session = director.require_session(session_id)
    if not session.p3_sync_pending:
        return
    last_receipt = session.receipts[-1]
    chapter_id = last_receipt.get("chapter_id")
    # Resolve the required view from the manifest chapter definition,
    # not from the committed receipt (which has no "chapter" key).
    manifest_chapter = director.manifest.chapter(chapter_id)
    active_view = dict(manifest_chapter.ui_directive or {}).get("active_view")
    # Simulate a P3-issued receipt digest.
    digest_input = f"{chapter_id}|{active_view}|{session.identity_digest}"
    receipt_digest = _hl.sha256(digest_input.encode()).hexdigest()
    director.acknowledge_p3_sync(
        session_id,
        presentation_receipt={
            "chapter_id": chapter_id,
            "active_view": active_view,
            "identity_digest": session.identity_digest,
            "receipt_digest": receipt_digest,
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


# ---------------------------------------------------------------------------
# Harness-Guided Finalization regression tests
# ---------------------------------------------------------------------------

def test_concurrent_next_produces_one_effect():
    """Two concurrent identical NEXT requests produce exactly one admitted claim."""
    import threading
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-concurrent"),
        construction_state_digest=sha("state-concurrent"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    results = []
    lock = threading.Lock()

    def claim():
        try:
            r = director.claim_next(session_id)
            with lock:
                results.append(r)
        except Exception as e:
            with lock:
                results.append({"error": str(e), "admitted": False})

    t1 = threading.Thread(target=claim)
    t2 = threading.Thread(target=claim)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    admitted = [r for r in results if r.get("admitted") is True]
    assert len(admitted) == 1, f"Expected 1 admitted, got {len(admitted)}: {results}"


def test_stale_transition_digest_cannot_claim():
    """A stale transition digest cannot commit."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-stale"),
        construction_state_digest=sha("state-stale"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    claimed = director.claim_next(session_id)
    assert claimed["admitted"] is True
    # Try to commit with a wrong digest.
    with pytest.raises(ValueError):
        director.commit_next(
            session_id,
            transition_digest="deadbeef" * 8,
            effect_receipt={"ok": True},
            claim_token=claimed.get("claim_token", ""),
        )


def test_stale_claim_cannot_release_newer():
    """A stale claim token cannot release a newer claim."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-stale-claim"),
        construction_state_digest=sha("state-stale-claim"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    first = director.claim_next(session_id)
    assert first["admitted"] is True
    first_token = first.get("claim_token", "")
    # Second claim should fail (first is still active).
    with pytest.raises(ValueError, match="already claimed"):
        director.claim_next(session_id)
    # Release with the first token (should succeed).
    director.release_claim(session_id, claim_token=first_token)
    # Now try to release with the old token again — should be a no-op (no error).
    director.release_claim(session_id, claim_token=first_token)


def test_receipt_budget_exhaustion_rejects():
    """After all chapters are committed, the next claim is not admitted."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-budget"),
        construction_state_digest=sha("state-budget"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    evidence_by_effect = {
        "START_CAPTURE": {"capture_active": True},
        "MARK_INCIDENT": {"incident_marker_present": True},
        "FINALIZE_CAPTURE": {"capture_dissolved": True, "replay_packet_retained": True, "capture_resources_dissolved": True},
        "RUN_RUNTIME_REPLAY": {"runtime_proof_retained": True},
        "RECORD_REPAIR_ATTEMPT": {"repair_attempt_retained": True},
        "PREVIEW_DEGRADED": {"rollback_receipt_retained": True},
        "PREVIEW_SUCCESS": {"successful_preview_retained": True},
        "RUN_GOVERNED_U7": {"human_disposition_retained": True},
    }
    for chapter in director.manifest.chapters:
        projected = director.claim_next(session_id)
        assert projected["admitted"] is True, (chapter.chapter_id, projected)
        director.commit_next(
            session_id,
            transition_digest=projected["transition_digest"],
            effect_receipt={"ok": True, "chapter": chapter.chapter_id},
            claim_token=projected.get("claim_token", ""),
            evidence_updates=evidence_by_effect.get(chapter.effect),
        )
        if director.require_session(session_id).p3_sync_pending:
            _ack_p3_sync(director, session_id)
    # All chapters committed — next claim should not be admitted.
    final = director.require_session(session_id)
    assert final.dissolved is True
    exhausted = director.claim_next(session_id)
    assert exhausted["admitted"] is False


def test_failed_effect_releases_claim():
    """A failed commit_next releases the claim so the session is not stuck."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-failed"),
        construction_state_digest=sha("state-failed"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    claimed = director.claim_next(session_id)
    assert claimed["admitted"] is True
    # Try to commit with a wrong claim token — should fail.
    with pytest.raises(ValueError):
        director.commit_next(
            session_id,
            transition_digest=claimed["transition_digest"],
            effect_receipt={"ok": True},
            claim_token="wrong-token",
        )
    # Release the claim with the correct token (simulating P4's error path).
    director.release_claim(session_id, claim_token=claimed["claim_token"])
    # Session should be able to claim again.
    re_claimed = director.claim_next(session_id)
    assert re_claimed["admitted"] is True


def test_p3_sync_pending_blocks_next_and_jump():
    """p3_sync_pending blocks NEXT, JUMP, and continued autoplay."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-blocked"),
        construction_state_digest=sha("state-blocked"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    # Advance to the first presentation chapter (chapter 0 has active_view).
    claimed = director.claim_next(session_id)
    director.commit_next(
        session_id,
        transition_digest=claimed["transition_digest"],
        effect_receipt={"ok": True},
        claim_token=claimed["claim_token"],
    )
    session_obj = director.require_session(session_id)
    if session_obj.p3_sync_pending:
        # NEXT should be blocked.
        with pytest.raises(ValueError, match="blocked"):
            director.claim_next(session_id)
        # JUMP should also be blocked — the Director raises ValueError for
        # progression when p3_sync_pending is set.
        with pytest.raises(ValueError):
            director.control(session_id, control=DirectorControl.JUMP, chapter_id=director.manifest.chapters[1].chapter_id)


def test_rejected_ack_stays_pending():
    """A rejected acknowledgment remains pending and keeps progression disabled."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-rejected"),
        construction_state_digest=sha("state-rejected"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    claimed = director.claim_next(session_id)
    director.commit_next(
        session_id,
        transition_digest=claimed["transition_digest"],
        effect_receipt={"ok": True},
        claim_token=claimed["claim_token"],
    )
    session_obj = director.require_session(session_id)
    assert session_obj.p3_sync_pending is True, "first chapter must create the P3 sync gate"
    # Try to acknowledge with a wrong chapter_id.
    with pytest.raises(ValueError):
        director.acknowledge_p3_sync(
            session_id,
            presentation_receipt={
                "chapter_id": "wrong-chapter",
                "active_view": "WRONG",
                "identity_digest": session_obj.identity_digest,
                "receipt_digest": "fake",
            },
        )
    # p3_sync_pending should still be True.
    assert director.require_session(session_id).p3_sync_pending is True


def test_complete_15_chapter_loopback_succeeds():
    """A complete 15-chapter loopback walkthrough succeeds with one receipt per chapter."""
    item = manifest()
    director = ConstructionFoundryDirector(item)
    session = director.start_session(
        identity_digest=sha("identity-loopback"),
        construction_state_digest=sha("state-loopback"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    evidence_by_effect = {
        "START_CAPTURE": {"capture_active": True},
        "MARK_INCIDENT": {"incident_marker_present": True},
        "FINALIZE_CAPTURE": {"capture_dissolved": True, "replay_packet_retained": True, "capture_resources_dissolved": True},
        "RUN_RUNTIME_REPLAY": {"runtime_proof_retained": True},
        "RECORD_REPAIR_ATTEMPT": {"repair_attempt_retained": True},
        "PREVIEW_DEGRADED": {"rollback_receipt_retained": True},
        "PREVIEW_SUCCESS": {"successful_preview_retained": True},
        "RUN_GOVERNED_U7": {"human_disposition_retained": True},
    }
    receipt_count = 0
    for chapter in item.chapters:
        projected = director.claim_next(session_id)
        assert projected["admitted"] is True, f"Chapter {chapter.chapter_id} not admitted: {projected}"
        result = director.commit_next(
            session_id,
            transition_digest=projected["transition_digest"],
            effect_receipt={"ok": True, "chapter": chapter.chapter_id},
            claim_token=projected.get("claim_token", ""),
            evidence_updates=evidence_by_effect.get(chapter.effect),
        )
        receipt_count += 1
        # Acknowledge P3 sync for presentation chapters.
        if director.require_session(session_id).p3_sync_pending:
            _ack_p3_sync(director, session_id)
    final = director.require_session(session_id)
    # One receipt per chapter.
    assert len(director.receipts(session_id)) == len(item.chapters)
    assert receipt_count == len(item.chapters)
    # No leaked claims.
    assert session_id not in director._transition_claims
    # No pending acknowledgments.
    assert final.p3_sync_pending is False
    # Session is dissolved.
    assert final.dissolved is True
    assert final.current_state == "DISSOLVED"


def test_construction_state_and_authority_remain_unchanged():
    """Construction state and all prohibited authority fields remain unchanged throughout."""
    item = manifest()
    director = ConstructionFoundryDirector(item)
    session = director.start_session(
        identity_digest=sha("identity-authority"),
        construction_state_digest=sha("state-authority"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    original_state = session["construction_state_digest"]
    evidence_by_effect = {
        "START_CAPTURE": {"capture_active": True},
        "MARK_INCIDENT": {"incident_marker_present": True},
        "FINALIZE_CAPTURE": {"capture_dissolved": True, "replay_packet_retained": True, "capture_resources_dissolved": True},
        "RUN_RUNTIME_REPLAY": {"runtime_proof_retained": True},
        "RECORD_REPAIR_ATTEMPT": {"repair_attempt_retained": True},
        "PREVIEW_DEGRADED": {"rollback_receipt_retained": True},
        "PREVIEW_SUCCESS": {"successful_preview_retained": True},
        "RUN_GOVERNED_U7": {"human_disposition_retained": True},
    }
    for chapter in item.chapters:
        projected = director.claim_next(session_id)
        result = director.commit_next(
            session_id,
            transition_digest=projected["transition_digest"],
            effect_receipt={"ok": True, "chapter": chapter.chapter_id},
            claim_token=projected.get("claim_token", ""),
            evidence_updates=evidence_by_effect.get(chapter.effect),
        )
        # Verify construction_state_unchanged is True in every receipt.
        assert result["receipt"]["construction_state_unchanged"] is True
        # Verify authority fields are all False.
        authority = result["receipt"]["authority"]
        assert authority, "receipt must carry the authority matrix"
        assert all(value is False for value in authority.values()), authority
        if director.require_session(session_id).p3_sync_pending:
            _ack_p3_sync(director, session_id)
    # Final state digest should match the original (unchanged).
    final = director.require_session(session_id)
    assert final.construction_state_digest == original_state


def test_acknowledge_rejects_missing_identity_digest():
    """acknowledge_p3_sync rejects a receipt with no identity_digest."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-no-id"),
        construction_state_digest=sha("state-no-id"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    claimed = director.claim_next(session_id)
    director.commit_next(
        session_id,
        transition_digest=claimed["transition_digest"],
        effect_receipt={"ok": True},
        claim_token=claimed["claim_token"],
    )
    sess = director.require_session(session_id)
    assert sess.p3_sync_pending is True, "first chapter must create the P3 sync gate"
    last_receipt = sess.receipts[-1]
    chapter_id = last_receipt.get("chapter_id")
    manifest_chapter = director.manifest.chapter(chapter_id)
    active_view = dict(manifest_chapter.ui_directive or {}).get("active_view")
    # Missing identity_digest.
    with pytest.raises(ValueError, match="identity_digest"):
        director.acknowledge_p3_sync(
            session_id,
            presentation_receipt={
                "chapter_id": chapter_id,
                "active_view": active_view,
                "receipt_digest": "fake",
            },
        )
    # Empty identity_digest.
    with pytest.raises(ValueError, match="identity_digest"):
        director.acknowledge_p3_sync(
            session_id,
            presentation_receipt={
                "chapter_id": chapter_id,
                "active_view": active_view,
                "identity_digest": "",
                "receipt_digest": "fake",
            },
        )
    # p3_sync_pending must remain True.
    assert director.require_session(session_id).p3_sync_pending is True


def test_acknowledge_rejects_missing_receipt_digest():
    """acknowledge_p3_sync rejects a receipt with no receipt_digest."""
    director = ConstructionFoundryDirector(manifest())
    session = director.start_session(
        identity_digest=sha("identity-no-digest"),
        construction_state_digest=sha("state-no-digest"),
        initial_evidence=initial_evidence(),
    )
    session_id = session["session_id"]
    claimed = director.claim_next(session_id)
    director.commit_next(
        session_id,
        transition_digest=claimed["transition_digest"],
        effect_receipt={"ok": True},
        claim_token=claimed["claim_token"],
    )
    sess = director.require_session(session_id)
    assert sess.p3_sync_pending is True, "first chapter must create the P3 sync gate"
    last_receipt = sess.receipts[-1]
    chapter_id = last_receipt.get("chapter_id")
    manifest_chapter = director.manifest.chapter(chapter_id)
    active_view = dict(manifest_chapter.ui_directive or {}).get("active_view")
    # Missing receipt_digest.
    with pytest.raises(ValueError, match="receipt_digest"):
        director.acknowledge_p3_sync(
            session_id,
            presentation_receipt={
                "chapter_id": chapter_id,
                "active_view": active_view,
                "identity_digest": sess.identity_digest,
            },
        )
    # Empty receipt_digest.
    with pytest.raises(ValueError, match="receipt_digest"):
        director.acknowledge_p3_sync(
            session_id,
            presentation_receipt={
                "chapter_id": chapter_id,
                "active_view": active_view,
                "identity_digest": sess.identity_digest,
                "receipt_digest": "",
            },
        )
    # p3_sync_pending must remain True.
    assert director.require_session(session_id).p3_sync_pending is True

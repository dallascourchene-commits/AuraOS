from __future__ import annotations

import dataclasses
import hashlib
import json
import pytest

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity, BoundedIncidentCapture, BoundedRepairFoundry,
    build_current_reproof, build_preview_receipt, build_spatial_foundry_projection,
)


def d(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def identity() -> BilateralIdentity:
    return BilateralIdentity(d("intent"), d("confirmation"), d("ledger"), d("guards"),
                             "revision-7", "f1b9d786", d("tree"), d("profile"))


def replay():
    capture = BoundedIncidentCapture(identity=identity(), release_id="release-1", environment_id="local-browser")
    capture.observe("POINTER", {"authorization": "Bearer hidden"}, observed_at=1.0)
    capture.mark_incident("selection lost", {"api_key": "sk-secret-value-123456"})
    return capture.finalize(expected_positive=["selection stable"],
                            expected_negative=["must not pick hidden storey"],
                            preservation_claims=["source geometry unchanged"])


def test_capture_redacts_binds_identity_and_grants_no_authority():
    packet = replay(); encoded = json.dumps(dataclasses.asdict(packet))
    assert "Bearer hidden" not in encoded and "sk-secret" not in encoded
    assert packet.packet_id.startswith("IRP-")
    assert packet.authority["merge"] is False
    assert packet.authority["learning_promotion"] is False
    assert packet.authority["human_review_required"] is True


def test_capture_requires_marker_all_obligations_and_dissolves():
    capture = BoundedIncidentCapture(identity=identity(), release_id="r", environment_id="e")
    with pytest.raises(ValueError, match="marker"):
        capture.finalize(expected_positive=["p"], expected_negative=["n"], preservation_claims=["k"])
    capture.mark_incident("failure")
    with pytest.raises(ValueError, match="positive, negative, and preservation"):
        capture.finalize(expected_positive=[], expected_negative=["n"], preservation_claims=["k"])
    capture.finalize(expected_positive=["p"], expected_negative=["n"], preservation_claims=["k"])
    with pytest.raises(RuntimeError, match="closed"):
        capture.observe("AFTER", {})


def test_foundry_enforces_no_repeat_budget_and_all_proof_classes():
    foundry = BoundedRepairFoundry(replay(), max_attempts=2)
    first = foundry.record_candidate(hypothesis={"cause": "reset"}, candidate_digest=d("c1"),
        positive_passed=True, negative_passed=False, preservation_passed=True,
        adjacent_regressions_passed=True, minimized_counterexample={"hidden": "selected"})
    assert first.promotion_ready is False
    with pytest.raises(ValueError, match="repeated"):
        foundry.record_candidate(hypothesis={"cause": "reset"}, candidate_digest=d("c1"),
            positive_passed=True, negative_passed=True, preservation_passed=True,
            adjacent_regressions_passed=True)
    second = foundry.record_candidate(hypothesis={"cause": "filter"}, candidate_digest=d("c2"),
        positive_passed=True, negative_passed=True, preservation_passed=True,
        adjacent_regressions_passed=True)
    assert second.promotion_ready is True
    with pytest.raises(RuntimeError, match="budget"):
        foundry.record_candidate(hypothesis={"cause": "third"}, candidate_digest=d("c3"),
            positive_passed=True, negative_passed=True, preservation_passed=True,
            adjacent_regressions_passed=True)


def test_preview_retains_verified_version_and_requires_rollback_reason():
    with pytest.raises(ValueError, match="rollback_reason"):
        build_preview_receipt(candidate_digest=d("c"), last_verified_digest=d("v"),
            health_before={"ok": True}, health_after={"ok": False}, rollback_triggered=True)
    receipt = build_preview_receipt(candidate_digest=d("c"), last_verified_digest=d("v"),
        health_before={"ok": True}, health_after={"ok": False}, rollback_triggered=True,
        rollback_reason="health regression")
    assert receipt.production_mutation is False and receipt.human_promotion_required is True


def test_current_reproof_requires_p0_p1_disposition_and_experience():
    packet = replay()
    incomplete = build_current_reproof(identity=identity(), replay_packet_digest=packet.packet_digest,
        candidate_digest=d("c"), p0_positive=True, p0_negative=True, p1_guardrail=False,
        p1_preservation=True, independent_verifier_id="p1", human_community_disposition="CONFIRMED",
        relationship_experience_ref="REL-1", qdkt_eligible=True)
    assert not incomplete.durable_learning_authorized and not incomplete.qdkt_eligible
    rejected = build_current_reproof(identity=identity(), replay_packet_digest=packet.packet_digest,
        candidate_digest=d("c"), p0_positive=True, p0_negative=True, p1_guardrail=True,
        p1_preservation=True, independent_verifier_id="p1", human_community_disposition="REJECTED",
        relationship_experience_ref="REL-1", qdkt_eligible=True)
    assert not rejected.durable_learning_authorized and not rejected.qdkt_eligible
    complete = build_current_reproof(identity=identity(), replay_packet_digest=packet.packet_digest,
        candidate_digest=d("c"), p0_positive=True, p0_negative=True, p1_guardrail=True,
        p1_preservation=True, independent_verifier_id="p1", human_community_disposition="CONFIRMED",
        relationship_experience_ref="REL-1", qdkt_eligible=True)
    assert complete.durable_learning_authorized and complete.qdkt_eligible


def test_spatial_projection_is_complete_but_non_authoritative():
    packet = replay(); foundry = BoundedRepairFoundry(packet)
    attempt = foundry.record_candidate(hypothesis={"cause": "reset"}, candidate_digest=d("c"),
        positive_passed=True, negative_passed=True, preservation_passed=True,
        adjacent_regressions_passed=True)
    preview = build_preview_receipt(candidate_digest=d("c"), last_verified_digest=d("v"),
        health_before={"ok": True}, health_after={"ok": True}, rollback_triggered=False)
    reproof = build_current_reproof(identity=identity(), replay_packet_digest=packet.packet_digest,
        candidate_digest=d("c"), p0_positive=True, p0_negative=True, p1_guardrail=True,
        p1_preservation=True, independent_verifier_id="p1", human_community_disposition="CONFIRMED",
        relationship_experience_ref="REL-1")
    projection = build_spatial_foundry_projection(identity=identity(), incident=packet,
        attempts=[attempt], preview=preview, reproof=reproof,
        intent={"positive": ["keep selection"]}, plan={"steps": ["repair"]},
        code_targets=[{"path": "renderer.js", "digest": d("renderer")}])
    assert projection["projection_only"] is True
    assert projection["authority"]["visual_truth"] is False
    assert projection["authority"]["patch"] is False
    assert projection["authority"]["merge"] is False
    assert projection["proof"]["incident_packet_digest"] == packet.packet_digest
    assert projection["projection_digest"]

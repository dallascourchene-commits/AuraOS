from __future__ import annotations

import dataclasses
import hashlib
import time

import pytest

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    BilateralLiveRepairService,
    BoundedIncidentCapture,
)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def sha1(value: str) -> str:
    return hashlib.sha1(value.encode()).hexdigest()


def identity() -> BilateralIdentity:
    return BilateralIdentity(
        intent_digest=sha("intent"),
        confirmation_digest=f"intent-confirmation_{sha('confirmation')}",
        semantic_ledger_digest=sha("ledger"),
        guardrail_set_digest=sha("guardrails"),
        intent_revision_id="NOT_CREATED_NO_POST_CONFIRMATION_DRIFT",
        repository_head=sha1("head"),
        source_tree_digest=sha1("tree"),
        runtime_profile_digest=sha("profile"),
        verifier_id="independent-verifier",
        verifier_source_digest=sha("verifier-source"),
    )


def packet():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
        retention_seconds=120,
    )
    capture.mark_incident("selection disappeared")
    result = capture.finalize(
        expected_positive=["selection remains stable"],
        expected_negative=["hidden storeys are never selected"],
        preservation_claims=["source geometry remains unchanged"],
        current_identity=item,
    )
    return item, result


def strict_runtime_proof(item: BilateralIdentity) -> dict:
    return {
        "version": "AURA_RUNTIME_BILATERAL_PROOF_V1",
        "ok": True,
        "profile_sha256": item.runtime_profile_digest,
        "repository_identity_unchanged": True,
        "resolved_expected_repository_head": item.repository_head,
        "resolved_expected_source_tree": item.source_tree_digest,
        "intent_contract": {
            "intent_digest": item.intent_digest,
            "semantic_ledger_digest": item.semantic_ledger_digest,
            "confirmation_digest": item.confirmation_digest,
            "guardrail_set_digest": item.guardrail_set_digest,
            "intent_revision_status": item.intent_revision_id,
            "expected_repository_head": item.repository_head,
            "expected_source_tree": item.source_tree_digest,
            "allowed_path_set_digest": sha("allowed-paths"),
        },
        "independent_verifier": {
            "verifier_id": item.verifier_id,
            "source_sha256": item.verifier_source_digest,
        },
        "human_review_required": True,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "production_mutation": False,
        "professional_authority": False,
        "physical_work_authority": False,
        "learning_promotion": False,
        "bilateral_runtime_evidence_authority": False,
    }


def test_strict_runtime_proof_binds_every_incident_identity():
    item, replay = packet()
    BilateralLiveRepairService._validate_runtime_proof(replay, strict_runtime_proof(item))
    mismatched = strict_runtime_proof(item)
    mismatched["intent_contract"] = {
        **mismatched["intent_contract"],
        "confirmation_digest": f"intent-confirmation_{sha('other')}",
    }
    with pytest.raises(BilateralLiveRepairError, match="confirmation_digest"):
        BilateralLiveRepairService._validate_runtime_proof(replay, mismatched)


def test_runtime_proof_cannot_remove_human_review_or_add_authority():
    item, replay = packet()
    no_human = {**strict_runtime_proof(item), "human_review_required": False}
    with pytest.raises(BilateralLiveRepairError, match="human review"):
        BilateralLiveRepairService._validate_runtime_proof(replay, no_human)
    escalated = {**strict_runtime_proof(item), "automatic_merge": True}
    with pytest.raises(BilateralLiveRepairError, match="forbidden authority"):
        BilateralLiveRepairService._validate_runtime_proof(replay, escalated)


def test_finalize_scrubs_separate_marker_from_service_memory(tmp_path):
    item = identity()
    service = BilateralLiveRepairService(tmp_path, attempt_archive_db_path=tmp_path / "attempts.db")
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release",
            "environment_id": "browser",
            "capture_authorized": True,
            "retention_seconds": 120,
        }
    )
    capture_id = started["capture_id"]
    service.mark(capture_id, "selection disappeared")
    service.finalize_capture(
        capture_id,
        {
            "current_identity": dataclasses.asdict(item),
            "expected_positive": ["selection remains stable"],
            "expected_negative": ["hidden storeys are never selected"],
            "preservation_claims": ["source geometry remains unchanged"],
        },
    )
    retained = service._captures[capture_id]
    assert retained._closed is True
    assert retained._marker_event is None
    assert not retained._events
    service.close()


def test_status_sweeps_expired_capture_and_scrubs_all_buffers(tmp_path):
    item = identity()
    service = BilateralLiveRepairService(tmp_path, attempt_archive_db_path=tmp_path / "attempts.db")
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release",
            "environment_id": "browser",
            "capture_authorized": True,
            "retention_seconds": 1,
        }
    )
    capture = service._captures[started["capture_id"]]
    capture.mark_incident("selection disappeared")
    capture.started_at = time.time() - 2
    status = service.status()
    assert status["active_capture_count"] == 0
    assert capture._closed is True
    assert capture._marker_event is None
    assert not capture._events
    service.close()

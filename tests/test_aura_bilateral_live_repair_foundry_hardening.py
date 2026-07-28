from __future__ import annotations

import dataclasses
import hashlib
import json
import time

import pytest

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    BilateralLiveRepairService,
    BoundedIncidentCapture,
    PreviewRollbackReceipt,
    canonical_bytes,
)
from aura_arena_attempt_archive import ArenaAttemptArchive
from aura_bilateral_live_repair_foundry_contracts import _runtime_binding_digest


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
        "profile_version": "AURA_RUNTIME_PROFILE_V2",
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
        "confirmed_positive_requirement_digests": [
            _runtime_binding_digest("selection remains stable"),
        ],
        "confirmed_negative_requirement_digests": [
            _runtime_binding_digest("hidden storeys are never selected"),
            _runtime_binding_digest("source geometry remains unchanged"),
        ],
        "requirement_bindings": {
            "positive_assertions": [{
                "requirement_digest": _runtime_binding_digest("selection remains stable"),
                "assertion_ids": ["positive"],
            }],
            "negative_assertions": [{
                "requirement_digest": _runtime_binding_digest("hidden storeys are never selected"),
                "assertion_ids": ["negative"],
            }],
            "preservation_assertions": [{
                "requirement_digest": _runtime_binding_digest("source geometry remains unchanged"),
                "assertion_ids": ["preservation"],
            }],
            "fault_injections": [{
                "requirement_digest": _runtime_binding_digest("hidden storeys are never selected"),
                "assertion_ids": ["fault"],
            }],
        },
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


def test_runtime_proof_requires_exact_versions_and_captured_obligations():
    item, replay = packet()
    wrong_version = {**strict_runtime_proof(item), "profile_version": "AURA_RUNTIME_PROFILE_V3"}
    with pytest.raises(BilateralLiveRepairError, match="version"):
        BilateralLiveRepairService._validate_runtime_proof(replay, wrong_version)
    wrong_obligations = {
        **strict_runtime_proof(item),
        "confirmed_positive_requirement_digests": [_runtime_binding_digest("different requirement")],
    }
    with pytest.raises(BilateralLiveRepairError, match="captured obligations"):
        BilateralLiveRepairService._validate_runtime_proof(replay, wrong_obligations)


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
    assert capture_id not in service._captures
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


def test_archive_route_filter_is_applied_before_limit(tmp_path):
    archive = ArenaAttemptArchive(tmp_path, db_path=tmp_path / "attempts.db")
    workflow_id = "IRP-route-filter"
    archive.record(
        arena_id="construction",
        route="bilateral-live-repair/repair-attempt",
        request={"action_id": "repair"},
        result={"ok": False, "status": "REJECTED"},
        workflow_state={"workflow_id": workflow_id},
    )
    for index in range(12):
        archive.record(
            arena_id="construction",
            route=f"unrelated/{index}",
            request={"action_id": "noise"},
            result={"ok": True},
            workflow_state={"workflow_id": workflow_id},
        )
    rows = archive.list(
        workflow_id=workflow_id,
        route="bilateral-live-repair/repair-attempt",
        limit=1,
    )
    assert len(rows) == 1
    assert rows[0]["route"] == "bilateral-live-repair/repair-attempt"
    archive.close()


def test_marker_payload_cannot_replace_canonical_marker():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
    )
    event = capture.mark_incident("canonical marker", {"marker": "attacker marker"})
    assert event.payload["marker"] == "canonical marker"


def test_expired_capture_scrubs_separate_marker():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
        retention_seconds=1,
    )
    capture.mark_incident("canonical marker")
    capture.started_at = time.time() - 2
    with pytest.raises(BilateralLiveRepairError, match="expired"):
        capture.observe("LATE")
    assert capture._marker_event is None


def test_obligations_are_sanitized_and_canonically_ordered():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
    )
    capture.mark_incident("canonical marker")
    replay = capture.finalize(
        expected_positive={"z requirement", "authorization: Bearer hidden-value"},
        expected_negative={"never b", "never a"},
        preservation_claims={"preserve b", "preserve a"},
        current_identity=item,
    )
    encoded = json.dumps(replay.to_dict(), sort_keys=True)
    assert "hidden-value" not in encoded
    assert replay.expected_positive == tuple(sorted(replay.expected_positive))
    assert "secret_value:<root>" in replay.privacy_receipt["redaction_refs"]


def test_canonical_mapping_rejects_stringified_key_collisions():
    with pytest.raises(ValueError, match="collide"):
        canonical_bytes({1: "numeric", "1": "text"})


def test_preview_receipt_rehydration_recomputes_identity(tmp_path):
    item = identity()
    service = BilateralLiveRepairService(tmp_path, attempt_archive_db_path=tmp_path / "attempts.db")
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release",
            "environment_id": "browser",
            "capture_authorized": True,
        }
    )
    service.mark(started["capture_id"], "selection disappeared")
    replay = service.finalize_capture(
        started["capture_id"],
        {
            "current_identity": dataclasses.asdict(item),
            "expected_positive": ["selection remains stable"],
            "expected_negative": ["hidden storeys are never selected"],
            "preservation_claims": ["source geometry remains unchanged"],
        },
    )["packet"]
    receipt = service.preview_candidate(
        packet_id=replay["packet_id"],
        current_identity=item,
        candidate_digest=sha("candidate"),
        last_verified_digest=sha("verified"),
        health_before={"ok": True},
        health_after={"ok": True},
        environment_class="LOCAL_EPHEMERAL",
        rollback_preauthorized=False,
    )
    PreviewRollbackReceipt.from_mapping(receipt.to_dict())
    tampered = {**receipt.to_dict(), "candidate_digest": sha("other")}
    with pytest.raises(ValueError, match="identity"):
        PreviewRollbackReceipt.from_mapping(tampered)
    with pytest.raises(ValueError, match="boolean"):
        service.preview_candidate(
            packet_id=replay["packet_id"],
            current_identity=item,
            candidate_digest=sha("candidate"),
            last_verified_digest=sha("verified"),
            health_before={"ok": True},
            health_after={"ok": False},
            environment_class="LOCAL_EPHEMERAL",
            rollback_preauthorized="false",  # type: ignore[arg-type]
            rollback_reason="regression",
        )
    service.close()

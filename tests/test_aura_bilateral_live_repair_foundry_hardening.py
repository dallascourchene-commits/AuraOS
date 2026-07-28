from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
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
from aura_bilateral_live_repair_foundry_contracts import (
    MAX_CAPTURE_BYTES,
    MAX_EVENT_BYTES,
    _runtime_binding_digest,
)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def git_oid(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:40]


def identity() -> BilateralIdentity:
    return BilateralIdentity(
        intent_digest=sha("intent"),
        confirmation_digest=f"intent-confirmation_{sha('confirmation')}",
        semantic_ledger_digest=sha("ledger"),
        guardrail_set_digest=sha("guardrails"),
        intent_revision_id="NOT_CREATED_NO_POST_CONFIRMATION_DRIFT",
        repository_head=git_oid("head"),
        source_tree_digest=git_oid("tree"),
        runtime_profile_digest=sha("profile"),
        verifier_id="independent-verifier",
        verifier_source_digest=sha("verifier-source"),
    )


def packet(*, required_assets=()):
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
        required_assets=required_assets,
        current_identity=item,
    )
    return item, result


def strict_runtime_proof(item: BilateralIdentity) -> dict:
    proof = {
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
        "required_trace_artifacts": [],
    }
    proof["proof_digest"] = _runtime_binding_digest(proof)
    return proof


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


def test_runtime_proof_binds_every_captured_required_asset():
    asset_digest = sha("incident-console")
    item, replay = packet(required_assets=[{
        "path": "incident-console.json",
        "sha256": asset_digest,
    }])
    proof = strict_runtime_proof(item)
    proof["required_trace_artifacts"] = [{
        "path": "incident-console.json",
        "present": True,
        "within_size_limit": True,
        "sha256": asset_digest,
    }]
    proof["proof_digest"] = _runtime_binding_digest({
        key: value for key, value in proof.items() if key != "proof_digest"
    })
    BilateralLiveRepairService._validate_runtime_proof(replay, proof)
    proof["required_trace_artifacts"][0]["within_size_limit"] = False
    with pytest.raises(BilateralLiveRepairError, match="required asset"):
        BilateralLiveRepairService._validate_runtime_proof(replay, proof)


def test_runtime_proof_rejects_noncanonical_embedded_digest():
    item, replay = packet()
    proof = strict_runtime_proof(item)
    proof["proof_digest"] = sha("tampered-proof")
    with pytest.raises(BilateralLiveRepairError, match="canonical owner identity"):
        BilateralLiveRepairService._validate_runtime_proof(replay, proof)


def test_finalize_scrubs_separate_marker_from_service_memory(tmp_path):
    item = identity()
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "attempts.db",
        current_identity_resolver=lambda _captured: item,
    )
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


def test_finalize_uses_trusted_identity_resolver_not_request_identity(tmp_path):
    item = identity()
    stale = dataclasses.replace(item, intent_digest=sha("changed-intent"))
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "attempts.db",
        current_identity_resolver=lambda _captured: stale,
    )
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release",
            "environment_id": "browser",
            "capture_authorized": True,
        }
    )
    service.mark(started["capture_id"], "selection disappeared")
    with pytest.raises(BilateralLiveRepairError, match="stale"):
        service.finalize_capture(
            started["capture_id"],
            {
                "current_identity": dataclasses.asdict(item),
                "expected_positive": ["selection remains stable"],
                "expected_negative": ["hidden storeys are never selected"],
                "preservation_claims": ["source geometry remains unchanged"],
            },
        )
    service.close()


def test_failed_archive_retains_finalized_packet_for_bounded_retry(tmp_path):
    item = identity()
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "attempts.db",
        current_identity_resolver=lambda _captured: item,
    )
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release",
            "environment_id": "browser",
            "capture_authorized": True,
        }
    )
    service.mark(started["capture_id"], "selection disappeared")
    original_record = service.attempt_archive.record
    service.attempt_archive.record = lambda **_kwargs: {"ok": False}
    with pytest.raises(BilateralLiveRepairError, match="retained in memory for archive retry"):
        service.finalize_capture(
            started["capture_id"],
            {
                "expected_positive": ["selection remains stable"],
                "expected_negative": ["hidden storeys are never selected"],
                "preservation_claims": ["source geometry remains unchanged"],
            },
        )
    assert len(service._pending_packet_archives) == 1
    packet_id = next(iter(service._pending_packet_archives))
    assert packet_id in service._packets
    service.attempt_archive.record = original_record
    retried = service.retry_packet_archive(packet_id)
    assert retried["ok"] is True
    assert not service._pending_packet_archives
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


def test_idle_capture_expires_without_another_service_request(tmp_path):
    item = identity()
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "attempts.db",
    )
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
    deadline = time.time() + 2.5
    while started["capture_id"] in service._captures and time.time() < deadline:
        time.sleep(0.02)
    assert started["capture_id"] not in service._captures
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


def test_direct_finalize_dissolves_separately_retained_marker():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
    )
    capture.mark_incident("canonical marker")
    capture.finalize(
        expected_positive=["selection remains stable"],
        expected_negative=["hidden storeys are never selected"],
        preservation_claims=["source geometry remains unchanged"],
        current_identity=item,
    )
    assert capture._marker_event is None
    assert not capture._events


def test_capture_enforces_per_event_and_aggregate_byte_ceilings():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
    )
    with pytest.raises(BilateralLiveRepairError, match="event exceeds"):
        capture.observe("OVERSIZED", {"data": "x" * MAX_EVENT_BYTES})
    accepted = 0
    with pytest.raises(BilateralLiveRepairError, match="aggregate byte ceiling"):
        while True:
            capture.observe("BOUNDED", {"data": "x" * 60_000, "index": accepted})
            accepted += 1
    assert accepted * 60_000 < MAX_CAPTURE_BYTES


def test_canonical_identity_rejects_runtime_specific_objects_and_class_types():
    with pytest.raises(ValueError, match="unsupported canonical value type"):
        canonical_bytes({"value": object()})
    with pytest.raises(ValueError, match="unsupported canonical value type"):
        canonical_bytes(BilateralIdentity)


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


def test_review_workflow_and_waboose_scope_are_exact_and_complete():
    root = Path(__file__).resolve().parent.parent
    workflow = (root / ".github" / "workflows" / "aura-review-learning.yml").read_text(
        encoding="utf-8"
    )
    assert workflow.count("fetch --depth=1 --no-tags origin") == 2
    request = json.loads(
        (
            root
            / ".aura"
            / "waboose_requests"
            / "bilateral_intent_guardrail_foundry_final.v2.json"
        ).read_text(encoding="utf-8")
    )
    expected = {
        "aura_agent_arena_bridge.py",
        "aura_agent_arena_persistence_bridge.py",
        "aura_arena_attempt_archive.py",
        "scripts/aura_review_learning_architect_harness.py",
    }
    assert expected.issubset(request["changed_files"])
    assert expected.issubset(request["allowed_paths"])


def test_preview_receipt_rehydration_recomputes_identity(tmp_path):
    item = identity()
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "attempts.db",
        current_identity_resolver=lambda _captured: item,
    )
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

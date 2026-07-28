from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    BilateralLiveRepairService,
    BoundedIncidentCapture,
    IncidentReplayPacket,
    canonical_bytes,
    classify_repair_route,
    derive_repair_failure_class,
    digest,
)
from aura_bilateral_live_repair_foundry_contracts import _runtime_binding_digest


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def sha1(value: str) -> str:
    return hashlib.sha1(value.encode()).hexdigest()


def identity(seed: str = "one") -> BilateralIdentity:
    return BilateralIdentity(
        intent_digest=sha(f"intent-{seed}"),
        confirmation_digest=f"intent-confirmation_{sha(f'confirmation-{seed}')}",
        semantic_ledger_digest=sha(f"ledger-{seed}"),
        guardrail_set_digest=sha(f"guardrails-{seed}"),
        intent_revision_id=f"revision-{seed}",
        repository_head=sha1(f"head-{seed}"),
        source_tree_digest=sha1(f"tree-{seed}"),
        runtime_profile_digest=sha(f"profile-{seed}"),
        verifier_id=f"independent-verifier-{seed}",
        verifier_source_digest=sha(f"verifier-source-{seed}"),
    )


def runtime_proof(item: BilateralIdentity, *, negative: bool = True, ok: bool = True):
    return {
        "ok": ok,
        "profile_sha256": item.runtime_profile_digest,
        "repository_identity_unchanged": True,
        "positive_assertions": [{"assertion_id": "positive", "passed": True}],
        "negative_assertions": [{"assertion_id": "negative", "passed": negative}],
        "preservation_assertions": [{"assertion_id": "preservation", "passed": True}],
        "fault_injections": [{"assertion_id": "fault", "passed": True}],
        "independent_verifier": {
            "verifier_id": item.verifier_id,
            "source_sha256": item.verifier_source_digest,
        },
        "base_runtime_receipt": {"ok": True, "run_digest": sha("base-runtime")},
    }


def finalized_capture(item: BilateralIdentity, *, max_events: int = 4) -> IncidentReplayPacket:
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release-1",
        environment_id="loopback-browser",
        capture_authorized=True,
        max_events=max_events,
        retention_seconds=120,
    )
    capture.observe("POINTER", {"authorization": "Bearer hidden-value"})
    capture.mark_incident("selection disappeared", {"api_key": "sk-secret-value-123456"})
    return capture.finalize(
        expected_positive=["selection remains stable"],
        expected_negative=["hidden storeys are never pickable"],
        preservation_claims=["canonical Construction state remains unchanged"],
        current_identity=item,
    )


def service_with_packet(tmp_path: Path, item: BilateralIdentity):
    db_path = tmp_path / "attempts.db"
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=db_path,
        runtime_runner=lambda *_a, **_k: runtime_proof(item),
        current_identity_resolver=lambda _captured: item,
        allow_reduced_runtime_fixture=True,
    )
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release-1",
            "environment_id": "loopback-browser",
            "capture_authorized": True,
            "max_events": 4,
            "retention_seconds": 120,
        }
    )
    service.observe(started["capture_id"], "POINTER", {"authorization": "Bearer hidden-value"})
    service.mark(started["capture_id"], "selection disappeared", {"api_key": "sk-secret-value-123456"})
    result = service.finalize_capture(
        started["capture_id"],
        {
            "current_identity": dataclasses.asdict(item),
            "expected_positive": ["selection remains stable"],
            "expected_negative": ["hidden storeys are never pickable"],
            "preservation_claims": ["canonical Construction state remains unchanged"],
            "arena_id": "construction",
        },
    )
    return service, db_path, result["packet"]


def retain_proof(service: BilateralLiveRepairService, packet_id: str, item: BilateralIdentity, proof=None) -> str:
    value = dict(proof or runtime_proof(item))
    service.runtime_runner = lambda *_args, **_kwargs: value
    result = service.execute_replay(
        packet_id=packet_id,
        profile_path="profile.v2.json",
        confirmation_packet="external-confirmation.json",
        output_dir="external-runtime-output",
    )
    return result["runtime_proof_ref"]


def test_confirmation_receipt_reference_is_preserved_not_forced_to_hex():
    item = identity()
    assert item.confirmation_digest.startswith("intent-confirmation_")
    assert item.identity_digest == digest(dataclasses.asdict(item))


def test_capture_requires_explicit_authorization():
    with pytest.raises(BilateralLiveRepairError, match="authorization"):
        BoundedIncidentCapture(
            identity=identity(),
            release_id="release",
            environment_id="browser",
            capture_authorized=False,
        )


def test_marker_survives_rolling_buffer_eviction_and_capture_dissolves():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
        max_events=2,
    )
    capture.mark_incident("first marker")
    for index in range(8):
        capture.observe("AFTER", {"index": index})
    packet = capture.finalize(
        expected_positive=["stable"],
        expected_negative=["never hidden"],
        preservation_claims=["source unchanged"],
        current_identity=item,
    )
    assert packet.marker_event.payload["marker"] == "first marker"
    assert len(packet.events) == 2
    assert packet.total_event_count == 9
    assert packet.window_start_sequence == 7
    assert packet.dissolution_receipt.buffers_cleared is True
    with pytest.raises(BilateralLiveRepairError, match="closed"):
        capture.observe("LATE", {})


def test_nested_sets_and_mappings_have_deterministic_identity():
    left = {"values": {"z", "a", "m"}, "nested": [{"b": 2, "a": 1}]}
    right = {"nested": [{"a": 1, "b": 2}], "values": {"m", "z", "a"}}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert digest(left) == digest(right)


def test_capture_uses_canonical_privacy_sanitizer_and_retains_no_raw_secret():
    packet = finalized_capture(identity())
    encoded = json.dumps(packet.to_dict(), sort_keys=True)
    assert "Bearer hidden-value" not in encoded
    assert "sk-secret-value" not in encoded
    assert packet.privacy_receipt["raw_secret_retained"] is False
    assert packet.authority["production_mutation"] is False
    assert packet.authority["human_review_required"] is True


def test_archived_packet_rehydrates_with_exact_digest_after_service_restart(tmp_path):
    item = identity()
    first, db_path, raw = service_with_packet(tmp_path, item)
    packet_id = raw["packet_id"]
    first.close()
    second = BilateralLiveRepairService(tmp_path, attempt_archive_db_path=db_path, runtime_runner=lambda *_a, **_k: runtime_proof(item))
    packet = second._packet(packet_id)
    assert isinstance(packet, IncidentReplayPacket)
    assert packet.packet_digest == raw["packet_digest"]
    assert packet.marker_event.payload["marker"] == "selection disappeared"
    second.close()


def test_archived_packet_tampering_fails_closed(tmp_path):
    packet = finalized_capture(identity())
    raw = packet.to_dict()
    raw["expected_negative"] = ["tampered"]
    with pytest.raises(ValueError, match="identity"):
        IncidentReplayPacket.from_mapping(raw)


def test_runtime_replay_delegates_to_profile_v2_and_binds_exact_profile(tmp_path):
    item = identity()
    calls = []
    def runner(root, **kwargs):
        calls.append((root, kwargs))
        return runtime_proof(item)
    service, _db, raw = service_with_packet(tmp_path, item)
    service.runtime_runner = runner
    result = service.execute_replay(
        packet_id=raw["packet_id"],
        profile_path=".aura/runtime_profiles/construction_demo_bilateral.v2.json",
        confirmation_packet=tmp_path / "confirmation.json",
        output_dir=tmp_path / "runtime-output",
    )
    assert result["ok"] is True
    assert calls[0][1]["allow_dirty"] is False
    assert result["runtime_proof"]["profile_sha256"] == item.runtime_profile_digest
    assert result["runtime_proof_ref"] == digest(result["runtime_proof"])
    service.runtime_runner = lambda *_a, **_k: {**runtime_proof(item), "profile_sha256": sha("wrong")}
    with pytest.raises(BilateralLiveRepairError, match="profile identity"):
        service.execute_replay(
            packet_id=raw["packet_id"],
            profile_path="profile",
            confirmation_packet="confirmation",
            output_dir="output",
        )
    service.close()


def test_repair_candidate_is_bound_to_retained_runtime_candidate(tmp_path):
    item = identity()
    service, _db, raw = service_with_packet(tmp_path, item)
    proof = {
        **runtime_proof(item),
        "runtime_candidate_id": "candidate-bound-to-proof",
    }
    proof_ref = digest(proof)
    service._runtime_proofs[proof_ref] = (raw["packet_id"], proof)
    with pytest.raises(BilateralLiveRepairError, match="candidate differs"):
        service.record_repair_attempt(
            packet_id=raw["packet_id"],
            hypothesis={"cause": "selection reset"},
            candidate_digest=sha("unrelated candidate"),
            runtime_proof_ref=proof_ref,
            minimized_counterexample=None,
            current_identity=item,
        )
    attempt = service.record_repair_attempt(
        packet_id=raw["packet_id"],
        hypothesis={"cause": "selection reset"},
        candidate_digest=_runtime_binding_digest("candidate-bound-to-proof"),
        runtime_proof_ref=proof_ref,
        minimized_counterexample=None,
        current_identity=item,
    )
    assert attempt.promotion_ready is True
    service.close()


def test_full_runtime_proof_survives_archive_restart_without_list_truncation(tmp_path):
    item = identity()
    first, db_path, raw = service_with_packet(tmp_path, item)
    proof = runtime_proof(item)
    proof["positive_assertions"] = [
        {"assertion_id": f"positive-{index}", "passed": True}
        for index in range(256)
    ]
    proof_ref = retain_proof(first, raw["packet_id"], item, proof)
    first.close()
    second = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=db_path,
        runtime_runner=lambda *_a, **_k: proof,
    )
    replay = second._packet(raw["packet_id"])
    retained = second._runtime_proof(replay, proof_ref)
    assert len(retained["positive_assertions"]) == 256
    second.close()


def test_missing_negative_proof_blocks_repair_promotion(tmp_path):
    item = identity()
    service, _db, raw = service_with_packet(tmp_path, item)
    attempt = service.record_repair_attempt(
        packet_id=raw["packet_id"],
        hypothesis={"cause": "selection reset"},
        candidate_digest=sha("candidate"),
        runtime_proof_ref=retain_proof(service, raw["packet_id"], item, runtime_proof(item, negative=False)),
        minimized_counterexample={"hidden_storey_selected": True},
        current_identity=item,
    )
    assert attempt.positive_passed is True
    assert attempt.negative_passed is False
    assert attempt.promotion_ready is False
    assert attempt.route_class == "STRUCTURAL"
    service.close()


def test_failed_runtime_proof_rehydrates_as_rejected_attempt(tmp_path):
    item = identity()
    service, _db, raw = service_with_packet(tmp_path, item)
    proof_ref = retain_proof(service, raw["packet_id"], item, runtime_proof(item, ok=False))
    attempt = service.record_repair_attempt(
        packet_id=raw["packet_id"],
        hypothesis={"cause": "proof-level failure"},
        candidate_digest=sha("candidate"),
        runtime_proof_ref=proof_ref,
        minimized_counterexample=None,
        current_identity=item,
    )
    assert attempt.runtime_proof_passed is False
    assert attempt.promotion_ready is False
    rehydrated = service.attempts_for_packet(raw["packet_id"])[0]
    assert rehydrated.runtime_proof_passed is False
    assert rehydrated.promotion_ready is False
    service.close()


def test_failed_hypothesis_cannot_repeat_across_service_restart(tmp_path):
    item = identity()
    first, db_path, raw = service_with_packet(tmp_path, item)
    proof_ref = retain_proof(first, raw["packet_id"], item, runtime_proof(item, negative=False))
    first.record_repair_attempt(
        packet_id=raw["packet_id"],
        hypothesis={"cause": "selection reset"},
        candidate_digest=sha("candidate-1"),
        runtime_proof_ref=proof_ref,
        minimized_counterexample={"hidden": True},
        current_identity=item,
    )
    assert len(first.attempts_for_packet(raw["packet_id"])) == 1
    first.close()
    second = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=db_path,
        runtime_runner=lambda *_a, **_k: runtime_proof(item),
    )
    with pytest.raises(BilateralLiveRepairError, match="repeated failed hypothesis"):
        second.record_repair_attempt(
            packet_id=raw["packet_id"],
            hypothesis={"cause": "selection reset"},
            candidate_digest=sha("candidate-2"),
            runtime_proof_ref=proof_ref,
            minimized_counterexample=None,
            current_identity=item,
        )
    second.close()


def test_repair_attempt_budget_is_persistent_and_bounded(tmp_path):
    item = identity()
    service, _db, raw = service_with_packet(tmp_path, item)
    proof_ref = retain_proof(service, raw["packet_id"], item, runtime_proof(item, negative=False))
    for index in range(8):
        service.record_repair_attempt(
            packet_id=raw["packet_id"],
            hypothesis={"strategy": index},
            candidate_digest=sha(f"candidate-{index}"),
            runtime_proof_ref=proof_ref,
            minimized_counterexample={"strategy": index},
            current_identity=item,
        )
    with pytest.raises(BilateralLiveRepairError, match="budget"):
        service.record_repair_attempt(
            packet_id=raw["packet_id"],
            hypothesis={"strategy": 9},
            candidate_digest=sha("candidate-9"),
            runtime_proof_ref=proof_ref,
            minimized_counterexample=None,
            current_identity=item,
        )
    service.close()


def test_failure_routing_matches_harness_surgeon_and_council_classes():
    assert classify_repair_route("LOCAL_TEST") == "LOCAL"
    assert classify_repair_route("INTERFACE") == "STRUCTURAL"
    assert derive_repair_failure_class(runtime_proof(identity(), negative=False)) == "PROHIBITION"
    assert derive_repair_failure_class(runtime_proof(identity())) == "SOURCE_ASSERTION"
    with pytest.raises(ValueError, match="canonical"):
        classify_repair_route("GUESS_AND_PATCH")


def test_preview_is_isolated_and_restores_exact_verified_digest(tmp_path):
    item = identity()
    service, _db, raw = service_with_packet(tmp_path, item)
    verified = sha("verified")
    receipt = service.preview_candidate(
        packet_id=raw["packet_id"],
        current_identity=item,
        candidate_digest=sha("candidate"),
        last_verified_digest=verified,
        health_before={"ok": True, "version": "v1"},
        health_after={"ok": False, "version": "v2"},
        environment_class="LOCAL_EPHEMERAL",
        rollback_preauthorized=True,
        rollback_reason="health regression",
        restore_local=lambda expected: expected,
    )
    assert receipt.preview_isolated is True
    assert receipt.technical_rollback_executed is True
    assert receipt.rollback_succeeded is True
    assert receipt.restored_digest == verified
    assert receipt.production_mutation is False
    assert service.latest_preview(raw["packet_id"]).preview_id == receipt.preview_id
    with pytest.raises(BilateralLiveRepairError, match="isolated"):
        service.preview_candidate(
            packet_id=raw["packet_id"],
            current_identity=item,
            candidate_digest=sha("candidate"),
            last_verified_digest=verified,
            health_before={"ok": True},
            health_after={"ok": True},
            environment_class="PRODUCTION",
            rollback_preauthorized=False,
        )
    service.close()


def test_failed_rollback_is_archived_before_error_is_propagated(tmp_path):
    item = identity()
    service, db_path, raw = service_with_packet(tmp_path, item)
    verified = sha("verified")
    with pytest.raises(BilateralLiveRepairError, match="exact last verified"):
        service.preview_candidate(
            packet_id=raw["packet_id"],
            current_identity=item,
            candidate_digest=sha("candidate"),
            last_verified_digest=verified,
            health_before={"ok": True},
            health_after={"ok": False},
            environment_class="LOCAL_EPHEMERAL",
            rollback_preauthorized=True,
            rollback_reason="health regression",
            restore_local=lambda _expected: sha("wrong"),
        )
    receipt = service.latest_preview(raw["packet_id"])
    assert receipt is not None
    assert receipt.technical_rollback_executed is True
    assert receipt.rollback_succeeded is False
    assert receipt.rollback_failure == "rollback did not restore the exact last verified identity"
    service.close()
    second = BilateralLiveRepairService(tmp_path, attempt_archive_db_path=db_path)
    retained = second.latest_preview(raw["packet_id"])
    assert retained is not None
    assert retained.preview_id == receipt.preview_id
    assert retained.rollback_failure == receipt.rollback_failure
    second.close()


def test_u7_delegates_p0_p1_and_finalization_to_canonical_owner(tmp_path, monkeypatch):
    calls = []
    module = types.ModuleType("aura_unified_memory_continuity_learning")
    class Packet:
        def __init__(self, kind): self.kind = kind
        def to_dict(self): return {"kind": self.kind}
    def commit(*args, **kwargs): calls.append("P0"); return Packet("P0")
    def observe(*args, **kwargs): calls.append("P1"); return Packet("P1")
    def finalize(*args, **kwargs): calls.append("FINALIZE"); return {"ok": True, "human_disposition": {"disposition": "APPROVED"}}
    module.commit_bridge_prediction = commit
    module.observe_bridge_prediction = observe
    module.finalize_bridge_learning = finalize
    monkeypatch.setitem(sys.modules, "aura_unified_memory_continuity_learning", module)
    service = BilateralLiveRepairService(tmp_path, attempt_archive_db_path=tmp_path / "u7.db", runtime_runner=lambda *_a, **_k: {})
    result = service.run_governed_u7(
        bridge=object(),
        plan_phase_hash="phase",
        task_id="task",
        prediction_contract={"positive": True, "negative": True},
        observation_contract={"guardrail": True, "preservation": True},
        finalization_contract={"human_disposition": "APPROVED"},
    )
    assert calls == ["P0", "P1", "FINALIZE"]
    assert result["canonical_owner"] == "aura_unified_memory_continuity_learning"
    assert result["automatic_crystallization"] is False
    service.close()


def test_u7_retry_resumes_from_retained_p0(tmp_path, monkeypatch):
    calls = []
    session = {
        "unified_prediction_packets": {},
        "unified_p1_observations": {},
        "unified_learning_results": {},
    }

    class Bridge:
        def _require_session(self, phase):
            assert phase == "phase"
            return session

    class Packet:
        def __init__(self, kind):
            self.kind = kind

        def to_dict(self):
            return {"kind": self.kind}

    module = types.ModuleType("aura_unified_memory_continuity_learning")

    def commit(*_args, **kwargs):
        calls.append("P0")
        value = Packet("P0")
        session["unified_prediction_packets"][kwargs["task_id"]] = value
        return value

    def observe(*_args, **kwargs):
        calls.append("P1")
        if calls.count("P1") == 1:
            raise ValueError("transient P1 failure")
        value = Packet("P1")
        session["unified_p1_observations"][kwargs["task_id"]] = value
        return value

    def finalize(*_args, **_kwargs):
        calls.append("FINALIZE")
        return {"ok": True}

    module.commit_bridge_prediction = commit
    module.observe_bridge_prediction = observe
    module.finalize_bridge_learning = finalize
    monkeypatch.setitem(sys.modules, "aura_unified_memory_continuity_learning", module)
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "u7-resume.db",
        runtime_runner=lambda *_a, **_k: {},
    )
    kwargs = {
        "bridge": Bridge(),
        "plan_phase_hash": " phase ",
        "task_id": " task ",
        "prediction_contract": {},
        "observation_contract": {},
        "finalization_contract": {},
    }
    with pytest.raises(ValueError, match="transient"):
        service.run_governed_u7(**kwargs)
    result = service.run_governed_u7(**kwargs)
    assert result["ok"] is True
    assert calls == ["P0", "P1", "P1", "FINALIZE"]
    service.close()


def test_projection_rejects_stale_identity_and_grants_no_visual_truth(tmp_path):
    item = identity()
    service, _db, raw = service_with_packet(tmp_path, item)
    projection = service.build_projection(
        packet_id=raw["packet_id"],
        intent={"positive": ["selection remains stable"]},
        plan={"next": "runtime replay"},
        code_targets=[{"path": "renderer.js", "digest": sha("renderer")}],
        attempts=[],
        preview=None,
        u7_result=None,
        source_drilldown=[{"path": "renderer.js", "line": 42}],
        receipt_drilldown=[{"kind": "confirmation", "id": item.confirmation_digest}],
        current_identity=item,
    )
    assert projection["projection_only"] is True
    assert projection["authority"]["visual_truth"] is False
    assert projection["authority"]["merge"] is False
    assert projection["proof"]["p0"] is None
    with pytest.raises(BilateralLiveRepairError, match="stale"):
        service.build_projection(
            packet_id=raw["packet_id"],
            intent={}, plan={}, code_targets=[], attempts=[], preview=None, u7_result=None,
            source_drilldown=[], receipt_drilldown=[], current_identity=identity("two"),
        )
    service.close()

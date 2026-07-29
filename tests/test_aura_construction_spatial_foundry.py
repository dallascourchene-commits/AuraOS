from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    RepairCandidateResult,
)
from aura_bilateral_live_repair_foundry_contracts import PROJECTION_VERSION, digest
from aura_construction_spatial_foundry import (
    ArenaBoundBilateralLiveRepairService,
    ConstructionCoordinationCandidateArtifact,
    DomainDecisionEnvelope,
    TrustedBilateralIdentityBroker,
    reject_raw_identity_currency_claim,
)
from aura_construction_spatial_foundry_server import (
    ConstructionFoundryShowcaseState,
    _static_response,
    dispatch_construction_foundry_request,
)
from aura_spatial_foundry_projection import (
    SPATIAL_FOUNDRY_PROJECTION_V2,
    build_spatial_foundry_projection_v2,
    project_guarded_wfst,
)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def git_oid(value: str) -> str:
    return sha(value)[:40]


def identity(seed: str = "one") -> BilateralIdentity:
    return BilateralIdentity(
        intent_digest=sha(f"intent-{seed}"),
        confirmation_digest=f"intent-confirmation_{sha(f'confirmation-{seed}')}",
        semantic_ledger_digest=sha(f"ledger-{seed}"),
        guardrail_set_digest=sha(f"guardrails-{seed}"),
        intent_revision_id=f"revision-{seed}",
        repository_head=git_oid(f"head-{seed}"),
        source_tree_digest=git_oid(f"tree-{seed}"),
        runtime_profile_digest=sha(f"profile-{seed}"),
        verifier_id=f"independent-verifier-{seed}",
        verifier_source_digest=sha(f"verifier-source-{seed}"),
    )


def base_projection() -> dict:
    body = {
        "version": PROJECTION_VERSION,
        "projection_only": True,
        "stale": False,
        "identity": {"identity_digest": sha("identity")},
        "confirmed_intent": {"expected_positive": ["stable"]},
        "negative_intent": ["never hide failures"],
        "guardrails": ["preserve source"],
        "plan": {"status": "READY"},
        "code_targets": [{"path": "aura_showcase/live-repair-foundry.js"}],
        "live_runtime": {"capture_id": "CAPTURE-1"},
        "incident": {"packet_id": "IRP-1"},
        "failures": [],
        "counterexamples": [],
        "repair_attempts": [],
        "preview_rollback": None,
        "proof": {"incident_packet_digest": sha("packet"), "u7": {}, "p0": None, "p1": None},
        "human_community_disposition": None,
        "source_drilldown": [],
        "receipt_drilldown": [],
        "authority": {
            "visual_truth": False,
            "patch": False,
            "commit": False,
            "push": False,
            "pull_request": False,
            "merge": False,
            "deployment": False,
            "production_mutation": False,
            "professional": False,
            "physical_work": False,
            "learning_promotion": False,
            "automatic_crystallization": False,
            "human_review_required": True,
        },
    }
    return {**body, "projection_digest": digest(body)}


def construction_candidate() -> ConstructionCoordinationCandidateArtifact:
    return ConstructionCoordinationCandidateArtifact(
        candidate_id="CC-001",
        candidate_digest=sha("candidate"),
        base_state_digest=sha("state"),
        assessment_status="READY_FOR_HUMAN_REVIEW",
        closure_count=3,
        closure_total=3,
        open_obligations=(),
        schedule_delta={"days": -2, "measurement_class": "DEMO_ESTIMATE"},
        budget_delta={"amount": 1500, "currency": "CAD", "measurement_class": "DEMO_ESTIMATE"},
        idle_time_delta={"crew_days": -4, "measurement_class": "DEMO_ESTIMATE"},
        evidence_refs=("evidence:asbestos-clearance",),
        recommended_for_human_review=True,
    )


def domain_decision() -> DomainDecisionEnvelope:
    return DomainDecisionEnvelope(
        status="READY_FOR_HUMAN_REVIEW",
        candidate_id="CC-001",
        candidate_digest=sha("candidate"),
        recommended_for_human_review=True,
        reasons=("All declared demo obligations are closed.",),
        open_obligations=(),
    )


def decoded(response):
    return response[0], json.loads(response[2].decode())


def test_v2_projection_wraps_v1_without_removing_code_targets():
    base = base_projection()
    transitions = project_guarded_wfst(
        arena_id="construction",
        current_state="REPLAY_READY",
        evidence={"runtime_proof_retained": False},
    )
    result = build_spatial_foundry_projection_v2(
        base_projection=base,
        arena_id="construction",
        domain={
            "arena_id": "construction",
            "domain_type": "CONSTRUCTION",
            "state_digest": sha("state"),
            "runtime_packet_digest": sha("runtime"),
            "adapter_version": "AURA_TEST_ADAPTER_V1",
            "privacy_class": "PRESENTATION_MINIMIZED",
        },
        domain_targets=[
            {
                "target_id": "zone-1",
                "target_type": "WORK_ZONE",
                "canonical_ref": "construction:zone-1",
                "digest": sha("zone-1"),
                "truth_class": "CANONICAL_REF",
            }
        ],
        domain_artifacts=[
            {
                "artifact_id": "scene-1",
                "artifact_type": "PASCAL_SCENE",
                "digest": sha("scene"),
                "source_ref": "artifact:scene-1",
                "coordinate_receipt_digest": sha("coordinates"),
            }
        ],
        coordination_candidates=[construction_candidate().to_dict()],
        domain_decision=domain_decision().to_dict(),
        transition_projection=transitions,
    )
    assert result["version"] == SPATIAL_FOUNDRY_PROJECTION_V2
    assert result["compatibility"]["base_projection_digest"] == base["projection_digest"]
    assert result["compatibility"]["v1_readable"] is True
    assert result["code_targets"] == base["code_targets"]
    assert result["arena_id"] == "construction"
    assert result["coordination_candidates"][0]["candidate_type"] == "CONSTRUCTION_COORDINATION"
    assert result["authority"]["physical_work_authorized"] is False
    assert result["authority"]["professional_approval"] is False
    assert result["authority"]["automatic_execution"] is False
    supplied = result["projection_digest"]
    assert digest({key: value for key, value in result.items() if key != "projection_digest"}) == supplied


def test_construction_candidate_and_repair_candidate_types_fail_closed():
    candidate = construction_candidate()
    with pytest.raises((ValueError, TypeError)):
        RepairCandidateResult.from_mapping(candidate.to_dict())
    repair = {
        "attempt_id": "RA-001",
        "replay_packet_digest": sha("packet"),
        "hypothesis_digest": sha("hypothesis"),
        "candidate_digest": sha("repair"),
        "runtime_proof_digest": sha("proof"),
        "runtime_proof_passed": True,
        "positive_passed": True,
        "negative_passed": True,
        "preservation_passed": True,
        "fault_injections_passed": True,
        "adjacent_regressions_passed": True,
        "repository_unchanged": True,
        "independent_verifier_exact": True,
        "minimized_counterexample": None,
        "failure_class": "SOURCE_ASSERTION",
        "route_class": "LOCAL",
        "promotion_ready": True,
        "archive_artifact_ref": "ATT-1",
        "created_at": 1.0,
    }
    with pytest.raises(ValueError, match="schema mismatch"):
        ConstructionCoordinationCandidateArtifact.from_mapping(repair)


def test_guarded_wfst_exposes_admitted_and_blocked_transitions_without_authority():
    admitted = project_guarded_wfst(
        arena_id="construction",
        current_state="IDLE",
        evidence={"identity_current": True, "operator_authorized": True},
    )
    assert admitted["recommended_transition"] == "START_BOUNDED_CAPTURE"
    assert admitted["admitted_transitions"][0]["execution_authority"] is False
    assert admitted["admitted_transitions"][0]["state_mutation"] is False

    blocked = project_guarded_wfst(
        arena_id="construction",
        current_state="IDLE",
        evidence={"identity_current": True},
    )
    assert blocked["recommended_transition"] is None
    assert blocked["blocked_transitions"][0]["missing_evidence"] == ["operator_authorized"]


def test_required_assets_and_exact_arena_survive_capture_and_preview(tmp_path: Path):
    item = identity()
    service = ArenaBoundBilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "attempts.db",
        runtime_runner=lambda *_args, **_kwargs: {},
        current_identity_resolver=lambda _expected: item,
        allow_reduced_runtime_fixture=True,
    )
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release-1",
            "environment_id": "browser",
            "capture_authorized": True,
            "max_events": 8,
            "retention_seconds": 120,
            "arena_id": "construction",
        }
    )
    service.mark(started["capture_id"], "coordinate receipt mismatch", {})
    finalized = service.finalize_capture(
        started["capture_id"],
        {
            "expected_positive": ["retain exact selection"],
            "expected_negative": ["never hide digest failures"],
            "preservation_claims": ["Construction truth remains unchanged"],
            "required_assets": [
                {"path": "fixtures/pascal-scene.json", "sha256": sha("scene")}
            ],
            "arena_id": "construction",
        },
    )
    packet = finalized["packet"]
    assert packet["required_assets"] == [
        {"path": "fixtures/pascal-scene.json", "sha256": sha("scene")}
    ]
    packet_id = packet["packet_id"]
    incident = service.attempt_archive.list(
        workflow_id=packet_id,
        route="bilateral-live-repair/incident-capture",
        limit=10,
    )[0]
    assert incident["arena_id"] == "construction"

    service.preview_candidate(
        packet_id=packet_id,
        current_identity=item,
        candidate_digest=sha("candidate"),
        last_verified_digest=sha("verified"),
        health_before={"ok": True},
        health_after={"ok": True},
        environment_class="LOCAL_EPHEMERAL",
        rollback_preauthorized=False,
    )
    preview = service.attempt_archive.list(
        workflow_id=packet_id,
        route="bilateral-live-repair/preview-rollback",
        limit=10,
    )[0]
    assert preview["arena_id"] == "construction"
    assert preview["arena_id"] != "coding"

    with pytest.raises(BilateralLiveRepairError, match="arena"):
        service.record_repair_attempt(
            packet_id=packet_id,
            hypothesis={"cause": "adapter"},
            candidate_digest=sha("candidate"),
            runtime_proof_ref=sha("proof"),
            minimized_counterexample=None,
            current_identity=item,
            arena_id="coding",
        )
    service.close()


def test_trusted_identity_summary_returns_handle_not_full_identity_and_stales():
    current = [identity()]
    broker = TrustedBilateralIdentityBroker(lambda: current[0])
    summary = broker.issue_summary()
    assert summary["currency"] == "SERVER_RESOLVED_CURRENT"
    assert summary["full_identity_returned"] is False
    assert "confirmation_digest" not in summary
    assert broker.resolve(summary["identity_handle"]) == current[0]
    current[0] = identity("changed")
    with pytest.raises(BilateralLiveRepairError, match="stale"):
        broker.resolve(summary["identity_handle"])


def test_raw_request_cannot_declare_identity_currency():
    with pytest.raises(BilateralLiveRepairError, match="cannot declare identity currency"):
        reject_raw_identity_currency_claim(
            {"identity_handle": "BID-1", "identity_is_current": True}
        )
    with pytest.raises(BilateralLiveRepairError, match="cannot declare identity currency"):
        reject_raw_identity_currency_claim(
            {"metadata": {"identity_currency": "CURRENT"}}
        )


def test_composed_server_issues_identity_handle_and_rejects_raw_currency(tmp_path: Path):
    item = identity()
    state = ConstructionFoundryShowcaseState(
        tmp_path,
        demo_project="demo",
        auto_start=False,
        trusted_identity_provider=lambda: item,
        current_identity_resolver=lambda _expected: item,
    )
    status, summary = decoded(
        dispatch_construction_foundry_request(
            state, "GET", "/api/showcase/live-repair/identity/current"
        )
    )
    assert status == 200
    handle = summary["identity_handle"]
    assert summary["full_identity_returned"] is False

    start_status, started = decoded(
        dispatch_construction_foundry_request(
            state,
            "POST",
            "/api/showcase/live-repair/capture/start",
            {
                "identity_handle": handle,
                "release_id": "release",
                "environment_id": "browser",
                "capture_authorized": True,
                "max_events": 4,
                "retention_seconds": 120,
            },
        )
    )
    assert start_status == 200
    assert started["arena_id"] == "construction"

    denied_status, denied = decoded(
        dispatch_construction_foundry_request(
            state,
            "POST",
            "/api/showcase/live-repair/capture/start",
            {
                "identity_handle": handle,
                "identity_is_current": True,
                "release_id": "release",
                "environment_id": "browser",
                "capture_authorized": True,
            },
        )
    )
    assert denied_status == 409
    assert "cannot declare identity currency" in denied["error"]
    state.close()


def test_composed_static_surface_adds_trusted_identity_and_required_asset_intake():
    status, content_type, body = _static_response("/index.html")
    assert status == 200
    assert content_type.startswith("text/html")
    assert body.count(b'id="construction-foundry-pr1"') == 1
    assert b'id="construction-foundry-identity-summary"' in body
    assert b'id="construction-foundry-required-assets"' in body
    assert b"construction-spatial-foundry.js" in body

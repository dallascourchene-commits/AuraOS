from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import aura_construction_spatial_foundry_server as construction_server
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
from aura_construction_adapter import ConstructionCoordinationCandidate
from aura_construction_contracts import ConstructionScope
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
    canonical = ConstructionCoordinationCandidate.create(
        scope=ConstructionScope(project_id="project-1"),
        lane="ALTERNATIVE_WORK",
        title="Sequence interior work",
        summary="Proposal-only deterministic coordination alternative",
        required_claim_ids=("claim-1",),
        declared_hard_blockers=(),
        assumptions=("Crew remains available",),
        authority_route="OWNER_REVIEW_REQUIRED",
        projected_time_delta_hours=-16.0,
        projected_cost_delta_cad=1500.0,
        projected_idle_delta_hours=-32.0,
        safety_risk=0.1,
        deadline_risk=0.2,
        evidence_quality=0.9,
        reversibility=1.0,
        measurement_class="DERIVED",
    )
    return ConstructionCoordinationCandidateArtifact(
        candidate=canonical,
        base_state_digest=sha("state"),
    )


def domain_decision() -> DomainDecisionEnvelope:
    candidate = construction_candidate()
    return DomainDecisionEnvelope(
        status="READY_FOR_HUMAN_REVIEW",
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.candidate_digest,
        recommended_for_human_review=True,
        reasons=("All declared demo obligations are closed.",),
        open_obligations=(),
    )


def decoded(response):
    return response[0], json.loads(response[2].decode())


def validate_construction_schema(value: dict) -> None:
    root = Path(__file__).resolve().parents[1]
    base_schema = json.loads(
        (root / "schemas/aura_spatial_foundry_projection_v2.schema.json").read_text(
            encoding="utf-8"
        )
    )
    construction_schema = json.loads(
        (
            root / "schemas/aura_construction_spatial_foundry_projection.schema.json"
        ).read_text(encoding="utf-8")
    )
    registry = Registry().with_resource(
        base_schema["$id"],
        Resource.from_contents(base_schema),
    )
    Draft202012Validator(construction_schema, registry=registry).validate(value)


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
    validate_construction_schema(result)


def test_v2_projection_defaults_complete_false_decision_and_validates_schema():
    transitions = project_guarded_wfst(
        arena_id="construction",
        current_state="IDLE",
        evidence={},
    )
    result = build_spatial_foundry_projection_v2(
        base_projection=base_projection(),
        arena_id="construction",
        domain={"arena_id": "construction", "domain_type": "CONSTRUCTION"},
        transition_projection=transitions,
    )
    assert result["domain_decision"]["survey_authority"] is False
    assert result["domain_decision"]["construction_truth"] is False
    validate_construction_schema(result)


def test_v2_projection_rejects_arena_authority_candidate_and_transition_tampering():
    transitions = project_guarded_wfst(
        arena_id="construction",
        current_state="IDLE",
        evidence={},
    )
    common = {
        "base_projection": base_projection(),
        "arena_id": "construction",
        "domain": {"arena_id": "construction", "domain_type": "CONSTRUCTION"},
        "transition_projection": transitions,
    }
    with pytest.raises(BilateralLiveRepairError, match="domain arena"):
        build_spatial_foundry_projection_v2(
            **{**common, "domain": {"arena_id": "coding", "domain_type": "CONSTRUCTION"}}
        )
    with pytest.raises(ValueError, match="authority"):
        build_spatial_foundry_projection_v2(
            **{
                **common,
                "domain_decision": {"physical_work_authorized": True},
            }
        )
    with pytest.raises(BilateralLiveRepairError, match="arena"):
        build_spatial_foundry_projection_v2(
            **{
                **common,
                "transition_projection": {**transitions, "arena_id": "coding"},
            }
        )
    with pytest.raises((ValueError, BilateralLiveRepairError), match="authority"):
        build_spatial_foundry_projection_v2(
            **{
                **common,
                "transition_projection": {
                    **transitions,
                    "execution_authority": True,
                },
            }
        )
    with pytest.raises(ValueError, match="software repair fields"):
        build_spatial_foundry_projection_v2(
            **{
                **common,
                "coordination_candidates": [
                    {
                        "candidate_id": "repair-shaped",
                        "candidate_type": "CONSTRUCTION_COORDINATION",
                        "promotion_ready": True,
                    }
                ],
            }
        )


def test_v2_projection_rejects_duplicate_domain_identities_and_v1_authority():
    transitions = project_guarded_wfst(
        arena_id="construction",
        current_state="IDLE",
        evidence={},
    )
    target = {
        "target_id": "zone-1",
        "target_type": "WORK_ZONE",
        "canonical_ref": "construction:zone-1",
        "digest": sha("zone"),
        "truth_class": "CANONICAL_REF",
    }
    with pytest.raises(ValueError, match="duplicates"):
        build_spatial_foundry_projection_v2(
            base_projection=base_projection(),
            arena_id="construction",
            domain={"arena_id": "construction", "domain_type": "CONSTRUCTION"},
            domain_targets=[target, {**target, "digest": sha("other")}],
            transition_projection=transitions,
        )
    unsafe = base_projection()
    unsafe["authority"]["patch"] = True
    body = {key: value for key, value in unsafe.items() if key != "projection_digest"}
    unsafe["projection_digest"] = digest(body)
    with pytest.raises(BilateralLiveRepairError, match="forbidden authority"):
        build_spatial_foundry_projection_v2(
            base_projection=unsafe,
            arena_id="construction",
            domain={"arena_id": "construction", "domain_type": "CONSTRUCTION"},
            transition_projection=transitions,
        )


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
    with pytest.raises(ValueError, match="forbidden"):
        ConstructionCoordinationCandidateArtifact.from_mapping(repair)

    tampered = candidate.to_dict()
    tampered["projected_cost_delta_cad"] = 999999.0
    with pytest.raises(ValueError, match="digest"):
        ConstructionCoordinationCandidateArtifact.from_mapping(tampered)


@pytest.mark.parametrize(
    "field",
    [
        "physical_work_authorized",
        "professional_approval",
        "payment_released",
        "access_granted",
        "automatic_execution",
        "survey_authority",
        "construction_truth",
    ],
)
def test_domain_decision_rejects_granted_authority(field: str):
    payload = {**domain_decision().to_dict(), field: True}
    with pytest.raises(ValueError, match="must remain false"):
        DomainDecisionEnvelope.from_mapping(payload)


def test_domain_decision_requires_human_review_and_safe_status():
    payload = {**domain_decision().to_dict(), "human_review_required": False}
    with pytest.raises(ValueError, match="human_review_required"):
        DomainDecisionEnvelope.from_mapping(payload)
    payload = {**domain_decision().to_dict(), "status": "PAYMENT_RELEASED"}
    with pytest.raises(ValueError, match="unsupported non-authoritative"):
        DomainDecisionEnvelope.from_mapping(payload)


def test_guarded_wfst_exposes_admitted_and_blocked_transitions_without_authority():
    admitted = project_guarded_wfst(
        arena_id="construction",
        current_state="IDLE",
        evidence={"identity_current": True, "operator_authorized": True},
    )
    assert admitted["recommended_transition"] == "START_BOUNDED_CAPTURE"
    assert admitted["arena_id"] == "construction"
    assert admitted["projection_only"] is True
    assert admitted["execution_authority"] is False
    assert admitted["state_mutation"] is False
    assert admitted["human_review_required"] is True
    assert len(admitted["state_binding_digest"]) == 64
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
    try:
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
        assert packet["required_assets"] == (
            {"path": "fixtures/pascal-scene.json", "sha256": sha("scene")},
        )
        packet_id = packet["packet_id"]
        assert started["capture_id"] not in service._capture_arena
        assert started["capture_id"] not in service._arena_archive._capture_arenas
        incident = service.attempt_archive.list(
            workflow_id=packet_id,
            route="bilateral-live-repair/incident-capture",
            limit=10,
        )[0]
        assert incident["arena_id"] == "construction"

        candidate = construction_candidate()
        with pytest.raises(BilateralLiveRepairError, match="base_state_digest"):
            service.build_projection_v2(
                packet_id=packet_id,
                intent={},
                plan={},
                code_targets=[],
                attempts=[],
                preview=None,
                u7_result=None,
                source_drilldown=[],
                receipt_drilldown=[],
                current_identity=item,
                domain={
                    "arena_id": "construction",
                    "domain_type": "CONSTRUCTION",
                    "state_digest": sha("different-state"),
                },
                coordination_candidates=[candidate],
            )
        mismatched_decision = {
            **domain_decision().to_dict(),
            "candidate_digest": sha("different-candidate"),
        }
        with pytest.raises(BilateralLiveRepairError, match="exactly one"):
            service.build_projection_v2(
                packet_id=packet_id,
                intent={},
                plan={},
                code_targets=[],
                attempts=[],
                preview=None,
                u7_result=None,
                source_drilldown=[],
                receipt_drilldown=[],
                current_identity=item,
                domain={
                    "arena_id": "construction",
                    "domain_type": "CONSTRUCTION",
                    "state_digest": sha("state"),
                },
                coordination_candidates=[candidate],
                domain_decision=mismatched_decision,
            )

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
    finally:
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


@pytest.fixture
def trusted_showcase_state(tmp_path: Path):
    item = identity()
    state = ConstructionFoundryShowcaseState(
        tmp_path,
        demo_project="demo",
        auto_start=False,
        trusted_identity_provider=lambda: item,
        current_identity_resolver=lambda _expected: item,
    )
    try:
        yield state, item
    finally:
        state.close()


def test_composed_server_issues_identity_handle_and_rejects_raw_currency(
    trusted_showcase_state,
):
    state, _item = trusted_showcase_state
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


def test_default_server_preserves_legacy_identity_flow(tmp_path: Path):
    item = identity()
    state = ConstructionFoundryShowcaseState(
        tmp_path,
        demo_project="demo",
        auto_start=False,
    )
    try:
        status, _summary = decoded(
            dispatch_construction_foundry_request(
                state, "GET", "/api/showcase/live-repair/identity/current"
            )
        )
        assert status == 409
        start_status, started = decoded(
            dispatch_construction_foundry_request(
                state,
                "POST",
                "/api/showcase/live-repair/capture/start",
                {
                    "identity": dataclasses.asdict(item),
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
    finally:
        state.close()


def test_v2_endpoint_rejects_malformed_evidence_domain_and_client_u7(
    trusted_showcase_state,
):
    state, _item = trusted_showcase_state
    _, summary = decoded(
        dispatch_construction_foundry_request(
            state, "GET", "/api/showcase/live-repair/identity/current"
        )
    )
    handle = summary["identity_handle"]
    _, started = decoded(
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
    state.live_repair.mark(started["capture_id"], "incident", {})
    finalized = state.live_repair.finalize_capture(
        started["capture_id"],
        {
            "expected_positive": ["retain evidence"],
            "expected_negative": ["never accept malformed evidence"],
            "preservation_claims": ["Construction truth remains unchanged"],
            "arena_id": "construction",
        },
    )
    packet_id = finalized["packet"]["packet_id"]

    for mutation, expected in (
        ({"domain_targets": [{"ok": True}, "bad-row"]}, "domain_targets[1]"),
        ({"domain": {"domain_type": "SPATIAL"}}, "domain.domain_type"),
        ({"u7_result": {"fabricated": True}}, "client-authored U7"),
    ):
        status, result = decoded(
            dispatch_construction_foundry_request(
                state,
                "POST",
                "/api/showcase/live-repair/projection",
                {
                    "identity_handle": handle,
                    "packet_id": packet_id,
                    "projection_version": SPATIAL_FOUNDRY_PROJECTION_V2,
                    **mutation,
                },
            )
        )
        assert status == 409
        assert expected in result["error"]


def test_identity_handle_rewrites_attempt_preview_projection_and_replay_routes(
    trusted_showcase_state,
    monkeypatch,
):
    state, item = trusted_showcase_state
    _, summary = decoded(
        dispatch_construction_foundry_request(
            state, "GET", "/api/showcase/live-repair/identity/current"
        )
    )
    handle = summary["identity_handle"]
    _, started = decoded(
        dispatch_construction_foundry_request(
            state,
            "POST",
            "/api/showcase/live-repair/capture/start",
            {
                "identity_handle": handle,
                "release_id": "release",
                "environment_id": "browser",
                "capture_authorized": True,
            },
        )
    )
    state.live_repair.mark(started["capture_id"], "incident", {})
    finalized = state.live_repair.finalize_capture(
        started["capture_id"],
        {
            "expected_positive": ["retain evidence"],
            "expected_negative": ["never accept stale identity"],
            "preservation_claims": ["Construction truth remains unchanged"],
            "arena_id": "construction",
        },
    )
    packet_id = finalized["packet"]["packet_id"]
    forwarded: list[tuple[str, dict]] = []

    def fake_dispatch(_state, _method, raw_path, payload):
        forwarded.append((raw_path, dict(payload)))
        return 200, "application/json; charset=utf-8", b'{"ok":true}'

    monkeypatch.setattr(
        construction_server,
        "base_dispatch_live_repair_request",
        fake_dispatch,
    )
    for route in (
        "/api/showcase/live-repair/attempt",
        "/api/showcase/live-repair/preview",
        "/api/showcase/live-repair/projection",
        "/api/showcase/live-repair/replay/run",
    ):
        status, result = decoded(
            dispatch_construction_foundry_request(
                state,
                "POST",
                route,
                {"packet_id": packet_id, "identity_handle": handle},
            )
        )
        assert status == 200
        assert result["ok"] is True

    assert [item[0] for item in forwarded] == [
        "/api/showcase/live-repair/attempt",
        "/api/showcase/live-repair/preview",
        "/api/showcase/live-repair/projection",
        "/api/showcase/live-repair/replay/run",
    ]
    for route, payload in forwarded:
        assert "identity_handle" not in payload
        if route != "/api/showcase/live-repair/replay/run":
            assert payload["current_identity"] == dataclasses.asdict(item)
    assert forwarded[0][1]["arena_id"] == "construction"


def test_finalize_rejects_duplicate_required_asset_paths(trusted_showcase_state):
    state, _item = trusted_showcase_state
    _, summary = decoded(
        dispatch_construction_foundry_request(
            state, "GET", "/api/showcase/live-repair/identity/current"
        )
    )
    _, started = decoded(
        dispatch_construction_foundry_request(
            state,
            "POST",
            "/api/showcase/live-repair/capture/start",
            {
                "identity_handle": summary["identity_handle"],
                "release_id": "release",
                "environment_id": "browser",
                "capture_authorized": True,
            },
        )
    )
    state.live_repair.mark(started["capture_id"], "incident", {})
    status, result = decoded(
        dispatch_construction_foundry_request(
            state,
            "POST",
            f"/api/showcase/live-repair/capture/{started['capture_id']}/finalize/v1",
            {
                "expected_positive": ["retain evidence"],
                "expected_negative": ["never accept conflicting assets"],
                "preservation_claims": ["Construction truth remains unchanged"],
                "required_assets": [
                    {"path": "scene.json", "sha256": sha("one")},
                    {"path": "scene.json", "sha256": sha("two")},
                ],
            },
        )
    )
    assert status == 409
    assert "conflicting hashes" in result["error"]


def test_composed_static_surface_adds_trusted_identity_and_required_asset_intake():
    status, content_type, body = _static_response("/index.html")
    assert status == 200
    assert content_type.startswith("text/html")
    assert body.count(b'id="construction-foundry-pr1"') == 1
    assert b'id="construction-foundry-identity-summary"' in body
    assert b'id="construction-foundry-required-assets"' in body
    assert b"construction-spatial-foundry.js" in body
    script_status, _, script = _static_response(
        "/construction-spatial-foundry.js"
    )
    assert script_status == 200
    assert b"setLegacyIdentityVisible(true)" in script
    assert b"adapter.identityBrokerAvailable" in script


def test_projection_and_request_nesting_are_bounded():
    nested: dict[str, object] = {}
    cursor = nested
    for _ in range(14):
        child: dict[str, object] = {}
        cursor["child"] = child
        cursor = child
    with pytest.raises(ValueError, match="projection nesting"):
        project_guarded_wfst(
            arena_id="construction",
            current_state="IDLE",
            evidence=nested,
        )
    with pytest.raises(BilateralLiveRepairError, match="request nesting"):
        reject_raw_identity_currency_claim(nested)


def test_abnormal_capture_expiry_releases_arena_binding(tmp_path: Path):
    item = identity()
    service = ArenaBoundBilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "expiry-attempts.db",
        current_identity_resolver=lambda _expected: item,
    )
    started = service.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release-expiry",
            "environment_id": "browser-expiry",
            "capture_authorized": True,
            "max_events": 4,
            "retention_seconds": 120,
            "arena_id": "construction",
        }
    )
    capture_id = started["capture_id"]
    assert service._capture_arena[capture_id] == "construction"
    service._expire_capture(capture_id)
    assert capture_id not in service._capture_arena
    assert capture_id not in service._arena_archive._capture_arenas
    service.close()


def test_arena_rehydrates_from_canonical_incident_row_after_restart(tmp_path: Path):
    item = identity()
    db_path = tmp_path / "restart-attempts.db"
    first = ArenaBoundBilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=db_path,
        current_identity_resolver=lambda _expected: item,
    )
    started = first.start_capture(
        {
            "identity": dataclasses.asdict(item),
            "release_id": "release-restart",
            "environment_id": "browser-restart",
            "capture_authorized": True,
            "max_events": 4,
            "retention_seconds": 120,
            "arena_id": "construction",
        }
    )
    first.mark(started["capture_id"], "restart identity check", {})
    finalized = first.finalize_capture(
        started["capture_id"],
        {
            "expected_positive": ["retain exact arena"],
            "expected_negative": ["never infer arena from a later generic row"],
            "preservation_claims": ["Attempt Archive remains canonical"],
            "arena_id": "construction",
        },
    )
    packet_id = finalized["packet"]["packet_id"]
    first.close()

    second = ArenaBoundBilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=db_path,
        current_identity_resolver=lambda _expected: item,
    )
    assert second.arena_for_packet(packet_id) == "construction"
    second.close()

from __future__ import annotations

from pathlib import Path

import pytest

from aura_model_cognome import ModelAccessClass, ModelEndpointIdentity
from aura_model_cognome_drift import (
    QUARANTINE_PROPOSED,
    STABLE,
    DriftPolicy,
    ProbeDefinition,
    ProbeResult,
    assess_drift,
    persist_drift_assessment,
)
from aura_model_cognome_federation import (
    create_federation_envelope,
    enqueue_federation_envelope,
    import_validated_envelope,
    validate_federation_envelope,
)
from aura_model_cognome_promotion import (
    PROMOTION_PROPOSED,
    PROMOTION_REJECTED,
    PromotionEvidence,
    RoutePromotionPolicy,
    crucible_route_policy_packet,
    evaluate_route_policy_promotion,
)
from aura_model_cognome_replay import (
    CASCADE,
    DIRECT,
    PANEL,
    ReplayCase,
    ReplayOutcome,
    ReplayPolicy,
    compare_replay_evaluations,
    evaluate_replay,
    persist_replay_comparison,
)
from aura_model_cognome_store import ModelCognomeStore
from aura_open_weight_jacobian_adapter import (
    JacobianLensSummary,
    build_open_weight_observation,
    persist_open_weight_observation,
)


def outcome(
    case: str,
    profile: str,
    passed: bool,
    *,
    cost: float = 1.0,
    latency: float = 100.0,
    repair: float = 0.0,
    scope: int = 0,
    policy_mode: str = "",
) -> ReplayOutcome:
    return ReplayOutcome(
        observation_id=f"obs-{case}-{profile}-{policy_mode or 'single'}",
        profile_id=profile,
        verifier_pass=passed,
        cost_usd=cost,
        time_to_verified_ms=latency,
        repair_attempts=repair,
        scope_violation_count=scope,
        evidence_digest=f"digest-{case}-{profile}-{policy_mode or 'single'}",
        policy_mode=policy_mode,
    )


def replay_case(name: str, outcomes: tuple[ReplayOutcome, ...], **kwargs) -> ReplayCase:
    return ReplayCase.create(
        task_context_id=f"task-{name}",
        evidence_split="VALIDATION",
        capability_graph_digest="graph-1",
        path_digest=f"path-{name}",
        outcomes=outcomes,
        created_at=1.0,
        **kwargs,
    )


def test_replay_rejects_training_evidence() -> None:
    with pytest.raises(ValueError, match="VALIDATION or SHADOW"):
        ReplayCase.create(
            task_context_id="task",
            evidence_split="TRAIN",
            capability_graph_digest="graph",
            path_digest="path",
        )


def test_direct_and_cascade_replay_use_recorded_outcomes_only() -> None:
    case = replay_case(
        "one",
        (
            outcome("one", "cheap", False, cost=0.1, latency=10),
            outcome("one", "strong", True, cost=1.0, latency=40),
        ),
    )
    direct = evaluate_replay((case,), ReplayPolicy.create(policy_mode=DIRECT, profile_ids=("strong",)))
    assert direct.verified_success_rate == 1.0
    assert direct.mean_cost_usd == 1.0

    cascade = evaluate_replay((case,), ReplayPolicy.create(policy_mode=CASCADE, profile_ids=("cheap", "strong")))
    result = cascade.case_results[0]
    assert result.used_profile_ids == ("cheap", "strong")
    assert result.cost_usd == 1.1
    assert result.time_to_verified_ms == 50.0


def test_panel_replay_never_synthesizes_independent_calls() -> None:
    independent = replay_case(
        "panel",
        (outcome("panel", "p1", True), outcome("panel", "p2", True)),
    )
    policy = ReplayPolicy.create(policy_mode=PANEL, profile_ids=("p1", "p2"))
    denied = evaluate_replay((independent,), policy)
    assert denied.evaluated_count == 0
    assert "independent calls are not synthesized" in denied.case_results[0].reason

    recorded_panel = replay_case(
        "panel-recorded",
        (outcome("panel-recorded", "p1", True), outcome("panel-recorded", "p2", True)),
        panel_outcome=outcome("panel-recorded", "panel-judge", True, policy_mode=PANEL),
    )
    accepted = evaluate_replay((recorded_panel,), policy)
    assert accepted.evaluated_count == 1
    assert accepted.verified_success_rate == 1.0


def test_replay_comparison_recomputes_metrics_on_common_cases() -> None:
    common = replay_case(
        "common",
        (outcome("common", "candidate", True, cost=1.0), outcome("common", "baseline", True, cost=1.0)),
    )
    candidate_only = replay_case(
        "candidate-only",
        (outcome("candidate-only", "candidate", True, cost=100.0),),
    )
    candidate = evaluate_replay(
        (common, candidate_only),
        ReplayPolicy.create(policy_mode=DIRECT, profile_ids=("candidate",)),
    )
    baseline = evaluate_replay(
        (common, candidate_only),
        ReplayPolicy.create(policy_mode=DIRECT, profile_ids=("baseline",)),
    )
    comparison = compare_replay_evaluations(candidate, baseline)
    assert comparison["common_case_count"] == 1
    assert comparison["mean_cost_delta_usd"] == 0.0
    assert comparison["success_rate_delta"] == 0.0


def test_replay_comparison_persists_in_existing_store(tmp_path: Path) -> None:
    case = replay_case(
        "persist",
        (outcome("persist", "candidate", True), outcome("persist", "baseline", False)),
    )
    candidate = evaluate_replay((case,), ReplayPolicy.create(policy_mode=DIRECT, profile_ids=("candidate",)))
    baseline = evaluate_replay((case,), ReplayPolicy.create(policy_mode=DIRECT, profile_ids=("baseline",)))
    comparison = compare_replay_evaluations(candidate, baseline)
    comparison["coverage"] = 1.0
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        comparison_id = persist_replay_comparison(store, comparison)
        row = store._conn.execute(
            "SELECT measurement_mode,approved_live,record_json FROM experiment_comparisons WHERE comparison_id=?",
            (comparison_id,),
        ).fetchone()
    assert row[0] == "REPLAY"
    assert row[1] == 0
    assert '"approved_live":false' in row[2]


def probe_definition(name: str) -> ProbeDefinition:
    return ProbeDefinition.create(
        name=name,
        prompt_digest=f"prompt-{name}",
        verifier_id="pytest",
        max_tokens=20,
        timeout_ms=1000,
    )


def probe_result(
    definition: ProbeDefinition,
    *,
    fingerprint: str,
    passed: bool = True,
    formatted: bool = True,
    latency: float = 100,
    error: str = "",
    observed_at: float = 1.0,
) -> ProbeResult:
    return ProbeResult(
        probe_id=definition.probe_id,
        profile_id="profile-drift",
        endpoint_fingerprint=fingerprint,
        verifier_pass=passed,
        format_valid=formatted,
        latency_ms=latency,
        error_class=error,
        output_digest=f"output-{definition.probe_id}-{fingerprint}-{passed}-{formatted}-{latency}-{error}",
        observed_at=observed_at,
    )


def test_drift_assessment_stable_and_quarantine_proposed() -> None:
    probes = tuple(probe_definition(str(index)) for index in range(3))
    reference = tuple(probe_result(item, fingerprint="fp-1") for item in probes)
    stable = assess_drift(reference, reference, created_at=2.0)
    assert stable.status == STABLE
    assert stable.drift_score == 0.0

    current = tuple(
        probe_result(item, fingerprint="fp-2", passed=False, formatted=False, latency=400, error="timeout")
        for item in probes
    )
    drift = assess_drift(reference, current, created_at=3.0)
    assert drift.status == QUARANTINE_PROPOSED
    assert drift.proposal_only is True
    assert drift.drift_score >= DriftPolicy().quarantine_score


def test_drift_rejects_duplicate_or_mismatched_probe_suites() -> None:
    one, two, three = (probe_definition(name) for name in ("one", "two", "three"))
    duplicate = (
        probe_result(one, fingerprint="fp"),
        probe_result(one, fingerprint="fp"),
        probe_result(two, fingerprint="fp"),
    )
    with pytest.raises(ValueError, match="duplicate"):
        assess_drift(duplicate, duplicate)

    reference = tuple(probe_result(item, fingerprint="fp") for item in (one, two, three))
    current = tuple(probe_result(item, fingerprint="fp") for item in (one, two, probe_definition("other")))
    with pytest.raises(ValueError, match="same probe IDs"):
        assess_drift(reference, current)


def test_drift_persistence_requires_explicit_named_approval(tmp_path: Path) -> None:
    endpoint = ModelEndpointIdentity.create(
        provider="test",
        requested_model="drift-model",
        endpoint_fingerprint="fp-1",
        first_seen_at=1,
        last_seen_at=1,
    )
    probes = tuple(probe_definition(str(index)) for index in range(3))
    reference = tuple(
        ProbeResult(
            probe_id=item.probe_id,
            profile_id=endpoint.profile_id,
            endpoint_fingerprint="fp-1",
            verifier_pass=True,
            format_valid=True,
            latency_ms=100,
            observed_at=1,
        )
        for item in probes
    )
    current = tuple(
        ProbeResult(
            probe_id=item.probe_id,
            profile_id=endpoint.profile_id,
            endpoint_fingerprint="fp-2",
            verifier_pass=False,
            format_valid=False,
            latency_ms=500,
            error_class="bad",
            observed_at=2,
        )
        for item in probes
    )
    assessment = assess_drift(reference, current)
    with ModelCognomeStore(db_path=tmp_path / "drift.db") as store:
        store.upsert_endpoint(endpoint)
        persist_drift_assessment(store, assessment)
        assert store.get_endpoint(endpoint.profile_id)["status"] == "ACTIVE"
        with pytest.raises(ValueError, match="approved_by"):
            persist_drift_assessment(store, assessment, approve_lifecycle_change=True)
        persist_drift_assessment(
            store,
            assessment,
            approve_lifecycle_change=True,
            approved_by="human-reviewer",
        )
        assert store.get_endpoint(endpoint.profile_id)["status"] == "QUARANTINED"


def promotion_evidence(mode: str, digest: str, **overrides) -> PromotionEvidence:
    values = {
        "measurement_mode": mode,
        "evaluated_count": 30 if mode == "REPLAY" else 15,
        "coverage": 1.0,
        "success_rate_delta": 0.05,
        "mean_cost_delta_usd": -0.1,
        "mean_time_delta_ms": -10.0,
        "mean_scope_violation_delta": 0.0,
        "drift_score": 0.05,
        "uncertainty": 0.05,
        "evidence_digest": digest,
    }
    values.update(overrides)
    return PromotionEvidence(**values)


def test_promotion_requires_independent_replay_and_shadow_evidence() -> None:
    decision = evaluate_route_policy_promotion(
        candidate_policy_id="candidate",
        candidate_policy_mode="CASCADE",
        baseline_policy_id="baseline",
        replay_evidence=promotion_evidence("REPLAY", "replay-digest"),
        shadow_evidence=promotion_evidence("SHADOW", "shadow-digest"),
        policy=RoutePromotionPolicy(),
        created_at=1.0,
    )
    assert decision.status == PROMOTION_PROPOSED
    assert decision.proposal is not None
    assert decision.proposal.required_next_gate == "VERIFIER_AND_HUMAN_REVIEW"
    assert decision.proposal.automatic_policy_promotion is False
    packet = crucible_route_policy_packet(decision)
    assert packet["runtime_authority"] is False
    assert packet["automatic_commit"] is False

    with pytest.raises(ValueError, match="independent"):
        evaluate_route_policy_promotion(
            candidate_policy_id="candidate",
            candidate_policy_mode="DIRECT",
            baseline_policy_id="baseline",
            replay_evidence=promotion_evidence("REPLAY", "same"),
            shadow_evidence=promotion_evidence("SHADOW", "same"),
        )


def test_promotion_rejects_weak_or_unknown_evidence() -> None:
    decision = evaluate_route_policy_promotion(
        candidate_policy_id="candidate",
        candidate_policy_mode="DIRECT",
        baseline_policy_id="baseline",
        replay_evidence=promotion_evidence("REPLAY", "replay", coverage=0.2),
        shadow_evidence=promotion_evidence("SHADOW", "shadow", drift_score=None),
    )
    assert decision.status == PROMOTION_REJECTED
    assert decision.proposal is None
    assert "REPLAY:minimum_coverage" in decision.denial_reasons
    assert "SHADOW:drift_known_and_bounded" in decision.denial_reasons


def test_federation_signature_expiry_replay_and_tamper_checks() -> None:
    payload = {
        "store_version": "AURA_MODEL_COGNOME_STORE_V2",
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
        "records": {},
    }

    def signer(message: bytes) -> str:
        return "sig:" + message.hex()

    def verifier(message: bytes, signature: str, sender: str) -> bool:
        return sender == "node-a" and signature == "sig:" + message.hex()

    envelope = create_federation_envelope(
        payload,
        sender_id="node-a",
        recipient_scope="community-a",
        nonce="nonce-1",
        ttl_seconds=60,
        signer=signer,
        signature_scheme="TEST",
        created_at=100,
    )
    seen: set[str] = set()
    accepted = validate_federation_envelope(
        envelope,
        allowed_senders={"node-a"},
        expected_recipient_scope="community-a",
        seen_nonces=seen,
        verifier=verifier,
        now=110,
    )
    assert accepted["ok"] is True
    replayed = validate_federation_envelope(
        envelope,
        allowed_senders={"node-a"},
        expected_recipient_scope="community-a",
        seen_nonces=seen,
        verifier=verifier,
        now=111,
    )
    assert replayed["errors"] == ["replayed_nonce"]
    expired = validate_federation_envelope(
        envelope,
        allowed_senders={"node-a"},
        expected_recipient_scope="community-a",
        verifier=verifier,
        now=200,
    )
    assert "envelope_expired" in expired["errors"]
    tampered = envelope.to_dict()
    tampered["payload"] = {"tampered": True}
    result = validate_federation_envelope(
        tampered,
        allowed_senders={"node-a"},
        expected_recipient_scope="community-a",
        verifier=verifier,
        now=110,
    )
    assert result["ok"] is False
    assert "payload_digest_mismatch" in result["errors"]


def test_federation_uses_existing_bundle_store_and_outbox(tmp_path: Path) -> None:
    source_endpoint = ModelEndpointIdentity.create(
        provider="test",
        requested_model="federated-model",
        first_seen_at=1,
        last_seen_at=1,
    )
    source_bundle = tmp_path / "source.json"
    with ModelCognomeStore(db_path=tmp_path / "source.db") as source:
        source.upsert_endpoint(source_endpoint)
        source.export_bundle(source_bundle)
    payload = __import__("json").loads(source_bundle.read_text(encoding="utf-8"))
    envelope = create_federation_envelope(
        payload,
        sender_id="node-a",
        recipient_scope="node-b",
        nonce="bundle-1",
        allow_unsigned_local=True,
        created_at=1,
    )
    with ModelCognomeStore(db_path=tmp_path / "target.db") as target:
        outbox_id = enqueue_federation_envelope(target, envelope)
        assert outbox_id
        result = import_validated_envelope(
            target,
            envelope,
            allowed_senders={"node-a"},
            expected_recipient_scope="node-b",
            allow_unsigned_local=True,
            staging_path=tmp_path / "staged.json",
            now=2,
        )
        assert result["ok"] is True
        assert target.get_endpoint(source_endpoint.profile_id)["requested_model"] == "federated-model"


def test_jacobian_adapter_is_open_weight_and_aggregate_only(tmp_path: Path) -> None:
    model_digest = "model-artifact-digest"
    endpoint = ModelEndpointIdentity.create(
        provider="local-open",
        requested_model="open-model",
        access_class=ModelAccessClass.OPEN_WEIGHT,
        endpoint_fingerprint=model_digest,
        first_seen_at=1,
        last_seen_at=1,
    )
    summary = JacobianLensSummary.create(
        model_artifact_digest=model_digest,
        method_version="jacobian-lens-v1",
        layer_start=4,
        layer_end=8,
        sample_count=12,
        metrics={"global_workspace_score": 0.8, "causal_effect_size": 0.4},
        dataset_digest="dataset",
        code_digest="code",
        created_at=2,
    )
    observation = build_open_weight_observation(endpoint, summary, call_id="analysis-1")
    assert observation.evidence_class == "MECHANISTIC_OPEN_WEIGHT"
    assert observation.extra_evidence["raw_activations_stored"] is False
    with ModelCognomeStore(db_path=tmp_path / "jacobian.db") as store:
        store.upsert_endpoint(endpoint)
        observation_id = persist_open_weight_observation(store, endpoint, observation)
        assert store.get_observation(observation_id)["evidence_class"] == "MECHANISTIC_OPEN_WEIGHT"

    closed = ModelEndpointIdentity.create(
        provider="closed",
        requested_model="closed-model",
        access_class=ModelAccessClass.BLACK_BOX,
        endpoint_fingerprint=model_digest,
        first_seen_at=1,
        last_seen_at=1,
    )
    with pytest.raises(ValueError, match="OPEN_WEIGHT"):
        build_open_weight_observation(closed, summary)
    with pytest.raises(ValueError, match="aggregate summaries only"):
        JacobianLensSummary(
            **{
                **summary.to_dict(),
                "raw_activations_stored": True,
            }
        )

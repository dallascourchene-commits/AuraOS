from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from aura_codebase_navigator import DEFAULT_SKIP_DIRS
from aura_model_cognome import ModelAccessClass, ModelEndpointIdentity
from aura_model_cognome_drift import ProbeResult, STABLE, DriftAssessment, persist_drift_assessment
from aura_model_cognome_federation import (
    FederationEnvelope,
    create_federation_envelope,
    import_validated_envelope,
    validate_federation_envelope,
)
from aura_model_cognome_promotion import RoutePromotionPolicy, evaluate_route_policy_promotion
from aura_model_cognome_replay import CASCADE, ReplayOutcome, ReplayPolicy
from aura_open_weight_jacobian_adapter import JacobianLensSummary, build_open_weight_observation


def test_codemap_excludes_generated_sandbox_vault() -> None:
    assert "Aura_Sandbox" in DEFAULT_SKIP_DIRS


def test_replay_and_probe_boolean_fields_are_strict() -> None:
    with pytest.raises(ValueError, match="boolean"):
        ReplayOutcome.from_mapping({
            "observation_id": "obs",
            "profile_id": "profile",
            "verifier_pass": "false",
            "evidence_digest": "digest",
        })
    with pytest.raises(ValueError, match="boolean"):
        ProbeResult.from_mapping({
            "probe_id": "probe",
            "profile_id": "profile",
            "endpoint_fingerprint": "fp",
            "verifier_pass": "false",
            "format_valid": True,
            "latency_ms": 1,
        })


def test_replay_policy_rejects_duplicate_profiles() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ReplayPolicy.create(policy_mode=CASCADE, profile_ids=("same", "same"))


def _signed_envelope():
    def signer(message: bytes) -> str:
        return "sig:" + message.hex()

    return create_federation_envelope(
        {"records": {}},
        sender_id="node-a",
        recipient_scope="community",
        nonce="nonce-a",
        signer=signer,
        signature_scheme="TEST",
        created_at=10,
        ttl_seconds=30,
    )


def test_federation_rejects_tampered_identity_and_string_authority_flags() -> None:
    envelope = _signed_envelope()
    tampered = envelope.to_dict()
    tampered["envelope_id"] = "forged-id"
    result = validate_federation_envelope(
        tampered,
        allowed_senders={"node-a"},
        expected_recipient_scope="community",
        verifier=lambda message, signature, sender: True,
        now=20,
    )
    assert result["ok"] is False
    assert "envelope_invalid" in result["errors"]

    invalid_flag = envelope.to_dict()
    invalid_flag["runtime_authority"] = "false"
    with pytest.raises(ValueError, match="boolean"):
        FederationEnvelope.from_mapping(invalid_flag)


def test_federation_requires_finite_timing_and_consumes_nonce_after_import(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="finite"):
        create_federation_envelope(
            {"records": {}},
            sender_id="node-a",
            recipient_scope="community",
            nonce="nonce-inf",
            ttl_seconds=float("inf"),
            allow_unsigned_local=True,
        )

    class FailingStore:
        def import_bundle(self, path: Path):
            raise RuntimeError("import failed")

    envelope = create_federation_envelope(
        {"records": {}},
        sender_id="node-a",
        recipient_scope="community",
        nonce="nonce-import",
        allow_unsigned_local=True,
        created_at=10,
    )
    seen: set[str] = set()
    with pytest.raises(RuntimeError, match="import failed"):
        import_validated_envelope(
            FailingStore(),
            envelope,
            allowed_senders={"node-a"},
            expected_recipient_scope="community",
            seen_nonces=seen,
            allow_unsigned_local=True,
            staging_path=tmp_path / "manual-review-import.json",
            now=20,
        )
    assert "nonce-import" not in seen


def test_drift_approval_only_applies_to_lifecycle_proposals() -> None:
    assessment = DriftAssessment(
        assessment_id="assessment",
        profile_id="profile",
        reference_fingerprint="fp",
        current_fingerprint="fp",
        reference_count=3,
        current_count=3,
        drift_score=0.0,
        status=STABLE,
        metric_deltas={},
        evidence_digest="digest",
        policy_version="test",
        created_at=1,
    )
    with pytest.raises(ValueError, match="only stale or quarantine"):
        persist_drift_assessment(
            object(), assessment, approve_lifecycle_change=True, approved_by="reviewer"
        )


def test_promotion_thresholds_and_policy_identity_are_safe() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        RoutePromotionPolicy(maximum_cost_increase_usd=-1)
    with pytest.raises(ValueError, match="must differ"):
        evaluate_route_policy_promotion(
            candidate_policy_id="same",
            candidate_policy_mode="DIRECT",
            baseline_policy_id="same",
            replay_evidence={},
            shadow_evidence={},
        )


def test_jacobian_summary_is_content_addressed_and_privacy_flags_are_strict() -> None:
    summary = JacobianLensSummary.create(
        model_artifact_digest="model-fp",
        method_version="test",
        layer_start=1,
        layer_end=2,
        sample_count=3,
        metrics={"workspace_rank": 1},
        created_at=1,
    )
    tampered = summary.to_dict()
    tampered["summary_id"] = "forged-summary"
    with pytest.raises(ValueError, match="summary_id"):
        JacobianLensSummary.from_mapping(tampered)

    invalid_flag = summary.to_dict()
    invalid_flag["raw_prompts_stored"] = "false"
    with pytest.raises(ValueError, match="boolean"):
        JacobianLensSummary.from_mapping(invalid_flag)

    endpoint = ModelEndpointIdentity.create(
        provider="test",
        requested_model="open-model",
        access_class=ModelAccessClass.OPEN_WEIGHT,
        endpoint_fingerprint="model-fp",
        first_seen_at=1,
        last_seen_at=1,
    )
    with pytest.raises(ValueError, match="artifact fingerprint"):
        build_open_weight_observation(replace(endpoint, endpoint_fingerprint=""), summary)

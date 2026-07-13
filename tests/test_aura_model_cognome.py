from __future__ import annotations

import pytest

from aura_model_cognome import (
    BEHAVIORAL_SURROGATE,
    MECHANISTIC_OPEN_WEIGHT,
    CapabilityPosterior,
    ModelAccessClass,
    ModelCapabilityEdge,
    ModelEndpointIdentity,
    ModelObservation,
    RouteDecision,
    TaskContext,
    canonical_json,
    stable_digest,
    validate_evidence_claim,
)


def test_endpoint_identity_is_stable_and_uses_identity_fingerprint_by_default() -> None:
    first = ModelEndpointIdentity.create(provider="Fireworks", requested_model="glm")
    second = ModelEndpointIdentity.create(provider="fireworks", requested_model="glm")
    assert first.profile_id == second.profile_id
    assert first.endpoint_fingerprint == second.endpoint_fingerprint
    assert first.access_class == "BLACK_BOX"
    assert first.fingerprint_version == "identity-v1"
    assert "api_key" not in canonical_json(first.to_dict()).lower()


def test_endpoint_returned_model_can_drift_without_changing_profile_identity() -> None:
    first = ModelEndpointIdentity.create(provider="api", requested_model="alias", returned_model="v1")
    second = ModelEndpointIdentity.create(provider="api", requested_model="alias", returned_model="v2")
    assert first.profile_id == second.profile_id
    assert first.endpoint_fingerprint != second.endpoint_fingerprint


def test_invalid_endpoint_enums_fail_closed() -> None:
    with pytest.raises(ValueError):
        ModelEndpointIdentity.create(provider="api", requested_model="x", access_class="MAYBE")
    with pytest.raises(ValueError):
        ModelEndpointIdentity.create(provider="api", requested_model="x", status="BROKEN")


def test_task_context_hashes_objective_and_all_route_relevant_fields() -> None:
    purpose = stable_digest({"authority": "human"})
    first = TaskContext.create(
        objective="Refactor the model router",
        purpose_digest=purpose,
        task_family="code_refactor",
        required_capability_ids=("aura.agent_arena.bridge",),
        privacy_class="LOCAL_ONLY",
    )
    second = TaskContext.create(
        objective="Refactor the model router",
        purpose_digest=purpose,
        task_family="code_refactor",
        required_capability_ids=("aura.agent_arena.bridge",),
        privacy_class="PUBLIC",
    )
    encoded = canonical_json(first.to_dict())
    assert "Refactor the model router" not in encoded
    assert first.task_context_id != second.task_context_id


def test_route_and_observation_ids_include_event_time() -> None:
    purpose = stable_digest({"authority": "human"})
    first = RouteDecision.create(
        task_context_id="task", purpose_digest=purpose, policy_mode="DIRECT",
        policy_version="v1", created_at=1.0,
    )
    second = RouteDecision.create(
        task_context_id="task", purpose_digest=purpose, policy_mode="DIRECT",
        policy_version="v1", created_at=2.0,
    )
    assert first.route_decision_id != second.route_decision_id
    obs1 = ModelObservation.create(profile_id="p", call_id="c", created_at=1.0)
    obs2 = ModelObservation.create(profile_id="p", call_id="c", created_at=2.0)
    assert obs1.observation_id != obs2.observation_id


def test_zero_model_cannot_select_a_profile() -> None:
    with pytest.raises(ValueError):
        RouteDecision.create(
            task_context_id="task",
            purpose_digest="purpose",
            policy_mode="ZERO_MODEL",
            policy_version="v1",
            selected_profile_ids=("profile",),
        )


def test_model_capability_edge_validates_quantiles_and_probabilities() -> None:
    endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
    edge = ModelCapabilityEdge.create(
        profile_id=endpoint.profile_id,
        aura_capability_id="aura.agent_arena.bridge",
        task_bucket="localization",
        support_level="VALIDATED",
        verified_success_probability=0.8,
        p50_time_to_verified_ms=100,
        p95_time_to_verified_ms=200,
    )
    assert edge.edge_id.startswith("model-capability-edge_")
    with pytest.raises(ValueError):
        ModelCapabilityEdge.create(
            profile_id=endpoint.profile_id,
            aura_capability_id="aura.agent_arena.bridge",
            task_bucket="localization",
            support_level="VALIDATED",
            verified_success_probability=1.5,
        )


def test_closed_models_cannot_claim_mechanistic_jspace() -> None:
    validate_evidence_claim(ModelAccessClass.BLACK_BOX, BEHAVIORAL_SURROGATE)
    with pytest.raises(ValueError):
        validate_evidence_claim(ModelAccessClass.BLACK_BOX, MECHANISTIC_OPEN_WEIGHT)
    validate_evidence_claim(ModelAccessClass.OPEN_WEIGHT, MECHANISTIC_OPEN_WEIGHT)


def test_beta_posterior_update_keeps_split_separate() -> None:
    posterior = CapabilityPosterior(
        profile_id="p",
        task_bucket="coding",
        context_bucket="small",
        verifier_id="tests",
        validation_split="SHADOW",
        verified_success_alpha=9,
        verified_success_beta=3,
    )
    assert posterior.verified_success_mean == 0.75
    updated = posterior.update_verified_outcome(True, evidence_digest="e", validated_at=10)
    assert updated.sample_count == 1
    assert updated.verified_success_alpha == 10
    assert updated.validation_split == "SHADOW"

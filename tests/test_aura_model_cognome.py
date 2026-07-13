from __future__ import annotations

import pytest

from aura_model_cognome import (
    BEHAVIORAL_SURROGATE,
    MECHANISTIC_OPEN_WEIGHT,
    CapabilityPosterior,
    ModelAccessClass,
    ModelCapabilityEdge,
    ModelEndpointIdentity,
    TaskContext,
    canonical_json,
    stable_digest,
    validate_evidence_claim,
)


def test_endpoint_identity_is_stable_and_secret_free() -> None:
    first = ModelEndpointIdentity.create(provider="Fireworks", requested_model="glm")
    second = ModelEndpointIdentity.create(provider="fireworks", requested_model="glm")
    assert first.profile_id == second.profile_id
    assert first.endpoint_fingerprint == second.endpoint_fingerprint
    assert first.access_class == "BLACK_BOX"
    assert "api" not in canonical_json(first.to_dict()).lower()


def test_task_context_hashes_objective_without_storing_plaintext() -> None:
    context = TaskContext.create(
        objective="Refactor the model router",
        purpose_digest=stable_digest({"authority": "human"}),
        task_family="code_refactor",
        required_capability_ids=("aura.agent_arena.bridge",),
    )
    encoded = canonical_json(context.to_dict())
    assert "Refactor the model router" not in encoded
    assert context.required_capability_ids == ("aura.agent_arena.bridge",)


def test_model_capability_edge_id_is_task_conditioned() -> None:
    endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
    edge = ModelCapabilityEdge.create(
        profile_id=endpoint.profile_id,
        aura_capability_id="aura.agent_arena.bridge",
        task_bucket="localization",
        support_level="VALIDATED",
    )
    assert edge.edge_id.startswith("model-capability-edge_")
    assert edge.aura_capability_id == "aura.agent_arena.bridge"


def test_closed_models_cannot_claim_mechanistic_jspace() -> None:
    validate_evidence_claim(ModelAccessClass.BLACK_BOX, BEHAVIORAL_SURROGATE)
    with pytest.raises(ValueError):
        validate_evidence_claim(ModelAccessClass.BLACK_BOX, MECHANISTIC_OPEN_WEIGHT)
    validate_evidence_claim(ModelAccessClass.OPEN_WEIGHT, MECHANISTIC_OPEN_WEIGHT)


def test_beta_posterior_mean() -> None:
    posterior = CapabilityPosterior(
        profile_id="p",
        task_bucket="coding",
        context_bucket="small",
        verifier_id="tests",
        verified_success_alpha=9,
        verified_success_beta=3,
    )
    assert posterior.verified_success_mean == 0.75

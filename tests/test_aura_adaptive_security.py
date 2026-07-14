from __future__ import annotations

from aura_model_cognome_execution_auth import ExecutionAuthorization
from aura_model_cognome_store import ModelCognomeStore
from aura_shadow_model_router import DIRECT


def test_paired_live_claim_survives_process_restart(tmp_path) -> None:
    comparison = {
        "comparison_id": "paired_live_claim",
        "measurement_mode": "PAIRED_LIVE",
        "approved_live": True,
        "approved_by": "Dallas",
        "authorization_id": "authorization",
        "purpose_digest": "purpose",
        "capability_graph_digest": "graph",
        "created_at": 1.0,
    }
    with ModelCognomeStore(tmp_path) as store:
        assert store.record_experiment_comparison(comparison) == "paired_live_claim"
    with ModelCognomeStore(tmp_path) as store:
        assert store.record_experiment_comparison(comparison) == ""


def test_paired_live_approval_rejects_string_truthiness(tmp_path) -> None:
    comparison = {
        "comparison_id": "invalid_claim",
        "measurement_mode": "PAIRED_LIVE",
        "approved_live": "false",
        "created_at": 1.0,
    }
    with ModelCognomeStore(tmp_path) as store:
        try:
            store.record_experiment_comparison(comparison)
        except ValueError as exc:
            assert "boolean" in str(exc)
        else:
            raise AssertionError("string approval was treated as truthy")


def test_execution_authorization_requires_explicit_model_profiles() -> None:
    try:
        ExecutionAuthorization.create(
            approved_by="Dallas",
            verifier_id="verifier",
            purpose_digest="purpose",
            capability_graph_digest="graph",
            allowed_policy_modes=[DIRECT],
            nonce="nonce",
            issued_at=1.0,
            expires_at=2.0,
            max_calls=1,
        )
    except ValueError as exc:
        assert "profile allowlist" in str(exc)
    else:
        raise AssertionError("model execution was authorized without explicit profiles")


def test_execution_authorization_rejects_empty_profile_values() -> None:
    try:
        ExecutionAuthorization.create(
            approved_by="Dallas",
            verifier_id="verifier",
            purpose_digest="purpose",
            capability_graph_digest="graph",
            allowed_policy_modes=[DIRECT],
            allowed_profile_ids=[""],
            nonce="nonce",
            issued_at=1.0,
            expires_at=2.0,
            max_calls=1,
        )
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty endpoint profile was authorized")


def test_execution_authorization_rejects_content_tampering() -> None:
    authorization = ExecutionAuthorization.create(
        approved_by="Dallas",
        verifier_id="verifier",
        purpose_digest="purpose",
        capability_graph_digest="graph",
        allowed_policy_modes=[DIRECT],
        allowed_profile_ids=["profile-a"],
        nonce="nonce",
        issued_at=1.0,
        expires_at=2.0,
        max_calls=1,
    )
    tampered = authorization.to_dict()
    tampered["allowed_profile_ids"] = ["profile-b"]

    try:
        ExecutionAuthorization.from_mapping(tampered)
    except ValueError as exc:
        assert "authorization_id" in str(exc)
    else:
        raise AssertionError("tampered authorization was accepted")

def test_paired_live_comparison_id_is_authorization_bound() -> None:
    from aura_adaptive_model_executor import paired_live_comparison_id

    first = paired_live_comparison_id("authorization-a")
    second = paired_live_comparison_id("authorization-a")
    different = paired_live_comparison_id("authorization-b")
    assert first == second
    assert first != different


def test_topology_hub_ties_are_sorted_by_node_id(tmp_path) -> None:
    from aura_topology_manager import TopologyBuilder

    builder = TopologyBuilder(tmp_path)
    builder.nodes = [{"id": node_id} for node_id in ("c", "a", "b")]
    builder._node_ids = {"a", "b", "c"}
    builder.edges = [
        {"source": "a", "target": "b", "kind": "call"},
        {"source": "b", "target": "c", "kind": "call"},
        {"source": "c", "target": "a", "kind": "call"},
    ]

    hubs = builder._compute_diagnostics()["top_hubs"]
    assert [item["id"] for item in hubs] == ["a", "b", "c"]

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

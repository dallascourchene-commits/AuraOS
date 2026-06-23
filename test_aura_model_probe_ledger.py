from pathlib import Path

from aura_model_probe_ledger import (
    AuraModelProbeLedger,
    ModelProbeProfile,
    deterministic_probe_packets,
    score_model,
)


def test_model_probe_score_uses_weighted_equation():
    profile = ModelProbeProfile(
        provider="mock",
        model="m1",
        role="WORKER",
        historical_quality=1.0,
        capsule_comprehension=1.0,
        json_success=1.0,
        role_affinity=1.0,
        latency_score=1.0,
        cost_score=1.0,
        failure_penalty=0.0,
    )
    assert score_model(profile) == 1.0

    low = profile.to_dict()
    low["failure_penalty"] = 1.0
    assert score_model(low) == 0.8


def test_probe_ledger_appends_and_returns_latest(tmp_path: Path):
    path = tmp_path / "probe.jsonl"
    ledger = AuraModelProbeLedger(path=str(path))
    row = ledger.append(ModelProbeProfile(provider="mock", model="m1", role="VERIFIER", json_success=0.9))

    assert path.exists()
    assert row["routing_score"] == ledger.score_agent("mock", "m1", "VERIFIER")
    assert deterministic_probe_packets()

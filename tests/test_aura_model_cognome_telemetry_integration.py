from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aura_empirical_cost_ledger import EmpiricalCostLedger
from aura_model_cognome import ModelEndpointIdentity
from aura_model_cognome_call_logger import NormalizedCallLogger
from aura_model_cognome_store import ModelCognomeStore
from aura_model_cognome_telemetry import (
    StageTimings,
    TelemetryLinkage,
    build_telemetry_packet,
    persist_telemetry_packet,
)
from aura_pricing_registry import PricingRegistry


@dataclass
class FakeSavingsDB:
    calls: list[dict[str, Any]] = field(default_factory=list)

    def insert_llm_call(self, **kwargs: Any) -> int:
        self.calls.append(dict(kwargs))
        return len(self.calls)


def test_replayed_packet_is_one_logical_call_across_all_stores(tmp_path: Path) -> None:
    endpoint = ModelEndpointIdentity.create(provider="fireworks", requested_model="unknown-model")
    linkage = TelemetryLinkage.create(
        correlation_id="correlation",
        profile_id=endpoint.profile_id,
        event_nonce="provider-request-id",
    )
    packet = build_telemetry_packet(
        linkage=linkage,
        provider="fireworks",
        model="unknown-model",
        raw_usage={},
        timings=StageTimings(queue_ms=5, generation_ms=50, verifier_ms=10),
        pricing_registry=PricingRegistry(tmp_path),
        policy_mode="DIRECT",
        verifier_pass=False,
        failure_class="USAGE_UNAVAILABLE",
    )
    savings = FakeSavingsDB()
    logger = NormalizedCallLogger(db=savings, mode="DIRECT")

    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as cognome:
        cognome.upsert_endpoint(endpoint)
        with EmpiricalCostLedger(tmp_path) as empirical:
            first = persist_telemetry_packet(
                packet,
                cognome_store=cognome,
                empirical_ledger=empirical,
                logger_sink=logger,
            )
            second = persist_telemetry_packet(
                packet,
                cognome_store=cognome,
                empirical_ledger=empirical,
                logger_sink=logger,
            )
            assert first["observation_id"] == second["observation_id"]
            assert first["cost_run_id"] == second["cost_run_id"]
            assert len(empirical.get_by_call_id(linkage.call_id)) == 1
            run = empirical.get_run(linkage.cost_run_id)
            assert run is not None
            assert run["calculated_cost_usd"] is None
            assert run["cost_status"] == "COST_UNKNOWN"

        observation = cognome.get_observation(packet.observation.observation_id)
        assert observation is not None
        assert observation["cost_usd"] is None
        assert observation["time_to_verified_outcome_ms"] is None

    assert len(savings.calls) == 1
    assert savings.calls[0]["cost_usd"] is None
    assert savings.calls[0]["metadata"]["call_id"] == linkage.call_id

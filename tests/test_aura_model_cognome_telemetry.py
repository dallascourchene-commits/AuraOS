from __future__ import annotations

from pathlib import Path

import pytest

from aura_empirical_cost_ledger import EmpiricalCostLedger
from aura_model_cognome import ModelEndpointIdentity
from aura_model_cognome_store import ModelCognomeStore
from aura_model_cognome_telemetry import (
    StageTimings,
    TelemetryLinkage,
    build_telemetry_packet,
    calculate_normalized_cost,
    normalize_usage_with_provenance,
    persist_telemetry_packet,
)
from aura_pricing_registry import (
    COST_CALCULATED,
    COST_LOCAL_ZERO,
    COST_MEASURED,
    COST_UNKNOWN,
    PricingRegistry,
)


def test_unknown_usage_remains_none_and_cost_unknown(tmp_path: Path) -> None:
    usage = normalize_usage_with_provenance({}, provider="fireworks", model="unknown")
    assert usage["input_tokens"] is None
    assert usage["output_tokens"] is None
    assert usage["field_measurement_classes"]["input_tokens"] == "UNAVAILABLE"
    cost = calculate_normalized_cost(usage, pricing_registry=PricingRegistry(tmp_path))
    assert cost["cost_usd"] is None
    assert cost["cost_status"] == COST_UNKNOWN


def test_derived_total_has_field_level_provenance() -> None:
    usage = normalize_usage_with_provenance(
        {"prompt_tokens": 10, "completion_tokens": 4},
        provider="fireworks",
        model="accounts/fireworks/models/glm-5p2",
    )
    assert usage["total_tokens"] == 14
    assert usage["field_measurement_classes"]["input_tokens"] == "MEASURED"
    assert usage["field_measurement_classes"]["output_tokens"] == "MEASURED"
    assert usage["field_measurement_classes"]["total_tokens"] == "DERIVED"


def test_provider_billed_cost_precedes_registry(tmp_path: Path) -> None:
    usage = normalize_usage_with_provenance(
        {"prompt_tokens": 10, "completion_tokens": 4},
        provider="fireworks",
        model="accounts/fireworks/models/glm-5p2",
    )
    usage["provider_reported_cost_usd"] = 0.123
    cost = calculate_normalized_cost(usage, pricing_registry=PricingRegistry(tmp_path))
    assert cost["cost_usd"] == 0.123
    assert cost["cost_status"] == COST_MEASURED
    assert cost["price_snapshot"] is None


def test_calculated_cost_pins_price_snapshot(tmp_path: Path) -> None:
    usage = normalize_usage_with_provenance(
        {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
        provider="fireworks",
        model="accounts/fireworks/models/glm-5p2",
    )
    cost = calculate_normalized_cost(usage, pricing_registry=PricingRegistry(tmp_path))
    assert cost["cost_status"] == COST_CALCULATED
    assert cost["cost_usd"] == 1.8
    assert cost["price_snapshot_digest"]


def test_local_api_cost_is_explicitly_zero() -> None:
    usage = normalize_usage_with_provenance(
        {"input_tokens": 10, "output_tokens": 2, "runtime_ms": 50},
        provider="local",
        model="qwen",
    )
    cost = calculate_normalized_cost(usage, pricing_registry=PricingRegistry("."))
    assert cost["cost_usd"] == 0.0
    assert cost["cost_status"] == COST_LOCAL_ZERO


def test_time_to_verified_excludes_human_wait() -> None:
    timings = StageTimings(
        router_decision_ms=5,
        queue_ms=10,
        connect_ms=5,
        time_to_first_token_ms=20,
        generation_ms=100,
        verifier_ms=10,
        retry_ms=30,
        fallback_ms=40,
        human_wait_ms=5_000,
    )
    assert timings.machine_total_ms() == 220
    assert timings.time_to_verified_outcome_ms(True) == 220
    assert timings.workflow_wall_ms() == 5_220
    assert timings.time_to_verified_outcome_ms(False) is None


def test_invalid_stage_timing_fails_closed() -> None:
    with pytest.raises(ValueError):
        StageTimings(queue_ms=-1)
    with pytest.raises(ValueError):
        StageTimings(queue_ms=float("nan"))


def test_linkage_is_idempotent_and_attempt_conditioned() -> None:
    first = TelemetryLinkage.create(correlation_id="c", profile_id="p", attempt_index=0)
    replay = TelemetryLinkage.create(correlation_id="c", profile_id="p", attempt_index=0)
    retry = TelemetryLinkage.create(correlation_id="c", profile_id="p", attempt_index=1)
    assert first.call_id == replay.call_id
    assert first.cost_run_id == replay.cost_run_id
    assert first.call_id != retry.call_id


def test_packet_captures_repair_fallback_and_throughput(tmp_path: Path) -> None:
    linkage = TelemetryLinkage.create(
        correlation_id="corr",
        profile_id="profile",
        attempt_index=1,
        fallback_index=1,
    )
    packet = build_telemetry_packet(
        linkage=linkage,
        provider="fireworks",
        model="accounts/fireworks/models/glm-5p2",
        raw_usage={"prompt_tokens": 100, "completion_tokens": 50},
        timings=StageTimings(generation_ms=1_000, verifier_ms=20, retry_ms=30, fallback_ms=40),
        pricing_registry=PricingRegistry(tmp_path),
        policy_mode="CASCADE",
        verifier_pass=True,
        repair_attempt_count=1,
    )
    assert packet.observation.output_tokens_per_second == 50.0
    assert packet.observation.time_to_verified_outcome_ms == 1_090
    assert packet.observation.retry_ms == 30
    assert packet.observation.fallback_ms == 40
    assert packet.cost_run["call_id"] == linkage.call_id
    assert packet.cost_run["observation_id"] == packet.observation.observation_id


def test_persistence_links_cognome_and_empirical_ledger(tmp_path: Path) -> None:
    endpoint = ModelEndpointIdentity.create(provider="fireworks", requested_model="accounts/fireworks/models/glm-5p2")
    linkage = TelemetryLinkage.create(correlation_id="corr", profile_id=endpoint.profile_id)
    packet = build_telemetry_packet(
        linkage=linkage,
        provider="fireworks",
        model="accounts/fireworks/models/glm-5p2",
        raw_usage={"prompt_tokens": 100, "completion_tokens": 50},
        timings=StageTimings(queue_ms=5, generation_ms=100, verifier_ms=10),
        pricing_registry=PricingRegistry(tmp_path),
        policy_mode="DIRECT",
        verifier_pass=True,
    )
    logged: list[dict] = []
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        store.upsert_endpoint(endpoint)
        ledger = EmpiricalCostLedger(tmp_path)
        result = persist_telemetry_packet(
            packet,
            cognome_store=store,
            empirical_ledger=ledger,
            logger_sink=logged.append,
        )
        assert result["observation_id"] == packet.observation.observation_id
        assert result["cost_run_id"] == linkage.cost_run_id
        assert store.get_observation(packet.observation.observation_id)["call_id"] == linkage.call_id
        assert ledger.get_run(linkage.cost_run_id)["run_id"] == linkage.cost_run_id
        assert logged[0]["cost_status"] == COST_CALCULATED
        ledger.close()


def test_persistence_rejects_unknown_profile(tmp_path: Path) -> None:
    packet = build_telemetry_packet(
        linkage=TelemetryLinkage.create(correlation_id="corr", profile_id="missing"),
        provider="fireworks",
        model="accounts/fireworks/models/glm-5p2",
        raw_usage={"prompt_tokens": 1, "completion_tokens": 1},
        timings=StageTimings(generation_ms=10),
        pricing_registry=PricingRegistry(tmp_path),
    )
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        with pytest.raises(ValueError, match="Unknown Cognome profile"):
            persist_telemetry_packet(packet, cognome_store=store)

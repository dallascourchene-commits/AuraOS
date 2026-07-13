from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from aura_model_cognome_call_logger import NormalizedCallLogger, log_normalized_call


@dataclass
class FakeSavingsDB:
    calls: list[dict[str, Any]] = field(default_factory=list)

    def insert_llm_call(self, **kwargs: Any) -> int:
        self.calls.append(dict(kwargs))
        return len(self.calls)


def _record(**overrides: Any) -> dict[str, Any]:
    record = {
        "call_id": "call-1",
        "correlation_id": "correlation-1",
        "route_decision_id": "route-1",
        "task_context_id": "task-1",
        "profile_id": "profile-1",
        "cost_run_id": "cost-run-1",
        "experience_id": "experience-1",
        "provider": "fireworks",
        "model": "glm",
        "input_tokens": None,
        "output_tokens": 12,
        "cost_usd": None,
        "cost_status": "COST_UNKNOWN",
        "latency_ms": 100.0,
        "time_to_verified_outcome_ms": None,
        "measurement_class": "UNAVAILABLE",
        "field_measurement_classes": {
            "input_tokens": "UNAVAILABLE",
            "output_tokens": "MEASURED",
        },
    }
    record.update(overrides)
    return record


def test_unknown_cost_remains_none_in_existing_call_store() -> None:
    db = FakeSavingsDB()
    result = log_normalized_call(_record(), db=db, mode="DIRECT")
    assert result["cost_usd"] is None
    assert result["cost_status"] == "COST_UNKNOWN"
    assert db.calls[0]["cost_usd"] is None
    assert db.calls[0]["input_tokens"] is None
    assert db.calls[0]["mode"] == "DIRECT"


def test_linkage_and_measurement_provenance_are_preserved_in_metadata() -> None:
    db = FakeSavingsDB()
    log_normalized_call(_record(), db=db)
    metadata = db.calls[0]["metadata"]
    assert metadata["call_id"] == "call-1"
    assert metadata["correlation_id"] == "correlation-1"
    assert metadata["route_decision_id"] == "route-1"
    assert metadata["task_context_id"] == "task-1"
    assert metadata["profile_id"] == "profile-1"
    assert metadata["cost_run_id"] == "cost-run-1"
    assert metadata["experience_id"] == "experience-1"
    assert metadata["field_measurement_classes"]["input_tokens"] == "UNAVAILABLE"


def test_callable_logger_suppresses_duplicate_logical_call_in_process() -> None:
    db = FakeSavingsDB()
    logger = NormalizedCallLogger(db=db)
    first = logger(_record())
    second = logger(_record())
    assert first["duplicate_suppressed"] is False
    assert second["duplicate_suppressed"] is True
    assert len(db.calls) == 1


def test_distinct_call_ids_are_recorded() -> None:
    db = FakeSavingsDB()
    logger = NormalizedCallLogger(db=db)
    logger(_record(call_id="call-1"))
    logger(_record(call_id="call-2"))
    assert len(db.calls) == 2


def test_required_fields_and_nonnegative_metrics_fail_closed() -> None:
    with pytest.raises(ValueError, match="missing"):
        log_normalized_call(_record(call_id=""), db=FakeSavingsDB())
    with pytest.raises(ValueError, match="input_tokens"):
        log_normalized_call(_record(input_tokens=-1), db=FakeSavingsDB())
    with pytest.raises(ValueError, match="cost_usd"):
        log_normalized_call(_record(cost_usd=-0.1), db=FakeSavingsDB())

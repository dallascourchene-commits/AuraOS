"""Compatibility adapter from Cognome telemetry to Aura's existing call logger DB.

The adapter consumes an already normalized logger record. It never estimates
usage or price and therefore cannot turn missing cost into zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
LOGGER_ADAPTER_VERSION = "AURA_MODEL_COGNOME_CALL_LOGGER_V1"


class SavingsCallStore(Protocol):
    def insert_llm_call(
        self,
        provider: str,
        model: str,
        operation: str,
        mode: str,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
        latency_ms: float | None,
        request_chars: int,
        response_chars: int,
        metadata: dict[str, Any] | None = None,
    ) -> Any: ...


_REQUIRED_KEYS = frozenset({"call_id", "provider", "model", "cost_status"})


def _validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(record)
    missing = sorted(key for key in _REQUIRED_KEYS if not str(data.get(key, "")).strip())
    if missing:
        raise ValueError("Normalized call record is missing: " + ", ".join(missing))
    for name in ("input_tokens", "output_tokens"):
        value = data.get(name)
        if value is not None and int(value) < 0:
            raise ValueError(f"{name} must be non-negative or None")
    for name in ("cost_usd", "latency_ms", "time_to_verified_outcome_ms"):
        value = data.get(name)
        if value is not None and float(value) < 0:
            raise ValueError(f"{name} must be non-negative or None")
    return data


def log_normalized_call(
    record: Mapping[str, Any],
    *,
    db: SavingsCallStore | None = None,
    operation: str = "model_cognome",
    mode: str = "",
) -> dict[str, Any]:
    """Write one normalized logical model call to Aura's existing savings DB."""
    data = _validate_record(record)
    if db is None:
        from aura_savings_db import AuraSavingsDB

        db = AuraSavingsDB()
    metadata = {
        "telemetry_version": LOGGER_ADAPTER_VERSION,
        "call_id": data["call_id"],
        "correlation_id": data.get("correlation_id", ""),
        "route_decision_id": data.get("route_decision_id", ""),
        "task_context_id": data.get("task_context_id", ""),
        "profile_id": data.get("profile_id", ""),
        "cost_run_id": data.get("cost_run_id", ""),
        "experience_id": data.get("experience_id", ""),
        "cost_status": data["cost_status"],
        "measurement_class": data.get("measurement_class", "UNAVAILABLE"),
        "field_measurement_classes": data.get("field_measurement_classes", {}),
        "time_to_verified_outcome_ms": data.get("time_to_verified_outcome_ms"),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    result = db.insert_llm_call(
        provider=str(data["provider"]),
        model=str(data["model"]),
        operation=str(operation),
        mode=str(mode or data.get("policy_mode", "")),
        input_tokens=data.get("input_tokens"),
        output_tokens=data.get("output_tokens"),
        cost_usd=data.get("cost_usd"),
        latency_ms=data.get("latency_ms"),
        request_chars=int(data.get("request_chars") or 0),
        response_chars=int(data.get("response_chars") or 0),
        metadata=metadata,
    )
    return {
        "ok": True,
        "call_id": data["call_id"],
        "database_result": result,
        "cost_usd": data.get("cost_usd"),
        "cost_status": data["cost_status"],
        "version": LOGGER_ADAPTER_VERSION,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


@dataclass
class NormalizedCallLogger:
    """Callable sink with process-local duplicate suppression by logical call ID."""

    db: SavingsCallStore | None = None
    operation: str = "model_cognome"
    mode: str = ""
    _seen_call_ids: set[str] = field(default_factory=set, init=False, repr=False)

    def __call__(self, record: Mapping[str, Any]) -> dict[str, Any]:
        data = _validate_record(record)
        call_id = str(data["call_id"])
        if call_id in self._seen_call_ids:
            return {
                "ok": True,
                "call_id": call_id,
                "duplicate_suppressed": True,
                "cost_usd": data.get("cost_usd"),
                "cost_status": data["cost_status"],
                "version": LOGGER_ADAPTER_VERSION,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        result = log_normalized_call(
            data,
            db=self.db,
            operation=self.operation,
            mode=self.mode,
        )
        self._seen_call_ids.add(call_id)
        result["duplicate_suppressed"] = False
        return result

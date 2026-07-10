"""
Aura Cost Telemetry Events — event protocol for real-time UI updates.

Events: cost_run_started, provider_usage_received, cost_stage_completed,
quality_gate_started, quality_gate_passed, quality_gate_failed,
savings_provisional, savings_verified, savings_invalidated, cost_run_completed.

The UI must continue functioning when the live stream is unavailable.

Dependencies: stdlib only.
"""
from __future__ import annotations

import json
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
TELEMETRY_VERSION = "AURA_COST_TELEMETRY_EVENTS_V1"

# Event types
EVENT_TYPES = [
    "cost_run_started",
    "provider_usage_received",
    "cost_stage_completed",
    "quality_gate_started",
    "quality_gate_passed",
    "quality_gate_failed",
    "savings_provisional",
    "savings_verified",
    "savings_invalidated",
    "cost_run_completed",
]

# Visual states for UI
VISUAL_STATES = {
    "unavailable": "grey",
    "measuring": "blue",
    "estimate": "yellow",
    "verified": "green",
    "invalidated": "red",
    "counterfactual": "purple",
}

# Keys that should never be stored in events
SECRET_KEYS = ["api_key", "secret", "token", "password", "secret_field"]


class TelemetryEventStream:
    """Bounded event stream for real-time UI updates."""

    def __init__(self, max_events: int = 1000) -> None:
        self._events: list[dict[str, Any]] = []
        self._max_events = max_events
        self._subscribers: list = []  # Callable subscribers

    def emit(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Emit a telemetry event."""
        if event_type not in EVENT_TYPES:
            return {"ok": False, "error": f"Unknown event type: {event_type}"}

        # Filter out secret keys
        filtered_data = {k: v for k, v in data.items() if k not in SECRET_KEYS}

        event = {
            "event": event_type,
            "timestamp": time.time(),
            "version": TELEMETRY_VERSION,
            **filtered_data,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        # Notify subscribers
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:
                pass

        return {"ok": True, "event": event}

    def subscribe(self, callback) -> None:
        """Subscribe to events."""
        self._subscribers.append(callback)

    def get_events(self, since: float = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Get events since a timestamp."""
        result = [e for e in self._events if e.get("timestamp", 0) >= since]
        return result[-limit:]

    def clear(self) -> None:
        self._events.clear()

    def event_count(self) -> int:
        return len(self._events)


# Global event stream instance
_global_stream: TelemetryEventStream | None = None


def get_telemetry_stream() -> TelemetryEventStream:
    """Get the global telemetry event stream."""
    global _global_stream
    if _global_stream is None:
        _global_stream = TelemetryEventStream()
    return _global_stream


def emit_cost_run_started(run_id: str, comparison_id: str, mode: str, provider: str, model: str) -> dict[str, Any]:
    return get_telemetry_stream().emit("cost_run_started", {
        "run_id": run_id, "comparison_id": comparison_id,
        "mode": mode, "provider": provider, "model": model,
    })


def emit_provider_usage_received(run_id: str, usage: dict[str, Any]) -> dict[str, Any]:
    return get_telemetry_stream().emit("provider_usage_received", {
        "run_id": run_id, "usage": usage,
    })


def emit_cost_stage_completed(run_id: str, comparison_id: str, stage: str,
                               measurement_class: str, input_tokens: int | None,
                               output_tokens: int | None, exclusive_tokens_saved: int,
                               elapsed_ms: float) -> dict[str, Any]:
    return get_telemetry_stream().emit("cost_stage_completed", {
        "run_id": run_id, "comparison_id": comparison_id, "stage": stage,
        "measurement_class": measurement_class,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "exclusive_tokens_saved": exclusive_tokens_saved, "elapsed_ms": elapsed_ms,
    })


def emit_quality_gate(run_id: str, passed: bool, tests_run: int = 0, tests_failed: int = 0) -> dict[str, Any]:
    event_type = "quality_gate_passed" if passed else "quality_gate_failed"
    return get_telemetry_stream().emit(event_type, {
        "run_id": run_id, "passed": passed,
        "tests_run": tests_run, "tests_failed": tests_failed,
    })


def emit_savings_status(run_id: str, status: str, savings: float | None = None) -> dict[str, Any]:
    event_map = {
        "SAVINGS_PROVISIONAL": "savings_provisional",
        "SAVINGS_VERIFIED": "savings_verified",
        "SAVINGS_INVALIDATED_BY_QUALITY": "savings_invalidated",
    }
    event_type = event_map.get(status, "savings_provisional")
    return get_telemetry_stream().emit(event_type, {
        "run_id": run_id, "savings_status": status, "savings_usd": savings,
    })


def emit_cost_run_completed(run_id: str, comparison_id: str, total_cost: float | None,
                             verification_status: str, savings_status: str) -> dict[str, Any]:
    return get_telemetry_stream().emit("cost_run_completed", {
        "run_id": run_id, "comparison_id": comparison_id,
        "total_cost_usd": total_cost, "verification_status": verification_status,
        "savings_status": savings_status,
    })


def format_event_as_sse(event: dict[str, Any]) -> str:
    """Format an event as Server-Sent Events data."""
    return f"data: {json.dumps(event, default=str)}\n\n"


def visual_state_for_measurement_class(measurement_class: str) -> str:
    """Map measurement class to visual state color."""
    mapping = {
        "MEASURED": "green",
        "TOKENIZER_EXACT": "green",
        "DERIVED": "blue",
        "ESTIMATED": "yellow",
        "UNAVAILABLE": "grey",
        "COUNTERFACTUAL_ESTIMATE": "purple",
        "PAIRED_MEASURED": "green",
        "REPLAY_FIXTURE": "blue",
    }
    return mapping.get(measurement_class, "grey")


def visual_state_for_savings(savings_status: str) -> str:
    """Map savings status to visual state color."""
    mapping = {
        "SAVINGS_VERIFIED": "green",
        "SAVINGS_PROVISIONAL": "yellow",
        "SAVINGS_INCONCLUSIVE": "grey",
        "SAVINGS_INVALIDATED_BY_QUALITY": "red",
        "NO_COMPARABLE_BASELINE": "grey",
    }
    return mapping.get(savings_status, "grey")

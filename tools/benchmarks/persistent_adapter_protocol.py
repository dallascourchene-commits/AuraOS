from __future__ import annotations

import re
from typing import Any


PROTOCOL_ID = "AURA_BENCHMARK_PERSISTENT_ADAPTER_V1"
_TELEMETRY_PROVENANCE = {"OBSERVED", "ESTIMATED", "UNKNOWN"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_handshake(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("HANDSHAKE_MUST_BE_OBJECT")
    if payload.get("type") != "adapter_handshake":
        raise ValueError("INVALID_HANDSHAKE_TYPE")
    if payload.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("INVALID_PROTOCOL_ID")
    generation = payload.get("adapter_generation")
    if not isinstance(generation, str) or not generation.strip():
        raise ValueError("ADAPTER_GENERATION_REQUIRED")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError("CAPABILITIES_REQUIRED")
    if capabilities.get("persistent_process") is not True:
        raise ValueError("PERSISTENT_PROCESS_REQUIRED")
    if capabilities.get("state_digest") is not True:
        raise ValueError("STATE_DIGEST_CAPABILITY_REQUIRED")
    telemetry = capabilities.get("telemetry_provenance")
    if not isinstance(telemetry, list) or not telemetry:
        raise ValueError("TELEMETRY_PROVENANCE_CAPABILITY_REQUIRED")
    if any(item not in _TELEMETRY_PROVENANCE for item in telemetry):
        raise ValueError("INVALID_TELEMETRY_PROVENANCE_CAPABILITY")
    return {
        "type": "adapter_handshake",
        "protocol_id": PROTOCOL_ID,
        "adapter_generation": generation.strip(),
        "capabilities": {
            "persistent_process": True,
            "state_digest": True,
            "per_turn_timeout_control": capabilities.get("per_turn_timeout_control") is True,
            "provider_usage_receipts": capabilities.get("provider_usage_receipts") is True,
            "telemetry_provenance": sorted(set(telemetry)),
        },
    }


def _validate_telemetry(telemetry: dict[str, Any]) -> dict[str, Any]:
    provenance = telemetry.get("provenance", "UNKNOWN")
    if provenance not in _TELEMETRY_PROVENANCE:
        raise ValueError("INVALID_TELEMETRY_PROVENANCE")
    metric_keys = ("input_tokens", "output_tokens", "cost_usd", "peak_rss_mb")
    if provenance == "UNKNOWN" and any(telemetry.get(key) is not None for key in metric_keys):
        raise ValueError("UNKNOWN_TELEMETRY_CANNOT_CARRY_VALUES")
    for key in ("input_tokens", "output_tokens"):
        value = telemetry.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise ValueError(f"INVALID_{key.upper()}")
    for key in ("cost_usd", "peak_rss_mb"):
        value = telemetry.get(key)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0):
            raise ValueError(f"INVALID_{key.upper()}")
    return telemetry


def validate_turn_response(
    payload: dict[str, Any],
    *,
    expected_turn: int,
    adapter_generation: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("TURN_RESPONSE_MUST_BE_OBJECT")
    if payload.get("type") != "turn_result":
        raise ValueError("INVALID_TURN_RESPONSE_TYPE")
    if payload.get("turn") != expected_turn:
        raise ValueError("TURN_ID_MISMATCH")
    if payload.get("adapter_generation") != adapter_generation:
        raise ValueError("ADAPTER_GENERATION_MISMATCH")
    state_digest = payload.get("state_digest")
    if not isinstance(state_digest, str) or not _SHA256_RE.fullmatch(state_digest.lower()):
        raise ValueError("STATE_DIGEST_MUST_BE_SHA256")
    telemetry = payload.get("telemetry", {"provenance": "UNKNOWN"})
    if not isinstance(telemetry, dict):
        raise ValueError("INVALID_TELEMETRY")
    telemetry = _validate_telemetry(telemetry)
    return {
        "type": "turn_result",
        "turn": expected_turn,
        "adapter_generation": adapter_generation,
        "state_digest": state_digest.lower(),
        "telemetry": telemetry,
    }


def make_turn_request(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("WORKLOAD_ITEM_MUST_BE_OBJECT")
    turn = item.get("turn")
    operation = item.get("operation")
    if not isinstance(turn, int) or isinstance(turn, bool) or turn < 0:
        raise ValueError("INVALID_TURN")
    if not isinstance(operation, dict):
        raise ValueError("INVALID_OPERATION")
    return {
        "type": "turn_request",
        "protocol_id": PROTOCOL_ID,
        "turn": turn,
        "operation": operation,
    }

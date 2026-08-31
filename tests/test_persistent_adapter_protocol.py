from __future__ import annotations

import pytest

from tools.benchmarks.persistent_adapter_protocol import (
    PROTOCOL_ID,
    make_turn_request,
    validate_handshake,
    validate_turn_response,
)


D = "a" * 64


def handshake():
    return {
        "type": "adapter_handshake",
        "protocol_id": PROTOCOL_ID,
        "adapter_generation": "pi-rpc-wrapper-v1",
        "capabilities": {
            "persistent_process": True,
            "state_digest": True,
            "per_turn_timeout_control": True,
            "provider_usage_receipts": False,
            "telemetry_provenance": ["UNKNOWN", "OBSERVED"],
        },
    }


def test_handshake_preserves_generation_and_capabilities():
    normalized = validate_handshake(handshake())
    assert normalized["adapter_generation"] == "pi-rpc-wrapper-v1"
    assert normalized["capabilities"]["persistent_process"] is True
    assert normalized["capabilities"]["state_digest"] is True
    assert normalized["capabilities"]["telemetry_provenance"] == ["OBSERVED", "UNKNOWN"]


def test_nonpersistent_adapter_cannot_claim_persistent_protocol():
    bad = handshake()
    bad["capabilities"]["persistent_process"] = False
    with pytest.raises(ValueError, match="PERSISTENT_PROCESS_REQUIRED"):
        validate_handshake(bad)


def test_turn_response_is_bound_to_turn_and_adapter_generation():
    payload = {
        "type": "turn_result",
        "turn": 3,
        "adapter_generation": "pi-rpc-wrapper-v1",
        "state_digest": D,
        "telemetry": {"provenance": "UNKNOWN"},
    }
    normalized = validate_turn_response(
        payload,
        expected_turn=3,
        adapter_generation="pi-rpc-wrapper-v1",
    )
    assert normalized["turn"] == 3
    assert normalized["state_digest"] == D

    with pytest.raises(ValueError, match="TURN_ID_MISMATCH"):
        validate_turn_response(payload, expected_turn=4, adapter_generation="pi-rpc-wrapper-v1")
    with pytest.raises(ValueError, match="ADAPTER_GENERATION_MISMATCH"):
        validate_turn_response(payload, expected_turn=3, adapter_generation="aura-wrapper-v1")


def test_unknown_telemetry_still_cannot_carry_zero():
    payload = {
        "type": "turn_result",
        "turn": 0,
        "adapter_generation": "aura-wrapper-v1",
        "state_digest": D,
        "telemetry": {"provenance": "UNKNOWN", "input_tokens": 0},
    }
    with pytest.raises(ValueError, match="UNKNOWN_TELEMETRY_CANNOT_CARRY_VALUES"):
        validate_turn_response(payload, expected_turn=0, adapter_generation="aura-wrapper-v1")


def test_turn_request_does_not_include_expected_state_digest():
    request = make_turn_request(
        {
            "turn": 5,
            "operation": {"type": "get", "key": "k1", "expected": 7},
            "expected_state_digest": D,
        }
    )
    assert request == {
        "type": "turn_request",
        "protocol_id": PROTOCOL_ID,
        "turn": 5,
        "operation": {"type": "get", "key": "k1", "expected": 7},
    }
    assert "expected_state_digest" not in request

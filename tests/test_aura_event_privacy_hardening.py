from __future__ import annotations

import json

import pytest

from aura_event_contracts import AppendOnlyEventStore, sanitize_payload, stable_digest


@pytest.mark.parametrize(
    "field_name",
    [
        "scratchpad",
        "scratch_pad",
        "scratchPad",
        "internalScratchpad",
        "modelChainOfThought",
    ],
)
def test_private_reasoning_aliases_fail_closed(field_name: str) -> None:
    with pytest.raises(ValueError, match="private reasoning"):
        sanitize_payload({field_name: "must never persist"})


@pytest.mark.parametrize(
    "payload",
    [
        '{"access_token": "abc/DEF+ghi~=123"}',
        "access_token: abc/DEF+ghi~=123",
        "Authorization: Bearer abc/DEF+ghi~=123",
        "https://example.test/?access_token=abc/DEF+ghi~=123",
        "authorization=Bearer abc/DEF+ghi~=123",
        "log refresh_token='abc/DEF+ghi~=123'",
    ],
)
def test_string_level_credentials_are_fully_redacted(payload: str) -> None:
    sanitized = sanitize_payload(payload)
    assert "abc/DEF+ghi~=123" not in sanitized
    assert "[REDACTED]" in sanitized


def test_nested_serialized_tool_output_is_redacted_before_digest_and_persistence(tmp_path) -> None:
    payload = {
        "items": [
            {"message": '{"access_token":"abc/DEF+ghi~=123"}'},
            "Authorization: Bearer abc/DEF+ghi~=123",
            ["refresh_token=abc/DEF+ghi~=123"],
        ]
    }
    sanitized = sanitize_payload(payload)
    encoded = json.dumps(sanitized, sort_keys=True)
    assert "abc/DEF+ghi~=123" not in encoded

    expected_digest = stable_digest(sanitized)
    store = AppendOnlyEventStore(tmp_path / "events")
    ref = store.store_payload(payload, kind="privacy-regression")
    persisted = (store.root / ref.path).read_text(encoding="utf-8")

    assert ref.payload_digest == expected_digest
    assert ref.redacted is True
    assert "abc/DEF+ghi~=123" not in persisted
    assert "[REDACTED]" in persisted


def test_benign_token_metrics_are_not_redacted() -> None:
    payload = {"token_count": 42, "input_tokens": 100}
    assert sanitize_payload(payload) == payload
